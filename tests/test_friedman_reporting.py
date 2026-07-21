from __future__ import annotations

from modori.friedman_reporting import prose_for_friedman, table_for_friedman
from modori.friedman_results import FriedmanLevelSummary, FriedmanResult


def test_reporting_formats_level_rows_and_korean_noncausal_prose() -> None:
    result = FriedmanResult(
        analysis_key="friedman",
        title_ko="Friedman 검정",
        measures=("pre", "mid", "post"),
        within_factor="time",
        n_total=10,
        n_used=8,
        n_excluded=2,
        levels=(
            FriedmanLevelSummary(
                variable="pre",
                level_index=1,
                level_label="사전",
                n=8,
                median=2.5,
                mean_rank=1.2,
                mean=2.7,
                sd=1.1,
            ),
            FriedmanLevelSummary(
                variable="post",
                level_index=2,
                level_label="사후",
                n=8,
                median=5.5,
                mean_rank=2.8,
                mean=5.7,
                sd=1.4,
            ),
        ),
        statistic_label="Q",
        statistic=9.1234,
        degrees_of_freedom=2,
        p_value=0.0101,
        kendalls_w=0.5702,
        posthoc=None,
        warnings_ko=("검증된 사후검정은 아직 제공하지 않는다.",),
        notes_ko=("중앙 차트 렌더링 훅이 없어 차트는 생성하지 않는다.",),
        no_canonical_chart_reason_ko="중앙 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_friedman(result, language="ko")
    rows = table_for_friedman(result)

    assert "Friedman" in prose
    assert "영향" not in prose
    assert "affect" not in prose.lower()
    assert rows == [
        {
            "level": "사전",
            "variable": "pre",
            "n": "8",
            "median": "2.50",
            "mean_rank": "1.20",
            "mean": "2.70",
            "SD": "1.10",
            "statistic": "Q",
            "Q": "9.123",
            "df": "2",
            "p_value": "0.010",
            "kendalls_w": "0.570",
            "posthoc": "",
            "warnings": "검증된 사후검정은 아직 제공하지 않는다.",
        },
        {
            "level": "사후",
            "variable": "post",
            "n": "8",
            "median": "5.50",
            "mean_rank": "2.80",
            "mean": "5.70",
            "SD": "1.40",
            "statistic": "Q",
            "Q": "9.123",
            "df": "2",
            "p_value": "0.010",
            "kendalls_w": "0.570",
            "posthoc": "",
            "warnings": "검증된 사후검정은 아직 제공하지 않는다.",
        },
    ]
