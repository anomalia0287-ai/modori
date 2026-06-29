from pathlib import Path

import pandas as pd


def test_app_engine_smoke_writes_success_payload(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.app import main

    csv_path = tmp_path / "survey.csv"
    data_path = tmp_path / "survey.xlsx"
    output_path = tmp_path / "engine-smoke.json"
    write_reference_csv(csv_path)
    pd.read_csv(csv_path).to_excel(data_path, index=False, sheet_name="Responses")

    result = main(["modori", "--engine-smoke", str(data_path), str(output_path)])

    assert result == 0
    text = Path(output_path).read_text(encoding="utf-8")
    assert '"ok": true' in text
    assert '"status": "ready"' in text
