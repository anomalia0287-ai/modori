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
    covariates: list[str] | None = None,
) -> tuple[float, float]:
    covariates = ["c1"] if covariates is None else covariates
    rng = np.random.default_rng(seed)
    effects = []
    n = len(frame)
    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, n, size=n)].reset_index(drop=True)
        a = ols_coefficients(sample, "m", ["x", *covariates])[1]
        b = ols_coefficients(sample, "y", ["x", "m", *covariates])[2]
        effects.append(float(a * b))
    return tuple(np.percentile(effects, [2.5, 97.5]))


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"x": "x", "mediator": "m", "y": "y"})

    with pytest.raises(ValueError, match="unknown mediation params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "x": "x", "mediator": "m", "y": "y"})


def test_mediation_bootstrap_defaults_to_user_facing_5000_iterations() -> None:
    params = _params()
    params.pop("bootstrap")

    validated = _step_cls().validate_params(params)

    assert validated["bootstrap"]["iterations"] == 5000


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
    assert any("1000회 미만" in warning for warning in result.warnings_ko)
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko


def test_mediation_without_covariates_matches_independent_reference() -> None:
    frame = mediation_frame()
    params = {**_params(), "covariates": []}

    result = run_step(dataset_factory(frame), params)

    a_reference = ols_coefficients(frame, "m", ["x"])
    b_reference = ols_coefficients(frame, "y", ["x", "m"])
    c_reference = ols_coefficients(frame, "y", ["x"])
    ci_low, ci_high = bootstrap_indirect_reference(
        frame,
        iterations=300,
        seed=20260708,
        covariates=[],
    )

    assert result.covariates == ()
    assert result.n_used == 28
    assert result.n_excluded == 0
    assert result.path_a.b == pytest.approx(a_reference[1], abs=1e-10)
    assert result.path_b.b == pytest.approx(b_reference[2], abs=1e-10)
    assert result.direct_effect.b == pytest.approx(b_reference[1], abs=1e-10)
    assert result.total_effect.b == pytest.approx(c_reference[1], abs=1e-10)
    assert result.indirect_ci == pytest.approx((ci_low, ci_high), abs=1e-10)


def test_mediation_listwise_missing_rows_match_complete_case_reference() -> None:
    frame = mediation_frame()
    frame.loc[1, "x"] = np.nan
    frame.loc[5, "m"] = np.nan
    frame.loc[8, "y"] = np.nan
    frame.loc[13, "c1"] = np.nan
    complete = frame.dropna(axis=0, how="any").copy()

    result = run_step(dataset_factory(frame), _params())

    a_reference = ols_coefficients(complete, "m", ["x", "c1"])
    b_reference = ols_coefficients(complete, "y", ["x", "m", "c1"])
    c_reference = ols_coefficients(complete, "y", ["x", "c1"])
    ci_low, ci_high = bootstrap_indirect_reference(
        complete,
        iterations=300,
        seed=20260708,
    )

    assert result.n_total == 28
    assert result.n_used == 24
    assert result.n_excluded == 4
    assert result.path_a.b == pytest.approx(a_reference[1], abs=1e-10)
    assert result.path_b.b == pytest.approx(b_reference[2], abs=1e-10)
    assert result.direct_effect.b == pytest.approx(b_reference[1], abs=1e-10)
    assert result.total_effect.b == pytest.approx(c_reference[1], abs=1e-10)
    assert result.indirect_ci == pytest.approx((ci_low, ci_high), abs=1e-10)


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


def test_mediation_rejects_ill_conditioned_ols_design() -> None:
    frame = mediation_frame()
    frame["near_x"] = frame["x"] + (1e-12 * np.sin(np.arange(len(frame)) * 1.7))

    with pytest.raises(ValueError, match="ill-conditioned"):
        run_step(
            dataset_factory(frame),
            {**_params(), "covariates": ["c1", "near_x"]},
        )


def test_mediation_ols_covariance_avoids_normal_equation_inverse(monkeypatch) -> None:
    mediation_module = importlib.import_module("modori.steps.mediation")
    frame = mediation_frame()

    def fail_inv(_matrix):
        raise AssertionError("normal-equation inverse should not be used")

    monkeypatch.setattr(mediation_module.np.linalg, "inv", fail_inv)

    fit = mediation_module._fit_ols(frame, outcome="y", predictors=["x", "m", "c1"])

    assert fit.coefficients["x"].se > 0.0
