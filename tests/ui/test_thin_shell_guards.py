import ast
from pathlib import Path


def iter_python_sources() -> list[Path]:
    return sorted(Path("src/modori/ui").glob("**/*.py"))


def test_ui_layer_has_no_forbidden_statistics_imports() -> None:
    from modori.ui.security import FORBIDDEN_STATISTICS_IMPORTS

    violations: list[str] = []
    for path in iter_python_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_STATISTICS_IMPORTS:
                        violations.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_STATISTICS_IMPORTS:
                    violations.append(f"{path}:{node.module}")

    assert violations == []


def test_ui_layer_has_no_forbidden_reduction_calls() -> None:
    from modori.ui.security import FORBIDDEN_REDUCTION_CALLS

    violations: list[str] = []
    for path in iter_python_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_REDUCTION_CALLS:
                    violations.append(f"{path}:{node.func.attr}")

    assert violations == []
