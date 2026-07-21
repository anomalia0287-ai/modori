from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats


FIXTURE_DIR = Path("tests/fixtures/jamovi")
RUNBOOK = Path("docs/qa/jamovi-gui-validation-runbook.md")


def test_jamovi_gui_validation_runbook_references_all_fixtures() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    for fixture in sorted(FIXTURE_DIR.glob("*.csv")):
        assert f"tests\\fixtures\\jamovi\\{fixture.name}" in text

    assert "SPSS-equivalent" in text
    assert "does not replace the automated" in text


def test_jamovi_independent_t_fixture_expected_values() -> None:
    frame = pd.read_csv(FIXTURE_DIR / "independent_t.csv")
    first = frame.loc[frame["group"] == "control", "score"]
    second = frame.loc[frame["group"] == "treatment", "score"]

    reference = stats.ttest_ind(first, second, equal_var=False)

    assert reference.statistic == pytest.approx(-4.714045207910317, abs=1e-12)
    assert reference.df == pytest.approx(18.0, abs=1e-12)
    assert reference.pvalue == pytest.approx(0.00017304393340073732, abs=1e-15)


def test_jamovi_rank_fixture_expected_values() -> None:
    mwu_frame = pd.read_csv(FIXTURE_DIR / "mann_whitney_tied.csv")
    first = mwu_frame.loc[mwu_frame["group"] == "control", "score"]
    second = mwu_frame.loc[mwu_frame["group"] == "treatment", "score"]
    mwu = stats.mannwhitneyu(
        first,
        second,
        alternative="two-sided",
        method="asymptotic",
        use_continuity=True,
    )

    kruskal_frame = pd.read_csv(FIXTURE_DIR / "kruskal_tied.csv")
    groups = [
        kruskal_frame.loc[kruskal_frame["arm"] == arm, "score"]
        for arm in ["A", "B", "C"]
    ]
    kruskal = stats.kruskal(*groups)

    assert mwu.statistic == pytest.approx(11.0, abs=1e-12)
    assert mwu.pvalue == pytest.approx(0.28584403374200407, abs=1e-12)
    assert kruskal.statistic == pytest.approx(9.640000000000004, abs=1e-12)
    assert kruskal.pvalue == pytest.approx(0.008066787139099599, abs=1e-12)


def test_jamovi_paired_and_anova_fixture_expected_values() -> None:
    paired_frame = pd.read_csv(FIXTURE_DIR / "paired_wilcoxon.csv")
    wilcoxon = stats.wilcoxon(
        paired_frame["post"],
        paired_frame["pre"],
        zero_method="wilcox",
        correction=True,
        method="asymptotic",
    )

    anova_frame = pd.read_csv(FIXTURE_DIR / "anova_balanced.csv")
    groups = [
        anova_frame.loc[anova_frame["arm"] == arm, "score"]
        for arm in ["A", "B", "C"]
    ]
    anova = stats.f_oneway(*groups)

    assert wilcoxon.statistic == pytest.approx(0.0, abs=1e-12)
    assert wilcoxon.pvalue == pytest.approx(0.05790726541729722, abs=1e-12)
    assert anova.statistic == pytest.approx(27.0, abs=1e-12)
    assert anova.pvalue == pytest.approx(0.0010000000000000002, abs=1e-15)


def test_jamovi_regression_and_correlation_fixture_expected_values() -> None:
    frame = pd.read_csv(FIXTURE_DIR / "regression_correlation.csv")
    model = sm.OLS(frame["y"], sm.add_constant(frame[["x", "z"]])).fit()
    pearson = stats.pearsonr(frame["x"], frame["y"])

    assert model.params["const"] == pytest.approx(5.257017543859648, abs=1e-12)
    assert model.params["x"] == pytest.approx(0.8884210526315818, abs=1e-12)
    assert model.params["z"] == pytest.approx(-0.7258771929824618, abs=1e-12)
    assert model.rsquared == pytest.approx(0.9828072148335545, abs=1e-12)
    assert model.fvalue == pytest.approx(200.07376458299618, abs=1e-10)
    assert model.f_pvalue == pytest.approx(6.663644620262614e-07, abs=1e-18)
    assert pearson.statistic == pytest.approx(0.9590754396414614, abs=1e-12)
    assert pearson.pvalue == pytest.approx(1.1679512925750067e-05, abs=1e-18)
