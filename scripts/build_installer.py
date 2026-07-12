from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import importlib.metadata
import os
import platform
import shutil
import stat
import subprocess
import sys
import uuid
import winreg
from collections.abc import Callable, Mapping, Sequence
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        PRODUCTION_APP_ID,
        SMOKE_APP_ID,
        FileEvidence,
        SourceIdentity,
        build_manifest,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
        sha256_file,
        write_checksum_file,
        write_manifest,
    )
else:
    from installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        PRODUCTION_APP_ID,
        SMOKE_APP_ID,
        FileEvidence,
        SourceIdentity,
        build_manifest,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
        sha256_file,
        write_checksum_file,
        write_manifest,
    )

WORKSPACE = Path(__file__).resolve().parents[1]
INNO_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
COMPILER_SOURCE_PATH_BUDGET_UTF16_UNITS = 240
_VS_FIXEDFILEINFO_SIGNATURE = 0xFEEF04BD


class _VSFixedFileInfo(ctypes.Structure):
    _fields_ = [
        ("signature", wintypes.DWORD),
        ("structure_version", wintypes.DWORD),
        ("file_version_ms", wintypes.DWORD),
        ("file_version_ls", wintypes.DWORD),
        ("product_version_ms", wintypes.DWORD),
        ("product_version_ls", wintypes.DWORD),
        ("file_flags_mask", wintypes.DWORD),
        ("file_flags", wintypes.DWORD),
        ("file_os", wintypes.DWORD),
        ("file_type", wintypes.DWORD),
        ("file_subtype", wintypes.DWORD),
        ("file_date_ms", wintypes.DWORD),
        ("file_date_ls", wintypes.DWORD),
    ]


@dataclass(frozen=True)
class BuildOptions:
    staging_only: bool = False
    with_installed_smoke: bool = False


@dataclass(frozen=True)
class InnoToolchainEvidence:
    compiler: Path
    registered_version: str
    compiler_file_version: str
    compiler_sha256: str

    def manifest_tools(self) -> dict[str, str]:
        return {
            "inno_setup": self.registered_version,
            "inno_setup_compiler_file_version": self.compiler_file_version,
            "inno_setup_compiler_sha256": self.compiler_sha256,
        }


@dataclass(frozen=True)
class ToolchainEvidence:
    inno: InnoToolchainEvidence
    pyinstaller_version: str
    python_version: str

    def manifest_tools(self) -> dict[str, str]:
        return {
            **self.inno.manifest_tools(),
            "pyinstaller": self.pyinstaller_version,
            "python": self.python_version,
        }


@dataclass(frozen=True)
class TreeFile:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class TreeInventory:
    directories: tuple[str, ...]
    files: tuple[TreeFile, ...]
    digest: str

    @property
    def file_count(self) -> int:
        return len(self.files)


@dataclass(frozen=True)
class CompilerSourcePathEvidence:
    package_root: Path
    package_root_utf16_units: int
    longest_entry_kind: str
    longest_relative_path: str
    longest_relative_path_utf16_units: int
    relative_separator_utf16_units: int
    search_suffix: str
    search_suffix_utf16_units: int
    safe_path_budget_utf16_units: int
    computed_max_utf16_units: int


@dataclass(frozen=True)
class FileContentDigest:
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class FrozenReleaseInputs:
    package_root: Path
    installer_script: Path
    package_inventory: TreeInventory
    script_digest: FileContentDigest


def file_content_digest(path: Path) -> FileContentDigest:
    before = path.stat()
    digest = sha256_file(path)
    after = path.stat()
    before_signature = (
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        before.st_ino,
    )
    after_signature = (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
        after.st_ino,
    )
    if before_signature != after_signature:
        raise RuntimeError(f"File changed while hashing: {path}")
    return FileContentDigest(size_bytes=after.st_size, sha256=digest)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _is_reparse_point(metadata: os.stat_result) -> bool:
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_attribute
    )


def _tree_lstat(path: Path) -> os.stat_result:
    metadata = path.lstat()
    if _is_reparse_point(metadata):
        raise ValueError(f"Tree path contains a link or junction/reparse point: {path}")
    return metadata


def _require_resolved_inside(path: Path, resolved_root: Path) -> None:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"Tree entry resolves outside its lexical root: {path} -> {resolved}"
        ) from exc


