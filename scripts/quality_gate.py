from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

if __package__:
    from scripts.package_environment import without_workspace_reference_runtime
else:
    from package_environment import without_workspace_reference_runtime


def quality_commands(
    *,
    include_pip_audit: bool = False,
    include_package_check: bool = False,
    include_package_build: bool = False,
    include_installer_check: bool = False,
    include_installer_build: bool = False,
    include_installed_smoke: bool = False,
    include_packaged_launch: bool = False,
    include_slow_stats: bool = False,
) -> list[list[str]]:
    if include_installed_smoke and not include_installer_build:
        raise ValueError("Installed smoke requires installer build")
    if include_package_build and include_installer_build:
        raise ValueError("Installer build already rebuilds the package")

    commands = [
        ["-m", "compileall", "-q", "src", "tests", "scripts"],
        ["-m", "ruff", "check", "src", "tests", "scripts"],
        ["-m", "bandit", "-q", "-r", "src"],
        ["scripts/launch_smoke.py"],
        ["-m", "pytest", "-q", "-p", "no:cacheprovider"],
        ["-m", "pip", "check"],
    ]
    if include_package_check:
        commands.append(["scripts/package_windows.py", "--check"])
    if include_installer_check:
        commands.append(["scripts/build_installer.py", "--check"])
    if include_package_build:
        commands.append(["scripts/package_windows.py"])
    if include_installer_build:
        installer_command = ["scripts/build_installer.py"]
        if include_installed_smoke:
            installer_command.append("--with-installed-smoke")
        else:
            installer_command.append("--staging-only")
        commands.append(installer_command)
    if include_packaged_launch:
        commands.append(["scripts/package_launch_smoke.py"])
        commands.append(["scripts/package_engine_smoke.py"])
        commands.append(["scripts/package_public_data_smoke.py"])
    if include_slow_stats:
        commands.append(["scripts/slow_stats_gate.py"])
    if include_pip_audit:
        commands.append(
            [
                "-m",
                "pip_audit",
                "--local",
                "--cache-dir",
                ".pip-audit-cache",
                "--progress-spinner",
                "off",
            ]
        )
    return commands


def reference_environment() -> dict[str, str]:
    env = _with_workspace_source(os.environ)
    rscript = env.get("MODORI_RSCRIPT")
    if not rscript:
        local_rscript = Path(".tools") / "r-env" / "Scripts" / "Rscript.exe"
        if local_rscript.exists():
            rscript = str(local_rscript.resolve())
    if rscript:
        rscript = str(Path(rscript).resolve())
        env["MODORI_RSCRIPT"] = rscript
        prefix = Path(rscript).parents[1]
        r_paths = [
            prefix / "Library" / "bin",
            prefix / "Scripts",
            prefix / "lib" / "R" / "bin",
            prefix / "lib" / "R" / "bin" / "x64",
        ]
        env["PATH"] = (
            os.pathsep.join(str(path) for path in r_paths)
            + os.pathsep
            + env.get(
                "PATH",
                "",
            )
        )
    return env


def _with_workspace_source(source: Mapping[str, str]) -> dict[str, str]:
    env = dict(source)
    workspace_src = str((Path(__file__).resolve().parents[1] / "src").resolve())
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        workspace_src
        if not existing_pythonpath
        else os.pathsep.join((workspace_src, existing_pythonpath))
    )
    return env


def environment_for_command(
    command: Sequence[str],
    *,
    base_environment: dict[str, str],
    reference_environment: dict[str, str],
) -> dict[str, str]:
    needs_reference_runtime = list(command[:2]) == ["-m", "pytest"] or list(
        command[:1]
    ) == ["scripts/slow_stats_gate.py"]
    selected = reference_environment if needs_reference_runtime else base_environment
    return dict(selected)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run TongTong's local dependency and static-analysis gate."
    )
    parser.add_argument(
        "--with-pip-audit",
        action="store_true",
        help="Also run pip-audit. This may contact external advisory services.",
    )
    parser.add_argument(
        "--with-package-check",
        action="store_true",
        help="Also verify that the Windows packaging toolchain is installed.",
    )
    parser.add_argument(
        "--with-package-build",
        action="store_true",
        help="Also build the Windows desktop package. This is slow.",
    )
    parser.add_argument(
        "--with-installer-check",
        action="store_true",
        help="Also verify that the Inno Setup installer toolchain is installed.",
    )
    parser.add_argument(
        "--with-installer-build",
        action="store_true",
        help="Also build the internal Windows installer. This rebuilds the package.",
    )
    parser.add_argument(
        "--with-installed-smoke",
        action="store_true",
        help="Also run installed lifecycle smoke with the installer build.",
    )
    parser.add_argument(
        "--with-packaged-launch",
        action="store_true",
        help="Also smoke-test the packaged executable in offscreen mode.",
    )
    parser.add_argument(
        "--with-slow-stats",
        action="store_true",
        help="Also run slow statistical adequacy checks.",
    )
    args = parser.parse_args(argv)
    base_env = _with_workspace_source(without_workspace_reference_runtime())
    reference_env = reference_environment()

    for command in quality_commands(
        include_pip_audit=args.with_pip_audit,
        include_package_check=args.with_package_check,
        include_package_build=args.with_package_build,
        include_installer_check=args.with_installer_check,
        include_installer_build=args.with_installer_build,
        include_installed_smoke=args.with_installed_smoke,
        include_packaged_launch=args.with_packaged_launch,
        include_slow_stats=args.with_slow_stats,
    ):
        display = " ".join([sys.executable, *command])
        print(f"$ {display}", flush=True)
        command_env = environment_for_command(
            command,
            base_environment=base_env,
            reference_environment=reference_env,
        )
        completed = subprocess.run(
            [sys.executable, *command],
            check=False,
            env=command_env,
        )
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
