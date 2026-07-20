from __future__ import annotations

import ast
import re
from pathlib import Path


AUDITED_FILE_OPERATION_FILES = {
    "scripts/build_installer.py",
    "scripts/build_office_live_research_os_kit.py",
    "scripts/capture_entry_states.py",
    "scripts/capture_work_states.py",
    "scripts/installer_contract.py",
    "scripts/installer_smoke.py",
    "scripts/live_research_os_office_benchmark.py",
    "scripts/live_research_os_office_kit.py",
    "scripts/benchmark_counterfactual_clarification.py",
    "scripts/benchmark_research_memory.py",
    "scripts/build_office_research_memory_kit.py",
    "scripts/build_recommendation_pilot.py",
    "scripts/build_research_flow_visual_review_packet.py",
    "scripts/capture_research_flow_gallery.py",
    "scripts/check_product_wording.py",
    "scripts/quality_gate.py",
    "scripts/package_engine_smoke.py",
    "scripts/package_environment.py",
    "scripts/package_launch_smoke.py",
    "scripts/package_public_data_smoke.py",
    "scripts/package_windows.py",
    "scripts/prepare_build_week_demo_data.py",
    "scripts/recommendation_benchmark.py",
    "scripts/run_office_live_research_os_benchmark.py",
    "scripts/run_office_research_memory_benchmark.py",
    "scripts/stress_matrix.py",
    "scripts/verify_office_research_memory_kit.py",
    "scripts/verify_office_live_research_os_kit.py",
    "scripts/verify_release_integration.py",
    "src/modori/app.py",
    "src/modori/cache.py",
    "src/modori/knowledge/loader.py",
    "src/modori/path_policy.py",
    "src/modori/public_data_smoke.py",
    "src/modori/recommendation_baseline.py",
    "src/modori/recommendation_benchmark_io.py",
    "src/modori/research_memory/ledger_store.py",
    "src/modori/research_memory/task_index.py",
    "src/modori/ui/chart_assets.py",
    "src/modori/steps/reporting.py",
    "src/modori/ui/worker.py",
    "src/modori/ui/resources.py",
    "src/modori/ui/result_binding.py",
    "src/modori/ui/pipeline_ops.py",
    "src/modori/ui/report_export.py",
    "src/modori/ui/session.py",
    "src/modori/ui/settings.py",
}

