from __future__ import annotations

import json
from pathlib import Path


FIXTURE_DIR = Path("tests/fixtures/public_data_formats")


def test_public_data_import_smoke_payload_checks_nontrivial_contracts() -> None:
    from modori.public_data_smoke import public_data_import_smoke_payload

    payload = public_data_import_smoke_payload(FIXTURE_DIR)

    assert payload["ok"] is True
    assert payload["case_count"] == 7
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
    assert cases["notice-only-xlsx-reject"]["status"] == "expected_reject"


def test_app_public_data_smoke_writes_success_payload(tmp_path) -> None:
    from modori.app import main

    output_path = tmp_path / "public-data-smoke.json"

    result = main(["modori", "--public-data-smoke", str(FIXTURE_DIR), str(output_path)])

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["ok"] is True
    assert payload["case_count"] == 7
