import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.results import RegressionResult
from modori.steps import MultipleRegressionStep, RegressionCsvImportStep, ReportStep


def variable(name: str, *, measure: Measure = Measure.SCALE, dtype: str = "float") -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype=dtype,
        origin_step_id=None,
    )


def regression_dataset(frame: pd.DataFrame, *, measures: dict[str, Measure] | None = None) -> Dataset:
    measures = measures or {}
    variables = {
        column: variable(
            column,
            measure=measures.get(column, Measure.SCALE),
            dtype="float" if pd.api.types.is_numeric_dtype(frame[column]) else "string",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def mtcars_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "mpg": [21.0, 21.0, 22.8, 21.4, 18.7, 18.1, 14.3, 24.4, 22.8, 19.2, 17.8, 16.4, 17.3, 15.2, 10.4, 10.4, 14.7, 32.4, 30.4, 33.9, 21.5, 15.5, 15.2, 13.3, 19.2, 27.3, 26.0, 30.4, 15.8, 19.7, 15.0, 21.4],
            "cyl": [6, 6, 4, 6, 8, 6, 8, 4, 4, 6, 6, 8, 8, 8, 8, 8, 8, 4, 4, 4, 4, 8, 8, 8, 8, 4, 4, 4, 8, 6, 8, 4],
            "hp": [110, 110, 93, 110, 175, 105, 245, 62, 95, 123, 123, 180, 180, 180, 205, 215, 230, 66, 52, 65, 97, 150, 150, 245, 175, 66, 91, 113, 264, 175, 335, 109],
            "wt": [2.620, 2.875, 2.320, 3.215, 3.440, 3.460, 3.570, 3.190, 3.150, 3.440, 3.440, 4.070, 3.730, 3.780, 5.250, 5.424, 5.345, 2.200, 1.615, 1.835, 2.465, 3.520, 3.435, 3.840, 3.845, 1.935, 2.140, 1.513, 3.170, 2.770, 3.570, 2.780],
        }
    )


def regression_step(policy: dict | None = None, predictors: list[str] | None = None) -> MultipleRegressionStep:
    return MultipleRegressionStep(
        id="reg-main",
        title="Multiple regression",
        params={
            "dv": "mpg",
            "predictors": ["wt", "hp", "cyl"] if predictors is None else predictors,
            "regression_policy": policy or {"preset": "classic"},
        },
    )


def test_regression_schema_migrates_legacy_params_and_policy_alias() -> None:
    migrated = MultipleRegressionStep.migrate_params(
        {"dv": "mpg", "predictors": ["wt"], "policy": {"preset": "classic"}}
    )

    assert MultipleRegressionStep.validate_params(migrated) == {
        "schema_version": MultipleRegressionStep.CURRENT_SCHEMA_VERSION,
        "dv": "mpg",
        "predictors": ["wt"],
        "regression_policy": {"preset": "classic"},
    }


def test_regression_schema_rejects_newer_and_unknown_current_params() -> None:
    with pytest.raises(ValueError, match="newer schema_version"):
        MultipleRegressionStep.migrate_params(
            {"schema_version": 999, "dv": "mpg", "predictors": ["wt"]}
        )

    with pytest.raises(ValueError, match="unknown regression_ols params"):
        MultipleRegressionStep.validate_params(
            {
                "schema_version": MultipleRegressionStep.CURRENT_SCHEMA_VERSION,
                "dv": "mpg",
                "predictors": ["wt"],
                "regression_policy": {"preset": "classic"},
                "extra": "bad",
            }
        )


