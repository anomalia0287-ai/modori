from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__:
    from scripts.package_environment import packaged_subprocess_environment
else:
    from package_environment import packaged_subprocess_environment


_REQUIRED_HARDENED_CASE_NAMES = frozenset(
    {
        "kosis-two-row-csv",
        "kosis-two-row-drop",
        "cp949-public-csv",
        "notice-only-xlsx-reject",
    }
)


def run_public_data_smoke(
    executable: str | Path,
    *,
    fixture_dir: str | Path = Path("tests") / "fixtures" / "public_data_formats",
    timeout_seconds: float = 60.0,
    state_root: str | Path | None = None,
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
    output_path.unlink(missing_ok=True)
    completed = subprocess.run(
        [
            str(exe_path),
            "--public-data-smoke",
            str(fixture_path),
            str(output_path.resolve()),
        ],
        check=False,
        timeout=timeout_seconds,
        env=packaged_subprocess_environment(
            "packaged-public-data-runtime",
            state_root=state_root,
        ),
    )
    if completed.returncode != 0:
        return completed.returncode
    if not output_path.is_file():
        print(
            "Packaged public-data smoke did not produce a fresh result",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    case_count = payload.get("case_count")
    if not _payload_has_hardened_contracts(payload, cases, case_count):
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print("package-public-data-smoke-ok")
    return 0


def _payload_has_hardened_contracts(
    payload: dict[str, object],
    cases: object,
    case_count: object,
) -> bool:
    if payload.get("ok") is not True:
        return False
    if not isinstance(cases, list) or not cases or case_count != len(cases):
        return False
    if any(not isinstance(case, dict) or case.get("ok") is not True for case in cases):
        return False
    names = {str(case.get("name")) for case in cases}
    if not _REQUIRED_HARDENED_CASE_NAMES.issubset(names):
        return False
    by_name = {str(case.get("name")): case for case in cases}
    if not _has_warning(by_name["kosis-two-row-csv"], "집계/합계 행 1개를 감지했습니다."):
        return False
    if _full_import_sample_contains(by_name["kosis-two-row-drop"], "행정구역별(1)", "전국"):
        return False
    if not _has_full_import_warning(by_name["cp949-public-csv"], "CSV 인코딩: cp949"):
        return False
    for case in cases:
        if case.get("status") == "expected_reject":
            if not case.get("preview_error") or not case.get("full_import_error"):
                return False
            continue
        if not isinstance(case.get("full_import"), dict):
            return False
    return True


def _has_warning(case: dict[str, object], expected: str) -> bool:
    warnings = case.get("warnings")
    if not isinstance(warnings, list):
        return False
    return any(expected in str(warning) for warning in warnings)


def _has_full_import_warning(case: dict[str, object], expected: str) -> bool:
    full_import = case.get("full_import")
    if not isinstance(full_import, dict):
        return False
    warnings = full_import.get("warnings")
    if not isinstance(warnings, list):
        return False
    return any(expected in str(warning) for warning in warnings)


def _full_import_sample_contains(case: dict[str, object], column: str, value: object) -> bool:
    full_import = case.get("full_import")
    if not isinstance(full_import, dict):
        return False
    sample_rows = full_import.get("sample_rows")
    if not isinstance(sample_rows, list):
        return False
    return any(
        isinstance(row, dict) and row.get(column) == value
        for row in sample_rows
    )


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
    args = parser.parse_args(argv)

    return run_public_data_smoke(
        args.executable,
        fixture_dir=args.fixture_dir,
        timeout_seconds=args.timeout,
        state_root=args.state_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
