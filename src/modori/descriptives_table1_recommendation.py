from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate


_DESCRIPTIVE_MEASURES = {"scale", "ordinal", "nominal"}
_GROUP_MEASURES = {"ordinal", "nominal"}
_DEFAULT_VARIABLE_LIMIT = 20
_GROUP_NAME_HINTS = {
    "arm",
    "category",
    "class",
    "cohort",
    "condition",
    "department",
    "gender",
    "grade",
    "group",
    "major",
    "region",
    "school",
    "sex",
    "site",
    "treatment",
    "type",
}
_KOREAN_GROUP_NAME_HINTS = ("집단", "그룹", "성별", "조건", "지역", "학과")


@dataclass(frozen=True)
class DescriptivesTable1EligibilityProvider:
    module_key: str = "descriptives_table1"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis:
            return []

        frame = self._frame(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []

        variable_keys = self._usable_variable_keys(dataset, frame)
        if not variable_keys:
            return []

        group_key = self._first_plausible_group_key(dataset, frame, variable_keys)
        default_variable_keys = [
            key for key in variable_keys if key != group_key
        ][:_DEFAULT_VARIABLE_LIMIT]
        if not default_variable_keys:
            group_key = ""
            default_variable_keys = variable_keys[:_DEFAULT_VARIABLE_LIMIT]

        return [
            RecommendationCandidate(
                candidate_id="descriptives_table1.default",
                kind="descriptives",
                title_ko="기술통계 표 1",
                routing_tier=RecommendationRoutingTier.PRIMARY,
                reason_ko=(
                    "가져온 데이터셋에 요약 가능한 변수가 있어 "
                    "기술통계 표를 먼저 생성할 수 있습니다."
                ),
                variable_keys=default_variable_keys,
                group_key=group_key,
            )
        ]

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    def _usable_variable_keys(
        self,
        dataset: object,
        frame: pd.DataFrame,
    ) -> list[str]:
        variables = self._variables(dataset)
        usable: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None:
                continue
            if self._measure_value(variable) not in _DESCRIPTIVE_MEASURES:
                continue
            if not self._is_usable_column(frame[key], key):
                continue
            usable.append(key)
        return usable

    def _first_plausible_group_key(
        self,
        dataset: object,
        frame: pd.DataFrame,
        variable_keys: list[str],
    ) -> str:
        if len(variable_keys) <= 1:
            return ""

        variables = self._variables(dataset)
        for key in variable_keys:
            if not self._has_group_name_hint(key):
                continue
            variable = variables.get(key)
            if variable is None or self._measure_value(variable) not in _GROUP_MEASURES:
                continue
            observed_count = frame[key].dropna().nunique(dropna=True)
            if 2 <= int(observed_count) <= 12:
                return key
        return ""

    @staticmethod
    def _variables(dataset: object) -> Mapping[str, object]:
        variables = getattr(dataset, "variables", {})
        return variables if isinstance(variables, Mapping) else {}

    @staticmethod
    def _measure_value(variable: object) -> str:
        measure = getattr(variable, "measure", "")
        value = getattr(measure, "value", measure)
        return str(value)

    @staticmethod
    def _is_usable_column(series: pd.Series, column: str) -> bool:
        lower = column.lower()
        if lower in {"id", "rowid", "row_id", "rownames", "row_names", "index"}:
            return False
        if lower.startswith("unnamed:"):
            return False

        non_missing = series.dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        if non_missing.nunique(dropna=True) <= 1:
            return False
        return float(non_missing.value_counts(normalize=True).iloc[0]) < 0.95

    @staticmethod
    def _has_group_name_hint(key: str) -> bool:
        lower = key.lower()
        parts = [lower, *lower.split("_"), *lower.split("-")]
        return (
            lower in _GROUP_NAME_HINTS
            or any(part in _GROUP_NAME_HINTS for part in parts)
            or any(hint in lower for hint in _KOREAN_GROUP_NAME_HINTS)
        )


def eligibility_provider() -> DescriptivesTable1EligibilityProvider:
    return DescriptivesTable1EligibilityProvider()
