from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.correlation")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.correlation":
            pytest.fail("modori.steps.correlation is not implemented")
        raise
    return module.CorrelationStep


def _matrix_params(
    variables: list[str],
    *,
    method: str = "auto",
    missing_policy: str = "pairwise",
    p_adjust: str = "none",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "variables": variables,
        "method": method,
        "missing_policy": missing_policy,
        "p_adjust": p_adjust,
    }


def _pair_params(
    x: str,
    y: str,
    *,
    method: str = "auto",
    missing_policy: str = "pairwise",
    p_adjust: str = "none",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "pairs": [[x, y]],
        "method": method,
        "missing_policy": missing_policy,
        "p_adjust": p_adjust,
    }


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    missing_values: Mapping[str, list[float]] | None = None,
) -> Dataset:
    frame = pd.DataFrame(rows)
    labels = labels or {}
    missing_values = missing_values or {}
    variables: dict[str, Variable] = {}
    for column in frame.columns:
        raw_measure = measures[column]
        measure = raw_measure if isinstance(raw_measure, Measure) else Measure(raw_measure)
        variables[column] = Variable(
            name=column,
            label=labels.get(column),
            measure=measure,
            value_labels={},
            missing_values=list(missing_values.get(column, [])),
            dtype=str(frame[column].dtype),
            origin_step_id="import",
        )
    return Dataset(df=frame, variables=variables)


def run_step(dataset: Dataset, params: dict[str, object]):
    step = _step_cls()(
        id="corr-main",
        title="상관분석",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def test_current_schema_rejects_missing_schema_version_unknown_params_and_newer_schema() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"variables": ["x", "y"]})

    params = {**_pair_params("x", "y"), "extra": True}
    with pytest.raises(ValueError, match="unknown correlation params"):
        _step_cls().validate_params(params)

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params({"schema_version": 999, "variables": ["x", "y"]})


def test_pairwise_pearson_pair_matches_scipy_and_reports_missing_counts() -> None:
    dataset = dataset_factory(
        rows=[
            {"height": 150.0, "weight": 45.0},
            {"height": 160.0, "weight": 50.0},
            {"height": 170.0, "weight": 60.0},
            {"height": 180.0, "weight": None},
            {"height": None, "weight": 70.0},
            {"height": 190.0, "weight": 80.0},
        ],
        measures={"height": "scale", "weight": "scale"},
        labels={"height": "키", "weight": "몸무게"},
    )

    result = run_step(dataset, _pair_params("height", "weight", method="pearson"))
    pair = result.pairs[0]
    reference = stats.pearsonr([150.0, 160.0, 170.0, 190.0], [45.0, 50.0, 60.0, 80.0])

    assert result.analysis_key == "correlation"
    assert result.variables == ("height", "weight")
    assert result.method_policy == "pearson"
    assert result.missing_policy == "pairwise"
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko
    assert pair.x == "height"
    assert pair.y == "weight"
    assert pair.x_label == "키"
    assert pair.y_label == "몸무게"
    assert pair.method == "pearson"
    assert pair.statistic_label == "r"
    assert pair.coefficient == pytest.approx(reference.statistic, abs=1e-12)
    assert pair.p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert pair.n == 4
    assert pair.excluded_n == 2
    assert pair.warnings_ko == ()


def test_auto_matrix_uses_spearman_for_ordinal_pairs_and_preserves_param_order() -> None:
    dataset = dataset_factory(
        rows=[
            {"satisfaction": 1, "income": 30.0, "age": 20.0},
            {"satisfaction": 2, "income": 35.0, "age": 21.0},
            {"satisfaction": 3, "income": 40.0, "age": 23.0},
            {"satisfaction": 4, "income": 55.0, "age": 25.0},
            {"satisfaction": 5, "income": 65.0, "age": 28.0},
        ],
        measures={
            "satisfaction": "ordinal",
            "income": "scale",
            "age": "scale",
        },
    )

    result = run_step(
        dataset,
        _matrix_params(["satisfaction", "income", "age"], method="auto"),
    )

    assert [(pair.x, pair.y, pair.method) for pair in result.pairs] == [
        ("satisfaction", "income", "spearman"),
        ("satisfaction", "age", "spearman"),
        ("income", "age", "pearson"),
    ]
    reference = stats.spearmanr(
        [1, 2, 3, 4, 5],
        [30.0, 35.0, 40.0, 55.0, 65.0],
    )
    assert result.pairs[0].statistic_label == "rho"
    assert result.pairs[0].coefficient == pytest.approx(reference.statistic, abs=1e-12)
    assert result.pairs[0].p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert any("다중비교" in warning for warning in result.warnings_ko)
    assert all(pair.p_adjusted is None for pair in result.pairs)


