from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from modori.path_policy import is_link_or_junction, resolve_secure_directory_path


def _default_cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        appdata = resolve_secure_directory_path(base)
        if appdata is not None:
            return appdata / "Modori" / "cache"
    home = resolve_secure_directory_path(Path.home())
    if home is not None:
        return home / ".modori" / "cache"
    return Path.cwd().resolve(strict=False) / ".modori_cache" / "fallback"


def _last_resort_cache_dir() -> Path:
    temp_root = resolve_secure_directory_path(tempfile.gettempdir())
    if temp_root is not None:
        return temp_root / "modori-cache"
    return Path.cwd().resolve(strict=False) / ".modori_cache" / "fallback"


def _ensure_cache_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if is_link_or_junction(path) or not path.is_dir():
        raise OSError(f"Configured cache path is not a directory: {path}")
    probe = path / f".modori-write-test-{uuid.uuid4().hex}.tmp"
    try:
        probe.write_text("", encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Configured cache path is not writable: {path}") from exc
    finally:
        try:
            probe.unlink()
        except OSError:
            pass
    return path


def cache_dir() -> Path:
    configured = os.environ.get("MODORI_CACHE_DIR")
    configured_path = resolve_secure_directory_path(configured) if configured else None
    candidates = [path for path in (configured_path, _default_cache_dir(), _last_resort_cache_dir()) if path]

    for path in candidates:
        try:
            return _ensure_cache_dir(path)
        except OSError:
            continue
    return _ensure_cache_dir(Path.cwd().resolve(strict=False) / ".modori_cache" / "fallback")


def matplotlib_cache_dir() -> Path:
    configured = os.environ.get("MPLCONFIGDIR")
    configured_path = resolve_secure_directory_path(configured) if configured else None
    if configured_path is not None:
        try:
            return _ensure_cache_dir(configured_path)
        except OSError:
            pass

    path = cache_dir() / "matplotlib"
    try:
        return _ensure_cache_dir(path)
    except OSError:
        return cache_dir()
