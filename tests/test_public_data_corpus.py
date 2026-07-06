from __future__ import annotations

from pathlib import Path

import pytest

from modori.table_io import TableReadError, read_preview


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "public_data_formats"


PUBLIC_DATA_CORPUS_CASES = (
    pytest.param(
        {
            "file_name": "kosis-two-row.csv",
            "file_type": "csv",
            "columns": (
                "행정구역별(1)",
                "특성별(1)",
                "특성별(2)",
                "2025 계 (%)",
                "2025 매우 만족",
                "2025 약간 만족",
            ),
            "header_row_index": 0,
            "header_row_count": 2,
            "data_start_row_index": 2,
            "confidence": "high",
            "reasons": ("다중 헤더 2행을 하나의 열 이름으로 합쳤습니다.",),
        },
        id="kosis-two-row-csv",
    ),
    pytest.param(
        {
            "file_name": "molit-deep-preamble.csv",
            "file_type": "csv",
            "columns": ("시군구", "번지", "거래금액"),
            "header_row_index": 15,
            "header_row_count": 1,
            "data_start_row_index": 16,
            "confidence": "medium",
            "reasons": ("표 헤더 앞의 안내 행 15개를 건너뛰었습니다.",),
        },
        id="molit-deep-preamble-csv",
    ),
    pytest.param(
        {
            "file_name": "weather-text-xls.xls",
            "file_type": "xls",
            "columns": ("지점", "지점명", "일시", "기온(°C)"),
            "header_row_index": 0,
            "header_row_count": 1,
            "data_start_row_index": 1,
            "confidence": "high",
            "reasons": ("XLS 확장자이지만 텍스트 표로 읽었습니다.",),
        },
        id="weather-text-xls",
    ),
    pytest.param(
        {
            "file_name": "merged-public-header.xlsx",
            "file_type": "xlsx",
            "columns": (
                "순번",
                "기준연도",
                "학과",
                "재학생(A) 계 정원내",
                "재학생(A) 계 정원외",
                "재학생(A) 남 정원내",
                "재학생(A) 남 정원외",
            ),
            "header_row_index": 3,
            "header_row_count": 3,
            "data_start_row_index": 6,
            "confidence": "high",
            "reasons": (
                "표 헤더 앞의 안내 행 3개를 건너뛰었습니다.",
                "다중 헤더 3행을 하나의 열 이름으로 합쳤습니다.",
            ),
        },
        id="merged-public-header-xlsx",
    ),
)


@pytest.mark.parametrize("case", PUBLIC_DATA_CORPUS_CASES)
def test_checked_in_public_data_corpus_matches_inference_contract(
    case: dict[str, object],
) -> None:
    path = FIXTURE_DIR / str(case["file_name"])

    result = read_preview(path, str(case["file_type"]))

    assert result.columns == case["columns"]
    report = result.inference_report
    assert report is not None
    assert report.file_type == case["file_type"]
    assert report.header_row_index == case["header_row_index"]
    assert report.header_row_count == case["header_row_count"]
    assert report.data_start_row_index == case["data_start_row_index"]
    assert report.column_count == len(case["columns"])
    assert report.confidence == case["confidence"]
    assert report.requires_user_confirmation is False
    for reason in case["reasons"]:
        assert reason in report.reasons


def test_checked_in_public_data_corpus_rejects_notice_only_xlsx() -> None:
    path = FIXTURE_DIR / "notice-only.xlsx"

    with pytest.raises(TableReadError) as exc_info:
        read_preview(path, "xlsx")

    assert exc_info.value.message_ko == (
        "표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요."
    )
