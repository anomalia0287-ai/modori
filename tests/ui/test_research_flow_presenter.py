from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import modori.research_flow.coordinator as coordinator_module
from modori.research_flow import (
    DurableDecision,
    DurablePendingDecision,
    DurableRetraction,
    PreflightDisposition,
    PreflightResult,
    ResearchFlowState,
    StaticBoundary,
    StepInputIssue,
    map_passport_to_step,
    preflight_mapped_step,
)
from modori.research_memory import LedgerArtifact
from modori.research_os import (
    AnalysisPassport,
    Language,
    P1TaskProfile,
    PrimaryAction,
    ResearchOsService,
    ResearchRequest,
    build_causal_abstention_request,
)
from modori.research_os.counterfactual_planner import CounterfactualPlanner
from modori.ui.contracts import ControllerMode
from modori.ui.recommendation_controller import RecommendationControllerMixin
from modori.ui.research_flow_presenter import (
    ResearchCandidateView,
    ResearchFlowPresentationError,
    ResearchFlowView,
    ResearchOptionView,
    ResearchUiAction,
    ResearchUiCommand,
    present_durable_record,
    present_static_boundary,
    present_transient_state,
)
from modori.ui.strings import RESEARCH_FLOW_STRINGS
from tests.test_research_flow_handoff import _terminal
from tests.test_research_flow_preflight import _blocked_dataset, _valid_dataset
from tests.test_research_os_p1_intake import _passport_envelope, _request


def _durable(request: ResearchRequest, passport: AnalysisPassport) -> DurableDecision:
    artifact = LedgerArtifact.from_value(passport)
    return DurableDecision(
        task_project_id=request.question.envelope.project_id,
        request=request,
        passport=passport,
        passport_artifact_id=artifact.artifact_id,
        passport_digest=passport.digest(),
        committed_event_id=passport.envelope.created_event_ref,
        committed_sequence=2,
        committed_head_hash="f" * 64,
        action=passport.action,
        _coordinator_seal=coordinator_module._DURABLE_COORDINATOR_SEAL,
    )


def _terminal_record(profile: P1TaskProfile) -> DurableDecision:
    request, passport = _terminal(profile)
    return _durable(request, passport)


def _clarify_record() -> DurableDecision:
    request = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    resolved = ResearchOsService().resolve_and_plan(
        request,
        _passport_envelope(request, 1),
    )
    assert resolved.passport.action is PrimaryAction.CLARIFY
    return _durable(request, resolved.passport)


def _abstain_record(language: Language = Language.KO) -> DurableDecision:
    base = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    request = build_causal_abstention_request(
        task_project_id=base.question.envelope.project_id,
        initial_event_id="event:causal:1",
        dataset_fingerprint=base.current_dataset_fingerprint,
        source_schema_fingerprint=base.study.source_schema_fingerprint,
        available_variable_ids=base.available_variable_ids,
        language=language,
    )
    resolved = ResearchOsService().resolve_and_plan(
        request,
        _passport_envelope(request, 1),
    )
    assert resolved.passport.action is PrimaryAction.ABSTAIN
    return _durable(request, resolved.passport)


def _labels(record: DurableDecision) -> dict[str, str]:
    return {
        variable_id: f"표시 변수 {index}"
        for index, variable_id in enumerate(
            record.request.available_variable_ids,
            start=1,
        )
    }


