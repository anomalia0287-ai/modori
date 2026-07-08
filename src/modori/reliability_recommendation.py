from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from modori.recommendations import RecommendationCandidate, RecommendationLevel


@dataclass(frozen=True)
class ReliabilityEligibilityProvider:
    module_key: str = "reliability"

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
        return self._reliability_candidates(self._item_groups(frame, numeric))

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

    def _item_groups(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
    ) -> list[tuple[str, list[str]]]:
        grouped: dict[str, list[tuple[int, str]]] = {}
        for column in numeric:
            match = re.match(r"^([A-Za-z가-힣_]+)(\d+)$", column)
            if match is None or not self._is_survey_numeric(frame[column]):
                continue
            grouped.setdefault(match.group(1), []).append((int(match.group(2)), column))

        item_groups: list[tuple[str, list[str]]] = []
        for prefix, numbered_columns in grouped.items():
            ordered = [column for _, column in sorted(numbered_columns)]
            if len(ordered) >= 3:
                item_groups.append((prefix, ordered))
        return sorted(item_groups, key=lambda item: item[0])

    @staticmethod
    def _reliability_candidates(
        item_groups: list[tuple[str, list[str]]],
    ) -> list[RecommendationCandidate]:
        candidates: list[RecommendationCandidate] = []
        for prefix, item_keys in item_groups:
            level: RecommendationLevel = "강한 추천" if len(item_keys) >= 5 else "가능한 후보"
            candidates.append(
                RecommendationCandidate(
                    candidate_id=f"reliability:{prefix}",
                    kind="reliability",
                    title_ko=f"신뢰도 분석: {item_keys[0]}-{item_keys[-1]}",
                    level=level,
                    reason_ko=f"같은 접두사 {prefix}로 묶인 {len(item_keys)}개 설문 문항입니다.",
                    item_keys=item_keys,
                )
            )
        return candidates


def eligibility_provider() -> ReliabilityEligibilityProvider:
    return ReliabilityEligibilityProvider()
