from __future__ import annotations

from dataclasses import dataclass

from modori.recommendations import RecommendationCandidate
from modori.repeated_measures_anova_recommendation import _first_numbered_group


@dataclass(frozen=True)
class FriedmanEligibilityProvider:
    module_key: str = "friedman"

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
                candidate_id=f"friedman:{'-'.join(group)}",
                kind="friedman",
                title_ko=f"Friedman 후보: {group[0]}-{group[-1]}",
                level="가능한 후보",
                reason_ko="같은 접두사로 묶인 세 개 이상 반복측정 변수의 순위 기반 대안입니다.",
                variable_keys=list(group),
            )
        ]


def eligibility_provider() -> FriedmanEligibilityProvider:
    return FriedmanEligibilityProvider()
