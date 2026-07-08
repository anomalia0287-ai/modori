from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class RepeatedMeasuresAnovaEligibilityProvider:
    module_key: str = "repeated_measures_anova"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis:
            return []
        group = _first_numbered_group(dataset)
        if not group:
            return []
        return [
            RecommendationCandidate(
                candidate_id=f"repeated_measures_anova:{'-'.join(group)}",
                kind="repeated_measures_anova",
                title_ko=f"반복측정 ANOVA 후보: {group[0]}-{group[-1]}",
                level="가능한 후보",
                reason_ko="같은 접두사로 묶인 세 개 이상 숫자형 반복측정 변수입니다.",
                variable_keys=list(group),
            )
        ]


def _first_numbered_group(dataset: object) -> list[str]:
    frame_for_compute = getattr(dataset, "frame_for_compute", None)
    frame = frame_for_compute() if callable(frame_for_compute) else getattr(dataset, "df", None)
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    grouped: dict[str, list[tuple[int, str]]] = {}
    for column in frame.columns:
        key = str(column)
        match = re.match(r"^([A-Za-z가-힣_]+)(\d+)$", key)
        if match is None or not pd.api.types.is_numeric_dtype(frame[key]):
            continue
        values = pd.to_numeric(frame[key], errors="coerce").dropna()
        if len(values) < 3 or values.nunique(dropna=True) < 2:
            continue
        grouped.setdefault(match.group(1), []).append((int(match.group(2)), key))
    for _prefix, columns in sorted(grouped.items()):
        ordered = [key for _number, key in sorted(columns)]
        if len(ordered) >= 3:
            return ordered
    return []


def eligibility_provider() -> RepeatedMeasuresAnovaEligibilityProvider:
    return RepeatedMeasuresAnovaEligibilityProvider()
