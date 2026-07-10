from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from modori.recommendation_benchmark import (
    BenchmarkContractError,
    AdjudicationRecord,
    LabelingRates,
    GoldRecord,
    PredictionRecord,
    PrimaryAction,
    RecommendationIdentity,
    ReviewerAnnotation,
    ReviewerSubmission,
    ScorerConfig,
    canonical_json,
    newcombe_paired_difference_interval,
    project_labeling_cost,
    reviewer_agreement,
    score_predictions,
    scorer_fingerprint,
    wilson_lower_bound,
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
    with pytest.raises(BenchmarkContractError, match="first candidate"):
        PredictionRecord(
            case_id="case-1",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="recommend", value=candidate),
            candidates=(other, candidate),
            level="candidate",
        )
    with pytest.raises(BenchmarkContractError, match="level must be none"):
        PredictionRecord(
            case_id="case-1",
            evidence_stage="cold_start",
            primary_action=PrimaryAction(kind="abstain", value="insufficient_context"),
            level="candidate",
        )


def test_gold_action_class_rejects_cross_class_evidence() -> None:
    candidate = identity()

    with pytest.raises(BenchmarkContractError, match="must not include clarification"):
        GoldRecord(
            case_id="case-1",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
            acceptable_recommendations=(candidate,),
            required_clarification_facts=("paired_status",),
        )
    with pytest.raises(BenchmarkContractError, match="must not include recommendations"):
        GoldRecord(
            case_id="case-1",
            evidence_stage="cold_start",
            action_class="abstention_required",
            acceptable_recommendations=(candidate,),
            acceptable_abstention_reasons=("unsupported_design",),
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


def test_score_predictions_separates_recommendation_clarification_and_abstention() -> None:
    correct = identity()
    wrong = identity(outcome="other")
    gold = (
        GoldRecord(
            case_id="recommend-correct",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
            acceptable_recommendations=(correct,),
        ),
        GoldRecord(
            case_id="recommend-wrong-top3-hit",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
            acceptable_recommendations=(correct,),
            failure_severity="E3",
        ),
        GoldRecord(
            case_id="needs-question",
            evidence_stage="cold_start",
            action_class="clarification_required",
            required_clarification_facts=("paired_status",),
        ),
        GoldRecord(
            case_id="must-abstain",
            evidence_stage="cold_start",
            action_class="abstention_required",
            acceptable_abstention_reasons=("unsupported_design",),
            failure_severity="E4",
        ),
    )
    predictions = (
        PredictionRecord(
            case_id="recommend-correct",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="recommend", value=correct),
            candidates=(correct,),
            level="strong",
        ),
        PredictionRecord(
            case_id="recommend-wrong-top3-hit",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="recommend", value=wrong),
            candidates=(wrong, correct),
            level="candidate",
        ),
        PredictionRecord(
            case_id="needs-question",
            evidence_stage="cold_start",
            primary_action=PrimaryAction(kind="clarify", value="paired_status"),
            questions=("paired_status",),
        ),
        PredictionRecord(
            case_id="must-abstain",
            evidence_stage="cold_start",
            primary_action=PrimaryAction(kind="abstain", value="unsupported_design"),
        ),
    )

    score = score_predictions(gold, predictions, ScorerConfig())

    assert (score.recommendation_top1.successes, score.recommendation_top1.total) == (1, 2)
    assert (score.top3_case_hit.successes, score.top3_case_hit.total) == (2, 2)
    assert (score.recommendation_coverage.successes, score.recommendation_coverage.total) == (
        2,
        2,
    )
    assert (score.clarification_accuracy.successes, score.clarification_accuracy.total) == (
        1,
        1,
    )
    assert (score.abstention_accuracy.successes, score.abstention_accuracy.total) == (1, 1)
    assert (score.primary_action_accuracy.successes, score.primary_action_accuracy.total) == (
        3,
        4,
    )
    assert (score.strong_precision.successes, score.strong_precision.total) == (1, 1)
    assert (score.question_efficiency.successes, score.question_efficiency.total) == (1, 1)
    assert dict(score.errors_by_severity) == {
        "E1": 0,
        "E2": 0,
        "E3": 1,
        "E4": 0,
        "E5": 0,
    }


def test_tied_alternatives_can_hit_top3_without_top1_or_coverage() -> None:
    acceptable = identity()
    alternative = identity(outcome="other")
    gold = (
        GoldRecord(
            case_id="tie",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
            acceptable_recommendations=(acceptable,),
        ),
    )
    predictions = (
        PredictionRecord(
            case_id="tie",
            evidence_stage="clarified",
            primary_action=PrimaryAction(kind="abstain", value="unresolved_tie"),
            candidates=(alternative, acceptable),
            level="none",
        ),
    )

    score = score_predictions(gold, predictions, ScorerConfig())

    assert score.recommendation_top1.rate == 0.0
    assert score.top3_case_hit.rate == 1.0
    assert score.recommendation_coverage.rate == 0.0


