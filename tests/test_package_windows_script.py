from __future__ import annotations

import tomllib
from pathlib import Path

from scripts import package_windows
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
    assert "src/modori/app.py" in command


def test_pyproject_declares_packaging_extra() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    packaging = pyproject["project"]["optional-dependencies"]["packaging"]

    assert any(requirement.startswith("pyinstaller>=") for requirement in packaging)


def test_package_environment_uses_workspace_writable_matplotlib_cache() -> None:
    env = build_package_environment()

    assert env["MPLCONFIGDIR"].endswith(".tmp\\pyinstaller-matplotlib")
    assert env["MODORI_CACHE_DIR"].endswith(".tmp\\pyinstaller-modori-cache")
