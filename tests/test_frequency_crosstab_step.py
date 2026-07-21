from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.frequency_crosstab")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.frequency_crosstab":
            pytest.fail("modori.steps.frequency_crosstab is not implemented")
        raise
    return module.FrequencyCrosstabStep


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    value_labels: Mapping[str, Mapping[object, str]] | None = None,
    missing_values: Mapping[str, list[object]] | None = None,
) -> Dataset:
    frame = pd.DataFrame(rows)
    labels = labels or {}
    value_labels = value_labels or {}
    missing_values = missing_values or {}
    variables: dict[str, Variable] = {}
    for column in frame.columns:
        raw_measure = measures[column]
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure(raw_measure)
        variables[column] = Variable(
            name=column,
            label=labels.get(column),
            measure=measure,
            value_labels=dict(value_labels.get(column, {})),
            missing_values=list(missing_values.get(column, [])),
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="freq_xtab",
        title="빈도 및 교차분석",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def test_frequency_summary_uses_non_missing_denominator_and_metadata_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"gender": "F", "satisfaction": "low"},
            {"gender": "M", "satisfaction": "high"},
            {"gender": "F", "satisfaction": "medium"},
            {"gender": None, "satisfaction": "low"},
            {"gender": "X", "satisfaction": None},
        ],
        measures={"gender": "nominal", "satisfaction": "ordinal"},
        labels={"gender": "성별", "satisfaction": "만족도"},
        value_labels={
            "gender": {"M": "남성", "F": "여성"},
            "satisfaction": {
                "low": "낮음",
                "medium": "보통",
                "high": "높음",
            },
        },
    )

    result = run_step(
        dataset,
        {"schema_version": 1, "mode": "frequency", "variables": ["gender"]},
    )

    table = result.frequency_tables[0]
    assert result.analysis_key == "frequency_crosstab"
    assert result.mode == "frequency"
    assert table.key == "gender"
    assert table.label == "성별"
    assert table.measure == "nominal"
    assert table.n_total == 5
    assert table.n_obs == 4
    assert table.n_missing == 1
    assert [
        (row.value, row.label, row.count, row.percent)
        for row in table.categories
    ] == [
        ("M", "남성", 1, pytest.approx(25.0)),
        ("F", "여성", 2, pytest.approx(50.0)),
        ("X", "X", 1, pytest.approx(25.0)),
    ]


def test_frequency_orders_unlabelled_categories_by_normalized_lexical_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"segment": "z"},
            {"segment": "A"},
            {"segment": "m"},
            {"segment": "a"},
        ],
        measures={"segment": "nominal"},
        value_labels={"segment": {"m": "엠"}},
    )

    result = run_step(
        dataset,
        {"schema_version": 1, "mode": "frequency", "variables": ["segment"]},
    )

    assert [row.value for row in result.frequency_tables[0].categories] == [
        "m",
        "A",
        "a",
        "z",
    ]


def test_crosstab_counts_percentages_chi_square_and_cramers_v_match_scipy() -> None:
    rows = [
        {"treatment": "A", "outcome": "yes"},
        {"treatment": "A", "outcome": "yes"},
        {"treatment": "A", "outcome": "no"},
        {"treatment": "B", "outcome": "yes"},
        {"treatment": "B", "outcome": "no"},
        {"treatment": "B", "outcome": "no"},
        {"treatment": "B", "outcome": None},
        {"treatment": None, "outcome": "yes"},
    ]
    dataset = dataset_factory(
        rows=rows,
        measures={"treatment": "nominal", "outcome": "nominal"},
        labels={"treatment": "처치군", "outcome": "결과"},
        value_labels={
            "treatment": {"A": "A군", "B": "B군"},
            "outcome": {"yes": "예", "no": "아니오"},
        },
    )

    result = run_step(
        dataset,
        {
            "schema_version": 1,
            "mode": "crosstab",
            "row_variable": "treatment",
            "column_variable": "outcome",
        },
    )

    table = result.crosstab
    assert table is not None
    assert table.row_variable == "treatment"
    assert table.column_variable == "outcome"
    assert table.row_labels == ("A군", "B군")
    assert table.column_labels == ("예", "아니오")
    assert table.n_total == 8
    assert table.n_obs == 6
    assert table.n_missing_row == 1
    assert table.n_missing_column == 1
    assert table.n_excluded == 2
    assert [[cell.count for cell in row] for row in table.cells] == [[2, 1], [1, 2]]
    assert table.cells[0][0].row_percent == pytest.approx(66.6666667)
    assert table.cells[0][0].column_percent == pytest.approx(66.6666667)
    assert table.cells[0][0].total_percent == pytest.approx(33.3333333)

    expected_counts = [[2, 1], [1, 2]]
    chi2, p_value, df, expected = stats.chi2_contingency(
        expected_counts,
        correction=False,
    )
    assert table.test.pearson_chi_square == pytest.approx(chi2)
    assert table.test.df == df
    assert table.test.pearson_p_value == pytest.approx(p_value)
    assert table.test.expected_counts == tuple(
        tuple(float(v) for v in row) for row in expected
    )
    assert table.test.cramers_v == pytest.approx((chi2 / 6) ** 0.5)


