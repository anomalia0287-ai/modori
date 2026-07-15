from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest

import modori.research_os as research_os
from modori.research_os.contracts import (
    AssignmentMechanism,
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    DataLayout,
    DependenceKind,
    DesignFamily,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
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
from modori.research_os.method_space import (
    ExternalRoute,
    LifecycleStatus,
    MethodSpace,
    RecommendationEvidence,
    RouteEvidence,
    SupportStatus,
)
from modori.research_os.decision_evidence import (
    DecisionEvidenceKind,
    DecisionEvidenceRef,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.passport import ClaimClass, ClarifyPayloadV2
from modori.research_os.resolver import (
    PrimaryAction,
    ResolverError,
)
from modori.research_os.service import (
    ResolvedPassport,
    ResearchOsService,
    ResearchRequest,
    ResearchServiceError,
    validate_passport_request_binding,
)


DATASET_FINGERPRINT = "a" * 64
SCHEMA_FINGERPRINT = "b" * 64
SUMMARY_KEY = (
    "descriptive_summary:unweighted_summary:summary:"
    "independent_unweighted:roles-v1"
)


def _envelope(
    schema_id: str,
    object_id: str,
    project_id: str = "project-1",
) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id=project_id,
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:{object_id}:1",
    )


def _passport_envelope(
    project_id: str = "project-1",
    *,
    version: int = 2,
) -> SchemaEnvelope:
    return replace(
        _envelope("modori.analysis_passport", "passport-1", project_id),
        schema_version=version,
    )


def _question(
    *,
    causal_intent: CausalIntent = CausalIntent.NONCAUSAL,
    project_id: str = "project-1",
) -> QuestionSpec:
    return QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1", project_id),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=Fact.user_confirmed(
            ResearchGoal.DESCRIBE,
            provenance_refs=("answer:goal",),
        ),
        causal_intent=Fact.user_confirmed(
            causal_intent,
            provenance_refs=("answer:causal",),
        ),
    )


def _estimand(project_id: str = "project-1") -> EstimandSpec:
    return EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1", project_id),
        template=Fact.user_confirmed(
            EstimandTemplate.SUMMARY,
            provenance_refs=("answer:template",),
        ),
        claim_basis=Fact.user_confirmed(
            ClaimBasis.DESCRIPTIVE,
            provenance_refs=("answer:claim",),
        ),
        target_population=Fact.user_confirmed(
            "조사 대상 표본",
            provenance_refs=("answer:population",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:unit",),
        ),
        target_roles=(
            TargetRoleBinding(
                role=TargetRole.OUTCOME,
                variable_ids=Fact.user_confirmed(
                    ("score",),
                    provenance_refs=("answer:outcome",),
                ),
            ),
        ),
        contrast=Fact.not_applicable(reason_code="summary_has_no_contrast"),
        time_scope=Fact.user_confirmed(
            "declared_study_window",
            provenance_refs=("answer:time",),
        ),
        effect_scale=Fact.user_confirmed(
            EffectScale.DISTRIBUTION,
            provenance_refs=("answer:scale",),
        ),
        association_target=Fact.user_confirmed(
            AssociationTarget.NOT_APPLICABLE,
            provenance_refs=("answer:not-association",),
        ),
    )