def test_score_zero_denominators_are_explicit_and_questions_do_not_inflate_top1() -> None:
    gold = (
        GoldRecord(
            case_id="question",
            evidence_stage="cold_start",
            action_class="clarification_required",
            required_clarification_facts=("unit_of_observation",),
        ),
    )
    predictions = (
        PredictionRecord(
            case_id="question",
            evidence_stage="cold_start",
            primary_action=PrimaryAction(kind="clarify", value="unit_of_observation"),
        ),
    )

    score = score_predictions(gold, predictions, ScorerConfig())

    assert score.recommendation_top1.status == "insufficient_evidence"
    assert score.recommendation_top1.rate is None
    assert score.strong_precision.status == "insufficient_evidence"
    assert score.question_efficiency.status == "not_applicable"
    assert score.primary_action_accuracy.rate == 1.0


def test_score_predictions_rejects_missing_extra_and_duplicate_case_stages() -> None:
    candidate = identity()
    gold = (
        GoldRecord(
            case_id="case-1",
            evidence_stage="clarified",
            action_class="recommendation_eligible",
            acceptable_recommendations=(candidate,),
        ),
    )
    prediction = PredictionRecord(
        case_id="case-1",
        evidence_stage="clarified",
        primary_action=PrimaryAction(kind="recommend", value=candidate),
        candidates=(candidate,),
        level="candidate",
    )

    with pytest.raises(BenchmarkContractError, match="missing predictions"):
        score_predictions(gold, (), ScorerConfig())
    with pytest.raises(BenchmarkContractError, match="unexpected predictions"):
        score_predictions(
            gold,
            (
                prediction,
                PredictionRecord(
                    case_id="case-2",
                    evidence_stage="clarified",
                    primary_action=PrimaryAction(kind="abstain", value="no_candidate"),
                ),
            ),
            ScorerConfig(),
        )
    with pytest.raises(BenchmarkContractError, match="duplicate gold"):
        score_predictions((gold[0], gold[0]), (prediction,), ScorerConfig())
    with pytest.raises(BenchmarkContractError, match="gold records must not be empty"):
        score_predictions((), (), ScorerConfig())


def test_one_sided_wilson_release_boundaries_are_locked() -> None:
    assert wilson_lower_bound(334, 400, 0.95) > 0.80
    assert wilson_lower_bound(333, 400, 0.95) < 0.80
    assert wilson_lower_bound(370, 400, 0.95) > 0.90
    assert wilson_lower_bound(369, 400, 0.95) < 0.90
    assert wilson_lower_bound(0, 0, 0.95) is None


def test_newcombe_method_10_matches_published_table_iii_example() -> None:
    both_correct, gain, loss, both_wrong = 20, 12, 2, 16
    candidate_correct = (
        [True] * both_correct
        + [True] * gain
        + [False] * loss
        + [False] * both_wrong
    )
    baseline_correct = (
        [True] * both_correct
        + [False] * gain
        + [True] * loss
        + [False] * both_wrong
    )

    lower, upper = newcombe_paired_difference_interval(
        baseline_correct,
        candidate_correct,
        0.95,
    )
    reverse_lower, reverse_upper = newcombe_paired_difference_interval(
        candidate_correct,
        baseline_correct,
        0.95,
    )

    assert lower == pytest.approx(0.0562, abs=5e-5)
    assert upper == pytest.approx(0.3292, abs=5e-5)
    assert reverse_lower == pytest.approx(-upper, abs=1e-12)
    assert reverse_upper == pytest.approx(-lower, abs=1e-12)


def test_newcombe_interval_rejects_empty_or_unpaired_inputs() -> None:
    with pytest.raises(BenchmarkContractError, match="at least one"):
        newcombe_paired_difference_interval([], [], 0.95)
    with pytest.raises(BenchmarkContractError, match="equal length"):
        newcombe_paired_difference_interval([True], [True, False], 0.95)


def annotation(
    case_id: str,
    action_class: str,
    *,
    recommendations: tuple[RecommendationIdentity, ...] = (),
    clarification_facts: tuple[str, ...] = (),
    active_minutes: float = 10.0,
) -> ReviewerAnnotation:
    return ReviewerAnnotation(
        case_id=case_id,
        evidence_stage="cold_start",
        action_class=action_class,
        acceptable_recommendations=recommendations,
        required_clarification_facts=clarification_facts,
        acceptable_abstention_reasons=(
            ("unsupported_design",) if action_class == "abstention_required" else ()
        ),
        active_minutes=active_minutes,
    )


