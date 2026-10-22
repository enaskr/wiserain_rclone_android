"""Offline tests for Markdown structure preservation in the Korean README generator."""
import unittest

from translate_readme import PROTECTED, translate_markdown


class ReadmeTranslationTests(unittest.TestCase):
    def setUp(self):
        self.translate = lambda value: "번역(" + value + ")"

    def test_code_fences_stay_unchanged(self):
        source = "# Features\n\n```kotlin\ndependencies {\n  implementation(files(\"libs/rclone.aar\"))\n}\n```\n"
        output = translate_markdown(source, self.translate)
        self.assertIn("```kotlin\ndependencies {\n  implementation(files(\"libs/rclone.aar\"))\n}\n```", output)
        self.assertIn("번역(Features)", output)

    def test_markdown_links_inline_code_and_urls(self):
        source = "- Install `gomobile` and see [wiserain/rclone](https://github.com/wiserain/rclone).\n"
        output = translate_markdown(source, self.translate)
        self.assertEqual(PROTECTED.findall(source), PROTECTED.findall(output))
        self.assertIn("`gomobile`", output)

    def test_reviewed_override_does_not_call_machine_translator(self):
        source = "- Upstream release changes\n"
        result = translate_markdown(
            source, lambda _x: self.fail("Unexpected machine translation"),
            {"- Upstream release changes": "- 원본 릴리스 변경\n".rstrip("\n")},
        )
        self.assertEqual(result, "- 원본 릴리스 변경\n")

    def test_empty_input(self):
        self.assertEqual(translate_markdown("", self.translate), "")

    def test_unclosed_fence_fails(self):
        with self.assertRaises(RuntimeError):
            translate_markdown("```bash\necho hello\n", self.translate)

    def test_blank_translation_fails_closed(self):
        with self.assertRaises(RuntimeError):
            translate_markdown("# Important\n", lambda _x: "")


if __name__ == "__main__":
    unittest.main()
