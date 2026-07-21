from __future__ import annotations

from dataclasses import replace

import pytest

import modori.research_os as research_os
from modori.research_os.clarification import (
    ClarificationLifecycle,
    ClarificationRegistry,
)
from modori.research_os.contracts import (
    AssignmentMechanism,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    ContrastKind,
    DataLayout,
    DependenceKind,
    DesignFamily,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    FactState,
    Language,
    QuestionSpec,
    ResearchGoal,
    SamplingDesign,
    SchemaEnvelope,
    StudyRole,
    StudyRoleBinding,
    StudySpec,
    TargetRole,
    TargetRoleBinding,
    TemporalStructure,
    UnitKind,
)
from modori.research_os.counterfactual_planner import CounterfactualPlanner
from modori.research_os.decision_evidence import (
    AnswerValue,
    AnswerValueKind,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.passport import (
    AnalysisPassport,
    ClarifyPayload,
    ClarifyPayloadV2,
    ComponentRevisionRef,
)
from modori.research_os.resolver import PrimaryAction
from modori.research_os.service import ResearchOsService, ResearchRequest
from modori.research_os.transition import (
    ClarificationTransitionService,
    PassportMigrationRequired,
    RevisionCandidate,
    TransitionError,
)
from tests.research_os_v2_fixtures import v2_clarify_passport


DATASET_FINGERPRINT = "a" * 64
SCHEMA_FINGERPRINT = "b" * 64


def _envelope(
    schema_id: str,
    object_id: str,
    *,
    project_id: str = "project-1",
    revision: int = 1,
    supersedes_revision: int | None = None,
    created_event_ref: str | None = None,
) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id=project_id,
        object_id=object_id,
        revision=revision,
        supersedes_revision=supersedes_revision,
        created_event_ref=created_event_ref or f"event:{object_id}:{revision}",
    )


def _passport_envelope(object_id: str) -> SchemaEnvelope:
    return replace(
        _envelope("modori.analysis_passport", object_id),
        schema_version=2,
    )


def _question() -> QuestionSpec:
    return QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1"),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=Fact.user_confirmed(
            ResearchGoal.DESCRIBE,
            provenance_refs=("answer:goal:initial",),
        ),
        causal_intent=Fact.user_confirmed(
            CausalIntent.NONCAUSAL,
            provenance_refs=("answer:causal:initial",),
        ),
    )


def _estimand() -> EstimandSpec:
    return EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1"),
        template=Fact.user_confirmed(
            EstimandTemplate.SUMMARY,
            provenance_refs=("answer:template:initial",),
        ),
        claim_basis=Fact.user_confirmed(
            ClaimBasis.DESCRIPTIVE,
            provenance_refs=("answer:claim:initial",),
        ),
        target_population=Fact.user_confirmed(
            "조사 대상 표본",
            provenance_refs=("answer:population:initial",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:unit:initial",),
        ),
        target_roles=(
            TargetRoleBinding(
                role=TargetRole.OUTCOME,
                variable_ids=Fact.user_confirmed(
                    ("score",),
                    provenance_refs=("answer:outcome:initial",),
                ),
            ),
        ),
        contrast=Fact.not_applicable(reason_code="summary_has_no_contrast"),
        time_scope=Fact.user_confirmed(
            "declared_study_window",
            provenance_refs=("answer:time:initial",),
        ),
        effect_scale=Fact.user_confirmed(
            EffectScale.DISTRIBUTION,
            provenance_refs=("answer:scale:initial",),
        ),
        association_target=Fact.user_confirmed(
            AssociationTarget.NOT_APPLICABLE,
            provenance_refs=("answer:association:initial",),
        ),
    )


