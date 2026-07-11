from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate


_SUPPORTED_MEASURES = {"scale", "ordinal"}
_DEFAULT_VARIABLE_LIMIT = 12


@dataclass(frozen=True)
class FactorPcaEligibilityProvider:
    module_key: str = "factor_pca"

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

        variables = self._eligible_variable_keys(dataset, frame)
        if len(variables) < 3:
            return []
        selected = variables[:_DEFAULT_VARIABLE_LIMIT]
        return [
            RecommendationCandidate(
                candidate_id="factor_pca.item_set",
                kind="factor_pca",
                title_ko="요인/PCA 후보",
                routing_tier=RecommendationRoutingTier.SECONDARY,
                reason_ko=(
                    f"척도·서열 숫자형 문항 {len(selected)}개가 있어 "
                    "문항 묶음의 차원성을 탐색할 수 있습니다. "
                    "구성개념 명명은 별도 해석이 필요합니다."
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

    def _eligible_variable_keys(
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


def eligibility_provider() -> FactorPcaEligibilityProvider:
    return FactorPcaEligibilityProvider()
