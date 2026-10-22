#!/usr/bin/env python3
"""Translate README.md to Korean with Argos Translate without changing code/URLs.

This is intentionally fail-closed: failures never commit broken translations.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Callable

SOURCE = Path("README.md")
DESTINATION = Path("README_KO.md")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
PREFIX = re.compile(r"^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)?)")
PROTECTED = re.compile(r"(`+[^`\n]+`+|\[[^\]]+\]\([^)]+\)|https?://[^\s)]+)")


def translate_piece(part: str, translate: Callable[[str], str]) -> str:
    if not re.search("[A-Za-z]", part):
        return part
    leading = len(part) - len(part.lstrip())
    trailing = len(part) - len(part.rstrip())
    core = part.strip()
    if not core:
        return part
    translated = translate(core).strip()
    if not translated:
        raise RuntimeError(f"Translation returned empty content for: {core[:120]}")
    return part[:leading] + translated + (part[-trailing:] if trailing else "")


def translate_markdown(text: str, translate: Callable[[str], str]) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        suffix = "\n" if line.endswith("\n") else ""
        body = line[:-1] if suffix else line
        marker = FENCE.match(body)
        if marker:
            current = marker.group(1)
            if fence is None:
                fence = current
            elif current[0] == fence[0] and len(current) >= len(fence):
                fence = None
            output.append(line)
            continue
        if fence or not body.strip() or body.lstrip().startswith("<!--"):
            output.append(line)
            continue
        prefix = PREFIX.match(body).group(1)
        remaining = body[len(prefix):]
        parts: list[str] = []
        last = 0
        for token in PROTECTED.finditer(remaining):
            parts.append(translate_piece(remaining[last:token.start()], translate))
            parts.append(token.group(0))
            last = token.end()
        parts.append(translate_piece(remaining[last:], translate))
        output.append(prefix + "".join(parts) + suffix)
    if fence is not None:
        raise RuntimeError("Unclosed Markdown code fence")
    return "".join(output)


def offline_translator() -> Callable[[str], str]:
    from argostranslate import package, translate

    installed = [
        item for item in package.get_installed_packages()
        if item.from_code == "en" and item.to_code == "ko"
    ]
    if not installed:
        package.update_package_index()
        available = package.get_available_packages()
        model = next((item for item in available
                      if item.from_code == "en" and item.to_code == "ko"), None)
        if model is None:
            raise RuntimeError("English-to-Korean Argos model is unavailable")
        package.install_from_path(model.download())
    return lambda sentence: translate.translate(sentence, "en", "ko")


def main() -> None:
    original = SOURCE.read_text(encoding="utf-8")
    translated = translate_markdown(original, offline_translator())
    if PROTECTED.findall(original) != PROTECTED.findall(translated):
        raise RuntimeError("Inline code or links were changed by translation")
    if original.count("```") != translated.count("```"):
        raise RuntimeError("Fenced code blocks were modified")
    if not re.search("[가-힣]", translated):
        raise RuntimeError("Translation did not produce Korean content")
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
    header = (f"<!-- Auto-generated from README.md with Argos Translate. "
              f"Source SHA-256: {digest}. -->\n\n")
    DESTINATION.write_text(header + translated, encoding="utf-8")
    print(f"Wrote {DESTINATION} from {SOURCE}; SHA-256={digest}")


if __name__ == "__main__":
    main()