def _study(
    dependence: Fact[DependenceKind] | None = None,
) -> StudySpec:
    return StudySpec(
        envelope=_envelope("modori.study_spec", "study-1"),
        dataset_fingerprint=DATASET_FINGERPRINT,
        source_schema_fingerprint=SCHEMA_FINGERPRINT,
        unit_of_observation=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:observation-unit:initial",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:analysis-unit:initial",),
        ),
        design_family=Fact.user_confirmed(
            DesignFamily.OBSERVATIONAL,
            provenance_refs=("answer:design:initial",),
        ),
        data_layout=Fact.observed(
            DataLayout.UNIT_ROWS,
            provenance_refs=("profile:layout",),
        ),
        temporal_structure=Fact.user_confirmed(
            TemporalStructure.SINGLE_WAVE,
            provenance_refs=("answer:temporal:initial",),
        ),
        dependence_structure=(
            dependence
            if dependence is not None
            else Fact.user_confirmed(
                DependenceKind.INDEPENDENT,
                provenance_refs=("answer:dependence:initial",),
            )
        ),
        assignment_mechanism=Fact.user_confirmed(
            AssignmentMechanism.NONRANDOMIZED,
            provenance_refs=("answer:assignment:initial",),
        ),
        sampling_design=Fact.user_confirmed(
            SamplingDesign.CONVENIENCE,
            provenance_refs=("answer:sampling:initial",),
        ),
        design_roles=(
            StudyRoleBinding(
                role=StudyRole.WEIGHT,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-weight:initial",),
                ),
            ),
            StudyRoleBinding(
                role=StudyRole.CLUSTER,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-cluster:initial",),
                ),
            ),
        ),
        repeated_measure_order=Fact.not_applicable(
            reason_code="single_wave_has_no_repeated_order"
        ),
        missing_code_meanings=(),
    )


def _request(
    *,
    question: QuestionSpec | None = None,
    estimand: EstimandSpec | None = None,
    study: StudySpec | None = None,
    question_budget_remaining: int = 3,
) -> ResearchRequest:
    return ResearchRequest(
        question=question or _question(),
        estimand=estimand or _estimand(),
        study=study or _study(),
        current_dataset_fingerprint=DATASET_FINGERPRINT,
        available_variable_ids=(
            "score",
            "predictor",
            "group",
            "pre",
            "post",
            "weight",
            "cluster",
        ),
        question_budget_remaining=question_budget_remaining,
    )


def _component_ref(spec: QuestionSpec | EstimandSpec | StudySpec) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=spec.envelope.schema_id,
        object_id=spec.envelope.object_id,
        revision=spec.envelope.revision,
        digest=spec.digest(),
    )


def _legacy_clarify_passport(
    request: ResearchRequest,
    question_id: str,
) -> AnalysisPassport:
    registry = build_p1_clarification_registry()
    question = registry.get(question_id)
    method_space = build_p1_method_space()
    return AnalysisPassport(
        envelope=_envelope("modori.analysis_passport", "passport-1"),
        question_ref=_component_ref(request.question),
        estimand_ref=_component_ref(request.estimand),
        study_ref=_component_ref(request.study),
        dataset_fingerprint=request.current_dataset_fingerprint,
        method_space_version=method_space.version,
        method_space_digest=method_space.digest(),
        ruleset_version=method_space.ruleset_version,
        resolver_decision_digest="c" * 64,
        decision_evidence_digests=tuple(
            reference.evidence_digest
            for reference in request.decision_evidence_refs
        ),
        clarify=ClarifyPayload(
            question_ids=(question_id,),
            blocking_fact_addresses=(question.fact_address,),
        ),
    )


def _clarify_passport(
    request: ResearchRequest,
    question_id: str,
) -> AnalysisPassport:
    return v2_clarify_passport(request, question_id)


def _answer_for_passport(
    request: ResearchRequest,
    passport: AnalysisPassport,
    value: AnswerValue,
    *,
    event_sequence: int = 1,
) -> research_os.ClarificationAnswerEvent:
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    reference = passport.clarify.clarification_ref
    return research_os.ClarificationAnswerEvent(
        event_id=f"answer:{reference.question_id}:{event_sequence}",
        project_id=request.question.envelope.project_id,
        event_sequence=event_sequence,
        source_passport_digest=passport.digest(),
        question_id=reference.question_id,
        question_version=reference.question_version,
        question_digest=reference.question_digest,
        fact_address=reference.fact_address,
        answer_value=value,
    )


def _answer(
    request: ResearchRequest,
    question_id: str,
    value: AnswerValue,
    *,
    event_sequence: int = 1,
) -> research_os.ClarificationAnswerEvent:
    passport = _clarify_passport(request, question_id)
    return _answer_for_passport(
        request,
        passport,
        value,
        event_sequence=event_sequence,
    )


def _registry_with_revised_question(question_id: str) -> ClarificationRegistry:
    registry = build_p1_clarification_registry()
    return ClarificationRegistry(
        questions=tuple(
            replace(question, version=question.version + 1)
            if question.question_id == question_id
            else question
            for question in registry.questions
        ),
        required_question_ids=registry.required_question_ids,
    )


def _choice(value: str) -> AnswerValue:
    return AnswerValue(kind=AnswerValueKind.CHOICE, choice_value=value)