def test_weak_2x2_expected_cells_route_to_fisher_exact_when_available() -> None:
    dataset = dataset_factory(
        rows=[
            *([{"group": "A", "event": "yes"}] * 8),
            {"group": "A", "event": "no"},
            {"group": "B", "event": "yes"},
            {"group": "B", "event": "no"},
        ],
        measures={"group": "nominal", "event": "nominal"},
        value_labels={"event": {"yes": "예", "no": "아니오"}},
    )

    result = run_step(
        dataset,
        {
            "schema_version": 1,
            "mode": "crosstab",
            "row_variable": "group",
            "column_variable": "event",
        },
    )

    table = result.crosstab
    assert table is not None
    odds_ratio, p_value = stats.fisher_exact([[8, 1], [1, 1]])
    assert table.test.expected_cell_warning is True
    assert table.test.selected_method == "fisher_exact"
    assert table.test.selected_p_value == pytest.approx(p_value)
    assert table.test.fisher_odds_ratio == pytest.approx(odds_ratio)
    assert any("Fisher" in warning for warning in result.warnings_ko)


def test_larger_weak_expected_table_fails_closed_for_exact_test() -> None:
    dataset = dataset_factory(
        rows=[
            {"grade": "low", "region": "north"},
            {"grade": "low", "region": "south"},
            {"grade": "medium", "region": "north"},
            {"grade": "high", "region": "east"},
        ],
        measures={"grade": "ordinal", "region": "nominal"},
        value_labels={"grade": {"low": "하", "medium": "중", "high": "상"}},
    )

    result = run_step(
        dataset,
        {
            "schema_version": 1,
            "mode": "crosstab",
            "row_variable": "grade",
            "column_variable": "region",
        },
    )

    table = result.crosstab
    assert table is not None
    assert table.test.expected_cell_warning is True
    assert table.test.selected_method == "unsupported_exact"
    assert table.test.selected_p_value is None
    assert any("지원하지 않습니다" in warning for warning in result.warnings_ko)


def test_schema_contract_rejects_missing_newer_and_unknown_params() -> None:
    step_cls = _step_cls()
    with pytest.raises(ValueError, match="require schema_version"):
        step_cls.migrate_params({"mode": "frequency", "variables": ["gender"]})
    with pytest.raises(ValueError, match="newer schema_version"):
        step_cls.migrate_params({"schema_version": 999, "mode": "frequency"})
    with pytest.raises(ValueError, match="unknown frequency_crosstab params"):
        step_cls.validate_params(
            {
                "schema_version": 1,
                "mode": "frequency",
                "variables": ["gender"],
                "extra": True,
            }
        )


def test_validation_rejects_scale_variables_and_duplicate_crosstab_roles() -> None:
    dataset = dataset_factory(
        rows=[{"age": 20, "gender": "F"}, {"age": 30, "gender": "M"}],
        measures={"age": "scale", "gender": "nominal"},
    )

    with pytest.raises(ValueError, match="명목 또는 서열"):
        run_step(
            dataset,
            {"schema_version": 1, "mode": "frequency", "variables": ["age"]},
        )
    with pytest.raises(ValueError, match="서로 다른"):
        run_step(
            dataset,
            {
                "schema_version": 1,
                "mode": "crosstab",
                "row_variable": "gender",
                "column_variable": "gender",
            },
        )
