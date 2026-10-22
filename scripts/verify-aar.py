#!/usr/bin/env python3
"""Validate arm64-v8a ELF 16 KiB alignment and ckReader JNI bindings.

Other ABIs may be included by gomobile but are intentionally outside the
compatibility gate. Do not claim that they have passed validation.
"""

from __future__ import annotations

import io
import json
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

PAGE_SIZE = 16 * 1024
# Only the ARM64 binary is a release-blocking compatibility target.
# gomobile still produces its normal multi-ABI AAR.
ABI_ELF = {
    "arm64-v8a": (2, 183),  # ELF64 / EM_AARCH64
}
REQUIRED_METHODS = (
    "rcloneInitialize",
    "rcloneRPC",
    "rcloneFinalize",
    "rcloneStatSize",
    "rcloneReadRange",
)


def verify_elf_alignment(data: bytes, abi: str) -> list[int]:
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[5] != 1:
        raise ValueError(f"{abi}: invalid or non-little-endian ELF")
    expected_class, expected_machine = ABI_ELF[abi]
    if data[4] != expected_class:
        raise ValueError(f"{abi}: unexpected ELF class {data[4]}")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != expected_machine:
        raise ValueError(f"{abi}: unexpected ELF machine {machine}")
    if data[4] == 2:
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phentsize, phnum = struct.unpack_from("<HH", data, 54)
        min_entry, offset_pos, addr_pos, align_pos = 56, 8, 16, 48
        addr_format = "<Q"
    else:
        phoff = struct.unpack_from("<I", data, 28)[0]
        phentsize, phnum = struct.unpack_from("<HH", data, 42)
        min_entry, offset_pos, addr_pos, align_pos = 32, 4, 8, 28
        addr_format = "<I"
    if phentsize < min_entry or phnum < 1 or phoff + phentsize * phnum > len(data):
        raise ValueError(f"{abi}: invalid ELF program header table")
    load_alignments = []
    for i in range(phnum):
        start = phoff + i * phentsize
        p_type = struct.unpack_from("<I", data, start)[0]
        if p_type != 1:  # PT_LOAD
            continue
        offset = struct.unpack_from(addr_format, data, start + offset_pos)[0]
        address = struct.unpack_from(addr_format, data, start + addr_pos)[0]
        align = struct.unpack_from(addr_format, data, start + align_pos)[0]
        if align < PAGE_SIZE or align % PAGE_SIZE != 0:
            raise ValueError(f"{abi}: PT_LOAD[{i}] p_align={align}, requires >=16384")
        if offset % PAGE_SIZE != address % PAGE_SIZE:
            raise ValueError(f"{abi}: PT_LOAD[{i}] offset and virtual address are not 16 KiB congruent")
        load_alignments.append(align)
    if not load_alignments:
        raise ValueError(f"{abi}: no loadable ELF segments")
    return load_alignments


def verify_java_bindings(jar_bytes: bytes, tmp: pathlib.Path) -> list[str]:
    jar_path = tmp / "classes.jar"
    jar_path.write_bytes(jar_bytes)
    with zipfile.ZipFile(io.BytesIO(jar_bytes)) as jar:
        binding = jar.read("org/rclone/gomobile/Gomobile.class")
        if not binding:
            raise ValueError("Gomobile.class is empty")
    details = subprocess.run(
        ["javap", "-classpath", str(jar_path), "-public",
         "org.rclone.gomobile.Gomobile"],
        check=True, text=True, capture_output=True,
    ).stdout
    methods = set(re.findall(r"\b(rclone(?:Initialize|RPC|Finalize|StatSize|ReadRange))\s*\(", details))
    missing = sorted(set(REQUIRED_METHODS) - methods)
    if missing:
        raise ValueError(f"Missing Java/JNI binding methods: {', '.join(missing)}")
    if not re.search(r"\blong\s+rcloneStatSize\(java\.lang\.String,\s*java\.lang\.String\)", details):
        raise ValueError("rcloneStatSize JNI signature mismatch")
    # gobind maps Go int to Java long on some architectures/versions.
    # Check API shape while allowing either valid numeric count representation.
    read_range_declarations = [
        line.strip() for line in details.splitlines()
        if "rcloneReadRange(" in line
    ]
    print("Java rcloneReadRange declaration:", read_range_declarations)
    if not re.search(
        r"\bbyte\[\]\s+rcloneReadRange\(java\.lang\.String,\s*java\.lang\.String,\s*long,\s*(?:int|long)\)",
        details,
    ):
        raise ValueError(
            "rcloneReadRange JNI signature mismatch: "
            + "; ".join(read_range_declarations)
        )
    return sorted(methods)


