from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest

from modori.analysis_catalog import (
    AnalysisStatus,
    get_module_spec,
)
from modori.core import Dataset, Measure, PipelineContext, Variable
from modori.recommendation_policy import (
    RecommendationEvidenceStatus,
    RecommendationRoutingPolicy,
)


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.descriptives_table1")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.descriptives_table1":
            pytest.fail("modori.steps.descriptives_table1 is not implemented")
        raise
    return module.DescriptivesTableStep


def _table_params(
    variables: list[str],
    *,
    group: str | None = None,
    include_missing_counts: bool = True,
    language: str = "ko",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "variables": variables,
        "group": group,
        "include_missing_counts": include_missing_counts,
        "language": language,
    }


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    value_labels: Mapping[str, Mapping[object, str]] | None = None,
) -> Dataset:
    frame = pd.DataFrame(rows)
    labels = labels or {}
    value_labels = value_labels or {}
    variables: dict[str, Variable] = {}
    for column in frame.columns:
        raw_measure = measures[column]
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure(raw_measure)
        variables[column] = Variable(
            name=column,
            label=labels.get(column),
            measure=measure,
            value_labels=dict(value_labels.get(column, {})),
            missing_values=[],
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="table1",
        title="기술통계 표 1",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def test_module_spec_registers_executable_strong_contract() -> None:
    spec = get_module_spec("descriptives_table1")

    assert spec is not None
    assert spec.status is AnalysisStatus.EXECUTABLE
    assert spec.step_type == "stats.descriptives_table1"
    assert (
        spec.result_type
        == "modori.descriptives_table1_results.DescriptivesTableResult"
    )
    assert spec.recommendation_policy is RecommendationRoutingPolicy.PRIMARY_REVIEW
    assert (
        spec.recommendation_evidence_status
        is RecommendationEvidenceStatus.EXPERIMENTAL
    )
    assert "tests/test_descriptives_table1_step.py" in spec.contract_tests


def test_current_schema_rejects_missing_schema_version() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"variables": ["age"]})


def test_current_schema_rejects_unknown_params_after_migration() -> None:
    params = {
        **_table_params(["age"]),
        "extra": "bad",
    }
    with pytest.raises(ValueError, match="unknown descriptives_table1 params"):
        _step_cls().validate_params(params)


def test_newer_schema_version_is_rejected_explicitly() -> None:
    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "variables": ["age"]})


def test_reads_include_variables_and_group_and_writes_analysis_key() -> None:
    step = _step_cls()(
        id="table1",
        title="기술통계 표 1",
        params=_table_params(["gender", "age"], group="group"),
    )

    assert step.reads() == {"gender", "age", "group"}
    assert step.writes() == {"table1"}


def test_scale_summary_matches_pandas_sample_sd() -> None:
    dataset = dataset_factory(
        rows=[{"age": 20}, {"age": 24}, {"age": None}, {"age": 28}],
        measures={"age": "scale"},
        labels={"age": "Age"},
    )
    result = run_step(dataset, _table_params(["age"]))

    summary = result.summaries[0]
    assert summary.key == "age"
    assert summary.label == "Age"
    assert summary.measure == "scale"
    assert summary.n_obs == 3
    assert summary.n_missing == 1
    assert summary.mean == pytest.approx(24.0)
    assert summary.sd == pytest.approx(pd.Series([20, 24, 28]).std(ddof=1))
    assert summary.median == pytest.approx(24.0)
    assert summary.minimum == pytest.approx(20.0)
    assert summary.maximum == pytest.approx(28.0)
    assert summary.categories == ()


def test_scale_summary_reuses_decimal_conversion_for_mean_and_sd(monkeypatch) -> None:
    module = importlib.import_module("modori.steps.descriptives_table1")
    original = module._decimal_values
    calls = 0

    def counting_decimal_values(values, key):
        nonlocal calls
        calls += 1
        return original(values, key)

    monkeypatch.setattr(module, "_decimal_values", counting_decimal_values)
    dataset = dataset_factory(
        rows=[{"score": "10000000.2"}, {"score": "10000000.1"}, {"score": "10000000.3"}],
        measures={"score": "scale"},
    )

    result = run_step(dataset, _table_params(["score"]))

    assert result.summaries[0].sd == pytest.approx(0.1, rel=1e-12, abs=1e-12)
    assert calls == 1


