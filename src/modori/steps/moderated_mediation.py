from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.moderated_mediation_results import (
    ConditionalIndirectEffect,
    ModeratedMediationModelFit,
    ModeratedMediationResult,
)
from modori.steps.mediation import _as_finite_float, _fit_ols, _ols_coefficients


@dataclass
class ModeratedMediationStep(Step):
    step_type = "stats.moderated_mediation"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "model": 7,
            "x": "x",
            "mediator": "m",
            "moderator": "w",
            "y": "y",
            "covariates": [],
            "bootstrap": {"iterations": 250, "seed": 20260708, "ci": 0.95},
            "moderator_values": "mean_sd",
            "center": "mean",
            "language": "ko",
        },
        "newer": {"schema_version": 999, "model": 7, "x": "x"},
        "unknown_current": {
            "schema_version": 1,
            "model": 7,
            "x": "x",
            "mediator": "m",
            "moderator": "w",
            "y": "y",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("moderated_mediation params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("moderated_mediation params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported moderated_mediation schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "model",
            "x",
            "mediator",
            "moderator",
            "y",
            "covariates",
            "bootstrap",
            "moderator_values",
            "center",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown moderated_mediation params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "moderated_mediation params were not migrated to the current schema"
            )
        model = params.get("model")
        if model not in {7, 14}:
            raise ValueError("moderated_mediation model must be 7 or 14")
        x = cls._string_param(params, "x")
        mediator = cls._string_param(params, "mediator")
        moderator = cls._string_param(params, "moderator")
        y = cls._string_param(params, "y")
        covariates = params.get("covariates", [])
        if not isinstance(covariates, list) or not all(
            isinstance(item, str) and item for item in covariates
        ):
            raise ValueError("moderated_mediation covariates must be a list of strings")
        roles = [x, mediator, moderator, y, *covariates]
        if len(set(roles)) != len(roles):
            raise ValueError(
                "moderated_mediation x, mediator, moderator, y, and covariates must be distinct"
            )
        bootstrap = cls._bootstrap_params(params.get("bootstrap", {}))
        moderator_values = str(params.get("moderator_values", "mean_sd"))
        if moderator_values != "mean_sd":
            raise ValueError("moderated_mediation moderator_values must be mean_sd")
        center = str(params.get("center", "mean"))
        if center != "mean":
            raise ValueError("moderated_mediation center must be mean")
        language = str(params.get("language", "ko"))
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "model": int(model),
            "x": x,
            "mediator": mediator,
            "moderator": moderator,
            "y": y,
            "covariates": list(covariates),
            "bootstrap": bootstrap,
            "moderator_values": moderator_values,
            "center": center,
            "language": language,
        }

    @staticmethod
    def _string_param(params: Mapping[str, object], key: str) -> str:
        value = params.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"moderated_mediation {key} must be a non-empty string")
        return value

    @staticmethod
    def _bootstrap_params(value: object) -> dict[str, object]:
        raw = value if isinstance(value, Mapping) else {}
        iterations = raw.get("iterations", 1000)
        seed = raw.get("seed", 20260708)
        ci = raw.get("ci", 0.95)
        if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 50:
            raise ValueError(
                "moderated_mediation bootstrap iterations must be an integer >= 50"
            )
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("moderated_mediation bootstrap seed must be an integer")
        ci_float = float(ci)
        if not np.isfinite(ci_float) or not 0.5 < ci_float < 1.0:
            raise ValueError("moderated_mediation bootstrap ci must be between 0.5 and 1")
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
            str(params["moderator"]),
            str(params["y"]),
            *[str(item) for item in params["covariates"]],
        }

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return (
            f"moderated mediation model {params['model']} for "
            f"{params['x']} -> {params['mediator']} -> {params['y']}"
        )

    def _compute_result(
        self,
        dataset: Dataset,
        params: dict[str, object],
    ) -> ModeratedMediationResult:
        model = int(params["model"])
        x = str(params["x"])
        mediator = str(params["mediator"])
        moderator = str(params["moderator"])
        y = str(params["y"])
        covariates = [str(item) for item in params["covariates"]]
        bootstrap = dict(params["bootstrap"])
        variables = [x, mediator, moderator, y, *covariates]
        self._validate_dataset(dataset, variables)
        frame = dataset.frame_for_compute(variables)
        n_total = int(len(frame))
        complete = frame.dropna(axis=0, how="any").copy()
        n_used = int(len(complete))
        if n_used <= 6 + len(covariates):
            raise ValueError(
                "moderated_mediation requires more complete rows than model parameters"
            )
        n_excluded = n_total - n_used
        for variable in variables:
            complete[variable] = self._numeric_series(complete[variable], variable)
            if complete[variable].nunique(dropna=True) < 2:
                raise ValueError(
                    "moderated_mediation variables must have non-zero variance"
                )
        centered = self._centered_frame(complete, x=x, mediator=mediator, moderator=moderator)
        moderator_mean = float(complete[moderator].mean())
        moderator_sd = _as_finite_float(complete[moderator].std(ddof=1), "moderator SD")
        if moderator_sd <= 0:
            raise ValueError("moderated_mediation moderator SD must be positive")

        if model == 7:
            mediator_predictors = [
                "x_centered",
                "w_centered",
                "x_centered:w_centered",
                *covariates,
            ]
            outcome_predictors = ["x_centered", mediator, *covariates]
            mediator_fit = _fit_ols(centered, outcome=mediator, predictors=mediator_predictors)
            outcome_fit = _fit_ols(centered, outcome=y, predictors=outcome_predictors)
            a1 = mediator_fit.coefficients["x_centered"].b
            a3 = mediator_fit.coefficients["x_centered:w_centered"].b
            b = outcome_fit.coefficients[mediator].b
            point_effects = {
                label: (a1 + a3 * centered_value) * b
                for label, centered_value in self._moderator_points(moderator_sd)
            }
            index = a3 * b
        else:
            mediator_predictors = ["x_centered", *covariates]
            outcome_predictors = [
                "x_centered",
                mediator,
                "w_centered",
                "m:w_centered",
                *covariates,
            ]
            mediator_fit = _fit_ols(centered, outcome=mediator, predictors=mediator_predictors)
            outcome_fit = _fit_ols(centered, outcome=y, predictors=outcome_predictors)
            a = mediator_fit.coefficients["x_centered"].b
            b1 = outcome_fit.coefficients[mediator].b
            b3 = outcome_fit.coefficients["m:w_centered"].b
            point_effects = {
                label: a * (b1 + b3 * centered_value)
                for label, centered_value in self._moderator_points(moderator_sd)
            }
            index = a * b3

        effect_cis, index_ci = _bootstrap_cis(
            centered,
            model=model,
            mediator=mediator,
            y=y,
            covariates=covariates,
            moderator_sd=moderator_sd,
            iterations=int(bootstrap["iterations"]),
            seed=int(bootstrap["seed"]),
            ci=float(bootstrap["ci"]),
        )
        conditional_effects = tuple(
            ConditionalIndirectEffect(
                moderator_label=label,
                moderator_value=moderator_mean + centered_value,
                effect=_as_finite_float(point_effects[label], f"conditional effect {label}"),
                ci=effect_cis[label],
            )
            for label, centered_value in self._moderator_points(moderator_sd)
        )
        return ModeratedMediationResult(
            analysis_key="moderated_mediation",
            title_ko="조절된 매개분석",
            model=model,
            x=x,
            mediator=mediator,
            moderator=moderator,
            y=y,
            covariates=tuple(covariates),
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            moderator_mean=moderator_mean,
            moderator_sd=moderator_sd,
            conditional_effects=conditional_effects,
            index_of_moderated_mediation=_as_finite_float(
                index,
                "index of moderated mediation",
            ),
            index_ci=index_ci,
            bootstrap_iterations=int(bootstrap["iterations"]),
            bootstrap_seed=int(bootstrap["seed"]),
            bootstrap_ci_level=float(bootstrap["ci"]),
            mediator_model=ModeratedMediationModelFit(
                outcome=mediator,
                predictors=tuple(mediator_predictors),
                r_squared=mediator_fit.r_squared,
            ),
            outcome_model=ModeratedMediationModelFit(
                outcome=y,
                predictors=tuple(outcome_predictors),
                r_squared=outcome_fit.r_squared,
            ),
            warnings_ko=("횡단면 자료에서는 인과적 조건부 간접효과로 단정하지 않는다.",),
            notes_ko=("부트스트랩 CI는 percentile 방법을 사용했다.",),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "조절된 매개분석 ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, variables: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 조절된 매개분석을 실행할 수 없습니다.")
        missing = [variable for variable in variables if variable not in dataset.variables]
        if missing:
            raise ValueError(f"데이터셋에 없는 변수: {', '.join(missing)}")
        for variable in variables:
            if dataset.variables[variable].measure is not Measure.SCALE:
                raise ValueError("moderated_mediation variables must be scale variables")

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"moderated_mediation variable must be numeric: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"moderated_mediation variable must be finite: {key}")
        return values

    @staticmethod
    def _centered_frame(
        frame: pd.DataFrame,
        *,
        x: str,
        mediator: str,
        moderator: str,
    ) -> pd.DataFrame:
        centered = frame.copy()
        centered["x_centered"] = centered[x] - float(centered[x].mean())
        centered["w_centered"] = centered[moderator] - float(centered[moderator].mean())
        centered["x_centered:w_centered"] = (
            centered["x_centered"] * centered["w_centered"]
        )
        centered["m:w_centered"] = centered[mediator] * centered["w_centered"]
        return centered

    @staticmethod
    def _moderator_points(moderator_sd: float) -> tuple[tuple[str, float], ...]:
        return (
            ("mean - 1 SD", -moderator_sd),
            ("mean", 0.0),
            ("mean + 1 SD", moderator_sd),
        )