def _study(
    dependence: Fact[DependenceKind] | None = None,
    *,
    project_id: str = "project-1",
) -> StudySpec:
    return StudySpec(
        envelope=_envelope("modori.study_spec", "study-1", project_id),
        dataset_fingerprint=DATASET_FINGERPRINT,
        source_schema_fingerprint=SCHEMA_FINGERPRINT,
        unit_of_observation=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:observation-unit",),
        ),
        unit_of_analysis=Fact.user_confirmed(
            UnitKind.PERSON,
            provenance_refs=("answer:analysis-unit",),
        ),
        design_family=Fact.user_confirmed(
            DesignFamily.OBSERVATIONAL,
            provenance_refs=("answer:design",),
        ),
        data_layout=Fact.observed(
            DataLayout.UNIT_ROWS,
            provenance_refs=("profile:layout",),
        ),
        temporal_structure=Fact.user_confirmed(
            TemporalStructure.SINGLE_WAVE,
            provenance_refs=("answer:temporal",),
        ),
        dependence_structure=(
            dependence
            if dependence is not None
            else Fact.user_confirmed(
                DependenceKind.INDEPENDENT,
                provenance_refs=("answer:dependence",),
            )
        ),
        assignment_mechanism=Fact.user_confirmed(
            AssignmentMechanism.NONRANDOMIZED,
            provenance_refs=("answer:assignment",),
        ),
        sampling_design=Fact.user_confirmed(
            SamplingDesign.CONVENIENCE,
            provenance_refs=("answer:sampling",),
        ),
        design_roles=(
            StudyRoleBinding(
                role=StudyRole.WEIGHT,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-weight",),
                ),
            ),
            StudyRoleBinding(
                role=StudyRole.CLUSTER,
                variable_ids=Fact.user_confirmed(
                    (),
                    provenance_refs=("answer:no-cluster",),
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
    current_fingerprint: str = DATASET_FINGERPRINT,
) -> ResearchRequest:
    return ResearchRequest(
        question=question or _question(),
        estimand=estimand or _estimand(),
        study=study or _study(),
        current_dataset_fingerprint=current_fingerprint,
        available_variable_ids=("score",),
    )


def _external_route_method_space() -> MethodSpace:
    base = build_p1_method_space()
    target = next(
        capability
        for capability in base.capabilities
        if capability.identity.key == SUMMARY_KEY
    )
    capabilities = tuple(
        replace(
            capability,
            support=SupportStatus.GUIDED_EXTERNAL,
            recommendation_evidence=RecommendationEvidence.VALIDATED,
            lifecycle=LifecycleStatus.RELEASED,
            local_analysis_kind=None,
        )
        if capability.identity.key == SUMMARY_KEY
        else capability
        for capability in base.capabilities
    )
    route = ExternalRoute(
        route_id="route.summary.external",
        capability_key=SUMMARY_KEY,
        recommendation_evidence=RecommendationEvidence.VALIDATED,
        route_evidence=RouteEvidence.ROUNDTRIP_VERIFIED,
        lifecycle=LifecycleStatus.RELEASED,
        resource_id="resource.summary.external",
        privacy_boundary="manual_export_only",
        rule_ids=target.rule_ids,
        source_refs=("source:test-verified-route",),
    )
    return MethodSpace(
        version="research-os-route-test-v1",
        ruleset_version=base.ruleset_version,
        capabilities=capabilities,
        rules=base.rules,
        routes=(route,),
    )


def test_plan_binds_exact_component_revisions_and_method_space() -> None:
    service = ResearchOsService()
    request = _request()

    with patch.object(service, "resolve", wraps=service.resolve) as resolve:
        passport = service.plan(request, _passport_envelope())

    resolve.assert_called_once_with(request)
    assert passport.action is PrimaryAction.RECOMMEND_LOCAL
    assert passport.question_ref.object_id == request.question.envelope.object_id
    assert passport.question_ref.revision == request.question.envelope.revision
    assert passport.question_ref.digest == request.question.digest()
    assert passport.estimand_ref.digest == request.estimand.digest()
    assert passport.study_ref.digest == request.study.digest()
    assert passport.dataset_fingerprint == request.current_dataset_fingerprint
    assert passport.method_space_version == service.method_space_version
    assert passport.method_space_digest == service.method_space_digest
    assert passport.ruleset_version == service.ruleset_version


def test_recommend_plan_copies_only_stable_metadata_and_claim_boundary() -> None:
    passport = ResearchOsService().plan(_request(), _passport_envelope())

    assert passport.recommend_local is not None
    assert passport.recommend_local.capability_keys == (SUMMARY_KEY,)
    assert passport.recommend_local.local_analysis_kinds == ("descriptives",)
    assert passport.recommend_local.claim_permissions == (
        ClaimClass.SAMPLE_DESCRIPTION,
    )
    assert passport.recommend_local.experimental is True
    assert passport.recommend_local.auto_selected is False
    assert passport.recommend_local.requires_explicit_configure_confirm_run is True


def test_clarify_plan_resolves_exact_registered_questions_without_candidates() -> None:
    service = ResearchOsService()
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )

    passport = service.plan(request, _passport_envelope())
    decision = service.resolve(request)
    questions = service.clarifications_for(decision)

    assert passport.action is PrimaryAction.CLARIFY
    assert passport.recommend_local is None
    assert isinstance(passport.clarify, ClarifyPayloadV2)
    assert passport.clarify.clarification_ref.question_id == (
        decision.clarification_ids[0]
    )
    assert tuple(question.question_id for question in questions) == decision.clarification_ids
    assert tuple(question.fact_address for question in questions) == (
        decision.blocking_fact_addresses
    )


def test_resolve_and_plan_returns_one_decision_and_matching_v2_passport() -> None:
    service = ResearchOsService()
    request = _request(
        study=_study(Fact.unknown(reason_code="dependence_not_confirmed"))
    )
    with patch.object(service, "resolve", wraps=service.resolve) as resolve:
        result = service.resolve_and_plan(request, _passport_envelope(version=2))

    resolve.assert_called_once_with(request)
    assert result.passport.envelope.schema_version == 2
    assert result.passport.request_binding_digest == request.request_binding_digest()
    assert (
        result.passport.clarification_registry_digest
        == service.clarification_registry_digest
    )
    assert result.decision.clarification_plan is not None
    assert isinstance(result.passport.clarify, ClarifyPayloadV2)
    assert result.passport.clarify.clarification_plan == (
        result.decision.clarification_plan
    )


