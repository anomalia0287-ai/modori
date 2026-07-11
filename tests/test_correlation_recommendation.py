from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.correlation_recommendation import eligibility_provider
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


def test_provider_recommends_correlation_for_numeric_scale_or_ordinal_variables() -> None:
    dataset = _dataset(
        rows=[
            {"stress": 1, "sleep": 5.0, "group": "A"},
            {"stress": 2, "sleep": 4.0, "group": "B"},
            {"stress": 3, "sleep": 3.0, "group": "A"},
        ],
        measures={
            "stress": Measure.ORDINAL,
            "sleep": Measure.SCALE,
            "group": Measure.NOMINAL,
        },
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "correlation"
    assert candidate.routing_tier is RecommendationRoutingTier.SECONDARY
    assert candidate.variable_keys == ["stress", "sleep"]
    assert "인과" not in candidate.reason_ko


def test_recommendation_service_exposes_correlation_candidate_without_stealing_default() -> None:
    dataset = _dataset(
        rows=[
            {"stress": 1, "sleep": 5.0},
            {"stress": 2, "sleep": 4.0},
            {"stress": 3, "sleep": 3.0},
        ],
        measures={"stress": Measure.ORDINAL, "sleep": Measure.SCALE},
    )

    state = RecommendationService().recommend(dataset)

    assert any(candidate.kind == "correlation" for candidate in state.candidates)
    assert state.candidates[0].kind == "descriptives"
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