def _validated_tree_root(root: Path) -> tuple[Path, Path]:
    boundary = _lexical_absolute(WORKSPACE)
    selected_root = _lexical_absolute(root)
    try:
        relative = selected_root.relative_to(boundary)
    except ValueError as exc:
        raise ValueError(
            f"Tree root is outside the workspace boundary: {selected_root}"
        ) from exc

    component = boundary
    boundary_metadata = _tree_lstat(component)
    if not stat.S_ISDIR(boundary_metadata.st_mode):
        raise ValueError(f"Workspace boundary is not a directory: {boundary}")
    for part in relative.parts:
        component /= part
        component_metadata = _tree_lstat(component)
        if not stat.S_ISDIR(component_metadata.st_mode):
            raise ValueError(f"Tree root component is not a directory: {component}")
    resolved_root = selected_root.resolve(strict=True)
    return selected_root, resolved_root


def _safe_tree_file_digest(path: Path, resolved_root: Path) -> FileContentDigest:
    before = _tree_lstat(path)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Tree entry is not a regular file: {path}")
    _require_resolved_inside(path, resolved_root)
    content = file_content_digest(path)
    after = _tree_lstat(path)
    before_signature = (
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
        before.st_ino,
        getattr(before, "st_file_attributes", 0),
    )
    after_signature = (
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
        after.st_ino,
        getattr(after, "st_file_attributes", 0),
    )
    if before_signature != after_signature:
        raise RuntimeError(f"Tree file changed while hashing: {path}")
    return content


def inventory_tree(root: Path) -> TreeInventory:
    selected_root, resolved_root = _validated_tree_root(root)
    pending = [selected_root]
    directory_paths: list[Path] = []
    file_paths: list[Path] = []
    while pending:
        directory = pending.pop()
        directory_metadata = _tree_lstat(directory)
        if not stat.S_ISDIR(directory_metadata.st_mode):
            raise ValueError(f"Tree entry is not a directory: {directory}")
        _require_resolved_inside(directory, resolved_root)
        with os.scandir(directory) as scanned:
            entries = sorted(scanned, key=lambda entry: entry.name)
        for entry in entries:
            path = directory / entry.name
            metadata = entry.stat(follow_symlinks=False)
            if _is_reparse_point(metadata):
                raise ValueError(
                    f"Tree path contains a link or junction/reparse point: {path}"
                )
            _require_resolved_inside(path, resolved_root)
            if stat.S_ISDIR(metadata.st_mode):
                directory_paths.append(path)
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                file_paths.append(path)
            else:
                raise ValueError(f"Tree contains an unsupported entry: {path}")

    directories = sorted(
        path.relative_to(selected_root).as_posix() for path in directory_paths
    )
    files: list[TreeFile] = []
    for path in sorted(
        file_paths,
        key=lambda item: item.relative_to(selected_root).as_posix(),
    ):
        relative = path.relative_to(selected_root).as_posix()
        content = _safe_tree_file_digest(path, resolved_root)
        files.append(
            TreeFile(
                relative_path=relative,
                size_bytes=content.size_bytes,
                sha256=content.sha256,
            )
        )
    digest = hashlib.sha256()
    for relative in directories:
        digest.update(b"directory\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\n")
    for file in files:
        digest.update(b"file\0")
        digest.update(file.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(file.size_bytes).encode("ascii"))
        digest.update(b"\0")
        digest.update(file.sha256.encode("ascii"))
        digest.update(b"\n")
    return TreeInventory(
        directories=tuple(directories),
        files=tuple(files),
        digest=digest.hexdigest().upper(),
    )


def windows_path_utf16_units(value: str | Path) -> int:
    try:
        encoded = str(value).encode("utf-16-le", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"Windows path is not valid UTF-16: {value!r}") from exc
    return len(encoded) // 2


