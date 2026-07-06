from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modori.table_io import TableReadError, read_preview


@dataclass(frozen=True)
class PublicDataSmokeCase:
    name: str
    file_name: str
    file_type: str
    columns: tuple[str, ...] = ()
    sample_rows: tuple[dict[str, Any], ...] = ()
    header_row_index: int | None = None
    header_row_count: int | None = None
    data_start_row_index: int | None = None
    confidence: str | None = None
    required_warnings: tuple[str, ...] = ()
    drop_aggregate_rows: bool = False
    expected_error: str | None = None


PUBLIC_DATA_SMOKE_CASES: tuple[PublicDataSmokeCase, ...] = (
    PublicDataSmokeCase(
        name="kosis-two-row-csv",
        file_name="kosis-two-row.csv",
        file_type="csv",
        columns=(
            "행정구역별(1)",
            "특성별(1)",
            "특성별(2)",
            "2025 계 (%)",
            "2025 매우 만족",
            "2025 약간 만족",
        ),
        sample_rows=(
            {
                "행정구역별(1)": "전국",
                "특성별(1)": "전체",
                "특성별(2)": "계",
                "2025 계 (%)": 100.0,
                "2025 매우 만족": 11.5,
                "2025 약간 만족": 27.9,
            },
        ),
        header_row_index=0,
        header_row_count=2,
        data_start_row_index=2,
        confidence="high",
        required_warnings=("다중 헤더 2행을 하나의 열 이름으로 합쳤습니다.",),
    ),
    PublicDataSmokeCase(
        name="molit-deep-preamble-csv",
        file_name="molit-deep-preamble.csv",
        file_type="csv",
        columns=("시군구", "번지", "거래금액"),
        sample_rows=({"시군구": "서울특별시 종로구", "번지": "1-1", "거래금액": 100000},),
        header_row_index=15,
        header_row_count=1,
        data_start_row_index=16,
        confidence="medium",
        required_warnings=("표 헤더 앞의 안내 행 15개를 건너뛰었습니다.",),
    ),
    PublicDataSmokeCase(
        name="weather-text-xls",
        file_name="weather-text-xls.xls",
        file_type="xls",
        columns=("지점", "지점명", "일시", "기온(°C)"),
        sample_rows=({"지점": 108, "지점명": "서울", "일시": "2026-07-06 01:00", "기온(°C)": 25.1},),
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        confidence="high",
        required_warnings=("XLS 확장자이지만 텍스트 표로 읽었습니다.",),
    ),
    PublicDataSmokeCase(
        name="merged-public-header-xlsx",
        file_name="merged-public-header.xlsx",
        file_type="xlsx",
        columns=(
            "순번",
            "기준연도",
            "학과",
            "재학생(A) 계 정원내",
            "재학생(A) 계 정원외",
            "재학생(A) 남 정원내",
            "재학생(A) 남 정원외",
        ),
        sample_rows=(
            {
                "순번": "합 계",
                "기준연도": None,
                "학과": None,
                "재학생(A) 계 정원내": 3240,
                "재학생(A) 계 정원외": 743,
                "재학생(A) 남 정원내": 1667,
                "재학생(A) 남 정원외": 417,
            },
        ),
        header_row_index=3,
        header_row_count=3,
        data_start_row_index=6,
        confidence="high",
        required_warnings=(
            "표 헤더 앞의 안내 행 3개를 건너뛰었습니다.",
            "다중 헤더 3행을 하나의 열 이름으로 합쳤습니다.",
            "집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다.",
        ),
    ),
    PublicDataSmokeCase(
        name="aggregate-row-warn",
        file_name="aggregate-row.csv",
        file_type="csv",
        columns=("지역", "인구"),
        sample_rows=({"지역": "합 계", "인구": 300},),
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        confidence="high",
        required_warnings=("집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다.",),
    ),
    PublicDataSmokeCase(
        name="aggregate-row-drop",
        file_name="aggregate-row.csv",
        file_type="csv",
        columns=("지역", "인구"),
        sample_rows=({"지역": "종로구", "인구": 100}, {"지역": "중구", "인구": 200}),
        header_row_index=0,
        header_row_count=1,
        data_start_row_index=1,
        confidence="high",
        required_warnings=("집계/합계 행 1개를 제외했습니다.",),
        drop_aggregate_rows=True,
    ),
    PublicDataSmokeCase(
        name="notice-only-xlsx-reject",
        file_name="notice-only.xlsx",
        file_type="xlsx",
        expected_error="표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요.",
    ),
)


