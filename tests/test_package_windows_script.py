from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from scripts import package_windows
from scripts.package_environment import (
    packaged_subprocess_environment,
    without_workspace_reference_runtime,
)
from scripts.package_windows import build_package_environment, build_pyinstaller_command


def test_package_script_reports_missing_packager_cleanly(monkeypatch, capsys) -> None:
    monkeypatch.setattr(package_windows, "pyinstaller_available", lambda: False)

    result = package_windows.main(["--check"])

    captured = capsys.readouterr()
    assert result == 2
    assert "PyInstaller is not installed" in captured.err


def test_pyinstaller_command_collects_qml_and_pyside6() -> None:
    command = build_pyinstaller_command()

    assert "--name" in command
    assert "Modori" in command
    assert "--windowed" in command
    assert "--collect-all" not in command
    for module in [
        "matplotlib.backends.backend_agg",
        "matplotlib.backends.backend_ps",
        "matplotlib.backends.backend_svg",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
    ]:
        assert "--hidden-import" in command
        assert module in command
    assert "--add-data" in command
    assert "src/modori/ui/qml;modori/ui/qml" in command
    assert "library/entries;library/entries" in command
    assert "src/modori/app.py" in command


def test_pyproject_declares_packaging_extra() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    packaging = pyproject["project"]["optional-dependencies"]["packaging"]

    assert any(requirement.startswith("pyinstaller>=") for requirement in packaging)


def test_package_environment_uses_workspace_writable_matplotlib_cache() -> None:
    env = build_package_environment()

    assert env["MPLCONFIGDIR"].endswith(".tmp\\pyinstaller-matplotlib")
    assert env["MODORI_CACHE_DIR"].endswith(".tmp\\pyinstaller-modori-cache")


def test_package_environment_pins_release_workspace_source_first(
    monkeypatch,
) -> None:
    foreign_source = str(
        (Path(".worktrees") / "recommendation-benchmark-pilot" / "src").resolve()
    )
    monkeypatch.setenv("PYTHONPATH", foreign_source)

    env = build_package_environment()

    python_paths = env["PYTHONPATH"].split(os.pathsep)
    assert Path(python_paths[0]) == (Path("src").resolve())
    assert foreign_source in python_paths[1:]


def test_package_environment_removes_workspace_r_runtime_dll_paths(
    tmp_path,
    monkeypatch,
) -> None:
    r_root = tmp_path / ".tools" / "r-env"
    rscript = r_root / "Scripts" / "Rscript.exe"
    rscript.parent.mkdir(parents=True)
    rscript.write_text("", encoding="utf-8")
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(rscript))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))

    env = build_package_environment()

    assert "MODORI_RSCRIPT" not in env
    assert str(r_root).casefold() not in env["PATH"].casefold()
    assert "C:\\Windows" in env["PATH"]


def test_runtime_cleanup_does_not_infer_a_root_from_bare_rscript_name() -> None:
    workspace_tool = str((Path("tools") / "bin").resolve())
    original_path = os.pathsep.join([workspace_tool, "C:\\Windows"])

    env = without_workspace_reference_runtime(
        {
            "MODORI_RSCRIPT": "Rscript.exe",
            "PATH": original_path,
        }
    )

    assert "MODORI_RSCRIPT" not in env
    assert env["PATH"] == original_path


def test_package_environment_removes_mixed_workspace_r_library_values(tmp_path) -> None:
    r_library = tmp_path / ".tools" / "r-env" / "Library"
    source = {
        "PATH": "C:\\Windows",
        "R_LIBS": os.pathsep.join([str(r_library), "C:\\R-libs"]),
    }

    env = without_workspace_reference_runtime(source)

    assert "R_LIBS" not in env


@pytest.mark.parametrize("namespace", [".", "..", "nested/name", "C:\\absolute"])
def test_packaged_subprocess_environment_rejects_escaping_namespaces(
    namespace: str,
) -> None:
    with pytest.raises(ValueError, match="one safe path segment"):
        packaged_subprocess_environment(namespace)


@pytest.mark.parametrize(
    "script",
    [
        "scripts/package_windows.py",
        "scripts/package_engine_smoke.py",
        "scripts/package_public_data_smoke.py",
        "scripts/quality_gate.py",
    ],
)
def test_package_script_entrypoints_resolve_local_environment_helper(
    script: str,
) -> None:
    completed = subprocess.run(
        [sys.executable, script, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
