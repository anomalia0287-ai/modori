from __future__ import annotations

from modori.descriptives_table1_results import (
    DescriptiveCategoryRow,
    DescriptiveGroupSummary,
    DescriptiveVariableSummary,
    DescriptivesTableResult,
)
from modori.steps.reporting import prose_for, table_for


def test_descriptives_reporting_formats_scale_and_category_rows() -> None:
    result = DescriptivesTableResult(
        analysis_key="descriptives_table1",
        title_ko="기술통계 표 1",
        variables=("age", "gender"),
        group=None,
        n_total=4,
        summaries=(
            DescriptiveVariableSummary(
                key="age",
                label="Age",
                measure="scale",
                n_obs=3,
                n_missing=1,
                mean=24.0,
                sd=4.0,
                median=24.0,
                minimum=20.0,
                maximum=28.0,
            ),
            DescriptiveVariableSummary(
                key="gender",
                label="Gender",
                measure="nominal",
                n_obs=3,
                n_missing=1,
                categories=(
                    DescriptiveCategoryRow(
                        value="F",
                        label="여성",
                        count=2,
                        percent=66.6667,
                    ),
                ),
            ),
        ),
    )

    rows = table_for(result)

    assert prose_for(result, language="ko")
    assert prose_for(result, language="en")
    assert rows[0]["variable"] == "Age"
    assert rows[0]["mean"] == "24.00"
    assert rows[1]["category"] == "여성"
    assert rows[1]["percent"] == "66.7"


def test_descriptives_reporting_formats_grouped_rows_without_causal_language() -> None:
    result = DescriptivesTableResult(
        analysis_key="descriptives_table1",
        title_ko="기술통계 표 1",
        variables=("age",),
        group="gender",
        n_total=2,
        summaries=(),
        grouped_summaries=(
            DescriptiveGroupSummary(
                group_value="F",
                group_label="여성",
                n_total=1,
                variables=(
                    DescriptiveVariableSummary(
                        key="age",
                        label="Age",
                        measure="scale",
                        n_obs=1,
                        n_missing=0,
                        mean=20.0,
                        sd=None,
                        median=20.0,
                        minimum=20.0,
                        maximum=20.0,
                    ),
                ),
            ),
        ),
    )

    prose = prose_for(result, language="ko")
    rows = table_for(result)

    assert "처치" not in prose
    assert "통제" not in prose
    assert rows[0]["group"] == "여성"
    assert rows[0]["group_n"] == "1"
    assert rows[0]["SD"] == ""