def _preflight(
    record: DurableDecision,
    *,
    blocked: bool = False,
) -> PreflightResult:
    profile_by_capability_fragment = {
        "descriptive_summary": P1TaskProfile.NUMERIC_DISTRIBUTION,
        "frequency_distribution": P1TaskProfile.CATEGORY_FREQUENCY,
        "pearson_product_moment": P1TaskProfile.LINEAR_CO_MOVEMENT,
        "spearman_rank_monotonic": P1TaskProfile.RANK_CO_MOVEMENT,
        "welch_mean_difference": P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
        "paired_t_mean_change": P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
    }
    payload = record.passport.recommend_local
    assert payload is not None
    capability_key = payload.capability_keys[0]
    profile = next(
        value
        for fragment, value in profile_by_capability_fragment.items()
        if fragment in capability_key
    )
    mapping = map_passport_to_step(
        record.passport,
        record.request,
        current_dataset_fingerprint=record.request.current_dataset_fingerprint,
    )
    dataset = _blocked_dataset(profile)[0] if blocked else _valid_dataset(profile)
    return preflight_mapped_step(
        mapping,
        dataset,
        captured_pipeline_version=7,
        current_pipeline_version=lambda: 7,
    )


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
@pytest.mark.parametrize("language", (Language.KO, Language.EN))
def test_candidate_projection_keeps_authority_identical_across_modes(
    profile: P1TaskProfile,
    language: Language,
) -> None:
    record = _terminal_record(profile)
    preflight = _preflight(record)
    labels = _labels(record)

    casual = present_durable_record(
        record,
        mode=ControllerMode.GUIDED,
        language=language,
        preflight=preflight,
        variable_labels=labels,
    )
    pro = present_durable_record(
        record,
        mode=ControllerMode.STANDARD,
        language=language,
        preflight=preflight,
        variable_labels=labels,
    )

    assert casual.state is pro.state is ResearchFlowState.CANDIDATE_READY
    assert casual.decision_identity_digest == pro.decision_identity_digest
    assert casual.decision_identity_digest == record.passport_digest
    assert casual.visible_passport_digest == ""
    assert pro.visible_passport_digest == record.passport_digest[:12]
    assert casual.primary_action is not None
    assert pro.primary_action is not None
    assert casual.primary_action.command is pro.primary_action.command
    assert casual.primary_action.command is ResearchUiCommand.PREPARE
    assert casual.primary_action.enabled is pro.primary_action.enabled is True
    assert casual.candidate is not None
    assert pro.candidate is not None
    assert casual.candidate.capability_label == pro.candidate.capability_label
    assert casual.candidate.method_label == pro.candidate.method_label
    assert casual.candidate.claim_boundary == pro.candidate.claim_boundary
    assert casual.candidate.role_rows == ()
    assert pro.candidate.role_rows
    assert all(value in labels.values() for _label, value in pro.candidate.role_rows)
    assert not set(record.request.available_variable_ids).intersection(
        value for _label, value in pro.candidate.role_rows
    )
    assert casual.evidence_rows == ()
    assert pro.evidence_rows
    copy = RESEARCH_FLOW_STRINGS[language.value]
    assert casual.badge_text == copy["candidate.experimental_badge"]
    assert casual.candidate.review_status == copy["candidate.review_status"]
    assert casual.candidate.persistent_boundary == copy["candidate.no_auto_run"]
    assert casual.primary_action.label == copy["action.prepare"]


def test_question_projection_uses_committed_question_copy_without_replanning_or_legacy_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _clarify_record()

    def poisoned(*_args, **_kwargs):
        raise AssertionError("presentation must not search or read a legacy reason")

    monkeypatch.setattr(CounterfactualPlanner, "plan", poisoned)
    monkeypatch.setattr(
        RecommendationControllerMixin,
        "recommendationReason",
        property(poisoned),
    )

    casual = present_durable_record(
        record,
        mode=ControllerMode.GUIDED,
        language=Language.KO,
        preflight=None,
        variable_labels=None,
    )
    pro = present_durable_record(
        record,
        mode=ControllerMode.STANDARD,
        language=Language.KO,
        preflight=None,
        variable_labels=None,
    )

    assert casual.state is pro.state is ResearchFlowState.CLARIFY_READY
    assert casual.question is not None
    assert pro.question is not None
    assert casual.question.question_text == pro.question.question_text
    assert casual.question.base_reason == pro.question.base_reason
    assert casual.question.evidence_rows == ()
    assert pro.question.evidence_rows
    assert casual.decision_identity_digest == pro.decision_identity_digest
    assert casual.primary_action is not None
    assert pro.primary_action is not None
    assert casual.primary_action.command is pro.primary_action.command
    assert casual.primary_action.command is ResearchUiCommand.ANSWER
    assert casual.options == pro.options
    assert casual.visible_passport_digest == ""
    assert pro.visible_passport_digest == record.passport_digest[:12]


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_preflight_block_preserves_exact_method_and_says_no_analysis_ran(
    profile: P1TaskProfile,
) -> None:
    record = _terminal_record(profile)
    preflight = _preflight(record, blocked=True)
    assert preflight.disposition is PreflightDisposition.PREPARE_BLOCKED

    view = present_durable_record(
        record,
        mode=ControllerMode.STANDARD,
        language=Language.EN,
        preflight=preflight,
        variable_labels=_labels(record),
    )

    assert view.state is ResearchFlowState.PREPARATION_BLOCKED
    assert view.candidate is not None
    assert view.primary_action is None
    assert "No analysis was run" in view.body
    payload = record.passport.recommend_local
    assert payload is not None
    if "pearson" in payload.capability_keys[0]:
        assert "Pearson" in view.candidate.method_label
        assert "Spearman" not in view.candidate.method_label
    assert any(label == "Blocked condition" for label, _value in view.evidence_rows)