def test_scale_summary_rejects_boolean_values_explicitly() -> None:
    dataset = dataset_factory(
        rows=[{"flag": True}, {"flag": False}],
        measures={"flag": "scale"},
    )

    with pytest.raises(ValueError, match="boolean"):
        run_step(dataset, _table_params(["flag"]))


def test_scale_summary_sd_is_none_for_single_observation() -> None:
    dataset = dataset_factory(
        rows=[{"age": 20}, {"age": None}],
        measures={"age": "scale"},
    )
    result = run_step(dataset, _table_params(["age"]))

    assert result.summaries[0].n_obs == 1
    assert result.summaries[0].sd is None


def test_nominal_summary_uses_non_missing_denominator_and_label_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"gender": "F"},
            {"gender": "M"},
            {"gender": "F"},
            {"gender": None},
        ],
        measures={"gender": "nominal"},
        labels={"gender": "Gender"},
        value_labels={"gender": {"F": "여성", "M": "남성"}},
    )
    result = run_step(dataset, _table_params(["gender"]))

    summary = result.summaries[0]
    assert summary.n_obs == 3
    assert summary.n_missing == 1
    assert [
        (row.value, row.label, row.count, row.percent)
        for row in summary.categories
    ] == [
        ("F", "여성", 2, pytest.approx(66.6666667)),
        ("M", "남성", 1, pytest.approx(33.3333333)),
    ]


def test_nominal_summary_orders_labels_first_then_normalized_lexical() -> None:
    dataset = dataset_factory(
        rows=[
            {"category": "z"},
            {"category": "m"},
            {"category": "a"},
            {"category": "z"},
        ],
        measures={"category": "nominal"},
        value_labels={"category": {"m": "엠"}},
    )
    result = run_step(dataset, _table_params(["category"]))

    assert [row.value for row in result.summaries[0].categories] == ["m", "a", "z"]


def test_grouped_output_preserves_variable_order_and_group_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"group": "B", "age": 20, "gender": "F"},
            {"group": "A", "age": 30, "gender": "M"},
            {"group": "B", "age": 40, "gender": "F"},
        ],
        measures={"group": "nominal", "age": "scale", "gender": "nominal"},
        value_labels={"group": {"A": "A집단", "B": "B집단"}},
    )
    result = run_step(
        dataset,
        _table_params(["gender", "age"], group="group"),
    )

    assert [group.group_value for group in result.grouped_summaries] == ["A", "B"]
    assert [group.group_label for group in result.grouped_summaries] == [
        "A집단",
        "B집단",
    ]
    assert [
        [summary.key for summary in group.variables]
        for group in result.grouped_summaries
    ] == [["gender", "age"], ["gender", "age"]]


def test_validation_rejects_duplicate_variables_unknown_keys_and_empty_data() -> None:
    dataset = dataset_factory(
        rows=[{"age": 20}],
        measures={"age": "scale"},
    )

    with pytest.raises(ValueError, match="중복"):
        run_step(dataset, _table_params(["age", "age"]))
    with pytest.raises(ValueError, match="데이터셋에 없는 변수"):
        run_step(dataset, _table_params(["missing"]))

    empty_dataset = dataset_factory(rows=[], measures={})
    with pytest.raises(ValueError, match="비어"):
        run_step(empty_dataset, _table_params(["age"]))


def test_validation_rejects_scale_group_variable() -> None:
    dataset = dataset_factory(
        rows=[{"group": 1, "age": 20}, {"group": 2, "age": 30}],
        measures={"group": "scale", "age": "scale"},
    )

    with pytest.raises(ValueError, match="그룹 변수"):
        run_step(dataset, _table_params(["age"], group="group"))
