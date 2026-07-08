from __future__ import annotations

import importlib
from collections.abc import Mapping

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.mediation")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.mediation":
            pytest.fail("modori.steps.mediation is not implemented")
        raise
    return module.MediationStep


def _params() -> dict[str, object]:
    return {
        "schema_version": 1,
        "x": "x",
        "mediator": "m",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 300, "seed": 20260708, "ci": 0.95},
        "standardize": False,
        "language": "ko",
    }


def dataset_factory(
    frame: pd.DataFrame,
    *,
    measures: Mapping[str, Measure] | None = None,
) -> Dataset:
    measures = measures or {}
    variables = {
        column: Variable(
            name=column,
            label=column,
            measure=measures.get(column, Measure.SCALE),
            value_labels={},
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def mediation_frame() -> pd.DataFrame:
    x = np.linspace(-2.5, 3.0, 28)
    c1 = np.array([0.2, -0.4, 0.1, 0.6, -0.2, 0.3, -0.1] * 4)
    m_noise = np.array(
        [
            0.10,
            -0.08,
            0.04,
            0.12,
            -0.06,
            0.02,
            -0.04,
            0.05,
            -0.03,
            0.07,
            -0.09,
            0.11,
            -0.02,
            0.08,
            -0.05,
            0.06,
            -0.07,
            0.03,
            0.09,
            -0.11,
            0.01,
            0.04,
            -0.06,
            0.10,
            -0.08,
            0.05,
            -0.03,
            0.07,
        ]
    )
    y_noise = np.array(
        [
            -0.12,
            0.04,
            -0.03,
            0.08,
            -0.05,
            0.06,
            -0.01,
            0.09,
            -0.10,
            0.02,
            0.07,
            -0.04,
            0.05,
            -0.08,
            0.11,
            -0.02,
            0.03,
            -0.07,
            0.10,
            -0.06,
            0.04,
            -0.03,
            0.08,
            -0.09,
            0.02,
            0.06,
            -0.05,
            0.07,
        ]
    )
    m = 1.0 + 0.65 * x + 0.25 * c1 + m_noise
    y = 2.0 + 0.35 * x + 0.8 * m + 0.15 * c1 + y_noise
    return pd.DataFrame({"x": x, "m": m, "y": y, "c1": c1})


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(id="mediation-main", title="Mediation", params=dict(params))
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def ols_coefficients(frame: pd.DataFrame, outcome: str, predictors: list[str]) -> np.ndarray:
    x_matrix = np.column_stack(
        [np.ones(len(frame)), *[frame[predictor].to_numpy(dtype=float) for predictor in predictors]]
    )
    y_vector = frame[outcome].to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    return coefficients


def bootstrap_indirect_reference(
    frame: pd.DataFrame,
    *,
    iterations: int,
    seed: int,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    effects = []
    n = len(frame)
    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, n, size=n)].reset_index(drop=True)
        a = ols_coefficients(sample, "m", ["x", "c1"])[1]
        b = ols_coefficients(sample, "y", ["x", "m", "c1"])[2]
        effects.append(float(a * b))
    return tuple(np.percentile(effects, [2.5, 97.5]))


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"x": "x", "mediator": "m", "y": "y"})

    with pytest.raises(ValueError, match="unknown mediation params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "x": "x", "mediator": "m", "y": "y"})


def test_simple_mediation_matches_independent_ols_and_deterministic_bootstrap() -> None:
    frame = mediation_frame()
    dataset = dataset_factory(frame)

    result = run_step(dataset, _params())

    a_reference = ols_coefficients(frame, "m", ["x", "c1"])
    b_reference = ols_coefficients(frame, "y", ["x", "m", "c1"])
    c_reference = ols_coefficients(frame, "y", ["x", "c1"])
    ci_low, ci_high = bootstrap_indirect_reference(
        frame,
        iterations=300,
        seed=20260708,
    )

    assert result.analysis_key == "mediation"
    assert result.x == "x"
    assert result.mediator == "m"
    assert result.y == "y"
    assert result.covariates == ("c1",)
    assert result.n_total == 28
    assert result.n_used == 28
    assert result.n_excluded == 0
    assert result.path_a.b == pytest.approx(a_reference[1], abs=1e-10)
    assert result.path_b.b == pytest.approx(b_reference[2], abs=1e-10)
    assert result.direct_effect.b == pytest.approx(b_reference[1], abs=1e-10)
    assert result.total_effect.b == pytest.approx(c_reference[1], abs=1e-10)
    assert result.indirect_effect == pytest.approx(result.path_a.b * result.path_b.b, abs=1e-12)
    assert result.indirect_ci == pytest.approx((ci_low, ci_high), abs=1e-10)
    assert result.bootstrap_iterations == 300
    assert result.bootstrap_seed == 20260708
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko


def test_validation_rejects_duplicate_roles_non_scale_and_singular_models() -> None:
    frame = mediation_frame()
    dataset = dataset_factory(frame)

    with pytest.raises(ValueError, match="distinct"):
        run_step(dataset, {**_params(), "mediator": "x"})

    nominal_dataset = dataset_factory(frame, measures={"m": Measure.NOMINAL})
    with pytest.raises(ValueError, match="scale"):
        run_step(nominal_dataset, _params())

    with pytest.raises(ValueError, match="standardize"):
        run_step(dataset, {**_params(), "standardize": True})

    singular = frame.assign(c2=frame["c1"] * 2.0)
    with pytest.raises(ValueError, match="full rank"):
        run_step(
            dataset_factory(singular),
            {**_params(), "covariates": ["c1", "c2"]},
        )