def test_plan_delegates_to_resolve_and_plan_without_second_resolution() -> None:
    service = ResearchOsService()
    request = _request()
    with patch.object(
        service,
        "resolve_and_plan",
        wraps=service.resolve_and_plan,
    ) as combined:
        passport = service.plan(request, _passport_envelope(version=2))

    combined.assert_called_once_with(request, _passport_envelope(version=2))
    assert passport.envelope.schema_version == 2


def test_passport_request_binding_accepts_identity_reordering_but_rejects_drift() -> None:
    service = ResearchOsService()
    request = replace(_request(), available_variable_ids=("group", "score"))
    passport = service.plan(request, _passport_envelope())

    validate_passport_request_binding(passport, request)
    validate_passport_request_binding(
        passport,
        replace(
            request,
            available_variable_ids=tuple(reversed(request.available_variable_ids)),
        ),
    )
    with pytest.raises(ResearchServiceError, match="request binding"):
        validate_passport_request_binding(
            passport,
            replace(request, question_budget_remaining=2),
        )
    with pytest.raises(ResearchServiceError, match="component"):
        validate_passport_request_binding(
            passport,
            replace(request, question=replace(request.question, language=Language.EN)),
        )


def test_clarification_decision_rejects_plan_address_mismatch() -> None:
    decision = ResearchOsService().resolve(
        _request(study=_study(Fact.unknown(reason_code="dependence_not_confirmed")))
    )
    assert decision.clarification_plan is not None

    with pytest.raises(ResolverError, match="blocking fact address"):
        replace(decision, blocking_fact_addresses=("study.role.weight",))


def test_plan_maps_causal_and_stale_dataset_abstentions_to_recovery() -> None:
    causal = ResearchOsService().plan(
        _request(question=_question(causal_intent=CausalIntent.CAUSAL)),
        _passport_envelope(),
    )
    stale = ResearchOsService().plan(
        _request(current_fingerprint="c" * 64),
        _passport_envelope(),
    )

    assert causal.abstain is not None
    assert causal.abstain.reason_codes == ("unsupported_causal_target",)
    assert causal.abstain.recovery_requirement_ids == (
        "declare_noncausal_or_use_external_causal_workflow",
    )
    assert stale.abstain is not None
    assert "integrity:dataset_fingerprint_mismatch" in stale.abstain.reason_codes
    assert "rebind_specs_to_current_dataset" in stale.abstain.recovery_requirement_ids


def test_verified_external_route_plan_copies_privacy_boundary_but_no_resource() -> None:
    service = ResearchOsService(method_space=_external_route_method_space())

    passport = service.plan(_request(), _passport_envelope())

    assert passport.action is PrimaryAction.ROUTE_EXTERNAL
    assert passport.route_external is not None
    assert passport.route_external.route_ids == ("route.summary.external",)
    assert passport.route_external.privacy_boundary_ids == ("manual_export_only",)
    assert "resource_id" not in passport.to_mapping()["route_external"]


def test_plan_rejects_wrong_passport_schema_or_project_binding() -> None:
    service = ResearchOsService()

    with pytest.raises(ResearchServiceError, match="analysis_passport"):
        service.plan(
            _request(),
            _envelope("modori.study_spec", "passport-1"),
        )
    with pytest.raises(ResearchServiceError, match="project ID"):
        service.plan(_request(), _passport_envelope("project-2"))
    with pytest.raises(ResearchServiceError, match="component project IDs"):
        service.plan(
            _request(estimand=_estimand(project_id="project-2")),
            _passport_envelope(),
        )


def test_identical_semantic_decision_has_stable_digest() -> None:
    service = ResearchOsService()
    request = _request()

    left = service.plan(request, _passport_envelope())
    right = service.plan(
        request,
        replace(_passport_envelope(), object_id="passport-2"),
    )

    assert left.resolver_decision_digest == right.resolver_decision_digest
    assert left.digest() != right.digest()


def test_plan_binds_request_decision_evidence_in_event_order() -> None:
    first = DecisionEvidenceRef(
        evidence_id="answer:goal:2",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
        event_sequence=2,
        evidence_digest="d" * 64,
        subject_digests=("1" * 64,),
    )
    second = DecisionEvidenceRef(
        evidence_id="acceptance:goal:3",
        project_id="project-1",
        evidence_kind=DecisionEvidenceKind.REVISION_ACCEPTANCE,
        event_sequence=3,
        evidence_digest="e" * 64,
        subject_digests=("2" * 64,),
    )
    request = replace(
        _request(),
        decision_evidence_refs=(first, second),
    )

    passport = ResearchOsService().plan(request, _passport_envelope())

    assert passport.decision_evidence_digests == ("d" * 64, "e" * 64)


def test_planning_service_is_exposed_from_package() -> None:
    assert research_os.ResearchOsService is ResearchOsService
    assert research_os.ResolvedPassport is ResolvedPassport
    assert (
        research_os.validate_passport_request_binding
        is validate_passport_request_binding
    )
    assert callable(ResearchOsService.plan)
    assert callable(ResearchOsService.clarifications_for)
