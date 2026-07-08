from __future__ import annotations

from pathlib import Path


LEDGER = Path("docs/qa/statistics-accuracy-ledger.md")
LITERATURE_MAP = Path("docs/qa/statistics-numerical-accuracy-literature.md")


def test_statistics_accuracy_ledger_records_high_risk_module_coverage() -> None:
    text = LEDGER.read_text(encoding="utf-8")

    required_modules = [
        "repeated_measures_anova",
        "friedman",
        "mediation",
        "moderated_mediation",
        "ancova",
        "regression_ols",
        "factor_pca",
        "reliability_omega",
        "anova_oneway",
        "rank_based_nonparametric_tests",
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


def test_statistics_literature_map_records_certified_and_product_specific_risks() -> None:
    text = LITERATURE_MAP.read_text(encoding="utf-8")

    required_terms = [
        "NIST Statistical Reference Datasets",
        "NumAcc",
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
