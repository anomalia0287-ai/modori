from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

import modori.research_os as research_os
from modori.research_os.contracts import SchemaEnvelope
from modori.research_os.passport import (
    AbstainPayload,
    AnalysisPassport,
    ClaimClass,
    ClarifyPayload,
    ComponentRevisionRef,
    PassportError,
    RecommendLocalPayload,
    RouteExternalPayload,
)
from modori.research_os.resolver import PrimaryAction


def _passport_envelope() -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id="modori.analysis_passport",
        schema_version=1,
        project_id="project-1",
        object_id="passport-1",
        revision=1,
        supersedes_revision=None,
        created_event_ref="event:passport-1:1",
    )


def _ref(schema_id: str, object_id: str, fill: str) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=schema_id,
        object_id=object_id,
        revision=1,
        digest=fill * 64,
    )


def _recommend_payload() -> RecommendLocalPayload:
    return RecommendLocalPayload(
        capability_keys=("family:variant:estimand:design:roles-v1",),
        local_analysis_kinds=("comparison",),
        claim_permissions=(ClaimClass.ASSOCIATION,),
        experimental=True,
    )


def _clarify_payload() -> ClarifyPayload:
    return ClarifyPayload(
        question_ids=("confirm_dependence",),
        blocking_fact_addresses=("study.dependence_structure",),
    )


def _route_payload() -> RouteExternalPayload:
    return RouteExternalPayload(
        route_ids=("route.nonlocal.mixed_model",),
        privacy_boundary_ids=("manual_export_only",),
    )


def _abstain_payload() -> AbstainPayload:
    return AbstainPayload(
        reason_codes=("unsupported_causal_target",),
        recovery_requirement_ids=("declare_noncausal_or_use_external_workflow",),
    )


def _passport(**payloads: object) -> AnalysisPassport:
    return AnalysisPassport(
        envelope=_passport_envelope(),
        question_ref=_ref("modori.question_spec", "question-1", "1"),
        estimand_ref=_ref("modori.estimand_spec", "estimand-1", "2"),
        study_ref=_ref("modori.study_spec", "study-1", "3"),
        dataset_fingerprint="a" * 64,
        method_space_version="research-os-p1-v1",
        method_space_digest="b" * 64,
        ruleset_version="research-os-c1-p1-v1",
        resolver_decision_digest="c" * 64,
        **payloads,
    )


def _valid_recommend_passport() -> AnalysisPassport:
    return _passport(recommend_local=_recommend_payload())


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for item in value.values()
            for key in _all_keys(item)
        }
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def test_passport_rejects_mixed_or_missing_action_payloads() -> None:
    with pytest.raises(PassportError, match="exactly one action payload"):
        _passport(
            recommend_local=_recommend_payload(),
            clarify=_clarify_payload(),
        )

    with pytest.raises(PassportError, match="exactly one action payload"):
        _passport()


@pytest.mark.parametrize(
    ("payload_name", "payload", "action"),
    [
        ("recommend_local", _recommend_payload(), PrimaryAction.RECOMMEND_LOCAL),
        ("clarify", _clarify_payload(), PrimaryAction.CLARIFY),
        ("route_external", _route_payload(), PrimaryAction.ROUTE_EXTERNAL),
        ("abstain", _abstain_payload(), PrimaryAction.ABSTAIN),
    ],
)
def test_each_payload_maps_to_exactly_one_primary_action(
    payload_name: str,
    payload: object,
    action: PrimaryAction,
) -> None:
    passport = _passport(**{payload_name: payload})

    assert passport.action is action


def test_recommend_payload_cannot_auto_select_or_bypass_confirmation() -> None:
    with pytest.raises(PassportError, match="auto_selected must be false"):
        replace(_recommend_payload(), auto_selected=True)

    with pytest.raises(PassportError, match="explicit configure-confirm-run gate"):
        replace(
            _recommend_payload(),
            requires_explicit_configure_confirm_run=False,
        )

    with pytest.raises(PassportError, match="one local analysis kind per capability"):
        replace(_recommend_payload(), local_analysis_kinds=("comparison", "other"))


