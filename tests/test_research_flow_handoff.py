from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import inspect
import json

import pytest

import modori.research_flow.handoff as handoff_module
from modori.research_flow import (
    PassportBoundPreparation,
    PassportHandoffError,
    PassportStepMapping,
    PreflightDisposition,
    ResearchFlowContractError,
    map_passport_to_step,
)
from modori.research_memory import LedgerArtifact, canonical_bytes, canonical_digest
from modori.research_os import (
    AnalysisPassport,
    ClarificationTransitionService,
    ComponentRevisionRef,
    EstimandSpec,
    Fact,
    Language,
    P1TaskProfile,
    PrimaryAction,
    ResearchOsService,
    ResearchRequest,
    TargetRole,
    TargetRoleBinding,
)
from modori.steps.correlation import CorrelationStep
from modori.steps.descriptives_table1 import DescriptivesTableStep
from modori.steps.frequency_crosstab import FrequencyCrosstabStep
from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep
from tests.test_research_os_p1_intake import (
    _answer_selected,
    _passport_envelope,
    _request,
    _safe_value,
)


SUMMARY_KEY = (
    "descriptive_summary:unweighted_summary:summary:"
    "independent_unweighted:roles-v1"
)
FREQUENCY_KEY = (
    "frequency_distribution:unweighted_frequency:frequency_distribution:"
    "independent_unweighted:roles-v1"
)
PEARSON_KEY = (
    "bivariate_association:pearson_product_moment:association_correlation:"
    "independent_unweighted:roles-v1"
)
SPEARMAN_KEY = (
    "bivariate_association:spearman_rank_monotonic:association_correlation:"
    "independent_unweighted:roles-v1"
)
WELCH_KEY = (
    "compare_two_groups:welch_mean_difference:group_contrast_mean:"
    "independent_unweighted:roles-v1"
)
PAIRED_KEY = (
    "compare_two_groups:paired_t_mean_change:within_unit_mean_change:"
    "paired_unweighted:roles-v1"
)


EXPECTED_HANDOFFS = {
    P1TaskProfile.NUMERIC_DISTRIBUTION: (
        SUMMARY_KEY,
        "stats.descriptives_table1",
        {
            "schema_version": 1,
            "variables": ["outcome", "x"],
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
        },
        DescriptivesTableStep,
    ),
    P1TaskProfile.CATEGORY_FREQUENCY: (
        FREQUENCY_KEY,
        "stats.frequency_crosstab",
        {
            "schema_version": 1,
            "mode": "frequency",
            "variables": ["outcome", "x"],
            "language": "ko",
        },
        FrequencyCrosstabStep,
    ),
    P1TaskProfile.LINEAR_CO_MOVEMENT: (
        PEARSON_KEY,
        "stats.correlation",
        {
            "schema_version": 1,
            "pairs": [["y", "x"]],
            "method": "pearson",
            "missing_policy": "pairwise",
            "p_adjust": "none",
        },
        CorrelationStep,
    ),
    P1TaskProfile.RANK_CO_MOVEMENT: (
        SPEARMAN_KEY,
        "stats.correlation",
        {
            "schema_version": 1,
            "pairs": [["y", "x"]],
            "method": "spearman",
            "missing_policy": "pairwise",
            "p_adjust": "none",
        },
        CorrelationStep,
    ),
    P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: (
        WELCH_KEY,
        "stats.compare_groups",
        {
            "schema_version": 1,
            "dv": "outcome",
            "group": "group",
            "routing_policy": {"preset": "always_welch"},
        },
        CompareGroupsStep,
    ),
    P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: (
        PAIRED_KEY,
        "stats.paired_comparison",
        {
            "schema_version": 1,
            "before": "before",
            "after": "after",
            "routing_policy": {"preset": "classic"},
        },
        PairedComparisonStep,
    ),
}


