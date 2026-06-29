from __future__ import annotations

import argparse
import json
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from modori.core import Dataset, Pipeline
from modori.steps import (
    CompareGroupsStep,
    ComposeScaleStep,
    ImportStep,
    RecodeReverseStep,
    ReliabilityStep,
    ReportStep,
)
from modori.table_io import FullReadLimits, read_full, read_preview


SURVEY_COLUMNS = ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "group"]
STRESS_OUTPUT_DIR = Path(".stress-matrix")


@dataclass(frozen=True)
class StressCase:
    name: str
    rows: int
    file_type: str


def generate_synthetic_survey_frame(rows: int) -> pd.DataFrame:
    if rows < 6:
        raise ValueError("Stress datasets require at least 6 rows")
    rng = random.Random(20260629 + rows)
    data: dict[str, list[int]] = {}
    for item_index in range(1, 9):
        data[f"q{item_index}"] = [rng.randint(1, 5) for _ in range(rows)]
    data["group"] = [1 if row_index % 2 == 0 else 2 for row_index in range(rows)]
    return pd.DataFrame(data, columns=SURVEY_COLUMNS)


def write_stress_dataset(output_dir: Path, case: StressCase) -> Path:
    frame = generate_synthetic_survey_frame(case.rows)
    path = output_dir / f"survey-{case.rows}.{case.file_type}"
    if case.file_type == "csv":
        frame.to_csv(path, index=False)
    elif case.file_type == "xlsx":
        frame.to_excel(path, index=False)
    else:
        raise ValueError(f"Unsupported stress file type: {case.file_type}")
    return path


def run_stress_matrix(
    *,
    output_dir: Path,
    cases: Sequence[StressCase],
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for case in cases:
        path = write_stress_dataset(output_dir, case)
        results.extend(
            [
                _measure_case_operation(
                    case,
                    "preview",
                    f"read_preview({path.name})",
                    lambda path=path, case=case: read_preview(path, case.file_type),
                ),
                _measure_case_operation(
                    case,
                    "full_import",
                    f"read_full({path.name})",
                    lambda path=path, case=case: read_full(
                        path,
                        case.file_type,
                        limits=FullReadLimits(
                            max_rows=case.rows,
                            max_columns=len(SURVEY_COLUMNS),
                            max_cells=case.rows * len(SURVEY_COLUMNS),
                        ),
                    ),
                ),
                _measure_case_operation(
                    case,
                    "analysis",
                    f"reference_pipeline_analysis({path.name})",
                    lambda path=path, case=case: _run_analysis(path, case.file_type),
                ),
                _measure_case_operation(
                    case,
                    "report_export",
                    f"reference_pipeline_report({path.name})",
                    lambda path=path, case=case, output_dir=output_dir: _run_report_export(
                        path,
                        case.file_type,
                        output_dir / f"report-{case.name}",
                    ),
                ),
            ]
        )
    return results


def _measure_case_operation(
    case: StressCase,
    operation: str,
    command: str,
    func,
) -> dict[str, Any]:
    started = time.perf_counter()
    status = "pass"
    message = ""
    try:
        func()
    except Exception as exc:  # pragma: no cover - exercised through CLI failures.
        status = "fail"
        message = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - started
    return {
        "dataset": case.name,
        "file_type": case.file_type,
        "rows": case.rows,
        "columns": len(SURVEY_COLUMNS),
        "operation": operation,
        "command": command,
        "elapsed_seconds": round(elapsed, 6),
        "status": status,
        "message": message,
    }


def _analysis_pipeline(path: Path, file_type: str) -> Pipeline:
    items = ["q1", "q2", "q3_R", "q4", "q5", "q6", "q7_R", "q8"]
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import stress data",
            params={"path": str(path), "file_type": file_type},
        )
    )
    pipeline.add(
        RecodeReverseStep(
            id="reverse-negative-items",
            title="Reverse-code negative items",
            params={"columns": ["q3", "q7"], "scale_min": 1, "scale_max": 5},
        )
    )
    pipeline.add(
        ComposeScaleStep(
            id="compose-job-sat",
            title="Compose job satisfaction",
            params={
                "items": items,
                "method": "mean",
                "name": "job_sat",
                "missing_policy": {"preset": "survey", "min_valid": 0.8},
            },
        )
    )
    pipeline.add(
        ReliabilityStep(
            id="reliability-job-sat",
            title="Reliability",
            params={"items": items, "scale_name": "job_sat"},
        )
    )
    pipeline.add(
        CompareGroupsStep(
            id="compare-groups",
            title="Compare groups",
            params={
                "dv": "job_sat",
                "group": "group",
                "routing_policy": {"preset": "modern"},
            },
        )
    )
    return pipeline


def _run_analysis(path: Path, file_type: str) -> Pipeline:
    pipeline = _analysis_pipeline(path, file_type)
    pipeline.recompute(dirty_from=None)
    return pipeline


def _run_report_export(path: Path, file_type: str, output_dir: Path) -> Path:
    pipeline = _run_analysis(path, file_type)
    pipeline.add(
        ReportStep(
            id="report",
            title="APA report",
            params={
                "include": ["reliability:job_sat", "comparison:job_sat:group"],
                "output_dir": str(output_dir),
                "filename": "report.docx",
                "language": "ko",
            },
        )
    )
    pipeline.recompute(dirty_from="report")
    report_path = output_dir / "report.docx"
    if not report_path.exists():
        raise RuntimeError(f"Report was not created: {report_path}")
    return report_path


def _parse_rows(value: str) -> list[int]:
    rows = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not rows:
        raise argparse.ArgumentTypeError("At least one row count is required")
    return rows


def _parse_formats(value: str) -> list[str]:
    formats = [item.strip().lower() for item in value.split(",") if item.strip()]
    unsupported = sorted(set(formats) - {"csv", "xlsx"})
    if unsupported:
        raise argparse.ArgumentTypeError(f"Unsupported formats: {unsupported}")
    if not formats:
        raise argparse.ArgumentTypeError("At least one format is required")
    return formats


def _cases(rows: Sequence[int], formats: Sequence[str]) -> list[StressCase]:
    return [
        StressCase(name=f"{file_type}-{row_count}", rows=row_count, file_type=file_type)
        for row_count in rows
        for file_type in formats
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic local import/analysis/report stress checks."
    )
    parser.add_argument("--output-dir", type=Path, default=STRESS_OUTPUT_DIR)
    parser.add_argument("--rows", type=_parse_rows, default=[50, 500])
    parser.add_argument("--formats", type=_parse_formats, default=["csv", "xlsx"])
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    results = run_stress_matrix(
        output_dir=args.output_dir,
        cases=_cases(args.rows, args.formats),
    )
    text = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if all(result["status"] == "pass" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
