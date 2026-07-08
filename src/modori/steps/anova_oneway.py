from __future__ import annotations

import importlib
import os
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from modori.anova_oneway_results import (
    OneWayAnovaAssumptions,
    OneWayAnovaGroupSummary,
    OneWayAnovaNormalityDiagnostic,
    OneWayAnovaPosthocComparison,
    OneWayAnovaPosthocResult,
    OneWayAnovaResult,
)
from modori.cache import matplotlib_cache_dir
from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable


_SUPPORTED_GROUP_MEASURES = {Measure.NOMINAL, Measure.ORDINAL}
_SUPPORTED_POSTHOC = {"auto", "none"}


@dataclass
class OneWayAnovaStep(Step):
    step_type = "stats.anova_oneway"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "dv": "score",
            "group": "arm",
            "posthoc": "auto",
        },
        "newer": {"schema_version": 999, "dv": "score", "group": "arm"},
        "unknown_current": {
            "schema_version": 1,
            "dv": "score",
            "group": "arm",
            "posthoc": "auto",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("anova_oneway params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("anova_oneway params use a newer schema_version")
        if version == cls.CURRENT_SCHEMA_VERSION:
            return params
        raise ValueError(f"unsupported anova_oneway schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {"schema_version", "dv", "group", "posthoc"}
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown anova_oneway params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("anova_oneway params were not migrated to the current schema")
        dv = params.get("dv")
        group = params.get("group")
        if not isinstance(dv, str) or not dv:
            raise ValueError("anova_oneway param dv must be a non-empty string")
        if not isinstance(group, str) or not group:
            raise ValueError("anova_oneway param group must be a non-empty string")
        posthoc = params.get("posthoc", "auto")
        if posthoc not in _SUPPORTED_POSTHOC:
            raise ValueError("anova_oneway posthoc must be auto or none")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "dv": dv,
            "group": group,
            "posthoc": str(posthoc),
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(params["dv"]), str(params["group"])}

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return f"one-way ANOVA for {params['dv']} by {params['group']}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> OneWayAnovaResult:
        dataset = ctx.dataset
        dv = str(params["dv"])
        group = str(params["group"])
        self._validate_dataset(dataset, dv, group)

        source_frame = dataset.frame_for_compute([dv, group])
        n_total = int(len(source_frame))
        frame = source_frame.dropna(axis=0, how="any").copy()
        n_used = int(len(frame))
        n_excluded = n_total - n_used
        frame[dv] = self._numeric_series(frame[dv], dv)
        group_variable = dataset.variables[group]
        group_values = self._ordered_values(frame[group], group_variable)
        grouped_values = tuple(
            frame.loc[frame[group] == value, dv].astype(float)
            for value in group_values
        )
        self._validate_grouped_values(grouped_values)

        summaries = tuple(
            self._group_summary(group_variable, value, values)
            for value, values in zip(group_values, grouped_values, strict=True)
        )
        assumptions = self._assumptions(
            group_variable,
            group_values,
            grouped_values,
        )
        omnibus = stats.f_oneway(*grouped_values)
        f_statistic = _as_finite_float(omnibus.statistic, "F statistic")
        p_value = _as_finite_float(omnibus.pvalue, "p-value")
        df_between = len(grouped_values) - 1
        df_within = n_used - len(grouped_values)
        eta_squared, omega_squared = self._effect_sizes(grouped_values, df_between)
        posthoc = self._posthoc(
            frame,
            dv,
            group,
            group_variable,
            assumptions,
            posthoc=str(params["posthoc"]),
        )
        warnings_ko = (
            "가정 진단은 자동으로 충족 여부를 단정하지 않으며 연구 맥락과 함께 검토해야 한다.",
        )
        notes_ko = (
            "중앙 차트 렌더링 훅이 없어 일원분산분석 차트는 아직 생성하지 않는다.",
        )
        return OneWayAnovaResult(
            analysis_key="anova_oneway",
            title_ko="일원분산분석",
            dv=dv,
            group=group,
            dv_label=dataset.variables[dv].label or dv,
            group_label=group_variable.label or group,
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            groups=summaries,
            assumptions=assumptions,
            f_statistic=f_statistic,
            df_between=df_between,
            df_within=df_within,
            p_value=p_value,
            eta_squared=eta_squared,
            omega_squared=omega_squared,
            posthoc=posthoc,
            warnings_ko=warnings_ko,
            notes_ko=notes_ko,
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "일원분산분석 ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 "
                "차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, dv: str, group: str) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 일원분산분석을 실행할 수 없습니다.")
        if dv == group:
            raise ValueError("종속변수와 그룹 변수는 서로 달라야 합니다.")
        missing = [key for key in (dv, group) if key not in dataset.variables]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"데이터셋에 없는 변수: {names}")
        if dataset.variables[dv].measure is not Measure.SCALE:
            raise ValueError("일원분산분석 종속변수는 척도형이어야 합니다.")
        if dataset.variables[group].measure not in _SUPPORTED_GROUP_MEASURES:
            raise ValueError("일원분산분석 그룹 변수는 명목 또는 서열 척도여야 합니다.")

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"일원분산분석 종속변수는 숫자여야 합니다: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"일원분산분석 종속변수는 유한한 숫자여야 합니다: {key}")
        return values

    @staticmethod
    def _validate_grouped_values(groups: tuple[pd.Series, ...]) -> None:
        if len(groups) < 3:
            raise ValueError("일원분산분석은 3개 이상의 그룹이 필요합니다.")
        too_small = [values for values in groups if len(values) < 3]
        if too_small:
            raise ValueError("일원분산분석은 각 그룹에 최소 3개의 유효 사례가 필요합니다.")
        zero_variance = [values for values in groups if values.nunique(dropna=True) < 2]
        if zero_variance:
            raise ValueError("일원분산분석은 각 그룹에 0이 아닌 분산이 필요합니다.")

    def _assumptions(
        self,
        group_variable: Variable,
        group_values: tuple[object, ...],
        groups: tuple[pd.Series, ...],
    ) -> OneWayAnovaAssumptions:
        levene = stats.levene(*groups, center="median")
        variances = [float(values.var(ddof=1)) for values in groups]
        normality, notes = self._normality_diagnostics(
            group_variable,
            group_values,
            groups,
        )
        return OneWayAnovaAssumptions(
            group_count=len(groups),
            min_group_n=min(int(len(values)) for values in groups),
            max_group_n=max(int(len(values)) for values in groups),
            min_group_variance=min(variances),
            max_group_variance=max(variances),
            levene_statistic=_as_finite_float(levene.statistic, "Levene statistic"),
            levene_p_value=_as_finite_float(levene.pvalue, "Levene p-value"),
            normality=normality,
            notes_ko=notes,
        )

    def _normality_diagnostics(
        self,
        group_variable: Variable,
        group_values: tuple[object, ...],
        groups: tuple[pd.Series, ...],
    ) -> tuple[tuple[OneWayAnovaNormalityDiagnostic, ...], tuple[str, ...]]:
        diagnostics: list[OneWayAnovaNormalityDiagnostic] = []
        skipped = False
        for value, values in zip(group_values, groups, strict=True):
            n = int(len(values))
            if not 3 <= n <= 5000:
                skipped = True
                continue
            shapiro = stats.shapiro(values)
            diagnostics.append(
                OneWayAnovaNormalityDiagnostic(
                    group_value=self._display_value(value),
                    group_label=self._label_for_value(group_variable, value),
                    n=n,
                    test_name="shapiro_wilk",
                    statistic=_as_finite_float(shapiro.statistic, "Shapiro statistic"),
                    p_value=_as_finite_float(shapiro.pvalue, "Shapiro p-value"),
                )
            )
        notes = (
            ("일부 그룹의 표본 수가 Shapiro-Wilk 진단 범위를 벗어나 정규성 진단을 생략했다.",)
            if skipped
            else ()
        )
        return tuple(diagnostics), notes

    def _posthoc(
        self,
        frame: pd.DataFrame,
        dv: str,
        group: str,
        group_variable: Variable,
        assumptions: OneWayAnovaAssumptions,
        *,
        posthoc: str,
    ) -> OneWayAnovaPosthocResult:
        if posthoc == "none":
            return OneWayAnovaPosthocResult(
                method=None,
                status="skipped",
                reason_ko="posthoc=none 설정으로 사후비교를 산출하지 않았다.",
            )
        if assumptions.levene_p_value < 0.05:
            return self._games_howell(frame, dv, group, group_variable)
        return self._tukey_hsd(frame, dv, group, group_variable)

    def _tukey_hsd(
        self,
        frame: pd.DataFrame,
        dv: str,
        group: str,
        group_variable: Variable,
    ) -> OneWayAnovaPosthocResult:
        try:
            result = pairwise_tukeyhsd(
                endog=frame[dv],
                groups=frame[group],
                alpha=0.05,
            )
        except Exception as exc:  # pragma: no cover - dependency failure path
            return OneWayAnovaPosthocResult(
                method="tukey_hsd",
                status="unavailable",
                reason_ko=f"Tukey HSD 산출에 실패해 사후비교를 제공하지 않는다: {exc}",
                method_details=_tukey_method_details(),
            )
        comparisons = []
        pairs = list(_pairwise_values(result.groupsunique))
        for index, (first, second) in enumerate(pairs):
            ci_low, ci_high = result.confint[index]
            comparisons.append(
                OneWayAnovaPosthocComparison(
                    group1_value=self._display_value(first),
                    group2_value=self._display_value(second),
                    group1_label=self._label_for_value(group_variable, first),
                    group2_label=self._label_for_value(group_variable, second),
                    mean_difference=float(result.meandiffs[index]),
                    p_value=float(result.pvalues[index]),
                    ci_low=float(ci_low),
                    ci_high=float(ci_high),
                    reject=bool(result.reject[index]),
                )
            )
        return OneWayAnovaPosthocResult(
            method="tukey_hsd",
            status="computed",
            reason_ko="Levene 검정에서 등분산 가정을 기각하지 않아 Tukey HSD를 산출했다.",
            comparisons=tuple(comparisons),
            method_details=_tukey_method_details(),
        )

    def _games_howell(
        self,
        frame: pd.DataFrame,
        dv: str,
        group: str,
        group_variable: Variable,
    ) -> OneWayAnovaPosthocResult:
        try:
            pg = _import_pingouin()
        except ImportError as exc:
            return OneWayAnovaPosthocResult(
                method="games_howell",
                status="unavailable",
                reason_ko=f"Games-Howell 의존성을 사용할 수 없어 사후비교를 제공하지 않는다: {exc}",
                method_details=_games_howell_method_details(),
            )
        try:
            result = pg.pairwise_gameshowell(data=frame, dv=dv, between=group)
        except Exception as exc:  # pragma: no cover - dependency failure path
            return OneWayAnovaPosthocResult(
                method="games_howell",
                status="unavailable",
                reason_ko=f"Games-Howell 산출에 실패해 사후비교를 제공하지 않는다: {exc}",
                method_details=_games_howell_method_details(),
            )
        comparisons = []
        for _, row in result.iterrows():
            first = row["A"]
            second = row["B"]
            comparisons.append(
                OneWayAnovaPosthocComparison(
                    group1_value=self._display_value(first),
                    group2_value=self._display_value(second),
                    group1_label=self._label_for_value(group_variable, first),
                    group2_label=self._label_for_value(group_variable, second),
                    mean_difference=float(row["diff"]),
                    p_value=float(row["pval"]),
                    ci_low=None,
                    ci_high=None,
                    reject=None,
                )
            )
        return OneWayAnovaPosthocResult(
            method="games_howell",
            status="computed",
            reason_ko="Levene 검정에서 등분산 가정을 기각해 Games-Howell을 산출했다.",
            comparisons=tuple(comparisons),
            method_details=_games_howell_method_details(),
        )

    @staticmethod
    def _group_summary(
        variable: Variable,
        value: object,
        values: pd.Series,
    ) -> OneWayAnovaGroupSummary:
        return OneWayAnovaGroupSummary(
            group_value=OneWayAnovaStep._display_value(value),
            group_label=OneWayAnovaStep._label_for_value(variable, value),
            n=int(len(values)),
            mean=float(values.mean()),
            sd=float(values.std(ddof=1)),
            median=float(values.median()),
        )

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

    @staticmethod
    def _effect_sizes(
        groups: tuple[pd.Series, ...],
        df_between: int,
    ) -> tuple[float, float]:
        all_values = pd.concat(groups, ignore_index=True).astype(float)
        grand_mean = float(all_values.mean())
        centered_groups = tuple(values.astype(float) - grand_mean for values in groups)
        ss_between = sum(
            len(values) * float(values.mean()) ** 2 for values in centered_groups
        )
        ss_within = sum(
            float(((values - float(values.mean())) ** 2).sum())
            for values in centered_groups
        )
        ss_total = ss_between + ss_within
        df_within = len(all_values) - len(groups)
        ms_within = ss_within / df_within
        eta_squared = ss_between / ss_total
        omega_squared = (ss_between - (df_between * ms_within)) / (ss_total + ms_within)
        return float(eta_squared), float(omega_squared)


def _pairwise_values(values: np.ndarray) -> tuple[tuple[object, object], ...]:
    pairs = []
    for left_index, left in enumerate(values):
        for right in values[left_index + 1 :]:
            pairs.append((left, right))
    return tuple(pairs)


def _tukey_method_details() -> dict[str, object]:
    return {
        "alpha": 0.05,
        "df_method": "pooled_residual",
        "equal_variance_assumed": True,
        "p_value_source": "statsmodels.stats.multicomp.pairwise_tukeyhsd",
        "tail_function": "scipy.stats.studentized_range.sf",
    }


def _games_howell_method_details() -> dict[str, object]:
    return {
        "alpha": 0.05,
        "df_method": "welch_satterthwaite",
        "equal_variance_assumed": False,
        "p_value_source": "pingouin.pairwise_gameshowell",
        "tail_function": "scipy.stats.studentized_range.sf",
    }


def _import_pingouin() -> Any:
    os.environ["MPLCONFIGDIR"] = str(matplotlib_cache_dir())
    return importlib.import_module("pingouin")


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"One-way ANOVA produced non-finite {label}; inference is undefined.")
    return scalar


Step.register_type(OneWayAnovaStep.step_type, OneWayAnovaStep)
