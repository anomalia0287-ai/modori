from __future__ import annotations

import importlib
from collections.abc import Mapping

import pandas as pd
import pytest
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Variable


def _step_cls() -> type:
    try:
        module = importlib.import_module("modori.steps.kruskal_wallis")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.steps.kruskal_wallis":
            pytest.fail("modori.steps.kruskal_wallis is not implemented")
        raise
    return module.KruskalWallisStep


def _params(
    dependent: str = "score",
    group: str = "arm",
    *,
    posthoc_method: str = "none",
    p_adjust: str = "none",
    include_group_mean_sd: bool = True,
    language: str = "ko",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "dependent": dependent,
        "group": group,
        "posthoc_method": posthoc_method,
        "p_adjust": p_adjust,
        "include_group_mean_sd": include_group_mean_sd,
        "language": language,
    }


def dataset_factory(
    *,
    rows: list[dict[str, object]],
    measures: Mapping[str, str | Measure],
    labels: Mapping[str, str] | None = None,
    value_labels: Mapping[str, Mapping[object, str]] | None = None,
    missing_values: Mapping[str, list[float]] | None = None,
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
        id="kw-main",
        title="Kruskal-Wallis 검정",
        params=dict(params),
    )
    return step.compute(PipelineContext(dataset=dataset, analyses={})).analysis


def test_current_schema_rejects_missing_unknown_and_newer_params() -> None:
    with pytest.raises(ValueError, match="require schema_version"):
        _step_cls().migrate_params({"dependent": "score", "group": "arm"})

    with pytest.raises(ValueError, match="unknown kruskal_wallis params"):
        _step_cls().validate_params({**_params(), "extra": "bad"})

    with pytest.raises(ValueError, match="newer schema_version"):
        _step_cls().migrate_params(
            {"schema_version": 999, "dependent": "score", "group": "arm"}
        )


def test_reads_include_dependent_and_group_and_writes_analysis_key() -> None:
    step = _step_cls()(
        id="kw-main",
        title="Kruskal-Wallis 검정",
        params=_params(dependent="satisfaction", group="cohort"),
    )

    assert step.reads() == {"satisfaction", "cohort"}
    assert step.writes() == {"kw-main"}


def test_kruskal_wallis_matches_scipy_and_reports_group_summaries() -> None:
    dataset = dataset_factory(
        rows=[
            {"arm": "B", "score": 8.0},
            {"arm": "A", "score": 1.0},
            {"arm": "C", "score": 9.0},
            {"arm": "B", "score": 7.0},
            {"arm": "A", "score": 2.0},
            {"arm": "C", "score": 10.0},
            {"arm": "B", "score": None},
            {"arm": "A", "score": 3.0},
            {"arm": "C", "score": 11.0},
            {"arm": None, "score": 12.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
        labels={"arm": "처치군", "score": "점수"},
        value_labels={"arm": {"C": "세 번째", "A": "첫 번째"}},
    )

    result = run_step(dataset, _params())
    reference = stats.kruskal([9.0, 10.0, 11.0], [1.0, 2.0, 3.0], [8.0, 7.0])

    assert result.analysis_key == "kruskal_wallis"
    assert result.dependent == "score"
    assert result.dependent_label == "점수"
    assert result.group == "arm"
    assert result.group_label == "처치군"
    assert result.n_total == 10
    assert result.n_used == 8
    assert result.n_excluded == 2
    assert result.statistic_label == "H"
    assert result.statistic == pytest.approx(reference.statistic, abs=1e-12)
    assert result.degrees_of_freedom == 2
    assert result.p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert result.effect_size_label == "epsilon_squared"
    assert result.effect_size == pytest.approx((reference.statistic - 3 + 1) / (8 - 3))
    assert result.chart_spec is None
    assert result.no_canonical_chart_reason_ko
    assert result.posthoc is None
    assert any("사후검정" in warning for warning in result.warnings_ko)
    assert [(row.group_value, row.group_label, row.n) for row in result.groups] == [
        ("C", "세 번째", 3),
        ("A", "첫 번째", 3),
        ("B", "B", 2),
    ]
    assert [row.median for row in result.groups] == [
        pytest.approx(10.0),
        pytest.approx(2.0),
        pytest.approx(7.5),
    ]
    assert [row.mean_rank for row in result.groups] == [
        pytest.approx(7.0),
        pytest.approx(2.0),
        pytest.approx(4.5),
    ]
    assert result.groups[0].mean == pytest.approx(10.0)
    assert result.groups[0].sd == pytest.approx(1.0)


def test_kruskal_wallis_records_tied_rank_policy() -> None:
    dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1},
            {"arm": "A", "score": 1},
            {"arm": "A", "score": 2},
            {"arm": "A", "score": 2},
            {"arm": "B", "score": 2},
            {"arm": "B", "score": 3},
            {"arm": "B", "score": 3},
            {"arm": "B", "score": 3},
            {"arm": "C", "score": 4},
            {"arm": "C", "score": 4},
            {"arm": "C", "score": 5},
            {"arm": "C", "score": 5},
        ],
        measures={"arm": "nominal", "score": "ordinal"},
    )

    result = run_step(dataset, _params())
    reference = stats.kruskal(
        [1, 1, 2, 2],
        [2, 3, 3, 3],
        [4, 4, 5, 5],
    )

    assert result.statistic == pytest.approx(reference.statistic, abs=1e-12)
    assert result.p_value == pytest.approx(reference.pvalue, abs=1e-12)
    assert result.method_details == {
        "method": "chi_square_approximation",
        "ties_present": True,
        "tie_correction": "scipy_kruskal",
        "groups": 3,
    }


