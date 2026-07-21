from __future__ import annotations

from modori.moderated_mediation_reporting import (
    prose_for_moderated_mediation,
    table_for_moderated_mediation,
)
from modori.moderated_mediation_results import (
    ConditionalIndirectEffect,
    ModeratedMediationModelFit,
    ModeratedMediationResult,
)


def test_reporting_formats_conditional_effects_and_noncausal_korean_prose() -> None:
    result = ModeratedMediationResult(
        analysis_key="moderated_mediation",
        title_ko="조절된 매개분석",
        model=7,
        x="x",
        mediator="m",
        moderator="w",
        y="y",
        covariates=("c1",),
        n_total=34,
        n_used=32,
        n_excluded=2,
        moderator_mean=1.5,
        moderator_sd=0.8,
        conditional_effects=(
            ConditionalIndirectEffect(
                moderator_label="mean - 1 SD",
                moderator_value=0.7,
                effect=0.21,
                ci=(0.10, 0.32),
            ),
            ConditionalIndirectEffect(
                moderator_label="mean",
                moderator_value=1.5,
                effect=0.36,
                ci=(0.22, 0.50),
            ),
        ),
        index_of_moderated_mediation=0.18,
        index_ci=(0.08, 0.29),
        bootstrap_iterations=1000,
        bootstrap_seed=20260708,
        bootstrap_ci_level=0.95,
        mediator_model=ModeratedMediationModelFit(
            outcome="m",
            predictors=("x_centered", "w_centered", "x_centered:w_centered", "c1"),
            r_squared=0.74,
        ),
        outcome_model=ModeratedMediationModelFit(
            outcome="y",
            predictors=("x_centered", "m", "c1"),
            r_squared=0.88,
        ),
        warnings_ko=("횡단면 자료에서는 인과적 조건부 간접효과로 단정하지 않는다.",),
        notes_ko=("부트스트랩 CI는 percentile 방법을 사용했다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_moderated_mediation(result, language="ko")
    rows = table_for_moderated_mediation(result)

    assert "조절된 매개분석" in prose
    assert "조건부 간접효과" in prose
    assert "원인" not in prose
    assert "영향" not in prose
    assert "cause" not in prose.lower()
    assert rows[0] == {
        "model": "7",
        "moderator_level": "mean - 1 SD",
        "moderator_value": "0.700",
        "conditional_indirect_effect": "0.210",
        "ci_low": "0.100",
        "ci_high": "0.320",
        "index_of_moderated_mediation": "0.180",
        "index_ci_low": "0.080",
        "index_ci_high": "0.290",
        "bootstrap_iterations": "1000",
        "warnings": "횡단면 자료에서는 인과적 조건부 간접효과로 단정하지 않는다.",
    }
