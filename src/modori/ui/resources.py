from __future__ import annotations

from pathlib import Path


def ui_package_dir() -> Path:
    return Path(__file__).resolve().parent


def root_qml_path() -> Path:
    path = ui_package_dir() / "qml" / "Main.qml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Modori QML root: {path}")
    return path