def _resolve_terminal(
    request: ResearchRequest,
) -> tuple[ResearchRequest, AnalysisPassport]:
    service = ResearchOsService()
    transition = ClarificationTransitionService()
    for round_number in range(1, 5):
        resolved = service.resolve_and_plan(
            request,
            _passport_envelope(request, round_number),
        )
        if resolved.decision.action is PrimaryAction.RECOMMEND_LOCAL:
            return request, resolved.passport
        assert resolved.decision.action is PrimaryAction.CLARIFY
        clarify = resolved.passport.clarify
        assert clarify is not None
        answer = _answer_selected(
            request,
            resolved.passport,
            _safe_value(clarify.clarification_ref.fact_address),
            sequence=round_number,
        )
        candidate = transition.propose(request, resolved.passport, answer)
        assert candidate.requires_acceptance is False
        request = transition.commit_ready(request, candidate)
    raise AssertionError("request did not reach a local recommendation")


def _terminal(profile: P1TaskProfile) -> tuple[ResearchRequest, AnalysisPassport]:
    return _resolve_terminal(_request(profile))


def _mapping_digest_payload(mapping: PassportStepMapping) -> dict[str, object]:
    return {
        "schema_id": "modori.passport_step_mapping",
        "schema_version": 1,
        "passport_artifact_id": mapping.passport_artifact_id,
        "passport_digest": mapping.passport_digest,
        "capability_key": mapping.capability_key,
        "dataset_fingerprint": mapping.dataset_fingerprint,
        "step_type": mapping.step_type,
        "canonical_step_params": json.loads(
            mapping.canonical_step_params.decode("utf-8")
        ),
        "experimental": mapping.experimental,
        "requires_explicit_configure_confirm_run": (
            mapping.requires_explicit_configure_confirm_run
        ),
    }


def _preparation_digest_payload(
    mapping: PassportStepMapping,
    disposition: PreflightDisposition,
) -> dict[str, object]:
    payload = _mapping_digest_payload(mapping)
    payload["schema_id"] = "modori.passport_bound_preparation"
    payload["preflight_disposition"] = disposition.value
    return payload


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_all_six_passports_map_to_exact_canonical_current_step_params(
    profile: P1TaskProfile,
) -> None:
    request, passport = _terminal(profile)
    expected_key, expected_step, expected_params, step_class = EXPECTED_HANDOFFS[
        profile
    ]

    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )

    assert tuple(mapping.__dataclass_fields__) == (
        "passport_artifact_id",
        "passport_digest",
        "capability_key",
        "dataset_fingerprint",
        "step_type",
        "canonical_step_params",
        "experimental",
        "requires_explicit_configure_confirm_run",
        "mapping_digest",
    )
    assert mapping.passport_artifact_id == LedgerArtifact.from_value(
        passport
    ).artifact_id
    assert mapping.passport_digest == passport.digest()
    assert mapping.capability_key == expected_key
    assert mapping.dataset_fingerprint == request.current_dataset_fingerprint
    assert mapping.step_type == expected_step
    assert mapping.canonical_step_params == canonical_bytes(expected_params)
    assert mapping.experimental is True
    assert mapping.requires_explicit_configure_confirm_run is True
    assert mapping.mapping_digest == canonical_digest(
        _mapping_digest_payload(mapping)
    )

    raw_params = json.loads(mapping.canonical_step_params.decode("utf-8"))
    migrated = step_class.migrate_params(raw_params)
    step_class.validate_params(migrated)
    with pytest.raises(FrozenInstanceError):
        mapping.step_type = "stats.nearby"  # type: ignore[misc]


def test_preparation_contract_is_separate_and_binds_preflight_disposition() -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )
    disposition = PreflightDisposition.PREPARE_READY
    preparation = PassportBoundPreparation(
        passport_artifact_id=mapping.passport_artifact_id,
        passport_digest=mapping.passport_digest,
        capability_key=mapping.capability_key,
        dataset_fingerprint=mapping.dataset_fingerprint,
        step_type=mapping.step_type,
        canonical_step_params=mapping.canonical_step_params,
        preflight_disposition=disposition,
        experimental=True,
        requires_explicit_configure_confirm_run=True,
        preparation_digest=canonical_digest(
            _preparation_digest_payload(mapping, disposition)
        ),
    )

    assert tuple(preparation.__dataclass_fields__) == (
        "passport_artifact_id",
        "passport_digest",
        "capability_key",
        "dataset_fingerprint",
        "step_type",
        "canonical_step_params",
        "preflight_disposition",
        "experimental",
        "requires_explicit_configure_confirm_run",
        "preparation_digest",
    )
    with pytest.raises(ResearchFlowContractError):
        replace(preparation, preflight_disposition="ready")  # type: ignore[arg-type]
    with pytest.raises(ResearchFlowContractError):
        replace(preparation, preparation_digest="0" * 64)


