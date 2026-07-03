from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

import pandas as pd


RecommendationKind = Literal["reliability", "comparison", "regression"]
RecommendationLevel = Literal["강한 추천", "가능한 후보", "주의 필요"]

_EMPTY_MESSAGE = "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."
_CAUTION_ONLY_MESSAGE = "주의가 필요한 후보만 찾았습니다. 직접 확인한 뒤 선택해 주세요."


@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: str
    kind: RecommendationKind
    title_ko: str
    level: RecommendationLevel
    reason_ko: str
    item_keys: list[str] = field(default_factory=list)
    outcome_key: str = ""
    group_key: str = ""
    predictor_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecommendationState:
    candidates: list[RecommendationCandidate]
    default_candidate: RecommendationCandidate | None
    selected_candidate: RecommendationCandidate | None
    message_ko: str = ""


class RecommendationService:
    def recommend(self, dataset: object | None) -> RecommendationState:
        frame = self._frame_for_recommendation(dataset)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return self._empty_state()

        usable = [
            str(column)
            for column in frame.columns
            if self._is_usable_column(frame[column], str(column))
        ]
        numeric = [
            column for column in usable if pd.api.types.is_numeric_dtype(frame[column])
        ]

        item_groups = self._item_groups(frame, numeric)
        candidates: list[RecommendationCandidate] = []
        candidates.extend(self._reliability_candidates(item_groups))
        candidates.extend(self._comparison_candidates(frame, numeric, usable))
        candidates.extend(self._caution_candidates(frame, numeric))
        candidates = self._rank(candidates)

        default = self._default_candidate(candidates)
        return RecommendationState(
            candidates=candidates,
            default_candidate=default,
            selected_candidate=default,
            message_ko=self._message(candidates, default),
        )

    @staticmethod
    def _frame_for_recommendation(dataset: object | None) -> object | None:
        if dataset is None:
            return None
        frame_for_compute = getattr(dataset, "frame_for_compute", None)
        if callable(frame_for_compute):
            return frame_for_compute()
        return getattr(dataset, "df", None)

    @staticmethod
    def _empty_state() -> RecommendationState:
        return RecommendationState(
            candidates=[],
            default_candidate=None,
            selected_candidate=None,
            message_ko=_EMPTY_MESSAGE,
        )

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
        return non_missing.value_counts(normalize=True).iloc[0] < 0.95

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

    def _comparison_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
        usable: list[str],
    ) -> list[RecommendationCandidate]:
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
    def _is_two_group_column(series: pd.Series) -> bool:
        return series.dropna().nunique(dropna=True) == 2

    @staticmethod
    def _preferred_group(group_keys: list[str]) -> str:
        return "gender" if "gender" in group_keys else group_keys[0]

    def _caution_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
    ) -> list[RecommendationCandidate]:
        survey_outcomes = [
            column for column in numeric if self._is_survey_numeric(frame[column])
        ]
        candidates: list[RecommendationCandidate] = []
        for predictor_key in numeric:
            if predictor_key.lower() not in {"age", "education"}:
                continue
            outcome_key = next(
                (column for column in survey_outcomes if column != predictor_key),
                "",
            )
            if not outcome_key:
                continue
            candidates.append(
                RecommendationCandidate(
                    candidate_id=f"regression-caution:{predictor_key}",
                    kind="regression",
                    title_ko=f"회귀 후보: {predictor_key} -> {outcome_key}",
                    level="주의 필요",
                    reason_ko=f"{predictor_key}는 예측 변수로 가능하지만 연구 의도 확인이 필요합니다.",
                    outcome_key=outcome_key,
                    predictor_keys=[predictor_key],
                )
            )
        return candidates

    @staticmethod
    def _rank(
        candidates: list[RecommendationCandidate],
    ) -> list[RecommendationCandidate]:
        level_rank = {"강한 추천": 0, "가능한 후보": 1, "주의 필요": 2}
        kind_rank = {"reliability": 0, "comparison": 1, "regression": 2}
        return sorted(
            candidates,
            key=lambda candidate: (
                level_rank[candidate.level],
                kind_rank[candidate.kind],
                candidate.candidate_id,
            ),
        )

    @staticmethod
    def _default_candidate(
        candidates: list[RecommendationCandidate],
    ) -> RecommendationCandidate | None:
        for candidate in candidates:
            if candidate.level != "주의 필요":
                return candidate
        return None

    @staticmethod
    def _message(
        candidates: list[RecommendationCandidate],
        default: RecommendationCandidate | None,
    ) -> str:
        if not candidates:
            return _EMPTY_MESSAGE
        if default is None:
            return _CAUTION_ONLY_MESSAGE
        return ""