def test_regression_import_writes_reads_only_csv_header(tmp_path, monkeypatch) -> None:
    path = tmp_path / "regression.csv"
    path.write_text("y,x\n1,2\n3,4\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame(columns=["y", "x"])

    monkeypatch.setattr("modori.table_io.pd.read_csv", read_csv_spy)
    step = RegressionCsvImportStep(
        id="reg-import",
        title="Regression import",
        params={"path": str(path), "scale_columns": ["y", "x"]},
    )

    assert step.writes() == {"y", "x"}
    assert calls == [{"nrows": 0}]


def test_regression_import_step_drops_aggregate_rows_when_requested(tmp_path) -> None:
    path = tmp_path / "regression-public.csv"
    path.write_text(
        "\n".join(
            [
                "지역,y,x",
                "합 계,30,3",
                "종로구,10,1",
                "중구,20,2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    step = RegressionCsvImportStep(
        id="reg-import",
        title="Regression import",
        params={
            "path": str(path),
            "file_type": "csv",
            "scale_columns": ["y", "x"],
            "drop_aggregate_rows": True,
        },
    )

    result = step.compute_context_free(Dataset.empty())

    assert result.new_columns["지역"].tolist() == ["종로구", "중구"]
    assert result.new_columns["y"].tolist() == [10, 20]
    assert result.notes == [
        "Imported 2 rows and 3 columns for regression.",
        "집계/합계 행 1개를 제외했습니다.",
    ]


def test_regression_import_step_honors_duplicate_and_column_selection(tmp_path) -> None:
    from modori.table_io import ImportSelection, read_schema

    path = tmp_path / "regression.csv"
    path.write_text("y,x,note\n1,2,a\n1,2,b\n3,4,c\n", encoding="utf-8")
    schema = read_schema(path, "csv")
    selection = ImportSelection(
        source_columns=schema.columns,
        included_columns=("y", "x"),
        schema_fingerprint=schema.fingerprint,
    )
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        RegressionCsvImportStep(
            id="import-data",
            title="Import regression data",
            params={
                "path": str(path),
                "file_type": "csv",
                "scale_columns": ["y", "x"],
                "drop_duplicate_rows": True,
                "import_selection": {
                    "schema_version": 1,
                    "source_columns": list(selection.source_columns),
                    "included_columns": list(selection.included_columns),
                    "schema_fingerprint": selection.schema_fingerprint,
                    "created_from": "preview",
                },
            },
        )
    )

    pipeline.recompute(dirty_from=None)

    assert pipeline.current_dataset.df.to_dict(orient="records") == [
        {"y": 1, "x": 2},
        {"y": 3, "x": 4},
    ]
    assert "note" not in pipeline.current_dataset.df.columns


def numpy_ols_reference(frame: pd.DataFrame, dv: str, predictors: list[str]) -> dict[str, np.ndarray | float]:
    y = frame[dv].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(frame)), frame[predictors].to_numpy(dtype=float)])
    b, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ b
    df_resid = len(frame) - x.shape[1]
    sigma2 = float((residuals @ residuals) / df_resid)
    cov = sigma2 * np.linalg.inv(x.T @ x)
    se = np.sqrt(np.diag(cov))
    ss_tot = float(((y - y.mean()) @ (y - y.mean())))
    r_squared = 1.0 - float((residuals @ residuals) / ss_tot)
    return {"b": b, "se": se, "r_squared": r_squared}


def test_regression_step_matches_independent_numpy_ols_reference() -> None:
    dataset = regression_dataset(mtcars_frame())
    result = regression_step().compute_context_free(dataset).analysis
    reference = numpy_ols_reference(mtcars_frame(), "mpg", ["wt", "hp", "cyl"])

    assert isinstance(result, RegressionResult)
    assert result.n_obs == 32
    assert result.n_total == 32
    assert result.n_dropped == 0
    assert result.se_type == "classical"
    assert [row.name for row in result.coefficients] == ["(Intercept)", "wt", "hp", "cyl"]
    assert [row.b for row in result.coefficients] == pytest.approx(reference["b"], abs=1e-10)
    assert [row.se for row in result.coefficients] == pytest.approx(reference["se"], abs=1e-10)
    assert result.r_squared == pytest.approx(reference["r_squared"], abs=1e-12)
    assert result.chart_spec.type == "coefficient_forest"
    assert result.apa_template_id == "regression.v1"
    assert all(np.isfinite(row.b) and np.isfinite(row.se) and np.isfinite(row.t) for row in result.coefficients)


def test_regression_standardized_beta_and_ci_are_scaled_from_unstandardized_values() -> None:
    frame = mtcars_frame()
    result = regression_step().compute_context_free(regression_dataset(frame)).analysis
    sd_y = frame["mpg"].std(ddof=1)

    for row in result.coefficients:
        if row.name == "(Intercept)":
            assert row.beta is None
            assert row.beta_ci is None
            continue
        scale = frame[row.name].std(ddof=1) / sd_y
        assert row.beta == pytest.approx(row.b * scale, abs=1e-12)
        assert row.beta_ci == pytest.approx((row.ci[0] * scale, row.ci[1] * scale), abs=1e-12)


