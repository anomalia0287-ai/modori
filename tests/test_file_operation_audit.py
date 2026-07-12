from __future__ import annotations

import re
from pathlib import Path


AUDITED_FILE_OPERATION_FILES = {
    "scripts/build_installer.py",
    "scripts/installer_contract.py",
    "scripts/installer_smoke.py",
    "scripts/quality_gate.py",
    "scripts/package_engine_smoke.py",
    "scripts/package_environment.py",
    "scripts/package_launch_smoke.py",
    "scripts/package_public_data_smoke.py",
    "scripts/package_windows.py",
    "scripts/stress_matrix.py",
    "src/modori/app.py",
    "src/modori/cache.py",
    "src/modori/knowledge/loader.py",
    "src/modori/path_policy.py",
    "src/modori/public_data_smoke.py",
    "src/modori/ui/chart_assets.py",
    "src/modori/steps/reporting.py",
    "src/modori/ui/worker.py",
    "src/modori/ui/resources.py",
    "src/modori/ui/result_binding.py",
    "src/modori/ui/session.py",
    "src/modori/ui/settings.py",
}

FILE_OPERATION_PATTERN = re.compile(
    r"(?:\.(?:write_text|write_bytes|mkdir|unlink|replace|rmdir|resolve|lstat)"
    r"|shutil\.(?:copyfile|copytree)|os\.scandir)\s*\("
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


def test_installer_smoke_audit_documents_bounded_recursive_state_cleanup() -> None:
    row = next(
        line
        for line in AUDIT_DOCUMENT.read_text(encoding="utf-8").splitlines()
        if "`scripts/installer_smoke.py`" in line
    )

    for required_text in (
        "entire install root",
        "direct child",
        "every descendant",
        "symlink/junction/reparse",
        "recursive",
        "sibling logs",
    ):
        assert required_text in row


def test_installer_builder_audit_documents_frozen_staging_boundary() -> None:
    row = next(
        line
        for line in AUDIT_DOCUMENT.read_text(encoding="utf-8").splitlines()
        if "`scripts/build_installer.py`" in line
    )

    for required_text in (
        "full-tree snapshot",
        "exact installer script",
        "content SHA",
        "installed lifecycle",
        "staging-only",
        "preserved on failure",
        "selected compiler",
        "fixed file version",
        "SHA256",
        "before and after every ISCC",
        "tiny downgrade",
        "lexical",
        "junction/reparse",
        "after candidate materialization",
        "three regular non-reparse",
        "scandir",
    ):
        assert required_text in row
