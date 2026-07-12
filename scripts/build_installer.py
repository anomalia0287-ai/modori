from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import importlib.metadata
import os
import platform
import shutil
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


def inventory_tree(root: Path) -> TreeInventory:
    selected_root = root.resolve()
    if not selected_root.is_dir():
        raise ValueError(f"Tree root does not exist: {selected_root}")
    entries = sorted(
        selected_root.rglob("*"),
        key=lambda path: path.relative_to(selected_root).as_posix(),
    )
    directories: list[str] = []
    files: list[TreeFile] = []
    for path in entries:
        relative = path.relative_to(selected_root).as_posix()
        if path.is_symlink():
            raise ValueError(f"Tree contains a symbolic link: {path}")
        if path.is_dir():
            directories.append(relative)
            continue
        if not path.is_file():
            raise ValueError(f"Tree contains an unsupported entry: {path}")
        content = file_content_digest(path)
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


def freeze_release_inputs(
    *,
    source_package: Path,
    source_script: Path,
    staging: Path,
    tree_copier: Callable[[Path, Path], object] = shutil.copytree,
    file_copier: Callable[[Path, Path], object] = shutil.copyfile,
) -> FrozenReleaseInputs:
    package_before = inventory_tree(source_package)
    script_before = file_content_digest(source_script)
    snapshot = staging / "snapshot"
    snapshot.mkdir()
    snapshot_package = snapshot / "package"
    snapshot_script = snapshot / "modori.iss"
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


def read_tool_versions(compiler: Path) -> dict[str, str]:
    try:
        pyinstaller_version = importlib.metadata.version("pyinstaller")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("PyInstaller distribution is not installed") from exc
    python_version = platform.python_version().strip()
    if not python_version:
        raise RuntimeError("Python version metadata is empty")
    inno = read_inno_version(compiler)
    return {
        **inno.manifest_tools(),
        "pyinstaller": pyinstaller_version,
        "python": python_version,
    }


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
    compiler: Path,
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
        compiler=compiler,
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
    run_required(command, runner)
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


def build_release(
    options: BuildOptions,
    *,
    runner=run_command,
) -> Path:
    if not options.staging_only and not options.with_installed_smoke:
        raise ValueError(
            "Installer publication requires successful installed lifecycle smoke"
        )
    identity = source_identity(staging_only=options.staging_only)
    compiler = find_iscc()
    tools = read_tool_versions(compiler)
    staging = (
        WORKSPACE
        / ".tmp"
        / "installer-build"
        / f"{identity.build_identity}-{uuid.uuid4().hex}"
    )
    staging.mkdir(parents=True)

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
        smoke_output = staging / "smoke-output"
        smoke_output.mkdir(parents=True)
        smoke_name = f"Modori-Installer-Smoke-{identity.build_identity}"
        smoke_installer = compile_installer(
            compiler=compiler,
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
        probe_output = staging / "downgrade-probe-output"
        probe_output.mkdir(parents=True)
        probe_installer = compile_installer(
            compiler=compiler,
            installer_script=installer_script_path,
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=package_root,
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

    production_output = staging / "production-output"
    production_output.mkdir(parents=True)
    setup_base_name = f"Modori-Setup-{identity.build_identity}"
    production_installer = compile_installer(
        compiler=compiler,
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
    require_release_inputs_unchanged(
        identity=identity,
        staging_only=options.staging_only,
        live_package=live_package_root,
        live_script=live_installer_script,
        frozen=frozen,
    )
    candidate = staging / "candidate"
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
            tools = read_tool_versions(compiler)
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
