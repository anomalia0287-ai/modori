from pathlib import Path


def test_annotation_guide_freezes_actions_vocabularies_and_error_costs() -> None:
    text = Path("docs/qa/recommendation-benchmark-annotation-guide.md").read_text(
        encoding="utf-8"
    )

    for term in (
        "recommendation_eligible",
        "clarification_required",
        "abstention_required",
        "descriptives_table1",
        "paired_comparison",
        "logistic_regression",
        "anova_factorial",
        "unit_of_observation",
        "missing_code_meaning",
        "unsupported_design",
        "conflicting_evidence",
        "E1",
        "E2",
        "E3",
        "E4",
        "E5",
        "baseline-a-predictions.jsonl",
    ):
        assert term in text
    assert "리뷰어에게 제공하지 않는다" in text


def test_pilot_runbook_is_korean_first_and_documents_human_handoff() -> None:
    text = Path("docs/qa/recommendation-benchmark-pilot-runbook.md").read_text(
        encoding="utf-8"
    )

    for term in (
        "통계 자격을 갖춘 독립 검토자 2인",
        "판정자",
        "Codex",
        "Claude",
        "validate-pack",
        "validate-submissions",
        "agreement",
        "cost",
        "score",
        "reviewer-a.xlsx",
        "reviewer-b.xlsx",
        "adjudication.xlsx",
        "20건 모두",
        "descriptives_table1",
        "금라벨",
    ):
        assert term in text
    assert "원본 템플릿을 직접 수정하지 않는다" in text


def test_fixture_readme_registers_recommendation_benchmark_pack() -> None:
    text = Path("tests/fixtures/README.md").read_text(encoding="utf-8")

    assert "recommendation_benchmark" in text
    assert "economics pilot" in text
    assert "not accuracy evidence" in text
