from __future__ import annotations

import argparse
import os
import subprocess
import sys
import winreg
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.installer_contract import (
        SourceIdentity,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
    )
else:
    from installer_contract import (
        SourceIdentity,
        make_source_identity,
        measure_payload_paths,
        read_project_version,
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
) -> list[str]:
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
        str(script.resolve()),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the internal Modori Windows installer.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--staging-only", action="store_true")
    parser.add_argument("--with-installed-smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        identity = source_identity(staging_only=args.staging_only)
        compiler = find_iscc()
        version = read_inno_version()
        if args.check:
            check_payload()
    except (FileNotFoundError, KeyError, OSError, RuntimeError, ValueError) as exc:
        print(f"installer-check-failed: {exc}", file=sys.stderr)
        return 2
    print(f"installer-tool-ok: Inno Setup {version}: {compiler}")
    print(f"installer-source: {identity.git_commit}")
    if args.check:
        return 0
    parser.error("This preflight revision requires --check; build orchestration lands in Task 4")


if __name__ == "__main__":
    raise SystemExit(main())
