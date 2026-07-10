from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.logistic_numerics import (
    PreconditionedDesign,
    detect_logistic_separation,
    precondition_logistic_design,
)
from modori.regression_design import (
    CategoricalEncoding,
    RegressionDesignMatrix,
    build_regression_design_matrix,
)


_TOP_LEVEL_KEYS = {
    "schema_version",
    "outcome",
    "event_value",
    "predictors",
    "logistic_policy",
    "language",
}
_POLICY_KEYS = {
    "preset",
    "classification_threshold",
    "calibration_bins",
    "categorical_predictors",
}


def _python_scalar(value: object) -> bool | int | float | str:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("Logistic scalar values must be finite")
        return value
    if isinstance(value, str):
        return value
    raise ValueError("Logistic scalar values must be bool, int, float, or string")


def _scalar_key(value: object) -> tuple[str, object]:
    scalar = _python_scalar(value)
    if isinstance(scalar, bool):
        return "bool", scalar
    if isinstance(scalar, int | float):
        return "number", float(scalar)
    return "string", scalar


def _display_label(dataset: Dataset, variable: str, value: object) -> str:
    scalar = _python_scalar(value)
    labels = dataset.variables[variable].value_labels
    if not isinstance(scalar, bool) and isinstance(scalar, int | float):
        label = labels.get(float(scalar))
        if label is not None:
            return str(label)
    return str(scalar)


@dataclass(frozen=True)
class PreparedLogisticInputs:
    outcome: str
    predictors: tuple[str, ...]
    event_value: bool | int | float | str
    non_event_value: bool | int | float | str
    event_label: str
    non_event_label: str
    frame: pd.DataFrame
    y: np.ndarray
    design: RegressionDesignMatrix
    preconditioned: PreconditionedDesign
    term_names: tuple[str, ...]
    n_obs: int
    n_total: int
    n_dropped: int
    event_count: int
    non_event_count: int
    threshold: float
    calibration_bins: int
    language: str
    categorical_encodings: dict[str, CategoricalEncoding]