def compiler_source_path_evidence(
    package_root: Path,
    inventory: TreeInventory,
    *,
    safe_path_budget_utf16_units: int = COMPILER_SOURCE_PATH_BUDGET_UTF16_UNITS,
) -> CompilerSourcePathEvidence:
    if not inventory.files:
        raise ValueError("Frozen package inventory contains no files")
    resolved_root = package_root.resolve()
    root_units = windows_path_utf16_units(resolved_root)
    candidates: list[tuple[int, str, str, int, int, str, int]] = [
        (root_units + 2, "root", "", 0, 0, "\\*", 2),
    ]
    for relative in inventory.directories:
        relative_units = windows_path_utf16_units(relative)
        candidates.append(
            (
                root_units + 1 + relative_units + 2,
                "directory",
                relative,
                relative_units,
                1,
                "\\*",
                2,
            )
        )
    for file in inventory.files:
        relative_units = windows_path_utf16_units(file.relative_path)
        candidates.append(
            (
                root_units + 1 + relative_units,
                "file",
                file.relative_path,
                relative_units,
                1,
                "",
                0,
            )
        )
    (
        computed,
        entry_kind,
        longest,
        longest_units,
        separator_units,
        suffix,
        suffix_units,
    ) = max(candidates, key=lambda item: (item[0], item[2], item[1]))
    return CompilerSourcePathEvidence(
        package_root=resolved_root,
        package_root_utf16_units=root_units,
        longest_entry_kind=entry_kind,
        longest_relative_path=longest,
        longest_relative_path_utf16_units=longest_units,
        relative_separator_utf16_units=separator_units,
        search_suffix=suffix,
        search_suffix_utf16_units=suffix_units,
        safe_path_budget_utf16_units=safe_path_budget_utf16_units,
        computed_max_utf16_units=computed,
    )


def require_compiler_source_path_budget(
    package_root: Path,
    inventory: TreeInventory,
    *,
    safe_path_budget_utf16_units: int = COMPILER_SOURCE_PATH_BUDGET_UTF16_UNITS,
) -> CompilerSourcePathEvidence:
    evidence = compiler_source_path_evidence(
        package_root,
        inventory,
        safe_path_budget_utf16_units=safe_path_budget_utf16_units,
    )
    if evidence.computed_max_utf16_units > evidence.safe_path_budget_utf16_units:
        source = str(evidence.package_root)
        if evidence.longest_relative_path:
            source += "\\" + evidence.longest_relative_path.replace("/", "\\")
        source += evidence.search_suffix
        raise ValueError(
            "Frozen compiler source path budget exceeded in UTF-16 code units: "
            f"{evidence.package_root_utf16_units} + "
            f"{evidence.relative_separator_utf16_units} + "
            f"{evidence.longest_relative_path_utf16_units} + "
            f"{evidence.search_suffix_utf16_units} = "
            f"{evidence.computed_max_utf16_units} > "
            f"{evidence.safe_path_budget_utf16_units} "
            f"({evidence.longest_entry_kind}): {source}"
        )
    return evidence


def copy_inventory_tree(
    source: Path,
    destination: Path,
    inventory: TreeInventory,
) -> None:
    source_root, resolved_root = _validated_tree_root(source)
    destination_root = _lexical_absolute(destination)
    destination_root.mkdir()
    for relative in inventory.directories:
        source_directory = source_root / Path(relative)
        metadata = _tree_lstat(source_directory)
        if not stat.S_ISDIR(metadata.st_mode):
            raise RuntimeError(
                f"Snapshot source directory changed before copy: {source_directory}"
            )
        _require_resolved_inside(source_directory, resolved_root)
        (destination_root / Path(relative)).mkdir(parents=True)
    for file in inventory.files:
        source_file = source_root / Path(file.relative_path)
        before = _tree_lstat(source_file)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"Snapshot source file changed before copy: {source_file}")
        _require_resolved_inside(source_file, resolved_root)
        destination_file = destination_root / Path(file.relative_path)
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_file, destination_file)
        after = _tree_lstat(source_file)
        if _is_reparse_point(after) or (
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_ino,
            getattr(before, "st_file_attributes", 0),
        ) != (
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_ino,
            getattr(after, "st_file_attributes", 0),
        ):
            raise RuntimeError(f"Snapshot source file changed during copy: {source_file}")


def freeze_release_inputs(
    *,
    source_package: Path,
    source_script: Path,
    staging: Path,
    tree_copier: Callable[[Path, Path], object] | None = None,
    file_copier: Callable[[Path, Path], object] = shutil.copyfile,
) -> FrozenReleaseInputs:
    package_before = inventory_tree(source_package)
    script_before = file_content_digest(source_script)
    snapshot = staging / "s"
    snapshot.mkdir()
    snapshot_package = snapshot / "p"
    snapshot_script = snapshot / "modori.iss"
    if tree_copier is None:
        copy_inventory_tree(source_package, snapshot_package, package_before)
    else:
        tree_copier(source_package, snapshot_package)
    file_copier(source_script, snapshot_script)

    package_after = inventory_tree(source_package)
    script_after = file_content_digest(source_script)
    if package_after != package_before:
        raise RuntimeError("Package source changed during snapshot")
    if script_after != script_before:
        raise RuntimeError("Installer script source changed during snapshot")

    copied_package = inventory_tree(snapshot_package)
    copied_script = file_content_digest(snapshot_script)
    if copied_package != package_before:
        raise RuntimeError("Package snapshot does not match its source inventory")
    if copied_script != script_before:
        raise RuntimeError("Installer script snapshot does not match its source digest")
    return FrozenReleaseInputs(
        package_root=snapshot_package.resolve(),
        installer_script=snapshot_script.resolve(),
        package_inventory=package_before,
        script_digest=script_before,
    )


