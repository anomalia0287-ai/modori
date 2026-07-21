from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.frequency_crosstab_recommendation import eligibility_provider
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


def _dataset(rows: list[dict[str, object]], measures: dict[str, Measure]) -> Dataset:
    frame = pd.DataFrame(rows)
    return Dataset(
        df=frame,
        variables={
            column: _variable(column, measure, str(frame[column].dtype))
            for column, measure in measures.items()
        },
    )


def test_provider_recommends_frequency_for_categorical_variables() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "region": "north", "score": 1.0},
            {"group": "B", "region": "south", "score": 2.0},
            {"group": "A", "region": "south", "score": 3.0},
        ],
        measures={
            "group": Measure.NOMINAL,
            "region": Measure.NOMINAL,
            "score": Measure.SCALE,
        },
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "frequency_crosstab"
    assert candidate.routing_tier is RecommendationRoutingTier.SECONDARY
    assert candidate.variable_keys == ["group", "region"]
    assert "영향" not in candidate.reason_ko


def test_recommendation_service_exposes_frequency_candidate_without_stealing_default() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "score": 1.0},
            {"group": "B", "score": 2.0},
            {"group": "A", "score": 3.0},
        ],
        measures={"group": Measure.NOMINAL, "score": Measure.SCALE},
    )

    state = RecommendationService().recommend(dataset)

    assert any(candidate.kind == "frequency_crosstab" for candidate in state.candidates)
    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
