from __future__ import annotations

from dataclasses import replace
import warnings

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

from modori.core import Dataset, Measure, Variable
from modori.logistic_regression_reporting import prose_for_logistic, table_for_logistic
from modori.steps.logistic_regression import BinaryLogisticRegressionStep


def _dataset(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            column: Variable(
                name=column,
                label=column,
                measure=Measure.ORDINAL if column == "event" else Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id="fixture",
            )
            for column in frame.columns
        },
    )


def _params(predictors: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "outcome": "event",
        "event_value": 1,
        "predictors": predictors,
        "logistic_policy": {
            "preset": "conservative",
            "classification_threshold": 0.5,
            "calibration_bins": 10,
            "categorical_predictors": {},
        },
        "language": "ko",
    }


def _overlap_frame() -> pd.DataFrame:
    rng = np.random.default_rng(48)
    x = np.linspace(-2.0, 2.0, 80)
    probability = 1.0 / (1.0 + np.exp(-((-0.1) + (0.5 * x))))
    event = (rng.random(len(x)) < probability).astype(int)
    return pd.DataFrame({"event": event, "x": x})


def _compute(frame: pd.DataFrame, predictors: list[str]):
    return (
        BinaryLogisticRegressionStep(
            id="logit-hard",
            title="Logistic hard condition",
            params=_params(predictors),
        )
        .compute_context_free(_dataset(frame))
        .analysis
    )


def test_statsmodels_separation_warning_is_promoted_to_error(monkeypatch) -> None:
    import modori.steps.logistic_regression as module

    original = module._fit_binomial_glm

    def warning_fit(*args, **kwargs):
        warnings.warn("forced", PerfectSeparationWarning)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_fit_binomial_glm", warning_fit)

    with pytest.raises(ValueError, match="separation or convergence warning"):
        _compute(_overlap_frame(), ["x"])


def test_statsmodels_runtime_warning_is_promoted_to_error(monkeypatch) -> None:
    import modori.steps.logistic_regression as module

    original = module._fit_binomial_glm

    def warning_fit(*args, **kwargs):
        warnings.warn("forced numeric warning", RuntimeWarning)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_fit_binomial_glm", warning_fit)

    with pytest.raises(ValueError, match="numerical warning"):
        _compute(_overlap_frame(), ["x"])


def test_nonconverged_fit_is_rejected(monkeypatch) -> None:
    import modori.steps.logistic_regression as module

    original = module._fit_binomial_glm

    def nonconverged(*args, **kwargs):
        fitted = original(*args, **kwargs)
        fitted.converged = False
        return fitted

    monkeypatch.setattr(module, "_fit_binomial_glm", nonconverged)

    with pytest.raises(ValueError, match="did not converge"):
        _compute(_overlap_frame(), ["x"])


def test_score_residual_above_policy_is_rejected(monkeypatch) -> None:
    import modori.steps.logistic_regression as module

    monkeypatch.setattr(
        module,
        "_score_infinity_per_observation",
        lambda *args, **kwargs: 1e-6,
    )

    with pytest.raises(ValueError, match="score residual"):
        _compute(_overlap_frame(), ["x"])


def test_near_collinear_information_matrix_is_rejected() -> None:
    frame = _overlap_frame()
    frame["x2"] = frame["x"] + (1e-5 * np.sin(np.arange(len(frame))))

    with pytest.raises(ValueError, match="information matrix is ill-conditioned"):
        _compute(frame, ["x", "x2"])


def test_result_rejects_predictor_or_and_warning_mismatches() -> None:
    result = _compute(_overlap_frame(), ["x"])
    predictor_index = next(
        index
        for index, row in enumerate(result.coefficients)
        if row.term_type != "intercept"
    )
    coefficients = list(result.coefficients)
    coefficients[predictor_index] = replace(
        coefficients[predictor_index],
        odds_ratio=None,
        odds_ratio_ci=None,
    )

    with pytest.raises(ValueError, match="must align"):
        replace(result, coefficients=tuple(coefficients))

    with pytest.raises(ValueError, match="must align"):
        replace(
            result,
            warning_codes=(
                *result.warning_codes,
                "predictor_odds_ratio_unrepresentable",
            ),
            warnings=(*result.warnings, "unrepresentable predictor OR"),
        )


@pytest.mark.parametrize(
    ("event_label", "non_event_label"),
    [("", "control"), ("same", "SAME"), ("１", "1")],
)
def test_result_rejects_blank_or_ambiguous_outcome_labels(
    event_label: str,
    non_event_label: str,
) -> None:
    result = _compute(_overlap_frame(), ["x"])

    with pytest.raises(ValueError, match="outcome display labels"):
        replace(
            result,
            event_label=event_label,
            non_event_label=non_event_label,
        )


def test_result_rejects_numerically_identical_outcome_values() -> None:
    result = _compute(_overlap_frame(), ["x"])

    with pytest.raises(ValueError, match="outcome values must be distinct"):
        replace(
            result,
            event_value=1,
            non_event_value=1.0,
            event_label="event (1)",
            non_event_label="non-event (1)",
        )


@pytest.mark.parametrize("invert_event", [False, True])
@pytest.mark.parametrize("scale", [1e-9, 1e-6, 1.0, 1e6])
def test_unrepresentable_predictor_odds_ratio_preserves_fit_and_inference(
    invert_event: bool,
    scale: float,
) -> None:
    frame = _overlap_frame()
    if invert_event:
        frame["event"] = 1 - frame["event"]
    baseline = _compute(frame, ["x"])
    baseline_row = next(row for row in baseline.coefficients if row.name == "x")

    scaled_frame = frame.copy()
    scaled_frame["x"] *= scale
    scaled = _compute(scaled_frame, ["x"])
    scaled_row = next(row for row in scaled.coefficients if row.name == "x")

    assert scaled.log_likelihood == pytest.approx(baseline.log_likelihood, abs=1e-12)
    assert scaled_row.b * scale == pytest.approx(baseline_row.b, rel=1e-11)
    assert scaled_row.se * scale == pytest.approx(baseline_row.se, rel=1e-11)
    assert scaled_row.wald_z == pytest.approx(baseline_row.wald_z, abs=1e-11)
    assert scaled_row.p_value == pytest.approx(baseline_row.p_value, abs=1e-12)
    coefficient_table = table_for_logistic(scaled)
    x_row = next(row for row in coefficient_table if row["term"] == "x")
    if scale < 1.0:
        assert scaled_row.odds_ratio is None
        assert scaled_row.odds_ratio_ci is None
        assert "predictor_odds_ratio_unrepresentable" in scaled.warning_codes
        assert (
            "x"
            in scaled.warnings[
                scaled.warning_codes.index("predictor_odds_ratio_unrepresentable")
            ]
        )
        assert "odds_ratio_forest" not in {chart.type for chart in scaled.chart_specs}
        assert x_row["odds ratio"] == ""
        assert x_row["95% CI (OR)"] == ""
        assert "예측변수를 해석 가능한 단위로 재조정" in prose_for_logistic(
            scaled, "ko"
        )
    else:
        assert scaled_row.odds_ratio is not None
        assert scaled_row.odds_ratio_ci is not None
        assert "predictor_odds_ratio_unrepresentable" not in scaled.warning_codes
        assert "odds_ratio_forest" in {chart.type for chart in scaled.chart_specs}
        assert x_row["odds ratio"]
        assert x_row["95% CI (OR)"]
