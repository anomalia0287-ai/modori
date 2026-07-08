from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable
from modori.kruskal_wallis_results import (
    KruskalWallisGroupSummary,
    KruskalWallisResult,
)


_SUPPORTED_DEPENDENT_MEASURES = {Measure.SCALE, Measure.ORDINAL}
_SUPPORTED_GROUP_MEASURES = {Measure.NOMINAL, Measure.ORDINAL}
_SUPPORTED_POSTHOC_METHODS = {"none"}
_SUPPORTED_P_ADJUST = {"none"}


@dataclass
class KruskalWallisStep(Step):
    step_type = "stats.kruskal_wallis"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "dependent": "score",
            "group": "arm",
            "posthoc_method": "none",
            "p_adjust": "none",
            "include_group_mean_sd": True,
            "language": "ko",
        },
        "newer": {"schema_version": 999, "dependent": "score", "group": "arm"},
        "unknown_current": {
            "schema_version": 1,
            "dependent": "score",
            "group": "arm",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("kruskal_wallis params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("kruskal_wallis params use a newer schema_version")
        if version == 1:
            return params
        raise ValueError(f"unsupported kruskal_wallis schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "dependent",
            "group",
            "posthoc_method",
            "p_adjust",
            "include_group_mean_sd",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown kruskal_wallis params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "kruskal_wallis params were not migrated to the current schema"
            )

        dependent = params.get("dependent")
        if not isinstance(dependent, str) or not dependent:
            raise ValueError("dependent must be a variable key")
        group = params.get("group")
        if not isinstance(group, str) or not group:
            raise ValueError("group must be a variable key")

        posthoc_method = str(params.get("posthoc_method", "none"))
        if posthoc_method not in _SUPPORTED_POSTHOC_METHODS:
            raise ValueError("검증된 Kruskal-Wallis 사후검정은 아직 지원하지 않습니다.")
        p_adjust = str(params.get("p_adjust", "none"))
        if p_adjust not in _SUPPORTED_P_ADJUST:
            raise ValueError("kruskal_wallis p_adjust currently supports none only")
        include_group_mean_sd = params.get("include_group_mean_sd", True)
        if not isinstance(include_group_mean_sd, bool):
            raise ValueError("include_group_mean_sd must be boolean")
        language = params.get("language", "ko")
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")

        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "dependent": dependent,
            "group": group,
            "posthoc_method": posthoc_method,
            "p_adjust": p_adjust,
            "include_group_mean_sd": include_group_mean_sd,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {str(params["dependent"]), str(params["group"])}

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return f"Kruskal-Wallis test for {params['dependent']} by {params['group']}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> KruskalWallisResult:
        dataset = ctx.dataset
        dependent = str(params["dependent"])
        group = str(params["group"])
        self._validate_dataset(dataset, dependent, group)

        frame = dataset.frame_for_compute([dependent, group])
        complete = frame.dropna(axis=0, how="any")
        n_total = int(len(frame))
        n_used = int(len(complete))
        n_excluded = int(n_total - n_used)
        if n_used == 0:
            raise ValueError("완전한 관측치가 없어 Kruskal-Wallis 검정을 실행할 수 없습니다.")

        complete = complete.copy()
        complete[dependent] = self._numeric_series(complete[dependent], dependent)
        group_values = self._ordered_values(complete[group], dataset.variables[group])
        if len(group_values) < 3:
            raise ValueError("Kruskal-Wallis 검정은 3개 이상의 비어 있지 않은 그룹이 필요합니다.")

        group_arrays = [
            complete.loc[complete[group] == group_value, dependent].to_numpy(dtype=float)
            for group_value in group_values
        ]
        if any(len(values) < 2 for values in group_arrays):
            raise ValueError("Kruskal-Wallis 검정은 각 그룹에 최소 2개 관측치가 필요합니다.")

        statistic_result = stats.kruskal(*group_arrays)
        statistic = _as_finite_float(statistic_result.statistic, "Kruskal-Wallis H")
        p_value = _as_finite_float(statistic_result.pvalue, "Kruskal-Wallis p-value")
        degrees_of_freedom = len(group_values) - 1
        effect_size = _epsilon_squared(statistic, n_used, len(group_values))
        groups = self._group_summaries(
            dataset=dataset,
            complete=complete,
            dependent=dependent,
            group=group,
            group_values=group_values,
            include_group_mean_sd=bool(params["include_group_mean_sd"]),
        )
        warnings = (
            "검증된 Kruskal-Wallis 사후검정은 아직 제공하지 않는다. "
            "쌍별 비교가 필요하면 방법과 p-value 조정 절차를 명시해 별도 검증해야 한다.",
        )
        return KruskalWallisResult(
            analysis_key="kruskal_wallis",
            title_ko="Kruskal-Wallis 검정",
            dependent=dependent,
            dependent_label=dataset.variables[dependent].label or dependent,
            group=group,
            group_label=dataset.variables[group].label or group,
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            groups=groups,
            statistic_label="H",
            statistic=statistic,
            degrees_of_freedom=degrees_of_freedom,
            p_value=p_value,
            effect_size_label="epsilon_squared",
            effect_size=effect_size,
            posthoc=None,
            warnings_ko=warnings,
            notes_ko=(
                "epsilon_squared는 (H - k + 1) / (N - k) 공식을 사용했다.",
                "중앙 차트 렌더링 훅이 없어 표준 그룹 분포 차트는 아직 생성하지 않는다.",
            ),
            apa_template_id=None,
            chart_spec=None,
            no_canonical_chart_reason_ko=(
                "Kruskal-Wallis ChartSpec의 중앙 렌더링 훅이 아직 연결되지 않아 "
                "차트를 생성하지 않는다."
            ),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, dependent: str, group: str) -> None:
        if dataset.df.empty:
            raise ValueError("데이터셋이 비어 있어 Kruskal-Wallis 검정을 실행할 수 없습니다.")

        missing = [key for key in [dependent, group] if key not in dataset.variables]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"데이터셋에 없는 변수: {names}")

        dependent_measure = dataset.variables[dependent].measure
        if dependent_measure not in _SUPPORTED_DEPENDENT_MEASURES:
            raise ValueError("Kruskal-Wallis 종속 변수는 척도 또는 서열이어야 합니다.")
        if dependent == group:
            raise ValueError("Kruskal-Wallis 종속 변수와 그룹 변수는 서로 달라야 합니다.")
        group_measure = dataset.variables[group].measure
        if group_measure not in _SUPPORTED_GROUP_MEASURES:
            raise ValueError("Kruskal-Wallis 그룹 변수는 명목 또는 서열이어야 합니다.")

    def _group_summaries(
        self,
        *,
        dataset: Dataset,
        complete: pd.DataFrame,
        dependent: str,
        group: str,
        group_values: tuple[object, ...],
        include_group_mean_sd: bool,
    ) -> tuple[KruskalWallisGroupSummary, ...]:
        ranks = pd.Series(
            stats.rankdata(complete[dependent].to_numpy(dtype=float), method="average"),
            index=complete.index,
        )
        summaries = []
        for group_value in group_values:
            mask = complete[group] == group_value
            values = complete.loc[mask, dependent]
            rank_values = ranks.loc[mask]
            mean = float(values.mean()) if include_group_mean_sd else None
            sd = (
                None
                if not include_group_mean_sd or len(values) < 2
                else float(values.std(ddof=1))
            )
            summaries.append(
                KruskalWallisGroupSummary(
                    group_value=self._display_value(group_value),
                    group_label=self._label_for_value(
                        dataset.variables[group],
                        group_value,
                    ),
                    n=int(len(values)),
                    median=float(values.median()),
                    mean_rank=float(rank_values.mean()),
                    mean=mean,
                    sd=sd,
                )
            )
        return tuple(summaries)

    @staticmethod
    def _numeric_series(series: pd.Series, key: str) -> pd.Series:
        try:
            values = pd.to_numeric(series, errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Kruskal-Wallis 종속 변수는 숫자여야 합니다: {key}") from exc
        if len(values) and not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError(f"Kruskal-Wallis 종속 변수는 유한한 숫자여야 합니다: {key}")
        return values

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


def _epsilon_squared(statistic: float, n_used: int, group_count: int) -> float:
    denominator = n_used - group_count
    if denominator <= 0:
        raise ValueError("epsilon_squared 계산에는 N이 그룹 수보다 커야 합니다.")
    return float((statistic - group_count + 1) / denominator)


def _as_finite_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    if not np.isfinite(scalar):
        raise ValueError(f"{label} produced a non-finite value; inference is undefined.")
    return scalar


Step.register_type(KruskalWallisStep.step_type, KruskalWallisStep)
