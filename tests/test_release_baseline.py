from __future__ import annotations

from pathlib import Path


def test_gitignore_exists_and_excludes_generated_roots() -> None:
    gitignore = Path(".gitignore")

    assert gitignore.is_file()
    text = gitignore.read_text(encoding="utf-8")
    for pattern in [
        ".venv/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".test-tmp/",
        ".modori_cache/",
        ".tongtong_cache/",
        ".pip-audit-cache/",
        ".tools/",
        ".visual-qa/",
        "__pycache__/",
        "*.pyc",
        "*.spec",
    ]:
        assert pattern in text


def test_gitattributes_pins_text_line_endings() -> None:
    attributes = Path(".gitattributes")

    assert attributes.is_file()
    text = attributes.read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in text