class BinaryLogisticRegressionStep(Step):
    step_type = "stats.logistic_regression"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "outcome": "event",
            "event_value": 1,
            "predictors": ["x"],
            "logistic_policy": {"preset": "conservative"},
            "language": "ko",
        },
        "legacy": {
            "outcome": "event",
            "event_value": 1,
            "predictors": ["x"],
            "logistic_policy": {"preset": "conservative"},
            "language": "ko",
        },
        "newer": {
            "schema_version": 999,
            "outcome": "event",
            "event_value": 1,
            "predictors": ["x"],
        },
        "unknown_current": {
            "schema_version": 1,
            "outcome": "event",
            "event_value": 1,
            "predictors": ["x"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        migrated = dict(params)
        version = migrated.get("schema_version")
        if version is None:
            migrated["schema_version"] = cls.CURRENT_SCHEMA_VERSION
            return migrated
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("logistic_regression schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("logistic_regression params use a newer schema_version")
        if version < cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported logistic_regression schema_version: {version}")
        return migrated

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        unknown = set(params) - _TOP_LEVEL_KEYS
        if unknown:
            raise ValueError(
                f"unknown logistic_regression params: {', '.join(sorted(unknown))}"
            )
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("logistic_regression params were not migrated")
        outcome = params.get("outcome")
        if not isinstance(outcome, str) or not outcome.strip():
            raise ValueError("logistic_regression outcome must be a non-empty string")
        predictors = params.get("predictors")
        if not isinstance(predictors, list) or not predictors or not all(
            isinstance(item, str) and item.strip() for item in predictors
        ):
            raise ValueError("logistic_regression predictors must be a non-empty list of strings")
        clean_predictors = [str(item).strip() for item in predictors]
        if len(set(clean_predictors)) != len(clean_predictors):
            raise ValueError("logistic_regression predictors must be unique")
        if outcome.strip() in clean_predictors:
            raise ValueError("logistic_regression outcome cannot also be a predictor")
        if "event_value" not in params or params.get("event_value") is None:
            raise ValueError("logistic_regression event_value must be explicit")
        event_value = _python_scalar(params["event_value"])
        language = params.get("language", "ko")
        if language not in {"ko", "en"}:
            raise ValueError("logistic_regression language must be 'ko' or 'en'")
        policy = params.get("logistic_policy", {})
        if not isinstance(policy, Mapping):
            raise ValueError("logistic_regression logistic_policy must be an object")
        clean_policy = _validate_policy(policy)
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "outcome": outcome.strip(),
            "event_value": event_value,
            "predictors": clean_predictors,
            "logistic_policy": clean_policy,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        raise RuntimeError("Logistic regression fitting is not registered until inference is complete.")

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(params["outcome"]), *[str(item) for item in params["predictors"]]}

    def writes(self) -> set[str]:
        return {f"analysis:{self.id}"}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return (
            f"Binary logistic regression {params['outcome']} on "
            f"{', '.join(str(item) for item in params['predictors'])}"
        )


def _validate_policy(policy: Mapping[str, object]) -> dict[str, object]:
    unknown = set(policy) - _POLICY_KEYS
    if unknown:
        raise ValueError(f"unknown logistic_policy keys: {', '.join(sorted(unknown))}")
    preset = policy.get("preset", "conservative")
    if preset != "conservative":
        raise ValueError("logistic_policy preset must be 'conservative'")
    threshold = float(policy.get("classification_threshold", 0.5))
    if not np.isfinite(threshold) or not 0.0 < threshold < 1.0:
        raise ValueError("classification_threshold must be strictly between 0 and 1")
    bins = policy.get("calibration_bins", 10)
    if not isinstance(bins, int) or isinstance(bins, bool) or not 3 <= bins <= 20:
        raise ValueError("calibration_bins must be an integer between 3 and 20")
    raw_categorical = policy.get("categorical_predictors", {})
    if not isinstance(raw_categorical, Mapping):
        raise ValueError("categorical_predictors must be an object")
    categorical: dict[str, dict[str, object]] = {}
    for raw_variable, raw_spec in raw_categorical.items():
        variable = str(raw_variable).strip()
        if not variable or not isinstance(raw_spec, Mapping):
            raise ValueError("categorical predictor specs must be named objects")
        if set(raw_spec) != {"reference", "levels"}:
            raise ValueError(
                f"categorical predictor {variable} requires exactly reference and levels"
            )
        levels_raw = raw_spec.get("levels")
        if not isinstance(levels_raw, list) or len(levels_raw) < 2:
            raise ValueError(f"categorical predictor {variable} levels must contain at least two")
        levels = [str(level) for level in levels_raw]
        if len(set(levels)) != len(levels):
            raise ValueError(f"categorical predictor {variable} levels must be unique")
        reference = str(raw_spec.get("reference"))
        if reference not in levels:
            raise ValueError(f"categorical predictor {variable} reference must appear in levels")
        categorical[variable] = {"reference": reference, "levels": levels}
    return {
        "preset": "conservative",
        "classification_threshold": threshold,
        "calibration_bins": bins,
        "categorical_predictors": categorical,
    }


def _categorical_encodings(
    policy: Mapping[str, object],
    predictors: tuple[str, ...],
) -> dict[str, CategoricalEncoding]:
    raw = policy["categorical_predictors"]
    assert isinstance(raw, Mapping)
    extra = set(raw) - set(predictors)
    if extra:
        raise ValueError(
            f"categorical encoding declared for non-predictor: {', '.join(sorted(extra))}"
        )
    return {
        str(variable): CategoricalEncoding(
            variable=str(variable),
            reference=str(spec["reference"]),
            levels=tuple(str(level) for level in spec["levels"]),
        )
        for variable, spec in raw.items()
        if isinstance(spec, Mapping)
    }


def prepare_logistic_inputs(
    dataset: Dataset,
    raw_params: Mapping[str, object],
) -> PreparedLogisticInputs:
    params = BinaryLogisticRegressionStep.validate_params(
        BinaryLogisticRegressionStep.migrate_params(dict(raw_params))
    )
    outcome = str(params["outcome"])
    predictors = tuple(str(item) for item in params["predictors"])
    requested = [outcome, *predictors]
    missing = set(requested) - set(dataset.variables)
    if missing:
        raise ValueError(f"Logistic variables are not present: {', '.join(sorted(missing))}")
    policy = params["logistic_policy"]
    assert isinstance(policy, Mapping)
    categorical = _categorical_encodings(policy, predictors)

    for predictor in predictors:
        if predictor in categorical:
            continue
        variable = dataset.variables[predictor]
        if variable.measure is not Measure.SCALE:
            raise ValueError(
                f"Logistic predictor {predictor} must be SCALE or explicitly categorical"
            )
        series = dataset.frame_for_compute([predictor])[predictor].dropna()
        if not pd.api.types.is_numeric_dtype(series):
            raise ValueError(f"Logistic scale predictor {predictor} must be numeric")

    frame = dataset.frame_for_compute(requested).dropna(axis=0, how="any")
    n_total = int(len(dataset.df))
    n_obs = int(len(frame))
    n_dropped = n_total - n_obs
    if n_obs == 0:
        raise ValueError("Logistic regression has no complete observations")

    raw_levels = [_python_scalar(value) for value in pd.unique(frame[outcome])]
    level_by_key: dict[tuple[str, object], bool | int | float | str] = {}
    for level in raw_levels:
        key = _scalar_key(level)
        if key in level_by_key:
            raise ValueError("Logistic outcome levels are ambiguous after numeric normalization")
        level_by_key[key] = level
    if len(level_by_key) != 2:
        raise ValueError("Logistic outcome must contain exactly two complete-case levels")
    event_key = _scalar_key(params["event_value"])
    if event_key not in level_by_key:
        raise ValueError("Logistic event_value is not an observed outcome level")
    event_value = level_by_key[event_key]
    non_event_value = next(value for key, value in level_by_key.items() if key != event_key)
    y = np.asarray(
        [1.0 if _scalar_key(value) == event_key else 0.0 for value in frame[outcome]],
        dtype=float,
    )
    event_count = int(np.sum(y))
    non_event_count = n_obs - event_count
    if event_count < 10 or non_event_count < 10:
        raise ValueError("Logistic regression requires at least 10 events and 10 non-events")

    for predictor, encoding in categorical.items():
        observed_raw = [_python_scalar(value) for value in pd.unique(frame[predictor])]
        observed_labels = [str(value) for value in observed_raw]
        if len(set(observed_labels)) != len(observed_raw):
            raise ValueError(
                f"Logistic categorical predictor {predictor} has ambiguous display levels"
            )
        if set(observed_labels) != set(encoding.levels):
            raise ValueError(
                f"Logistic categorical predictor {predictor} observed levels do not match declared levels"
            )

    design = build_regression_design_matrix(
        frame=frame,
        predictors=predictors,
        categorical_encodings=categorical,
        interactions=(),
        center_scale_interactions=False,
        error_prefix="Logistic",
    )
    x = np.column_stack(
        [np.ones(n_obs, dtype=float), design.x_pred.to_numpy(dtype=float)]
    )
    if not np.all(np.isfinite(x)):
        raise ValueError("Logistic design matrix must contain finite values")
    if n_obs <= x.shape[1]:
        raise ValueError("Logistic regression requires more observations than parameters")
    if np.linalg.matrix_rank(x) < x.shape[1]:
        raise ValueError("Logistic design matrix is rank deficient")
    preconditioned = precondition_logistic_design(x)
    separation = detect_logistic_separation(preconditioned.scaled, y)
    if separation == "complete":
        raise ValueError("Logistic regression has complete separation; finite MLE is undefined")
    if separation == "quasi_complete":
        raise ValueError("Logistic regression has quasi-complete separation; finite MLE is undefined")

    return PreparedLogisticInputs(
        outcome=outcome,
        predictors=predictors,
        event_value=event_value,
        non_event_value=non_event_value,
        event_label=_display_label(dataset, outcome, event_value),
        non_event_label=_display_label(dataset, outcome, non_event_value),
        frame=frame,
        y=y,
        design=design,
        preconditioned=preconditioned,
        term_names=("(Intercept)", *tuple(design.x_pred.columns)),
        n_obs=n_obs,
        n_total=n_total,
        n_dropped=n_dropped,
        event_count=event_count,
        non_event_count=non_event_count,
        threshold=float(policy["classification_threshold"]),
        calibration_bins=int(policy["calibration_bins"]),
        language=str(params["language"]),
        categorical_encodings=categorical,
    )
