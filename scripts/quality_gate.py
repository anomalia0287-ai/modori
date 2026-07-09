from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def quality_commands(
    *,
    include_pip_audit: bool = False,
    include_package_check: bool = False,
    include_package_build: bool = False,
    include_packaged_launch: bool = False,
    include_slow_stats: bool = False,
) -> list[list[str]]:
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
    if include_package_build:
        commands.append(["scripts/package_windows.py"])
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
    env = os.environ.copy()
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
        env["PATH"] = os.pathsep.join(str(path) for path in r_paths) + os.pathsep + env.get(
            "PATH",
            "",
        )
    return env


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
    env = reference_environment()

    for command in quality_commands(
        include_pip_audit=args.with_pip_audit,
        include_package_check=args.with_package_check,
        include_package_build=args.with_package_build,
        include_packaged_launch=args.with_packaged_launch,
        include_slow_stats=args.with_slow_stats,
    ):
        display = " ".join([sys.executable, *command])
        print(f"$ {display}", flush=True)
        completed = subprocess.run([sys.executable, *command], check=False, env=env)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