def test_regression_results_are_stable_when_rows_are_shuffled() -> None:
    frame = mtcars_frame()
    result = regression_step().compute_context_free(regression_dataset(frame)).analysis
    shuffled = frame.sample(frac=1.0, random_state=20260626).reset_index(drop=True)
    reordered = regression_step().compute_context_free(regression_dataset(shuffled)).analysis

    assert [row.b for row in reordered.coefficients] == pytest.approx([row.b for row in result.coefficients], abs=1e-10)
    assert [row.se for row in reordered.coefficients] == pytest.approx([row.se for row in result.coefficients], abs=1e-10)
    assert reordered.r_squared == pytest.approx(result.r_squared, abs=1e-12)


def test_regression_inference_is_invariant_to_large_outcome_offset() -> None:
    frame = mtcars_frame()
    offset_frame = frame.copy()
    offset_frame["mpg"] = offset_frame["mpg"] + 1e12

    base = regression_step().compute_context_free(regression_dataset(frame)).analysis
    offset = regression_step().compute_context_free(regression_dataset(offset_frame)).analysis

    assert offset.r_squared == pytest.approx(base.r_squared, rel=1e-6, abs=1e-6)
    assert offset.adj_r_squared == pytest.approx(
        base.adj_r_squared,
        rel=1e-6,
        abs=1e-6,
    )
    assert offset.f_statistic == pytest.approx(base.f_statistic, rel=1e-5, abs=1e-5)
    assert offset.f_p_value == pytest.approx(base.f_p_value, rel=1e-5, abs=1e-12)
    assert offset.coefficients[0].b == pytest.approx(
        base.coefficients[0].b + 1e12,
        rel=1e-12,
        abs=1e-6,
    )
    for offset_row, base_row in zip(
        offset.coefficients[1:],
        base.coefficients[1:],
        strict=True,
    ):
        assert offset_row.b == pytest.approx(base_row.b, rel=5e-5, abs=1e-5)
        assert offset_row.se == pytest.approx(base_row.se, rel=5e-5, abs=1e-5)
        assert offset_row.t == pytest.approx(base_row.t, rel=5e-5, abs=1e-5)
        assert offset_row.p_value == pytest.approx(
            base_row.p_value,
            rel=1e-4,
            abs=1e-12,
        )


def test_regression_reports_missing_data_counts_and_warning() -> None:
    frame = mtcars_frame()
    frame.loc[:4, "hp"] = np.nan
    result = regression_step(
        {"preset": "classic", "missing_warning_threshold": 0.10}
    ).compute_context_free(regression_dataset(frame)).analysis

    assert result.n_total == 32
    assert result.n_obs == 27
    assert result.n_dropped == 5
    assert any("missing" in warning.lower() for warning in result.warnings)
    assert any("threshold" in warning.lower() for warning in result.warnings)


def test_regression_missing_rows_match_complete_case_reference() -> None:
    frame = mtcars_frame()
    frame.loc[0, "mpg"] = np.nan
    frame.loc[3, "wt"] = np.nan
    frame.loc[8, "hp"] = np.nan
    frame.loc[12, "cyl"] = np.nan
    complete = frame.dropna(axis=0, how="any").copy()

    result = regression_step(
        {"preset": "classic", "missing_warning_threshold": 0.10}
    ).compute_context_free(regression_dataset(frame)).analysis
    reference = numpy_ols_reference(complete, "mpg", ["wt", "hp", "cyl"])

    assert result.n_total == 32
    assert result.n_obs == 28
    assert result.n_dropped == 4
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference["b"],
        abs=1e-10,
    )
    assert [row.se for row in result.coefficients] == pytest.approx(
        reference["se"],
        abs=1e-10,
    )
    assert result.r_squared == pytest.approx(reference["r_squared"], abs=1e-12)


