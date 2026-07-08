from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class CompareGroupsEligibilityProvider:
    module_key: str = "compare_groups"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        frame = self._frame(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []

        usable = [
            str(column)
            for column in frame.columns
            if self._is_usable_column(frame[column], str(column))
        ]
        numeric = [
            column for column in usable if pd.api.types.is_numeric_dtype(frame[column])
        ]
        group_keys = [
            column for column in usable if self._is_two_group_column(frame[column])
        ]
        outcome_keys = [
            column
            for column in numeric
            if column not in group_keys and self._is_survey_numeric(frame[column])
        ]
        if not group_keys or not outcome_keys:
            return []

        group_key = self._preferred_group(group_keys)
        outcome_key = outcome_keys[0]
        return [
            RecommendationCandidate(
                candidate_id=f"comparison:{outcome_key}:{group_key}",
                kind="comparison",
                title_ko=f"집단 비교: {outcome_key} by {group_key}",
                level="강한 추천",
                reason_ko=f"{group_key}는 두 집단 변수이고 {outcome_key}는 숫자형 결과 변수입니다.",
                outcome_key=outcome_key,
                group_key=group_key,
            )
        ]

    @staticmethod
    def _frame(dataset: object) -> object | None:
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

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
        return bool(non_missing.value_counts(normalize=True).iloc[0] < 0.95)

    @staticmethod
    def _is_survey_numeric(series: pd.Series) -> bool:
        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if non_missing.empty:
            return False
        if non_missing.nunique() > 11:
            return False
        return float(non_missing.min()) >= 0 and float(non_missing.max()) <= 10

    @staticmethod
    def _is_two_group_column(series: pd.Series) -> bool:
        return bool(series.dropna().nunique(dropna=True) == 2)

    @staticmethod
    def _preferred_group(group_keys: list[str]) -> str:
        return "gender" if "gender" in group_keys else group_keys[0]


def eligibility_provider() -> CompareGroupsEligibilityProvider:
    return CompareGroupsEligibilityProvider()
