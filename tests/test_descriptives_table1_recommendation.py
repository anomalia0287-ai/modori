from __future__ import annotations

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.descriptives_table1_recommendation import eligibility_provider
from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationService


def _variable(name: str, measure: Measure, dtype: str = "object") -> Variable:
    return Variable(
        name=name,
        label=None,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype=dtype,
        origin_step_id="import",
    )


def _dataset(
    rows: list[dict[str, object]],
    *,
    measures: dict[str, str | Measure],
) -> Dataset:
    frame = pd.DataFrame(rows)
    variables = {
        column: _variable(
            column,
            measure if isinstance(measure, Measure) else Measure(measure),
            str(frame[column].dtype),
        )
        for column, measure in measures.items()
    }
    return Dataset(df=frame, variables=variables)


def test_provider_recommends_descriptives_for_imported_dataset_with_usable_variable():
    dataset = _dataset(
        rows=[{"age": 20}, {"age": 30}],
        measures={"age": "scale"},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "descriptives"
    assert candidate.variable_keys == ["age"]
    assert candidate.group_key == ""
    assert candidate.routing_tier is RecommendationRoutingTier.PRIMARY


def test_provider_returns_no_candidate_when_active_analysis_is_present():
    dataset = _dataset(rows=[{"age": 20}], measures={"age": "scale"})

    assert eligibility_provider().candidates(dataset, active_analysis=True) == []


@pytest.mark.parametrize(
    "column",
    ["id", "rowid", "row_id", "rownames", "row_names", "index", "Unnamed: 0"],
)
def test_provider_excludes_id_like_columns(column):
    dataset = _dataset(
        rows=[{column: 1001}, {column: 1002}],
        measures={column: "scale"},
    )

    assert eligibility_provider().candidates(dataset) == []


def test_provider_excludes_columns_with_less_than_half_non_missing_values():
    dataset = _dataset(
        rows=[
            {"score": 5},
            {"score": None},
            {"score": None},
            {"score": None},
        ],
        measures={"score": "scale"},
    )

    assert eligibility_provider().candidates(dataset) == []


def test_provider_excludes_constant_columns():
    dataset = _dataset(
        rows=[{"score": 3}, {"score": 3}, {"score": 3}],
        measures={"score": "scale"},
    )

    assert eligibility_provider().candidates(dataset) == []


def test_provider_excludes_dominant_value_columns_at_ninety_five_percent():
    rows = [{"score": 1} for _ in range(95)] + [{"score": 2} for _ in range(5)]
    dataset = _dataset(rows=rows, measures={"score": "scale"})

    assert eligibility_provider().candidates(dataset) == []


def test_provider_uses_plausible_group_without_treatment_language():
    dataset = _dataset(
        rows=[{"group": "A", "age": 20}, {"group": "B", "age": 30}],
        measures={"group": "nominal", "age": "scale"},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.group_key == "group"
    assert candidate.variable_keys == ["age"]
    assert "처치" not in candidate.reason_ko
    assert "통제" not in candidate.reason_ko


def test_provider_does_not_group_by_arbitrary_ordinal_survey_item():
    dataset = _dataset(
        rows=[
            {"A1": 1, "A2": 2, "A3": 3},
            {"A1": 2, "A2": 3, "A3": 4},
            {"A1": 3, "A2": 4, "A3": 5},
        ],
        measures={"A1": "ordinal", "A2": "ordinal", "A3": "ordinal"},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.group_key == ""
    assert candidate.variable_keys == ["A1", "A2", "A3"]


def test_provider_limits_default_variables_after_excluding_group():
    rows = [
        {"group": "A", **{f"v{index:02d}": index for index in range(25)}},
        {"group": "B", **{f"v{index:02d}": index + 1 for index in range(25)}},
    ]
    dataset = _dataset(
        rows=rows,
        measures={"group": "nominal"}
        | {f"v{index:02d}": "scale" for index in range(25)},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.group_key == "group"
    assert candidate.variable_keys == [f"v{index:02d}" for index in range(20)]


def test_provider_ignores_nominal_group_with_more_than_twelve_values():
    rows = [{"group": f"G{index}", "age": index} for index in range(13)]
    dataset = _dataset(
        rows=rows,
        measures={"group": "nominal", "age": "scale"},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.group_key == ""
    assert candidate.variable_keys == ["group", "age"]


def test_recommendation_service_includes_descriptives_without_removing_legacy_candidates():
    dataset = _dataset(
        rows=[
            {"stress_1": 1, "stress_2": 2, "stress_3": 3, "age": 20},
            {"stress_1": 2, "stress_2": 3, "stress_3": 4, "age": 30},
        ],
        measures={
            "stress_1": "scale",
            "stress_2": "scale",
            "stress_3": "scale",
            "age": "scale",
        },
    )

    result = RecommendationService().recommend(dataset)
    kinds = [candidate.kind for candidate in result.candidates]

    assert "descriptives" in kinds
    assert "reliability" in kinds
