from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def pyinstaller_available() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def build_pyinstaller_command() -> list[str]:
    qt_hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
    ]
    hidden_import_args = [
        item
        for module in qt_hidden_imports
        for item in ("--hidden-import", module)
    ]
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "Modori",
        "--windowed",
        *hidden_import_args,
        "--add-data",
        "src/modori/ui/qml;modori/ui/qml",
        "src/modori/app.py",
    ]


def build_package_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["MPLCONFIGDIR"] = str(Path(".tmp") / "pyinstaller-matplotlib")
    env["MODORI_CACHE_DIR"] = str(Path(".tmp") / "pyinstaller-modori-cache")
    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["MODORI_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    return env


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Windows Modori desktop package.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify that the packager is available.",
    )
    args = parser.parse_args(argv)

    if not pyinstaller_available():
        print(
            "PyInstaller is not installed. Install the packaging extra before building.",
            file=sys.stderr,
        )
        return 2
    if args.check:
        print("package-tool-ok")
        return 0

    command = build_pyinstaller_command()
    print("$ " + " ".join(command), flush=True)
    completed = subprocess.run(command, check=False, env=build_package_environment())
    if completed.returncode != 0:
        return completed.returncode

    exe_path = Path("dist") / "Modori" / "Modori.exe"
    if not exe_path.is_file():
        print(f"Expected packaged executable was not created: {exe_path}", file=sys.stderr)
        return 1
    print(exe_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
