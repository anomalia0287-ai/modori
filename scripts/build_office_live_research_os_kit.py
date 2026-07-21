"""Build the dedicated sealed live Research OS office benchmark kit."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

# Required only for resolved executables, fixed arguments, and shell=False.
import subprocess  # nosec B404
import sys
from types import MappingProxyType
import uuid
import zipfile


_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from scripts.live_research_os_office_benchmark import (  # noqa: E402
    ACCEPTANCE_FIXTURE_DIGEST,
    LIVE_BENCHMARK_RESULT_SCHEMA_ID,
    LIVE_BENCHMARK_RESULT_SCHEMA_VERSION,
    OfficeBenchmarkProtocol,
    protocol_digest,
)
from scripts.live_research_os_office_kit import (  # noqa: E402
    BENCHMARK_RESULT_SCHEMA_ID,
    BENCHMARK_RESULT_SCHEMA_VERSION,
    BUILDER_CONTRACT_VERSION,
    PINNED_PYTHON_VERSION,
    RUNTIME_LAYOUT,
    VERIFIER_CONTRACT_VERSION,
    KitContractError,
    KitIdentity,
    ManifestEntry,
    canonical_json_bytes,
    identity_bytes,
    kit_name,
    manifest_bytes,
    parse_identity,
    parse_package_lock,
    sha256_bytes,
)
from scripts.package_environment import without_workspace_reference_runtime  # noqa: E402


BENCHMARK_EXECUTABLE_NAME = "ModoriLiveResearchOSBenchmark"
PYINSTALLER_BUILD_NAME = "MROS"
RUNTIME_IDENTITY_RESOURCE_NAME = "LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json"
PACKAGE_LOCK_SOURCE = "scripts/office_live_research_os_kit/PACKAGE-LOCK.json"
PYINSTALLER_HOOK_SOURCE = "scripts/office_live_research_os_kit/hooks"
TEMPLATE_SOURCE_FILES = {
    "cmd": (
        "scripts/office_live_research_os_kit/"
        "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd.in"
    ),
    "powershell": "scripts/office_live_research_os_kit/VERIFY-AND-RUN.ps1.in",
    "readme": "scripts/office_live_research_os_kit/README-KO.txt",
}

_DELIVERY_DIRECTORY_NAME = "live-research-os-office"
_DELIVERY_PARENT_NAME = "dist"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MAX_RUNTIME_BYTES = 2 * 1024**3
_IMMUTABLE_EXCLUSIONS = frozenset(
    {
        "MANIFEST.json",
        "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd",
        "VERIFY-AND-RUN.ps1",
    }
)


class KitBuildError(RuntimeError):
    """Raised when a kit build cannot prove its source or runtime inputs."""


@dataclass(frozen=True)
class KitSource:
    command_template: bytes
    powershell_template: bytes
    readme: bytes
    package_lock: bytes

    def __post_init__(self) -> None:
        for value, field in (
            (self.command_template, "command template"),
            (self.powershell_template, "PowerShell template"),
            (self.readme, "README"),
            (self.package_lock, "package lock"),
        ):
            if not isinstance(value, bytes) or not value:
                raise KitBuildError(f"{field} must be non-empty bytes")
        if self.command_template.count(b"__POWERSHELL_SHA256__") != 1:
            raise KitBuildError("command template token inventory is invalid")
        if self.powershell_template.count(b"__MANIFEST_SHA256__") != 1:
            raise KitBuildError("PowerShell manifest token inventory is invalid")
        if self.powershell_template.count(b"__IDENTITY_SHA256__") != 1:
            raise KitBuildError("PowerShell identity token inventory is invalid")
        try:
            self.readme.decode("utf-8", errors="strict")
            parse_package_lock(self.package_lock)
        except (UnicodeError, KitContractError) as exc:
            raise KitBuildError("package lock or README is invalid") from exc


@dataclass(frozen=True)
class RuntimeProduct:
    root: Path
    identity: KitIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path) or not self.root.is_absolute():
            raise KitBuildError("runtime root must be an absolute Path")
        if not isinstance(self.identity, KitIdentity):
            raise KitBuildError("runtime identity is invalid")


@dataclass(frozen=True)
class OuterBuildRequest:
    output_dir: Path
    runtime: RuntimeProduct
    source: KitSource

    def __post_init__(self) -> None:
        if not isinstance(self.output_dir, Path) or not self.output_dir.is_absolute():
            raise KitBuildError("output directory must be an absolute Path")
        if not isinstance(self.runtime, RuntimeProduct):
            raise KitBuildError("runtime product is invalid")
        if not isinstance(self.source, KitSource):
            raise KitBuildError("kit source is invalid")


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


def _is_link_or_reparse(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return (
            path.is_symlink()
            or bool(is_junction and is_junction())
            or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        )
    except OSError:
        return True


def _write_new(path: Path, raw: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise KitBuildError("build output already exists") from exc
    except OSError as exc:
        raise KitBuildError("build output could not be written") from exc


def validate_runtime_member_names(paths: Sequence[str]) -> tuple[str, ...]:
    """Validate a runtime inventory without relying on host case semantics."""

    if not isinstance(paths, Sequence) or isinstance(paths, (str, bytes)):
        raise KitBuildError("runtime member inventory is invalid")
    checked: list[str] = []
    try:
        for path in paths:
            if not isinstance(path, str):
                raise KitBuildError("runtime member inventory is invalid")
            ManifestEntry(path, 0, "0" * 64)
            checked.append(path)
    except KitContractError as exc:
        raise KitBuildError("runtime member path is invalid") from exc
    if len(checked) != len(set(checked)):
        raise KitBuildError("runtime contains duplicate paths")
    if len({path.casefold() for path in checked}) != len(checked):
        raise KitBuildError("runtime contains case-colliding paths")
    return tuple(checked)


def _relative_runtime_files(root: Path) -> tuple[tuple[str, Path], ...]:
    if not root.is_dir() or _is_link_or_reparse(root):
        raise KitBuildError("runtime root is missing, linked, or reparse-backed")
    result: list[tuple[str, Path]] = []
    total = 0
    try:
        for path in sorted(root.rglob("*")):
            if _is_link_or_reparse(path):
                raise KitBuildError("runtime contains a link or reparse point")
            if path.is_dir():
                continue
            if not path.is_file():
                raise KitBuildError("runtime contains a non-regular member")
            relative = path.relative_to(root).as_posix()
            try:
                ManifestEntry(relative, path.stat().st_size, _sha256_file(path))
            except KitContractError as exc:
                raise KitBuildError(
                    f"runtime member path is invalid: {relative}"
                ) from exc
            total += path.stat().st_size
            if total > _MAX_RUNTIME_BYTES:
                raise KitBuildError("runtime exceeds its closed size limit")
            result.append((relative, path))
    except KitBuildError:
        raise
    except OSError as exc:
        raise KitBuildError("runtime inventory could not be read") from exc
    if not result:
        raise KitBuildError("runtime inventory is empty")
    validate_runtime_member_names([relative for relative, _ in result])
    return tuple(result)


def _render(raw: bytes, replacements: Mapping[bytes, str]) -> bytes:
    rendered = raw
    for token, replacement in replacements.items():
        if rendered.count(token) != 1:
            raise KitBuildError("bootstrap template token inventory is invalid")
        rendered = rendered.replace(token, replacement.encode("ascii"))
    if any(token in rendered for token in replacements):
        raise KitBuildError("bootstrap template token was not replaced")
    return rendered


def _windows_command_bytes(raw: bytes) -> bytes:
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.replace(b"\n", b"\r\n")


def _manifest_for_tree(root: Path) -> bytes:
    entries: list[ManifestEntry] = []
    for path in sorted(root.rglob("*")):
        if _is_link_or_reparse(path):
            raise KitBuildError("kit staging tree contains a link or reparse point")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in _IMMUTABLE_EXCLUSIONS:
            continue
        entries.append(
            ManifestEntry(
                path=relative,
                size_bytes=path.stat().st_size,
                sha256=_sha256_file(path),
            )
        )
    try:
        return manifest_bytes(tuple(entries))
    except KitContractError as exc:
        raise KitBuildError("kit staging inventory is invalid") from exc


def _zip_datetime(epoch: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(epoch, timezone.utc)
    second = value.second - value.second % 2
    return value.year, value.month, value.day, value.hour, value.minute, second


def _write_deterministic_zip(
    kit_root: Path,
    archive_path: Path,
    root_name: str,
    epoch: int,
) -> None:
    entries: dict[str, tuple[Path, bool]] = {f"{root_name}/": (kit_root, True)}
    for path in kit_root.rglob("*"):
        relative = path.relative_to(kit_root).as_posix()
        is_directory = path.is_dir()
        name = f"{root_name}/{relative}" + ("/" if is_directory else "")
        entries[name] = path, is_directory
    date_time = _zip_datetime(epoch)
    try:
        with zipfile.ZipFile(
            archive_path,
            "x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            for name in sorted(entries):
                path, is_directory = entries[name]
                info = zipfile.ZipInfo(name, date_time=date_time)
                info.create_system = 3
                if is_directory:
                    info.compress_type = zipfile.ZIP_STORED
                    info.external_attr = (0o40755 << 16) | 0x10
                    raw = b""
                else:
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    raw = path.read_bytes()
                archive.writestr(info, raw, compresslevel=9)
    except (OSError, zipfile.BadZipFile) as exc:
        raise KitBuildError("deterministic ZIP could not be written") from exc


def _safe_outer_cleanup(stage: Path, output_dir: Path) -> None:
    if stage.parent != output_dir or not stage.name.startswith(".live-os-kit-build-"):
        raise KitBuildError("refusing unsafe outer builder cleanup")
    if stage.exists():
        shutil.rmtree(stage)


def _validate_dedicated_output(path: Path) -> Path:
    if (
        path.name != _DELIVERY_DIRECTORY_NAME
        or path.parent.name != _DELIVERY_PARENT_NAME
    ):
        raise KitBuildError("dedicated output directory is required")
    try:
        path.mkdir(parents=True, exist_ok=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise KitBuildError("dedicated output directory could not be created") from exc
    if resolved != path or _is_link_or_reparse(resolved) or not resolved.is_dir():
        raise KitBuildError("dedicated output directory is linked or ambiguous")
    return resolved


def build_outer_kit(request: OuterBuildRequest) -> BuildResult:
    """Seal an already-built verified runtime into a deterministic outer kit."""

    if not isinstance(request, OuterBuildRequest):
        raise KitBuildError("outer build request is invalid")
    output_dir = _validate_dedicated_output(request.output_dir)
    identity = request.runtime.identity
    lock_entries = parse_package_lock(request.source.package_lock)
    if (
        not lock_entries
        or sha256_bytes(request.source.package_lock) != identity.package_lock_sha256
    ):
        raise KitBuildError("package lock does not match runtime identity")
    runtime_files = _relative_runtime_files(request.runtime.root)
    embedded_identity_path = (
        request.runtime.root / "_internal" / RUNTIME_IDENTITY_RESOURCE_NAME
    )
    expected_identity = identity_bytes(identity)
    try:
        embedded_identity = embedded_identity_path.read_bytes()
    except OSError as exc:
        raise KitBuildError("runtime identity resource is missing") from exc
    if (
        embedded_identity != expected_identity
        or parse_identity(embedded_identity) != identity
    ):
        raise KitBuildError("runtime identity resource does not match")
    expected_executable = request.runtime.root / f"{BENCHMARK_EXECUTABLE_NAME}.exe"
    if not expected_executable.is_file() or _is_link_or_reparse(expected_executable):
        raise KitBuildError("runtime executable is missing or linked")

    name = kit_name(identity.source_commit, identity.python_version)
    final_archive = output_dir / f"{name}.zip"
    final_digest = output_dir / f"{name}.zip.sha256"
    if final_archive.exists() or final_digest.exists():
        raise KitBuildError("delivery output already exists")
    stage = output_dir / f".live-os-kit-build-{uuid.uuid4().hex}"
    root = stage / name
    staged_archive = stage / f"{name}.zip"
    archive_linked = False
    try:
        (root / "results").mkdir(parents=True)
        for relative, source in runtime_files:
            _write_new(root / "runtime" / PurePosixPath(relative), source.read_bytes())
        _write_new(root / "README-KO.txt", request.source.readme)
        _write_new(root / "PACKAGE-LOCK.json", request.source.package_lock)
        _write_new(root / "KIT-IDENTITY.json", expected_identity)
        manifest = _manifest_for_tree(root)
        _write_new(root / "MANIFEST.json", manifest)
        powershell = _render(
            request.source.powershell_template,
            {
                b"__IDENTITY_SHA256__": sha256_bytes(expected_identity),
                b"__MANIFEST_SHA256__": sha256_bytes(manifest),
            },
        )
        _write_new(root / "VERIFY-AND-RUN.ps1", powershell)
        command = _windows_command_bytes(
            _render(
                request.source.command_template,
                {b"__POWERSHELL_SHA256__": sha256_bytes(powershell)},
            )
        )
        _write_new(root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd", command)
        _write_deterministic_zip(
            root,
            staged_archive,
            name,
            identity.source_date_epoch,
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
            kit_name=name,
            source_commit=identity.source_commit,
        )
    except (KitContractError, OSError) as exc:
        if isinstance(exc, KitBuildError):
            raise
        raise KitBuildError("outer kit could not be sealed") from exc
    finally:
        if archive_linked and final_archive.exists() and not final_digest.exists():
            final_archive.unlink()
        _safe_outer_cleanup(stage, output_dir)


def build_pyinstaller_command(
    *,
    repository_root: Path,
    identity_resource: Path,
    work_root: Path,
) -> list[str]:
    """Return the sole allowed one-folder console build command."""

    repository = Path(repository_root)
    resource = Path(identity_resource)
    work = Path(work_root)
    hidden_imports = (
        "numpy",
        "pandas",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "modori.steps.statistics",
    )
    hidden_args = [
        item for module in hidden_imports for item in ("--hidden-import", module)
    ]
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        PYINSTALLER_BUILD_NAME,
        "--distpath",
        str(work / "d"),
        "--workpath",
        str(work / "w"),
        "--specpath",
        str(work / "s"),
        "--paths",
        str(repository / "src"),
        "--additional-hooks-dir",
        str(repository / PYINSTALLER_HOOK_SOURCE),
        "--add-data",
        f"{resource}{os.pathsep}.",
        *hidden_args,
        str(repository / "scripts" / "run_office_live_research_os_benchmark.py"),
    ]


def validate_pyinstaller_diagnostics(raw: str) -> tuple[str, ...]:
    if not isinstance(raw, str):
        raise KitBuildError("PyInstaller diagnostic stream is invalid")
    dangerous = tuple(
        line.strip()
        for line in raw.splitlines()
        if re.search(r"(?:^|\s)(?:WARNING|ERROR):|Traceback", line)
    )
    if dangerous:
        first = dangerous[0]
        if len(first) > 500:
            first = first[:500] + "..."
        raise KitBuildError(f"PyInstaller returned an unexpected diagnostic: {first}")
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


def _git(repository_root: Path, *arguments: str) -> bytes:
    git_command = shutil.which("git")
    if not git_command:
        raise KitBuildError("Git executable is unavailable")
    try:
        git_executable = Path(git_command).resolve(strict=True)
    except OSError as exc:
        raise KitBuildError("Git executable could not be resolved") from exc
    if not git_executable.is_file() or _is_link_or_reparse(git_executable):
        raise KitBuildError("Git executable is missing or linked")
    try:
        # Git is resolved to one plain executable; arguments are internal literals.
        completed = subprocess.run(  # nosec B603
            [str(git_executable), *arguments],
            cwd=repository_root,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KitBuildError("Git source read failed") from exc
    if completed.returncode != 0 or completed.stderr:
        raise KitBuildError("Git source read failed")
    return completed.stdout


def _clean_head(repository_root: Path, selected_commit: str | None) -> tuple[str, int]:
    root = repository_root.resolve(strict=True)
    if _git(root, "status", "--porcelain"):
        raise KitBuildError("source worktree must be clean")
    branch = _git(root, "symbolic-ref", "-q", "HEAD").decode("ascii").strip()
    if not branch:
        raise KitBuildError("source worktree must not be detached")
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if not _COMMIT_RE.fullmatch(head):
        raise KitBuildError("source HEAD is invalid")
    if selected_commit is not None and selected_commit != head:
        raise KitBuildError("selected source commit does not match clean HEAD")
    try:
        epoch = int(_git(root, "show", "-s", "--format=%ct", head).decode("ascii"))
    except (UnicodeError, ValueError) as exc:
        raise KitBuildError("source commit timestamp is invalid") from exc
    return head, epoch


def _read_committed_source(repository_root: Path, relative: str, commit: str) -> bytes:
    raw = _git(repository_root, "show", f"{commit}:{relative}")
    try:
        current = (repository_root / PurePosixPath(relative)).read_bytes()
    except OSError as exc:
        raise KitBuildError("required committed source is missing") from exc
    if current != raw:
        raise KitBuildError("required source differs from clean commit")
    return raw


def _installed_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError as exc:
        raise KitBuildError("package lock dependency is missing") from exc


def _validate_installed_lock(raw: bytes) -> Mapping[str, str]:
    try:
        entries = parse_package_lock(raw)
    except KitContractError as exc:
        raise KitBuildError("package lock is invalid") from exc
    installed: dict[str, str] = {}
    for entry in entries:
        observed = _installed_version(entry.name)
        if observed != entry.version:
            raise KitBuildError("installed package does not match package lock")
        installed[entry.name] = observed
    required = {
        "numpy",
        "pandas",
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "pyside6",
        "pyside6-addons",
        "pyside6-essentials",
        "shiboken6",
    }
    if not required <= set(installed):
        raise KitBuildError("package lock omits a required runtime package")
    return MappingProxyType(installed)


def _bootloader_path() -> Path:
    try:
        import PyInstaller
    except ImportError as exc:
        raise KitBuildError("PyInstaller is unavailable") from exc
    path = (
        Path(PyInstaller.__file__).resolve().parent
        / "bootloader"
        / "Windows-64bit-intel"
        / "run.exe"
    )
    if not path.is_file() or _is_link_or_reparse(path):
        raise KitBuildError("PyInstaller console bootloader is missing or linked")
    return path


def _build_environment(
    repository_root: Path,
    work_root: Path,
    *,
    source_date_epoch: int,
) -> dict[str, str]:
    environment = without_workspace_reference_runtime(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    environment["SOURCE_DATE_EPOCH"] = str(source_date_epoch)
    environment["PYTHONPATH"] = str(repository_root / "src")
    environment["MPLCONFIGDIR"] = str(work_root / "matplotlib-cache")
    environment["MODORI_CACHE_DIR"] = str(work_root / "modori-cache")
    Path(environment["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(environment["MODORI_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    return environment


def _runtime_versions() -> tuple[str, str, str, str, str]:
    import numpy
    import pandas
    import PySide6
    import sqlite3

    return (
        sys.version.split()[0],
        sqlite3.sqlite_version,
        PySide6.__version__,
        numpy.__version__,
        pandas.__version__,
    )


def _verify_runtime_product(runtime: RuntimeProduct) -> None:
    executable = runtime.root / f"{BENCHMARK_EXECUTABLE_NAME}.exe"
    try:
        # The executable is the verified product root and the argument is fixed.
        completed = subprocess.run(  # nosec B603
            [str(executable), "--self-identity"],
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise KitBuildError("dedicated runtime self-check could not execute") from exc
    if (
        completed.returncode != 0
        or completed.stderr
        or completed.stdout != identity_bytes(runtime.identity) + b"\n"
    ):
        stderr_code = (
            completed.stderr[-2_048:].decode("ascii", errors="replace").strip()
        )
        raise KitBuildError(
            "dedicated runtime self-identity does not match "
            f"(exit={completed.returncode}, stderr={stderr_code or 'empty'}, "
            f"stdout_bytes={len(completed.stdout)})"
        )


def build_kit_from_repository(
    repository_root: Path,
    *,
    output_dir: Path,
    selected_commit: str | None = None,
) -> BuildResult:
    """Build the runtime and outer kit only from one clean committed HEAD."""

    repository = repository_root.resolve(strict=True)
    commit, epoch = _clean_head(repository, selected_commit)
    lock = _read_committed_source(repository, PACKAGE_LOCK_SOURCE, commit)
    installed = _validate_installed_lock(lock)
    source = KitSource(
        command_template=_read_committed_source(
            repository, TEMPLATE_SOURCE_FILES["cmd"], commit
        ),
        powershell_template=_read_committed_source(
            repository, TEMPLATE_SOURCE_FILES["powershell"], commit
        ),
        readme=_read_committed_source(
            repository, TEMPLATE_SOURCE_FILES["readme"], commit
        ),
        package_lock=lock,
    )
    python_version, sqlite_version, pyside_version, numpy_version, pandas_version = (
        _runtime_versions()
    )
    if python_version != PINNED_PYTHON_VERSION:
        raise KitBuildError("build Python version does not match the pin")
    if (
        pyside_version != installed["pyside6"]
        or numpy_version != installed["numpy"]
        or pandas_version != installed["pandas"]
    ):
        raise KitBuildError("runtime import versions do not match package lock")
    if (
        BENCHMARK_RESULT_SCHEMA_ID != LIVE_BENCHMARK_RESULT_SCHEMA_ID
        or BENCHMARK_RESULT_SCHEMA_VERSION != LIVE_BENCHMARK_RESULT_SCHEMA_VERSION
    ):
        raise KitBuildError("benchmark result schema drifted from the kit contract")
    bootloader = _bootloader_path()
    identity = KitIdentity(
        source_commit=commit,
        source_date_epoch=epoch,
        protocol_digest=protocol_digest(OfficeBenchmarkProtocol()),
        fixture_digest=ACCEPTANCE_FIXTURE_DIGEST,
        python_version=python_version,
        sqlite_version=sqlite_version,
        pyside_version=pyside_version,
        numpy_version=numpy_version,
        pandas_version=pandas_version,
        pyinstaller_version=installed["pyinstaller"],
        pyinstaller_bootloader_sha256=_sha256_file(bootloader),
        package_lock_sha256=sha256_bytes(lock),
        executable_path=f"runtime/{BENCHMARK_EXECUTABLE_NAME}.exe",
        runtime_layout=RUNTIME_LAYOUT,
        builder_contract_version=BUILDER_CONTRACT_VERSION,
        verifier_contract_version=VERIFIER_CONTRACT_VERSION,
        result_schema_id=BENCHMARK_RESULT_SCHEMA_ID,
        result_schema_version=BENCHMARK_RESULT_SCHEMA_VERSION,
    )
    temporary_parent = repository / ".tmp" / "live-research-os-office-kit"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    work_root = temporary_parent / "b"
    if work_root.exists() or _is_link_or_reparse(temporary_parent):
        raise KitBuildError("dedicated build root is unsafe")
    try:
        work_root.mkdir()
        resource = work_root / RUNTIME_IDENTITY_RESOURCE_NAME
        _write_new(resource, identity_bytes(identity))
        command = build_pyinstaller_command(
            repository_root=repository,
            identity_resource=resource,
            work_root=work_root,
        )
        try:
            # The command is built locally from fixed PyInstaller arguments.
            completed = subprocess.run(  # nosec B603
                command,
                cwd=repository,
                env=_build_environment(
                    repository,
                    work_root,
                    source_date_epoch=epoch,
                ),
                capture_output=True,
                check=False,
                timeout=30 * 60,
                encoding="utf-8",
                errors="strict",
            )
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            raise KitBuildError("PyInstaller execution failed") from exc
        validate_pyinstaller_diagnostics(completed.stdout + "\n" + completed.stderr)
        if completed.returncode != 0:
            raise KitBuildError("PyInstaller returned a nonzero exit")
        runtime_root = work_root / "d" / PYINSTALLER_BUILD_NAME
        built_executable = runtime_root / f"{PYINSTALLER_BUILD_NAME}.exe"
        final_executable = runtime_root / f"{BENCHMARK_EXECUTABLE_NAME}.exe"
        if (
            not built_executable.is_file()
            or _is_link_or_reparse(built_executable)
            or final_executable.exists()
        ):
            raise KitBuildError("PyInstaller runtime executable is invalid")
        try:
            os.replace(built_executable, final_executable)
        except OSError as exc:
            raise KitBuildError(
                "PyInstaller runtime executable could not be renamed"
            ) from exc
        runtime = RuntimeProduct(
            root=runtime_root.resolve(strict=True), identity=identity
        )
        _relative_runtime_files(runtime.root)
        _verify_runtime_product(runtime)
        return build_outer_kit(
            OuterBuildRequest(
                output_dir=output_dir.resolve(),
                runtime=runtime,
                source=source,
            )
        )
    finally:
        if work_root.exists():
            if work_root.parent != temporary_parent or work_root.name != "b":
                raise KitBuildError("refusing unsafe PyInstaller cleanup")
            shutil.rmtree(work_root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist") / _DELIVERY_DIRECTORY_NAME,
    )
    parser.add_argument("--source-commit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = build_kit_from_repository(
            _REPOSITORY_ROOT,
            output_dir=arguments.output_dir.resolve(),
            selected_commit=arguments.source_commit,
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