@pytest.mark.parametrize(
    "disposition",
    (PreflightDisposition.STALE, PreflightDisposition.FAILURE),
)
def test_stale_or_failed_preflight_cannot_be_sealed_as_a_preparation(
    disposition: PreflightDisposition,
) -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )
    fields = {
        "passport_artifact_id": mapping.passport_artifact_id,
        "passport_digest": mapping.passport_digest,
        "capability_key": mapping.capability_key,
        "dataset_fingerprint": mapping.dataset_fingerprint,
        "step_type": mapping.step_type,
        "canonical_step_params": mapping.canonical_step_params,
        "preflight_disposition": disposition,
        "experimental": True,
        "requires_explicit_configure_confirm_run": True,
    }
    with pytest.raises(ResearchFlowContractError, match="ready|blocked|preparation"):
        digest = PassportBoundPreparation.compute_digest(**fields)
        PassportBoundPreparation(
            **fields,
            preparation_digest=digest,
        )


@pytest.mark.parametrize(
    "profile",
    (
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        P1TaskProfile.CATEGORY_FREQUENCY,
    ),
)
def test_language_is_taken_from_the_bound_question_not_hard_coded(
    profile: P1TaskProfile,
) -> None:
    initial = _request(profile)
    english_request = replace(
        initial,
        question=replace(initial.question, language=Language.EN),
    )
    request, passport = _resolve_terminal(english_request)

    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )

    params = json.loads(mapping.canonical_step_params.decode("utf-8"))
    assert params["language"] == "en"


@pytest.mark.parametrize("profile", tuple(P1TaskProfile))
def test_mapping_digest_rejects_any_normative_field_or_param_mutation(
    profile: P1TaskProfile,
) -> None:
    request, passport = _terminal(profile)
    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )
    raw = json.loads(mapping.canonical_step_params.decode("utf-8"))
    raw["schema_version"] = 999

    for change in (
        {"passport_artifact_id": "0" * 64},
        {"passport_digest": "0" * 64},
        {"capability_key": "nearby:capability"},
        {"dataset_fingerprint": "0" * 64},
        {"step_type": "stats.nearby"},
        {"canonical_step_params": canonical_bytes(raw)},
        {"experimental": False},
        {"requires_explicit_configure_confirm_run": False},
        {"mapping_digest": "0" * 64},
    ):
        with pytest.raises(ResearchFlowContractError):
            replace(mapping, **change)


@pytest.mark.parametrize(
    "malformed",
    (
        b"{}",
        b'{"schema_version":2}',
        b'{"schema_version":true}',
        b'{"schema_version":1, "variables":[]}',
        b'{"schema_version":1,"schema_version":1}',
        b'{"schema_version":1,"x":1.5}',
        b'{"schema_version":1,"x":NaN}',
        b'{"schema_version":1,"Schema":1}',
        b"[]",
        b"\xff",
    ),
)
def test_mapping_rejects_noncanonical_or_future_param_bytes(
    malformed: bytes,
) -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )

    with pytest.raises(ResearchFlowContractError):
        replace(mapping, canonical_step_params=malformed)


@pytest.mark.parametrize(
    ("profile", "field", "mutant"),
    (
        (P1TaskProfile.LINEAR_CO_MOVEMENT, "method", "auto"),
        (P1TaskProfile.RANK_CO_MOVEMENT, "method", "auto"),
        (
            P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN,
            "routing_policy",
            {"preset": "modern"},
        ),
        (
            P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE,
            "routing_policy",
            {"preset": "modern"},
        ),
    ),
)
def test_auto_or_modern_policy_is_not_the_exact_handoff_even_if_step_accepts_it(
    profile: P1TaskProfile,
    field: str,
    mutant: object,
) -> None:
    request, passport = _terminal(profile)
    mapping = map_passport_to_step(
        passport,
        request,
        current_dataset_fingerprint=request.current_dataset_fingerprint,
    )
    expected_params = dict(EXPECTED_HANDOFFS[profile][2])
    mutated = dict(expected_params)
    mutated[field] = mutant
    step_class = EXPECTED_HANDOFFS[profile][3]

    step_class.validate_params(step_class.migrate_params(mutated))
    assert canonical_bytes(mutated) != mapping.canonical_step_params


