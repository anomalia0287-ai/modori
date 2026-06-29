from __future__ import annotations

from pathlib import Path


def is_link_or_junction(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        return path.is_symlink() or bool(is_junction and is_junction())
    except OSError:
        return True


def resolve_secure_directory_path(candidate: str | Path) -> Path | None:
    path = Path(candidate).expanduser()
    if not path.is_absolute() or _has_symlink_in_existing_path(path):
        return None
    resolved = path.resolve(strict=False)
    try:
        if resolved.exists() and not resolved.is_dir():
            return None
    except OSError:
        return None
    return resolved


def resolve_secure_file_path(candidate: str | Path, *, suffix: str) -> Path | None:
    path = Path(candidate).expanduser()
    if not path.is_absolute() or path.suffix.lower() != suffix.lower():
        return None
    if _has_symlink_in_existing_path(path.parent):
        return None
    try:
        if path.exists() and is_link_or_junction(path):
            return None
        resolved = path.resolve(strict=False)
        if resolved.exists() and (resolved.is_symlink() or not resolved.is_file()):
            return None
    except OSError:
        return None
    return resolved


def _has_symlink_in_existing_path(path: Path) -> bool:
    current = path
    try:
        while not current.exists():
            parent = current.parent
            if parent == current:
                return False
            current = parent

        while True:
            if is_link_or_junction(current):
                return True
            parent = current.parent
            if parent == current:
                return False
            current = parent
    except OSError:
        return True
