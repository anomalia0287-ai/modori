import json
from pathlib import Path

import pandas as pd


def test_app_engine_smoke_writes_success_payload(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.app import main

    cache_path = tmp_path / "runtime-state" / "cache"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(cache_path))
    monkeypatch.setenv(
        "MODORI_SETTINGS_PATH",
        str(tmp_path / "runtime-state" / "settings.json"),
    )
    monkeypatch.setenv(
        "MPLCONFIGDIR",
        str(tmp_path / "runtime-state" / "matplotlib"),
    )
    csv_path = tmp_path / "survey.csv"
    data_path = tmp_path / "survey.xlsx"
    output_path = tmp_path / "engine-smoke.json"
    write_reference_csv(csv_path)
    pd.read_csv(csv_path).to_excel(data_path, index=False, sheet_name="Responses")

    assert not cache_path.exists()

    result = main(["modori", "--engine-smoke", str(data_path), str(output_path)])

    assert result == 0
    text = Path(output_path).read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["cache_dir"] == str(cache_path.resolve())
    assert cache_path.is_dir()
    assert '"ok": true' in text
    assert '"status": "ready"' in text
    assert '"v1_statistics_smoke"' in text
    assert '"repeated_measures_anova"' in text
    assert '"friedman"' in text
    assert '"mediation"' in text
    assert '"moderated_mediation"' in text
    assert '"factor_pca_pca"' in text
    assert '"regression_categorical_interaction"' in text