@pytest.mark.parametrize(
    "frame, measures, predictors, message",
    [
        (mtcars_frame(), {"mpg": Measure.ORDINAL}, ["wt"], "dependent variable must be SCALE"),
        (mtcars_frame(), {"wt": Measure.ORDINAL}, ["wt"], "predictor must be SCALE"),
        (mtcars_frame().assign(wt_text="heavy"), {}, ["wt_text"], "predictor must be numeric"),
        (mtcars_frame(), {}, [], "at least one predictor"),
        (mtcars_frame(), {}, ["wt", "wt"], "predictors must be unique"),
        (mtcars_frame().assign(constant=1.0), {}, ["constant"], "non-zero variance"),
        (mtcars_frame().assign(copy_wt=lambda df: df["wt"]), {}, ["wt", "copy_wt"], "perfectly collinear"),
    ],
)
def test_regression_rejects_invalid_inputs(frame, measures, predictors, message) -> None:
    with pytest.raises(ValueError, match=message):
        regression_step(predictors=predictors).compute_context_free(
            regression_dataset(frame, measures=measures)
        )


def test_regression_rejects_perfect_fit_instead_of_emitting_nan_or_inf() -> None:
    frame = pd.DataFrame({"y": [1.0, 2.0, 3.0, 4.0], "x": [1.0, 2.0, 3.0, 4.0]})
    step = MultipleRegressionStep(
        id="reg-perfect",
        title="Perfect fit",
        params={"dv": "y", "predictors": ["x"], "regression_policy": {"preset": "classic"}},
    )

    with pytest.raises(ValueError, match="zero residual variance|non-finite"):
        step.compute_context_free(regression_dataset(frame))


def test_regression_computes_diagnostics_and_vif_with_constant_in_design_matrix() -> None:
    result = regression_step().compute_context_free(regression_dataset(mtcars_frame())).analysis

    assert result.diagnostics["bp_p"] == pytest.approx(result.diagnostics["bp_p"], abs=0)
    assert result.diagnostics["dw"] == pytest.approx(result.diagnostics["dw"], abs=0)
    assert result.diagnostics["max_cooks"] >= 0
    assert result.diagnostics["cook_threshold"] == pytest.approx(4 / result.n_obs)
    assert result.diagnostics["max_vif"] == pytest.approx(
        max(row.vif for row in result.coefficients if row.vif is not None)
    )
    assert result.coefficients[0].vif is None
    assert all(row.vif is None or row.vif >= 1 for row in result.coefficients)


def test_single_predictor_regression_omits_vif_by_spec() -> None:
    result = regression_step(predictors=["wt"]).compute_context_free(
        regression_dataset(mtcars_frame())
    ).analysis

    assert result.diagnostics["vif"] == {}
    assert result.diagnostics["max_vif"] is None
    assert result.coefficients[0].vif is None
    assert result.coefficients[1].vif is None


def test_vif_warnings_have_moderate_and_severe_tiers() -> None:
    n_obs = 40
    x1 = np.linspace(-2, 2, n_obs)
    y = 1.0 + (0.3 * x1) + (np.cos(np.arange(n_obs)) * 0.2)

    moderate_x2 = 0.9 * x1 + (np.sin(np.arange(n_obs)) * 0.5)
    moderate = MultipleRegressionStep(
        id="reg-vif-moderate",
        title="Moderate VIF",
        params={"dv": "y", "predictors": ["x1", "x2"], "regression_policy": {"preset": "classic"}},
    ).compute_context_free(
        regression_dataset(pd.DataFrame({"y": y, "x1": x1, "x2": moderate_x2}))
    ).analysis

    severe_x2 = 0.9 * x1 + (np.sin(np.arange(n_obs)) * 0.45)
    severe = MultipleRegressionStep(
        id="reg-vif-severe",
        title="Severe VIF",
        params={"dv": "y", "predictors": ["x1", "x2"], "regression_policy": {"preset": "classic"}},
    ).compute_context_free(
        regression_dataset(pd.DataFrame({"y": y, "x1": x1, "x2": severe_x2}))
    ).analysis

    assert 5 < moderate.diagnostics["max_vif"] <= 10
    assert any("moderate" in warning.lower() and "VIF" in warning for warning in moderate.warnings)
    assert severe.diagnostics["max_vif"] > 10
    assert any("severe" in warning.lower() and "VIF" in warning for warning in severe.warnings)


