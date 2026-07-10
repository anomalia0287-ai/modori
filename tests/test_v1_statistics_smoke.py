from __future__ import annotations


def test_v1_statistics_smoke_executes_every_v1_engine_path() -> None:
    from modori.v1_statistics_smoke import v1_statistics_smoke_payload

    payload = v1_statistics_smoke_payload()

    assert payload["ok"] is True
    executed = {check["key"] for check in payload["checks"]}
    assert executed == {
        "descriptives_table1",
        "reliability",
        "frequency",
        "crosstab_fisher",
        "pearson_correlation",
        "spearman_correlation",
        "welch_t",
        "mann_whitney",
        "paired_t",
        "wilcoxon",
        "anova_oneway",
        "kruskal_wallis",
        "ancova",
        "repeated_measures_anova",
        "friedman",
        "mediation",
        "moderated_mediation",
        "factor_pca_pca",
        "factor_pca_efa",
        "regression_categorical_interaction",
        "logistic_regression",
    }
    assert all(check["ok"] is True for check in payload["checks"])
    assert all(check["analysis_type"] for check in payload["checks"])
    logistic = next(
        check for check in payload["checks"] if check["key"] == "logistic_regression"
    )
    assert logistic["analysis_type"] == "LogisticRegressionResult"
