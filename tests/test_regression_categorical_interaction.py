import numpy as np
import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, Variable
from modori.steps import MultipleRegressionStep


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


def regression_dataset(frame: pd.DataFrame, *, measures: dict[str, Measure]) -> Dataset:
    variables = {
        column: variable(
            column,
            measure=measures.get(column, Measure.SCALE),
            dtype="float" if pd.api.types.is_numeric_dtype(frame[column]) else "string",
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def ols_reference(y: pd.Series, design: pd.DataFrame) -> dict[str, np.ndarray]:
    y_arr = y.to_numpy(dtype=float)
    x_arr = np.column_stack([np.ones(len(design)), design.to_numpy(dtype=float)])
    coefficients, *_ = np.linalg.lstsq(x_arr, y_arr, rcond=None)
    residuals = y_arr - x_arr @ coefficients
    df_resid = len(y_arr) - x_arr.shape[1]
    sigma2 = float((residuals @ residuals) / df_resid)
    covariance = sigma2 * np.linalg.inv(x_arr.T @ x_arr)
    se = np.sqrt(np.diag(covariance))
    t_values = coefficients / se
    p_values = 2 * stats.t.sf(np.abs(t_values), df_resid)
    return {
        "coefficients": coefficients,
        "covariance": covariance,
        "se": se,
        "p_values": p_values,
        "df_resid": np.array([df_resid], dtype=float),
    }


def categorical_frame() -> pd.DataFrame:
    x = np.array([1.0, 2.0, 3.5, 4.0, 5.0, 6.5, 7.0, 8.0, 9.5, 10.0, 11.0, 12.5])
    group = np.array(
        [
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
        ]
    )
    group_effect = {"control": 0.0, "treat": 1.5, "placebo": -0.75}
    noise = np.array([0.2, -0.1, 0.05, -0.25, 0.1, -0.05, 0.18, -0.12, 0.08, -0.18, 0.15, -0.07])
    y = 4.0 + (0.7 * x) + np.array([group_effect[value] for value in group]) + noise
    return pd.DataFrame({"y": y, "x": x, "group": group})


def categorical_policy() -> dict[str, object]:
    return {
        "preset": "classic",
        "categorical_predictors": {
            "group": {"reference": "control", "levels": ["control", "treat", "placebo"]}
        },
    }


def test_categorical_predictor_requires_explicit_reference_levels() -> None:
    frame = categorical_frame()
    step = MultipleRegressionStep(
        id="reg-categorical-missing-policy",
        title="Categorical missing policy",
        params={
            "dv": "y",
            "predictors": ["x", "group"],
            "regression_policy": {"preset": "classic"},
        },
    )

    with pytest.raises(ValueError, match="categorical predictor group requires explicit encoding"):
        step.compute_context_free(
            regression_dataset(frame, measures={"group": Measure.NOMINAL})
        )


def test_categorical_predictor_uses_declared_reference_and_stable_dummy_rows() -> None:
    frame = categorical_frame()
    step = MultipleRegressionStep(
        id="reg-categorical",
        title="Categorical",
        params={
            "dv": "y",
            "predictors": ["x", "group"],
            "regression_policy": categorical_policy(),
        },
    )

    result = step.compute_context_free(
        regression_dataset(frame, measures={"group": Measure.NOMINAL})
    ).analysis

    design = pd.DataFrame(
        {
            "x": frame["x"],
            "group[T.treat]": (frame["group"] == "treat").astype(float),
            "group[T.placebo]": (frame["group"] == "placebo").astype(float),
        }
    )
    reference = ols_reference(frame["y"], design)

    assert [row.name for row in result.coefficients] == [
        "(Intercept)",
        "x",
        "group[T.treat]",
        "group[T.placebo]",
    ]
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference["coefficients"], abs=1e-10
    )
    treat_row = result.coefficients[2]
    assert treat_row.term_type == "categorical_level"
    assert treat_row.source_variable == "group"
    assert treat_row.level == "treat"
    assert treat_row.reference_level == "control"
    assert result.diagnostics["vif"].keys() == {"x", "group[T.treat]", "group[T.placebo]"}
    assert result.chart_spec.data["rows"][1]["name"] == "group[T.treat]"


def interaction_frame() -> pd.DataFrame:
    x = np.array([-3.0, -2.5, -1.5, -1.0, -0.2, 0.4, 1.1, 1.8, 2.6, 3.4, 4.2, 5.0])
    z = np.array([8.0, 6.5, 7.2, 5.8, 4.9, 6.1, 3.5, 4.2, 2.8, 3.1, 1.9, 2.4])
    noise = np.array([0.1, -0.2, 0.05, 0.15, -0.08, 0.04, -0.12, 0.2, -0.05, 0.07, -0.15, 0.11])
    y = 10.0 + (1.2 * x) - (0.45 * z) + (0.55 * x * z) + noise
    return pd.DataFrame({"y": y, "x": x, "z": z})


def test_scale_interaction_requires_explicit_mean_centering_policy() -> None:
    frame = interaction_frame()
    step = MultipleRegressionStep(
        id="reg-interaction-no-centering",
        title="Interaction without centering",
        params={
            "dv": "y",
            "predictors": ["x", "z"],
            "regression_policy": {
                "preset": "classic",
                "interactions": [{"terms": ["x", "z"]}],
            },
        },
    )

    with pytest.raises(ValueError, match="scale interactions require explicit mean centering"):
        step.compute_context_free(regression_dataset(frame, measures={}))


def test_scale_scale_interaction_adds_centered_terms_and_simple_slopes_at_mean_sd() -> None:
    frame = interaction_frame()
    step = MultipleRegressionStep(
        id="reg-scale-interaction",
        title="Scale interaction",
        params={
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {
                "preset": "classic",
                "center_scale_interactions": "mean",
                "interactions": [{"terms": ["x", "z"]}],
            },
        },
    )

    result = step.compute_context_free(regression_dataset(frame, measures={})).analysis

    x_centered = frame["x"] - frame["x"].mean()
    z_centered = frame["z"] - frame["z"].mean()
    design = pd.DataFrame(
        {
            "x_centered": x_centered,
            "z_centered": z_centered,
            "x_centered:z_centered": x_centered * z_centered,
        }
    )
    reference = ols_reference(frame["y"], design)

    assert result.predictors == ["x", "z"]
    assert [row.name for row in result.coefficients] == [
        "(Intercept)",
        "x_centered",
        "z_centered",
        "x_centered:z_centered",
    ]
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference["coefficients"], abs=1e-10
    )
    assert result.coefficients[1].source_variable == "x"
    assert result.coefficients[1].term_type == "scale_centered"
    assert result.coefficients[3].term_type == "interaction"
    assert result.diagnostics["transformed_terms"]["x"] == "x_centered"
    assert result.diagnostics["transformed_terms"]["z"] == "z_centered"

    coefficient_by_name = {row.name: row.b for row in result.coefficients}
    expected_slopes = {
        "mean - 1 SD": coefficient_by_name["x_centered"]
        + coefficient_by_name["x_centered:z_centered"] * -float(frame["z"].std(ddof=1)),
        "mean": coefficient_by_name["x_centered"],
        "mean + 1 SD": coefficient_by_name["x_centered"]
        + coefficient_by_name["x_centered:z_centered"] * float(frame["z"].std(ddof=1)),
    }
    assert [row.moderator_label for row in result.simple_slopes] == [
        "mean - 1 SD",
        "mean",
        "mean + 1 SD",
    ]
    assert [row.slope for row in result.simple_slopes] == pytest.approx(
        list(expected_slopes.values()), abs=1e-10
    )
    assert all(row.focal_predictor == "x" for row in result.simple_slopes)
    assert all(row.moderator == "z" for row in result.simple_slopes)
    assert all(row.interaction_term == "x_centered:z_centered" for row in result.simple_slopes)


