from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate


_GROUP_MEASURES = {"nominal", "ordinal"}
_DV_MEASURES = {"scale"}
_MAX_GROUPS = 12


@dataclass(frozen=True)
class AnovaOneWayEligibilityProvider:
    module_key: str = "anova_oneway"

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

        scale_keys = self._numeric_keys(dataset, frame, _DV_MEASURES)
        group_keys = self._group_keys(dataset, frame)
        for group_key in group_keys:
            for dv_key in scale_keys:
                if dv_key == group_key:
                    continue
                if not self._has_anova_shape(frame, dv_key=dv_key, group_key=group_key):
                    continue
                return [
                    RecommendationCandidate(
                        candidate_id=f"anova_oneway:{dv_key}:{group_key}",
                        kind="anova_oneway",
                        title_ko=f"일원분산분석 후보: {dv_key} by {group_key}",
                        routing_tier=RecommendationRoutingTier.SECONDARY,
                        reason_ko=(
                            f"{group_key}가 3개 이상 집단이고 {dv_key}는 척도형 변수라 "
                            "집단 간 평균 차이를 검토할 수 있습니다."
                        ),
                        outcome_key=dv_key,
                        group_key=group_key,
                    )
                ]
        return []

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    def _numeric_keys(
        self,
        dataset: object,
        frame: pd.DataFrame,
        measures: set[str],
    ) -> list[str]:
        variables = self._variables(dataset)
        keys: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None or self._measure_value(variable) not in measures:
                continue
            if not pd.api.types.is_numeric_dtype(frame[key]):
                continue
            if not self._is_usable_numeric(frame[key], key):
                continue
            keys.append(key)
        return keys

    def _group_keys(self, dataset: object, frame: pd.DataFrame) -> list[str]:
        variables = self._variables(dataset)
        keys: list[str] = []
        for column in frame.columns:
            key = str(column)
            variable = variables.get(key)
            if variable is None or self._measure_value(variable) not in _GROUP_MEASURES:
                continue
            observed = frame[key].dropna()
            group_count = int(observed.nunique(dropna=True))
            if not 3 <= group_count <= _MAX_GROUPS:
                continue
            if not self._is_usable_group(frame[key], key):
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
    def _is_usable_numeric(series: pd.Series, column: str) -> bool:
        if AnovaOneWayEligibilityProvider._is_identifier_like(column):
            return False
        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        return non_missing.nunique(dropna=True) > 1

    @staticmethod
    def _is_usable_group(series: pd.Series, column: str) -> bool:
        if AnovaOneWayEligibilityProvider._is_identifier_like(column):
            return False
        non_missing = series.dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        if non_missing.nunique(dropna=True) <= 1:
            return False
        return float(non_missing.value_counts(normalize=True).iloc[0]) < 0.95

    @staticmethod
    def _is_identifier_like(column: str) -> bool:
        lower = column.lower()
        return lower in {"id", "rowid", "row_id", "rownames", "row_names", "index"} or lower.startswith(
            "unnamed:"
        )

    @staticmethod
    def _has_anova_shape(
        frame: pd.DataFrame,
        *,
        dv_key: str,
        group_key: str,
    ) -> bool:
        values = frame.loc[:, [dv_key, group_key]].copy()
        values[dv_key] = pd.to_numeric(values[dv_key], errors="coerce")
        values = values.dropna(axis=0, how="any")
        if values.empty:
            return False
        counts = values.groupby(group_key, dropna=True)[dv_key].count()
        if len(counts) < 3:
            return False
        return bool((counts >= 3).all())


def eligibility_provider() -> AnovaOneWayEligibilityProvider:
    return AnovaOneWayEligibilityProvider()