def test_reviewer_agreement_computes_alpha_and_nonempty_set_metrics() -> None:
    first = identity(outcome="first")
    second = identity(outcome="second")
    third = identity(outcome="third")
    reviewer_a = ReviewerSubmission(
        reviewer_id="reviewer-a",
        annotations=(
            annotation("case-1", "recommendation_eligible", recommendations=(first, second)),
            annotation("case-2", "recommendation_eligible", recommendations=(third,)),
            annotation(
                "case-3",
                "clarification_required",
                clarification_facts=("paired_status", "unit"),
            ),
            annotation("case-4", "abstention_required"),
        ),
    )
    reviewer_b = ReviewerSubmission(
        reviewer_id="reviewer-b",
        annotations=(
            annotation("case-1", "recommendation_eligible", recommendations=(first,)),
            annotation(
                "case-2",
                "clarification_required",
                clarification_facts=("research_goal",),
            ),
            annotation(
                "case-3",
                "clarification_required",
                clarification_facts=("paired_status",),
            ),
            annotation("case-4", "abstention_required"),
        ),
    )

    report = reviewer_agreement(reviewer_a, reviewer_b)

    assert report.case_count == 4
    assert report.primary_action_alpha == pytest.approx(2.0 / 3.0)
    assert report.primary_action_status == "ok"
    assert report.recommendation_jaccard == pytest.approx(0.25)
    assert report.recommendation_exact == 0.0
    assert report.clarification_jaccard == pytest.approx(0.25)
    assert report.clarification_exact == 0.0


def test_reviewer_agreement_does_not_pass_constant_or_nonapplicable_labels() -> None:
    candidate = identity()
    submission_a = ReviewerSubmission(
        reviewer_id="reviewer-a",
        annotations=(
            annotation("case-1", "recommendation_eligible", recommendations=(candidate,)),
            annotation("case-2", "recommendation_eligible", recommendations=(candidate,)),
        ),
    )
    submission_b = ReviewerSubmission(
        reviewer_id="reviewer-b",
        annotations=submission_a.annotations,
    )

    report = reviewer_agreement(submission_a, submission_b)

    assert report.primary_action_alpha is None
    assert report.primary_action_status == "not_estimable"
    assert report.recommendation_jaccard == 1.0
    assert report.recommendation_exact == 1.0
    assert report.clarification_jaccard is None
    assert report.clarification_exact is None


def test_labeling_cost_projects_two_reviewers_adjudication_and_fixed_costs() -> None:
    reviewer_a = ReviewerSubmission(
        reviewer_id="reviewer-a",
        annotations=tuple(
            annotation(
                f"case-{index:02d}",
                "abstention_required",
                active_minutes=10.0,
            )
            for index in range(1, 21)
        ),
    )
    reviewer_b = ReviewerSubmission(
        reviewer_id="reviewer-b",
        annotations=tuple(
            annotation(
                f"case-{index:02d}",
                "abstention_required",
                active_minutes=12.0,
            )
            for index in range(1, 21)
        ),
    )
    adjudications = tuple(
        AdjudicationRecord(
            case_id=f"case-{index:02d}",
            evidence_stage="cold_start",
            resolution_minutes=4.0,
        )
        for index in range(1, 21)
    )

    projection = project_labeling_cost(
        (reviewer_a, reviewer_b),
        adjudications,
        stage_case_count=150,
        rates=LabelingRates(
            reviewer_hourly=100.0,
            adjudicator_hourly=150.0,
            setup_cost=1000.0,
            data_steward_cost=500.0,
            project_management_cost=250.0,
        ),
    )

    assert projection.pilot_case_count == 20
    assert projection.median_reviewer_minutes == 11.0
    assert projection.median_adjudication_minutes == 4.0
    assert projection.projected_reviewer_hours == pytest.approx(55.0)
    assert projection.projected_adjudication_hours == pytest.approx(10.0)
    assert projection.projected_expert_hours_with_contingency == pytest.approx(81.25)
    assert projection.base_labor_cost == pytest.approx(7000.0)
    assert projection.contingency_cost == pytest.approx(1750.0)
    assert projection.fixed_cost == pytest.approx(1750.0)
    assert projection.total_cost == pytest.approx(10500.0)


def test_agreement_and_cost_reject_incomplete_or_invalid_submissions() -> None:
    candidate = identity()
    reviewer_a = ReviewerSubmission(
        reviewer_id="same",
        annotations=(
            annotation("case-1", "recommendation_eligible", recommendations=(candidate,)),
        ),
    )
    reviewer_b = ReviewerSubmission(
        reviewer_id="same",
        annotations=(
            annotation("case-2", "recommendation_eligible", recommendations=(candidate,)),
        ),
    )

    with pytest.raises(BenchmarkContractError, match="different reviewer IDs"):
        reviewer_agreement(reviewer_a, reviewer_b)
    with pytest.raises(BenchmarkContractError, match="exactly 20 pilot cases"):
        project_labeling_cost(
            (reviewer_a, ReviewerSubmission("other", reviewer_a.annotations)),
            (
                AdjudicationRecord("case-1", "cold_start", 1.0),
            ),
            stage_case_count=150,
            rates=LabelingRates(100.0, 150.0),
        )
    with pytest.raises(BenchmarkContractError, match="finite and positive"):
        annotation(
            "case-invalid",
            "abstention_required",
            active_minutes=float("nan"),
        )
