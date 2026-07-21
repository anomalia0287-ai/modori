from __future__ import annotations

import json
from pathlib import Path


FIXTURE_DIR = Path("tests/fixtures/public_data_formats")


def test_public_data_import_smoke_payload_checks_nontrivial_contracts() -> None:
    from modori.public_data_smoke import (
        PUBLIC_DATA_SMOKE_CASES,
        public_data_import_smoke_payload,
    )

    payload = public_data_import_smoke_payload(FIXTURE_DIR)

    assert payload["ok"] is True
    assert payload["case_count"] == len(PUBLIC_DATA_SMOKE_CASES)
    cases = {case["name"]: case for case in payload["cases"]}
    assert cases["kosis-two-row-csv"]["inference"] == {
        "confidence": "high",
        "data_start_row_index": 2,
        "header_row_count": 2,
        "header_row_index": 0,
    }
    assert cases["kosis-two-row-csv"]["columns"][3:] == [
        "2025 계 (%)",
        "2025 매우 만족",
        "2025 약간 만족",
    ]
    assert "집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다." in (
        cases["kosis-two-row-csv"]["warnings"]
    )
    assert cases["kosis-two-row-drop"]["full_import"]["sample_rows"] == [
        {
            "행정구역별(1)": "서울특별시",
            "특성별(1)": "전체",
            "특성별(2)": "계",
            "2025 계 (%)": 100.0,
            "2025 매우 만족": 11.0,
            "2025 약간 만족": 30.3,
        }
    ]
    assert cases["molit-deep-preamble-csv"]["inference"]["header_row_index"] == 15
    assert cases["weather-text-xls"]["sample_rows"][0]["기온(°C)"] == 25.1
    assert cases["merged-public-header-xlsx"]["sample_rows"][0]["순번"] == "합 계"
    assert "집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다." in (
        cases["aggregate-row-warn"]["warnings"]
    )
    assert cases["aggregate-row-drop"]["sample_rows"] == [
        {"지역": "종로구", "인구": 100},
        {"지역": "중구", "인구": 200},
    ]
    assert cases["cp949-public-csv"]["full_import"] == {
        "row_count": 2,
        "columns": ["자치구", "연도", "인구"],
        "sample_rows": [
            {"자치구": "종로구", "연도": 2024, "인구": 140000},
            {"자치구": "중구", "연도": 2024, "인구": 120000},
        ],
        "warnings": ["CSV 인코딩: cp949"],
    }
    assert cases["notice-only-xlsx-reject"]["status"] == "expected_reject"
    assert cases["notice-only-xlsx-reject"]["preview_error"] == (
        "표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요."
    )
    assert cases["notice-only-xlsx-reject"]["full_import_error"] == (
        "표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요."
    )


def test_public_data_import_smoke_success_cases_include_full_import_contracts() -> None:
    from modori.public_data_smoke import public_data_import_smoke_payload

    payload = public_data_import_smoke_payload(FIXTURE_DIR)

    for case in payload["cases"]:
        if case["status"] == "expected_reject":
            continue
        assert "full_import" in case, case["name"]
        assert case["full_import"]["columns"] == case["columns"]
        assert case["full_import"]["sample_rows"][: len(case["sample_rows"])] == case["sample_rows"]


def test_public_data_smoke_includes_selected_column_contract() -> None:
    from modori.public_data_smoke import public_data_import_smoke_payload

    payload = public_data_import_smoke_payload(FIXTURE_DIR)
    selected = next(
        case for case in payload["cases"] if case["name"].endswith("selected-columns")
    )

    assert selected["ok"] is True
    assert selected["status"] == "preview_and_full_import_ok"
    assert selected["columns"] == ["자치구", "인구"]
    assert selected["columns"] == selected["full_import"]["columns"]
    assert selected["selection"]["included_columns"] == selected["columns"]
    assert "연도" not in selected["columns"]
    assert "CSV 인코딩: cp949" in selected["warnings"]


def test_app_public_data_smoke_writes_success_payload(tmp_path) -> None:
    from modori.app import main
    from modori.public_data_smoke import PUBLIC_DATA_SMOKE_CASES

    output_path = tmp_path / "public-data-smoke.json"

    result = main(["modori", "--public-data-smoke", str(FIXTURE_DIR), str(output_path)])

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["ok"] is True
    assert payload["case_count"] == len(PUBLIC_DATA_SMOKE_CASES)
