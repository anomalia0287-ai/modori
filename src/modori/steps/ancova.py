from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from modori.ancova_results import (
    AncovaEffectResult,
    AncovaGroupSummary,
    AncovaResult,
)
from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable
from modori.statistics_numerics import require_well_conditioned_ols_design


_SUPPORTED_GROUP_MEASURES = {Measure.NOMINAL, Measure.ORDINAL}


@dataclass
class AncovaStep(Step):
    step_type = "stats.ancova"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "dv": "outcome",
            "group": "group",
            "covariates": ["pretest"],
            "homogeneity_alpha": 0.05,
        },
        "newer": {"schema_version": 999, "dv": "outcome"},
        "unknown_current": {
            "schema_version": 1,
            "dv": "outcome",
            "group": "group",
            "covariates": ["pretest"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("ancova params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("ancova params use a newer schema_version")
        if version == 1:
            return params
        raise ValueError(f"unsupported ancova schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {"schema_version", "dv", "group", "covariates", "homogeneity_alpha"}
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown ancova params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("ancova params were not migrated to the current schema")

        dv = params.get("dv")
        group = params.get("group")
        covariates = params.get("covariates")
        if not isinstance(dv, str) or not dv:
            raise ValueError("dv must be a variable key")
        if not isinstance(group, str) or not group:
            raise ValueError("group must be a variable key")
        if (
            not isinstance(covariates, list)
            or not covariates
            or not all(isinstance(covariate, str) for covariate in covariates)
        ):
            raise ValueError("covariates must contain one or more variable keys")

        requested = [dv, group, *covariates]
        if len(set(requested)) != len(requested):
            raise ValueError("ANCOVA 변수는 중복될 수 없습니다.")

        homogeneity_alpha = params.get("homogeneity_alpha", 0.05)
        if (
            not isinstance(homogeneity_alpha, int | float)
            or isinstance(homogeneity_alpha, bool)
            or not 0.0 < float(homogeneity_alpha) < 1.0
        ):
            raise ValueError("homogeneity_alpha must be between 0 and 1")

        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "dv": dv,
            "group": group,
            "covariates": list(covariates),
            "homogeneity_alpha": float(homogeneity_alpha),
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(params["dv"]), str(params["group"]), *params["covariates"]}

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        covariates = ", ".join(str(key) for key in params["covariates"])
        return f"ancova for {params['dv']} by {params['group']} adjusted for {covariates}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> AncovaResult:
        dataset = ctx.dataset
        dv = str(params["dv"])
        group = str(params["group"])
        covariates = [str(covariate) for covariate in params["covariates"]]
        alpha = float(params["homogeneity_alpha"])
        self._validate_dataset(dataset, dv, group, covariates)

        frame = self._complete_numeric_frame(dataset, dv, group, covariates)
        n_total = int(len(dataset.df))
        n_used = int(len(frame))
        n_excluded = int(n_total - n_used)
        if n_used < 2:
            raise ValueError("ANCOVA에는 최소 2개 이상의 완전한 관측치가 필요합니다.")

        group_values = self._ordered_values(frame[group], dataset.variables[group])
        if len(group_values) < 2:
            raise ValueError("ANCOVA 집단 변수에는 최소 2개 이상의 관측 집단이 필요합니다.")

        y = frame[dv].astype(float)
        covariate_design = self._design_matrix(
            frame,
            group=group,
            covariates=covariates,
            group_values=group_values,
            include_group=False,
            include_interactions=False,
        )
        additive_design = self._design_matrix(
            frame,
            group=group,
            covariates=covariates,
            group_values=group_values,
            include_group=True,
            include_interactions=False,
        )
        interaction_design = self._design_matrix(
            frame,
            group=group,
            covariates=covariates,
            group_values=group_values,
            include_group=True,
            include_interactions=True,
        )

        covariate_model = self._fit_model(y, covariate_design)
        additive_model = self._fit_model(y, additive_design)
        interaction_model = self._fit_model(y, interaction_design)
        homogeneity_check = self._nested_effect(
            additive_model,
            interaction_model,
            term="group:covariates",
            label_ko="회귀기울기 동질성",
        )

        is_interpretable = homogeneity_check.p_value >= alpha
        warnings: tuple[str, ...] = ()
        group_effect: AncovaEffectResult | None = None
        adjusted_means: dict[object, float] = {}
        covariate_effects: tuple[AncovaEffectResult, ...] = ()
        if is_interpretable:
            group_effect = self._nested_effect(
                covariate_model,
                additive_model,
                term="group",
                label_ko="집단 효과",
            )
            adjusted_means = self._adjusted_means(
                additive_model,
                frame,
                group=group,
                covariates=covariates,
                group_values=group_values,
            )
            covariate_effects = tuple(
                self._covariate_effect(
                    y,
                    frame,
                    group=group,
                    covariates=covariates,
                    group_values=group_values,
                    covariate=covariate,
                    full_model=additive_model,
                )
                for covariate in covariates
            )
        else:
            warnings = (
                "회귀기울기 동질성 검정이 기준을 넘겨 표준 ANCOVA 집단 효과를 해석하지 않습니다.",
                "표준 ANCOVA 집단 효과와 조정평균은 검증되지 않은 값으로 보고하지 않습니다.",
            )

        groups = self._group_summaries(
            dataset,
            frame,
            dv=dv,
            group=group,
            group_values=group_values,
            adjusted_means=adjusted_means,
        )
        return AncovaResult(
            analysis_key="ancova",
            title_ko="공분산분석",
            dv=dv,
            dv_label=dataset.variables[dv].label or dv,
            group=group,
            group_label=dataset.variables[group].label or group,
            covariates=tuple(covariates),
            covariate_labels=tuple(
                dataset.variables[covariate].label or covariate
                for covariate in covariates
            ),
            homogeneity_alpha=alpha,
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            groups=groups,
            homogeneity_check=homogeneity_check,
            group_effect=group_effect,
            covariate_effects=covariate_effects,
            is_interpretable=is_interpretable,
            warnings_ko=warnings,
            notes_ko=(
                "집단 간 차이는 공변량을 보정한 모형 기반 요약이며 인과적 표현을 사용하지 않는다.",
                "중앙 차트 렌더링 훅이 없어 ANCOVA 차트는 아직 생성하지 않는다.",
            ),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "ANCOVA ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(
        dataset: Dataset,
        dv: str,
        group: str,
        covariates: list[str],
    ) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 ANCOVA를 실행할 수 없습니다.")
        requested = [dv, group, *covariates]
        missing = [key for key in requested if key not in dataset.variables]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"데이터셋에 없는 변수: {names}")
        if dataset.variables[dv].measure is not Measure.SCALE:
            raise ValueError("ANCOVA 종속변수는 척도형이어야 합니다.")
        bad_covariates = [
            covariate
            for covariate in covariates
            if dataset.variables[covariate].measure is not Measure.SCALE
        ]
        if bad_covariates:
            names = ", ".join(bad_covariates)
            raise ValueError(f"ANCOVA 공변량은 척도형이어야 합니다: {names}")
        if dataset.variables[group].measure not in _SUPPORTED_GROUP_MEASURES:
            raise ValueError("ANCOVA 집단 변수는 명목 또는 서열 척도여야 합니다.")

    @staticmethod
    def _complete_numeric_frame(
        dataset: Dataset,
        dv: str,
        group: str,
        covariates: list[str],
    ) -> pd.DataFrame:
        columns = [dv, group, *covariates]
        frame = dataset.frame_for_compute(columns)
        for key in [dv, *covariates]:
            try:
                converted = pd.to_numeric(frame[key], errors="raise").astype(float)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"ANCOVA 변수는 숫자여야 합니다: {key}") from exc
            observed = converted.dropna().to_numpy(dtype=float)
            if len(observed) and not np.all(np.isfinite(observed)):
                raise ValueError(f"ANCOVA 변수는 유한한 숫자여야 합니다: {key}")
            frame[key] = converted
        return frame.dropna(axis=0, how="any")

    @staticmethod
    def _fit_model(y: pd.Series, design: pd.DataFrame):
        if len(design) <= len(design.columns):
            raise ValueError("ANCOVA에는 모형 자유도를 확보할 완전한 관측치가 더 필요합니다.")
        design_matrix = design.to_numpy(dtype=float)
        rank = int(np.linalg.matrix_rank(design_matrix))
        if rank < len(design.columns):
            raise ValueError("ANCOVA 설계행렬이 특이하거나 공선성이 있어 계산할 수 없습니다.")
        require_well_conditioned_ols_design(design_matrix, label="ANCOVA OLS")
        return sm.OLS(y, design).fit()

    @classmethod
    def _nested_effect(
        cls,
        reduced_model: Any,
        full_model: Any,
        *,
        term: str,
        label_ko: str,
    ) -> AncovaEffectResult:
        df_num = int(round(reduced_model.df_resid - full_model.df_resid))
        df_den = int(round(full_model.df_resid))
        if df_num <= 0 or df_den <= 0:
            raise ValueError("ANCOVA에는 모형 자유도를 확보할 완전한 관측치가 더 필요합니다.")
        ss_effect = max(float(reduced_model.ssr - full_model.ssr), 0.0)
        ss_error = max(float(full_model.ssr), 0.0)
        ms_error = ss_error / float(full_model.df_resid)
        if np.isclose(ms_error, 0.0):
            f_statistic = float("inf") if ss_effect > 0 else 0.0
        else:
            f_statistic = (ss_effect / df_num) / ms_error
        p_value = float(stats.f.sf(f_statistic, df_num, df_den))
        effect_size = cls._partial_eta_squared(ss_effect, ss_error)
        return AncovaEffectResult(
            term=term,
            label_ko=label_ko,
            f_statistic=float(f_statistic),
            df_num=df_num,
            df_den=df_den,
            p_value=p_value,
            effect_size_name="partial_eta_squared",
            effect_size=effect_size,
        )

    @staticmethod
    def _partial_eta_squared(ss_effect: float, ss_error: float) -> float:
        denominator = ss_effect + ss_error
        if np.isclose(denominator, 0.0):
            return 0.0
        return float(ss_effect / denominator)

    def _covariate_effect(
        self,
        y: pd.Series,
        frame: pd.DataFrame,
        *,
        group: str,
        covariates: list[str],
        group_values: tuple[object, ...],
        covariate: str,
        full_model: Any,
    ) -> AncovaEffectResult:
        reduced_covariates = [
            candidate for candidate in covariates if candidate != covariate
        ]
        reduced_design = self._design_matrix(
            frame,
            group=group,
            covariates=reduced_covariates,
            group_values=group_values,
            include_group=True,
            include_interactions=False,
        )
        reduced_model = self._fit_model(y, reduced_design)
        return self._nested_effect(
            reduced_model,
            full_model,
            term=covariate,
            label_ko=f"공변량: {covariate}",
        )

    @classmethod
    def _design_matrix(
        cls,
        frame: pd.DataFrame,
        *,
        group: str,
        covariates: list[str],
        group_values: tuple[object, ...],
        include_group: bool,
        include_interactions: bool,
    ) -> pd.DataFrame:
        design = pd.DataFrame({"const": 1.0}, index=frame.index)
        for covariate in covariates:
            design[covariate] = frame[covariate].astype(float)
        if include_group:
            dummy_columns = cls._group_dummy_columns(frame, group, group_values)
            design = pd.concat([design, dummy_columns], axis=1)
            if include_interactions:
                for dummy_name in dummy_columns.columns:
                    for covariate in covariates:
                        design[f"{dummy_name}:{covariate}"] = (
                            dummy_columns[dummy_name] * frame[covariate].astype(float)
                        )
        return design.astype(float)

    @classmethod
    def _group_dummy_columns(
        cls,
        frame: pd.DataFrame,
        group: str,
        group_values: tuple[object, ...],
    ) -> pd.DataFrame:
        columns = {}
        for value in group_values[1:]:
            columns[f"group[{cls._display_value(value)}]"] = (
                frame[group] == value
            ).astype(float)
        return pd.DataFrame(columns, index=frame.index)

    @staticmethod
    def _adjusted_means(
        model: Any,
        frame: pd.DataFrame,
        *,
        group: str,
        covariates: list[str],
        group_values: tuple[object, ...],
    ) -> dict[object, float]:
        covariate_means = {
            covariate: float(frame[covariate].mean()) for covariate in covariates
        }
        adjusted: dict[object, float] = {}
        for value in group_values:
            row_data = {"const": 1.0, **covariate_means}
            for dummy_value in group_values[1:]:
                row_data[f"group[{AncovaStep._display_value(dummy_value)}]"] = (
                    1.0 if value == dummy_value else 0.0
                )
            row = pd.DataFrame([row_data])
            row = row.loc[:, model.model.exog_names]
            adjusted[value] = float(model.predict(row).iloc[0])
        return adjusted

    def _group_summaries(
        self,
        dataset: Dataset,
        frame: pd.DataFrame,
        *,
        dv: str,
        group: str,
        group_values: tuple[object, ...],
        adjusted_means: dict[object, float],
    ) -> tuple[AncovaGroupSummary, ...]:
        group_variable = dataset.variables[group]
        summaries = []
        for value in group_values:
            group_frame = frame.loc[frame[group] == value]
            values = group_frame[dv].astype(float)
            sd = None if len(values) < 2 else float(values.std(ddof=1))
            summaries.append(
                AncovaGroupSummary(
                    group_value=self._display_value(value),
                    group_label=self._label_for_value(group_variable, value),
                    n=int(len(group_frame)),
                    raw_mean=float(values.mean()),
                    raw_sd=sd,
                    adjusted_mean=adjusted_means.get(value),
                )
            )
        return tuple(summaries)

    def _ordered_values(self, series: pd.Series, variable: Variable) -> tuple[object, ...]:
        observed_values = list(pd.unique(series.dropna()))
        return tuple(
            sorted(
                observed_values,
                key=lambda value: self._value_sort_key(variable, value),
            )
        )

    @classmethod
    def _value_sort_key(
        cls,
        variable: Variable,
        value: object,
    ) -> tuple[int, int | str, str]:
        value_labels = variable.value_labels or {}
        label_key = cls._value_label_key(value_labels, value)
        if label_key is not None:
            label_order = {
                candidate: index for index, candidate in enumerate(value_labels)
            }
            return (0, label_order[label_key], cls._normalized(value))
        return (1, cls._normalized(value), cls._display_value(value))

    @classmethod
    def _label_for_value(cls, variable: Variable, value: object) -> str:
        value_labels = variable.value_labels or {}
        label_key = cls._value_label_key(value_labels, value)
        if label_key is None:
            return cls._display_value(value)
        return str(value_labels[label_key])

    @staticmethod
    def _value_label_key(
        value_labels: Mapping[object, str],
        value: object,
    ) -> object | None:
        try:
            if value in value_labels:
                return value
        except TypeError:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        if numeric_value in value_labels:
            return numeric_value
        return None

    @staticmethod
    def _display_value(value: object) -> str:
        return str(value)

    @staticmethod
    def _normalized(value: object) -> str:
        return unicodedata.normalize("NFKC", str(value)).casefold()


Step.register_type(AncovaStep.step_type, AncovaStep)
