from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Step, Variable
from modori.core.model import step_class_for_type
from modori.logistic_regression_results import (
    BinaryClassificationTable,
    CalibrationBin,
    LogisticCoefficientRow,
)
from modori.steps.logistic_regression import (
    BinaryLogisticRegressionStep,
    prepare_logistic_inputs,
)


def _variable(
    name: str,
    *,
    measure: Measure,
    value_labels: dict[float, str] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels=value_labels or {},
        missing_values=[],
        dtype="float" if measure is Measure.SCALE else "string",
        origin_step_id="fixture",
    )


def _dataset(frame: pd.DataFrame, measures: dict[str, Measure]) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            column: _variable(
                column,
                measure=measures.get(column, Measure.SCALE),
                value_labels={0.0: "미발생", 1.0: "발생"} if column == "event" else None,
            )
            for column in frame.columns
        },
    )


def _overlap_frame() -> pd.DataFrame:
    x = np.linspace(-3.0, 3.0, 24)
    event = np.asarray([0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1] * 2)
    group = np.asarray(["control", "treat", "placebo"] * 8)
    return pd.DataFrame({"event": event, "x": x, "group": group})


def _params(**overrides: object) -> dict[str, object]:
    params: dict[str, object] = {
        "schema_version": 1,
        "outcome": "event",
        "event_value": 1,
        "predictors": ["x"],
        "logistic_policy": {
            "preset": "conservative",
            "classification_threshold": 0.5,
            "calibration_bins": 10,
            "categorical_predictors": {},
        },
        "language": "ko",
    }
    params.update(overrides)
    return params


def test_logistic_schema_migrates_legacy_and_rejects_newer_or_unknown() -> None:
    legacy = _params()
    legacy.pop("schema_version")

    assert BinaryLogisticRegressionStep.migrate_params(legacy)["schema_version"] == 1

    with pytest.raises(ValueError, match="newer schema_version"):
        BinaryLogisticRegressionStep.migrate_params(
            _params(schema_version=999)
        )
    with pytest.raises(ValueError, match="unknown logistic_regression params"):
        BinaryLogisticRegressionStep.validate_params(
            {**_params(), "extra": "bad"}
        )


def test_completed_logistic_step_is_registered_and_serializable() -> None:
    assert step_class_for_type("stats.logistic_regression") is BinaryLogisticRegressionStep
    restored = Step.from_dict(
        {
            "type": "stats.logistic_regression",
            "id": "logit",
            "title": "Binary logistic regression",
            "params": _params(),
            "input_step_ids": [],
        }
    )

    assert isinstance(restored, BinaryLogisticRegressionStep)
    assert restored.reads() == {"event", "x"}
    assert restored.writes() == {"analysis:logit"}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(outcome=""), "outcome"),
        (lambda p: p.update(predictors=[]), "predictors"),
        (lambda p: p.update(predictors=["x", "x"]), "unique"),
        (lambda p: p.update(predictors=["event"]), "cannot also be a predictor"),
        (lambda p: p.update(event_value=None), "event_value"),
        (lambda p: p.update(language="fr"), "language"),
        (
            lambda p: p["logistic_policy"].update(classification_threshold=1.0),
            "strictly between 0 and 1",
        ),
        (
            lambda p: p["logistic_policy"].update(calibration_bins=2),
            "between 3 and 20",
        ),
        (
            lambda p: p["logistic_policy"].update(unknown=True),
            "unknown logistic_policy keys",
        ),
    ],
)
def test_logistic_schema_rejects_invalid_structural_contracts(mutate, message: str) -> None:
    params = _params()
    mutate(params)

    with pytest.raises(ValueError, match=message):
        BinaryLogisticRegressionStep.validate_params(params)


def test_prepare_logistic_inputs_maps_explicit_event_and_declared_category_order() -> None:
    frame = _overlap_frame()
    dataset = _dataset(frame, {"event": Measure.ORDINAL, "group": Measure.NOMINAL})
    params = _params(
        predictors=["x", "group"],
        logistic_policy={
            "preset": "conservative",
            "classification_threshold": 0.4,
            "calibration_bins": 8,
            "categorical_predictors": {
                "group": {
                    "reference": "control",
                    "levels": ["control", "treat", "placebo"],
                }
            },
        },
    )

    prepared = prepare_logistic_inputs(dataset, params)

    assert prepared.event_value == 1
    assert prepared.non_event_value == 0
    assert prepared.event_label == "발생"
    assert prepared.non_event_label == "미발생"
    assert prepared.n_total == prepared.n_obs == 24
    assert prepared.event_count == prepared.non_event_count == 12
    assert prepared.threshold == 0.4
    assert prepared.calibration_bins == 8
    assert prepared.term_names == (
        "(Intercept)",
        "x",
        "group[T.treat]",
        "group[T.placebo]",
    )
    assert prepared.y.tolist() == frame["event"].astype(float).tolist()
    assert prepared.preconditioned.scaled.shape == (24, 4)


