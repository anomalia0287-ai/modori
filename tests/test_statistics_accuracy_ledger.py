from __future__ import annotations

from pathlib import Path


LEDGER = Path("docs/qa/statistics-accuracy-ledger.md")
LITERATURE_MAP = Path("docs/qa/statistics-numerical-accuracy-literature.md")
LOGISTIC_EVIDENCE = Path("docs/qa/logistic-regression-reference-evidence.md")
LOGISTIC_REVIEW_BRIEF = Path("docs/qa/logistic-regression-external-review-brief.md")
FACTORIAL_EVIDENCE = Path("docs/qa/factorial-anova-reference-evidence.md")


def test_statistics_accuracy_ledger_records_high_risk_module_coverage() -> None:
    text = LEDGER.read_text(encoding="utf-8")

    required_modules = [
        "repeated_measures_anova",
        "friedman",
        "mediation",
        "moderated_mediation",
        "ancova",
        "regression_ols",
        "logistic_regression",
        "compare_groups_t",
        "descriptives_table1",
        "factor_pca",
        "reliability_omega",
        "anova_oneway",
        "rank_based_nonparametric_tests",
        "anova_factorial",
    ]
    for module in required_modules:
        assert f"`{module}`" in text

    required_evidence = [
        "Reference Basis",
        "Tolerance Policy",
        "mixed tolerance",
        "relative tolerance",
        "deterministic bootstrap reproduction",
        "Edge Coverage",
        "Known Limits",
        "Next Accuracy Work",
        "`pytest -p no:cacheprovider tests/test_repeated_measures_anova_step.py tests/test_friedman_step.py tests/test_mediation_step.py tests/test_moderated_mediation_step.py -q`",
    ]
    for evidence in required_evidence:
        assert evidence in text


def test_logistic_reference_evidence_records_reproducible_closure_facts() -> None:
    text = LOGISTIC_EVIDENCE.read_text(encoding="utf-8")

    required_terms = [
        "R 4.5.3",
        "80-digit",
        "1e-10",
        "1e-11",
        "197 passed",
        "1242 passed, 4 skipped",
        "3 passed, 1243 deselected",
        "23315F94BB82EAC76E7F575E1B7DB2D3B4C9602A275C48DCAB4A46D48B59BFCA",
        "package-engine-smoke-ok",
        "LogisticRegressionResult",
        "not adequacy evidence",
        "External Review Disposition",
        "Both actionable external-review findings",
    ]
    for term in required_terms:
        assert term in text


def test_logistic_external_review_brief_is_adversarial_and_reproducible() -> None:
    text = LOGISTIC_REVIEW_BRIEF.read_text(encoding="utf-8")

    required_terms = [
        "d47133c..2e11027",
        "22ad2a4",
        "197 passed",
        "1242 passed, 4 skipped",
        "56 passed",
        "23315F94BB82EAC76E7F575E1B7DB2D3B4C9602A275C48DCAB4A46D48B59BFCA",
        "separation",
        "preconditioning",
        "event coding",
        "pseudo-R2",
        "calibration wording",
        "recommendation promotion",
        "Native visual",
        "Do not approve",
        "F1",
        "F2",
        "Independent review | FINDINGS RECEIVED AND ADDRESSED",
    ]
    for term in required_terms:
        assert term in text


def test_factorial_reference_evidence_records_reproducible_claim_boundaries() -> None:
    text = FACTORIAL_EVIDENCE.read_text(encoding="utf-8")

    required_terms = [
        "complete-cell",
        "equal-cell-weight",
        "FactorialAnovaResult",
        "R 4.5.3",
        "80-digit",
        "formula-oracle parity",
        "anchored parity",
        "library parity",
        "not adequacy evidence",
        "2 x 2",
        "3 x 4",
        "6 x 6",
        "1.992507000",
        "28,714,181",
        "1498 passed, 5 skipped",
        "4 passed, 1499 deselected",
        "22 successful V1 checks",
        "874CE8AAAB203D84C9B3800354CB9B139968648019684C51911E8AD44C4F65AB",
        "VM: Modori-CleanWin-QA-Direct / Off",
        "ModoriPayloadV2.before-rebuild-20260711-010110.vhdx",
        "double-rounding",
        "one-family Holm",
        "pointwise",
        "omega squared",
        "empty cells",
        "package-engine-smoke-ok",
    ]
    for term in required_terms:
        assert term in text


def test_closure_matrix_keeps_adequacy_as_statistical_performance_evidence() -> None:
    text = Path("docs/qa/statistics-accuracy-closure-matrix.md").read_text(
        encoding="utf-8"
    )
    adequacy_row = next(
        line for line in text.splitlines() if line.startswith("| Adequacy |")
    )

    assert "Coverage simulation" in adequacy_row
    assert "iteration policy" not in adequacy_row
    assert "fail-closed limits" not in adequacy_row
    assert "| Complete-cell factorial ANOVA |" in text
    assert "owner review of the written complete-cell Type III" not in text


def test_statistics_literature_map_records_certified_and_product_specific_risks() -> (
    None
):
    text = LITERATURE_MAP.read_text(encoding="utf-8")

    required_terms = [
        "NIST Statistical Reference Datasets",
        "NumAcc",
        "NumAcc4",
        "SmLs01",
        "AtmWtAg",
        "Longley",
        "Filip",
        "Wampler",
        "Wampler5",
        "fail-closed",
        "ties",
        "Wilcoxon",
        "Mann-Whitney",
        "exact-vs-asymptotic",
        "condition-number",
        "default 5000",
        "below 1000",
        "studentized-range",
        "MacKinnon",
        "Hayes",
    ]
    for term in required_terms:
        assert term in text