def run_public_data_import_smoke(fixture_dir: Path, output_path: Path) -> int:
    payload = public_data_import_smoke_payload(fixture_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return 0 if payload["ok"] is True else 1


def public_data_import_smoke_payload(fixture_dir: Path) -> dict[str, Any]:
    cases = [_run_case(fixture_dir, case) for case in PUBLIC_DATA_SMOKE_CASES]
    return {
        "ok": all(case["ok"] for case in cases),
        "fixture_dir": str(fixture_dir),
        "case_count": len(cases),
        "cases": cases,
    }


def _run_case(fixture_dir: Path, case: PublicDataSmokeCase) -> dict[str, Any]:
    path = fixture_dir / case.file_name
    try:
        preview = read_preview(
            path,
            case.file_type,
            drop_aggregate_rows=case.drop_aggregate_rows,
        )
    except TableReadError as exc:
        ok = case.expected_error == exc.message_ko
        return {
            "name": case.name,
            "ok": ok,
            "status": "expected_reject" if ok else "unexpected_reject",
            "file_name": case.file_name,
            "error": exc.message_ko,
        }
    except Exception as exc:
        return {
            "name": case.name,
            "ok": False,
            "status": "exception",
            "file_name": case.file_name,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if case.expected_error is not None:
        return {
            "name": case.name,
            "ok": False,
            "status": "unexpected_success",
            "file_name": case.file_name,
            "columns": list(preview.columns),
        }
    failures = _preview_contract_failures(preview, case)
    report = preview.inference_report
    return {
        "name": case.name,
        "ok": not failures,
        "status": "preview_ok" if not failures else "contract_mismatch",
        "file_name": case.file_name,
        "columns": list(preview.columns),
        "sample_rows": list(preview.sample_rows[: len(case.sample_rows)]),
        "warnings": list(preview.warnings),
        "inference": None
        if report is None
        else {
            "header_row_index": report.header_row_index,
            "header_row_count": report.header_row_count,
            "data_start_row_index": report.data_start_row_index,
            "confidence": report.confidence,
        },
        "failures": failures,
    }


def _preview_contract_failures(
    preview: Any,
    case: PublicDataSmokeCase,
) -> list[str]:
    failures: list[str] = []
    if tuple(preview.columns) != case.columns:
        failures.append(f"columns mismatch: {tuple(preview.columns)!r}")
    actual_rows = tuple(preview.sample_rows[: len(case.sample_rows)])
    if actual_rows != case.sample_rows:
        failures.append(f"sample rows mismatch: {actual_rows!r}")
    for warning in case.required_warnings:
        if warning not in preview.warnings:
            failures.append(f"missing warning: {warning}")
    report = preview.inference_report
    if report is None:
        failures.append("missing inference report")
    else:
        if report.header_row_index != case.header_row_index:
            failures.append(f"header_row_index mismatch: {report.header_row_index!r}")
        if report.header_row_count != case.header_row_count:
            failures.append(f"header_row_count mismatch: {report.header_row_count!r}")
        if report.data_start_row_index != case.data_start_row_index:
            failures.append(f"data_start_row_index mismatch: {report.data_start_row_index!r}")
        if report.confidence != case.confidence:
            failures.append(f"confidence mismatch: {report.confidence!r}")
    return failures
