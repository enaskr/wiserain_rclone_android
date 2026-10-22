#!/usr/bin/env python3
"""Fail closed unless every Android ABI has 16 KiB PT_LOAD alignment and ckReader JNI bindings."""

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
ABI_ELF = {
    "armeabi-v7a": (1, 40),  # ELF32 / EM_ARM
    "arm64-v8a": (2, 183),   # ELF64 / EM_AARCH64
    "x86": (1, 3),           # ELF32 / EM_386
    "x86_64": (2, 62),       # ELF64 / EM_X86_64
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
    if not re.search(r"\bbyte\[\]\s+rcloneReadRange\(java\.lang\.String,\s*java\.lang\.String,\s*long,\s*int\)", details):
        raise ValueError("rcloneReadRange JNI signature mismatch")
    return sorted(methods)


def verify_jni_loader(data: bytes, abi: str, tmp: pathlib.Path) -> None:
    path = tmp / f"{abi}.so"
    path.write_bytes(data)
    output = subprocess.run(
        ["readelf", "-W", "--dyn-syms", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout
    if not re.search(r"\bJNI_OnLoad\b", output):
        raise ValueError(f"{abi}: exported JNI_OnLoad is missing")


def verify_aar(path: pathlib.Path, report_path: pathlib.Path | None = None) -> dict:
    if not path.is_file() or path.stat().st_size < 1024:
        raise ValueError(f"Missing or empty AAR: {path}")
    report = {"aar": path.name, "required_page_alignment": PAGE_SIZE, "abis": {}}
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
                verify_jni_loader(native, abi, tmp)
                report["abis"][abi] = {
                    "jni_lib": entry,
                    "bytes": len(native),
                    "pt_load_alignment": alignments,
                    "jni_onload": True,
                }
                print(f"{abi}: 16 KiB PT_LOAD alignment OK, JNI_OnLoad exported, segments={alignments}")
    print(f"Java bindings: {', '.join(report['java_methods'])}")
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
