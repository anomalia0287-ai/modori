from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def run_public_data_smoke(
    executable: str | Path,
    *,
    fixture_dir: str | Path = Path("tests") / "fixtures" / "public_data_formats",
    timeout_seconds: float = 60.0,
) -> int:
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2
    fixture_path = Path(fixture_dir).resolve()
    if not fixture_path.is_dir():
        print(f"Public data smoke fixture directory does not exist: {fixture_path}", file=sys.stderr)
        return 2

    smoke_dir = Path(".tmp") / "packaged-public-data-smoke"
    output_path = smoke_dir / "result.json"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(exe_path),
            "--public-data-smoke",
            str(fixture_path),
            str(output_path.resolve()),
        ],
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        return completed.returncode

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if payload.get("ok") is not True or payload.get("case_count") != 7:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print("package-public-data-smoke-ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test packaged Modori against public-data import contracts."
    )
    parser.add_argument(
        "executable",
        nargs="?",
        default=str(Path("dist") / "Modori" / "Modori.exe"),
    )
    parser.add_argument(
        "--fixture-dir",
        default=str(Path("tests") / "fixtures" / "public_data_formats"),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    return run_public_data_smoke(
        args.executable,
        fixture_dir=args.fixture_dir,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
