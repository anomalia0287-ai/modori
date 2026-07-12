from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import stat

from modori.path_policy import resolve_secure_directory_path


_R_ENVIRONMENT_KEYS = ("R_HOME", "R_LIBS", "R_LIBS_USER")
_REPARSE_POINT_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_reparse_point(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT_ATTRIBUTE
    )


def _require_safe_lexical_state_components(state_root: Path) -> None:
    component = Path(state_root.anchor)
    components = [component]
    for part in state_root.parts[1:]:
        component /= part
        components.append(component)

    for component in components:
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ValueError(
                f"Package state-root component could not be inspected: {component}"
            ) from exc
        if _is_reparse_point(metadata):
            raise ValueError(
                "Package state root contains a link or junction/reparse point: "
                f"{component}"
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(
                f"Package state-root component is not a directory: {component}"
            )


def _validated_explicit_state_root(state_root: str | Path) -> Path:
    supplied = Path(state_root)
    if not supplied.is_absolute():
        raise ValueError("Explicit package state root must be an absolute lexical path")
    lexical_root = Path(os.path.abspath(supplied))
    _require_safe_lexical_state_components(lexical_root)
    resolved_root = resolve_secure_directory_path(lexical_root)
    if resolved_root is None:
        raise ValueError(f"Explicit package state root is unsafe: {lexical_root}")
    _require_safe_lexical_state_components(lexical_root)
    return resolved_root


def without_workspace_reference_runtime(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if source is None else source)
    rscript = env.pop("MODORI_RSCRIPT", None)
    r_root = _r_root(rscript)
    path_entries = [entry for entry in env.get("PATH", "").split(os.pathsep) if entry]
    env["PATH"] = os.pathsep.join(
        entry
        for entry in path_entries
        if not _belongs_to_reference_runtime(entry, r_root)
    )
    for key in _R_ENVIRONMENT_KEYS:
        value = env.get(key)
        if value and any(
            _belongs_to_reference_runtime(entry, r_root)
            for entry in value.split(os.pathsep)
            if entry
        ):
            env.pop(key, None)
    return env


def packaged_subprocess_environment(
    namespace: str,
    *,
    state_root: str | Path | None = None,
) -> dict[str, str]:
    namespace_path = Path(namespace)
    if (
        not namespace
        or namespace in {".", ".."}
        or namespace_path.is_absolute()
        or len(namespace_path.parts) != 1
        or namespace_path.name != namespace
    ):
        raise ValueError("Package runtime namespace must be one safe path segment")
    env = without_workspace_reference_runtime()
    root = (
        (Path(".tmp") / namespace).resolve()
        if state_root is None
        else _validated_explicit_state_root(state_root)
    )
    matplotlib_dir = root / "matplotlib"
    cache_dir = root / "cache"
    if state_root is None:
        matplotlib_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
    env["MPLCONFIGDIR"] = str(matplotlib_dir)
    env["MODORI_CACHE_DIR"] = str(cache_dir)
    env["MODORI_SETTINGS_PATH"] = str(root / "settings.json")
    env["QT_QPA_PLATFORM"] = "offscreen"
    return env


def _r_root(rscript: str | None) -> Path | None:
    if not rscript:
        return None
    unresolved_path = Path(rscript).expanduser()
    if unresolved_path.parent == Path():
        return None
    path = unresolved_path.resolve()
    return path.parents[1] if len(path.parents) >= 2 else None


def _belongs_to_reference_runtime(value: str, r_root: Path | None) -> bool:
    path = Path(value).expanduser().resolve()
    if r_root is not None and (path == r_root or r_root in path.parents):
        return True
    parts = [part.casefold() for part in path.parts]
    return any(
        parts[index] == ".tools" and parts[index + 1] == "r-env"
        for index in range(len(parts) - 1)
    )
