from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.repeated_measures_anova")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.repeated_measures_anova":
            pytest.fail("modori.steps.repeated_measures_anova is not implemented")
        raise
    return module.RepeatedMeasuresAnovaStep


def _params(
    measures: list[str] | None = None,
    *,
    correction: str = "auto",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "measures": ["pre", "mid", "post"] if measures is None else measures,
        "within_factor": "time",
        "level_labels": ["사전", "중간", "사후"],
        "correction": correction,
        "sphericity_alpha": 0.05,
        "language": "ko",
    }


def dataset_factory(
    frame: pd.DataFrame,
    *,
    measures: Mapping[str, Measure] | None = None,
    labels: Mapping[str, str] | None = None,
) -> Dataset:
    measures = measures or {}
    labels = labels or {}
    variables = {
        column: Variable(
            name=column,
            label=labels.get(column, column),
            measure=measures.get(column, Measure.SCALE),
            value_labels={},
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="repeated-measures-main",
        title="Repeated-measures ANOVA",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def _wide_dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "pre": [4.0, 5.0, 6.0, 5.0, 7.0, 6.0, 8.0, 7.0],
            "mid": [5.0, 6.0, 7.0, 6.0, 8.0, 7.0, 8.0, 9.0],
            "post": [7.0, 8.0, 8.0, 7.0, 9.0, 8.0, 10.0, 9.0],
        }
    )
    return dataset_factory(
        frame,
        labels={"pre": "사전 점수", "mid": "중간 점수", "post": "사후 점수"},
    )


