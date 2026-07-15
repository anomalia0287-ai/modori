from __future__ import annotations

from dataclasses import replace

import modori.research_os as research_os

from modori.research_os.clarification import ClarificationRegistry
from modori.research_os.contracts import SchemaEnvelope
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.passport import (
    AnalysisPassport,
    ClarificationRef,
    ClarifyPayload,
    ClarifyPayloadV2,
    ComponentRevisionRef,
    clarify_decision_digest,
)
from modori.research_os.passport_audit import (
    PassportRegistryAuditStatus,
    audit_passport_registry,
)
from tests.research_os_v2_fixtures import locked_p1_plan


def _ref(schema_id: str, object_id: str, fill: str) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=schema_id,
        object_id=object_id,
        revision=1,
        digest=fill * 64,
    )


def _envelope(version: int) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id="modori.analysis_passport",
        schema_version=version,
        project_id="project-1",
        object_id=f"passport-audit-v{version}",
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:passport-audit-v{version}:1",
    )


def _v2_passport() -> AnalysisPassport:
    plan = locked_p1_plan()
    registry = build_p1_clarification_registry()
    decision_digest = clarify_decision_digest(
        question_id=plan.selected_question_id,
        fact_address=plan.selected_fact_address,
        plan=plan,
    )
    reference = ClarificationRef(
        question_id=plan.selected_question_id,
        question_version=plan.selected_question_version,
        question_digest=plan.selected_question_digest,
        fact_address=plan.selected_fact_address,
        planner_version=plan.planner_version,
        clarification_plan_digest=plan.digest(),
        source_decision_digest=decision_digest,
    )
    return AnalysisPassport(
        envelope=_envelope(2),
        question_ref=_ref("modori.question_spec", "question-1", "1"),
        estimand_ref=_ref("modori.estimand_spec", "estimand-1", "2"),
        study_ref=_ref("modori.study_spec", "study-1", "3"),
        dataset_fingerprint="a" * 64,
        method_space_version="research-os-p1-v1",
        method_space_digest="b" * 64,
        ruleset_version="research-os-c1-p1-v1",
        resolver_decision_digest=decision_digest,
        request_binding_digest="d" * 64,
        clarification_registry_digest=registry.digest(),
        clarify=ClarifyPayloadV2(reference, plan),
    )


def _v1_passport() -> AnalysisPassport:
    return AnalysisPassport(
        envelope=_envelope(1),
        question_ref=_ref("modori.question_spec", "question-1", "1"),
        estimand_ref=_ref("modori.estimand_spec", "estimand-1", "2"),
        study_ref=_ref("modori.study_spec", "study-1", "3"),
        dataset_fingerprint="a" * 64,
        method_space_version="research-os-p1-v1",
        method_space_digest="b" * 64,
        ruleset_version="research-os-c1-p1-v1",
        resolver_decision_digest="c" * 64,
        clarify=ClarifyPayload(
            question_ids=("confirm_dependence",),
            blocking_fact_addresses=("study.dependence_structure",),
        ),
    )


def test_registry_audit_distinguishes_unavailable_failure_and_verified() -> None:
    passport = _v2_passport()
    registry = build_p1_clarification_registry()

    verified = audit_passport_registry(passport, registry)
    unavailable = audit_passport_registry(passport, None)

    assert verified.status is PassportRegistryAuditStatus.VERIFIED
    assert verified.reason_code == "registry_verified"
    assert unavailable.status is PassportRegistryAuditStatus.UNAVAILABLE
    assert unavailable.reason_code == "registry_preimage_unavailable"
    selected_id = passport.clarify.clarification_ref.question_id
    changed = ClarificationRegistry(
        questions=tuple(
            replace(item, version=item.version + 1)
            if item.question_id == selected_id
            else item
            for item in registry.questions
        ),
        required_question_ids=registry.required_question_ids,
    )
    failure = audit_passport_registry(passport, changed)
    assert failure.status is PassportRegistryAuditStatus.FAILURE
    assert failure.reason_code == "registry_digest_mismatch"


def test_v1_registry_audit_is_unavailable_not_failed_or_verified() -> None:
    audit = audit_passport_registry(
        _v1_passport(),
        build_p1_clarification_registry(),
    )

    assert audit.status is PassportRegistryAuditStatus.UNAVAILABLE
    assert audit.reason_code == "v1_registry_unbound"


def test_registry_audit_contract_is_exposed_from_package() -> None:
    assert research_os.PassportRegistryAuditStatus is PassportRegistryAuditStatus
    assert research_os.audit_passport_registry is audit_passport_registry
