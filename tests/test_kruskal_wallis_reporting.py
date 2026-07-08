from __future__ import annotations

from modori.kruskal_wallis_reporting import (
    prose_for_kruskal_wallis,
    table_for_kruskal_wallis,
)
from modori.kruskal_wallis_results import (
    KruskalWallisGroupSummary,
    KruskalWallisResult,
)


def test_reporting_formats_group_rows_and_korean_noncausal_prose() -> None:
    result = KruskalWallisResult(
        analysis_key="kruskal_wallis",
        title_ko="Kruskal-Wallis 검정",
        dependent="score",
        dependent_label="만족도",
        group="arm",
        group_label="처치군",
        n_total=12,
        n_used=10,
        n_excluded=2,
        groups=(
            KruskalWallisGroupSummary(
                group_value="A",
                group_label="A군",
                n=4,
                median=3.5,
                mean_rank=4.25,
                mean=3.75,
                sd=1.5,
            ),
            KruskalWallisGroupSummary(
                group_value="B",
                group_label="B군",
                n=3,
                median=6.0,
                mean_rank=7.1,
                mean=6.2,
                sd=0.8,
            ),
        ),
        statistic_label="H",
        statistic=4.5678,
        degrees_of_freedom=1,
        p_value=0.0321,
        effect_size_label="epsilon_squared",
        effect_size=0.2468,
        posthoc=None,
        warnings_ko=("검증된 사후검정은 아직 제공하지 않는다.",),
        notes_ko=("중앙 차트 렌더링 훅이 없어 차트는 생성하지 않는다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_kruskal_wallis(result, language="ko")
    rows = table_for_kruskal_wallis(result)

    assert "Kruskal-Wallis" in prose
    assert "만족도" in prose
    assert "영향" not in prose
    assert "효과" not in prose
    assert "affect" not in prose.lower()
    assert rows == [
        {
            "group": "A군",
            "n": "4",
            "median": "3.50",
            "mean_rank": "4.25",
            "mean": "3.75",
            "SD": "1.50",
            "statistic": "H",
            "H": "4.568",
            "df": "1",
            "p_value": "0.032",
            "effect_size": "epsilon_squared",
            "effect_size_value": "0.247",
            "posthoc": "",
            "warnings": "검증된 사후검정은 아직 제공하지 않는다.",
        },
        {
            "group": "B군",
            "n": "3",
            "median": "6.00",
            "mean_rank": "7.10",
            "mean": "6.20",
            "SD": "0.80",
            "statistic": "H",
            "H": "4.568",
            "df": "1",
            "p_value": "0.032",
            "effect_size": "epsilon_squared",
            "effect_size_value": "0.247",
            "posthoc": "",
            "warnings": "검증된 사후검정은 아직 제공하지 않는다.",
        },
    ]


def test_reporting_handles_omitted_context_mean_sd() -> None:
    result = KruskalWallisResult(
        analysis_key="kruskal_wallis",
        title_ko="Kruskal-Wallis 검정",
        dependent="score",
        dependent_label="점수",
        group="arm",
        group_label="집단",
        n_total=9,
        n_used=9,
        n_excluded=0,
        groups=(
            KruskalWallisGroupSummary(
                group_value="A",
                group_label="A",
                n=3,
                median=1.0,
                mean_rank=2.0,
            ),
        ),
        statistic_label="H",
        statistic=1.0,
        degrees_of_freedom=2,
        p_value=0.6,
        effect_size_label="epsilon_squared",
        effect_size=0.0,
        posthoc=None,
        warnings_ko=(),
        notes_ko=(),
    )

    rows = table_for_kruskal_wallis(result)

    assert rows[0]["mean"] == ""
    assert rows[0]["SD"] == ""
