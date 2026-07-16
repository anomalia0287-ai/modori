from __future__ import annotations

import re
from pathlib import Path


AUDITED_FILE_OPERATION_FILES = {
    "scripts/benchmark_counterfactual_clarification.py",
    "scripts/benchmark_research_memory.py",
    "scripts/build_office_research_memory_kit.py",
    "scripts/build_recommendation_pilot.py",
    "scripts/check_product_wording.py",
    "scripts/quality_gate.py",
    "scripts/package_engine_smoke.py",
    "scripts/package_environment.py",
    "scripts/package_launch_smoke.py",
    "scripts/package_public_data_smoke.py",
    "scripts/package_windows.py",
    "scripts/recommendation_benchmark.py",
    "scripts/run_office_research_memory_benchmark.py",
    "scripts/stress_matrix.py",
    "scripts/verify_office_research_memory_kit.py",
    "scripts/verify_release_integration.py",
    "src/modori/app.py",
    "src/modori/cache.py",
    "src/modori/knowledge/loader.py",
    "src/modori/path_policy.py",
    "src/modori/public_data_smoke.py",
    "src/modori/recommendation_baseline.py",
    "src/modori/recommendation_benchmark_io.py",
    "src/modori/research_memory/ledger_store.py",
    "src/modori/ui/chart_assets.py",
    "src/modori/steps/reporting.py",
    "src/modori/ui/worker.py",
    "src/modori/ui/resources.py",
    "src/modori/ui/result_binding.py",
    "src/modori/ui/session.py",
    "src/modori/ui/settings.py",
}

FILE_OPERATION_PATTERN = re.compile(
    r"(?:\.(?:write_text|write_bytes|mkdir|unlink|replace|rmdir|resolve)"
    r"|\bshutil\.rmtree)\s*\("
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