def require_release_inputs_unchanged(
    *,
    identity: SourceIdentity,
    staging_only: bool,
    live_package: Path,
    live_script: Path,
    frozen: FrozenReleaseInputs,
    inno: InnoToolchainEvidence,
) -> None:
    try:
        current_identity = source_identity(staging_only=staging_only)
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(
            f"Release source HEAD/dirty identity drifted after snapshot: {exc}"
        ) from exc
    if current_identity != identity:
        raise RuntimeError(
            "Release source HEAD/dirty identity drifted after snapshot: "
            f"initial={identity.git_commit}/{identity.git_dirty}; "
            f"current={current_identity.git_commit}/{current_identity.git_dirty}"
        )
    current_frozen_package = inventory_tree(frozen.package_root)
    if current_frozen_package != frozen.package_inventory:
        raise RuntimeError(
            "Frozen package snapshot drifted after verification: "
            f"initial={frozen.package_inventory.digest}; "
            f"current={current_frozen_package.digest}"
        )
    current_frozen_script = file_content_digest(frozen.installer_script)
    if current_frozen_script != frozen.script_digest:
        raise RuntimeError(
            "Frozen installer script drifted after verification: "
            f"initial={frozen.script_digest.sha256}; "
            f"current={current_frozen_script.sha256}"
        )
    current_package = inventory_tree(live_package)
    if current_package != frozen.package_inventory:
        raise RuntimeError(
            "Live package tree drifted after snapshot: "
            f"initial={frozen.package_inventory.digest}; "
            f"current={current_package.digest}"
        )
    current_script = file_content_digest(live_script)
    if current_script != frozen.script_digest:
        raise RuntimeError(
            "Live installer script drifted after snapshot: "
            f"initial={frozen.script_digest.sha256}; "
            f"current={current_script.sha256}"
        )
    require_inno_toolchain_unchanged(inno)


