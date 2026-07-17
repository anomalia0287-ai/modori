from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

if __package__:
    from scripts.package_environment import (
        ExplicitDirectoryBoundary,
        packaged_subprocess_environment,
    )
    from scripts.package_smoke_contract import public_data_payload_has_contract
else:
    from package_environment import (  # type: ignore[import-not-found]
        ExplicitDirectoryBoundary,
        packaged_subprocess_environment,
    )
    from package_smoke_contract import (  # type: ignore[import-not-found]
        public_data_payload_has_contract,
    )


def run_public_data_smoke(
    executable: str | Path,
    *,
    fixture_dir: str | Path = Path("tests") / "fixtures" / "public_data_formats",
    timeout_seconds: float = 60.0,
    state_root: str | Path | None = None,
    evidence_dir: str | Path | None = None,
) -> int:
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2
    fixture_path = Path(fixture_dir).resolve()
    if not fixture_path.is_dir():
        print(
            f"Public data smoke fixture directory does not exist: {fixture_path}",
            file=sys.stderr,
        )
        return 2

    evidence_boundary = (
        None
        if evidence_dir is None
        else ExplicitDirectoryBoundary.capture(evidence_dir)
    )
    smoke_dir = (
        Path(".tmp") / "packaged-public-data-smoke"
        if evidence_boundary is None
        else evidence_boundary.lexical_directory
    )
    output_path = smoke_dir / "result.json"
    if evidence_boundary is None:
        smoke_dir.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)
        subprocess_output_path = output_path
    else:
        evidence_boundary.require_empty()
        subprocess_output_path = smoke_dir / f".result-{uuid.uuid4().hex}.json"
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
    completed = subprocess.run(
        [
            str(exe_path),
            "--public-data-smoke",
            str(fixture_path),
            str(
                subprocess_output_path.resolve()
                if evidence_boundary is None
                else subprocess_output_path
            ),
        ],
        check=False,
        timeout=timeout_seconds,
        env=packaged_subprocess_environment(
            "packaged-public-data-runtime",
            state_root=state_root,
        ),
    )
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
    if completed.returncode != 0:
        return completed.returncode
    if evidence_boundary is not None:
        evidence_boundary.require_regular_child(subprocess_output_path)
    elif not subprocess_output_path.is_file():
        print(
            "Packaged public-data smoke did not produce a fresh result",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(subprocess_output_path.read_text(encoding="utf-8"))
    if not public_data_payload_has_contract(payload):
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
        subprocess_output_path.rename(output_path)
        evidence_boundary.require_regular_child(output_path)
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
    parser.add_argument("--state-root")
    parser.add_argument("--evidence-dir")
    args = parser.parse_args(argv)

    return run_public_data_smoke(
        args.executable,
        fixture_dir=args.fixture_dir,
        timeout_seconds=args.timeout,
        state_root=args.state_root,
        evidence_dir=args.evidence_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
