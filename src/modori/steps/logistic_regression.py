from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationWarning

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.logistic_numerics import (
    PreconditionedDesign,
    detect_logistic_separation,
    logistic_fisher_covariance,
    logistic_information_condition_number,
    precondition_logistic_design,
    restore_logistic_parameters,
)
from modori.logistic_regression_results import (
    LOGISTIC_CLASSIFICATION_METRIC_LABELS,
    BinaryClassificationTable,
    CalibrationBin,
    LogisticCoefficientRow,
    LogisticRegressionResult,
    render_logistic_warning,
)
from modori.regression_design import (
    CategoricalEncoding,
    RegressionDesignMatrix,
    TermMetadata,
    build_regression_design_matrix,
    categorical_level_label,
)
from modori.results import ChartSpec
from modori.statistics_numerics import (
    DEFAULT_LOGISTIC_MAX_INFORMATION_CONDITION_NUMBER,
    LOGISTIC_INFORMATION_WARNING_CONDITION_NUMBER,
)
from modori.value_tokens import (
    display_label_key,
    display_value_label,
    normalized_value_key,
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
_MAX_LOG = float(np.log(np.finfo(float).max))
_MIN_LOG = float(np.log(np.finfo(float).tiny))


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
            raise ValueError(
                f"unsupported logistic_regression schema_version: {version}"
            )
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
        if (
            not isinstance(predictors, list)
            or not predictors
            or not all(isinstance(item, str) and item.strip() for item in predictors)
        ):
            raise ValueError(
                "logistic_regression predictors must be a non-empty list of strings"
            )
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
        prepared = prepare_logistic_inputs(ctx.dataset, self.params)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", PerfectSeparationWarning)
                warnings.simplefilter("error", ConvergenceWarning)
                warnings.simplefilter("error", RuntimeWarning)
                fitted = _fit_binomial_glm(prepared.y, prepared.preconditioned.scaled)
                null_fitted = _fit_binomial_glm(
                    prepared.y,
                    np.ones((prepared.n_obs, 1), dtype=float),
                )
        except RuntimeWarning as exc:
            raise ValueError(
                "Logistic regression emitted a numerical warning; inference is undefined."
            ) from exc
        except (PerfectSeparationWarning, ConvergenceWarning) as exc:
            raise ValueError(
                "Logistic regression emitted a separation or convergence warning; inference is undefined."
            ) from exc

        if not bool(getattr(fitted, "converged", False)) or not bool(
            getattr(null_fitted, "converged", False)
        ):
            raise ValueError("Logistic regression did not converge.")
        gamma = _finite_array(fitted.params, "scaled coefficients", ndim=1)
        probabilities = _finite_array(
            fitted.fittedvalues,
            "fitted probabilities",
            ndim=1,
        )
        if np.any(probabilities <= 0.0) or np.any(probabilities >= 1.0):
            raise ValueError(
                "Logistic fitted probabilities must remain strictly between 0 and 1."
            )

        score_residual = _score_infinity_per_observation(
            prepared.preconditioned.scaled,
            prepared.y,
            probabilities,
        )
        if score_residual > 1e-10:
            raise ValueError(
                "Logistic score residual exceeds the convergence policy; inference is undefined."
            )
        information_condition = logistic_information_condition_number(
            prepared.preconditioned.scaled,
            probabilities,
        )
        if information_condition > DEFAULT_LOGISTIC_MAX_INFORMATION_CONDITION_NUMBER:
            raise ValueError(
                "Logistic information matrix is ill-conditioned "
                f"({information_condition:.3g} exceeds "
                f"{DEFAULT_LOGISTIC_MAX_INFORMATION_CONDITION_NUMBER:.3g}); inference is undefined."
            )
        covariance_gamma = _finite_array(
            logistic_fisher_covariance(
                prepared.preconditioned.scaled,
                probabilities,
            ),
            "scaled covariance",
            ndim=2,
        )

        beta, covariance_beta = restore_logistic_parameters(
            gamma,
            covariance_gamma,
            prepared.preconditioned.transform,
        )
        coefficients = _coefficient_rows(
            prepared.term_names,
            beta,
            covariance_beta,
            prepared.design.term_metadata,
        )
        log_likelihood = _finite_float(fitted.llf, "log likelihood")
        null_log_likelihood = _finite_float(null_fitted.llf, "null log likelihood")
        likelihood_ratio = 2.0 * (log_likelihood - null_log_likelihood)
        if likelihood_ratio < -1e-10:
            raise ValueError(
                "Logistic full model likelihood is worse than the null optimum."
            )
        likelihood_ratio = max(0.0, likelihood_ratio)
        likelihood_ratio_df = len(prepared.term_names) - 1
        likelihood_ratio_p = _finite_float(
            stats.chi2.sf(likelihood_ratio, likelihood_ratio_df),
            "likelihood-ratio p-value",
        )
        mcfadden = _finite_float(
            1.0 - (log_likelihood / null_log_likelihood),
            "McFadden R-squared",
        )
        cox_snell = _finite_float(
            1.0
            - np.exp((2.0 / prepared.n_obs) * (null_log_likelihood - log_likelihood)),
            "Cox-Snell R-squared",
        )
        nagelkerke_denominator = 1.0 - np.exp(
            (2.0 / prepared.n_obs) * null_log_likelihood
        )
        if not np.isfinite(nagelkerke_denominator) or nagelkerke_denominator <= 0:
            raise ValueError("Logistic Nagelkerke denominator is undefined.")
        nagelkerke = _finite_float(
            cox_snell / nagelkerke_denominator,
            "Nagelkerke R-squared",
        )

        classification = _classification_table(
            prepared.y,
            probabilities,
            prepared.threshold,
        )
        roc_auc = _finite_float(
            roc_auc_score(prepared.y, probabilities),
            "ROC AUC",
        )
        brier_score = _finite_float(
            brier_score_loss(prepared.y, probabilities),
            "Brier score",
        )
        calibration, effective_calibration_bins = _calibration_bins(
            prepared.y,
            probabilities,
            prepared.calibration_bins,
        )
        minimum_weight = _finite_float(
            np.min(probabilities * (1.0 - probabilities)),
            "minimum fitted weight",
        )
        result_warning_codes, result_warnings = _result_warnings(
            prepared,
            classification=classification,
            coefficients=coefficients,
            information_condition=information_condition,
            minimum_weight=minimum_weight,
            effective_calibration_bins=effective_calibration_bins,
        )
        chart_specs = _chart_specs(
            prepared.y,
            probabilities,
            coefficients,
            calibration,
            language=prepared.language,
        )
        iterations = int(getattr(fitted, "fit_history", {}).get("iteration", -1))
        if iterations < 0:
            raise ValueError("Logistic fit iteration history is missing.")
        result = LogisticRegressionResult(
            outcome=prepared.outcome,
            predictors=prepared.predictors,
            event_value=prepared.event_value,
            non_event_value=prepared.non_event_value,
            event_label=prepared.event_label,
            non_event_label=prepared.non_event_label,
            n_obs=prepared.n_obs,
            n_total=prepared.n_total,
            n_dropped=prepared.n_dropped,
            event_count=prepared.event_count,
            non_event_count=prepared.non_event_count,
            log_likelihood=log_likelihood,
            null_log_likelihood=null_log_likelihood,
            minus_two_log_likelihood=-2.0 * log_likelihood,
            aic=_finite_float(fitted.aic, "AIC"),
            likelihood_ratio_chi_square=likelihood_ratio,
            likelihood_ratio_df=likelihood_ratio_df,
            likelihood_ratio_p_value=likelihood_ratio_p,
            mcfadden_r_squared=mcfadden,
            cox_snell_r_squared=cox_snell,
            nagelkerke_r_squared=nagelkerke,
            coefficients=coefficients,
            classification=classification,
            roc_auc=roc_auc,
            brier_score=brier_score,
            calibration_bins=calibration,
            diagnostics={
                "condition_number": information_condition,
                "score_infinity_per_observation": score_residual,
                "separation_status": "overlap",
                "converged": True,
                "iterations": iterations,
                "offset_ratio": prepared.preconditioned.offset_ratio,
                "minimum_fitted_probability": float(np.min(probabilities)),
                "maximum_fitted_probability": float(np.max(probabilities)),
                "minimum_fitted_weight": minimum_weight,
                "effective_calibration_bins": effective_calibration_bins,
                "classification_threshold": prepared.threshold,
                "categorical_predictors": {
                    name: {
                        "reference": encoding.reference,
                        "levels": list(encoding.levels),
                    }
                    for name, encoding in prepared.categorical_encodings.items()
                },
            },
            warning_codes=result_warning_codes,
            warnings=result_warnings,
            apa_template_id="logistic_regression.v1",
            chart_specs=chart_specs,
        )
        return StepResult(
            new_columns={},
            new_variables={},
            analysis=result,
            notes=[
                f"Fitted binary logistic regression for {prepared.outcome} "
                f"with {len(prepared.predictors)} predictors."
            ],
        )

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
            raise ValueError(
                f"categorical predictor {variable} levels must contain at least two"
            )
        levels = [str(level) for level in levels_raw]
        if len(set(levels)) != len(levels):
            raise ValueError(f"categorical predictor {variable} levels must be unique")
        reference = str(raw_spec.get("reference"))
        if reference not in levels:
            raise ValueError(
                f"categorical predictor {variable} reference must appear in levels"
            )
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
    if not isinstance(raw, Mapping):
        raise ValueError("Logistic categorical predictor policy must be an object")
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
        raise ValueError(
            f"Logistic variables are not present: {', '.join(sorted(missing))}"
        )
    policy = params["logistic_policy"]
    if not isinstance(policy, Mapping):
        raise ValueError("Logistic policy must be an object after validation")
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
    display_labels: set[str] = set()
    for level in raw_levels:
        key = normalized_value_key(level)
        if key in level_by_key:
            raise ValueError(
                "Logistic outcome levels are ambiguous after numeric normalization"
            )
        display_label = display_label_key(
            display_value_label(dataset.variables[outcome], level)
        )
        if not display_label:
            raise ValueError("Logistic outcome display labels are blank")
        if display_label in display_labels:
            raise ValueError("Logistic outcome display labels are ambiguous")
        level_by_key[key] = level
        display_labels.add(display_label)
    if len(level_by_key) != 2:
        raise ValueError(
            "Logistic outcome must contain exactly two complete-case levels"
        )
    event_key = normalized_value_key(params["event_value"])
    if event_key not in level_by_key:
        raise ValueError("Logistic event_value is not an observed outcome level")
    event_value = level_by_key[event_key]
    non_event_value = next(
        value for key, value in level_by_key.items() if key != event_key
    )
    y = np.asarray(
        [
            1.0 if normalized_value_key(value) == event_key else 0.0
            for value in frame[outcome]
        ],
        dtype=float,
    )
    event_count = int(np.sum(y))
    non_event_count = n_obs - event_count
    if event_count < 10 or non_event_count < 10:
        raise ValueError(
            "Logistic regression requires at least 10 events and 10 non-events"
        )

    for predictor, encoding in categorical.items():
        observed_raw = [_python_scalar(value) for value in pd.unique(frame[predictor])]
        observed_labels = [categorical_level_label(value) for value in observed_raw]
        if len(set(observed_labels)) != len(observed_raw):
            raise ValueError(
                f"Logistic categorical predictor {predictor} has ambiguous display levels"
            )
        if set(observed_labels) != set(encoding.levels):
            raise ValueError(
                f"Logistic categorical predictor {predictor} observed levels do not match declared levels"
            )
        frame[predictor] = frame[predictor].map(categorical_level_label)

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
        raise ValueError(
            "Logistic regression requires more observations than parameters"
        )
    preconditioned = precondition_logistic_design(x)
    if np.linalg.matrix_rank(preconditioned.scaled) < preconditioned.scaled.shape[1]:
        raise ValueError(
            "Logistic design matrix is rank deficient after preconditioning"
        )
    separation = detect_logistic_separation(preconditioned.scaled, y)
    if separation == "complete":
        raise ValueError(
            "Logistic regression has complete separation; finite MLE is undefined"
        )
    if separation == "quasi_complete":
        raise ValueError(
            "Logistic regression has quasi-complete separation; finite MLE is undefined"
        )

    return PreparedLogisticInputs(
        outcome=outcome,
        predictors=predictors,
        event_value=event_value,
        non_event_value=non_event_value,
        event_label=display_value_label(dataset.variables[outcome], event_value),
        non_event_label=display_value_label(
            dataset.variables[outcome], non_event_value
        ),
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


def _fit_binomial_glm(y: np.ndarray, design: np.ndarray) -> Any:
    return sm.GLM(
        y,
        design,
        family=sm.families.Binomial(link=sm.families.links.Logit()),
    ).fit(maxiter=200, tol=1e-10)


def _finite_array(value: object, label: str, *, ndim: int) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise ValueError(f"Logistic {label} must be a finite {ndim}D array.")
    return array


def _finite_float(value: object, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Logistic {label} must be finite.")
    return scalar


def _score_infinity_per_observation(
    design: np.ndarray,
    y: np.ndarray,
    probabilities: np.ndarray,
) -> float:
    score = design.T @ (y - probabilities)
    return _finite_float(
        np.max(np.abs(score)) / max(1, len(y)),
        "normalized score residual",
    )


def _safe_exp(value: float, label: str) -> float:
    if not _MIN_LOG <= value <= _MAX_LOG:
        raise ValueError(
            f"Logistic {label} cannot be represented as a finite odds ratio."
        )
    result = float(np.exp(value))
    if not np.isfinite(result) or result <= 0:
        raise ValueError(f"Logistic {label} produced a non-finite odds ratio.")
    return result


def _odds_values(
    b_value: float,
    ci: tuple[float, float],
    *,
    name: str,
) -> tuple[float | None, tuple[float, float] | None]:
    representable = _MIN_LOG <= min(b_value, *ci) and max(b_value, *ci) <= _MAX_LOG
    if not representable:
        return None, None
    return (
        _safe_exp(b_value, f"odds ratio for {name}"),
        (
            _safe_exp(ci[0], f"odds-ratio CI lower for {name}"),
            _safe_exp(ci[1], f"odds-ratio CI upper for {name}"),
        ),
    )


def _coefficient_rows(
    term_names: tuple[str, ...],
    beta: np.ndarray,
    covariance: np.ndarray,
    term_metadata: Mapping[str, TermMetadata],
) -> tuple[LogisticCoefficientRow, ...]:
    if covariance.shape != (len(beta), len(beta)) or len(term_names) != len(beta):
        raise ValueError("Logistic coefficient and covariance shapes do not agree.")
    variances = np.diag(covariance)
    if np.any(~np.isfinite(variances)) or np.any(variances <= 0):
        raise ValueError("Logistic coefficient variances must be finite and positive.")
    standard_errors = np.sqrt(variances)
    critical = _finite_float(stats.norm.ppf(0.975), "normal critical value")
    rows: list[LogisticCoefficientRow] = []
    for index, name in enumerate(term_names):
        b_value = _finite_float(beta[index], f"coefficient {name}")
        se = _finite_float(standard_errors[index], f"SE for {name}")
        z_value = _finite_float(b_value / se, f"Wald z for {name}")
        p_value = _finite_float(
            2.0 * stats.norm.sf(abs(z_value)),
            f"Wald p-value for {name}",
        )
        ci = (
            _finite_float(b_value - (critical * se), f"CI lower for {name}"),
            _finite_float(b_value + (critical * se), f"CI upper for {name}"),
        )
        metadata = term_metadata.get(
            name,
            TermMetadata(
                name=name,
                term_type="intercept" if name == "(Intercept)" else "term",
            ),
        )
        odds_ratio, odds_ratio_ci = _odds_values(
            b_value,
            ci,
            name=name,
        )
        rows.append(
            LogisticCoefficientRow(
                name=name,
                b=b_value,
                se=se,
                wald_z=z_value,
                wald_chi_square=z_value * z_value,
                p_value=p_value,
                odds_ratio=odds_ratio,
                ci=ci,
                odds_ratio_ci=odds_ratio_ci,
                term_type=metadata.term_type,
                source_variable=metadata.source_variable,
                level=metadata.level,
                reference_level=metadata.reference_level,
                components=metadata.components,
            )
        )
    return tuple(rows)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _classification_table(
    y: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> BinaryClassificationTable:
    predicted = probabilities >= threshold
    event = y == 1.0
    tn = int(np.sum(~event & ~predicted))
    fp = int(np.sum(~event & predicted))
    fn = int(np.sum(event & ~predicted))
    tp = int(np.sum(event & predicted))
    return BinaryClassificationTable(
        threshold=threshold,
        tn=tn,
        fp=fp,
        fn=fn,
        tp=tp,
        sensitivity=_ratio(tp, tp + fn),
        specificity=_ratio(tn, tn + fp),
        positive_predictive_value=_ratio(tp, tp + fp),
        negative_predictive_value=_ratio(tn, tn + fn),
        accuracy=(tn + tp) / len(y),
    )


def _calibration_bins(
    y: np.ndarray,
    probabilities: np.ndarray,
    requested_bins: int,
) -> tuple[tuple[CalibrationBin, ...], int]:
    unique_probabilities = np.unique(probabilities)
    if len(unique_probabilities) <= requested_bins:
        group_index = np.searchsorted(unique_probabilities, probabilities)
        effective_bins = len(unique_probabilities)
    else:
        boundaries = np.unique(
            np.quantile(
                probabilities,
                np.linspace(0.0, 1.0, requested_bins + 1),
                method="linear",
            )
        )
        group_index = np.searchsorted(boundaries[1:-1], probabilities, side="right")
        effective_bins = int(np.unique(group_index).size)
    if effective_bins < 3:
        return (), effective_bins

    rows: list[CalibrationBin] = []
    for output_index, raw_group in enumerate(sorted(np.unique(group_index)), start=1):
        mask = group_index == raw_group
        group_probabilities = probabilities[mask]
        group_y = y[mask]
        count = int(np.sum(mask))
        events = int(np.sum(group_y))
        rows.append(
            CalibrationBin(
                index=output_index,
                probability_lower=float(np.min(group_probabilities)),
                probability_upper=float(np.max(group_probabilities)),
                count=count,
                events=events,
                mean_predicted=float(np.mean(group_probabilities)),
                observed_rate=events / count,
            )
        )
    return tuple(rows), effective_bins


def _result_warnings(
    prepared: PreparedLogisticInputs,
    *,
    classification: BinaryClassificationTable,
    coefficients: tuple[LogisticCoefficientRow, ...],
    information_condition: float,
    minimum_weight: float,
    effective_calibration_bins: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    codes: list[str] = []
    messages: list[str] = []

    def add(code: str, *, detail: str | None = None) -> None:
        codes.append(code)
        messages.append(
            render_logistic_warning(
                code,
                prepared.language,
                detail=detail,
            )
        )

    add("same_sample_metrics")
    if min(prepared.event_count, prepared.non_event_count) < 20:
        add("small_outcome_class")
    parameter_count = len(prepared.term_names) - 1
    if min(prepared.event_count, prepared.non_event_count) / parameter_count < 10:
        add("low_events_per_parameter")
    if prepared.n_total and prepared.n_dropped / prepared.n_total > 0.05:
        add("high_missing_fraction")
    undefined_metrics = [
        name
        for name in (
            "sensitivity",
            "specificity",
            "positive_predictive_value",
            "negative_predictive_value",
        )
        if getattr(classification, name) is None
    ]
    if undefined_metrics:
        labels = LOGISTIC_CLASSIFICATION_METRIC_LABELS[prepared.language]
        add(
            "undefined_classification_metrics",
            detail=", ".join(labels[name] for name in undefined_metrics),
        )
    if information_condition > LOGISTIC_INFORMATION_WARNING_CONDITION_NUMBER:
        add("high_information_condition")
    if minimum_weight < 1e-8:
        add("extreme_fitted_probabilities")
    if prepared.preconditioned.offset_ratio > 1e8:
        add("large_predictor_offset")
    if any(
        row.term_type == "intercept" and row.odds_ratio is None for row in coefficients
    ):
        add("intercept_odds_ratio_undefined")
    unrepresentable_predictors = [
        row.name
        for row in coefficients
        if row.term_type != "intercept" and row.odds_ratio is None
    ]
    if unrepresentable_predictors:
        add(
            "predictor_odds_ratio_unrepresentable",
            detail=", ".join(unrepresentable_predictors),
        )
    if effective_calibration_bins < 3:
        add("calibration_suppressed")
    elif effective_calibration_bins < 5:
        add("calibration_sparse")
    return tuple(codes), tuple(messages)


def _chart_specs(
    y: np.ndarray,
    probabilities: np.ndarray,
    coefficients: tuple[LogisticCoefficientRow, ...],
    calibration: tuple[CalibrationBin, ...],
    *,
    language: str,
) -> tuple[ChartSpec, ...]:
    korean = language != "en"
    forest_rows = [
        {
            "name": row.name,
            "odds_ratio": row.odds_ratio,
            "ci": row.odds_ratio_ci,
            "p_value": row.p_value,
        }
        for row in coefficients
        if row.term_type != "intercept"
        and row.odds_ratio is not None
        and row.odds_ratio_ci is not None
    ]
    charts: list[ChartSpec] = []
    if forest_rows:
        charts.append(
            ChartSpec(
                type="odds_ratio_forest",
                title="승산비" if korean else "Odds ratios",
                data={"rows": forest_rows},
                x_label="승산비" if korean else "Odds ratio",
                y_label="예측변수" if korean else "Predictor",
            )
        )
    false_positive_rate, true_positive_rate, _ = roc_curve(y, probabilities)
    charts.append(
        ChartSpec(
            type="roc_curve",
            title="표본 내 ROC 곡선" if korean else "In-sample ROC curve",
            data={
                "rows": [
                    {
                        "false_positive_rate": float(fpr),
                        "true_positive_rate": float(tpr),
                    }
                    for fpr, tpr in zip(
                        false_positive_rate,
                        true_positive_rate,
                        strict=True,
                    )
                ]
            },
            x_label="위양성률" if korean else "False positive rate",
            y_label="진양성률" if korean else "True positive rate",
        )
    )
    if calibration:
        charts.append(
            ChartSpec(
                type="calibration_plot",
                title=(
                    "표본 내 기술적 보정"
                    if korean
                    else "In-sample descriptive calibration"
                ),
                data={"rows": [asdict(row) for row in calibration]},
                x_label="평균 적합확률" if korean else "Mean fitted probability",
                y_label="관측 사건 비율" if korean else "Observed event rate",
            )
        )
    return tuple(charts)


Step.register_type(BinaryLogisticRegressionStep.step_type, BinaryLogisticRegressionStep)
