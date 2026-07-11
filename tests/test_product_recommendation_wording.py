from __future__ import annotations

from pathlib import Path

from scripts.check_product_wording import product_wording_violations


def test_scanner_rejects_unvalidated_claim_in_product_path(tmp_path: Path) -> None:
    source = tmp_path / "src" / "modori" / "ui" / "copy.py"
    source.parent.mkdir(parents=True)
    source.write_text('LABEL = "강한 추천"', encoding="utf-8")

    assert product_wording_violations(tmp_path) == (
        "src/modori/ui/copy.py:강한 추천",
    )


def test_scanner_rejects_recommendation_accuracy_percentage(tmp_path: Path) -> None:
    source = tmp_path / "library" / "help.md"
    source.parent.mkdir(parents=True)
    source.write_text("추천 정확도 92%", encoding="utf-8")

    assert product_wording_violations(tmp_path) == (
        "library/help.md:recommendation-accuracy-percentage",
    )


def test_scanner_rejects_expert_equivalence_claim(tmp_path: Path) -> None:
    source = tmp_path / "docs" / "product" / "claims.md"
    source.parent.mkdir(parents=True)
    source.write_text("전문가와 동등한 추천", encoding="utf-8")

    assert product_wording_violations(tmp_path) == (
        "docs/product/claims.md:expert-equivalence-claim",
    )


def test_scanner_rejects_expert_first_english_equivalence_claim(
    tmp_path: Path,
) -> None:
    source = tmp_path / "README.md"
    source.write_text("Expert-equivalent recommendation", encoding="utf-8")

    assert product_wording_violations(tmp_path) == (
        "README.md:expert-equivalence-claim",
    )


def test_scanner_allows_historical_benchmark_vocabulary(tmp_path: Path) -> None:
    source = tmp_path / "src" / "modori" / "recommendation_baseline.py"
    source.parent.mkdir(parents=True)
    source.write_text('HISTORICAL = "강한 추천"', encoding="utf-8")

    assert product_wording_violations(tmp_path) == ()


def test_repository_product_text_has_no_unvalidated_claims() -> None:
    assert product_wording_violations(Path.cwd()) == ()
