from __future__ import annotations

import re
from pathlib import Path


AUDITED_FILE_OPERATION_FILES = {
    "scripts/package_launch_smoke.py",
    "scripts/package_windows.py",
    "scripts/stress_matrix.py",
    "src/modori/cache.py",
    "src/modori/knowledge/loader.py",
    "src/modori/path_policy.py",
    "src/modori/steps/reporting.py",
    "src/modori/ui/resources.py",
    "src/modori/ui/result_binding.py",
    "src/modori/ui/session.py",
    "src/modori/ui/settings.py",
}

FILE_OPERATION_PATTERN = re.compile(
    r"\.(?:write_text|write_bytes|mkdir|unlink|replace|rmdir|resolve)\s*\("
)
AUDIT_DOCUMENT = Path("docs/security/file-operations-audit-2026-06-29.md")


def _product_file_operation_files() -> set[str]:
    files: set[str] = set()
    for root in (Path("src"), Path("scripts")):
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if FILE_OPERATION_PATTERN.search(text):
                files.add(path.as_posix())
    return files


def test_direct_file_operations_remain_in_audited_files() -> None:
    assert _product_file_operation_files() == AUDITED_FILE_OPERATION_FILES


def test_file_operation_audit_document_covers_every_audited_file() -> None:
    text = AUDIT_DOCUMENT.read_text(encoding="utf-8")

    missing = [
        file_path
        for file_path in sorted(AUDITED_FILE_OPERATION_FILES)
        if file_path not in text
    ]

    assert missing == []
