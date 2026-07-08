from __future__ import annotations

import pandas as pd

from modori.ancova_recommendation import eligibility_provider
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


def test_provider_recommends_ancova_as_caution_candidate_with_covariate() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "outcome": 10.0, "pretest": 1.0},
            {"group": "A", "outcome": 11.0, "pretest": 2.0},
            {"group": "A", "outcome": 12.0, "pretest": 3.0},
            {"group": "B", "outcome": 14.0, "pretest": 1.0},
            {"group": "B", "outcome": 15.0, "pretest": 2.0},
            {"group": "B", "outcome": 16.0, "pretest": 3.0},
        ],
        measures={
            "group": Measure.NOMINAL,
            "outcome": Measure.SCALE,
            "pretest": Measure.SCALE,
        },
    )

    candidate = eligibility_provider().candidates(dataset)[0]

    assert candidate.kind == "ancova"
    assert candidate.level == "주의 필요"
    assert candidate.outcome_key == "outcome"
    assert candidate.group_key == "group"
    assert candidate.predictor_keys == ["pretest"]
    assert "연구 설계" in candidate.reason_ko


def test_recommendation_service_exposes_ancova_without_stealing_default() -> None:
    dataset = _dataset(
        rows=[
            {"group": "A", "outcome": 10.0, "pretest": 1.0},
            {"group": "A", "outcome": 11.0, "pretest": 2.0},
            {"group": "A", "outcome": 12.0, "pretest": 3.0},
            {"group": "B", "outcome": 14.0, "pretest": 1.0},
            {"group": "B", "outcome": 15.0, "pretest": 2.0},
            {"group": "B", "outcome": 16.0, "pretest": 3.0},
        ],
        measures={
            "group": Measure.NOMINAL,
            "outcome": Measure.SCALE,
            "pretest": Measure.SCALE,
        },
    )

    state = RecommendationService().recommend(dataset)

    assert any(candidate.kind == "ancova" for candidate in state.candidates)
    assert state.default_candidate is not None
    assert state.default_candidate.kind == "descriptives"
