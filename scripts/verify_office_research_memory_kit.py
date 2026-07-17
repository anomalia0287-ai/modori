"""Read-only verifier for an extracted portable office benchmark kit."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType

from scripts.office_research_memory_kit import (
    RUNTIME_SPEC,
    KitContractError,
    ManifestEntry,
    canonical_json_bytes,
    parse_manifest,
)


_BOOTSTRAP_FILES = frozenset(
    {
        "MANIFEST.json",
        "RUN-MODORI-BENCHMARK.cmd",
        "VERIFY-AND-RUN.ps1",
    }
)
_MUTABLE_ROOTS = frozenset({"results", "work"})
_IDENTITY_FIELDS = frozenset(
    {
        "builder_version",
        "runtime",
        "schema_id",
        "schema_version",
        "source_commit",
        "source_date_epoch",
    }
)
_RUNTIME_IDENTITY_FIELDS = frozenset(
    {"archive_sha256", "sqlite_version", "url", "version"}
)
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class KitVerificationError(RuntimeError):
    """Raised when an extracted kit cannot prove its immutable inventory."""


@dataclass(frozen=True)
class VerifiedKit:
    root: Path
    identity: Mapping[str, object]
    entries: tuple[ManifestEntry, ...]


def _is_link_or_junction(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        return path.is_symlink() or bool(is_junction and is_junction())
    except OSError:
        return True


def _require_plain_directory(path: Path, field: str) -> None:
    try:
        if _is_link_or_junction(path):
            raise KitVerificationError(f"{field} must not be a link or junction")
        if not path.is_dir():
            raise KitVerificationError(f"{field} directory is missing")
    except OSError as exc:
        raise KitVerificationError(f"{field} directory cannot be inspected") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise KitVerificationError("manifested file cannot be read") from exc
    return digest.hexdigest()


def _safe_member(root: Path, relative: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if _is_link_or_junction(path):
            raise KitVerificationError("kit inventory contains a link or junction")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise KitVerificationError("manifested file is missing") from exc
    if not resolved.is_relative_to(root):
        raise KitVerificationError("manifested path escapes the kit root")
    if not resolved.is_file():
        raise KitVerificationError("manifested path is not a regular file")
    return resolved


def _walk_immutable(root: Path) -> tuple[str, ...]:
    found: list[str] = []
    stack = [root]
    while stack:
        parent = stack.pop()
        try:
            entries = tuple(os.scandir(parent))
        except OSError as exc:
            raise KitVerificationError("kit inventory cannot be enumerated") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if relative.split("/", 1)[0] in _MUTABLE_ROOTS:
                continue
            if entry.is_symlink() or _is_link_or_junction(path):
                raise KitVerificationError("kit inventory contains a link or junction")
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    found.append(relative)
                else:
                    raise KitVerificationError(
                        "kit inventory contains a special file"
                    )
            except OSError as exc:
                raise KitVerificationError("kit inventory entry cannot be read") from exc
    return tuple(sorted(found))


class _DuplicateKey(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _read_identity(path: Path) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise KitVerificationError("kit identity cannot be read") from exc
    if len(raw) > 64 * 1024 or raw.startswith(b"\xef\xbb\xbf"):
        raise KitVerificationError("kit identity bytes are invalid")
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_hook)
    except (_DuplicateKey, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KitVerificationError("kit identity is not strict JSON") from exc
    try:
        canonical = canonical_json_bytes(parsed)
    except KitContractError as exc:
        raise KitVerificationError("kit identity is outside the canonical profile") from exc
    if canonical != raw:
        raise KitVerificationError("kit identity is not canonical")
    if not isinstance(parsed, dict) or set(parsed) != _IDENTITY_FIELDS:
        raise KitVerificationError("kit identity fields are invalid")
    if (
        parsed["schema_id"] != "modori.office_benchmark_kit_identity"
        or parsed["schema_version"] != 1
        or parsed["builder_version"] != 1
    ):
        raise KitVerificationError("kit identity schema is unsupported")
    if not isinstance(parsed["source_commit"], str) or not _COMMIT_RE.fullmatch(
        parsed["source_commit"]
    ):
        raise KitVerificationError("kit source commit is invalid")
    if (
        type(parsed["source_date_epoch"]) is not int
        or parsed["source_date_epoch"] < 315_532_800
    ):
        raise KitVerificationError("kit source date is invalid")
    runtime = parsed["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != _RUNTIME_IDENTITY_FIELDS:
        raise KitVerificationError("kit runtime identity fields are invalid")
    expected_runtime = {
        "archive_sha256": RUNTIME_SPEC.sha256,
        "sqlite_version": RUNTIME_SPEC.sqlite_version,
        "url": RUNTIME_SPEC.url,
        "version": RUNTIME_SPEC.version,
    }
    if runtime != expected_runtime:
        raise KitVerificationError("kit runtime identity does not match the pin")
    return MappingProxyType(parsed)


def verify_kit(root: Path) -> VerifiedKit:
    """Verify an extracted kit without importing or executing its payload."""

    if not isinstance(root, Path):
        raise KitVerificationError("kit root must be a Path")
    candidate = root.absolute()
    _require_plain_directory(candidate, "kit root")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise KitVerificationError("kit root cannot be resolved") from exc
    for mutable in sorted(_MUTABLE_ROOTS):
        _require_plain_directory(resolved / mutable, mutable)
    for bootstrap in sorted(_BOOTSTRAP_FILES):
        path = resolved / bootstrap
        if _is_link_or_junction(path):
            raise KitVerificationError("bootstrap file must not be a link")
        if not path.is_file():
            raise KitVerificationError("bootstrap file is missing")

    try:
        raw_manifest = (resolved / "MANIFEST.json").read_bytes()
        entries = parse_manifest(raw_manifest)
    except (OSError, KitContractError) as exc:
        raise KitVerificationError("kit manifest failed verification") from exc
    for entry in entries:
        path = _safe_member(resolved, entry.path)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise KitVerificationError("manifested file size cannot be read") from exc
        if size != entry.size_bytes:
            raise KitVerificationError("manifested file size does not verify")
        if sha256_file(path) != entry.sha256:
            raise KitVerificationError("manifested file digest does not verify")

    expected_inventory = tuple(
        sorted({entry.path for entry in entries} | _BOOTSTRAP_FILES)
    )
    if _walk_immutable(resolved) != expected_inventory:
        raise KitVerificationError("kit contains a missing or unexpected immutable file")
    runtime_inventory = {
        entry.path.removeprefix("runtime/")
        for entry in entries
        if entry.path.startswith("runtime/")
    }
    if runtime_inventory != set(RUNTIME_SPEC.expected_files):
        raise KitVerificationError("kit runtime inventory does not match the pin")
    identity_entry = next(
        (entry for entry in entries if entry.path == "KIT-IDENTITY.json"),
        None,
    )
    if identity_entry is None:
        raise KitVerificationError("kit identity is absent from the manifest")
    identity = _read_identity(resolved / identity_entry.path)
    return VerifiedKit(root=resolved, identity=identity, entries=entries)
