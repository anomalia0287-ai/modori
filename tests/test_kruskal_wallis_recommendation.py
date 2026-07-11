from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.kruskal_wallis_recommendation import eligibility_provider
from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationService


def _variable(name: str, measure: Measure, dtype: str = "float64") -> Variable:
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


def test_provider_recommends_kruskal_wallis_for_ordinal_or_scale_dependent() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "rating": 1},
            {"group": "A", "rating": 2},
            {"group": "B", "rating": 3},
            {"group": "B", "rating": 4},
            {"group": "C", "rating": 5},
            {"group": "C", "rating": 6},
        ],
        measures={"group": Measure.NOMINAL, "rating": Measure.ORDINAL},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "kruskal_wallis"
    assert candidate.routing_tier is RecommendationRoutingTier.SECONDARY
    assert candidate.outcome_key == "rating"
    assert candidate.group_key == "group"
    assert "인과" not in candidate.reason_ko


def test_recommendation_service_exposes_kruskal_candidate_without_stealing_default() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "rating": 1},
            {"group": "A", "rating": 2},
            {"group": "B", "rating": 3},
            {"group": "B", "rating": 4},
            {"group": "C", "rating": 5},
            {"group": "C", "rating": 6},
        ],
        measures={"group": Measure.NOMINAL, "rating": Measure.ORDINAL},
    )

    state = RecommendationService().recommend(dataset)

    assert any(candidate.kind == "kruskal_wallis" for candidate in state.candidates)
    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
