from __future__ import annotations

import importlib

import pytest

from modori.frequency_crosstab_results import (
    AssociationTestResult,
    CrosstabCell,
    CrosstabTableResult,
    FrequencyCategoryRow,
    FrequencyCrosstabResult,
    FrequencyVariableTable,
)


def _reporting_module():
    try:
        return importlib.import_module("modori.frequency_crosstab_reporting")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.frequency_crosstab_reporting":
            pytest.fail("modori.frequency_crosstab_reporting is not implemented")
        raise


def test_frequency_reporting_is_korean_first_and_formats_rows() -> None:
    result = FrequencyCrosstabResult(
        analysis_key="frequency_crosstab",
        title_ko="빈도분석",
        mode="frequency",
        variables=("gender",),
        n_total=4,
        frequency_tables=(
            FrequencyVariableTable(
                key="gender",
                label="성별",
                measure="nominal",
                n_total=4,
                n_obs=3,
                n_missing=1,
                categories=(
                    FrequencyCategoryRow(
                        value="F",
                        label="여성",
                        count=2,
                        percent=66.6667,
                    ),
                ),
            ),
        ),
    )

    reporting = _reporting_module()
    prose = reporting.prose_for_frequency_crosstab(result)
    rows = reporting.table_for_frequency_crosstab(result)

    assert prose.startswith("빈도분석은")
    assert "영향" not in prose
    assert rows == [
        {
            "section": "frequency",
            "variable": "성별",
            "category": "여성",
            "count": "2",
            "percent": "66.7",
            "n": "3",
            "missing": "1",
        }
    ]


def test_crosstab_reporting_is_non_causal_and_includes_test_summary() -> None:
    test = AssociationTestResult(
        pearson_chi_square=1.2,
        df=1,
        pearson_p_value=0.273321,
        expected_counts=((1.5, 1.5), (1.5, 1.5)),
        expected_cell_warning=True,
        min_expected_count=1.5,
        low_expected_cell_count=4,
        low_expected_cell_percent=100.0,
        cramers_v=0.4472136,
        selected_method="fisher_exact",
        selected_p_value=0.485714,
        fisher_odds_ratio=4.0,
    )
    result = FrequencyCrosstabResult(
        analysis_key="frequency_crosstab",
        title_ko="교차분석",
        mode="crosstab",
        variables=("group", "event"),
        n_total=6,
        crosstab=CrosstabTableResult(
            row_variable="group",
            row_label="집단",
            column_variable="event",
            column_label="사건",
            row_labels=("A", "B"),
            column_labels=("예", "아니오"),
            n_total=6,
            n_obs=6,
            n_missing_row=0,
            n_missing_column=0,
            n_excluded=0,
            cells=(
                (
                    CrosstabCell(
                        row_value="A",
                        row_label="A",
                        column_value="yes",
                        column_label="예",
                        count=2,
                        row_percent=66.6667,
                        column_percent=66.6667,
                        total_percent=33.3333,
                        expected_count=1.5,
                    ),
                ),
            ),
            test=test,
        ),
        warnings_ko=("기대빈도가 낮아 Fisher 정확검정을 함께 제시했다.",),
    )

    reporting = _reporting_module()
    prose = reporting.prose_for_frequency_crosstab(result)
    rows = reporting.table_for_frequency_crosstab(result)
    summary = reporting.test_summary_for_frequency_crosstab(result)

    assert "집단과 사건의 교차표" in prose
    assert "영향" not in prose
    assert "유발" not in prose
    assert rows[0]["row"] == "A"
    assert rows[0]["column"] == "예"
    assert rows[0]["count"] == "2"
    assert rows[0]["row_percent"] == "66.7"
    assert summary["selected_method"] == "Fisher 정확검정"
    assert summary["selected_p"] == "0.486"
    assert summary["cramers_v"] == "0.447"
