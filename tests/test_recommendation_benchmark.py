from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from modori.recommendation_benchmark import (
    BenchmarkContractError,
    GoldRecord,
    PredictionRecord,
    PrimaryAction,
    RecommendationIdentity,
    ScorerConfig,
    canonical_json,
    scorer_fingerprint,
)


def identity(
    family: str = "compare_groups",
    *,
    outcome: str = "score",
    group: str = "arm",
) -> RecommendationIdentity:
    return RecommendationIdentity(
        family=family,
        roles=(
            ("group", (group,)),
            ("outcome", (outcome,)),
        ),
        design_mode="independent",
    )


def test_recommendation_identity_canonicalizes_role_names_not_role_value_order() -> None:
    first = RecommendationIdentity(
        family="regression_ols",
        roles=(
            ("predictors", ("age", "education")),
            ("outcome", ("score",)),
        ),
        design_mode="main_effects",
    )
    second = RecommendationIdentity(
        family="regression_ols",
        roles=(
            ("outcome", ("score",)),
            ("predictors", ("age", "education")),
        ),
        design_mode="main_effects",
    )

    assert first == second
    assert first.roles == (
        ("outcome", ("score",)),
        ("predictors", ("age", "education")),
    )
    assert RecommendationIdentity(
        family="regression_ols",
        roles=(
            ("outcome", ("score",)),
            ("predictors", ("education", "age")),
        ),
        design_mode="main_effects",
    ) != first


def test_recommendation_identity_rejects_unknown_mapping_keys_and_duplicate_roles() -> None:
    with pytest.raises(BenchmarkContractError, match="unknown keys: extra"):
        RecommendationIdentity.from_mapping(
            {
                "family": "compare_groups",
                "roles": {"outcome": ["score"], "group": ["arm"]},
                "design_mode": "independent",
                "extra": True,
            }
        )

    with pytest.raises(BenchmarkContractError, match="duplicate role"):
        RecommendationIdentity(
            family="compare_groups",
            roles=(("outcome", ("score",)), ("outcome", ("other",))),
            design_mode="independent",
        )


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (PrimaryAction(kind="recommend", value="not-an-identity"), "identity"),
        (PrimaryAction(kind="clarify", value=""), "fact ID"),
        (PrimaryAction(kind="abstain", value=""), "reason code"),
        (PrimaryAction(kind="other", value="x"), "action kind"),
    ],
)
def test_primary_action_rejects_invalid_kind_value_pairs(
    action: PrimaryAction,
    message: str,
) -> None:
    with pytest.raises(BenchmarkContractError, match=message):
        action.validate()


def test_gold_record_requires_action_class_specific_evidence() -> None:
    with pytest.raises(BenchmarkContractError, match="acceptable recommendation"):
        GoldRecord(
            case_id="case-1",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
        )

    with pytest.raises(BenchmarkContractError, match="clarification fact"):
        GoldRecord(
            case_id="case-1",
            evidence_stage="cold_start",
            action_class="clarification_required",
        )

    with pytest.raises(BenchmarkContractError, match="abstention reason"):
        GoldRecord(
            case_id="case-1",
            evidence_stage="cold_start",
            action_class="abstention_required",
        )


def test_prediction_record_rejects_more_than_three_candidates() -> None:
    candidate = identity()

    with pytest.raises(BenchmarkContractError, match="at most three"):
        PredictionRecord(
            case_id="case-1",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="recommend", value=candidate),
            candidates=(candidate, candidate, candidate, candidate),
            level="candidate",
        )


def test_gold_and_prediction_mapping_round_trip_is_strict() -> None:
    candidate = identity()
    gold_mapping = {
        "case_id": "case-1",
        "evidence_stage": "clarified",
        "action_class": "recommendation_eligible",
        "acceptable_recommendations": [candidate.to_mapping()],
        "required_clarification_facts": [],
        "acceptable_abstention_reasons": [],
        "failure_severity": "E3",
    }
    prediction_mapping = {
        "case_id": "case-1",
        "evidence_stage": "clarified",
        "primary_action": {"kind": "recommend", "value": candidate.to_mapping()},
        "candidates": [candidate.to_mapping()],
        "level": "candidate",
        "questions": [],
    }

    gold = GoldRecord.from_mapping(gold_mapping)
    prediction = PredictionRecord.from_mapping(prediction_mapping)

    assert gold.to_mapping() == gold_mapping
    assert prediction.to_mapping() == prediction_mapping

    with pytest.raises(BenchmarkContractError, match="unknown keys: extra"):
        GoldRecord.from_mapping({**gold_mapping, "extra": True})
    with pytest.raises(BenchmarkContractError, match="unknown keys: extra"):
        PredictionRecord.from_mapping({**prediction_mapping, "extra": True})


def test_prediction_requires_recommend_default_in_candidates_and_matching_level() -> None:
    candidate = identity()
    other = identity(outcome="other")

    with pytest.raises(BenchmarkContractError, match="must appear in candidates"):
        PredictionRecord(
            case_id="case-1",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="recommend", value=candidate),
            candidates=(other,),
            level="candidate",
        )
    with pytest.raises(BenchmarkContractError, match="level must be none"):
        PredictionRecord(
            case_id="case-1",
            evidence_stage="cold_start",
            primary_action=PrimaryAction(kind="abstain", value="insufficient_context"),
            level="candidate",
        )


def test_scorer_fingerprint_is_canonical_and_configuration_sensitive() -> None:
    config = ScorerConfig(
        schema_version=1,
        scorer_version="recommendation-scorer-v1",
        confidence_level=0.95,
    )

    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert scorer_fingerprint(config) == scorer_fingerprint(config)
    assert scorer_fingerprint(config).startswith("sha256:")
    assert scorer_fingerprint(config) != scorer_fingerprint(
        ScorerConfig(
            schema_version=1,
            scorer_version="recommendation-scorer-v2",
            confidence_level=0.95,
        )
    )


def test_benchmark_contracts_are_frozen() -> None:
    candidate = identity()

    with pytest.raises(FrozenInstanceError):
        candidate.family = "other"  # type: ignore[misc]
