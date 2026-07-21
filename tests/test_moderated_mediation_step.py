from __future__ import annotations

import importlib
from collections.abc import Mapping

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.moderated_mediation")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.moderated_mediation":
            pytest.fail("modori.steps.moderated_mediation is not implemented")
        raise
    return module.ModeratedMediationStep


def _params(model: int = 7) -> dict[str, object]:
    return {
        "schema_version": 1,
        "model": model,
        "x": "x",
        "mediator": "m",
        "moderator": "w",
        "y": "y",
        "covariates": ["c1"],
        "bootstrap": {"iterations": 250, "seed": 20260708, "ci": 0.95},
        "moderator_values": "mean_sd",
        "center": "mean",
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


def moderated_frame() -> pd.DataFrame:
    x = np.linspace(-3.0, 3.0, 32)
    w = np.array(
        [
            -1.4,
            -0.8,
            0.2,
            1.1,
            -1.1,
            -0.4,
            0.6,
            1.5,
        ]
        * 4
    )
    c1 = np.array([0.2, -0.3, 0.4, -0.1] * 8)
    x_c = x - x.mean()
    w_c = w - w.mean()
    m_noise = np.array([0.04, -0.03, 0.05, -0.04, 0.02, -0.01, 0.03, -0.02] * 4)
    y_noise = np.array([-0.05, 0.04, -0.02, 0.03, -0.01, 0.02, -0.04, 0.05] * 4)
    m = 1.0 + 0.55 * x_c + 0.25 * w_c + 0.35 * x_c * w_c + 0.2 * c1 + m_noise
    y = 2.0 + 0.28 * x_c + 0.72 * m + 0.22 * w_c + 0.31 * m * w_c + 0.12 * c1 + y_noise
    return pd.DataFrame({"x": x, "w": w, "m": m, "y": y, "c1": c1})


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(id="moderated-mediation-main", title="Moderated mediation", params=dict(params))
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def ols_coefficients(frame: pd.DataFrame, outcome: str, predictors: list[str]) -> dict[str, float]:
    x_matrix = np.column_stack(
        [np.ones(len(frame)), *[frame[predictor].to_numpy(dtype=float) for predictor in predictors]]
    )
    y_vector = frame[outcome].to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    return dict(zip(["(Intercept)", *predictors], coefficients, strict=True))


def centered_reference_frame(frame: pd.DataFrame) -> pd.DataFrame:
    ref = frame.copy()
    ref["x_centered"] = ref["x"] - ref["x"].mean()
    ref["w_centered"] = ref["w"] - ref["w"].mean()
    ref["x_centered:w_centered"] = ref["x_centered"] * ref["w_centered"]
    ref["m:w_centered"] = ref["m"] * ref["w_centered"]
    return ref


def bootstrap_model_7_reference(
    frame: pd.DataFrame,
    *,
    iterations: int,
    seed: int,
    ci: float,
    covariates: list[str] | None = None,
) -> tuple[dict[str, tuple[float, float]], tuple[float, float]]:
    covariates = ["c1"] if covariates is None else covariates
    rng = np.random.default_rng(seed)
    moderator_sd = float(frame["w"].std(ddof=1))
    effects_by_label: dict[str, list[float]] = {
        "mean - 1 SD": [],
        "mean": [],
        "mean + 1 SD": [],
    }
    index_values: list[float] = []
    points = {
        "mean - 1 SD": -moderator_sd,
        "mean": 0.0,
        "mean + 1 SD": moderator_sd,
    }

    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, len(frame), size=len(frame))].reset_index(
            drop=True
        )
        mediator_model = ols_coefficients(
            sample,
            "m",
            ["x_centered", "w_centered", "x_centered:w_centered", *covariates],
        )
        outcome_model = ols_coefficients(
            sample,
            "y",
            ["x_centered", "m", *covariates],
        )
        a1 = mediator_model["x_centered"]
        a3 = mediator_model["x_centered:w_centered"]
        b = outcome_model["m"]
        for label, centered_value in points.items():
            effects_by_label[label].append((a1 + a3 * centered_value) * b)
        index_values.append(a3 * b)

    alpha = 1.0 - ci
    percentiles = [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)]
    effect_cis = {
        label: tuple(np.percentile(values, percentiles))
        for label, values in effects_by_label.items()
    }
    index_ci = tuple(np.percentile(index_values, percentiles))
    return effect_cis, index_ci