def _rebind_passport(
    passport: AnalysisPassport,
    request: ResearchRequest,
) -> AnalysisPassport:
    def component_ref(spec) -> ComponentRevisionRef:
        return ComponentRevisionRef(
            schema_id=spec.envelope.schema_id,
            object_id=spec.envelope.object_id,
            revision=spec.envelope.revision,
            digest=spec.digest(),
        )

    return replace(
        passport,
        question_ref=component_ref(request.question),
        estimand_ref=component_ref(request.estimand),
        study_ref=component_ref(request.study),
        dataset_fingerprint=request.current_dataset_fingerprint,
        decision_evidence_digests=tuple(
            item.evidence_digest for item in request.decision_evidence_refs
        ),
        request_binding_digest=request.request_binding_digest(),
    )


@pytest.mark.parametrize(
    "change",
    (
        "nearby_capability",
        "wrong_local_kind",
        "multiple_capabilities",
        "not_experimental",
        "stale_method_space",
        "stale_registry",
    ),
)
def test_nearby_or_stale_passport_payloads_fail_without_fallback(change: str) -> None:
    request, passport = _terminal(P1TaskProfile.LINEAR_CO_MOVEMENT)
    payload = passport.recommend_local
    assert payload is not None
    if change == "nearby_capability":
        passport = replace(
            passport,
            recommend_local=replace(
                payload,
                capability_keys=(PEARSON_KEY + ":nearby",),
            ),
        )
    elif change == "wrong_local_kind":
        passport = replace(
            passport,
            recommend_local=replace(
                payload,
                local_analysis_kinds=("regression",),
            ),
        )
    elif change == "multiple_capabilities":
        passport = replace(
            passport,
            recommend_local=replace(
                payload,
                capability_keys=(PEARSON_KEY, SPEARMAN_KEY),
                local_analysis_kinds=("correlation", "correlation"),
            ),
        )
    elif change == "not_experimental":
        passport = replace(
            passport,
            recommend_local=replace(payload, experimental=False),
        )
    elif change == "stale_method_space":
        passport = replace(passport, method_space_digest="0" * 64)
    else:
        passport = replace(passport, clarification_registry_digest="0" * 64)

    with pytest.raises(PassportHandoffError):
        map_passport_to_step(
            passport,
            request,
            current_dataset_fingerprint=request.current_dataset_fingerprint,
        )


def test_changed_fingerprint_wrong_request_and_nonrecommend_passport_fail_closed() -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    with pytest.raises(PassportHandoffError, match="fingerprint|stale"):
        map_passport_to_step(
            passport,
            request,
            current_dataset_fingerprint="f" * 64,
        )

    foreign_request, _foreign_passport = _terminal(
        P1TaskProfile.CATEGORY_FREQUENCY
    )
    with pytest.raises(PassportHandoffError, match="bind|current|request"):
        map_passport_to_step(
            passport,
            foreign_request,
            current_dataset_fingerprint=foreign_request.current_dataset_fingerprint,
        )

    initial = _request(P1TaskProfile.NUMERIC_DISTRIBUTION)
    clarify = ResearchOsService().resolve_and_plan(
        initial,
        _passport_envelope(initial, 1),
    ).passport
    with pytest.raises(PassportHandoffError, match="recommend|action"):
        map_passport_to_step(
            clarify,
            initial,
            current_dataset_fingerprint=initial.current_dataset_fingerprint,
        )

    legacy = replace(
        passport,
        envelope=replace(passport.envelope, schema_version=1),
        request_binding_digest=None,
        clarification_registry_digest=None,
    )
    with pytest.raises(PassportHandoffError, match="version 2"):
        map_passport_to_step(
            legacy,
            request,
            current_dataset_fingerprint=request.current_dataset_fingerprint,
        )