@pytest.mark.parametrize(
    ("preflight", "state"),
    (
        (
            PreflightResult(
                disposition=PreflightDisposition.STALE,
                issues=(StepInputIssue(code="pipeline_changed"),),
                preparation=None,
                captured_pipeline_version=7,
            ),
            ResearchFlowState.REPLAN_REQUIRED,
        ),
        (
            PreflightResult(
                disposition=PreflightDisposition.FAILURE,
                issues=(StepInputIssue(code="preflight_failure"),),
                preparation=None,
                captured_pipeline_version=7,
            ),
            ResearchFlowState.FAILURE,
        ),
    ),
)
def test_nonpreparable_terminal_preflight_never_leaks_a_candidate(
    preflight: PreflightResult,
    state: ResearchFlowState,
) -> None:
    record = _terminal_record(P1TaskProfile.LINEAR_CO_MOVEMENT)

    view = present_durable_record(
        record,
        mode=ControllerMode.STANDARD,
        language=Language.KO,
        preflight=preflight,
        variable_labels=_labels(record),
    )

    assert view.state is state
    assert view.candidate is None
    assert view.visible_passport_digest == record.passport_digest[:12]
    if state is ResearchFlowState.REPLAN_REQUIRED:
        assert view.primary_action is not None
        assert view.primary_action.command is ResearchUiCommand.REPLAN


def test_abstain_pending_and_retracted_are_distinct_closed_states() -> None:
    abstain = _abstain_record()
    pending_request = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    pending = DurablePendingDecision(
        task_project_id=pending_request.question.envelope.project_id,
        request=pending_request,
        committed_event_id="event:pending:1",
        committed_sequence=1,
        committed_head_hash="a" * 64,
        reason_code="decision_not_committed",
        _coordinator_seal=coordinator_module._DURABLE_COORDINATOR_SEAL,
    )
    prior = _terminal_record(P1TaskProfile.NUMERIC_DISTRIBUTION)
    retracted = DurableRetraction(
        task_project_id=prior.task_project_id,
        request=prior.request,
        retracted_passport_artifact_id=prior.passport_artifact_id,
        retracted_passport_digest=prior.passport_digest,
        committed_event_id="event:retracted:3",
        committed_sequence=3,
        committed_head_hash="b" * 64,
        _coordinator_seal=coordinator_module._DURABLE_COORDINATOR_SEAL,
    )

    views = (
        present_durable_record(
            abstain,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
            preflight=None,
            variable_labels=None,
        ),
        present_durable_record(
            pending,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
            preflight=None,
            variable_labels=None,
        ),
        present_durable_record(
            retracted,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
            preflight=None,
            variable_labels=None,
        ),
    )

    assert tuple(view.state for view in views) == (
        ResearchFlowState.ABSTAIN_READY,
        ResearchFlowState.RECOVERY_PENDING,
        ResearchFlowState.RETRACTED,
    )
    assert len({view.body for view in views}) == 3
    assert all(view.candidate is None for view in views)


@pytest.mark.parametrize("language", (Language.KO, Language.EN))
@pytest.mark.parametrize("boundary", tuple(StaticBoundary))
def test_static_boundaries_are_closed_and_carry_no_decision_authority(
    boundary: StaticBoundary,
    language: Language,
) -> None:
    view = present_static_boundary(
        boundary,
        mode=ControllerMode.GUIDED,
        language=language,
    )

    assert view.decision_identity_digest == ""
    assert view.visible_passport_digest == ""
    assert view.candidate is None
    assert view.question is None
    assert view.title
    assert view.body
    assert view.primary_action is not None
    if boundary is StaticBoundary.CAUSAL_SCOPE_NOTICE:
        assert view.primary_action.command is ResearchUiCommand.CAUSAL_RECORD
    else:
        assert view.primary_action.command is ResearchUiCommand.BACK


@pytest.mark.parametrize("language", (Language.KO, Language.EN))
@pytest.mark.parametrize(
    "state",
    (
        ResearchFlowState.IDLE,
        ResearchFlowState.FINGERPRINTING,
        ResearchFlowState.INTAKE_CAUSAL,
        ResearchFlowState.INTAKE_BLOCKED,
        ResearchFlowState.INTAKE_PROFILE,
        ResearchFlowState.INTAKE_ROLES,
        ResearchFlowState.COMMITTING,
        ResearchFlowState.HANDOFF_PREFLIGHT,
        ResearchFlowState.MEMORY_UNAVAILABLE,
        ResearchFlowState.FAILURE,
        ResearchFlowState.CORRUPTION,
        ResearchFlowState.REPLAN_REQUIRED,
        ResearchFlowState.CANCELLED,
        ResearchFlowState.PREPARE_REVIEW,
        ResearchFlowState.CONFIRMED,
        ResearchFlowState.MANUAL_RUN,
    ),
)
def test_transient_catalog_is_closed_bilingual_and_non_authoritative(
    state: ResearchFlowState,
    language: Language,
) -> None:
    view = present_transient_state(
        state,
        mode=ControllerMode.STANDARD,
        language=language,
    )

    assert view.state is state
    assert view.title
    assert view.body
    assert view.decision_identity_digest == ""
    assert view.visible_passport_digest == ""
    assert view.candidate is None
    assert view.question is None
    assert view.options == ()