def find_iscc(environment: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environment is None else environment
    candidates = [
        env.get("INNO_SETUP_COMPILER", ""),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for raw in candidates:
        if raw and Path(raw).is_file():
            return Path(raw).resolve()
    raise FileNotFoundError("Inno Setup 6 ISCC.exe was not found")


def _normalized_version(version: str, *, source: str) -> str:
    raw_components = version.strip().split(".")
    if not 3 <= len(raw_components) <= 4 or any(
        not component.isdigit() for component in raw_components
    ):
        raise ValueError(f"{source} version is not three or four numeric components")
    components = [int(component) for component in raw_components]
    while len(components) > 3 and components[-1] == 0:
        components.pop()
    return ".".join(str(component) for component in components)


def _fixed_file_version(version: str) -> str:
    raw_components = version.strip().split(".")
    if len(raw_components) != 4 or any(
        not component.isdigit() for component in raw_components
    ):
        raise ValueError(
            "Selected compiler Windows file version is not four numeric components"
        )
    return ".".join(str(int(component)) for component in raw_components)


def read_windows_file_version(executable: Path) -> str:
    selected = executable.resolve()
    if not selected.is_file():
        raise FileNotFoundError(f"Selected compiler is not a file: {selected}")
    version_api = ctypes.WinDLL("version", use_last_error=True)
    get_size = version_api.GetFileVersionInfoSizeW
    get_size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    get_size.restype = wintypes.DWORD
    ignored_handle = wintypes.DWORD()
    size = get_size(str(selected), ctypes.byref(ignored_handle))
    if size == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    buffer = ctypes.create_string_buffer(size)
    get_info = version_api.GetFileVersionInfoW
    get_info.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
    get_info.restype = wintypes.BOOL
    if not get_info(str(selected), 0, size, buffer):
        raise ctypes.WinError(ctypes.get_last_error())

    query_value = version_api.VerQueryValueW
    query_value.argtypes = [
        wintypes.LPCVOID,
        wintypes.LPCWSTR,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.UINT),
    ]
    query_value.restype = wintypes.BOOL
    fixed_pointer = wintypes.LPVOID()
    fixed_size = wintypes.UINT()
    if not query_value(buffer, "\\", ctypes.byref(fixed_pointer), ctypes.byref(fixed_size)):
        raise ctypes.WinError(ctypes.get_last_error())
    if fixed_size.value < ctypes.sizeof(_VSFixedFileInfo):
        raise ValueError(f"Selected compiler has truncated Windows version metadata: {selected}")
    fixed = ctypes.cast(
        fixed_pointer,
        ctypes.POINTER(_VSFixedFileInfo),
    ).contents
    if fixed.signature != _VS_FIXEDFILEINFO_SIGNATURE:
        raise ValueError(f"Selected compiler has invalid Windows version metadata: {selected}")
    components = (
        fixed.file_version_ms >> 16,
        fixed.file_version_ms & 0xFFFF,
        fixed.file_version_ls >> 16,
        fixed.file_version_ls & 0xFFFF,
    )
    return ".".join(str(component) for component in components)


def read_inno_version(compiler: Path) -> InnoToolchainEvidence:
    selected = compiler.resolve()
    access = winreg.KEY_READ | winreg.KEY_WOW64_32KEY
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, INNO_REGISTRY_KEY, 0, access) as key:
        registered_version_value, _kind = winreg.QueryValueEx(key, "DisplayVersion")
        install_location_value, _kind = winreg.QueryValueEx(key, "InstallLocation")
    registered_version = str(registered_version_value).strip()
    if not registered_version:
        raise ValueError("Inno Setup DisplayVersion is empty")
    install_location = str(install_location_value).strip()
    if not install_location:
        raise ValueError("Inno Setup InstallLocation is empty")
    registered_compiler = (Path(install_location) / "ISCC.exe").resolve()
    if os.path.normcase(str(selected)) != os.path.normcase(str(registered_compiler)):
        raise ValueError(
            "Selected compiler does not match registered Inno Setup path: "
            f"selected={selected}; registered={registered_compiler}"
        )
    try:
        compiler_before = file_content_digest(selected)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(f"Could not hash selected compiler: {selected}: {exc}") from exc
    try:
        file_version = _fixed_file_version(read_windows_file_version(selected))
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"Could not read selected compiler Windows file version: {selected}: {exc}"
        ) from exc
    normalized_registered = _normalized_version(
        registered_version,
        source="Registered Inno Setup",
    )
    try:
        compiler_after = file_content_digest(selected)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(f"Could not hash selected compiler: {selected}: {exc}") from exc
    if compiler_after != compiler_before:
        raise RuntimeError(
            "Selected compiler changed while binding toolchain evidence: "
            f"before={compiler_before.sha256}; after={compiler_after.sha256}"
        )
    compiler_sha256 = compiler_before.sha256
    if len(compiler_sha256) != 64 or any(
        character not in "0123456789ABCDEF" for character in compiler_sha256
    ):
        raise RuntimeError(f"Selected compiler SHA256 is invalid: {compiler_sha256}")
    return InnoToolchainEvidence(
        compiler=selected,
        registered_version=normalized_registered,
        compiler_file_version=file_version,
        compiler_sha256=compiler_sha256,
    )


def require_inno_toolchain_unchanged(expected: InnoToolchainEvidence) -> None:
    current = read_inno_version(expected.compiler)
    if current != expected:
        raise RuntimeError(
            "Selected compiler binding changed during installer build: "
            f"expected={expected}; current={current}"
        )


def read_tool_versions(compiler: Path) -> ToolchainEvidence:
    try:
        pyinstaller_version = importlib.metadata.version("pyinstaller")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("PyInstaller distribution is not installed") from exc
    python_version = platform.python_version().strip()
    if not python_version:
        raise RuntimeError("Python version metadata is empty")
    inno = read_inno_version(compiler)
    return ToolchainEvidence(
        inno=inno,
        pyinstaller_version=pyinstaller_version,
        python_version=python_version,
    )


def git_output(command: str, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", command, *arguments],
        cwd=WORKSPACE,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {command} failed")
    return completed.stdout.strip()


def source_identity(*, staging_only: bool) -> SourceIdentity:
    status = git_output("status", "--porcelain")
    dirty = bool(status)
    if dirty and not staging_only:
        raise ValueError(
            "Publishable installer build requires a clean Git worktree; "
            "current worktree is dirty"
        )
    version = read_project_version(WORKSPACE / "pyproject.toml")
    commit = git_output("rev-parse", "HEAD")
    return make_source_identity(version, commit, dirty=dirty)


def _require_safe_staging_directory(
    path: Path,
    resolved_workspace: Path,
) -> Path:
    selected = _lexical_absolute(path)
    metadata = _tree_lstat(selected)
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"Staging path is not a directory: {selected}")
    _require_resolved_inside(selected, resolved_workspace)
    return selected


