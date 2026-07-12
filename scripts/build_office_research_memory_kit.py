"""Deterministically build the sealed portable office benchmark kit."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
from types import MappingProxyType
import uuid
import zipfile


_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from scripts.office_research_memory_kit import (  # noqa: E402
    RUNTIME_SPEC,
    KitContractError,
    ManifestEntry,
    RuntimeSpec,
    canonical_json_bytes,
    manifest_bytes,
)


PAYLOAD_SOURCE_MAP = MappingProxyType(
    {
        "scripts/benchmark_research_memory.py": (
            "payload/scripts/benchmark_research_memory.py"
        ),
        "scripts/office_research_memory_kit.py": (
            "payload/scripts/office_research_memory_kit.py"
        ),
        "scripts/run_office_research_memory_benchmark.py": (
            "payload/scripts/run_office_research_memory_benchmark.py"
        ),
        "scripts/verify_office_research_memory_kit.py": (
            "payload/scripts/verify_office_research_memory_kit.py"
        ),
        "src/modori/__init__.py": "payload/src/modori/__init__.py",
        "src/modori/path_policy.py": "payload/src/modori/path_policy.py",
        "src/modori/research_memory/__init__.py": (
            "payload/src/modori/research_memory/__init__.py"
        ),
        "src/modori/research_memory/canonical.py": (
            "payload/src/modori/research_memory/canonical.py"
        ),
        "src/modori/research_memory/evidence_bundle.py": (
            "payload/src/modori/research_memory/evidence_bundle.py"
        ),
        "src/modori/research_memory/ledger_contracts.py": (
            "payload/src/modori/research_memory/ledger_contracts.py"
        ),
        "src/modori/research_memory/ledger_store.py": (
            "payload/src/modori/research_memory/ledger_store.py"
        ),
        "src/modori/research_memory/promotion.py": (
            "payload/src/modori/research_memory/promotion.py"
        ),
        "src/modori/research_memory/quarantine.py": (
            "payload/src/modori/research_memory/quarantine.py"
        ),
        "src/modori/research_os/__init__.py": (
            "payload/src/modori/research_os/__init__.py"
        ),
        "src/modori/research_os/clarification.py": (
            "payload/src/modori/research_os/clarification.py"
        ),
        "src/modori/research_os/contracts.py": (
            "payload/src/modori/research_os/contracts.py"
        ),
        "src/modori/research_os/decision_evidence.py": (
            "payload/src/modori/research_os/decision_evidence.py"
        ),
        "src/modori/research_os/method_space.py": (
            "payload/src/modori/research_os/method_space.py"
        ),
        "src/modori/research_os/p1_catalog.py": (
            "payload/src/modori/research_os/p1_catalog.py"
        ),
        "src/modori/research_os/p1_clarifications.py": (
            "payload/src/modori/research_os/p1_clarifications.py"
        ),
        "src/modori/research_os/passport.py": (
            "payload/src/modori/research_os/passport.py"
        ),
        "src/modori/research_os/resolver.py": (
            "payload/src/modori/research_os/resolver.py"
        ),
        "src/modori/research_os/service.py": (
            "payload/src/modori/research_os/service.py"
        ),
        "src/modori/research_os/transition.py": (
            "payload/src/modori/research_os/transition.py"
        ),
    }
)

TEMPLATE_SOURCE_FILES = MappingProxyType(
    {
        "cmd": "scripts/office_benchmark_kit/RUN-MODORI-BENCHMARK.cmd.in",
        "powershell": "scripts/office_benchmark_kit/VERIFY-AND-RUN.ps1.in",
        "readme": "scripts/office_benchmark_kit/README-KO.txt",
    }
)

_REQUIRED_SOURCE_FILES = frozenset(
    {*PAYLOAD_SOURCE_MAP, *TEMPLATE_SOURCE_FILES.values()}
)
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MAX_RUNTIME_BYTES = 256 * 1024 * 1024


class KitBuildError(RuntimeError):
    """Raised when the deterministic kit build cannot prove its inputs."""


@dataclass(frozen=True)
class SourceSnapshot:
    commit: str
    source_date_epoch: int
    files: Mapping[str, bytes]

    def __post_init__(self) -> None:
        if not _COMMIT_RE.fullmatch(self.commit):
            raise KitBuildError("source snapshot commit is invalid")
        if type(self.source_date_epoch) is not int or self.source_date_epoch < 315_532_800:
            raise KitBuildError("source snapshot timestamp is invalid")
        if not isinstance(self.files, Mapping):
            raise KitBuildError("source snapshot files must be a mapping")
        copied: dict[str, bytes] = {}
        for path, data in self.files.items():
            if not isinstance(path, str) or not isinstance(data, bytes):
                raise KitBuildError("source snapshot entries must be path-to-bytes")
            copied[path] = data
        object.__setattr__(self, "files", MappingProxyType(copied))


@dataclass(frozen=True)
class BuildRequest:
    output_dir: Path
    runtime_archive: Path
    runtime_spec: RuntimeSpec
    snapshot: SourceSnapshot
    validate_runtime: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.output_dir, Path) or not self.output_dir.is_absolute():
            raise KitBuildError("output directory must be an absolute Path")
        if not isinstance(self.runtime_archive, Path) or not self.runtime_archive.is_absolute():
            raise KitBuildError("runtime archive must be an absolute Path")
        if not isinstance(self.runtime_spec, RuntimeSpec):
            raise KitBuildError("runtime spec is invalid")
        if not isinstance(self.snapshot, SourceSnapshot):
            raise KitBuildError("source snapshot is invalid")
        if not isinstance(self.validate_runtime, bool):
            raise KitBuildError("validate_runtime must be boolean")


@dataclass(frozen=True)
class BuildResult:
    archive: Path
    digest_file: Path
    archive_sha256: str
    kit_name: str
    source_commit: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise KitBuildError("build input could not be read") from exc
    return digest.hexdigest()


def _is_link_or_junction(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        return path.is_symlink() or bool(is_junction and is_junction())
    except OSError:
        return True


def _write_new(path: Path, data: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise KitBuildError("build output already exists") from exc
    except OSError as exc:
        raise KitBuildError("build output could not be written") from exc


def _normalized_zip_member(name: str) -> str:
    candidate = PurePosixPath(name)
    if (
        not name
        or candidate.is_absolute()
        or candidate.as_posix() != name
        or "\\" in name
        or ":" in name
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise KitBuildError("runtime archive contains an unsafe path")
    return name


def _extract_runtime(
    archive_path: Path,
    destination: Path,
    runtime_spec: RuntimeSpec,
) -> None:
    if _sha256_file(archive_path) != runtime_spec.sha256:
        raise KitBuildError("runtime digest does not match the pin")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            normalized: list[str] = []
            total_size = 0
            for info in infos:
                name = _normalized_zip_member(info.filename)
                if info.is_dir() or info.flag_bits & 0x1:
                    raise KitBuildError("runtime archive contains an unsupported member")
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_IFMT(mode) == stat.S_IFLNK:
                    raise KitBuildError("runtime archive contains a link")
                total_size += info.file_size
                if total_size > _MAX_RUNTIME_BYTES:
                    raise KitBuildError("runtime archive exceeds its size limit")
                normalized.append(name)
            if len(set(normalized)) != len(normalized):
                raise KitBuildError("runtime archive contains duplicate members")
            if set(normalized) != set(runtime_spec.expected_files):
                raise KitBuildError("runtime archive inventory does not match the pin")
            for info in sorted(infos, key=lambda item: item.filename):
                target = destination / PurePosixPath(info.filename)
                _write_new(target, archive.read(info))
    except KitBuildError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise KitBuildError("runtime archive could not be safely extracted") from exc


def _validate_runtime_binary(runtime_root: Path, runtime_spec: RuntimeSpec) -> None:
    code = (
        "import json,sqlite3,sys;"
        "print(json.dumps({"
        "'defensive':hasattr(sqlite3,'SQLITE_DBCONFIG_DEFENSIVE'),"
        "'python':sys.version.split()[0],"
        "'setconfig':hasattr(sqlite3.Connection,'setconfig'),"
        "'sqlite':sqlite3.sqlite_version},sort_keys=True))"
    )
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [str(runtime_root / "python.exe"), "-I", "-c", code],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="strict",
            timeout=30,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise KitBuildError("pinned runtime could not execute") from exc
    if completed.returncode != 0 or completed.stderr.strip():
        raise KitBuildError("pinned runtime self-check failed")
    try:
        observed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise KitBuildError("pinned runtime self-check returned invalid JSON") from exc
    if observed != {
        "defensive": True,
        "python": runtime_spec.version,
        "setconfig": True,
        "sqlite": runtime_spec.sqlite_version,
    }:
        raise KitBuildError("pinned runtime capability set does not match")


def _render_template(raw: bytes, token: bytes, replacement: str) -> bytes:
    if raw.count(token) != 1:
        raise KitBuildError("bootstrap template token count is invalid")
    rendered = raw.replace(token, replacement.encode("ascii"))
    if token in rendered:
        raise KitBuildError("bootstrap template token was not replaced")
    return rendered


def _identity_bytes(snapshot: SourceSnapshot, runtime_spec: RuntimeSpec) -> bytes:
    return canonical_json_bytes(
        {
            "builder_version": 1,
            "runtime": {
                "archive_sha256": runtime_spec.sha256,
                "sqlite_version": runtime_spec.sqlite_version,
                "url": runtime_spec.url,
                "version": runtime_spec.version,
            },
            "schema_id": "modori.office_benchmark_kit_identity",
            "schema_version": 1,
            "source_commit": snapshot.commit,
            "source_date_epoch": snapshot.source_date_epoch,
        }
    )


def _manifest_for_tree(root: Path) -> bytes:
    entries: list[ManifestEntry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {
            "MANIFEST.json",
            "RUN-MODORI-BENCHMARK.cmd",
            "VERIFY-AND-RUN.ps1",
        }:
            continue
        data_size = path.stat().st_size
        entries.append(
            ManifestEntry(
                path=relative,
                size_bytes=data_size,
                sha256=_sha256_file(path),
            )
        )
    return manifest_bytes(tuple(entries))


def _zip_datetime(epoch: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(epoch, timezone.utc)
    second = value.second - value.second % 2
    return (value.year, value.month, value.day, value.hour, value.minute, second)


def _write_deterministic_zip(
    kit_root: Path,
    archive_path: Path,
    kit_name: str,
    epoch: int,
) -> None:
    entries: dict[str, tuple[Path, bool]] = {f"{kit_name}/": (kit_root, True)}
    for path in kit_root.rglob("*"):
        relative = path.relative_to(kit_root).as_posix()
        is_directory = path.is_dir()
        archive_name = f"{kit_name}/{relative}" + ("/" if is_directory else "")
        entries[archive_name] = (path, is_directory)
    date_time = _zip_datetime(epoch)
    try:
        with zipfile.ZipFile(
            archive_path,
            "x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for archive_name in sorted(entries):
                path, is_directory = entries[archive_name]
                info = zipfile.ZipInfo(archive_name, date_time=date_time)
                info.create_system = 3
                info.compress_type = (
                    zipfile.ZIP_STORED if is_directory else zipfile.ZIP_DEFLATED
                )
                if is_directory:
                    info.external_attr = (0o40755 << 16) | 0x10
                    data = b""
                else:
                    info.external_attr = 0o100644 << 16
                    data = path.read_bytes()
                archive.writestr(info, data, compresslevel=9)
    except (OSError, zipfile.BadZipFile) as exc:
        raise KitBuildError("deterministic ZIP could not be written") from exc


def _safe_cleanup(stage: Path, output_dir: Path) -> None:
    if stage.parent != output_dir or not stage.name.startswith(".office-kit-build-"):
        raise KitBuildError("refusing unsafe builder cleanup")
    if stage.exists():
        shutil.rmtree(stage)


def build_kit(request: BuildRequest) -> BuildResult:
    if not isinstance(request, BuildRequest):
        raise KitBuildError("build request is invalid")
    if set(request.snapshot.files) != _REQUIRED_SOURCE_FILES:
        raise KitBuildError("source snapshot does not match the closed allowlist")
    if _is_link_or_junction(request.runtime_archive) or not request.runtime_archive.is_file():
        raise KitBuildError("runtime archive is missing or linked")
    try:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        output_dir = request.output_dir.resolve(strict=True)
    except OSError as exc:
        raise KitBuildError("output directory cannot be created") from exc
    if _is_link_or_junction(output_dir) or not output_dir.is_dir():
        raise KitBuildError("output directory is not a plain directory")

    kit_name = (
        f"modori-office-benchmark-kit-{request.snapshot.commit[:12]}-"
        f"py{request.runtime_spec.version.replace('.', '')}"
    )
    final_archive = output_dir / f"{kit_name}.zip"
    final_digest = output_dir / f"{kit_name}.zip.sha256"
    if final_archive.exists() or final_digest.exists():
        raise KitBuildError("delivery output already exists")

    stage = output_dir / f".office-kit-build-{uuid.uuid4().hex}"
    kit_root = stage / kit_name
    staged_archive = stage / f"{kit_name}.zip"
    archive_linked = False
    try:
        kit_root.mkdir(parents=True)
        (kit_root / "results").mkdir()
        (kit_root / "work").mkdir()
        _extract_runtime(
            request.runtime_archive,
            kit_root / "runtime",
            request.runtime_spec,
        )
        if request.validate_runtime:
            _validate_runtime_binary(kit_root / "runtime", request.runtime_spec)
        for source, destination in sorted(PAYLOAD_SOURCE_MAP.items()):
            _write_new(kit_root / PurePosixPath(destination), request.snapshot.files[source])
        _write_new(
            kit_root / "README-KO.txt",
            request.snapshot.files[TEMPLATE_SOURCE_FILES["readme"]],
        )
        _write_new(
            kit_root / "KIT-IDENTITY.json",
            _identity_bytes(request.snapshot, request.runtime_spec),
        )
        manifest = _manifest_for_tree(kit_root)
        _write_new(kit_root / "MANIFEST.json", manifest)
        powershell = _render_template(
            request.snapshot.files[TEMPLATE_SOURCE_FILES["powershell"]],
            b"__MANIFEST_SHA256__",
            hashlib.sha256(manifest).hexdigest(),
        )
        _write_new(kit_root / "VERIFY-AND-RUN.ps1", powershell)
        command = _render_template(
            request.snapshot.files[TEMPLATE_SOURCE_FILES["cmd"]],
            b"__POWERSHELL_SHA256__",
            hashlib.sha256(powershell).hexdigest(),
        )
        _write_new(kit_root / "RUN-MODORI-BENCHMARK.cmd", command)
        _write_deterministic_zip(
            kit_root,
            staged_archive,
            kit_name,
            request.snapshot.source_date_epoch,
        )
        archive_sha256 = _sha256_file(staged_archive)
        try:
            os.link(staged_archive, final_archive)
            archive_linked = True
        except FileExistsError as exc:
            raise KitBuildError("delivery output already exists") from exc
        except OSError as exc:
            raise KitBuildError("delivery archive could not be finalized") from exc
        _write_new(
            final_digest,
            f"{archive_sha256}  {final_archive.name}\n".encode("ascii"),
        )
        return BuildResult(
            archive=final_archive,
            digest_file=final_digest,
            archive_sha256=archive_sha256,
            kit_name=kit_name,
            source_commit=request.snapshot.commit,
        )
    except Exception:
        if archive_linked and final_archive.exists() and not final_digest.exists():
            final_archive.unlink()
        raise
    finally:
        _safe_cleanup(stage, output_dir)


def _git(repository_root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KitBuildError("Git source read failed") from exc
    if completed.returncode != 0:
        raise KitBuildError("Git source read failed")
    return completed.stdout


def snapshot_from_git(
    repository_root: Path,
    commit: str | None = None,
) -> SourceSnapshot:
    root = repository_root.resolve(strict=True)
    if _git(root, "status", "--porcelain"):
        raise KitBuildError("source worktree must be clean")
    selected = (
        _git(root, "rev-parse", "HEAD").decode("ascii").strip()
        if commit is None
        else commit
    )
    if not _COMMIT_RE.fullmatch(selected):
        raise KitBuildError("selected source commit is invalid")
    epoch_raw = _git(root, "show", "-s", "--format=%ct", selected)
    try:
        epoch = int(epoch_raw.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as exc:
        raise KitBuildError("source commit timestamp is invalid") from exc
    files = {
        path: _git(root, "show", f"{selected}:{path}")
        for path in sorted(_REQUIRED_SOURCE_FILES)
    }
    return SourceSnapshot(commit=selected, source_date_epoch=epoch, files=files)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--source-commit")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        snapshot = snapshot_from_git(_REPOSITORY_ROOT, arguments.source_commit)
        result = build_kit(
            BuildRequest(
                output_dir=arguments.output_dir.resolve(),
                runtime_archive=arguments.runtime_archive.resolve(),
                runtime_spec=RUNTIME_SPEC,
                snapshot=snapshot,
            )
        )
    except (KitBuildError, KitContractError) as exc:
        print(f"kit build failed: {exc}", file=sys.stderr)
        return 1
    print(
        canonical_json_bytes(
            {
                "archive": result.archive.name,
                "archive_sha256": result.archive_sha256,
                "digest_file": result.digest_file.name,
                "kit_name": result.kit_name,
                "source_commit": result.source_commit,
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