def test_listwise_policy_uses_same_complete_case_set_for_all_matrix_pairs() -> None:
    dataset = dataset_factory(
        rows=[
            {"x": 1.0, "y": 2.0, "z": 10.0},
            {"x": 2.0, "y": None, "z": 11.0},
            {"x": 3.0, "y": 4.0, "z": 13.0},
            {"x": None, "y": 5.0, "z": 14.0},
            {"x": 5.0, "y": 8.0, "z": 20.0},
        ],
        measures={"x": "scale", "y": "scale", "z": "scale"},
    )

    result = run_step(
        dataset,
        _matrix_params(["x", "y", "z"], method="pearson", missing_policy="listwise"),
    )

    assert [(pair.n, pair.excluded_n) for pair in result.pairs] == [(3, 2), (3, 2), (3, 2)]
    reference = stats.pearsonr([1.0, 3.0, 5.0], [2.0, 4.0, 8.0])
    assert result.pairs[0].coefficient == pytest.approx(reference.statistic, abs=1e-12)


@pytest.mark.parametrize(
    "params, message",
    [
        ({"schema_version": 1, "variables": ["x"], "method": "auto"}, "at least two"),
        (_pair_params("x", "x"), "must differ"),
        ({**_pair_params("x", "y"), "variables": ["x", "y"]}, "exactly one"),
        (_pair_params("x", "y", method="kendall"), "method"),
        (_pair_params("x", "y", missing_policy="mean_impute"), "missing_policy"),
        (_pair_params("x", "y", p_adjust="bonferroni"), "p_adjust"),
    ],
)
def test_validation_rejects_invalid_params(params: dict[str, object], message: str) -> None:
    dataset = dataset_factory(
        rows=[{"x": 1.0, "y": 2.0}],
        measures={"x": "scale", "y": "scale"},
    )

    with pytest.raises(ValueError, match=message):
        run_step(dataset, params)


def test_validation_rejects_unsupported_variables_non_numeric_and_constant_inputs() -> None:
    nominal_dataset = dataset_factory(
        rows=[{"x": 1.0, "group": "A"}, {"x": 2.0, "group": "B"}, {"x": 3.0, "group": "A"}],
        measures={"x": "scale", "group": "nominal"},
    )
    with pytest.raises(ValueError, match="척도 또는 서열"):
        run_step(nominal_dataset, _pair_params("x", "group"))

    text_dataset = dataset_factory(
        rows=[{"x": "low", "y": 1.0}, {"x": "mid", "y": 2.0}, {"x": "high", "y": 3.0}],
        measures={"x": "ordinal", "y": "scale"},
    )
    with pytest.raises(ValueError, match="숫자"):
        run_step(text_dataset, _pair_params("x", "y", method="spearman"))

    constant_dataset = dataset_factory(
        rows=[{"x": 1.0, "y": 2.0}, {"x": 1.0, "y": 3.0}, {"x": 1.0, "y": 4.0}],
        measures={"x": "scale", "y": "scale"},
    )
    with pytest.raises(ValueError, match="분산"):
        run_step(constant_dataset, _pair_params("x", "y", method="pearson"))


def test_explicit_pearson_rejects_ordinal_pairs_fail_closed() -> None:
    dataset = dataset_factory(
        rows=[
            {"satisfaction": 1, "income": 30.0},
            {"satisfaction": 2, "income": 35.0},
            {"satisfaction": 3, "income": 40.0},
        ],
        measures={"satisfaction": "ordinal", "income": "scale"},
    )

    with pytest.raises(ValueError, match="Pearson"):
        run_step(dataset, _pair_params("satisfaction", "income", method="pearson"))
