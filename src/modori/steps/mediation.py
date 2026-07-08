from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.mediation_results import (
    MediationEffect,
    MediationModelFit,
    MediationResult,
)
from modori.statistics_numerics import (
    DEFAULT_BOOTSTRAP_ITERATIONS,
    MIN_BOOTSTRAP_ITERATIONS,
    bootstrap_iteration_warning_ko,
    require_well_conditioned_ols_design,
)


@dataclass(frozen=True)
class _OlsFit:
    outcome: str
    predictors: tuple[str, ...]
    coefficients: dict[str, MediationEffect]
    r_squared: float


@dataclass
class MediationStep(Step):
    step_type = "stats.mediation"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "x": "x",
            "mediator": "m",
            "y": "y",
            "covariates": [],
            "bootstrap": {
                "iterations": DEFAULT_BOOTSTRAP_ITERATIONS,
                "seed": 20260708,
                "ci": 0.95,
            },
            "standardize": False,
            "language": "ko",
        },
        "newer": {"schema_version": 999, "x": "x", "mediator": "m", "y": "y"},
        "unknown_current": {
            "schema_version": 1,
            "x": "x",
            "mediator": "m",
            "y": "y",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("mediation params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("mediation params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported mediation schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "x",
            "mediator",
            "y",
            "covariates",
            "bootstrap",
            "standardize",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown mediation params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("mediation params were not migrated to the current schema")

        x = cls._string_param(params, "x")
        mediator = cls._string_param(params, "mediator")
        y = cls._string_param(params, "y")
        covariates = params.get("covariates", [])
        if not isinstance(covariates, list) or not all(
            isinstance(item, str) and item for item in covariates
        ):
            raise ValueError("mediation covariates must be a list of strings")
        roles = [x, mediator, y, *covariates]
        if len(set(roles)) != len(roles):
            raise ValueError("mediation x, mediator, y, and covariates must be distinct")
        bootstrap = cls._bootstrap_params(params.get("bootstrap", {}))
        if bool(params.get("standardize", False)):
            raise ValueError("mediation standardize=True is not supported in schema v1")
        language = str(params.get("language", "ko"))
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "x": x,
            "mediator": mediator,
            "y": y,
            "covariates": list(covariates),
            "bootstrap": bootstrap,
            "standardize": False,
            "language": language,
        }

    @staticmethod
    def _string_param(params: Mapping[str, object], key: str) -> str:
        value = params.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"mediation {key} must be a non-empty string")
        return value

    @staticmethod
    def _bootstrap_params(value: object) -> dict[str, object]:
        raw = value if isinstance(value, Mapping) else {}
        iterations = raw.get("iterations", DEFAULT_BOOTSTRAP_ITERATIONS)
        seed = raw.get("seed", 20260708)
        ci = raw.get("ci", 0.95)
        if (
            not isinstance(iterations, int)
            or isinstance(iterations, bool)
            or iterations < MIN_BOOTSTRAP_ITERATIONS
        ):
            raise ValueError(
                f"mediation bootstrap iterations must be an integer >= {MIN_BOOTSTRAP_ITERATIONS}"
            )
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("mediation bootstrap seed must be an integer")
        ci_float = float(ci)
        if not np.isfinite(ci_float) or not 0.5 < ci_float < 1.0:
            raise ValueError("mediation bootstrap ci must be between 0.5 and 1")
        return {"iterations": iterations, "seed": seed, "ci": ci_float}

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx.dataset, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {
            str(params["x"]),
            str(params["mediator"]),
            str(params["y"]),
            *[str(item) for item in params["covariates"]],
        }

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return f"mediation model {params['x']} -> {params['mediator']} -> {params['y']}"

    def _compute_result(
        self,
        dataset: Dataset,
        params: dict[str, object],
    ) -> MediationResult:
        x = str(params["x"])
        mediator = str(params["mediator"])
        y = str(params["y"])
        covariates = [str(item) for item in params["covariates"]]
        bootstrap = dict(params["bootstrap"])
        variables = [x, mediator, y, *covariates]
        self._validate_dataset(dataset, variables)
        frame = dataset.frame_for_compute(variables)
        n_total = int(len(frame))
        complete = frame.dropna(axis=0, how="any").copy()
        n_used = int(len(complete))
        if n_used <= 4 + len(covariates):
            raise ValueError("mediation requires more complete rows than model parameters")
        n_excluded = n_total - n_used
        for variable in variables:
            complete[variable] = self._numeric_series(complete[variable], variable)
            if complete[variable].nunique(dropna=True) < 2:
                raise ValueError("mediation variables must have non-zero variance")

        mediator_fit = _fit_ols(complete, outcome=mediator, predictors=[x, *covariates])
        outcome_fit = _fit_ols(
            complete,
            outcome=y,
            predictors=[x, mediator, *covariates],
        )
        total_fit = _fit_ols(complete, outcome=y, predictors=[x, *covariates])
        path_a = mediator_fit.coefficients[x]
        path_b = outcome_fit.coefficients[mediator]
        direct_effect = outcome_fit.coefficients[x]
        total_effect = total_fit.coefficients[x]
        indirect_effect = _as_finite_float(path_a.b * path_b.b, "indirect effect")
        indirect_ci = _bootstrap_indirect_ci(
            complete,
            x=x,
            mediator=mediator,
            y=y,
            covariates=covariates,
            iterations=int(bootstrap["iterations"]),
            seed=int(bootstrap["seed"]),
            ci=float(bootstrap["ci"]),
        )
        warnings_ko = ["횡단면 자료에서는 인과 매개로 단정하지 않는다."]
        iteration_warning = bootstrap_iteration_warning_ko(int(bootstrap["iterations"]))
        if iteration_warning:
            warnings_ko.append(iteration_warning)

        return MediationResult(
            analysis_key="mediation",
            title_ko="매개분석",
            x=x,
            mediator=mediator,
            y=y,
            covariates=tuple(covariates),
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            path_a=path_a,
            path_b=path_b,
            direct_effect=direct_effect,
            total_effect=total_effect,
            indirect_effect=indirect_effect,
            indirect_ci=indirect_ci,
            bootstrap_iterations=int(bootstrap["iterations"]),
            bootstrap_seed=int(bootstrap["seed"]),
            bootstrap_ci_level=float(bootstrap["ci"]),
            mediator_model=MediationModelFit(
                outcome=mediator,
                predictors=tuple([x, *covariates]),
                r_squared=mediator_fit.r_squared,
            ),
            outcome_model=MediationModelFit(
                outcome=y,
                predictors=tuple([x, mediator, *covariates]),
                r_squared=outcome_fit.r_squared,
            ),
            total_model=MediationModelFit(
                outcome=y,
                predictors=tuple([x, *covariates]),
                r_squared=total_fit.r_squared,
            ),
            warnings_ko=tuple(warnings_ko),
            notes_ko=("부트스트랩 CI는 percentile 방법을 사용했다.",),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "매개분석 ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, variables: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 매개분석을 실행할 수 없습니다.")
        missing = [variable for variable in variables if variable not in dataset.variables]
        if missing:
            raise ValueError(f"데이터셋에 없는 변수: {', '.join(missing)}")
        for variable in variables:
            if dataset.variables[variable].measure is not Measure.SCALE:
                raise ValueError("mediation variables must be scale variables")

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"mediation variable must be numeric: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"mediation variable must be finite: {key}")
        return values


