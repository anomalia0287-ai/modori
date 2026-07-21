"""Independent verifier for the sealed live Research OS office benchmark kit."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

# Required only for the fixed frozen executable and two literal identity modes.
import subprocess  # nosec B404
import tempfile
from types import MappingProxyType
from typing import Literal, NoReturn
import zipfile
import zlib

from scripts.live_research_os_office_benchmark import (
    ACCEPTANCE_FIXTURE_DIGEST,
    BenchmarkContractError,
    BenchmarkEvaluation,
    OfficeBenchmarkProtocol,
    canonical_result_bytes,
    evaluate_result,
    protocol_digest,
    result_filename,
    verify_summary_bytes,
)
from scripts.live_research_os_office_kit import (
    KitContractError,
    KitIdentity,
    ManifestEntry,
    identity_bytes,
    kit_name,
    parse_identity,
    parse_manifest,
    parse_package_lock,
    sha256_bytes,
)


_BOOTSTRAP_FILES = frozenset(
    {
        "MANIFEST.json",
        "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd",
        "VERIFY-AND-RUN.ps1",
    }
)
_MUTABLE_ROOTS = frozenset({"results"})
_EMBEDDED_IDENTITY = "runtime/_internal/LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json"
_PYINSTALLER_BASE_LIBRARY = "runtime/_internal/base_library.zip"
_MAX_ARCHIVE_BYTES = 2 * 1024**3
_MAX_ARCHIVE_MEMBERS = 50_000
_MAX_TEXT_BYTES = 16 * 1024**2
_KIT_ROOT_RE = re.compile(r"^modori-live-research-os-office-kit-[0-9a-f]{12}-py31210$")
_SOURCE_ONLY_SUFFIXES = frozenset(
    {
        ".build",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".lib",
        ".pxd",
        ".pxi",
        ".py",
        ".pyc",
        ".pyi",
        ".pyo",
        ".pyx",
        ".tp",
    }
)
_SOURCE_ONLY_DIRECTORIES = frozenset(
    {".git", ".tmp", ".venv", "__pycache__", "fixtures", "tests"}
)
_REQUIRED_PACKAGE_FIELDS = {
    "numpy": "numpy_version",
    "pandas": "pandas_version",
    "pyinstaller": "pyinstaller_version",
    "pyside6": "pyside_version",
    "pyside6-addons": "pyside_version",
    "pyside6-essentials": "pyside_version",
    "shiboken6": "pyside_version",
}


class KitVerificationError(RuntimeError):
    """Raised when a kit cannot prove its sealed inventory and runtime identity."""

    def __init__(self, message: str, *, code: str = "kit_invalid") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class VerifiedKit:
    source: Path
    source_kind: Literal["directory", "zip"]
    archive_sha256: str | None
    identity: KitIdentity
    manifest_entries: tuple[ManifestEntry, ...]
    member_count: int
    runtime_verified: bool


@dataclass(frozen=True)
class ReturnedRunVerification:
    status: Literal["valid_pass", "valid_stop", "invalid_run"]
    reason_code: str | None
    evaluation: BenchmarkEvaluation | None
    result: Mapping[str, object] | None
    origin_authenticated: bool = False


RuntimeProbe = Callable[[Path, KitIdentity], None]


def _fail(message: str, *, code: str = "kit_invalid") -> NoReturn:
    raise KitVerificationError(message, code=code)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        junction = getattr(path, "is_junction", None)
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return (
            path.is_symlink()
            or bool(junction and junction())
            or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        )
    except OSError:
        return True


def _plain_directory(path: Path, field: str) -> Path:
    candidate = Path(path).absolute()
    if _is_link_or_reparse(candidate) or not candidate.is_dir():
        _fail(f"{field} is missing, linked, or reparse-backed")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise KitVerificationError(f"{field} cannot be resolved") from exc
    if _is_link_or_reparse(resolved) or not resolved.is_dir():
        _fail(f"{field} is not a plain directory")
    return resolved


def _plain_file(path: Path, field: str) -> Path:
    candidate = Path(path).absolute()
    if _is_link_or_reparse(candidate) or not candidate.is_file():
        _fail(f"{field} is missing, linked, or reparse-backed")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise KitVerificationError(f"{field} cannot be resolved") from exc
    if _is_link_or_reparse(resolved) or not resolved.is_file():
        _fail(f"{field} is not a plain file")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise KitVerificationError("verified file could not be read") from exc
    return digest.hexdigest()


def _read_small_file(path: Path, field: str) -> bytes:
    try:
        size = path.stat().st_size
        if size < 1 or size > _MAX_TEXT_BYTES:
            _fail(f"{field} size is invalid")
        return path.read_bytes()
    except OSError as exc:
        raise KitVerificationError(f"{field} could not be read") from exc


def _safe_manifest_path(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if _is_link_or_reparse(current):
            _fail("manifest member contains a link or reparse point")
    try:
        resolved = current.resolve(strict=True)
    except OSError as exc:
        raise KitVerificationError("manifest member is missing") from exc
    if not resolved.is_relative_to(root) or not resolved.is_file():
        _fail("manifest member escapes the kit or is not a regular file")
    return resolved


def _is_license_source_path(relative: str) -> bool:
    parts = tuple(part.casefold() for part in PurePosixPath(relative).parts)
    return (
        "src" in parts
        and any(part.endswith(".dist-info") for part in parts)
        and ("licenses" in parts)
    )


def _reject_contamination(relative: str) -> None:
    path = PurePosixPath(relative)
    parts = {part.casefold() for part in path.parts}
    suffix = path.suffix.casefold()
    if not parts.isdisjoint(_SOURCE_ONLY_DIRECTORIES):
        _fail("kit contains source, bytecode, fixture, test, or worktree material")
    if "src" in parts and not _is_license_source_path(relative):
        _fail("kit contains an executable source tree")
    if suffix in _SOURCE_ONLY_SUFFIXES:
        _fail("kit contains source or bytecode material")
    if suffix == ".zip" and relative != _PYINSTALLER_BASE_LIBRARY:
        _fail("kit contains a nested ZIP")


def _walk_immutable(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    found_files: list[str] = []
    found_directories: list[str] = []
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
            top = relative.split("/", 1)[0]
            if entry.is_symlink() or _is_link_or_reparse(path):
                _fail("kit inventory contains a link or reparse point")
            try:
                if entry.is_dir(follow_symlinks=False):
                    if top not in _MUTABLE_ROOTS:
                        found_directories.append(relative)
                        stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    if top not in _MUTABLE_ROOTS:
                        found_files.append(relative)
                else:
                    _fail("kit inventory contains a special file")
            except OSError as exc:
                raise KitVerificationError(
                    "kit inventory entry cannot be read"
                ) from exc
    return tuple(sorted(found_files)), tuple(sorted(found_directories))


def _required_directories(paths: set[str]) -> tuple[str, ...]:
    directories: set[str] = set()
    for relative in paths:
        parts = PurePosixPath(relative).parts
        directories.update("/".join(parts[:index]) for index in range(1, len(parts)))
    return tuple(sorted(directories))


def _verify_package_lock(raw: bytes, identity: KitIdentity) -> None:
    try:
        entries = parse_package_lock(raw)
    except KitContractError as exc:
        raise KitVerificationError("package lock contract is invalid") from exc
    if sha256_bytes(raw) != identity.package_lock_sha256:
        _fail("package lock digest does not match kit identity")
    versions = {entry.name: entry.version for entry in entries}
    if "pyinstaller-hooks-contrib" not in versions:
        _fail("package lock omits PyInstaller hooks")
    for package, identity_field in _REQUIRED_PACKAGE_FIELDS.items():
        if versions.get(package) != getattr(identity, identity_field):
            _fail("package lock runtime version does not match kit identity")


def _verify_bootstrap_chain(
    root: Path, identity_raw: bytes, manifest_raw: bytes
) -> None:
    powershell = _read_small_file(root / "VERIFY-AND-RUN.ps1", "PowerShell bootstrap")
    command = _read_small_file(
        root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd",
        "command bootstrap",
    )
    manifest_digest = sha256_bytes(manifest_raw).encode("ascii")
    identity_digest = sha256_bytes(identity_raw).encode("ascii")
    powershell_digest = sha256_bytes(powershell).encode("ascii")
    if powershell.count(manifest_digest) != 1:
        _fail("PowerShell bootstrap does not bind the manifest digest")
    if powershell.count(identity_digest) != 1:
        _fail("PowerShell bootstrap does not bind the identity digest")
    if command.count(powershell_digest) != 1:
        _fail("command bootstrap does not bind the PowerShell digest")
    if b"__" in powershell or b"__" in command:
        _fail("bootstrap contains an unresolved template token")


def _probe_environment(probe_root: Path) -> dict[str, str]:
    work = str(probe_root)
    environment = {
        "LOCALAPPDATA": work,
        "PYTHONDONTWRITEBYTECODE": "1",
        "TEMP": work,
        "TMP": work,
    }
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if system_root:
        environment["SystemRoot"] = system_root
        environment["WINDIR"] = system_root
        environment["PATH"] = str(Path(system_root) / "System32")
    if "COMSPEC" in os.environ:
        environment["COMSPEC"] = os.environ["COMSPEC"]
    if "PATHEXT" in os.environ:
        environment["PATHEXT"] = os.environ["PATHEXT"]
    return environment


def probe_runtime_identity(root: Path, identity: KitIdentity) -> None:
    """Run only the two fixed identity modes after static verification succeeds."""

    verified_root = _plain_directory(Path(root), "runtime identity kit root")
    executable = _safe_manifest_path(verified_root, identity.executable_path)
    commands = (
        ([str(executable), "--self-identity"], identity_bytes(identity) + b"\n"),
        ([str(executable), "--verify-kit-identity"], b""),
    )
    temporary_base = _plain_directory(
        Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()),
        "runtime identity probe base",
    )
    if temporary_base == verified_root or verified_root in temporary_base.parents:
        _fail("runtime identity probe workspace must not overlap the supplied kit")
    try:
        with tempfile.TemporaryDirectory(
            prefix="mrv-probe-",
            dir=temporary_base,
        ) as raw_probe_root:
            probe_root = _plain_directory(
                Path(raw_probe_root),
                "runtime identity probe root",
            )
            if probe_root == verified_root or verified_root in probe_root.parents:
                _fail("runtime identity probe workspace must remain outside the kit")
            environment = _probe_environment(probe_root)
            for command, expected_stdout in commands:
                try:
                    # The executable is manifest-verified and both arguments are literals.
                    completed = subprocess.run(  # nosec B603
                        command,
                        cwd=verified_root,
                        env=environment,
                        capture_output=True,
                        check=False,
                        timeout=120,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise KitVerificationError(
                        "runtime identity probe could not execute"
                    ) from exc
                if (
                    completed.returncode != 0
                    or completed.stderr
                    or completed.stdout != expected_stdout
                ):
                    _fail("runtime self-identity does not match the sealed kit")
    except KitVerificationError:
        raise
    except OSError as exc:
        raise KitVerificationError(
            "runtime identity probe workspace is unavailable"
        ) from exc


def _verify_directory(
    root: Path,
    *,
    source: Path,
    source_kind: Literal["directory", "zip"],
    archive_sha256: str | None,
    member_count: int | None,
    runtime_probe: RuntimeProbe,
) -> VerifiedKit:
    resolved = _plain_directory(root, "kit root")
    for mutable in sorted(_MUTABLE_ROOTS):
        _plain_directory(resolved / mutable, f"{mutable} root")
    for bootstrap in sorted(_BOOTSTRAP_FILES):
        _plain_file(resolved / bootstrap, f"{bootstrap} bootstrap")

    manifest_raw = _read_small_file(resolved / "MANIFEST.json", "manifest")
    try:
        entries = parse_manifest(manifest_raw)
    except KitContractError as exc:
        raise KitVerificationError("manifest contract is invalid") from exc
    for entry in entries:
        _reject_contamination(entry.path)
        path = _safe_manifest_path(resolved, entry.path)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise KitVerificationError("manifest member size cannot be read") from exc
        if size != entry.size_bytes:
            _fail("manifest member size does not match")
        if _sha256_file(path) != entry.sha256:
            _fail("manifest member digest does not match")

    expected_inventory = tuple(
        sorted({entry.path for entry in entries} | _BOOTSTRAP_FILES)
    )
    actual_files, actual_directories = _walk_immutable(resolved)
    if actual_files != expected_inventory:
        _fail("kit has a missing or unexpected immutable member")
    if actual_directories != _required_directories(set(expected_inventory)):
        _fail("kit has a missing or unexpected immutable directory")

    by_path = {entry.path: entry for entry in entries}
    required = {
        "KIT-IDENTITY.json",
        "PACKAGE-LOCK.json",
        "README-KO.txt",
        _EMBEDDED_IDENTITY,
        "runtime/ModoriLiveResearchOSBenchmark.exe",
    }
    if not required <= set(by_path):
        _fail("kit immutable closure is incomplete")
    identity_raw = _read_small_file(resolved / "KIT-IDENTITY.json", "kit identity")
    try:
        identity = parse_identity(identity_raw)
    except KitContractError as exc:
        raise KitVerificationError("kit identity contract is invalid") from exc
    if resolved.name != kit_name(identity.source_commit, identity.python_version):
        _fail("kit root name does not match its identity")
    if identity.protocol_digest != protocol_digest(OfficeBenchmarkProtocol()):
        _fail("kit protocol digest does not match the frozen protocol")
    if identity.fixture_digest != ACCEPTANCE_FIXTURE_DIGEST:
        _fail("kit fixture digest does not match the frozen fixture")
    embedded = _read_small_file(
        resolved / PurePosixPath(_EMBEDDED_IDENTITY),
        "embedded runtime identity",
    )
    if embedded != identity_raw or embedded != identity_bytes(identity):
        _fail("embedded runtime identity does not match the external identity")
    lock_raw = _read_small_file(resolved / "PACKAGE-LOCK.json", "package lock")
    _verify_package_lock(lock_raw, identity)
    _verify_bootstrap_chain(resolved, identity_raw, manifest_raw)

    if not callable(runtime_probe):
        _fail("runtime probe is invalid")
    runtime_probe(resolved, identity)
    return VerifiedKit(
        source=source,
        source_kind=source_kind,
        archive_sha256=archive_sha256,
        identity=identity,
        manifest_entries=entries,
        member_count=(
            len(entries) + len(_BOOTSTRAP_FILES) + len(_MUTABLE_ROOTS) + 1
            if member_count is None
            else member_count
        ),
        runtime_verified=True,
    )


def _verify_sidecar(archive: Path, sidecar: Path) -> str:
    digest = _sha256_file(archive)
    sidecar_path = _plain_file(sidecar, "archive sidecar")
    try:
        raw = sidecar_path.read_bytes()
    except OSError as exc:
        raise KitVerificationError("archive sidecar cannot be read") from exc
    expected = f"{digest}  {archive.name}\n".encode("ascii")
    if raw != expected:
        _fail("archive sidecar does not match the ZIP digest and filename")
    return digest


def _validate_zip_inventory(
    archive: zipfile.ZipFile,
) -> tuple[str, tuple[zipfile.ZipInfo, ...]]:
    infos = tuple(archive.infolist())
    if not infos or len(infos) > _MAX_ARCHIVE_MEMBERS:
        _fail("ZIP member count is invalid")
    names = tuple(info.filename for info in infos)
    if names != tuple(sorted(names)):
        _fail("ZIP members are not sorted")
    if len(names) != len(set(names)):
        _fail("ZIP contains duplicate members")
    if len(names) != len({name.casefold() for name in names}):
        _fail("ZIP contains case-colliding members")
    first = names[0]
    if not first.endswith("/") or first.count("/") != 1:
        _fail("ZIP does not have one explicit root directory")
    root_name = first[:-1]
    if not _KIT_ROOT_RE.fullmatch(root_name):
        _fail("ZIP root name is invalid")

    mutable_directories: set[str] = set()
    directory_relatives: set[str] = set()
    file_relatives: set[str] = set()
    total = 0
    for info in infos:
        name = info.filename
        if not name.startswith(root_name + "/") or "\\" in name or "\x00" in name:
            _fail("ZIP member is outside the single root")
        if info.flag_bits & 0x1:
            _fail("ZIP contains an encrypted member")
        is_directory = name.endswith("/")
        relative = name[len(root_name) + 1 :].removesuffix("/")
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if name == first:
            if not is_directory or kind != stat.S_IFDIR:
                _fail("ZIP root entry is not a plain directory")
            continue
        try:
            ManifestEntry(relative, 0, "0" * 64)
        except KitContractError as exc:
            raise KitVerificationError("ZIP member path is unsafe") from exc
        if is_directory:
            if kind != stat.S_IFDIR or info.file_size != 0:
                _fail("ZIP directory entry is invalid")
            directory_relatives.add(relative)
            if relative in _MUTABLE_ROOTS:
                mutable_directories.add(relative)
            elif relative.split("/", 1)[0] in _MUTABLE_ROOTS:
                _fail("ZIP contains a preseeded mutable directory")
        else:
            if kind != stat.S_IFREG:
                _fail("ZIP member is not a regular file")
            top = relative.split("/", 1)[0]
            if top in _MUTABLE_ROOTS:
                _fail("ZIP contains mutable result content")
            _reject_contamination(relative)
            file_relatives.add(relative)
        total += info.file_size
        if total > _MAX_ARCHIVE_BYTES:
            _fail("ZIP uncompressed size exceeds the closed limit")
    if mutable_directories != set(_MUTABLE_ROOTS):
        _fail("ZIP mutable roots are missing")
    expected_directories = set(_required_directories(file_relatives)) | set(
        _MUTABLE_ROOTS
    )
    if directory_relatives != expected_directories:
        _fail("ZIP directory inventory is incomplete or unexpected")
    try:
        bad = archive.testzip()
    except (OSError, zipfile.BadZipFile, RuntimeError, zlib.error) as exc:
        raise KitVerificationError("ZIP CRC verification failed") from exc
    if bad is not None:
        _fail("ZIP CRC verification failed")
    return root_name, infos


def _extract_verified_zip(
    archive: zipfile.ZipFile,
    infos: tuple[zipfile.ZipInfo, ...],
    parent: Path,
) -> Path:
    root_name = infos[0].filename[:-1]
    for info in infos:
        relative = info.filename.removeprefix(root_name + "/").removesuffix("/")
        target = parent / root_name
        if relative:
            target = target / PurePosixPath(relative)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=False)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with archive.open(info, "r") as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
        except (OSError, zipfile.BadZipFile) as exc:
            raise KitVerificationError("ZIP member extraction failed") from exc
        if target.stat().st_size != info.file_size:
            _fail("extracted ZIP member size does not match")
    return parent / root_name


def verify_kit(
    source: Path,
    *,
    sidecar: Path | None = None,
    runtime_probe: RuntimeProbe = probe_runtime_identity,
) -> VerifiedKit:
    """Verify an extracted root or ZIP+sidecar before any release run can start."""

    candidate = Path(source).absolute()
    if candidate.is_dir():
        if sidecar is not None:
            _fail("an extracted kit does not accept an archive sidecar")
        return _verify_directory(
            candidate,
            source=candidate,
            source_kind="directory",
            archive_sha256=None,
            member_count=None,
            runtime_probe=runtime_probe,
        )
    archive_path = _plain_file(candidate, "kit ZIP")
    if archive_path.suffix.casefold() != ".zip" or sidecar is None:
        _fail("kit ZIP and explicit sidecar are required")
    archive_digest = _verify_sidecar(archive_path, Path(sidecar))
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            root_name, infos = _validate_zip_inventory(archive)
            if archive_path.name != f"{root_name}.zip":
                _fail("ZIP filename does not match its root identity")
            temporary_base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
            with tempfile.TemporaryDirectory(prefix="mrv-", dir=temporary_base) as raw:
                extracted = _extract_verified_zip(archive, infos, Path(raw))
                return _verify_directory(
                    extracted,
                    source=archive_path,
                    source_kind="zip",
                    archive_sha256=archive_digest,
                    member_count=len(infos),
                    runtime_probe=runtime_probe,
                )
    except KitVerificationError:
        raise
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise KitVerificationError("kit ZIP could not be verified") from exc


class _DuplicateResultKey(ValueError):
    pass


def _result_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateResultKey(key)
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"unsupported JSON constant: {value}")


def _invalid_result(reason_code: str) -> ReturnedRunVerification:
    return ReturnedRunVerification(
        status="invalid_run",
        reason_code=reason_code,
        evaluation=None,
        result=None,
        origin_authenticated=False,
    )


def _strict_result_mapping(raw: bytes) -> dict[str, object]:
    if (
        not isinstance(raw, bytes)
        or not raw
        or len(raw) > _MAX_TEXT_BYTES
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        raise ValueError("result JSON bytes are invalid")
    parsed = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_result_pairs,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError("result JSON must be an object")
    return parsed


def _execution_is_valid(result: Mapping[str, object]) -> bool:
    execution = result.get("execution_conditions")
    return isinstance(execution, Mapping) and dict(execution) == {
        "ac_power": True,
        "drive_type": "fixed",
        "is_internal": True,
        "is_regular_directory": True,
        "is_reparse_point": False,
        "is_synced_root": False,
        "release_protocol": True,
        "runtime_verified": True,
        "working_root_class": "local_application_owned",
    }


def verify_returned_result_bytes(
    identity: KitIdentity,
    *,
    json_name: str,
    result_bytes: bytes,
    sidecar_bytes: bytes,
    summary_bytes: bytes,
) -> ReturnedRunVerification:
    """Recompute a returned run without trusting its stored PASS or STOP."""

    if not isinstance(identity, KitIdentity):
        return _invalid_result("kit_binding_invalid")
    if (
        not isinstance(json_name, str)
        or not json_name.isascii()
        or "/" in json_name
        or "\\" in json_name
    ):
        return _invalid_result("result_file_set_invalid")
    if not isinstance(result_bytes, bytes) or not isinstance(sidecar_bytes, bytes):
        return _invalid_result("result_file_set_invalid")
    expected_sidecar = (
        f"{hashlib.sha256(result_bytes).hexdigest()}  {json_name}\n".encode("ascii")
    )
    if sidecar_bytes != expected_sidecar:
        return _invalid_result("result_sidecar_invalid")
    try:
        result = _strict_result_mapping(result_bytes)
        if canonical_result_bytes(result) != result_bytes:
            return _invalid_result("result_contract_invalid")
        if result_filename(result) != json_name:
            return _invalid_result("result_file_set_invalid")
    except (
        BenchmarkContractError,
        _DuplicateResultKey,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
    ):
        return _invalid_result("result_contract_invalid")

    fixture = result.get("fixture")
    if (
        result.get("schema_id") != identity.result_schema_id
        or result.get("schema_version") != identity.result_schema_version
        or result.get("source_commit") != identity.source_commit
        or result.get("kit_identity_digest") != sha256_bytes(identity_bytes(identity))
        or result.get("protocol_digest") != identity.protocol_digest
        or not isinstance(fixture, Mapping)
        or fixture.get("fixture_digest") != identity.fixture_digest
        or result.get("recorded_at_utc") is None
    ):
        return _invalid_result("kit_binding_invalid")
    if not _execution_is_valid(result):
        return _invalid_result("execution_conditions_invalid")
    try:
        verify_summary_bytes(result, summary_bytes)
        evaluation = evaluate_result(result)
    except BenchmarkContractError:
        return _invalid_result("summary_invalid")
    return ReturnedRunVerification(
        status=("valid_pass" if evaluation.disposition == "pass" else "valid_stop"),
        reason_code=None,
        evaluation=evaluation,
        result=MappingProxyType(result),
        origin_authenticated=False,
    )


def verify_returned_result(
    identity: KitIdentity,
    *,
    json_path: Path,
    sidecar_path: Path,
    summary_path: Path,
) -> ReturnedRunVerification:
    """Read and verify the exact three files returned from the target PC."""

    try:
        json_file = _plain_file(Path(json_path), "result JSON")
        sidecar_file = _plain_file(Path(sidecar_path), "result sidecar")
        summary_file = _plain_file(Path(summary_path), "Korean summary")
        expected_sidecar_name = f"{json_file.name}.sha256"
        expected_summary_name = f"{json_file.stem}.summary-ko.txt"
        if (
            sidecar_file.name != expected_sidecar_name
            or summary_file.name != expected_summary_name
            or len({json_file.parent, sidecar_file.parent, summary_file.parent}) != 1
        ):
            return _invalid_result("result_file_set_invalid")
        result_raw = _read_small_file(json_file, "result JSON")
        sidecar_raw = _read_small_file(sidecar_file, "result sidecar")
        summary_raw = _read_small_file(summary_file, "Korean summary")
    except KitVerificationError:
        return _invalid_result("result_file_set_invalid")
    return verify_returned_result_bytes(
        identity,
        json_name=json_file.name,
        result_bytes=result_raw,
        sidecar_bytes=sidecar_raw,
        summary_bytes=summary_raw,
    )
