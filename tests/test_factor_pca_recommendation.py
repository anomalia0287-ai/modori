from __future__ import annotations

import importlib

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Variable
from modori.recommendation_policy import RecommendationRoutingTier


def _provider():
    try:
        module = importlib.import_module("modori.factor_pca_recommendation")
    except ModuleNotFoundError as exc:
        if exc.name == "modori.factor_pca_recommendation":
            pytest.fail("modori.factor_pca_recommendation is not implemented")
        raise
    return module.eligibility_provider()


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


def test_provider_suggests_candidate_for_three_numeric_scale_or_ordinal_items() -> None:
    dataset = _dataset(
        rows=[
            {"q1": 1, "q2": 2.0, "q3": 2, "group": "A"},
            {"q1": 2, "q2": 2.5, "q3": 3, "group": "B"},
            {"q1": 3, "q2": 3.5, "q3": 4, "group": "A"},
            {"q1": 4, "q2": 4.0, "q3": 5, "group": "B"},
        ],
        measures={
            "q1": Measure.ORDINAL,
            "q2": Measure.SCALE,
            "q3": Measure.ORDINAL,
            "group": Measure.NOMINAL,
        },
    )

    candidate = _provider().candidates(dataset)[0]

    assert candidate.kind == "factor_pca"
    assert candidate.routing_tier is RecommendationRoutingTier.SECONDARY
    assert candidate.variable_keys == ["q1", "q2", "q3"]
    assert "3개" in candidate.reason_ko
    assert "확정" not in candidate.reason_ko
    assert "입증" not in candidate.reason_ko


def test_provider_returns_no_candidate_when_active_or_too_few_usable_items() -> None:
    dataset = _dataset(
        rows=[
            {"q1": 1, "q2": 1, "q3": "low"},
            {"q1": 1, "q2": 2, "q3": "mid"},
            {"q1": 1, "q2": 3, "q3": "high"},
        ],
        measures={
            "q1": Measure.ORDINAL,
            "q2": Measure.SCALE,
            "q3": Measure.ORDINAL,
        },
    )

    provider = _provider()

    assert provider.candidates(dataset, active_analysis=True) == []
    assert provider.candidates(dataset) == []