def test_runtime_catalog_drift_fails_even_with_a_matching_forged_passport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    current = handoff_module.build_p1_method_space()

    class DriftedMethodSpace:
        version = current.version
        ruleset_version = current.ruleset_version
        capabilities = current.capabilities

        @staticmethod
        def digest() -> str:
            return "f" * 64

    monkeypatch.setattr(
        handoff_module,
        "build_p1_method_space",
        DriftedMethodSpace,
    )
    forged = replace(passport, method_space_digest="f" * 64)

    with pytest.raises(PassportHandoffError, match="catalog|oracle|drift"):
        map_passport_to_step(
            forged,
            request,
            current_dataset_fingerprint=request.current_dataset_fingerprint,
        )


def test_extra_target_role_is_rejected_even_when_forged_passport_binds_it() -> None:
    request, passport = _terminal(P1TaskProfile.LINEAR_CO_MOVEMENT)
    extra = TargetRoleBinding(
        role=TargetRole.EXPOSURE,
        variable_ids=Fact.user_confirmed(
            ("group",),
            provenance_refs=("test:extra-role",),
        ),
    )
    changed_estimand = replace(
        request.estimand,
        target_roles=request.estimand.target_roles + (extra,),
    )
    changed_request = replace(request, estimand=changed_estimand)
    forged = _rebind_passport(passport, changed_request)

    with pytest.raises(PassportHandoffError, match="role|exact"):
        map_passport_to_step(
            forged,
            changed_request,
            current_dataset_fingerprint=changed_request.current_dataset_fingerprint,
        )


def test_unknown_role_variable_fails_even_when_forged_passport_binds_it() -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    outcome = request.estimand.target_roles[0]
    changed_estimand = replace(
        request.estimand,
        target_roles=(
            replace(
                outcome,
                variable_ids=Fact.user_confirmed(
                    ("not-in-current-dataset",),
                    provenance_refs=("test:unknown-variable",),
                ),
            ),
        ),
    )
    changed_request = replace(request, estimand=changed_estimand)
    forged = _rebind_passport(passport, changed_request)

    with pytest.raises(PassportHandoffError, match="available|unknown|variable"):
        map_passport_to_step(
            forged,
            changed_request,
            current_dataset_fingerprint=changed_request.current_dataset_fingerprint,
        )


def test_study_fingerprint_mismatch_fails_after_full_passport_rebinding() -> None:
    request, passport = _terminal(P1TaskProfile.NUMERIC_DISTRIBUTION)
    changed_request = replace(
        request,
        study=replace(request.study, dataset_fingerprint="0" * 64),
    )
    forged = _rebind_passport(passport, changed_request)

    with pytest.raises(PassportHandoffError, match="fingerprint|study"):
        map_passport_to_step(
            forged,
            changed_request,
            current_dataset_fingerprint=changed_request.current_dataset_fingerprint,
        )


def test_duplicate_target_role_is_rejected_after_contract_bypass() -> None:
    request, passport = _terminal(P1TaskProfile.LINEAR_CO_MOVEMENT)
    forged_estimand = object.__new__(EstimandSpec)
    for field_name in EstimandSpec.__dataclass_fields__:
        value = getattr(request.estimand, field_name)
        if field_name == "target_roles":
            value = value + (value[0],)
        object.__setattr__(forged_estimand, field_name, value)
    forged_request = replace(request, estimand=forged_estimand)
    forged_passport = _rebind_passport(passport, forged_request)

    with pytest.raises(PassportHandoffError, match="role|duplicate|exact"):
        map_passport_to_step(
            forged_passport,
            forged_request,
            current_dataset_fingerprint=forged_request.current_dataset_fingerprint,
        )


def test_paired_order_role_and_outcome_must_match_exactly() -> None:
    request, passport = _terminal(P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE)
    changed_study = replace(
        request.study,
        repeated_measure_order=Fact.user_confirmed(
            ("after", "before"),
            provenance_refs=("test:swapped-order",),
        ),
    )
    changed_request = replace(request, study=changed_study)
    forged = _rebind_passport(passport, changed_request)

    with pytest.raises(PassportHandoffError, match="order|repeated|outcome"):
        map_passport_to_step(
            forged,
            changed_request,
            current_dataset_fingerprint=changed_request.current_dataset_fingerprint,
        )


def test_handoff_api_has_no_override_params_or_nearby_fallback_input() -> None:
    assert tuple(inspect.signature(map_passport_to_step).parameters) == (
        "passport",
        "request",
        "current_dataset_fingerprint",
    )