def _fit_ols(frame: pd.DataFrame, *, outcome: str, predictors: list[str]) -> _OlsFit:
    names = ["(Intercept)", *predictors]
    x_matrix = np.column_stack(
        [np.ones(len(frame)), *[frame[predictor].to_numpy(dtype=float) for predictor in predictors]]
    )
    y_vector = frame[outcome].to_numpy(dtype=float)
    if len(frame) <= x_matrix.shape[1]:
        raise ValueError("mediation requires more complete rows than model parameters")
    if np.linalg.matrix_rank(x_matrix) < x_matrix.shape[1]:
        raise ValueError("mediation design matrix must be full rank")
    require_well_conditioned_ols_design(x_matrix, label="mediation OLS")
    coefficients, *_ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    fitted = x_matrix @ coefficients
    residuals = y_vector - fitted
    df_resid = len(frame) - x_matrix.shape[1]
    ss_resid = float(residuals @ residuals)
    if ss_resid <= 0 or np.isclose(ss_resid, 0.0, atol=1e-12):
        raise ValueError("mediation residual variance must be positive")
    centered = y_vector - float(y_vector.mean())
    ss_total = float(centered @ centered)
    if ss_total <= 0:
        raise ValueError("mediation outcome variance must be positive")
    sigma2 = ss_resid / df_resid
    covariance = sigma2 * np.linalg.inv(x_matrix.T @ x_matrix)
    se = np.sqrt(np.diag(covariance))
    t_values = coefficients / se
    p_values = 2 * stats.t.sf(np.abs(t_values), df_resid)
    critical = stats.t.ppf(0.975, df_resid)
    effects = {}
    for index, name in enumerate(names):
        effects[name] = MediationEffect(
            name=name,
            predictor=name,
            outcome=outcome,
            b=_as_finite_float(coefficients[index], f"coefficient {name}"),
            se=_as_finite_float(se[index], f"SE {name}"),
            t=_as_finite_float(t_values[index], f"t {name}"),
            p_value=_as_finite_float(p_values[index], f"p {name}"),
            ci=(
                _as_finite_float(coefficients[index] - critical * se[index], f"CI low {name}"),
                _as_finite_float(coefficients[index] + critical * se[index], f"CI high {name}"),
            ),
        )
    return _OlsFit(
        outcome=outcome,
        predictors=tuple(predictors),
        coefficients=effects,
        r_squared=_as_finite_float(1.0 - (ss_resid / ss_total), "R-squared"),
    )


def _bootstrap_indirect_ci(
    frame: pd.DataFrame,
    *,
    x: str,
    mediator: str,
    y: str,
    covariates: list[str],
    iterations: int,
    seed: int,
    ci: float,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    effects: list[float] = []
    n_rows = len(frame)
    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, n_rows, size=n_rows)].reset_index(drop=True)
        a = _ols_coefficients(sample, outcome=mediator, predictors=[x, *covariates])[1]
        b = _ols_coefficients(sample, outcome=y, predictors=[x, mediator, *covariates])[2]
        effects.append(float(a * b))
    alpha = 1.0 - ci
    low, high = np.percentile(effects, [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)])
    return (
        _as_finite_float(low, "bootstrap indirect CI low"),
        _as_finite_float(high, "bootstrap indirect CI high"),
    )


def _ols_coefficients(
    frame: pd.DataFrame,
    *,
    outcome: str,
    predictors: list[str],
) -> np.ndarray:
    x_matrix = np.column_stack(
        [np.ones(len(frame)), *[frame[predictor].to_numpy(dtype=float) for predictor in predictors]]
    )
    y_vector = frame[outcome].to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(x_matrix, y_vector, rcond=None)
    return coefficients


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Mediation produced non-finite {label}.")
    return scalar


Step.register_type(MediationStep.step_type, MediationStep)
