"""Regression checks for ckReader Android AAR 16 KiB ELF policy."""
import importlib.util
import pathlib
import struct
import unittest


MODULE = pathlib.Path(__file__).with_name("verify-aar.py")
SPEC = importlib.util.spec_from_file_location("aar_verifier", str(MODULE))
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def make_elf(abi, alignment=16384, offset=0, address=0):
    elf_class, machine = VERIFIER.ABI_ELF[abi]
    image = bytearray(256)
    image[:6] = bytes((127, 69, 76, 70, elf_class, 1))
    struct.pack_into("<H", image, 18, machine)
    if elf_class == 2:
        struct.pack_into("<Q", image, 32, 64)
        struct.pack_into("<HH", image, 54, 56, 1)
        struct.pack_into("<I", image, 64, 1)
        struct.pack_into("<Q", image, 64 + 8, offset)
        struct.pack_into("<Q", image, 64 + 16, address)
        struct.pack_into("<Q", image, 64 + 48, alignment)
    else:
        struct.pack_into("<I", image, 28, 52)
        struct.pack_into("<HH", image, 42, 32, 1)
        struct.pack_into("<I", image, 52, 1)
        struct.pack_into("<I", image, 52 + 4, offset)
        struct.pack_into("<I", image, 52 + 8, address)
        struct.pack_into("<I", image, 52 + 28, alignment)
    return bytes(image)


class Test16KiBAlignment(unittest.TestCase):
    def test_all_four_abis_accept_16k(self):
        for abi in VERIFIER.ABI_ELF:
            with self.subTest(abi=abi):
                self.assertEqual(VERIFIER.verify_elf_alignment(make_elf(abi), abi), [16384])

    def test_all_four_abis_reject_4k(self):
        for abi in VERIFIER.ABI_ELF:
            with self.subTest(abi=abi), self.assertRaises(ValueError):
                VERIFIER.verify_elf_alignment(make_elf(abi, alignment=4096), abi)

    def test_all_four_abis_reject_misaligned_load_address(self):
        for abi in VERIFIER.ABI_ELF:
            with self.subTest(abi=abi), self.assertRaises(ValueError):
                VERIFIER.verify_elf_alignment(make_elf(abi, address=4096), abi)

    def test_accept_static_jni_exports(self):
        exports = [
            "Java_org_rclone_gomobile_Gomobile_" + method
            for method in VERIFIER.REQUIRED_METHODS
        ]
        symbols = "\n".join(
            f"100: 00000000 0 FUNC GLOBAL DEFAULT 12 {name}"
            for name in exports
        )
        result = VERIFIER.inspect_jni_exports(symbols, "arm64-v8a")
        self.assertEqual(result["mode"], "named_jni_exports")
        self.assertEqual(len(result["exports"]), len(VERIFIER.REQUIRED_METHODS))

    def test_accept_registration_via_jni_onload(self):
        result = VERIFIER.inspect_jni_exports(
            "2: 00000000 0 FUNC GLOBAL DEFAULT 12 JNI_OnLoad", "arm64-v8a"
        )
        self.assertEqual(result["mode"], "JNI_OnLoad")

    def test_non_utf8_symbol_table_text_keeps_ascii_exports(self):
        exported = [
            "Java_org_rclone_gomobile_Gomobile_" + method
            for method in VERIFIER.REQUIRED_METHODS
        ]
        raw = b"\xffsymbol\xfe\n" + "\n".join(exported).encode("ascii")
        decoded = raw.decode("utf-8", errors="replace")
        result = VERIFIER.inspect_jni_exports(decoded, "x86")
        self.assertEqual(result["mode"], "named_jni_exports")

    def test_missing_jni_export_rejected(self):
        with self.assertRaises(ValueError):
            VERIFIER.inspect_jni_exports(
                "1: 00000000 0 FUNC GLOBAL DEFAULT 12 Java_test_rcloneRPC",
                "x86_64",
            )

    def test_reject_elf_machine_mismatch(self):
        for abi in VERIFIER.ABI_ELF:
            with self.subTest(abi=abi), self.assertRaises(ValueError):
                image = bytearray(make_elf(abi))
                struct.pack_into("<H", image, 18, 0)
                VERIFIER.verify_elf_alignment(bytes(image), abi)


if __name__ == "__main__":
    unittest.main()
