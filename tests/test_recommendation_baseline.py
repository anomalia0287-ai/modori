from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from modori.recommendation_baseline import (
    candidate_identity,
    load_case_dataset,
    predict_current_baseline,
)
from modori.recommendations import RecommendationCandidate, RecommendationService


def test_load_case_dataset_uses_product_import_and_metadata_paths(tmp_path: Path) -> None:
    pilot_root = tmp_path / "pilot"
    data_path = pilot_root / "data" / "case.csv"
    data_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "arm": ["A", "A", "B", "B"],
            "score": [10.5, 12.0, 14.5, 15.0],
        }
    ).to_csv(data_path, index=False)
    case = {
        "case_id": "case-1",
        "evidence_stage": "cold_start",
        "data_file": "data/case.csv",
    }

    dataset = load_case_dataset(case, pilot_root)

    assert dataset.df.to_dict(orient="list") == {
        "arm": ["A", "A", "B", "B"],
        "score": [10.5, 12.0, 14.5, 15.0],
    }
    assert set(dataset.variables) == {"arm", "score"}
    assert dataset.variables["score"].origin_step_id == "benchmark-import"


def test_load_case_dataset_rejects_path_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes pilot root"):
        load_case_dataset(
            {
                "case_id": "case-1",
                "evidence_stage": "cold_start",
                "data_file": "../outside.csv",
            },
            tmp_path,
        )


def test_candidate_identity_normalizes_current_comparison_roles() -> None:
    candidate = RecommendationCandidate(
        candidate_id="comparison:score:arm",
        kind="comparison",
        title_ko="집단 비교",
        level="강한 추천",
        reason_ko="두 집단",
        outcome_key="score",
        group_key="arm",
    )

    normalized = candidate_identity(candidate)

    assert normalized.family == "compare_groups"
    assert normalized.design_mode == "independent"
    assert dict(normalized.roles) == {
        "group": ("arm",),
        "outcome": ("score",),
    }


def test_baseline_prediction_preserves_product_ranking_and_default() -> None:
    pilot_root = Path("tests/fixtures/recommendation_benchmark/public/pilot")
    case = {
        "case_id": "pilot-003-two-groups",
        "evidence_stage": "cold_start",
        "data_file": "data/pilot-003-two-groups.csv",
    }
    dataset = load_case_dataset(case, pilot_root)
    state = RecommendationService().recommend(dataset)

    prediction = predict_current_baseline(case, dataset)

    assert prediction.candidates == tuple(
        candidate_identity(candidate) for candidate in state.candidates[:3]
    )
    assert state.default_candidate is not None
    assert prediction.primary_action.value == candidate_identity(state.default_candidate)
    assert prediction.level == "strong"


def test_baseline_prediction_uses_explicit_abstention_when_current_a_has_no_default(
    tmp_path: Path,
) -> None:
    pilot_root = tmp_path / "pilot"
    data_path = pilot_root / "data" / "empty.csv"
    data_path.parent.mkdir(parents=True)
    pd.DataFrame({"id": [1, 2, 3], "constant": [1, 1, 1]}).to_csv(
        data_path,
        index=False,
    )
    case = {
        "case_id": "case-empty",
        "evidence_stage": "cold_start",
        "data_file": "data/empty.csv",
    }

    prediction = predict_current_baseline(
        case,
        load_case_dataset(case, pilot_root),
    )

    assert prediction.primary_action.kind == "abstain"
    assert prediction.primary_action.value == "no_safe_candidate"
    assert prediction.level == "none"
    assert prediction.candidates == ()
