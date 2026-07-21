import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


def test_engine_smoke_uses_stable_direct_rerun_path() -> None:
    source = Path("src/modori/app.py").read_text(encoding="utf-8")

    assert "controller.runPreparedRecommendation()" not in source
    assert "controller.configureDescriptivesFromText" in source
    assert "rerun = controller.rerun() if configured else None" in source


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
    assert payload["opened"] is True
    assert payload["rerun"] is True
    assert payload["waited"] is True
    assert '"ok": true' in text
    assert '"status": "ready"' in text
    assert '"v1_statistics_smoke"' in text
    assert '"repeated_measures_anova"' in text
    assert '"anova_factorial"' in text
    assert '"friedman"' in text
    assert '"mediation"' in text
    assert '"moderated_mediation"' in text
    assert '"factor_pca_pca"' in text
    assert '"regression_categorical_interaction"' in text
    logistic = next(
        check
        for check in payload["v1_statistics_smoke"]["checks"]
        if check["key"] == "logistic_regression"
    )
    assert logistic == {
        "analysis_type": "LogisticRegressionResult",
        "key": "logistic_regression",
        "ok": True,
    }
    factorial = next(
        check
        for check in payload["v1_statistics_smoke"]["checks"]
        if check["key"] == "anova_factorial"
    )
    assert factorial["analysis_type"] == "FactorialAnovaResult"
    assert factorial["evidence"] == {
        "analysis_key": "anova_factorial",
        "cell_count": 6,
        "chart_type": "factorial_interaction",
        "effect_count": 3,
        "finite_effect_statistics": True,
        "level_counts": [2, 3],
        "marginal_count": 5,
        "method": "type_iii_equal_cell_weight",
        "simple_effect_count": 5,
    }


def test_app_engine_smoke_fails_when_analysis_rerun_is_rejected(
    monkeypatch,
    tmp_path,
) -> None:
    import modori.app as app

    class VariableModel:
        def rowCount(self):
            return 3

        def index(self, row, _column):
            return row

        def data(self, row):
            return f"q{row + 1}"

    class RejectingController:
        status = "ready"
        lastError = "rerun rejected"
        resultSummary = ""
        dataModel = None
        variableModel = VariableModel()

        def openDataFile(self, _path, _options):
            return SimpleNamespace(ok=True)

        def configureDescriptivesFromText(self, variable_keys, group_key):
            assert variable_keys == "q1, q2, q3"
            assert group_key == ""
            return True

        def rerun(self):
            return SimpleNamespace(ok=False)

        def waitForLastRun(self, *, timeout):
            assert timeout == 30
            return True

    monkeypatch.setattr(app, "UiController", RejectingController)
    cache_path = tmp_path / "cache"
    cache_path.mkdir()
    monkeypatch.setattr(app, "cache_dir", lambda: cache_path)
    monkeypatch.setattr(
        app,
        "v1_statistics_smoke_payload",
        lambda: {"ok": True, "checks": []},
    )
    output_path = tmp_path / "engine-smoke.json"

    result = app._run_engine_smoke(tmp_path / "input.xlsx", output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result == 1
    assert payload["opened"] is True
    assert payload["rerun"] is False
    assert payload["ok"] is False