def test_error_taxonomy_copy_is_not_collapsed() -> None:
    states = (
        ResearchFlowState.MEMORY_UNAVAILABLE,
        ResearchFlowState.FAILURE,
        ResearchFlowState.CORRUPTION,
        ResearchFlowState.REPLAN_REQUIRED,
    )
    bodies = tuple(
        present_transient_state(
            state,
            mode=ControllerMode.GUIDED,
            language=Language.EN,
        ).body
        for state in states
    )

    assert len(set(bodies)) == len(states)
    assert "unavailable" in bodies[0].lower()
    assert "failed" in bodies[1].lower()
    assert "integrity" in bodies[2].lower()
    assert "current data" in bodies[3].lower()


def test_route_ready_and_durable_state_without_authority_are_rejected() -> None:
    with pytest.raises(ResearchFlowPresentationError, match="unreachable"):
        present_transient_state(
            ResearchFlowState.ROUTE_READY,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
        )
    with pytest.raises(ResearchFlowPresentationError, match="durable"):
        present_transient_state(
            ResearchFlowState.CANDIDATE_READY,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
        )


def test_missing_variable_label_fails_instead_of_leaking_raw_id() -> None:
    record = _terminal_record(P1TaskProfile.LINEAR_CO_MOVEMENT)

    with pytest.raises(ResearchFlowPresentationError, match="variable label"):
        present_durable_record(
            record,
            mode=ControllerMode.STANDARD,
            language=Language.KO,
            preflight=_preflight(record),
            variable_labels={},
        )


def test_candidate_language_forbids_validity_and_authority_overclaim() -> None:
    record = _terminal_record(P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN)
    view = present_durable_record(
        record,
        mode=ControllerMode.STANDARD,
        language=Language.EN,
        preflight=_preflight(record),
        variable_labels=_labels(record),
    )
    rendered = " ".join(
        (
            view.title,
            view.body,
            view.badge_text,
            view.candidate.capability_label if view.candidate else "",
            view.candidate.method_label if view.candidate else "",
            view.candidate.claim_boundary if view.candidate else "",
            view.candidate.review_status if view.candidate else "",
            view.candidate.persistent_boundary if view.candidate else "",
        )
    ).lower()

    for forbidden in (
        "best",
        "correct",
        "expert",
        "confidence",
        "trust score",
        "validated recommendation",
        "assumptions are satisfied",
        "estimates a causal effect",
        "%",
    ):
        assert forbidden not in rendered


def test_presentation_models_are_frozen_and_reject_open_values() -> None:
    action = ResearchUiAction(ResearchUiCommand.START, "Start", True)
    option = ResearchOptionView("yes", "Yes", False, True)
    candidate = ResearchCandidateView(
        capability_label="Distribution summary",
        method_label="Descriptive table",
        claim_boundary="Sample description only",
        role_rows=(),
        review_status="Review required",
        persistent_boundary="Experimental candidate; no automatic run",
    )
    assert candidate.method_label == "Descriptive table"
    view = ResearchFlowView(
        state=ResearchFlowState.IDLE,
        mode=ControllerMode.GUIDED,
        language=Language.EN,
        title="Title",
        body="Body",
        stage_text="",
        badge_text="",
        decision_identity_digest="",
        visible_passport_digest="",
        primary_action=action,
        secondary_actions=(),
        options=(option,),
        question=None,
        candidate=None,
        evidence_rows=(),
    )

    with pytest.raises(FrozenInstanceError):
        view.title = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        ResearchUiAction("execute anything", "Run", True)  # type: ignore[arg-type]


def test_catalog_has_exact_same_keys_in_both_languages_and_no_fallback_bucket() -> None:
    assert set(RESEARCH_FLOW_STRINGS) == {"ko", "en"}
    assert set(RESEARCH_FLOW_STRINGS["ko"]) == set(RESEARCH_FLOW_STRINGS["en"])
    assert "fallback" not in RESEARCH_FLOW_STRINGS["ko"]
    with pytest.raises(TypeError):
        RESEARCH_FLOW_STRINGS["ko"]["invented"] = "open prose"  # type: ignore[index]