FILE_OPERATION_PATTERN = re.compile(
    r"(?:\.(?:write_text|write_bytes|mkdir|unlink|replace|rmdir|resolve|lstat)"
    r"|shutil\.(?:copyfile|copytree|rmtree)|os\.scandir)\s*\("
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


def _audit_row(file_path: str) -> str:
    return next(
        line
        for line in AUDIT_DOCUMENT.read_text(encoding="utf-8").splitlines()
        if f"`{file_path}`" in line
    )


def _public_methods(file_path: str, class_name: str) -> set[str]:
    tree = ast.parse(Path(file_path).read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


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


def test_build_week_demo_builder_documents_its_offline_atomic_write_boundary() -> None:
    row = _audit_row("scripts/prepare_build_week_demo_data.py")

    for required_text in (
        "Developer-only offline",
        "fixed SHA-256",
        "caller-selected output",
        "unique temporary sibling",
        "atomically",
        "only its own incomplete temporary file",
        "no network client",
        "not packaged",
    ):
        assert required_text in row


def test_pipeline_operations_audit_documents_read_only_report_prediction() -> None:
    row = _audit_row("src/modori/ui/pipeline_ops.py")

    for required_text in (
        "Read-only report-destination write preflight",
        "trusted pipeline's `output_dir`",
        "validated filename",
        "containment",
        "collision",
        "during an explicitly approved replacement",
        "unexpected exporter path",
        "does not create, write, replace, or delete",
        "actual export",
    ):
        assert required_text in row


def test_live_research_os_office_tools_document_their_closed_file_boundaries() -> None:
    contract = _audit_row("scripts/live_research_os_office_benchmark.py")
    kit_contract = _audit_row("scripts/live_research_os_office_kit.py")
    builder = _audit_row("scripts/build_office_live_research_os_kit.py")
    runner = _audit_row("scripts/run_office_live_research_os_benchmark.py")
    verifier = _audit_row("scripts/verify_office_live_research_os_kit.py")

    for row in (contract, kit_contract):
        for required_text in (
            "scanner false positive",
            "no filesystem mutation",
            "not packaged in the shipping app",
        ):
            assert required_text in row
    for required_text in (
        "Developer-only",
        "clean committed HEAD",
        "`dist/live-research-os-office`",
        "exclusive creation",
        "UUID-named staging",
        "no user files",
        "no network",
    ):
        assert required_text in builder
    for required_text in (
        "Offline",
        "synthetic fixture",
        "sibling `<extraction-parent>/w`",
        "`q/<nonce>`",
        "marked ownership",
        "240 UTF-16 code units",
        "dynamic path preflight",
        "only `results` inside the kit",
        "marked child roots",
        "exact ancestry",
        "atomically",
        "no caller-selected path",
        "no registry",
        "no user dataset or document",
        "no network",
    ):
        assert required_text in runner
    for required_text in (
        "Read-only inputs",
        "`TemporaryDirectory`",
        "no-follow",
        "traversal",
        "fixed identity arguments",
        "runtime identity probe",
        "outside the supplied kit",
        "does not modify the supplied ZIP or extracted root",
    ):
        assert required_text in verifier


def test_live_research_os_persistence_exposes_no_broad_file_authority() -> None:
    assert _public_methods(
        "src/modori/research_memory/task_index.py", "ResearchTaskIndex"
    ) == {
        "allocate",
        "close",
        "get",
        "locate_active",
        "mark_readonly",
        "open_existing",
        "open_or_create",
        "verify",
    }
    assert _public_methods(
        "src/modori/research_flow/task_session.py", "ResearchTaskSessionStore"
    ) == {"locate_existing", "open_or_allocate", "start_replan"}

    forbidden_import_roots = {
        "ctypes",
        "http",
        "importlib",
        "multiprocessing",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    violations: list[str] = []
    for file_path in (
        "src/modori/research_flow/task_session.py",
        "src/modori/research_memory/ledger_store.py",
        "src/modori/research_memory/task_index.py",
    ):
        tree = ast.parse(Path(file_path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0]}
            else:
                continue
            for name in sorted(imported & forbidden_import_roots):
                violations.append(f"{file_path}:{name}")
    assert violations == []


def test_research_task_index_audit_documents_the_fixed_fail_closed_boundary() -> None:
    row = _audit_row("src/modori/research_memory/task_index.py")

    for required_text in (
        "%LOCALAPPDATA%\\Modori\\research-task-index.sqlite3",
        "closed identifiers",
        "SHA-256 dataset fingerprint",
        "before and after parent creation",
        "UNC and mapped remote drives",
        "symlink/junction/reparse",
        "`BEGIN IMMEDIATE`",
        "five-second busy timeout",
        "typed conflict, unavailable, integrity, path, and runtime errors",
        "fails closed",
        "no caller-selected path",
        "no import",
        "no delete",
        "no bundle",
        "10,000-row",
        "task deletion and secure erasure are unavailable",
    ):
        assert required_text in row


def test_decision_ledger_audit_documents_live_per_task_path_derivation() -> None:
    row = _audit_row("src/modori/research_memory/ledger_store.py")

    for required_text in (
        "closed local project ID",
        "SHA-256-derived project directory",
        "%LOCALAPPDATA%\\Modori\\projects",
        "decision-ledger.sqlite3",
        "live Research OS flow never accepts a caller-selected ledger path",
        "UNC and mapped remote drives",
        "symlink/junction/reparse",
    ):
        assert required_text in row


def test_visual_evidence_file_operations_are_developer_only_and_package_excluded() -> (
    None
):
    capture = _audit_row("scripts/capture_research_flow_gallery.py")
    packet = _audit_row("scripts/build_research_flow_visual_review_packet.py")

    for required_text in (
        "Developer-only",
        "not packaged",
        "synthetic",
        "clean committed source",
        "caller-selected empty output",
        "application-content-only",
        "no user data",
        "no network",
        "transient `.capture-<item-id>.json`",
    ):
        assert required_text in capture
    for required_text in (
        "Developer-only",
        "not packaged",
        "digest-bound",
        "caller-selected empty output",
        "re-encodes",
        "text metadata",
        "no source code, local paths, or user data",
        "no network",
        "never deletes or overwrites",
    ):
        assert required_text in packet


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


def test_package_engine_audit_documents_installed_cache_proof() -> None:
    row = next(
        line
        for line in AUDIT_DOCUMENT.read_text(encoding="utf-8").splitlines()
        if "`scripts/package_engine_smoke.py`" in line
    )

    for required_text in (
        "reported cache path",
        "`MODORI_CACHE_DIR`",
        "real directory",
        "link/junction",
    ):
        assert required_text in row


def test_package_environment_audit_documents_lexical_state_boundary() -> None:
    row = next(
        line
        for line in AUDIT_DOCUMENT.read_text(encoding="utf-8").splitlines()
        if "`scripts/package_environment.py`" in line
    )

    for required_text in (
        "absolute lexical",
        "component-by-component",
        "`lstat`",
        "symlink/junction/reparse",
        "lifecycle creates",
        "runtime children",
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
        ".tmp/ib/<commit12>-<uuid12>",
        "compiler source",
        "240",
        "component-by-component",
        "without following links",
        "after package-build return",
        "immediately before snapshot creation",
        "UTF-16 code units",
        "files, directories, and directory search wildcards",
    ):
        assert required_text in row
