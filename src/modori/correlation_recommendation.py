from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from modori.recommendations import RecommendationCandidate


_SUPPORTED_MEASURES = {"scale", "ordinal"}
_DEFAULT_VARIABLE_LIMIT = 6


@dataclass(frozen=True)
class CorrelationEligibilityProvider:
    module_key: str = "correlation"

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

        variables = self._correlatable_variable_keys(dataset, frame)
        if len(variables) < 2:
            return []
        selected = variables[:_DEFAULT_VARIABLE_LIMIT]
        return [
            RecommendationCandidate(
                candidate_id="correlation.matrix",
                kind="correlation",
                title_ko="상관분석 후보",
                level="가능한 후보",
                reason_ko=(
                    f"숫자형 척도·서열 변수 {len(selected)}개 사이의 상관을 확인할 수 있습니다."
                ),
                variable_keys=selected,
            )
        ]

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    def _correlatable_variable_keys(
        self,
        dataset: object,
        frame: pd.DataFrame,
    ) -> list[str]:
        variables = self._variables(dataset)
        keys: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None:
                continue
            if self._measure_value(variable) not in _SUPPORTED_MEASURES:
                continue
            if not pd.api.types.is_numeric_dtype(frame[key]):
                continue
            if not self._is_usable_column(frame[key], key):
                continue
            keys.append(key)
        return keys

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

        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        if non_missing.nunique(dropna=True) <= 1:
            return False
        return float(non_missing.value_counts(normalize=True).iloc[0]) < 0.95


def eligibility_provider() -> CorrelationEligibilityProvider:
    return CorrelationEligibilityProvider()