def _create_or_validate_staging_directory(
    path: Path,
    resolved_workspace: Path,
) -> Path:
    selected = _lexical_absolute(path)
    try:
        selected.mkdir()
    except FileExistsError:
        pass
    return _require_safe_staging_directory(selected, resolved_workspace)


def create_release_staging(identity: SourceIdentity) -> Path:
    workspace = _lexical_absolute(WORKSPACE)
    workspace_metadata = _tree_lstat(workspace)
    if not stat.S_ISDIR(workspace_metadata.st_mode):
        raise ValueError(f"Workspace boundary is not a directory: {workspace}")
    resolved_workspace = workspace.resolve(strict=True)
    _require_safe_staging_directory(workspace, resolved_workspace)
    temp_root = _create_or_validate_staging_directory(
        workspace / ".tmp",
        resolved_workspace,
    )
    parent = _create_or_validate_staging_directory(
        temp_root / "ib",
        resolved_workspace,
    )
    for component in (workspace, temp_root, parent):
        _require_safe_staging_directory(component, resolved_workspace)
    run_name = f"{identity.git_commit[:12]}-{uuid.uuid4().hex[:12]}"
    staging = parent / run_name
    staging.mkdir()
    for component in (workspace, temp_root, parent, staging):
        _require_safe_staging_directory(component, resolved_workspace)
    return _lexical_absolute(staging)


def check_payload(root: Path = WORKSPACE / "dist" / "Modori") -> None:
    executable = root / "Modori.exe"
    qml = root / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    if not executable.is_file() or not qml.is_file():
        raise ValueError(f"Current package is incomplete: {root}")
    measure_payload_paths(root)


def build_iscc_command(
    *,
    compiler: Path,
    script: Path,
    app_id: str,
    app_name: str,
    version: str,
    windows_file_version: str,
    package_root: Path,
    output_dir: Path,
    output_base_filename: str,
    allow_custom_dir: bool,
) -> list[str]:
    if not isinstance(allow_custom_dir, bool):
        raise TypeError("allow_custom_dir must be a bool")
    return [
        str(compiler),
        "/Qp",
        f"/DAppIdValue={app_id.strip('{}')}",
        f"/DAppNameValue={app_name}",
        f"/DAppVersionValue={version}",
        f"/DWindowsFileVersionValue={windows_file_version}",
        f"/DPackageRoot={package_root.resolve()}",
        f"/DOutputDir={output_dir.resolve()}",
        f"/DOutputBaseFilename={output_base_filename}",
        f"/DAllowCustomDirValue={int(allow_custom_dir)}",
        str(script.resolve()),
    ]


def run_command(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=WORKSPACE, check=False)
    return completed.returncode


def run_required(command: list[str], runner=run_command) -> None:
    result = runner(command)
    if result != 0:
        raise RuntimeError(f"Command failed with exit code {result}: {' '.join(command)}")


def compile_installer(
    *,
    inno: InnoToolchainEvidence,
    installer_script: Path,
    identity: SourceIdentity,
    app_id: str,
    app_name: str,
    package_root: Path,
    output_dir: Path,
    output_base_filename: str,
    allow_custom_dir: bool,
    runner=run_command,
    version: str | None = None,
) -> Path:
    selected_version = identity.version if version is None else version
    command = build_iscc_command(
        compiler=inno.compiler,
        script=installer_script,
        app_id=app_id,
        app_name=app_name,
        version=selected_version,
        windows_file_version=f"{selected_version}.0",
        package_root=package_root,
        output_dir=output_dir,
        output_base_filename=output_base_filename,
        allow_custom_dir=allow_custom_dir,
    )
    require_inno_toolchain_unchanged(inno)
    try:
        result = runner(command)
    finally:
        require_inno_toolchain_unchanged(inno)
    if result != 0:
        raise RuntimeError(f"Command failed with exit code {result}: {' '.join(command)}")
    installers = sorted(output_dir.glob("*.exe"))
    expected = output_dir / f"{output_base_filename}.exe"
    if installers != [expected] or not expected.is_file():
        raise RuntimeError(f"ISCC did not create exactly the expected installer: {expected}")
    return expected


