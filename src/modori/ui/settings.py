from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from modori.cache import cache_dir
from modori.path_policy import resolve_secure_file_path


DEFAULT_SETTINGS = {
    "explain_mode_enabled": True,
    "recent_files_enabled": True,
    "recent_files": [],
    "reduce_effects": False,
}


def _settings_path(configured: str | Path | None) -> Path:
    if configured is not None:
        resolved = resolve_secure_file_path(configured, suffix=".json")
        if resolved is not None:
            return resolved
    return (cache_dir() / "ui-settings.json").resolve(strict=False)


def _atomic_write_text(path: Path, text: str) -> None:
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


class UiSettingsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.environ.get("MODORI_SETTINGS_PATH")
        self.path = _settings_path(configured)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return dict(DEFAULT_SETTINGS)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return dict(DEFAULT_SETTINGS)
        if not isinstance(payload, dict):
            return dict(DEFAULT_SETTINGS)
        recent_files = payload.get("recent_files", [])
        if not isinstance(recent_files, list):
            recent_files = []
        return {
            "explain_mode_enabled": bool(payload.get("explain_mode_enabled", True)),
            "recent_files_enabled": bool(payload.get("recent_files_enabled", True)),
            "recent_files": [str(path) for path in recent_files if isinstance(path, str)],
            "reduce_effects": bool(payload.get("reduce_effects", False)),
        }

    def save(self, payload: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(
                self.path,
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            )
        except OSError:
            return