def scale_categorical_interaction_frame() -> pd.DataFrame:
    x = np.array([1.0, 2.0, 3.5, 4.0, 5.0, 6.5, 7.0, 8.0, 9.5, 10.0, 11.0, 12.5])
    group = np.array(
        [
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
        ]
    )
    intercept = {"control": 0.0, "treat": 1.0, "placebo": -0.5}
    slope = {"control": 0.4, "treat": 1.2, "placebo": -0.1}
    noise = np.array([0.12, -0.04, 0.07, -0.1, 0.05, -0.03, 0.09, -0.06, 0.04, -0.08, 0.03, -0.05])
    y = 3.0 + np.array([intercept[value] for value in group])
    y = y + np.array([slope[value] for value in group]) * x + noise
    return pd.DataFrame({"y": y, "x": x, "group": group})


def test_scale_categorical_interaction_reports_level_specific_simple_slopes() -> None:
    frame = scale_categorical_interaction_frame()
    step = MultipleRegressionStep(
        id="reg-scale-categorical-interaction",
        title="Scale by categorical interaction",
        params={
            "dv": "y",
            "predictors": ["x", "group"],
            "regression_policy": {
                **categorical_policy(),
                "center_scale_interactions": "mean",
                "interactions": [{"terms": ["x", "group"]}],
            },
        },
    )

    result = step.compute_context_free(
        regression_dataset(frame, measures={"group": Measure.NOMINAL})
    ).analysis

    x_centered = frame["x"] - frame["x"].mean()
    treat = (frame["group"] == "treat").astype(float)
    placebo = (frame["group"] == "placebo").astype(float)
    design = pd.DataFrame(
        {
            "x_centered": x_centered,
            "group[T.treat]": treat,
            "group[T.placebo]": placebo,
            "x_centered:group[T.treat]": x_centered * treat,
            "x_centered:group[T.placebo]": x_centered * placebo,
        }
    )
    reference = ols_reference(frame["y"], design)
    b_x, b_treat_interaction, b_placebo_interaction = (
        reference["coefficients"][1],
        reference["coefficients"][4],
        reference["coefficients"][5],
    )

    assert [row.name for row in result.coefficients] == [
        "(Intercept)",
        "x_centered",
        "group[T.treat]",
        "group[T.placebo]",
        "x_centered:group[T.treat]",
        "x_centered:group[T.placebo]",
    ]
    assert [row.b for row in result.coefficients] == pytest.approx(
        reference["coefficients"], abs=1e-10
    )
    assert {row.moderator_value: row.slope for row in result.simple_slopes} == pytest.approx(
        {
            "control": b_x,
            "treat": b_x + b_treat_interaction,
            "placebo": b_x + b_placebo_interaction,
        },
        abs=1e-10,
    )
    assert {row.moderator_label for row in result.simple_slopes} == {
        "control (reference)",
        "treat",
        "placebo",
    }


