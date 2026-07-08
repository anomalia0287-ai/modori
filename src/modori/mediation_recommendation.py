from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class MediationEligibilityProvider:
    module_key: str = "mediation"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis or not _has_numeric_columns(dataset, ["x", "m", "y"]):
            return []
        return [
            RecommendationCandidate(
                candidate_id="mediation:x:m:y",
                kind="mediation",
                title_ko="매개분석 후보: x -> m -> y",
                level="주의 필요",
                reason_ko="x, m, y로 명명된 척도형 후보가 있으나 연구모형 확인이 필요합니다.",
                variable_keys=["x", "m", "y"],
            )
        ]


def _has_numeric_columns(dataset: object, keys: list[str]) -> bool:
    frame_for_compute = getattr(dataset, "frame_for_compute", None)
    frame = frame_for_compute() if callable(frame_for_compute) else getattr(dataset, "df", None)
    if not isinstance(frame, pd.DataFrame):
        return False
    if any(key not in frame.columns for key in keys):
        return False
    for key in keys:
        values = pd.to_numeric(frame[key], errors="coerce").dropna()
        if len(values) < 6 or values.nunique(dropna=True) < 2:
            return False
    return True


def eligibility_provider() -> MediationEligibilityProvider:
    return MediationEligibilityProvider()