def _variables(*variable_ids: str) -> AnswerValue:
    return AnswerValue(
        kind=AnswerValueKind.VARIABLES,
        variable_ids=variable_ids,
    )


def _all_mapping_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for item in value.values() for key in _all_mapping_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _all_mapping_keys(item)}
    return set()


def _candidate_fact(candidate: RevisionCandidate, fact_address: str) -> Fact[object]:
    if fact_address == "question.research_goal":
        assert candidate.proposed_question is not None
        return candidate.proposed_question.research_goal
    if fact_address == "question.causal_intent":
        assert candidate.proposed_question is not None
        return candidate.proposed_question.causal_intent
    if fact_address.startswith("estimand.role."):
        assert candidate.proposed_estimand is not None
        role = TargetRole(fact_address.rsplit(".", 1)[-1])
        return next(
            binding.variable_ids
            for binding in candidate.proposed_estimand.target_roles
            if binding.role is role
        )
    if fact_address.startswith("estimand."):
        assert candidate.proposed_estimand is not None
        return getattr(candidate.proposed_estimand, fact_address.split(".", 1)[1])
    if fact_address.startswith("study.role."):
        assert candidate.proposed_study is not None
        role = StudyRole(fact_address.rsplit(".", 1)[-1])
        return next(
            binding.variable_ids
            for binding in candidate.proposed_study.design_roles
            if binding.role is role
        )
    assert candidate.proposed_study is not None
    return getattr(candidate.proposed_study, fact_address.split(".", 1)[1])


def test_v1_answer_requires_fresh_replan_before_candidate_construction() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _legacy_clarify_passport(request, "confirm_dependence")
    question = build_p1_clarification_registry().get("confirm_dependence")
    answer = research_os.ClarificationAnswerEvent(
        event_id="answer:confirm_dependence:1",
        project_id=request.question.envelope.project_id,
        event_sequence=1,
        source_passport_digest=passport.digest(),
        question_id=question.question_id,
        question_version=question.version,
        question_digest=question.digest(),
        fact_address=question.fact_address,
        answer_value=_choice("independent"),
    )

    with pytest.raises(PassportMigrationRequired):
        ClarificationTransitionService().propose(request, passport, answer)


def test_v2_transition_rejects_request_registry_and_answer_identity_drift() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _clarify_passport(request, "confirm_dependence")
    answer = _answer_for_passport(request, passport, _choice("independent"))

    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            replace(request, question_budget_remaining=2),
            passport,
            answer,
        )
    with pytest.raises(TransitionError):
        ClarificationTransitionService(
            _registry_with_revised_question("confirm_dependence")
        ).propose(request, passport, answer)
    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, question_version=answer.question_version + 1),
        )
    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, question_digest="f" * 64),
        )
    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, question_id="confirm_weight_use"),
        )
    with pytest.raises(TransitionError):
        ClarificationTransitionService().propose(
            request,
            passport,
            replace(answer, fact_address="study.role.weight"),
        )


def test_v2_transition_never_runs_a_second_planner_search(monkeypatch) -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _clarify_passport(request, "confirm_dependence")
    answer = _answer_for_passport(request, passport, _choice("independent"))

    def fail_second_search(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("second planner search")

    monkeypatch.setattr(CounterfactualPlanner, "plan", fail_second_search)

    assert isinstance(
        ClarificationTransitionService().propose(request, passport, answer),
        RevisionCandidate,
    )


def test_budget_zero_rejects_a_passport_issued_while_one_question_remained() -> None:
    issued_request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed")),
        question_budget_remaining=1,
    )
    passport = _clarify_passport(issued_request, "confirm_dependence")
    answer = _answer_for_passport(
        issued_request,
        passport,
        _choice("independent"),
    )

    with pytest.raises(TransitionError, match="budget is exhausted"):
        ClarificationTransitionService().propose(
            replace(issued_request, question_budget_remaining=0),
            passport,
            answer,
        )