def test_regression_rejects_duplicate_and_unsupported_interactions() -> None:
    frame = interaction_frame()
    duplicate = MultipleRegressionStep(
        id="reg-duplicate-interaction",
        title="Duplicate interaction",
        params={
            "dv": "y",
            "predictors": ["x", "z"],
            "regression_policy": {
                "preset": "classic",
                "center_scale_interactions": "mean",
                "interactions": [{"terms": ["x", "z"]}, {"terms": ["z", "x"]}],
            },
        },
    )

    with pytest.raises(ValueError, match="duplicate interaction"):
        duplicate.compute_context_free(regression_dataset(frame, measures={}))

    unsupported_frame = frame.assign(group="a", segment="b")
    unsupported = MultipleRegressionStep(
        id="reg-unsupported-interaction",
        title="Unsupported interaction",
        params={
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {
                "preset": "classic",
                "categorical_predictors": {
                    "group": {"reference": "a", "levels": ["a", "b"]},
                    "segment": {"reference": "b", "levels": ["b", "c"]},
                },
                "center_scale_interactions": "mean",
                "interactions": [{"terms": ["group", "segment"]}],
            },
        },
    )

    with pytest.raises(ValueError, match="unsupported categorical-by-categorical interaction"):
        unsupported.compute_context_free(
            regression_dataset(
                unsupported_frame,
                measures={"group": Measure.NOMINAL, "segment": Measure.NOMINAL},
            )
        )


def test_requested_simple_slopes_require_supported_interaction() -> None:
    frame = interaction_frame()
    step = MultipleRegressionStep(
        id="reg-simple-slopes-without-interaction",
        title="Simple slopes without interaction",
        params={
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {"preset": "classic", "simple_slopes": True},
        },
    )

    with pytest.raises(ValueError, match="simple slopes require an explicit supported interaction"):
        step.compute_context_free(regression_dataset(frame, measures={}))
