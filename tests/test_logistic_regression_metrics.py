from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.special import expit
from scipy.stats import chi2

from modori.core import Dataset, Measure, Variable
from modori.logistic_regression_results import LogisticRegressionResult
from modori.steps.logistic_regression import BinaryLogisticRegressionStep


def _dataset(frame: pd.DataFrame, measures: dict[str, Measure] | None = None) -> Dataset:
    measures = measures or {}
    return Dataset(
        df=frame,
        variables={
            column: Variable(
                name=column,
                label=column,
                measure=measures.get(column, Measure.SCALE),
                value_labels={0.0: "no", 1.0: "yes"} if column == "event" else {},
                missing_values=[],
                dtype="float" if pd.api.types.is_numeric_dtype(frame[column]) else "string",
                origin_step_id="fixture",
            )
            for column in frame.columns
        },
    )


def _continuous_frame() -> pd.DataFrame:
    rng = np.random.default_rng(20260710)
    x1 = np.linspace(-2.5, 2.5, 120)
    x2 = np.sin(np.linspace(0.0, 5.0 * np.pi, 120))
    probability = expit(-0.25 + (0.7 * x1) - (0.45 * x2))
    event = (rng.random(len(x1)) < probability).astype(int)
    return pd.DataFrame({"event": event, "x1": x1, "x2": x2})


def _params(*, threshold: float = 0.5, bins: int = 10) -> dict[str, object]:
    return {
        "schema_version": 1,
        "outcome": "event",
        "event_value": 1,
        "predictors": ["x1", "x2"],
        "logistic_policy": {
            "preset": "conservative",
            "classification_threshold": threshold,
            "calibration_bins": bins,
            "categorical_predictors": {},
        },
        "language": "ko",
    }


def _fit(frame: pd.DataFrame, params: dict[str, object] | None = None) -> LogisticRegressionResult:
    result = BinaryLogisticRegressionStep(
        id="logit",
        title="Binary logistic regression",
        params=params or _params(),
    ).compute_context_free(_dataset(frame)).analysis
    assert isinstance(result, LogisticRegressionResult)
    return result