def _bootstrap_cis(
    frame: pd.DataFrame,
    *,
    model: int,
    mediator: str,
    y: str,
    covariates: list[str],
    moderator_sd: float,
    iterations: int,
    seed: int,
    ci: float,
) -> tuple[dict[str, tuple[float, float]], tuple[float, float]]:
    rng = np.random.default_rng(seed)
    effects_by_label = {
        label: []
        for label, _centered_value in ModeratedMediationStep._moderator_points(moderator_sd)
    }
    index_values: list[float] = []
    n_rows = len(frame)
    for _ in range(iterations):
        sample = frame.iloc[rng.integers(0, n_rows, size=n_rows)].reset_index(drop=True)
        if model == 7:
            mediator_coefs = _ols_coefficients(
                sample,
                outcome=mediator,
                predictors=[
                    "x_centered",
                    "w_centered",
                    "x_centered:w_centered",
                    *covariates,
                ],
            )
            outcome_coefs = _ols_coefficients(
                sample,
                outcome=y,
                predictors=["x_centered", mediator, *covariates],
            )
            a1 = float(mediator_coefs[1])
            a3 = float(mediator_coefs[3])
            b = float(outcome_coefs[2])
            for label, centered_value in ModeratedMediationStep._moderator_points(moderator_sd):
                effects_by_label[label].append((a1 + a3 * centered_value) * b)
            index_values.append(a3 * b)
        else:
            mediator_coefs = _ols_coefficients(
                sample,
                outcome=mediator,
                predictors=["x_centered", *covariates],
            )
            outcome_coefs = _ols_coefficients(
                sample,
                outcome=y,
                predictors=[
                    "x_centered",
                    mediator,
                    "w_centered",
                    "m:w_centered",
                    *covariates,
                ],
            )
            a = float(mediator_coefs[1])
            b1 = float(outcome_coefs[2])
            b3 = float(outcome_coefs[4])
            for label, centered_value in ModeratedMediationStep._moderator_points(moderator_sd):
                effects_by_label[label].append(a * (b1 + b3 * centered_value))
            index_values.append(a * b3)
    alpha = 1.0 - ci
    percentiles = [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)]
    effect_cis = {
        label: _percentile_ci(values, percentiles)
        for label, values in effects_by_label.items()
    }
    return effect_cis, _percentile_ci(index_values, percentiles)


def _percentile_ci(values: list[float], percentiles: list[float]) -> tuple[float, float]:
    low, high = np.percentile(values, percentiles)
    return (
        _as_finite_float(low, "bootstrap CI low"),
        _as_finite_float(high, "bootstrap CI high"),
    )


Step.register_type(ModeratedMediationStep.step_type, ModeratedMediationStep)