def package_build_command() -> list[str]:
    return [sys.executable, "scripts/package_windows.py"]


def package_smoke_commands(executable: Path) -> list[list[str]]:
    selected = str(executable.resolve())
    return [
        [sys.executable, "scripts/package_launch_smoke.py", selected],
        [sys.executable, "scripts/package_engine_smoke.py", selected],
        [sys.executable, "scripts/package_public_data_smoke.py", selected],
    ]


def package_commands(
    executable: Path | None = None,
) -> list[list[str]]:
    selected = (
        WORKSPACE / "dist" / "Modori" / "Modori.exe"
        if executable is None
        else executable
    )
    return [package_build_command(), *package_smoke_commands(selected)]


def publish_directory(staged: Path, final: Path) -> None:
    if final.exists():
        raise FileExistsError(f"Installer evidence directory already exists: {final}")
    final.parent.mkdir(parents=True, exist_ok=True)
    staged.replace(final)


def require_candidate_inventory(candidate: Path, installer_name: str) -> None:
    expected = {installer_name, "release-manifest.json", "SHA256SUMS.txt"}
    try:
        lexical_candidate, resolved_candidate = _validated_tree_root(candidate)
        with os.scandir(lexical_candidate) as scanned:
            entries = sorted(scanned, key=lambda entry: entry.name)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Installer candidate boundary is invalid: {exc}") from exc
    actual = {entry.name for entry in entries}
    if actual != expected:
        raise RuntimeError(
            "Installer candidate inventory mismatch: "
            f"expected={sorted(expected)}; actual={sorted(actual)}"
        )
    for entry in entries:
        path = lexical_candidate / entry.name
        metadata = entry.stat(follow_symlinks=False)
        if _is_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(
                "Installer candidate entry is not a regular non-reparse file: "
                f"{path}"
            )
        try:
            _require_resolved_inside(path, resolved_candidate)
        except ValueError as exc:
            raise RuntimeError(f"Installer candidate entry is invalid: {exc}") from exc


