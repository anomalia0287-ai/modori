from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from modori.cache import matplotlib_cache_dir
from modori.core import Dataset, Measure, PipelineContext, Step, StepResult
from modori.repeated_measures_anova_results import (
    RepeatedMeasureLevelSummary,
    RepeatedMeasuresAnovaResult,
    RepeatedMeasuresSphericity,
)


_SUPPORTED_MEASURES = {Measure.SCALE, Measure.ORDINAL}
_SUPPORTED_CORRECTIONS = {"auto", "none", "greenhouse_geisser", "huynh_feldt"}


@dataclass
class RepeatedMeasuresAnovaStep(Step):
    step_type = "stats.repeated_measures_anova"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "measures": ["pre", "mid", "post"],
            "within_factor": "time",
            "level_labels": ["pre", "mid", "post"],
            "correction": "auto",
            "sphericity_alpha": 0.05,
            "language": "ko",
        },
        "newer": {"schema_version": 999, "measures": ["pre", "mid", "post"]},
        "unknown_current": {
            "schema_version": 1,
            "measures": ["pre", "mid", "post"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("repeated_measures_anova params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("repeated_measures_anova params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported repeated_measures_anova schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "measures",
            "within_factor",
            "level_labels",
            "correction",
            "sphericity_alpha",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown repeated_measures_anova params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "repeated_measures_anova params were not migrated to the current schema"
            )

        measures = params.get("measures")
        if (
            not isinstance(measures, list)
            or not all(isinstance(item, str) and item for item in measures)
        ):
            raise ValueError("repeated_measures_anova measures must be a list of strings")
        if len(measures) < 3:
            raise ValueError("repeated_measures_anova requires three or more measures")
        if len(set(measures)) != len(measures):
            raise ValueError("repeated_measures_anova measures contain duplicate variables")

        within_factor = params.get("within_factor", "condition")
        if not isinstance(within_factor, str) or not within_factor.strip():
            raise ValueError("within_factor must be a non-empty string")

        raw_level_labels = params.get("level_labels")
        if raw_level_labels is None:
            level_labels = list(measures)
        else:
            if (
                not isinstance(raw_level_labels, list)
                or len(raw_level_labels) != len(measures)
                or not all(isinstance(item, str) and item for item in raw_level_labels)
            ):
                raise ValueError("level_labels must match measures length")
            level_labels = list(raw_level_labels)

        correction = str(params.get("correction", "auto"))
        if correction not in _SUPPORTED_CORRECTIONS:
            raise ValueError(
                "correction must be auto, none, greenhouse_geisser, or huynh_feldt"
            )
        sphericity_alpha = float(params.get("sphericity_alpha", 0.05))
        if not np.isfinite(sphericity_alpha) or not 0.0 < sphericity_alpha < 1.0:
            raise ValueError("sphericity_alpha must be a finite float between 0 and 1")
        language = str(params.get("language", "ko"))
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "measures": list(measures),
            "within_factor": within_factor.strip(),
            "level_labels": level_labels,
            "correction": correction,
            "sphericity_alpha": sphericity_alpha,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx.dataset, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(measure) for measure in params["measures"]}

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return f"repeated-measures ANOVA for {', '.join(params['measures'])}"

    def _compute_result(
        self,
        dataset: Dataset,
        params: dict[str, object],
    ) -> RepeatedMeasuresAnovaResult:
        measures = [str(item) for item in params["measures"]]
        level_labels = [str(item) for item in params["level_labels"]]
        self._validate_dataset(dataset, measures)
        source = dataset.frame_for_compute(measures)
        n_total = int(len(source))
        complete = source.dropna(axis=0, how="any").copy()
        n_used = int(len(complete))
        if n_used < 3:
            raise ValueError(
                "repeated_measures_anova requires at least three complete subjects"
            )
        n_excluded = n_total - n_used
        for measure in measures:
            complete[measure] = self._numeric_series(complete[measure], measure)
            if complete[measure].nunique(dropna=True) < 2:
                raise ValueError(
                    "repeated_measures_anova requires non-zero variance for every measure"
                )

        anova = self._anova_components(complete)
        sphericity = self._sphericity(complete)
        correction_method = self._select_correction(
            str(params["correction"]),
            sphericity,
            float(params["sphericity_alpha"]),
        )
        corrected_df_effect, corrected_df_error, corrected_p_value = (
            self._corrected_test(anova, sphericity, correction_method)
        )
        warnings = self._warnings(correction_method)
        return RepeatedMeasuresAnovaResult(
            analysis_key="repeated_measures_anova",
            title_ko="반복측정 분산분석",
            measures=tuple(measures),
            within_factor=str(params["within_factor"]),
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            levels=tuple(
                self._level_summary(
                    complete,
                    variable=measure,
                    level_index=index + 1,
                    level_label=level_labels[index],
                )
                for index, measure in enumerate(measures)
            ),
            sphericity=sphericity,
            ss_effect=anova["ss_effect"],
            ss_error=anova["ss_error"],
            df_effect=anova["df_effect"],
            df_error=anova["df_error"],
            f_statistic=anova["f_statistic"],
            p_value=anova["p_value"],
            partial_eta_squared=anova["partial_eta_squared"],
            correction_method=correction_method,
            corrected_df_effect=corrected_df_effect,
            corrected_df_error=corrected_df_error,
            corrected_p_value=corrected_p_value,
            warnings_ko=warnings,
            notes_ko=(
                "중앙 차트 렌더링 훅이 없어 반복측정 분산분석 차트는 아직 생성하지 않는다.",
            ),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "반복측정 분산분석 ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 "
                "차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, measures: list[str]) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 반복측정 분산분석을 실행할 수 없습니다.")
        missing = [measure for measure in measures if measure not in dataset.variables]
        if missing:
            raise ValueError(f"데이터셋에 없는 변수: {', '.join(missing)}")
        for measure in measures:
            if dataset.variables[measure].measure not in _SUPPORTED_MEASURES:
                raise ValueError(
                    "repeated_measures_anova measures must be scale or ordinal variables"
                )

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"repeated_measures_anova measure must be numeric: {key}"
            ) from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"repeated_measures_anova measure must be finite: {key}")
        return values

    @staticmethod
    def _anova_components(frame: pd.DataFrame) -> dict[str, float]:
        values = frame.to_numpy(dtype=float)
        n_subjects, level_count = values.shape
        centered_values = values - float(values.mean())
        level_means = centered_values.mean(axis=0)
        subject_means = centered_values.mean(axis=1)
        ss_total = float((centered_values**2).sum())
        ss_subjects = float(level_count * (subject_means**2).sum())
        ss_within = ss_total - ss_subjects
        ss_effect = float(n_subjects * (level_means**2).sum())
        ss_error = ss_within - ss_effect
        if ss_error <= 0 or np.isclose(ss_error, 0.0, atol=1e-12):
            raise ValueError(
                "repeated_measures_anova residual error variance must be positive"
            )
        df_effect = float(level_count - 1)
        df_error = float((n_subjects - 1) * (level_count - 1))
        if df_error <= 0:
            raise ValueError("repeated_measures_anova error df must be positive")
        f_statistic = (ss_effect / df_effect) / (ss_error / df_error)
        p_value = float(stats.f.sf(f_statistic, df_effect, df_error))
        partial_eta_squared = ss_effect / (ss_effect + ss_error)
        return {
            "ss_effect": _as_finite_float(ss_effect, "SS effect"),
            "ss_error": _as_finite_float(ss_error, "SS error"),
            "df_effect": _as_finite_float(df_effect, "effect df"),
            "df_error": _as_finite_float(df_error, "error df"),
            "f_statistic": _as_finite_float(f_statistic, "F statistic"),
            "p_value": _as_finite_float(p_value, "p-value"),
            "partial_eta_squared": _as_finite_float(
                partial_eta_squared,
                "partial eta squared",
            ),
        }

    @staticmethod
    def _sphericity(frame: pd.DataFrame) -> RepeatedMeasuresSphericity:
        pg = _import_pingouin()
        try:
            sphericity = pg.sphericity(frame)
            epsilon_gg = float(pg.epsilon(frame, correction="gg"))
            epsilon_hf = float(pg.epsilon(frame, correction="hf"))
        except Exception as exc:
            raise ValueError(
                "repeated_measures_anova could not compute sphericity diagnostics"
            ) from exc
        return RepeatedMeasuresSphericity(
            method="mauchly",
            sphericity_assumed=bool(sphericity.spher),
            w_statistic=_as_finite_float(sphericity.W, "Mauchly W"),
            chi_square=_as_finite_float(sphericity.chi2, "Mauchly chi-square"),
            dof=int(sphericity.dof),
            p_value=_as_finite_float(sphericity.pval, "Mauchly p-value"),
            epsilon_gg=_as_finite_float(epsilon_gg, "Greenhouse-Geisser epsilon"),
            epsilon_hf=_as_finite_float(epsilon_hf, "Huynh-Feldt epsilon"),
        )

    @staticmethod
    def _select_correction(
        requested: str,
        sphericity: RepeatedMeasuresSphericity,
        alpha: float,
    ) -> str:
        if requested == "auto":
            return "greenhouse_geisser" if sphericity.p_value < alpha else "none"
        return requested

    @staticmethod
    def _corrected_test(
        anova: dict[str, float],
        sphericity: RepeatedMeasuresSphericity,
        correction_method: str,
    ) -> tuple[float | None, float | None, float | None]:
        if correction_method == "none":
            return None, None, None
        epsilon = (
            sphericity.epsilon_hf
            if correction_method == "huynh_feldt"
            else sphericity.epsilon_gg
        )
        corrected_df_effect = anova["df_effect"] * epsilon
        corrected_df_error = anova["df_error"] * epsilon
        corrected_p_value = float(
            stats.f.sf(
                anova["f_statistic"],
                corrected_df_effect,
                corrected_df_error,
            )
        )
        return (
            _as_finite_float(corrected_df_effect, "corrected effect df"),
            _as_finite_float(corrected_df_error, "corrected error df"),
            _as_finite_float(corrected_p_value, "corrected p-value"),
        )

    @staticmethod
    def _warnings(correction_method: str) -> tuple[str, ...]:
        if correction_method == "greenhouse_geisser":
            return (
                "구형성 가정이 충족되지 않아 Greenhouse-Geisser 보정을 적용했다.",
            )
        if correction_method == "huynh_feldt":
            return ("구형성 보정 정책에 따라 Huynh-Feldt 보정을 적용했다.",)
        return ()

    @staticmethod
    def _level_summary(
        frame: pd.DataFrame,
        *,
        variable: str,
        level_index: int,
        level_label: str,
    ) -> RepeatedMeasureLevelSummary:
        values = frame[variable]
        return RepeatedMeasureLevelSummary(
            variable=variable,
            level_index=level_index,
            level_label=level_label,
            n=int(len(values)),
            mean=float(values.mean()),
            sd=float(values.std(ddof=1)),
            median=float(values.median()),
        )


def _import_pingouin() -> Any:
    os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_dir())
    return importlib.import_module("pingouin")


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"Repeated-measures ANOVA produced non-finite {label}.")
    return scalar


Step.register_type(RepeatedMeasuresAnovaStep.step_type, RepeatedMeasuresAnovaStep)
