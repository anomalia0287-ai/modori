from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def package_launch_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    cache_dir = Path(".tmp") / "packaged-launch-cache"
    settings_path = Path(".tmp") / "packaged-launch-settings.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    env["MODORI_CACHE_DIR"] = str(cache_dir.resolve())
    env["MODORI_SETTINGS_PATH"] = str(settings_path.resolve())
    return env


def run_launch_smoke(
    executable: str | Path,
    *,
    timeout_seconds: float = 8.0,
    working_directory: str | Path = "C:/Users/V/Desktop",
) -> int:
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2

    smoke_dir = Path(".tmp") / "packaged-launch-smoke"
    output_path = smoke_dir / "result.json"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)
    command = [str(exe_path), "--launch-smoke", output_path.resolve()]
    try:
        completed = subprocess.run(
            command,
            check=False,
            cwd=str(Path(working_directory).resolve()),
            env=package_launch_environment(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        print("Packaged launch smoke timed out.", file=sys.stderr)
        return 1
    if completed.returncode != 0:
        print(
            f"Packaged launch smoke exited with code: {completed.returncode}",
            file=sys.stderr,
        )
        return completed.returncode

    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Packaged launch smoke did not write valid JSON: {exc}", file=sys.stderr)
        return 1
    if payload.get("ok") is not True or int(payload.get("root_objects", 0)) < 1:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print("package-launch-smoke-ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the packaged Modori executable.")
    parser.add_argument(
        "executable",
        nargs="?",
        default=str(Path("dist") / "Modori" / "Modori.exe"),
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--working-directory", default="C:/Users/V/Desktop")
    args = parser.parse_args(argv)

    return run_launch_smoke(
        args.executable,
        timeout_seconds=args.timeout,
        working_directory=args.working_directory,
    )


if __name__ == "__main__":
    raise SystemExit(main())