def inspect_jni_exports(readelf_output: str, abi: str) -> dict:
    """Accept Android JNI registration via JNI_OnLoad or named Java_* entrypoints."""
    exported = set(re.findall(r"\b(?:JNI_OnLoad|Java_[A-Za-z0-9_]+)\b", readelf_output))
    if "JNI_OnLoad" in exported:
        return {"mode": "JNI_OnLoad", "exports": ["JNI_OnLoad"]}
    named = sorted(symbol for symbol in exported if symbol.startswith("Java_"))
    missing = [
        method for method in REQUIRED_METHODS
        if not any(method in symbol for symbol in named)
    ]
    if missing:
        raise ValueError(
            f"{abi}: required native JNI exports missing: {', '.join(missing)}; "
            f"found: {', '.join(named[:20]) or '(none)'}"
        )
    return {"mode": "named_jni_exports", "exports": [
        next(symbol for symbol in named if method in symbol)
        for method in REQUIRED_METHODS
    ]}


def verify_jni_loader(data: bytes, abi: str, tmp: pathlib.Path) -> dict:
    path = tmp / f"{abi}.so"
    path.write_bytes(data)
    output = subprocess.run(
        ["readelf", "-W", "--dyn-syms", str(path)],
        check=True, text=True, encoding="utf-8", errors="replace",
        capture_output=True,
    ).stdout
    return inspect_jni_exports(output, abi)


def verify_aar(path: pathlib.Path, report_path: pathlib.Path | None = None) -> dict:
    if not path.is_file() or path.stat().st_size < 1024:
        raise ValueError(f"Missing or empty AAR: {path}")
    report = {
        "aar": path.name,
        "required_page_alignment": PAGE_SIZE,
        "verified_abis": list(ABI_ELF),
        "abis": {},
    }
    with tempfile.TemporaryDirectory() as temp:
        tmp = pathlib.Path(temp)
        with zipfile.ZipFile(path) as aar:
            bad_entry = aar.testzip()
            if bad_entry:
                raise ValueError(f"AAR ZIP corruption: {bad_entry}")
            report["java_methods"] = verify_java_bindings(aar.read("classes.jar"), tmp)
            for abi in ABI_ELF:
                entry = f"jni/{abi}/libgojni.so"
                native = aar.read(entry)
                alignments = verify_elf_alignment(native, abi)
                jni = verify_jni_loader(native, abi, tmp)
                report["abis"][abi] = {
                    "jni_lib": entry,
                    "bytes": len(native),
                    "pt_load_alignment": alignments,
                    "jni": jni,
                }
                print(f"{abi}: 16 KiB PT_LOAD alignment OK, JNI mode={jni['mode']}, segments={alignments}")
    print(f"Java bindings: {', '.join(report['java_methods'])}")
    print("Verification scope: arm64-v8a only (other ABIs are not compatibility-checked)")
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: verify-aar.py <rclone.aar> [report.json]")
    report = pathlib.Path(sys.argv[2]) if len(sys.argv) == 3 else None
    verify_aar(pathlib.Path(sys.argv[1]), report)


if __name__ == "__main__":
    main()