@pytest.mark.parametrize(
    ("question_id", "answer_value", "expected_state", "expected_value"),
    [
        (
            "confirm_association_target",
            _choice("not_applicable"),
            FactState.USER_CONFIRMED,
            AssociationTarget.NOT_APPLICABLE,
        ),
        (
            "confirm_causal_intent",
            _choice("causal"),
            FactState.USER_CONFIRMED,
            CausalIntent.CAUSAL,
        ),
        (
            "confirm_claim_basis",
            _choice("descriptive"),
            FactState.USER_CONFIRMED,
            ClaimBasis.DESCRIPTIVE,
        ),
        ("confirm_cluster_use", _variables(), FactState.USER_CONFIRMED, ()),
        (
            "confirm_contrast",
            _choice("not_applicable"),
            FactState.USER_CONFIRMED,
            ContrastKind.NOT_APPLICABLE,
        ),
        (
            "confirm_dependence",
            _choice("independent"),
            FactState.USER_CONFIRMED,
            DependenceKind.INDEPENDENT,
        ),
        (
            "confirm_effect_scale",
            _choice("distribution"),
            FactState.USER_CONFIRMED,
            EffectScale.DISTRIBUTION,
        ),
        (
            "confirm_estimand_template",
            _choice("summary"),
            FactState.USER_CONFIRMED,
            EstimandTemplate.SUMMARY,
        ),
        (
            "confirm_focal_predictor_role",
            _variables("predictor"),
            FactState.USER_CONFIRMED,
            ("predictor",),
        ),
        (
            "confirm_group_role",
            _variables("group"),
            FactState.USER_CONFIRMED,
            ("group",),
        ),
        (
            "confirm_outcome_role",
            _variables("score"),
            FactState.USER_CONFIRMED,
            ("score",),
        ),
        (
            "confirm_repeated_measure_order",
            _variables("pre", "post"),
            FactState.USER_CONFIRMED,
            ("pre", "post"),
        ),
        (
            "confirm_repeated_measure_role",
            _variables(),
            FactState.NOT_APPLICABLE,
            None,
        ),
        (
            "confirm_research_goal",
            _choice("compare"),
            FactState.USER_CONFIRMED,
            ResearchGoal.COMPARE,
        ),
        ("confirm_weight_use", _variables(), FactState.USER_CONFIRMED, ()),
    ],
)
def test_every_p1_question_maps_to_its_exact_fact(
    question_id: str,
    answer_value: AnswerValue,
    expected_state: FactState,
    expected_value: object,
) -> None:
    request = _request()
    registry_question = build_p1_clarification_registry().get(question_id)
    answer = _answer(request, question_id, answer_value)
    needs_acceptance = not registry_question.fact_address.startswith("study.")
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, question_id),
        answer,
        acceptance_certificate_id=(
            f"acceptance:{question_id}:1" if needs_acceptance else None
        ),
    )
    fact = _candidate_fact(candidate, registry_question.fact_address)

    assert fact.state is expected_state
    assert fact.value == expected_value
    if expected_state is FactState.USER_CONFIRMED:
        assert fact.provenance_refs == (answer.event_id,)
    else:
        assert fact.reason_code == "user_confirmed_no_repeated_measure_role"


def test_answer_cannot_apply_to_a_different_passport_digest() -> None:
    request = _request()
    passport = _clarify_passport(request, "confirm_dependence")
    answer = replace(
        _answer(request, "confirm_dependence", _choice("independent")),
        source_passport_digest="f" * 64,
    )

    with pytest.raises(TransitionError, match="source passport digest"):
        ClarificationTransitionService().propose(request, passport, answer)


def test_answer_cannot_apply_after_component_revision_changes() -> None:
    request = _request()
    passport = _clarify_passport(request, "confirm_dependence")
    answer = _answer(request, "confirm_dependence", _choice("independent"))
    newer_question = replace(
        request.question,
        envelope=_envelope(
            "modori.question_spec",
            "question-1",
            revision=2,
            supersedes_revision=1,
        ),
    )

    with pytest.raises(TransitionError, match="component revision"):
        ClarificationTransitionService().propose(
            replace(request, question=newer_question),
            passport,
            answer,
        )


def test_answer_requires_all_source_components_in_one_project() -> None:
    request = _request()
    mismatched = replace(
        request,
        estimand=replace(
            request.estimand,
            envelope=replace(
                request.estimand.envelope,
                project_id="project-2",
            ),
        ),
    )

    with pytest.raises(TransitionError, match="component project IDs"):
        ClarificationTransitionService().propose(
            mismatched,
            _clarify_passport(mismatched, "confirm_dependence"),
            _answer(mismatched, "confirm_dependence", _choice("independent")),
        )


def test_answer_variable_must_exist_in_exact_request_snapshot() -> None:
    request = _request()
    passport = _clarify_passport(request, "confirm_outcome_role")
    answer = _answer(
        request,
        "confirm_outcome_role",
        _variables("substituted"),
    )

    with pytest.raises(TransitionError, match="unknown variable"):
        ClarificationTransitionService().propose(
            request,
            passport,
            answer,
            acceptance_certificate_id="acceptance:outcome:1",
        )


