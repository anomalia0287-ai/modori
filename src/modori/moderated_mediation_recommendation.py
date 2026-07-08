from __future__ import annotations

from dataclasses import dataclass

from modori.mediation_recommendation import _has_numeric_columns
from modori.recommendations import RecommendationCandidate


@dataclass(frozen=True)
class ModeratedMediationEligibilityProvider:
    module_key: str = "moderated_mediation"

    def candidates(
        self,
        dataset: object,
        *,
        active_analysis: bool = False,
    ) -> list[RecommendationCandidate]:
        if active_analysis or not _has_numeric_columns(dataset, ["x", "m", "w", "y"]):
            return []
        return [
            RecommendationCandidate(
                candidate_id="moderated_mediation:7:x:m:w:y",
                kind="moderated_mediation",
                title_ko="조절된 매개분석 후보: Model 7",
                level="주의 필요",
                reason_ko="x, m, w, y로 명명된 척도형 후보가 있으나 PROCESS 모형 확인이 필요합니다.",
                variable_keys=["x", "m", "w", "y"],
            )
        ]


def eligibility_provider() -> ModeratedMediationEligibilityProvider:
    return ModeratedMediationEligibilityProvider()