def test_prepare_logistic_inputs_applies_metadata_missing_values_listwise() -> None:
    frame = _overlap_frame()
    frame.loc[0, "event"] = 99
    frame.loc[1, "x"] = np.nan
    dataset = _dataset(frame, {"event": Measure.ORDINAL, "group": Measure.NOMINAL})
    dataset.variables["event"].missing_values.append(99.0)

    prepared = prepare_logistic_inputs(dataset, _params())

    assert prepared.n_total == 24
    assert prepared.n_obs == 22
    assert prepared.n_dropped == 2


@pytest.mark.parametrize(
    ("frame_mutator", "params_mutator", "message"),
    [
        (
            lambda frame: frame.assign(event=np.arange(len(frame)) % 3),
            lambda params: None,
            "exactly two",
        ),
        (
            lambda frame: frame,
            lambda params: params.update(event_value=2),
            "event_value is not an observed outcome level",
        ),
        (
            lambda frame: frame.assign(event=np.arange(len(frame)) % 2 == 0),
            lambda params: params.update(event_value=1),
            "event_value is not an observed outcome level",
        ),
        (
            lambda frame: frame.assign(group=np.where(np.arange(len(frame)) == 0, "other", frame["group"])),
            lambda params: params.update(
                predictors=["x", "group"],
                logistic_policy={
                    "preset": "conservative",
                    "classification_threshold": 0.5,
                    "calibration_bins": 10,
                    "categorical_predictors": {
                        "group": {
                            "reference": "control",
                            "levels": ["control", "treat", "placebo"],
                        }
                    },
                },
            ),
            "observed levels do not match",
        ),
    ],
)
def test_prepare_logistic_inputs_rejects_outcome_and_level_ambiguity(
    frame_mutator,
    params_mutator,
    message: str,
) -> None:
    frame = frame_mutator(_overlap_frame())
    dataset = _dataset(frame, {"event": Measure.ORDINAL, "group": Measure.NOMINAL})
    params = _params()
    params_mutator(params)

    with pytest.raises(ValueError, match=message):
        prepare_logistic_inputs(dataset, params)


def test_prepare_logistic_inputs_rejects_small_classes_and_separation() -> None:
    small = _overlap_frame()
    small["event"] = np.asarray([0] * 15 + [1] * 9)
    with pytest.raises(ValueError, match="at least 10 events and 10 non-events"):
        prepare_logistic_inputs(
            _dataset(small, {"event": Measure.ORDINAL, "group": Measure.NOMINAL}),
            _params(),
        )

    separated = pd.DataFrame(
        {
            "event": [0] * 12 + [1] * 12,
            "x": list(range(-12, 0)) + list(range(1, 13)),
        }
    )
    with pytest.raises(ValueError, match="complete separation"):
        prepare_logistic_inputs(
            _dataset(separated, {"event": Measure.ORDINAL}),
            _params(),
        )


def test_result_rows_reject_invalid_bounds_and_inconsistent_counts() -> None:
    with pytest.raises(ValueError, match="ordered"):
        LogisticCoefficientRow(
            name="x",
            b=0.5,
            se=0.2,
            wald_z=2.5,
            wald_chi_square=6.25,
            p_value=0.01,
            odds_ratio=np.exp(0.5),
            ci=(0.7, 0.3),
            odds_ratio_ci=(1.1, 2.0),
        )
    with pytest.raises(ValueError, match="confusion counts"):
        BinaryClassificationTable(
            threshold=0.5,
            tn=-1,
            fp=1,
            fn=1,
            tp=1,
            sensitivity=0.5,
            specificity=0.5,
            positive_predictive_value=0.5,
            negative_predictive_value=0.5,
            accuracy=0.5,
        )
    with pytest.raises(ValueError, match="probability bounds"):
        CalibrationBin(
            index=1,
            probability_lower=0.8,
            probability_upper=0.2,
            count=10,
            events=4,
            mean_predicted=0.4,
            observed_rate=0.4,
        )


def test_result_rows_reject_formula_inconsistent_derived_values() -> None:
    with pytest.raises(ValueError, match="odds-ratio CI must equal exp"):
        LogisticCoefficientRow(
            name="x",
            b=0.5,
            se=0.2,
            wald_z=2.5,
            wald_chi_square=6.25,
            p_value=0.01,
            odds_ratio=np.exp(0.5),
            ci=(0.1, 0.9),
            odds_ratio_ci=(1.0, 2.0),
        )
    with pytest.raises(ValueError, match="sensitivity is inconsistent"):
        BinaryClassificationTable(
            threshold=0.5,
            tn=8,
            fp=2,
            fn=4,
            tp=6,
            sensitivity=0.5,
            specificity=0.8,
            positive_predictive_value=0.75,
            negative_predictive_value=2 / 3,
            accuracy=0.7,
        )
    with pytest.raises(ValueError, match="observed rate is inconsistent"):
        CalibrationBin(
            index=1,
            probability_lower=0.1,
            probability_upper=0.5,
            count=10,
            events=4,
            mean_predicted=0.3,
            observed_rate=0.5,
        )