def test_regression_rejects_ill_conditioned_design_matrix() -> None:
    x1 = np.linspace(-3.0, 3.0, 40)
    x2 = x1 + (1e-12 * np.sin(np.arange(len(x1)) * 1.7))
    y = 2.0 + (0.4 * x1) + (0.1 * np.cos(np.arange(len(x1))))
    step = MultipleRegressionStep(
        id="reg-conditioned",
        title="Ill-conditioned regression",
        params={"dv": "y", "predictors": ["x1", "x2"], "regression_policy": {"preset": "classic"}},
    )

    with pytest.raises(ValueError, match="ill-conditioned"):
        step.compute_context_free(regression_dataset(pd.DataFrame({"y": y, "x1": x1, "x2": x2})))


def test_small_sample_non_normal_residuals_emit_diagnostic_warning() -> None:
    x = np.arange(1, 13, dtype=float)
    residual_shock = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8.0], dtype=float)
    frame = pd.DataFrame({"y": 2 + (0.7 * x) + residual_shock, "x": x})
    step = MultipleRegressionStep(
        id="reg-shapiro",
        title="Small sample residual normality",
        params={"dv": "y", "predictors": ["x"], "regression_policy": {"preset": "classic"}},
    )

    result = step.compute_context_free(regression_dataset(frame)).analysis

    assert result.n_obs < 30
    assert result.diagnostics["shapiro_resid_p"] < 0.05
    assert any("Shapiro-Wilk" in warning and "residual" in warning for warning in result.warnings)


def heteroscedastic_dataset() -> Dataset:
    rng = np.random.default_rng(20260626)
    x = np.linspace(1, 80, 80)
    z = np.sin(x / 3.0)
    noise = rng.normal(0, x / 5)
    y = 5 + 0.7 * x - 1.5 * z + noise
    return regression_dataset(pd.DataFrame({"y": y, "x": x, "z": z}))


def test_modern_policy_switches_to_hc3_and_uses_robust_model_f_test() -> None:
    step = MultipleRegressionStep(
        id="reg-hc3",
        title="HC3 regression",
        params={"dv": "y", "predictors": ["x", "z"], "regression_policy": {"preset": "modern"}},
    )

    result = step.compute_context_free(heteroscedastic_dataset()).analysis

    assert result.diagnostics["bp_p"] < 0.05
    assert result.se_type == "HC3"
    assert result.diagnostics["model_test"] == "robust_wald_f"
    assert any("HC3" in warning for warning in result.warnings)
    assert any("variance" in item for item in result.educational_interpretation)
    assert any(item.startswith("Diagnostic note:") for item in result.educational_interpretation)
    assert any(spec.type == "residual_vs_fitted" for spec in result.diagnostic_chart_specs)


def test_hc3_coefficients_match_statsmodels_robust_reference() -> None:
    dataset = heteroscedastic_dataset()
    result = MultipleRegressionStep(
        id="reg-hc3-reference",
        title="HC3 regression reference",
        params={
            "dv": "y",
            "predictors": ["x", "z"],
            "regression_policy": {"preset": "custom", "se_type": "HC3"},
        },
    ).compute_context_free(dataset).analysis

    x = sm.add_constant(dataset.df[["x", "z"]], has_constant="add")
    reference = sm.OLS(dataset.df["y"], x).fit().get_robustcov_results(cov_type="HC3")

    assert result.se_type == "HC3"
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference.params,
        abs=1e-10,
    )
    assert [row.se for row in result.coefficients] == pytest.approx(
        reference.bse,
        abs=1e-10,
    )
    assert [row.t for row in result.coefficients] == pytest.approx(
        reference.tvalues,
        abs=1e-10,
    )
    assert [row.p_value for row in result.coefficients] == pytest.approx(
        reference.pvalues,
        abs=1e-10,
    )


def test_classic_policy_warns_but_keeps_classical_standard_errors() -> None:
    step = MultipleRegressionStep(
        id="reg-classic",
        title="Classic regression",
        params={"dv": "y", "predictors": ["x", "z"], "regression_policy": {"preset": "classic"}},
    )

    result = step.compute_context_free(heteroscedastic_dataset()).analysis

    assert result.diagnostics["bp_p"] < 0.05
    assert result.se_type == "classical"
    assert result.diagnostics["model_test"] == "classical_f"
    assert any("heteroscedasticity" in warning.lower() for warning in result.warnings)


