from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata
import os
import platform
import subprocess
import sys
import uuid
import winreg
from collections.abc import Mapping, Sequence
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
        write_checksum_file,
        write_manifest,
    )

WORKSPACE = Path(__file__).resolve().parents[1]
INNO_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"


@dataclass(frozen=True)
class BuildOptions:
    staging_only: bool = False
    with_installed_smoke: bool = False


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


def read_inno_version() -> str:
    access = winreg.KEY_READ | winreg.KEY_WOW64_32KEY
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, INNO_REGISTRY_KEY, 0, access) as key:
        value, _kind = winreg.QueryValueEx(key, "DisplayVersion")
    version = str(value).strip()
    if not version:
        raise ValueError("Inno Setup DisplayVersion is empty")
    return version


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
        script=WORKSPACE / "installer" / "modori.iss",
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


def package_commands() -> list[list[str]]:
    return [
        [sys.executable, "scripts/package_windows.py"],
        [sys.executable, "scripts/package_launch_smoke.py"],
        [sys.executable, "scripts/package_engine_smoke.py"],
        [sys.executable, "scripts/package_public_data_smoke.py"],
    ]


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
    identity = source_identity(staging_only=options.staging_only)
    compiler = find_iscc()
    tools = {
        "inno_setup": read_inno_version(),
        "pyinstaller": importlib.metadata.version("pyinstaller"),
        "python": platform.python_version(),
    }
    staging = (
        WORKSPACE
        / ".tmp"
        / "installer-build"
        / f"{identity.build_identity}-{uuid.uuid4().hex}"
    )
    staging.mkdir(parents=True)

    for command in package_commands():
        run_required(command, runner)

    package_root = WORKSPACE / "dist" / "Modori"
    check_payload(package_root)
    path_evidence = measure_payload_paths(package_root)
    package_evidence = FileEvidence.from_path(
        "dist/Modori/Modori.exe",
        package_root / "Modori.exe",
    )
    installer_script_path = WORKSPACE / "installer" / "modori.iss"
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
            identity=identity,
            app_id=SMOKE_APP_ID,
            app_name="Modori Installer Smoke",
            package_root=package_root,
            output_dir=smoke_output,
            output_base_filename=smoke_name,
            allow_custom_dir=True,
            runner=runner,
        )
        probe_payload = staging / "downgrade-probe-payload"
        probe_payload.mkdir(parents=True)
        (probe_payload / "Modori.exe").write_bytes(
            b"downgrade probe must never install"
        )
        probe_output = staging / "downgrade-probe-output"
        probe_output.mkdir(parents=True)
        probe_installer = compile_installer(
            compiler=compiler,
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

    production_output = staging / "production-output"
    production_output.mkdir(parents=True)
    setup_base_name = f"Modori-Setup-{identity.build_identity}"
    production_installer = compile_installer(
        compiler=compiler,
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        app_name="Modori",
        package_root=package_root,
        output_dir=production_output,
        output_base_filename=setup_base_name,
        allow_custom_dir=False,
        runner=runner,
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
            version = read_inno_version()
            check_payload()
        except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
            print(f"installer-check-failed: {exc}", file=sys.stderr)
            return 2
        print(f"installer-tool-ok: Inno Setup {version}: {compiler}")
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
