from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def pyinstaller_available() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def build_pyinstaller_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "Modori",
        "--windowed",
        "--collect-all",
        "PySide6",
        "--add-data",
        "src/modori/ui/qml;modori/ui/qml",
        "src/modori/app.py",
    ]


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
    completed = subprocess.run(command, check=False)
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