def test_withdrawn_question_cannot_validate_an_answer() -> None:
    request = _request()
    source_registry = build_p1_clarification_registry()
    questions = tuple(
        replace(question, lifecycle=ClarificationLifecycle.WITHDRAWN)
        if question.question_id == "confirm_dependence"
        else question
        for question in source_registry.questions
    )
    registry = ClarificationRegistry(
        questions=questions,
        required_question_ids=source_registry.required_question_ids,
    )

    with pytest.raises(TransitionError, match="registry"):
        ClarificationTransitionService(registry).propose(
            request,
            _clarify_passport(request, "confirm_dependence"),
            _answer(request, "confirm_dependence", _choice("independent")),
        )


def test_estimand_candidate_requires_reserved_acceptance_id() -> None:
    request = _request()
    passport = _clarify_passport(request, "confirm_effect_scale")
    answer = _answer(
        request,
        "confirm_effect_scale",
        _choice("distribution"),
    )

    with pytest.raises(TransitionError, match="acceptance_certificate_id"):
        ClarificationTransitionService().propose(request, passport, answer)

    candidate = ClarificationTransitionService().propose(
        request,
        passport,
        answer,
        acceptance_certificate_id="acceptance:effect-scale:1",
    )
    assert candidate.requires_acceptance is True
    assert candidate.proposed_estimand is not None
    assert candidate.proposed_estimand.envelope.revision == 2
    assert (
        candidate.proposed_estimand.envelope.created_event_ref
        == "acceptance:effect-scale:1"
    )


def test_study_candidate_is_ready_and_uses_answer_event_reference() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _clarify_passport(request, "confirm_dependence")
    answer = _answer(request, "confirm_dependence", _choice("independent"))

    candidate = ClarificationTransitionService().propose(request, passport, answer)

    assert candidate.requires_acceptance is False
    assert candidate.proposed_study is not None
    assert candidate.proposed_study.envelope.created_event_ref == answer.event_id
    assert candidate.proposed_study.dependence_structure.value is DependenceKind.INDEPENDENT


def test_candidate_is_deterministic_and_does_not_mutate_source() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    passport = _clarify_passport(request, "confirm_dependence")
    answer = _answer(request, "confirm_dependence", _choice("independent"))
    before = (
        request.question.digest(),
        request.estimand.digest(),
        request.study.digest(),
    )

    left = ClarificationTransitionService().propose(request, passport, answer)
    right = ClarificationTransitionService().propose(request, passport, answer)

    assert isinstance(left, RevisionCandidate)
    assert left == right
    assert left.digest() == right.digest()
    assert before == (
        request.question.digest(),
        request.estimand.digest(),
        request.study.digest(),
    )


def test_manually_forged_candidate_revision_or_event_ref_is_rejected() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_dependence"),
        _answer(request, "confirm_dependence", _choice("independent")),
    )
    assert candidate.proposed_study is not None

    with pytest.raises(TransitionError, match="exact next revision"):
        replace(
            candidate,
            proposed_study=replace(
                candidate.proposed_study,
                envelope=_envelope(
                    "modori.study_spec",
                    "study-1",
                    revision=3,
                    supersedes_revision=1,
                    created_event_ref=candidate.answer_event_id,
                ),
            ),
        )
    with pytest.raises(TransitionError, match="created_event_ref"):
        replace(
            candidate,
            proposed_study=replace(
                candidate.proposed_study,
                envelope=replace(
                    candidate.proposed_study.envelope,
                    created_event_ref="answer:forged:99",
                ),
            ),
        )


def test_variable_cardinality_is_fact_specific() -> None:
    request = _request()
    service = ClarificationTransitionService()

    with pytest.raises(TransitionError, match="exactly one variable"):
        service.propose(
            request,
            _clarify_passport(request, "confirm_outcome_role"),
            _answer(request, "confirm_outcome_role", _variables("score", "post")),
            acceptance_certificate_id="acceptance:outcome:1",
        )
    with pytest.raises(TransitionError, match="zero or at least two"):
        service.propose(
            request,
            _clarify_passport(request, "confirm_repeated_measure_role"),
            _answer(request, "confirm_repeated_measure_role", _variables("pre")),
            acceptance_certificate_id="acceptance:repeated-role:1",
        )
    with pytest.raises(TransitionError, match="at least two variables"):
        service.propose(
            request,
            _clarify_passport(request, "confirm_repeated_measure_order"),
            _answer(request, "confirm_repeated_measure_order", _variables("pre")),
        )


