from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from modori.path_policy import is_link_or_junction

if __package__:
    from scripts.package_environment import (
        ExplicitDirectoryBoundary,
        packaged_subprocess_environment,
    )
    from scripts.package_smoke_contract import engine_payload_has_contract
else:
    from package_environment import (  # type: ignore[import-not-found]
        ExplicitDirectoryBoundary,
        packaged_subprocess_environment,
    )
    from package_smoke_contract import (  # type: ignore[import-not-found]
        engine_payload_has_contract,
    )


GROUP1_SCORES = [
    [3, 2, 3, 2, 4, 4, 4, 4],
    [3, 2, 4, 2, 4, 4, 2, 4],
    [3, 3, 2, 3, 2, 2, 2, 2],
    [4, 3, 4, 2, 3, 4, 4, 3],
    [3, 3, 3, 4, 3, 2, 4, 2],
    [3, 3, 2, 3, 4, 3, 3, 3],
    [4, 4, 2, 4, 3, 4, 4, 3],
    [3, 3, 2, 4, 2, 3, 4, 3],
    [4, 2, 4, 2, 3, 4, 3, 3],
    [3, 2, 3, 3, 4, 3, 3, 4],
]
GROUP2_SCORES = [
    [4, 4, 5, 3, 4, 4, 4, 5],
    [4, 4, 5, 3, 4, 4, 4, 3],
    [5, 4, 4, 5, 4, 4, 5, 5],
    [4, 3, 5, 5, 4, 4, 3, 4],
    [4, 5, 5, 4, 5, 3, 5, 5],
    [3, 5, 4, 3, 4, 3, 4, 4],
    [3, 4, 4, 3, 5, 4, 4, 3],
    [4, 5, 4, 5, 4, 5, 4, 4],
    [3, 3, 3, 3, 4, 5, 3, 5],
    [4, 4, 4, 5, 4, 3, 4, 4],
]


def write_reference_xlsx(path: Path) -> None:
    rows: list[list[int]] = []
    for group, group_rows in [(1, GROUP1_SCORES), (2, GROUP2_SCORES)]:
        for scores in group_rows:
            raw = list(scores)
            raw[2] = 6 - raw[2]
            raw[6] = 6 - raw[6]
            rows.append([*raw, group])
    frame = pd.DataFrame(
        rows, columns=[f"q{index}" for index in range(1, 9)] + ["group"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(path, index=False, sheet_name="Responses")


def run_engine_smoke(
    executable: str | Path,
    *,
    timeout_seconds: float = 60.0,
    state_root: str | Path | None = None,
    evidence_dir: str | Path | None = None,
) -> int:
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2

    evidence_boundary = (
        None
        if evidence_dir is None
        else ExplicitDirectoryBoundary.capture(evidence_dir)
    )
    smoke_dir = (
        Path(".tmp") / "packaged-engine-smoke"
        if evidence_boundary is None
        else evidence_boundary.lexical_directory
    )
    if evidence_boundary is not None:
        evidence_boundary.require_empty()
    data_path = smoke_dir / "reference.xlsx"
    output_path = smoke_dir / "result.json"
    runtime_input_boundary: ExplicitDirectoryBoundary | None = None
    if evidence_boundary is None:
        write_reference_xlsx(data_path)
        output_path.unlink(missing_ok=True)
        subprocess_output_path = output_path
        subprocess_data_path = data_path
    else:
        if state_root is None:
            raise ValueError(
                "Explicit engine evidence requires an explicit runtime state root"
            )
        token = uuid.uuid4().hex
        transient_data_path = smoke_dir / f".reference-{token}.xlsx"
        subprocess_output_path = smoke_dir / f".result-{token}.json"
        evidence_boundary.revalidate()
        write_reference_xlsx(transient_data_path)
        evidence_boundary.require_regular_child(transient_data_path)
        transient_data_path.rename(data_path)
        evidence_boundary.require_regular_child(data_path)
        state_boundary = ExplicitDirectoryBoundary.capture(state_root)
        runtime_input_boundary = state_boundary.create_direct_child(
            f"engine-smoke-input-{token}"
        )
        subprocess_data_path = (
            runtime_input_boundary.lexical_directory / "reference.xlsx"
        )
        shutil.copyfile(data_path, subprocess_data_path)
        runtime_input_boundary.require_regular_child(subprocess_data_path)
    environment = packaged_subprocess_environment(
        "packaged-engine-runtime",
        state_root=state_root,
    )
    expected_cache_path = Path(environment["MODORI_CACHE_DIR"])
    expected_cache_dir = expected_cache_path.resolve()
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
        assert runtime_input_boundary is not None
        runtime_input_boundary.revalidate()
    completed = subprocess.run(
        [
            str(exe_path),
            "--engine-smoke",
            str(
                subprocess_data_path.resolve()
                if evidence_boundary is None
                else subprocess_data_path
            ),
            str(
                subprocess_output_path.resolve()
                if evidence_boundary is None
                else subprocess_output_path
            ),
        ],
        check=False,
        timeout=timeout_seconds,
        env=environment,
    )
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
        assert runtime_input_boundary is not None
        runtime_input_boundary.revalidate()
    if completed.returncode != 0:
        return completed.returncode
    if evidence_boundary is not None:
        evidence_boundary.require_regular_child(subprocess_output_path)
    elif not subprocess_output_path.is_file():
        print("Packaged engine smoke did not produce a fresh result", file=sys.stderr)
        return 1

    payload = json.loads(subprocess_output_path.read_text(encoding="utf-8"))
    if (
        not engine_payload_has_contract(
            payload,
            expected_cache_dir=expected_cache_dir,
        )
        or is_link_or_junction(expected_cache_path)
        or not expected_cache_path.is_dir()
    ):
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    if evidence_boundary is not None:
        evidence_boundary.revalidate()
        subprocess_output_path.rename(output_path)
        evidence_boundary.require_regular_child(output_path)
    print("package-engine-smoke-ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test the packaged Modori engine path."
    )
    parser.add_argument(
        "executable",
        nargs="?",
        default=str(Path("dist") / "Modori" / "Modori.exe"),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--state-root")
    parser.add_argument("--evidence-dir")
    args = parser.parse_args(argv)

    return run_engine_smoke(
        args.executable,
        timeout_seconds=args.timeout,
        state_root=args.state_root,
        evidence_dir=args.evidence_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
