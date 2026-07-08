from __future__ import annotations

from modori.mediation_reporting import prose_for_mediation, table_for_mediation
from modori.mediation_results import MediationEffect, MediationModelFit, MediationResult


def test_reporting_formats_paths_bootstrap_ci_and_noncausal_korean_prose() -> None:
    result = MediationResult(
        analysis_key="mediation",
        title_ko="매개분석",
        x="x",
        mediator="m",
        y="y",
        covariates=("c1",),
        n_total=30,
        n_used=28,
        n_excluded=2,
        path_a=MediationEffect(
            name="a",
            predictor="x",
            outcome="m",
            b=0.61,
            se=0.08,
            t=7.5,
            p_value=0.001,
            ci=(0.45, 0.77),
        ),
        path_b=MediationEffect(
            name="b",
            predictor="m",
            outcome="y",
            b=0.83,
            se=0.07,
            t=11.1,
            p_value=0.001,
            ci=(0.68, 0.98),
        ),
        direct_effect=MediationEffect(
            name="c_prime",
            predictor="x",
            outcome="y",
            b=0.32,
            se=0.06,
            t=5.1,
            p_value=0.001,
            ci=(0.20, 0.44),
        ),
        total_effect=MediationEffect(
            name="c",
            predictor="x",
            outcome="y",
            b=0.83,
            se=0.04,
            t=20.2,
            p_value=0.001,
            ci=(0.75, 0.91),
        ),
        indirect_effect=0.5063,
        indirect_ci=(0.35, 0.68),
        bootstrap_iterations=1000,
        bootstrap_seed=20260708,
        bootstrap_ci_level=0.95,
        mediator_model=MediationModelFit(outcome="m", predictors=("x", "c1"), r_squared=0.74),
        outcome_model=MediationModelFit(outcome="y", predictors=("x", "m", "c1"), r_squared=0.91),
        total_model=MediationModelFit(outcome="y", predictors=("x", "c1"), r_squared=0.84),
        warnings_ko=("횡단면 자료에서는 인과 매개로 단정하지 않는다.",),
        notes_ko=("부트스트랩 CI는 percentile 방법을 사용했다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_mediation(result, language="ko")
    rows = table_for_mediation(result)

    assert "매개분석" in prose
    assert "간접효과" in prose
    assert "원인" not in prose
    assert "영향" not in prose
    assert "cause" not in prose.lower()
    assert rows[0] == {
        "effect": "a",
        "predictor": "x",
        "outcome": "m",
        "b": "0.610",
        "SE": "0.080",
        "t": "7.500",
        "p_value": "0.001",
        "ci_low": "0.450",
        "ci_high": "0.770",
        "indirect_effect": "0.506",
        "indirect_ci_low": "0.350",
        "indirect_ci_high": "0.680",
        "bootstrap_iterations": "1000",
        "warnings": "횡단면 자료에서는 인과 매개로 단정하지 않는다.",
    }