def _manual_rm_anova(frame: pd.DataFrame) -> dict[str, float]:
    n_subjects, k_levels = frame.shape
    grand_mean = frame.to_numpy(dtype=float).mean()
    level_means = frame.mean(axis=0)
    subject_means = frame.mean(axis=1)
    ss_total = float(((frame - grand_mean) ** 2).to_numpy(dtype=float).sum())
    ss_subjects = float(k_levels * ((subject_means - grand_mean) ** 2).sum())
    ss_within = ss_total - ss_subjects
    ss_effect = float(n_subjects * ((level_means - grand_mean) ** 2).sum())
    ss_error = ss_within - ss_effect
    df_effect = k_levels - 1
    df_error = (n_subjects - 1) * (k_levels - 1)
    f_value = (ss_effect / df_effect) / (ss_error / df_error)
    return {
        "ss_effect": ss_effect,
        "ss_error": ss_error,
        "df_effect": float(df_effect),
        "df_error": float(df_error),
        "f_value": f_value,
        "p_value": float(stats.f.sf(f_value, df_effect, df_error)),
        "partial_eta_squared": ss_effect / (ss_effect + ss_error),
    }


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"measures": ["pre", "mid", "post"]})

    with pytest.raises(ValueError, match="unknown repeated_measures_anova params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "measures": ["a", "b", "c"]})


def test_wide_format_anova_matches_manual_and_pingouin_sphericity_reference() -> None:
    pg = pytest.importorskip("pingouin")
    dataset = _wide_dataset()
    complete = dataset.df.loc[:, ["pre", "mid", "post"]]
    manual = _manual_rm_anova(complete)

    result = run_step(dataset, _params(correction="auto"))

    sphericity = pg.sphericity(complete)
    epsilon_gg = float(pg.epsilon(complete, correction="gg"))
    epsilon_hf = float(pg.epsilon(complete, correction="hf"))

    assert result.analysis_key == "repeated_measures_anova"
    assert result.measures == ("pre", "mid", "post")
    assert result.within_factor == "time"
    assert result.n_total == 8
    assert result.n_used == 8
    assert result.n_excluded == 0
    assert [level.level_label for level in result.levels] == ["사전", "중간", "사후"]
    assert [level.variable for level in result.levels] == ["pre", "mid", "post"]
    assert result.ss_effect == pytest.approx(manual["ss_effect"], abs=1e-12)
    assert result.ss_error == pytest.approx(manual["ss_error"], abs=1e-12)
    assert result.df_effect == pytest.approx(manual["df_effect"], abs=1e-12)
    assert result.df_error == pytest.approx(manual["df_error"], abs=1e-12)
    assert result.f_statistic == pytest.approx(manual["f_value"], abs=1e-12)
    assert result.p_value == pytest.approx(manual["p_value"], abs=1e-12)
    assert result.partial_eta_squared == pytest.approx(
        manual["partial_eta_squared"],
        abs=1e-12,
    )
    assert result.sphericity.w_statistic == pytest.approx(float(sphericity.W), abs=1e-12)
    assert result.sphericity.chi_square == pytest.approx(float(sphericity.chi2), abs=1e-12)
    assert result.sphericity.p_value == pytest.approx(float(sphericity.pval), abs=1e-12)
    assert result.sphericity.epsilon_gg == pytest.approx(epsilon_gg, abs=1e-12)
    assert result.sphericity.epsilon_hf == pytest.approx(epsilon_hf, abs=1e-12)
    assert result.correction_method in {"none", "greenhouse_geisser"}
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko


def test_greenhouse_geisser_policy_reports_corrected_degrees_of_freedom_and_p_value() -> None:
    dataset = _wide_dataset()
    result = run_step(dataset, _params(correction="greenhouse_geisser"))

    assert result.correction_method == "greenhouse_geisser"
    assert result.corrected_df_effect == pytest.approx(
        result.df_effect * result.sphericity.epsilon_gg,
        abs=1e-12,
    )
    assert result.corrected_df_error == pytest.approx(
        result.df_error * result.sphericity.epsilon_gg,
        abs=1e-12,
    )
    assert result.corrected_p_value == pytest.approx(
        stats.f.sf(
            result.f_statistic,
            result.corrected_df_effect,
            result.corrected_df_error,
        ),
        abs=1e-12,
    )


def test_listwise_missing_subjects_match_complete_case_manual_reference() -> None:
    frame = pd.DataFrame(
        {
            "pre": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "mid": [2.0, 2.5, None, 5.0, 6.5, 7.2],
            "post": [3.0, 4.1, 5.0, None, 7.0, 7.5],
        }
    )
    dataset = dataset_factory(frame)
    complete = frame.loc[:, ["pre", "mid", "post"]].dropna(axis=0, how="any")
    manual = _manual_rm_anova(complete)

    result = run_step(dataset, _params(correction="none"))

    assert result.n_total == 6
    assert result.n_used == 4
    assert result.n_excluded == 2
    assert result.ss_effect == pytest.approx(manual["ss_effect"], abs=1e-12)
    assert result.ss_error == pytest.approx(manual["ss_error"], abs=1e-12)
    assert result.f_statistic == pytest.approx(manual["f_value"], abs=1e-12)
    assert result.p_value == pytest.approx(manual["p_value"], abs=1e-12)
    assert result.partial_eta_squared == pytest.approx(
        manual["partial_eta_squared"],
        abs=1e-12,
    )


def test_repeated_measures_anova_is_invariant_to_large_additive_offset() -> None:
    base_frame = pd.DataFrame(
        {
            "pre": [4.2, 5.1, 6.4, 5.8, 7.3, 6.2, 8.4, 7.6],
            "mid": [5.3, 6.4, 7.0, 6.7, 8.1, 7.5, 8.8, 9.2],
            "post": [7.1, 8.3, 8.4, 7.9, 9.5, 8.6, 10.1, 9.7],
        }
    )
    offset_frame = base_frame + 1e6

    base = run_step(dataset_factory(base_frame), _params(correction="none"))
    offset = run_step(dataset_factory(offset_frame), _params(correction="none"))

    assert offset.ss_effect == pytest.approx(base.ss_effect, rel=1e-10, abs=1e-10)
    assert offset.ss_error == pytest.approx(base.ss_error, rel=1e-10, abs=1e-10)
    assert offset.f_statistic == pytest.approx(base.f_statistic, rel=1e-10, abs=1e-10)
    assert offset.partial_eta_squared == pytest.approx(
        base.partial_eta_squared,
        rel=1e-10,
        abs=1e-12,
    )


def test_validation_rejects_unsupported_shapes_and_bad_inputs() -> None:
    dataset = _wide_dataset()

    with pytest.raises(ValueError, match="three or more"):
        run_step(dataset, _params(measures=["pre", "post"]))

    with pytest.raises(ValueError, match="duplicate"):
        run_step(dataset, _params(measures=["pre", "mid", "pre"]))

    nominal_dataset = dataset_factory(
        dataset.df,
        measures={"pre": Measure.NOMINAL, "mid": Measure.SCALE, "post": Measure.SCALE},
    )
    with pytest.raises(ValueError, match="scale or ordinal"):
        run_step(nominal_dataset, _params())

    non_numeric = dataset_factory(
        pd.DataFrame(
            {
                "pre": [1.0, 2.0, 3.0],
                "mid": [2.0, 3.0, 4.0],
                "post": ["high", "low", "mid"],
            }
        )
    )
    with pytest.raises(ValueError, match="numeric"):
        run_step(non_numeric, _params())

    constant = dataset_factory(
        pd.DataFrame(
            {
                "pre": [1.0, 1.0, 1.0, 1.0],
                "mid": [2.0, 3.0, 4.0, 5.0],
                "post": [3.0, 4.0, 5.0, 6.0],
            }
        )
    )
    with pytest.raises(ValueError, match="non-zero variance"):
        run_step(constant, _params())