def test_goal_change_stales_estimand_dependents_and_preserves_snapshots() -> None:
    request = _request()
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_research_goal"),
        _answer(request, "confirm_research_goal", _choice("compare")),
        acceptance_certificate_id="acceptance:goal:1",
    )
    proposed = candidate.proposed_estimand

    assert proposed is not None
    assert proposed.template.state is FactState.STALE
    assert proposed.template.stale_snapshot is not None
    assert proposed.template.stale_snapshot.value is request.estimand.template.value
    assert proposed.template.stale_snapshot.provenance_refs == (
        request.estimand.template.provenance_refs
    )
    assert all(
        binding.variable_ids.state is FactState.STALE
        for binding in proposed.target_roles
    )
    assert request.estimand.template.state is FactState.USER_CONFIRMED


def test_same_goal_reconfirmation_does_not_stale_unchanged_estimand() -> None:
    request = _request()
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_research_goal"),
        _answer(request, "confirm_research_goal", _choice("describe")),
    )

    assert candidate.requires_acceptance is False
    assert candidate.proposed_question is not None
    assert candidate.proposed_estimand is None
    assert request.estimand.template.state is FactState.USER_CONFIRMED


def test_same_template_reconfirmation_preserves_dependent_facts() -> None:
    request = _request()
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_estimand_template"),
        _answer(request, "confirm_estimand_template", _choice("summary")),
        acceptance_certificate_id="acceptance:template:1",
    )

    assert candidate.proposed_estimand is not None
    assert candidate.proposed_estimand.claim_basis == request.estimand.claim_basis
    assert candidate.proposed_estimand.target_roles == request.estimand.target_roles
    assert candidate.proposed_estimand.effect_scale == request.estimand.effect_scale


def test_not_sure_creates_unknown_and_never_a_default() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed")),
        question_budget_remaining=1,
    )
    answer = _answer(
        request,
        "confirm_dependence",
        AnswerValue(kind=AnswerValueKind.NOT_SURE),
    )
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_dependence"),
        answer,
    )

    assert candidate.proposed_study is not None
    assert candidate.proposed_study.dependence_structure.state is FactState.UNKNOWN
    assert candidate.proposed_study.dependence_structure.value is None
    assert candidate.next_question_budget_remaining == 0

    committed = ClarificationTransitionService().commit_ready(request, candidate)
    decision = ResearchOsService().resolve(committed)
    assert decision.action is PrimaryAction.ABSTAIN
    assert decision.reason_codes == ("clarification_budget_exhausted",)


def test_not_sure_answer_never_repeats_the_same_question() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed")),
        question_budget_remaining=3,
    )
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    passport = service.plan(
        request,
        _passport_envelope("passport-not-sure-1"),
    )
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    refused_id = passport.clarify.clarification_ref.question_id
    answer = replace(
        _answer(
            request,
            refused_id,
            AnswerValue(kind=AnswerValueKind.NOT_SURE),
        ),
        source_passport_digest=passport.digest(),
    )
    candidate = transition.propose(request, passport, answer)

    revised = transition.commit_ready(request, candidate)
    second = service.resolve(revised)

    assert refused_id not in second.clarification_ids
    assert second.action is PrimaryAction.ABSTAIN
    assert second.reason_codes == ("clarification_answer_unavailable",)
    assert revised.question_budget_remaining == 2
    second_passport = service.plan(
        revised,
        _passport_envelope("passport-not-sure-2"),
    )
    assert second_passport.abstain is not None
    assert second_passport.abstain.recovery_requirement_ids == (
        "complete_structured_intake_or_revise_scope",
    )


