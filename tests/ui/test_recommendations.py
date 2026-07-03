from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.ui.recommendations import RecommendationService


def _variable(
    name: str,
    measure: Measure,
    dtype: str = "int64",
    missing_values: list[float] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=None,
        measure=measure,
        value_labels={},
        missing_values=[] if missing_values is None else missing_values,
        dtype=dtype,
        origin_step_id="import",
    )


def _dataset(frame: pd.DataFrame) -> Dataset:
    variables = {}
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            measure = Measure.SCALE
            dtype = "float64"
        else:
            measure = Measure.NOMINAL
            dtype = "object"
        variables[column] = _variable(column, measure, dtype)
    return Dataset(df=frame, variables=variables)


def test_recommendation_service_produces_item_group_candidates_for_bfi_columns() -> None:
    frame = pd.read_csv("tests/fixtures/psych_bfi.csv").head(60)

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is not None
    assert state.default_candidate.kind == "reliability"
    assert state.default_candidate.level == "강한 추천"
    assert state.default_candidate.item_keys == ["A1", "A2", "A3", "A4", "A5"]
    assert "같은 접두사" in state.default_candidate.reason_ko
    assert ["C1", "C2", "C3", "C4", "C5"] in [
        candidate.item_keys
        for candidate in state.candidates
        if candidate.kind == "reliability"
    ]
    assert ["E1", "E2", "E3", "E4", "E5"] in [
        candidate.item_keys
        for candidate in state.candidates
        if candidate.kind == "reliability"
    ]


def test_recommendation_service_masks_declared_missing_values_for_item_detection() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 5, 99],
            "A2": [2, 3, 4, 5, 1, 99],
            "A3": [3, 4, 5, 1, 2, 99],
        }
    )
    dataset = Dataset(
        df=frame,
        variables={
            column: _variable(
                column,
                Measure.SCALE,
                "float64",
                missing_values=[99.0],
            )
            for column in frame.columns
        },
    )

    state = RecommendationService().recommend(dataset)

    reliability = next(candidate for candidate in state.candidates if candidate.kind == "reliability")
    assert reliability.item_keys == ["A1", "A2", "A3"]
    assert reliability.level == "가능한 후보"


def test_recommendation_service_produces_two_group_comparison_candidate() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 2, 3, 4, 5],
            "A2": [1, 2, 3, 4, 2, 3, 4, 5],
            "A3": [1, 2, 3, 4, 2, 3, 4, 5],
            "gender": [1, 1, 1, 1, 2, 2, 2, 2],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    comparison = next(candidate for candidate in state.candidates if candidate.kind == "comparison")
    assert comparison.outcome_key == "A1"
    assert comparison.group_key == "gender"
    assert comparison.level in {"강한 추천", "가능한 후보"}
    assert "두 집단" in comparison.reason_ko


def test_recommendation_service_excludes_near_constant_group_columns() -> None:
    frame = pd.DataFrame(
        {
            "score": [index % 5 + 1 for index in range(100)],
            "gender": [1] * 98 + [2] * 2,
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(
        candidate.kind == "comparison" and candidate.group_key == "gender"
        for candidate in state.candidates
    )
    assert state.default_candidate is None
    assert state.message_ko == "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."


def test_recommendation_service_excludes_exactly_95_percent_near_constant_columns() -> None:
    frame = pd.DataFrame(
        {
            "score": [index % 5 + 1 for index in range(100)],
            "gender": [1] * 95 + [2] * 5,
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert not any(
        candidate.kind == "comparison" and candidate.group_key == "gender"
        for candidate in state.candidates
    )
    assert state.default_candidate is None
    assert state.message_ko == "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."


def test_recommendation_service_returns_no_default_without_safe_candidate() -> None:
    frame = pd.DataFrame(
        {
            "id": [1001, 1002, 1003, 1004],
            "constant": [1, 1, 1, 1],
            "mostly_missing": [None, None, None, 3],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is None
    assert state.candidates == []
    assert state.message_ko == "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."


def test_recommendation_service_explains_caution_only_state() -> None:
    frame = pd.DataFrame(
        {
            "score": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.candidates
    assert {candidate.level for candidate in state.candidates} == {"주의 필요"}
    assert state.default_candidate is None
    assert state.selected_candidate is None
    assert state.message_ko == "주의가 필요한 후보만 찾았습니다. 직접 확인한 뒤 선택해 주세요."


def test_caution_candidates_are_not_default_when_stronger_candidates_exist() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 5, 6],
            "A2": [1, 2, 3, 4, 5, 6],
            "A3": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is not None
    assert state.default_candidate.level != "주의 필요"
    assert any(candidate.level == "주의 필요" for candidate in state.candidates)
