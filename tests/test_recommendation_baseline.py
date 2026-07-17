from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from modori.recommendation_baseline import (
    _historical_baseline_default,
    candidate_identity,
    load_case_dataset,
    predict_current_baseline,
)
from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationCandidate, RecommendationService


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BASELINE = (
    ROOT
    / "tests"
    / "fixtures"
    / "recommendation_benchmark"
    / "public"
    / "pilot"
    / "baseline-a-predictions.jsonl"
)
CANONICAL_SHA256 = "FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650"


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
        routing_tier=RecommendationRoutingTier.PRIMARY,
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


def test_candidate_identity_preserves_ordered_factorial_roles() -> None:
    candidate = RecommendationCandidate(
        candidate_id="anova_factorial:score:condition:site",
        kind="anova_factorial",
        title_ko="이원 Type III 분산분석 후보",
        routing_tier=RecommendationRoutingTier.SECONDARY,
        reason_ko="역할 확인 필요",
        outcome_key="score",
        factor_a_key="condition",
        factor_b_key="site",
        requires_configuration=True,
    )

    normalized = candidate_identity(candidate)

    assert normalized.family == "anova_factorial"
    assert normalized.design_mode == "complete_cell_type_iii"
    assert dict(normalized.roles) == {
        "factor_a": ("condition",),
        "factor_b": ("site",),
        "outcome": ("score",),
    }


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (
            RecommendationCandidate(
                candidate_id="mediation:x:m:y",
                kind="mediation",
                title_ko="매개분석 후보",
                routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
                reason_ko="모형 확인 필요",
                x_key="x",
                mediator_key="m",
                y_key="y",
            ),
            ("x", "m", "y"),
        ),
        (
            RecommendationCandidate(
                candidate_id="moderated_mediation:7:x:m:w:y",
                kind="moderated_mediation",
                title_ko="조절된 매개분석 후보",
                routing_tier=RecommendationRoutingTier.HEIGHTENED_REVIEW,
                reason_ko="모형 확인 필요",
                model="7",
                x_key="x",
                mediator_key="m",
                moderator_key="w",
                y_key="y",
            ),
            ("x", "m", "w", "y"),
        ),
    ],
)
def test_candidate_identity_reconstructs_historical_mediation_roles(
    candidate: RecommendationCandidate,
    expected: tuple[str, ...],
) -> None:
    normalized = candidate_identity(candidate)

    assert dict(normalized.roles) == {"variables": expected}


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
    historical = _historical_baseline_default(state.candidates)
    assert historical is state.candidates[0]
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
    assert prediction.primary_action.value == candidate_identity(historical)
    assert prediction.level == "strong"


def test_predict_a_preserves_canonical_baseline_bytes(tmp_path: Path) -> None:
    output = tmp_path / "baseline-a-predictions.jsonl"

    subprocess.run(
        [
            sys.executable,
            "scripts/recommendation_benchmark.py",
            "predict-a",
            "--pack-root",
            "tests/fixtures/recommendation_benchmark",
            "--output",
            str(output),
            "--force",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    actual = output.read_bytes()
    assert actual == CANONICAL_BASELINE.read_bytes()
    assert hashlib.sha256(actual).hexdigest().upper() == CANONICAL_SHA256


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