def test_three_refusal_rounds_are_finite_budgeted_and_never_repeat() -> None:
    request = _request(
        study=replace(
            _study(Fact.unknown(reason_code="dependence_not_confirmed")),
            design_roles=(),
        ),
        question_budget_remaining=3,
    )
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    current = request
    seen_questions: set[str] = set()
    seen_states = {
        (
            current.question.digest(),
            current.estimand.digest(),
            current.study.digest(),
            current.question_budget_remaining,
        )
    }
    budgets = [current.question_budget_remaining]

    for sequence in (1, 2, 3):
        passport = service.plan(
            current,
            _passport_envelope(f"passport-refusal-{sequence}"),
        )
        assert isinstance(passport.clarify, ClarifyPayloadV2)
        question_id = passport.clarify.clarification_ref.question_id
        assert question_id not in seen_questions
        seen_questions.add(question_id)
        answer = replace(
            _answer(
                current,
                question_id,
                AnswerValue(kind=AnswerValueKind.NOT_SURE),
                event_sequence=sequence,
            ),
            source_passport_digest=passport.digest(),
        )
        candidate = transition.propose(current, passport, answer)
        current = transition.commit_ready(current, candidate)
        state = (
            current.question.digest(),
            current.estimand.digest(),
            current.study.digest(),
            current.question_budget_remaining,
        )
        assert state not in seen_states
        seen_states.add(state)
        budgets.append(current.question_budget_remaining)

    final = service.resolve(current)

    assert budgets == [3, 2, 1, 0]
    assert seen_questions == {
        "confirm_cluster_use",
        "confirm_dependence",
        "confirm_weight_use",
    }
    assert final.action is PrimaryAction.ABSTAIN
    assert final.reason_codes == ("clarification_budget_exhausted",)


def test_replayed_or_nonmonotonic_answer_event_is_rejected() -> None:
    base = _request()
    replayed_answer = _answer(
        base,
        "confirm_dependence",
        _choice("independent"),
        event_sequence=2,
    )
    used = DecisionEvidenceRef(
        evidence_id=replayed_answer.event_id,
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=1,
        evidence_digest="d" * 64,
        subject_digests=("e" * 64,),
    )
    replay_request = replace(base, decision_evidence_refs=(used,))

    with pytest.raises(TransitionError, match="already been used"):
        ClarificationTransitionService().propose(
            replay_request,
            _clarify_passport(replay_request, "confirm_dependence"),
            replace(
                replayed_answer,
                source_passport_digest=_clarify_passport(
                    replay_request,
                    "confirm_dependence",
                ).digest(),
            ),
        )

    prior = replace(used, evidence_id="answer:prior:2", event_sequence=2)
    ordered_request = replace(base, decision_evidence_refs=(prior,))
    late_required = _answer(
        ordered_request,
        "confirm_dependence",
        _choice("independent"),
        event_sequence=2,
    )
    with pytest.raises(TransitionError, match="later than existing evidence"):
        ClarificationTransitionService().propose(
            ordered_request,
            _clarify_passport(ordered_request, "confirm_dependence"),
            late_required,
        )


def test_reserved_acceptance_id_cannot_reuse_existing_evidence_id() -> None:
    prior = DecisionEvidenceRef(
        evidence_id="acceptance:effect-scale:1",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.REVISION_ACCEPTANCE,
        event_sequence=1,
        evidence_digest="d" * 64,
        subject_digests=("e" * 64,),
    )
    request = replace(_request(), decision_evidence_refs=(prior,))

    with pytest.raises(TransitionError, match="acceptance certificate ID.*used"):
        ClarificationTransitionService().propose(
            request,
            _clarify_passport(request, "confirm_effect_scale"),
            _answer(
                request,
                "confirm_effect_scale",
                _choice("distribution"),
                event_sequence=2,
            ),
            acceptance_certificate_id="acceptance:effect-scale:1",
        )


def test_answer_cannot_use_passport_with_omitted_decision_evidence() -> None:
    prior = DecisionEvidenceRef(
        evidence_id="answer:prior:1",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=1,
        evidence_digest="d" * 64,
        subject_digests=("e" * 64,),
    )
    request = replace(_request(), decision_evidence_refs=(prior,))
    proper = _clarify_passport(request, "confirm_dependence")
    tampered = replace(proper, decision_evidence_digests=())
    answer = replace(
        _answer(
            request,
            "confirm_dependence",
            _choice("independent"),
            event_sequence=2,
        ),
        source_passport_digest=tampered.digest(),
    )

    with pytest.raises(TransitionError, match="decision evidence"):
        ClarificationTransitionService().propose(request, tampered, answer)


def test_candidate_cannot_commit_after_decision_evidence_changes() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        _clarify_passport(request, "confirm_dependence"),
        _answer(request, "confirm_dependence", _choice("independent")),
    )
    new_evidence = DecisionEvidenceRef(
        evidence_id="answer:other:1",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=1,
        evidence_digest="d" * 64,
        subject_digests=("e" * 64,),
    )

    with pytest.raises(TransitionError, match="base decision evidence is stale"):
        transition.commit_ready(
            replace(request, decision_evidence_refs=(new_evidence,)),
            candidate,
        )