def bootstrap_model_14_reference(
    frame: pd.DataFrame,
    *,
    iterations: int,
    seed: int,
    ci: float,
    covariates: list[str] | None = None,
) -> tuple[dict[str, tuple[float, float]], tuple[float, float]]:
    covariates = ["c1"] if covariates is None else covariates
    rng = np.random.default_rng(seed)
    moderator_sd = float(frame["w"].std(ddof=1))
    effects_by_label: dict[str, list[float]] = {
        "mean - 1 SD": [],
        "mean": [],
        "mean + 1 SD": [],
    }
    index_values: list[float] = []
    points = {
        "mean - 1 SD": -moderator_sd,
        "mean": 0.0,
        "mean + 1 SD": moderator_sd,
    }

    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, len(frame), size=len(frame))].reset_index(
            drop=True
        )
        mediator_model = ols_coefficients(sample, "m", ["x_centered", *covariates])
        outcome_model = ols_coefficients(
            sample,
            "y",
            ["x_centered", "m", "w_centered", "m:w_centered", *covariates],
        )
        a = mediator_model["x_centered"]
        b1 = outcome_model["m"]
        b3 = outcome_model["m:w_centered"]
        for label, centered_value in points.items():
            effects_by_label[label].append(a * (b1 + b3 * centered_value))
        index_values.append(a * b3)

    alpha = 1.0 - ci
    percentiles = [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)]
    effect_cis = {
        label: tuple(np.percentile(values, percentiles))
        for label, values in effects_by_label.items()
    }
    index_ci = tuple(np.percentile(index_values, percentiles))
    return effect_cis, index_ci


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"model": 7, "x": "x", "mediator": "m", "moderator": "w", "y": "y"})

    with pytest.raises(ValueError, match="unknown moderated_mediation params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "model": 7, "x": "x"})


def test_moderated_mediation_bootstrap_defaults_to_user_facing_5000_iterations() -> None:
    params = _params()
    params.pop("bootstrap")

    validated = _step_cls().validate_params(params)

    assert validated["bootstrap"]["iterations"] == 5000


def test_model_7_reports_conditional_indirect_effects_and_index() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    result = run_step(dataset_factory(frame), _params(model=7))

    mediator_model = ols_coefficients(
        ref,
        "m",
        ["x_centered", "w_centered", "x_centered:w_centered", "c1"],
    )
    outcome_model = ols_coefficients(ref, "y", ["x_centered", "m", "c1"])
    moderator_sd = float(ref["w"].std(ddof=1))
    expected = {
        "mean - 1 SD": (
            mediator_model["x_centered"]
            + mediator_model["x_centered:w_centered"] * -moderator_sd
        )
        * outcome_model["m"],
        "mean": mediator_model["x_centered"] * outcome_model["m"],
        "mean + 1 SD": (
            mediator_model["x_centered"]
            + mediator_model["x_centered:w_centered"] * moderator_sd
        )
        * outcome_model["m"],
    }
    expected_index = mediator_model["x_centered:w_centered"] * outcome_model["m"]

    assert result.analysis_key == "moderated_mediation"
    assert result.model == 7
    assert result.n_used == 32
    assert {effect.moderator_label: effect.effect for effect in result.conditional_effects} == pytest.approx(
        expected,
        abs=1e-10,
    )
    assert result.index_of_moderated_mediation == pytest.approx(expected_index, abs=1e-10)
    assert result.index_ci[0] < result.index_of_moderated_mediation < result.index_ci[1]
    assert all(effect.ci[0] < effect.effect < effect.ci[1] for effect in result.conditional_effects)


def test_model_7_bootstrap_cis_match_independent_percentile_reference() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    params = _params(model=7)

    result = run_step(dataset_factory(frame), params)
    effect_cis, index_ci = bootstrap_model_7_reference(
        ref,
        iterations=params["bootstrap"]["iterations"],
        seed=params["bootstrap"]["seed"],
        ci=params["bootstrap"]["ci"],
    )

    assert result.index_ci == pytest.approx(index_ci, abs=1e-10)
    assert any("1000회 미만" in warning for warning in result.warnings_ko)
    actual_effect_cis = {
        effect.moderator_label: effect.ci for effect in result.conditional_effects
    }
    assert actual_effect_cis == pytest.approx(effect_cis, abs=1e-10)


def test_model_7_listwise_missing_rows_match_complete_case_reference() -> None:
    frame = moderated_frame()
    frame.loc[1, "x"] = np.nan
    frame.loc[5, "w"] = np.nan
    frame.loc[9, "m"] = np.nan
    frame.loc[12, "y"] = np.nan
    frame.loc[17, "c1"] = np.nan
    complete = frame.dropna(axis=0, how="any").copy()
    ref = centered_reference_frame(complete)
    params = _params(model=7)

    result = run_step(dataset_factory(frame), params)

    mediator_model = ols_coefficients(
        ref,
        "m",
        ["x_centered", "w_centered", "x_centered:w_centered", "c1"],
    )
    outcome_model = ols_coefficients(ref, "y", ["x_centered", "m", "c1"])
    moderator_sd = float(ref["w"].std(ddof=1))
    expected = {
        "mean - 1 SD": (
            mediator_model["x_centered"]
            + mediator_model["x_centered:w_centered"] * -moderator_sd
        )
        * outcome_model["m"],
        "mean": mediator_model["x_centered"] * outcome_model["m"],
        "mean + 1 SD": (
            mediator_model["x_centered"]
            + mediator_model["x_centered:w_centered"] * moderator_sd
        )
        * outcome_model["m"],
    }
    effect_cis, index_ci = bootstrap_model_7_reference(
        ref,
        iterations=params["bootstrap"]["iterations"],
        seed=params["bootstrap"]["seed"],
        ci=params["bootstrap"]["ci"],
    )

    assert result.n_total == 32
    assert result.n_used == 27
    assert result.n_excluded == 5
    assert {effect.moderator_label: effect.effect for effect in result.conditional_effects} == pytest.approx(
        expected,
        abs=1e-10,
    )
    assert result.index_ci == pytest.approx(index_ci, abs=1e-10)
    actual_effect_cis = {
        effect.moderator_label: effect.ci for effect in result.conditional_effects
    }
    assert actual_effect_cis == pytest.approx(effect_cis, abs=1e-10)


def test_model_14_reports_conditional_indirect_effects_and_index() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    result = run_step(dataset_factory(frame), _params(model=14))

    mediator_model = ols_coefficients(ref, "m", ["x_centered", "c1"])
    outcome_model = ols_coefficients(
        ref,
        "y",
        ["x_centered", "m", "w_centered", "m:w_centered", "c1"],
    )
    moderator_sd = float(ref["w"].std(ddof=1))
    expected = {
        "mean - 1 SD": mediator_model["x_centered"]
        * (outcome_model["m"] + outcome_model["m:w_centered"] * -moderator_sd),
        "mean": mediator_model["x_centered"] * outcome_model["m"],
        "mean + 1 SD": mediator_model["x_centered"]
        * (outcome_model["m"] + outcome_model["m:w_centered"] * moderator_sd),
    }
    expected_index = mediator_model["x_centered"] * outcome_model["m:w_centered"]

    assert result.model == 14
    assert {effect.moderator_label: effect.effect for effect in result.conditional_effects} == pytest.approx(
        expected,
        abs=1e-10,
    )
    assert result.index_of_moderated_mediation == pytest.approx(expected_index, abs=1e-10)
    assert result.index_ci[0] < result.index_of_moderated_mediation < result.index_ci[1]


def test_model_14_bootstrap_cis_match_independent_percentile_reference() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    params = _params(model=14)

    result = run_step(dataset_factory(frame), params)
    effect_cis, index_ci = bootstrap_model_14_reference(
        ref,
        iterations=params["bootstrap"]["iterations"],
        seed=params["bootstrap"]["seed"],
        ci=params["bootstrap"]["ci"],
    )

    assert result.index_ci == pytest.approx(index_ci, abs=1e-10)
    actual_effect_cis = {
        effect.moderator_label: effect.ci for effect in result.conditional_effects
    }
    assert actual_effect_cis == pytest.approx(effect_cis, abs=1e-10)


def test_model_14_without_covariates_matches_independent_reference() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    params = {**_params(model=14), "covariates": []}

    result = run_step(dataset_factory(frame), params)

    mediator_model = ols_coefficients(ref, "m", ["x_centered"])
    outcome_model = ols_coefficients(
        ref,
        "y",
        ["x_centered", "m", "w_centered", "m:w_centered"],
    )
    moderator_sd = float(ref["w"].std(ddof=1))
    expected = {
        "mean - 1 SD": mediator_model["x_centered"]
        * (outcome_model["m"] + outcome_model["m:w_centered"] * -moderator_sd),
        "mean": mediator_model["x_centered"] * outcome_model["m"],
        "mean + 1 SD": mediator_model["x_centered"]
        * (outcome_model["m"] + outcome_model["m:w_centered"] * moderator_sd),
    }
    effect_cis, index_ci = bootstrap_model_14_reference(
        ref,
        iterations=params["bootstrap"]["iterations"],
        seed=params["bootstrap"]["seed"],
        ci=params["bootstrap"]["ci"],
        covariates=[],
    )

    assert result.covariates == ()
    assert {effect.moderator_label: effect.effect for effect in result.conditional_effects} == pytest.approx(
        expected,
        abs=1e-10,
    )
    assert result.index_ci == pytest.approx(index_ci, abs=1e-10)
    actual_effect_cis = {
        effect.moderator_label: effect.ci for effect in result.conditional_effects
    }
    assert actual_effect_cis == pytest.approx(effect_cis, abs=1e-10)


def test_validation_rejects_unsupported_model_duplicate_roles_and_non_scale() -> None:
    frame = moderated_frame()
    dataset = dataset_factory(frame)

    with pytest.raises(ValueError, match="model must be 7 or 14"):
        run_step(dataset, _params(model=8))

    with pytest.raises(ValueError, match="distinct"):
        run_step(dataset, {**_params(), "moderator": "x"})

    nominal_dataset = dataset_factory(frame, measures={"w": Measure.NOMINAL})
    with pytest.raises(ValueError, match="scale"):
        run_step(nominal_dataset, _params())

    with pytest.raises(ValueError, match="center"):
        run_step(dataset, {**_params(), "center": "none"})


def test_moderated_mediation_rejects_ill_conditioned_interaction_design() -> None:
    frame = moderated_frame()
    ref = centered_reference_frame(frame)
    frame["near_interaction"] = ref["x_centered:w_centered"] + (
        1e-12 * np.sin(np.arange(len(frame)) * 1.3)
    )

    with pytest.raises(ValueError, match="ill-conditioned"):
        run_step(
            dataset_factory(frame),
            {**_params(model=7), "covariates": ["c1", "near_interaction"]},
        )
