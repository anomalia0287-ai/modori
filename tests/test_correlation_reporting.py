from __future__ import annotations

from modori.correlation_reporting import prose_for_correlation, table_for_correlation
from modori.correlation_results import CorrelationPairResult, CorrelationResult


def test_correlation_reporting_formats_pair_rows_and_korean_noncausal_prose() -> None:
    result = CorrelationResult(
        analysis_key="correlation",
        title_ko="상관분석",
        variables=("stress", "sleep"),
        method_policy="spearman",
        missing_policy="pairwise",
        n_total=5,
        pairs=(
            CorrelationPairResult(
                x="stress",
                y="sleep",
                x_label="스트레스",
                y_label="수면",
                method="spearman",
                statistic_label="rho",
                coefficient=-0.81234,
                p_value=0.04991,
                n=5,
                excluded_n=0,
            ),
        ),
        warnings_ko=(),
        notes_ko=("표준 상관분석 차트는 아직 정의하지 않았다.",),
        no_canonical_chart_reason_ko="상관행렬 렌더링 훅이 아직 중앙 보고 경로에 연결되지 않았다.",
    )

    prose = prose_for_correlation(result, language="ko")
    rows = table_for_correlation(result)

    assert "상관" in prose
    assert "영향" not in prose
    assert "예측" not in prose
    assert "affect" not in prose.lower()
    assert rows == [
        {
            "x": "스트레스",
            "y": "수면",
            "method": "spearman",
            "statistic": "rho",
            "coefficient": "-0.812",
            "p_value": "0.050",
            "p_adjusted": "",
            "n": "5",
            "excluded_n": "0",
            "warnings": "",
        }
    ]


def test_correlation_reporting_includes_multiple_comparison_guidance_for_matrix() -> None:
    result = CorrelationResult(
        analysis_key="correlation",
        title_ko="상관분석",
        variables=("x", "y", "z"),
        method_policy="auto",
        missing_policy="listwise",
        n_total=10,
        pairs=(
            CorrelationPairResult(
                x="x",
                y="y",
                x_label="X",
                y_label="Y",
                method="pearson",
                statistic_label="r",
                coefficient=0.5,
                p_value=0.1,
                n=8,
                excluded_n=2,
            ),
            CorrelationPairResult(
                x="x",
                y="z",
                x_label="X",
                y_label="Z",
                method="pearson",
                statistic_label="r",
                coefficient=0.6,
                p_value=0.08,
                n=8,
                excluded_n=2,
            ),
        ),
        warnings_ko=("상관행렬은 여러 쌍을 동시에 검토하므로 다중비교 가능성을 함께 해석해야 한다.",),
        notes_ko=(),
        no_canonical_chart_reason_ko="중앙 차트 렌더링 훅이 아직 없다.",
    )

    prose = prose_for_correlation(result, language="ko")

    assert "다중비교" in prose
    assert "조정" in prose
