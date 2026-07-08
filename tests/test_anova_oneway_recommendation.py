from __future__ import annotations

import pandas as pd

from modori.anova_oneway_recommendation import eligibility_provider
from modori.core import Dataset, Measure, Variable
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


def test_provider_recommends_one_way_anova_for_scale_dv_and_three_groups() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "score": 1.0},
            {"group": "A", "score": 2.0},
            {"group": "A", "score": 3.0},
            {"group": "B", "score": 4.0},
            {"group": "B", "score": 5.0},
            {"group": "B", "score": 6.0},
            {"group": "C", "score": 7.0},
            {"group": "C", "score": 8.0},
            {"group": "C", "score": 9.0},
        ],
        measures={"group": Measure.NOMINAL, "score": Measure.SCALE},
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "anova_oneway"
    assert candidate.level == "가능한 후보"
    assert candidate.outcome_key == "score"
    assert candidate.group_key == "group"
    assert "영향" not in candidate.reason_ko


def test_recommendation_service_exposes_anova_candidate_without_stealing_default() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "score": 1.0},
            {"group": "A", "score": 2.0},
            {"group": "A", "score": 3.0},
            {"group": "B", "score": 4.0},
            {"group": "B", "score": 5.0},
            {"group": "B", "score": 6.0},
            {"group": "C", "score": 7.0},
            {"group": "C", "score": 8.0},
            {"group": "C", "score": 9.0},
        ],
        measures={"group": Measure.NOMINAL, "score": Measure.SCALE},
    )

    state = RecommendationService().recommend(dataset)

    assert any(candidate.kind == "anova_oneway" for candidate in state.candidates)
    assert state.default_candidate is not None
    assert state.default_candidate.kind == "descriptives"
