from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl


def local_path_from_qml(path: str) -> Path:
    text = str(path)
    if text.startswith("file:"):
        return Path(QUrl(text).toLocalFile())
    return Path(text)
