from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

from modori.core import Dataset, Measure, Variable
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
    return BinaryLogisticRegressionStep(
        id="logit-hard",
        title="Logistic hard condition",
        params=_params(predictors),
    ).compute_context_free(_dataset(frame)).analysis


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