def test_ordinal_dependent_and_group_are_supported_with_missing_value_codes() -> None:
    dataset = dataset_factory(
        rows=[
            {"group": 1, "rating": 1},
            {"group": 1, "rating": 2},
            {"group": 2, "rating": 3},
            {"group": 2, "rating": 4},
            {"group": 3, "rating": 5},
            {"group": 3, "rating": 6},
            {"group": 3, "rating": 99},
        ],
        measures={"group": "ordinal", "rating": "ordinal"},
        value_labels={"group": {2: "중간", 1: "낮음", 3: "높음"}},
        missing_values={"rating": [99]},
    )

    result = run_step(dataset, _params(dependent="rating", group="group"))

    assert result.n_total == 7
    assert result.n_used == 6
    assert result.n_excluded == 1
    assert [row.group_label for row in result.groups] == ["중간", "낮음", "높음"]


@pytest.mark.parametrize(
    "params, message",
    [
        ({**_params(), "dependent": "arm"}, "종속 변수"),
        ({**_params(), "group": "score"}, "그룹 변수"),
        ({**_params(), "dependent": "score", "group": "score"}, "서로 달라야"),
        ({**_params(posthoc_method="dunn")}, "사후검정"),
        ({**_params(p_adjust="holm")}, "p_adjust"),
        ({**_params(include_group_mean_sd="yes")}, "include_group_mean_sd"),
        ({**_params(language="ja")}, "language"),
    ],
)
def test_validation_rejects_invalid_params_and_measures(
    params: dict[str, object],
    message: str,
) -> None:
    dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "B", "score": 2.0},
            {"arm": "C", "score": 3.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )

    with pytest.raises(ValueError, match=message):
        run_step(dataset, params)


def test_requires_at_least_three_nonempty_groups_and_two_values_per_group() -> None:
    two_group_dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "A", "score": 2.0},
            {"arm": "B", "score": 3.0},
            {"arm": "B", "score": 4.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )
    with pytest.raises(ValueError, match="3개 이상"):
        run_step(two_group_dataset, _params())

    sparse_dataset = dataset_factory(
        rows=[
            {"arm": "A", "score": 1.0},
            {"arm": "B", "score": 2.0},
            {"arm": "B", "score": 3.0},
            {"arm": "C", "score": 4.0},
            {"arm": "C", "score": 5.0},
        ],
        measures={"arm": "nominal", "score": "scale"},
    )
    with pytest.raises(ValueError, match="각 그룹"):
        run_step(sparse_dataset, _params())