def test_action_payloads_require_complete_closed_identifiers() -> None:
    with pytest.raises(PassportError, match="same number"):
        ClarifyPayload(
            question_ids=("confirm_dependence", "confirm_weight_use"),
            blocking_fact_addresses=("study.dependence_structure",),
        )
    with pytest.raises(PassportError, match="same number"):
        RouteExternalPayload(
            route_ids=("route.one", "route.two"),
            privacy_boundary_ids=("manual_export_only",),
        )
    with pytest.raises(PassportError, match="recovery requirement"):
        AbstainPayload(
            reason_codes=("no_stable_supported_capability",),
            recovery_requirement_ids=(),
        )


def test_component_reference_rejects_boolean_revision_and_bad_digest() -> None:
    with pytest.raises(PassportError, match="revision must be a positive integer"):
        replace(_ref("modori.question_spec", "question-1", "1"), revision=True)
    with pytest.raises(PassportError, match="lowercase SHA-256"):
        replace(_ref("modori.question_spec", "question-1", "1"), digest="bad")


def test_passport_requires_exact_schema_and_component_types() -> None:
    with pytest.raises(PassportError, match="modori.analysis_passport"):
        replace(
            _valid_recommend_passport(),
            envelope=replace(_passport_envelope(), schema_id="modori.study_spec"),
        )
    with pytest.raises(PassportError, match="question_ref must reference"):
        replace(
            _valid_recommend_passport(),
            question_ref=_ref("modori.study_spec", "question-1", "1"),
        )


def test_passport_strict_roundtrip_preserves_digest() -> None:
    passport = _valid_recommend_passport()

    restored = AnalysisPassport.from_mapping(passport.to_mapping())

    assert restored == passport
    assert restored.digest() == passport.digest()

    with pytest.raises(PassportError, match="unknown field.*execute"):
        AnalysisPassport.from_mapping(passport.to_mapping() | {"execute": True})


def test_v1_wire_mapping_and_digest_are_frozen() -> None:
    passport = _valid_recommend_passport()

    assert passport.envelope.schema_version == 1
    assert "request_binding_digest" not in passport.to_mapping()
    assert "clarification_registry_digest" not in passport.to_mapping()
    assert passport.digest() == (
        "256019034d7fb5fbe1ac1547c5c3516dfc83ae0f125f059c5ceb91f6c9d41ec8"
    )
    assert AnalysisPassport.from_mapping(passport.to_mapping()) == passport


def test_passport_decision_evidence_digests_are_ordered_unique_hashes() -> None:
    passport = _valid_recommend_passport()

    assert passport.decision_evidence_digests == ()
    with_evidence = replace(
        passport,
        decision_evidence_digests=("d" * 64, "e" * 64),
    )
    assert AnalysisPassport.from_mapping(with_evidence.to_mapping()) == with_evidence
    assert with_evidence.digest() != passport.digest()
    assert replace(
        with_evidence,
        decision_evidence_digests=tuple(
            reversed(with_evidence.decision_evidence_digests)
        ),
    ).digest() != with_evidence.digest()
    with pytest.raises(PassportError, match="duplicates"):
        replace(
            passport,
            decision_evidence_digests=("d" * 64, "d" * 64),
        )
    with pytest.raises(PassportError, match="lowercase SHA-256"):
        replace(passport, decision_evidence_digests=("invalid",))


def test_every_action_roundtrips_without_mixed_authority() -> None:
    passports = (
        _valid_recommend_passport(),
        _passport(clarify=_clarify_payload()),
        _passport(route_external=_route_payload()),
        _passport(abstain=_abstain_payload()),
    )

    for passport in passports:
        assert AnalysisPassport.from_mapping(passport.to_mapping()) == passport


def test_passport_wire_has_no_execution_authority_key() -> None:
    forbidden = {
        "command",
        "worker_token",
        "path",
        "url",
        "execute",
        "pipeline_mutation",
    }

    assert _all_keys(_valid_recommend_passport().to_mapping()).isdisjoint(forbidden)


def test_passport_contract_is_exposed_from_package() -> None:
    assert research_os.AnalysisPassport is AnalysisPassport
    assert research_os.ClaimClass is ClaimClass
