from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

if __package__:
    from scripts.package_environment import packaged_subprocess_environment
else:
    from package_environment import packaged_subprocess_environment


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
) -> int:
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2

    smoke_dir = Path(".tmp") / "packaged-engine-smoke"
    data_path = smoke_dir / "reference.xlsx"
    output_path = smoke_dir / "result.json"
    write_reference_xlsx(data_path)
    output_path.unlink(missing_ok=True)
    completed = subprocess.run(
        [
            str(exe_path),
            "--engine-smoke",
            str(data_path.resolve()),
            str(output_path.resolve()),
        ],
        check=False,
        timeout=timeout_seconds,
        env=packaged_subprocess_environment("packaged-engine-runtime"),
    )
    if completed.returncode != 0:
        return completed.returncode
    if not output_path.is_file():
        print("Packaged engine smoke did not produce a fresh result", file=sys.stderr)
        return 1

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    v1_statistics_smoke = payload.get("v1_statistics_smoke")
    checks = (
        v1_statistics_smoke.get("checks")
        if isinstance(v1_statistics_smoke, dict)
        else None
    )
    logistic_ok = isinstance(checks, list) and any(
        isinstance(check, dict)
        and check.get("key") == "logistic_regression"
        and check.get("ok") is True
        and check.get("analysis_type") == "LogisticRegressionResult"
        for check in checks
    )
    if (
        payload.get("ok") is not True
        or payload.get("opened") is not True
        or payload.get("rerun") is not True
        or payload.get("waited") is not True
        or payload.get("status") != "ready"
        or not isinstance(v1_statistics_smoke, dict)
        or v1_statistics_smoke.get("ok") is not True
        or not logistic_ok
    ):
        if not logistic_ok:
            print(
                "Missing or failed logistic_regression packaged smoke evidence",
                file=sys.stderr,
            )
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
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
    args = parser.parse_args(argv)

    return run_engine_smoke(args.executable, timeout_seconds=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
