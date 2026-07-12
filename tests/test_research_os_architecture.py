from __future__ import annotations

import ast
import inspect
from pathlib import Path

from modori.recommendations import RecommendationService
from modori.research_os.service import ResearchOsService, ResearchRequest


RESEARCH_OS_ROOT = Path("src/modori/research_os")


def _python_trees() -> tuple[tuple[Path, ast.AST], ...]:
    return tuple(
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(RESEARCH_OS_ROOT.glob("*.py"))
    )


def _import_roots() -> set[str]:
    roots: set[str] = set()
    for _, tree in _python_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


def test_research_os_has_no_network_tool_or_calculation_imports() -> None:
    forbidden = {
        "PySide6",
        "httpx",
        "joblib",
        "numpy",
        "pandas",
        "pickle",
        "requests",
        "scipy",
        "sklearn",
        "socket",
        "statsmodels",
        "subprocess",
        "urllib",
    }

    assert _import_roots().isdisjoint(forbidden)


def test_research_os_production_code_has_no_io_or_dynamic_execution_call() -> None:
    forbidden_names = {"compile", "eval", "exec", "open", "__import__"}
    forbidden_attributes = {
        "open",
        "read_bytes",
        "read_text",
        "write_bytes",
        "write_text",
    }
    violations: list[str] = []
    for path, tree in _python_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_names:
                violations.append(f"{path}:{node.lineno}:{node.func.id}")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in forbidden_attributes
            ):
                violations.append(f"{path}:{node.lineno}:{node.func.attr}")

    assert violations == []


def test_structure_only_request_has_no_dataset_or_execution_field() -> None:
    field_names = tuple(ResearchRequest.__dataclass_fields__)

    assert "dataset" not in field_names
    assert "dataframe" not in field_names
    assert "command" not in field_names
    assert "execution" not in field_names
    assert field_names == (
        "question",
        "estimand",
        "study",
        "current_dataset_fingerprint",
        "available_variable_ids",
        "surface",
        "question_budget_remaining",
    )


def test_research_os_public_service_cannot_run_or_persist() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(ResearchOsService)
        if callable(member) and not name.startswith("_")
    }

    assert public_methods == {"resolve"}


def test_existing_recommendation_service_signature_is_unchanged() -> None:
    parameters = inspect.signature(RecommendationService.recommend).parameters

    assert tuple(parameters) == ("self", "dataset", "active_analysis")
    assert parameters["active_analysis"].kind is inspect.Parameter.KEYWORD_ONLY