def test_logistic_fit_matches_direct_glm_and_reconstructed_metrics() -> None:
    frame = _continuous_frame()
    result = _fit(frame, _params(threshold=0.4, bins=8))
    x = sm.add_constant(frame[["x1", "x2"]], has_constant="add").to_numpy(dtype=float)
    y = frame["event"].to_numpy(dtype=float)
    reference = sm.GLM(y, x, family=sm.families.Binomial()).fit(maxiter=200, tol=1e-10)
    null = sm.GLM(y, np.ones((len(y), 1)), family=sm.families.Binomial()).fit(
        maxiter=200,
        tol=1e-10,
    )

    returned_b = np.asarray([row.b for row in result.coefficients])
    returned_se = np.asarray([row.se for row in result.coefficients])
    probability = expit(x @ returned_b)
    predicted = probability >= 0.4
    tn = int(np.sum((y == 0) & ~predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    tp = int(np.sum((y == 1) & predicted))
    lr = 2.0 * (float(reference.llf) - float(null.llf))
    cox_snell = 1.0 - np.exp((2.0 / len(y)) * (float(null.llf) - float(reference.llf)))
    nagelkerke = cox_snell / (1.0 - np.exp((2.0 / len(y)) * float(null.llf)))

    assert returned_b == pytest.approx(reference.params, abs=1e-9, rel=1e-9)
    assert returned_se == pytest.approx(reference.bse, abs=1e-9, rel=1e-9)
    assert result.log_likelihood == pytest.approx(reference.llf, abs=1e-10)
    assert result.null_log_likelihood == pytest.approx(null.llf, abs=1e-10)
    assert result.minus_two_log_likelihood == pytest.approx(-2.0 * reference.llf, abs=1e-10)
    assert result.aic == pytest.approx(reference.aic, abs=1e-10)
    assert result.likelihood_ratio_chi_square == pytest.approx(lr, abs=1e-10)
    assert result.likelihood_ratio_df == 2
    assert result.likelihood_ratio_p_value == pytest.approx(chi2.sf(lr, 2), abs=1e-12)
    assert result.mcfadden_r_squared == pytest.approx(1.0 - reference.llf / null.llf)
    assert result.cox_snell_r_squared == pytest.approx(cox_snell)
    assert result.nagelkerke_r_squared == pytest.approx(nagelkerke)
    assert (
        result.classification.tn,
        result.classification.fp,
        result.classification.fn,
        result.classification.tp,
    ) == (tn, fp, fn, tp)
    assert result.brier_score == pytest.approx(np.mean((probability - y) ** 2), abs=1e-12)
    assert result.event_label == "yes"
    assert result.non_event_label == "no"
    assert result.diagnostics["score_infinity_per_observation"] <= 1e-10
    assert result.diagnostics["separation_status"] == "overlap"
    assert any("동일 자료" in warning for warning in result.warnings)


def test_logistic_odds_ratio_and_wald_rows_are_formula_locked() -> None:
    result = _fit(_continuous_frame())

    for row in result.coefficients:
        assert row.wald_z == pytest.approx(row.b / row.se, rel=1e-12)
        assert row.wald_chi_square == pytest.approx(row.wald_z**2, rel=1e-12)
        if row.odds_ratio is not None:
            assert row.odds_ratio == pytest.approx(np.exp(row.b), rel=1e-12)
            assert row.odds_ratio_ci == pytest.approx(np.exp(row.ci), rel=1e-12)


def test_logistic_categorical_reference_order_matches_explicit_glm_matrix() -> None:
    frame = _continuous_frame()
    frame["group"] = np.asarray(["treat", "control", "placebo"] * 40)
    params = _params()
    params["predictors"] = ["x1", "group"]
    params["logistic_policy"] = {
        "preset": "conservative",
        "classification_threshold": 0.5,
        "calibration_bins": 10,
        "categorical_predictors": {
            "group": {
                "reference": "control",
                "levels": ["control", "treat", "placebo"],
            }
        },
    }
    result = BinaryLogisticRegressionStep(
        id="logit-categorical",
        title="Categorical logistic regression",
        params=params,
    ).compute_context_free(
        _dataset(frame, {"group": Measure.NOMINAL})
    ).analysis
    x = np.column_stack(
        [
            np.ones(len(frame)),
            frame["x1"],
            frame["group"] == "treat",
            frame["group"] == "placebo",
        ]
    ).astype(float)
    reference = sm.GLM(
        frame["event"].to_numpy(dtype=float),
        x,
        family=sm.families.Binomial(),
    ).fit(maxiter=200, tol=1e-10)

    assert [row.name for row in result.coefficients] == [
        "(Intercept)",
        "x1",
        "group[T.treat]",
        "group[T.placebo]",
    ]
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference.params,
        abs=1e-9,
        rel=1e-9,
    )
    assert result.coefficients[2].reference_level == "control"
    assert result.coefficients[3].level == "placebo"


def test_logistic_fit_is_row_order_and_large_offset_invariant() -> None:
    frame = _continuous_frame()
    frame["x1"] = (np.arange(len(frame), dtype=float) - 60.0) / 8.0
    shifted = frame.assign(x1=frame["x1"] + 1e12)
    shuffled = frame.sample(frac=1.0, random_state=20260710).reset_index(drop=True)

    base = _fit(frame)
    moved = _fit(shifted)
    reordered = _fit(shuffled)

    assert [row.b for row in moved.coefficients[1:]] == pytest.approx(
        [row.b for row in base.coefficients[1:]],
        rel=1e-8,
        abs=1e-8,
    )
    assert [row.se for row in moved.coefficients[1:]] == pytest.approx(
        [row.se for row in base.coefficients[1:]],
        rel=1e-8,
        abs=1e-8,
    )
    assert moved.log_likelihood == pytest.approx(base.log_likelihood, abs=1e-9)
    assert moved.brier_score == pytest.approx(base.brier_score, abs=1e-10)
    assert moved.roc_auc == pytest.approx(base.roc_auc, abs=1e-12)
    assert moved.classification == base.classification
    assert moved.diagnostics["offset_ratio"] > 1e8
    assert moved.coefficients[0].odds_ratio is None
    assert moved.coefficients[0].odds_ratio_ci is None
    assert any("절편" in warning for warning in moved.warnings)
    assert [row.b for row in reordered.coefficients] == pytest.approx(
        [row.b for row in base.coefficients],
        abs=1e-10,
    )
    assert reordered.log_likelihood == pytest.approx(base.log_likelihood, abs=1e-10)


def test_calibration_ties_are_not_split_and_can_be_suppressed() -> None:
    frame = _continuous_frame()
    frame["binary_x"] = np.asarray([0, 1] * 60)
    params = _params()
    params["predictors"] = ["binary_x"]

    result = _fit(frame, params)

    assert result.calibration_bins == ()
    assert result.diagnostics["effective_calibration_bins"] == 2
    assert any("보정 구간" in warning for warning in result.warnings)


def test_missingness_and_small_class_heuristics_are_disclosed() -> None:
    frame = _continuous_frame()
    frame.loc[:11, "x2"] = np.nan
    result = _fit(frame)

    assert result.n_total == 120
    assert result.n_obs == 108
    assert result.n_dropped == 12
    assert any("결측" in warning for warning in result.warnings)