def build_release(
    options: BuildOptions,
    *,
    runner=run_command,
    compiler_source_path_budget_utf16_units: int = (
        COMPILER_SOURCE_PATH_BUDGET_UTF16_UNITS
    ),
) -> Path:
    if not options.staging_only and not options.with_installed_smoke:
        raise ValueError(
            "Installer publication requires successful installed lifecycle smoke"
        )
    identity = source_identity(staging_only=options.staging_only)
    compiler = find_iscc()
    toolchain = read_tool_versions(compiler)
    tools = toolchain.manifest_tools()
    staging = create_release_staging(identity)

    run_required(package_build_command(), runner)

    live_package_root = WORKSPACE / "dist" / "Modori"
    live_installer_script = WORKSPACE / "installer" / "modori.iss"
    frozen = freeze_release_inputs(
        source_package=live_package_root,
        source_script=live_installer_script,
        staging=staging,
    )
    package_root = frozen.package_root
    installer_script_path = frozen.installer_script
    require_compiler_source_path_budget(
        package_root,
        frozen.package_inventory,
        safe_path_budget_utf16_units=compiler_source_path_budget_utf16_units,
    )
    check_payload(package_root)
    for command in package_smoke_commands(package_root / "Modori.exe"):
        run_required(command, runner)

    path_evidence = measure_payload_paths(package_root)
    package_evidence = FileEvidence.from_path(
        "dist/Modori/Modori.exe",
        package_root / "Modori.exe",
    )
    script_evidence = FileEvidence.from_path(
        "installer/modori.iss",
        installer_script_path,
    )

    installed_lifecycle_smoke = False
    if options.with_installed_smoke:
        smoke_output = staging / "so"
        smoke_output.mkdir(parents=True)
        smoke_name = f"Modori-Installer-Smoke-{identity.build_identity}"
        smoke_installer = compile_installer(
            inno=toolchain.inno,
            installer_script=installer_script_path,
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=package_root,
            output_dir=smoke_output,
            output_base_filename=smoke_name,
            allow_custom_dir=True,
            runner=runner,
        )
        probe_payload = staging / "dp"
        probe_payload.mkdir(parents=True)
        (probe_payload / "Modori.exe").write_bytes(
            b"downgrade probe must never install"
        )
        probe_output = staging / "do"
        probe_output.mkdir(parents=True)
        probe_installer = compile_installer(
            inno=toolchain.inno,
            installer_script=installer_script_path,
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=probe_payload,
            output_dir=probe_output,
            output_base_filename="Modori-Installer-Smoke-Downgrade-0.0.9",
            allow_custom_dir=True,
            runner=runner,
            version=DOWNGRADE_PROBE_VERSION,
        )
        smoke_manifest_path = staging / "smoke-manifest.json"
        smoke_manifest = build_manifest(
            identity=identity,
            app_id=SMOKE_APP_ID,
            channel="internal-smoke",
            smoke_only=True,
            tools=tools,
            package_executable=package_evidence,
            installer=FileEvidence.from_path(smoke_installer.name, smoke_installer),
            installer_script=script_evidence,
            payload_paths=path_evidence,
            installed_lifecycle_smoke=False,
            installed_lifecycle_app_id=None,
            built_at=dt.datetime.now().astimezone().isoformat(),
            downgrade_probe=FileEvidence.from_path(
                probe_installer.name,
                probe_installer,
            ),
        )
        write_manifest(smoke_manifest_path, smoke_manifest)
        run_required(
            [
                sys.executable,
                "scripts/installer_smoke.py",
                str(smoke_installer),
                "--manifest",
                str(smoke_manifest_path),
                "--downgrade-probe",
                str(probe_installer),
            ],
            runner,
        )
        installed_lifecycle_smoke = True

    production_output = staging / "po"
    production_output.mkdir(parents=True)
    setup_base_name = f"Modori-Setup-{identity.build_identity}"
    production_installer = compile_installer(
        inno=toolchain.inno,
        installer_script=installer_script_path,
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        app_name="Modori",
        package_root=package_root,
        output_dir=production_output,
        output_base_filename=setup_base_name,
        allow_custom_dir=False,
        runner=runner,
    )
    candidate = staging / "c"
    candidate.mkdir()
    final_installer = candidate / production_installer.name
    production_installer.replace(final_installer)
    # Future signing belongs here, before the installer bytes are hashed.
    manifest = build_manifest(
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        channel="internal",
        smoke_only=False,
        tools=tools,
        package_executable=package_evidence,
        installer=FileEvidence.from_path(final_installer.name, final_installer),
        installer_script=script_evidence,
        payload_paths=path_evidence,
        installed_lifecycle_smoke=installed_lifecycle_smoke,
        installed_lifecycle_app_id=(
            SMOKE_APP_ID if installed_lifecycle_smoke else None
        ),
        built_at=dt.datetime.now().astimezone().isoformat(),
    )
    write_manifest(candidate / "release-manifest.json", manifest)
    write_checksum_file(
        candidate / "SHA256SUMS.txt",
        FileEvidence.from_path(final_installer.name, final_installer),
    )
    require_candidate_inventory(candidate, final_installer.name)
    require_release_inputs_unchanged(
        identity=identity,
        staging_only=options.staging_only,
        live_package=live_package_root,
        live_script=live_installer_script,
        frozen=frozen,
        inno=toolchain.inno,
    )
    if options.staging_only:
        return candidate
    final = WORKSPACE / "dist" / "installer" / identity.build_identity
    publish_directory(candidate, final)
    return final


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the internal Modori Windows installer.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--staging-only", action="store_true")
    parser.add_argument("--with-installed-smoke", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        try:
            identity = source_identity(staging_only=args.staging_only)
            compiler = find_iscc()
            toolchain = read_tool_versions(compiler)
            tools = toolchain.manifest_tools()
            check_payload()
        except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
            print(f"installer-check-failed: {exc}", file=sys.stderr)
            return 2
        print(
            "installer-tool-ok: Inno Setup registered "
            f"{tools['inno_setup']}: {compiler}"
        )
        print(
            "installer-tool-ok: ISCC.exe Windows file version "
            f"{tools['inno_setup_compiler_file_version']}"
        )
        print(
            "installer-tool-ok: ISCC.exe SHA256 "
            f"{tools['inno_setup_compiler_sha256']}"
        )
        print(f"installer-tool-ok: PyInstaller {tools['pyinstaller']}")
        print(f"installer-tool-ok: Python {tools['python']}")
        print(f"installer-source: {identity.git_commit}")
        return 0
    try:
        result_path = build_release(
            BuildOptions(
                staging_only=args.staging_only,
                with_installed_smoke=args.with_installed_smoke,
            )
        )
    except (FileExistsError, FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"installer-build-failed: {exc}", file=sys.stderr)
        return 1
    print(f"installer-build-ok: {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
