from __future__ import annotations

import ast
import inspect
from pathlib import Path
import sys

from modori.research_memory.ledger_contracts import ImportedAssertion
from modori.research_memory.ledger_store import DecisionLedgerStore
from modori.research_memory.promotion import ResearchMemoryCoordinator
from modori.research_memory.quarantine import QuarantineResult


RESEARCH_MEMORY_ROOT = Path("src/modori/research_memory")
RESEARCH_OS_ROOT = Path("src/modori/research_os")
RESEARCH_FLOW_ROOT = Path("src/modori/research_flow")
PROHIBITED_IMPORT_PREFIXES = (
    "modori.steps",
    "modori.workflow",
    "modori.ui",
    "modori.importers",
    "PySide6",
    "requests",
    "urllib",
    "socket",
    "subprocess",
    "zipfile",
    "tarfile",
    "pickle",
)


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return tuple(names)


def test_dependency_direction_keeps_research_os_pure() -> None:
    for path in RESEARCH_OS_ROOT.glob("*.py"):
        assert all(
            not name.startswith(("modori.research_memory", "modori.research_flow"))
            for name in _imports(path)
        ), path


def test_research_flow_never_imports_the_ui_layer() -> None:
    for path in RESEARCH_FLOW_ROOT.glob("*.py"):
        assert all(not name.startswith("modori.ui") for name in _imports(path)), path


def test_research_flow_pure_contract_boundaries_have_no_persistence_imports() -> None:
    for name in ("contracts.py", "fingerprint.py"):
        path = RESEARCH_FLOW_ROOT / name
        if not path.exists():
            continue
        imports = _imports(path)
        assert "sqlite3" not in imports, path
        assert all(
            not imported.startswith(("modori.path_policy", "modori.research_memory"))
            for imported in imports
        ), path


def test_research_memory_uses_stdlib_and_pure_modori_contracts_only() -> None:
    for path in RESEARCH_MEMORY_ROOT.glob("*.py"):
        for name in _imports(path):
            root = name.split(".", 1)[0]
            assert root in sys.stdlib_module_names or root == "modori", (path, name)
            assert not name.startswith(PROHIBITED_IMPORT_PREFIXES), (path, name)


def test_only_ledger_store_imports_sqlite_or_path_policy() -> None:
    for path in RESEARCH_MEMORY_ROOT.glob("*.py"):
        names = _imports(path)
        if path.name == "ledger_store.py":
            assert "sqlite3" in names
            assert "modori.path_policy" in names
        else:
            assert "sqlite3" not in names
            assert "modori.path_policy" not in names


def test_quarantine_has_no_file_calls_or_authority_bearing_result_fields() -> None:
    path = RESEARCH_MEMORY_ROOT / "quarantine.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert calls.isdisjoint({"open", "eval", "exec", "compile"})
    assert attributes.isdisjoint(
        {
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "unlink",
            "remove",
            "execute",
            "run",
        }
    )
    forbidden_fields = {
        "research_request",
        "pipeline",
        "path",
        "url",
        "command",
        "execution_token",
    }
    assert forbidden_fields.isdisjoint(QuarantineResult.__annotations__)
    assert forbidden_fields.isdisjoint(ImportedAssertion.__annotations__)


def test_public_memory_api_has_no_delete_clear_execute_or_pipeline_authority() -> None:
    forbidden = {"delete", "clear", "remove", "unlink", "execute", "run", "pipeline"}
    store_methods = {
        name
        for name, value in inspect.getmembers(DecisionLedgerStore, inspect.isfunction)
        if not name.startswith("_")
    }
    coordinator_methods = {
        name
        for name, value in inspect.getmembers(
            ResearchMemoryCoordinator,
            inspect.isfunction,
        )
        if not name.startswith("_")
    }
    assert store_methods.isdisjoint(forbidden)
    assert coordinator_methods.isdisjoint(forbidden)


def test_no_trusted_project_bypass_is_introduced() -> None:
    for root in (Path("src"), RESEARCH_MEMORY_ROOT):
        for path in root.rglob("*.py"):
            assert "trust_project_file=True" not in path.read_text(encoding="utf-8")