def test_durbin_watson_warning_is_gated_on_declared_order() -> None:
    frame = pd.DataFrame(
        {
            "y": list(range(1, 41)),
            "x": list(range(1, 41)),
            "order": list(range(1, 41)),
        }
    )
    frame["y"] = frame["y"] + np.sin(np.linspace(0, 1, 40))
    dataset = regression_dataset(frame)
    unordered = MultipleRegressionStep(
        id="reg-unordered",
        title="Unordered",
        params={"dv": "y", "predictors": ["x"], "regression_policy": {"preset": "classic"}},
    ).compute_context_free(dataset).analysis
    ordered = MultipleRegressionStep(
        id="reg-ordered",
        title="Ordered",
        params={
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {"preset": "classic", "order_var": "order"},
        },
    ).compute_context_free(dataset).analysis

    assert not any("Durbin-Watson" in warning for warning in unordered.warnings)
    assert any("Durbin-Watson" in warning for warning in ordered.warnings)


def test_regression_writes_analysis_by_stable_step_id_for_pipeline_and_report(tmp_path: Path) -> None:
    pipeline = Pipeline(regression_dataset(mtcars_frame()))
    pipeline.add(regression_step())
    pipeline.add(
        ReportStep(
            id="report",
            title="Report",
            params={
                "include": ["reg-main"],
                "output_dir": str(tmp_path),
                "filename": "report.docx",
                "language": "ko",
            },
        )
    )

    pipeline.recompute(dirty_from=None)
    original_prose = pipeline.analysis_objects["report"].prose
    pipeline.edit_params(
        "reg-main",
        {"dv": "mpg", "predictors": ["wt", "hp"], "regression_policy": {"preset": "classic"}},
    )

    assert "analysis:reg-main" in pipeline.analysis_objects
    assert "reg-main" in pipeline.analysis_objects
    assert pipeline.analysis_objects["report"].prose != original_prose
    assert pipeline.analysis_objects["report"].docx_path.endswith("report.docx")


def test_regression_matches_committed_r_reference_when_r_is_available() -> None:
    rscript = os.environ.get("MODORI_RSCRIPT")
    if not rscript:
        local = Path(__file__).resolve().parents[1] / ".tools" / "r-env" / "Scripts" / "Rscript.exe"
        rscript = str(local) if local.exists() else shutil.which("Rscript")
    if rscript is None:
        pytest.skip("Rscript is not installed; R regression reference check cannot run here.")

    script = Path(__file__).parent / "r" / "regression_reference.R"
    expected_stdout = (Path(__file__).parent / "r" / "regression_reference.stdout.txt").read_text(
        encoding="utf-8"
    ).strip()
    env = os.environ.copy()
    explicit_or_local_rscript = rscript
    if explicit_or_local_rscript:
        prefix = Path(explicit_or_local_rscript).resolve().parents[1]
        r_paths = [
            prefix / "Library" / "bin",
            prefix / "Scripts",
            prefix / "lib" / "R" / "bin",
            prefix / "lib" / "R" / "bin" / "x64",
        ]
        env["PATH"] = ";".join(str(path) for path in r_paths) + ";" + env.get("PATH", "")
    completed = subprocess.run(
        [rscript, str(script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0 and "package" in completed.stderr:
        pytest.skip(completed.stderr)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == expected_stdout

    reference = json.loads(expected_stdout)
    classical = regression_step().compute_context_free(regression_dataset(mtcars_frame())).analysis
    assert [row.b for row in classical.coefficients] == pytest.approx(reference["classical"]["coef"], abs=1e-9)
    assert [row.se for row in classical.coefficients] == pytest.approx(reference["classical"]["se"], abs=1e-9)
    assert classical.r_squared == pytest.approx(reference["classical"]["r_squared"], abs=1e-12)
    assert classical.f_statistic == pytest.approx(reference["classical"]["f"], abs=1e-9)
    assert [row.vif for row in classical.coefficients if row.vif is not None] == pytest.approx(
        reference["classical"]["vif"],
        abs=1e-9,
    )

    hc3 = regression_step({"preset": "custom", "se_type": "HC3"}).compute_context_free(
        regression_dataset(mtcars_frame())
    ).analysis
    assert [row.se for row in hc3.coefficients] == pytest.approx(reference["hc3"]["se"], abs=1e-9)
    assert [row.t for row in hc3.coefficients] == pytest.approx(reference["hc3"]["t"], abs=1e-9)
    assert [row.p_value for row in hc3.coefficients] == pytest.approx(reference["hc3"]["p"], abs=1e-9)
