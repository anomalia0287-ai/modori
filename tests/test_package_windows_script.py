from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

from scripts.package_windows import build_pyinstaller_command


def test_package_script_reports_missing_packager_cleanly() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/package_windows.py", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "PyInstaller is not installed" in result.stderr


def test_pyinstaller_command_collects_qml_and_pyside6() -> None:
    command = build_pyinstaller_command()

    assert "--name" in command
    assert "Modori" in command
    assert "--windowed" in command
    assert "--collect-all" in command
    assert "PySide6" in command
    assert "--add-data" in command
    assert "src/modori/ui/qml;modori/ui/qml" in command
    assert "src/modori/app.py" in command


def test_pyproject_declares_packaging_extra() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    packaging = pyproject["project"]["optional-dependencies"]["packaging"]

    assert any(requirement.startswith("pyinstaller>=") for requirement in packaging)