def test_ready_commit_appends_answer_evidence_and_freshly_resolves() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        _clarify_passport(request, "confirm_dependence"),
        _answer(request, "confirm_dependence", _choice("independent")),
    )

    committed = transition.commit_ready(request, candidate)
    decision = ResearchOsService().resolve(committed)

    assert committed is not request
    assert committed.study is candidate.proposed_study
    assert committed.question_budget_remaining == 2
    assert len(committed.decision_evidence_refs) == 1
    assert (
        committed.decision_evidence_refs[0].evidence_kind
        is DecisionEvidenceKind.CLARIFICATION_ANSWER
    )
    assert decision.action is PrimaryAction.RECOMMEND_LOCAL


def test_estimand_bundle_cannot_commit_without_matching_acceptance() -> None:
    request = _request()
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        _clarify_passport(request, "confirm_effect_scale"),
        _answer(request, "confirm_effect_scale", _choice("distribution")),
        acceptance_certificate_id="acceptance:effect-scale:1",
    )

    with pytest.raises(TransitionError, match="requires acceptance"):
        transition.commit_ready(request, candidate)

    certificate = transition.build_acceptance_certificate(
        candidate,
        event_sequence=2,
    )
    committed = transition.commit_accepted(request, candidate, certificate)

    assert committed.estimand is candidate.proposed_estimand
    assert len(committed.decision_evidence_refs) == 2
    assert committed.decision_evidence_refs[-1].evidence_kind is (
        DecisionEvidenceKind.REVISION_ACCEPTANCE
    )


def test_accepted_goal_change_must_freshly_clarify_staled_estimand() -> None:
    request = _request()
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        _clarify_passport(request, "confirm_research_goal"),
        _answer(request, "confirm_research_goal", _choice("compare")),
        acceptance_certificate_id="acceptance:goal:1",
    )
    certificate = transition.build_acceptance_certificate(
        candidate,
        event_sequence=2,
    )

    committed = transition.commit_accepted(request, candidate, certificate)
    decision = ResearchOsService().resolve(committed)

    assert decision.action is PrimaryAction.CLARIFY
    assert decision.capability_keys == ()
    assert decision.clarification_ids
    assert committed.estimand.template.state is FactState.STALE
    assert set(decision.clarification_ids).issubset(
        {
            "confirm_estimand_template",
            "confirm_claim_basis",
            "confirm_effect_scale",
            "confirm_association_target",
            "confirm_contrast",
            "confirm_outcome_role",
            "confirm_focal_predictor_role",
            "confirm_group_role",
            "confirm_repeated_measure_role",
        }
    )


def test_candidate_mapping_carries_no_execution_authority() -> None:
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    candidate = ClarificationTransitionService().propose(
        request,
        _clarify_passport(request, "confirm_dependence"),
        _answer(request, "confirm_dependence", _choice("independent")),
    )
    forbidden = {
        "command",
        "worker_token",
        "path",
        "url",
        "execute",
        "pipeline_mutation",
        "dataset",
        "dataframe",
    }

    assert _all_mapping_keys(candidate.to_mapping()).isdisjoint(forbidden)


def test_acceptance_sequence_and_candidate_digest_attacks_fail_closed() -> None:
    request = _request()
    transition = ClarificationTransitionService()
    candidate = transition.propose(
        request,
        _clarify_passport(request, "confirm_claim_basis"),
        _answer(
            request,
            "confirm_claim_basis",
            _choice("descriptive"),
            event_sequence=4,
        ),
        acceptance_certificate_id="acceptance:claim:1",
    )

    with pytest.raises(TransitionError, match="later than answer"):
        transition.build_acceptance_certificate(candidate, event_sequence=4)

    certificate = transition.build_acceptance_certificate(
        candidate,
        event_sequence=5,
    )
    with pytest.raises(TransitionError, match="candidate digest"):
        transition.commit_accepted(
            request,
            candidate,
            replace(certificate, candidate_digest="f" * 64),
        )
    with pytest.raises(TransitionError, match="component digest"):
        transition.commit_accepted(
            request,
            candidate,
            replace(certificate, accepted_component_digests=("f" * 64,)),
        )


def test_transition_service_is_exposed_without_execution_authority() -> None:
    assert research_os.ClarificationTransitionService is ClarificationTransitionService
    assert research_os.PassportMigrationRequired is PassportMigrationRequired
    assert (
        ClarificationTransitionService().clarification_registry_digest
        == build_p1_clarification_registry().digest()
    )
    assert callable(ClarificationTransitionService.propose)
    assert not hasattr(ClarificationTransitionService, "execute")
    assert not hasattr(ClarificationTransitionService, "save")
