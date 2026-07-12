from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

PRODUCTION_APP_ID = "{430f4cea-53ca-4578-800c-f7ce1b6aead2}"
SMOKE_APP_ID = "{97d13afd-818d-40c5-80ee-ce53eea57c0c}"
DOWNGRADE_PROBE_VERSION = "0.0.9"
ASSUMED_INSTALL_ROOT_CHARS = 90
SAFE_PATH_BUDGET_CHARS = 240
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class SourceIdentity:
    version: str
    windows_file_version: str
    git_commit: str
    git_dirty: bool
    build_identity: str


@dataclass(frozen=True)
class FileEvidence:
    path: str
    size_bytes: int
    sha256: str

    @classmethod
    def from_path(cls, display_path: str, source: Path) -> "FileEvidence":
        size = source.stat().st_size
        if size <= 0:
            raise ValueError(f"Evidence file is empty: {source}")
        return cls(path=display_path, size_bytes=size, sha256=sha256_file(source))


@dataclass(frozen=True)
class PayloadPathEvidence:
    file_count: int
    longest_relative_path: str
    longest_relative_path_chars: int
    assumed_install_root_chars: int
    safe_path_budget_chars: int
    computed_max_chars: int


def read_project_version(path: Path) -> str:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    version = str(payload["project"]["version"])
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("Installer version must have exactly three numeric components")
    return version


def make_source_identity(version: str, git_commit: str, *, dirty: bool) -> SourceIdentity:
    if not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("Installer version must have exactly three numeric components")
    commit = git_commit.casefold()
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("Git commit must be 40 lowercase hexadecimal characters")
    return SourceIdentity(
        version=version,
        windows_file_version=f"{version}.0",
        git_commit=commit,
        git_dirty=dirty,
        build_identity=f"{version}-g{commit[:12]}",
    )


def measure_payload_paths(root: Path) -> PayloadPathEvidence:
    if not root.is_dir():
        raise ValueError(f"Package root does not exist: {root}")
    relatives = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    if not relatives:
        raise ValueError(f"Package root contains no files: {root}")
    longest = max(relatives, key=lambda value: (len(value), value))
    computed = ASSUMED_INSTALL_ROOT_CHARS + 1 + len(longest)
    if computed > SAFE_PATH_BUDGET_CHARS:
        raise ValueError(
            f"Package path budget exceeded: {computed} > {SAFE_PATH_BUDGET_CHARS}: {longest}"
        )
    return PayloadPathEvidence(
        file_count=len(relatives),
        longest_relative_path=longest,
        longest_relative_path_chars=len(longest),
        assumed_install_root_chars=ASSUMED_INSTALL_ROOT_CHARS,
        safe_path_budget_chars=SAFE_PATH_BUDGET_CHARS,
        computed_max_chars=computed,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_manifest(
    *,
    identity: SourceIdentity,
    app_id: str,
    channel: str,
    smoke_only: bool,
    tools: Mapping[str, str],
    package_executable: FileEvidence,
    installer: FileEvidence,
    installer_script: FileEvidence,
    payload_paths: PayloadPathEvidence,
    installed_lifecycle_smoke: bool,
    installed_lifecycle_app_id: str | None,
    built_at: str,
    downgrade_probe: FileEvidence | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "product": "Modori",
        "channel": channel,
        "app_id": app_id,
        "smoke_only": smoke_only,
        "signed": False,
        "version": identity.version,
        "windows_file_version": identity.windows_file_version,
        "git_commit": identity.git_commit,
        "git_dirty": identity.git_dirty,
        "built_at": built_at,
        "tools": dict(tools),
        "package_executable": asdict(package_executable),
        "installer_script": asdict(installer_script),
        "payload_paths": asdict(payload_paths),
        "installer": {
            "filename": Path(installer.path).name,
            "size_bytes": installer.size_bytes,
            "sha256": installer.sha256,
        },
        "verification": {
            "package_launch_smoke": True,
            "package_engine_smoke": True,
            "package_public_data_smoke": True,
            "installed_lifecycle_smoke": installed_lifecycle_smoke,
            "installed_lifecycle_app_id": installed_lifecycle_app_id,
        },
    }
    if downgrade_probe is not None:
        payload["downgrade_probe"] = {
            "version": DOWNGRADE_PROBE_VERSION,
            "filename": Path(downgrade_probe.path).name,
            "size_bytes": downgrade_probe.size_bytes,
            "sha256": downgrade_probe.sha256,
        }
    return payload


def write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_checksum_file(path: Path, installer: FileEvidence) -> None:
    path.write_text(f"{installer.sha256}  {Path(installer.path).name}\n", encoding="utf-8")
