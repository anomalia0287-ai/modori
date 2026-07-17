"""Exact, no-fallback passport-to-step handoff for the six P1 capabilities."""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType

from modori.research_flow.contracts import PassportStepMapping
from modori.research_memory.canonical import CanonicalizationError, canonical_bytes
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerContractError,
)
from modori.research_os import (
    AnalysisPassport,
    AssociationTarget,
    CausalIntent,
    ClaimBasis,
    ClaimClass,
    ContrastKind,
    DependenceKind,
    EffectScale,
    EstimandTemplate,
    Fact,
    FactState,
    PrimaryAction,
    ProductSurface,
    ResearchGoal,
    ResearchRequest,
    ResearchServiceError,
    StudyRole,
    TargetRole,
    build_p1_clarification_registry,
    build_p1_method_space,
    validate_passport_request_binding,
)


class PassportHandoffError(ValueError):
    """Raised when a passport cannot become one exact P1 step mapping."""


_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_EXPECTED_METHOD_SPACE_VERSION = "research-os-p1-v1"
_EXPECTED_RULESET_VERSION = "research-os-c1-p1-v1"
_EXPECTED_METHOD_SPACE_DIGEST = (
    "3c8eb1ce4ff19c703fc30ef6ceb77c34ba4d03c06b55b65b09a7585b5b576b29"
)
_EXPECTED_CLARIFICATION_REGISTRY_DIGEST = (
    "ed762a596485de8b678357619455de3519d13659c157208cf9a8e05b0414029e"
)
_SUMMARY_KEY = (
    "descriptive_summary:unweighted_summary:summary:"
    "independent_unweighted:roles-v1"
)
_FREQUENCY_KEY = (
    "frequency_distribution:unweighted_frequency:frequency_distribution:"
    "independent_unweighted:roles-v1"
)
_PEARSON_KEY = (
    "bivariate_association:pearson_product_moment:association_correlation:"
    "independent_unweighted:roles-v1"
)
_SPEARMAN_KEY = (
    "bivariate_association:spearman_rank_monotonic:association_correlation:"
    "independent_unweighted:roles-v1"
)
_WELCH_KEY = (
    "compare_two_groups:welch_mean_difference:group_contrast_mean:"
    "independent_unweighted:roles-v1"
)
_PAIRED_KEY = (
    "compare_two_groups:paired_t_mean_change:within_unit_mean_change:"
    "paired_unweighted:roles-v1"
)


@dataclass(frozen=True)
class _HandoffRow:
    capability_key: str
    local_analysis_kind: str
    claim_permission: ClaimClass
    target_roles: tuple[TargetRole, ...]
    goal: ResearchGoal
    template: EstimandTemplate
    claim_basis: ClaimBasis
    effect_scale: EffectScale
    association_target: AssociationTarget | None
    contrast: ContrastKind | None
    dependence: DependenceKind
    step_type: str


_ROWS = (
    _HandoffRow(
        capability_key=_SUMMARY_KEY,
        local_analysis_kind="descriptives",
        claim_permission=ClaimClass.SAMPLE_DESCRIPTION,
        target_roles=(TargetRole.OUTCOME,),
        goal=ResearchGoal.DESCRIBE,
        template=EstimandTemplate.SUMMARY,
        claim_basis=ClaimBasis.DESCRIPTIVE,
        effect_scale=EffectScale.DISTRIBUTION,
        association_target=None,
        contrast=None,
        dependence=DependenceKind.INDEPENDENT,
        step_type="stats.descriptives_table1",
    ),
    _HandoffRow(
        capability_key=_FREQUENCY_KEY,
        local_analysis_kind="frequency_crosstab",
        claim_permission=ClaimClass.SAMPLE_DESCRIPTION,
        target_roles=(TargetRole.OUTCOME,),
        goal=ResearchGoal.DESCRIBE,
        template=EstimandTemplate.FREQUENCY_DISTRIBUTION,
        claim_basis=ClaimBasis.DESCRIPTIVE,
        effect_scale=EffectScale.DISTRIBUTION,
        association_target=None,
        contrast=None,
        dependence=DependenceKind.INDEPENDENT,
        step_type="stats.frequency_crosstab",
    ),
    _HandoffRow(
        capability_key=_PEARSON_KEY,
        local_analysis_kind="correlation",
        claim_permission=ClaimClass.ASSOCIATION,
        target_roles=(TargetRole.OUTCOME, TargetRole.FOCAL_PREDICTOR),
        goal=ResearchGoal.ASSOCIATE,
        template=EstimandTemplate.ASSOCIATION,
        claim_basis=ClaimBasis.ASSOCIATIONAL,
        effect_scale=EffectScale.CORRELATION,
        association_target=AssociationTarget.PRODUCT_MOMENT,
        contrast=None,
        dependence=DependenceKind.INDEPENDENT,
        step_type="stats.correlation",
    ),
    _HandoffRow(
        capability_key=_SPEARMAN_KEY,
        local_analysis_kind="correlation",
        claim_permission=ClaimClass.ASSOCIATION,
        target_roles=(TargetRole.OUTCOME, TargetRole.FOCAL_PREDICTOR),
        goal=ResearchGoal.ASSOCIATE,
        template=EstimandTemplate.ASSOCIATION,
        claim_basis=ClaimBasis.ASSOCIATIONAL,
        effect_scale=EffectScale.CORRELATION,
        association_target=AssociationTarget.RANK_MONOTONIC,
        contrast=None,
        dependence=DependenceKind.INDEPENDENT,
        step_type="stats.correlation",
    ),
    _HandoffRow(
        capability_key=_WELCH_KEY,
        local_analysis_kind="comparison",
        claim_permission=ClaimClass.ASSOCIATION,
        target_roles=(TargetRole.OUTCOME, TargetRole.GROUP),
        goal=ResearchGoal.COMPARE,
        template=EstimandTemplate.GROUP_CONTRAST,
        claim_basis=ClaimBasis.ASSOCIATIONAL,
        effect_scale=EffectScale.DIFFERENCE,
        association_target=None,
        contrast=ContrastKind.PAIRWISE,
        dependence=DependenceKind.INDEPENDENT,
        step_type="stats.compare_groups",
    ),
    _HandoffRow(
        capability_key=_PAIRED_KEY,
        local_analysis_kind="paired_comparison",
        claim_permission=ClaimClass.ASSOCIATION,
        target_roles=(TargetRole.OUTCOME, TargetRole.REPEATED_MEASURE),
        goal=ResearchGoal.COMPARE,
        template=EstimandTemplate.WITHIN_UNIT_CHANGE,
        claim_basis=ClaimBasis.ASSOCIATIONAL,
        effect_scale=EffectScale.DIFFERENCE,
        association_target=None,
        contrast=ContrastKind.PAIRWISE,
        dependence=DependenceKind.PAIRED,
        step_type="stats.paired_comparison",
    ),
)
_ROWS_BY_KEY = MappingProxyType({row.capability_key: row for row in _ROWS})


def _require_user_fact(fact: Fact[object], expected: object, field: str) -> None:
    if fact.state is not FactState.USER_CONFIRMED or fact.value != expected:
        raise PassportHandoffError(
            f"{field} does not exactly match the selected P1 capability"
        )


def _require_not_applicable(fact: Fact[object], field: str) -> None:
    if fact.state is not FactState.NOT_APPLICABLE or fact.value is not None:
        raise PassportHandoffError(
            f"{field} must be explicitly not applicable for this capability"
        )


def _validate_catalog_identity(passport: AnalysisPassport) -> None:
    method_space = build_p1_method_space()
    registry = build_p1_clarification_registry()
    if (
        method_space.version != _EXPECTED_METHOD_SPACE_VERSION
        or method_space.ruleset_version != _EXPECTED_RULESET_VERSION
        or method_space.digest() != _EXPECTED_METHOD_SPACE_DIGEST
        or registry.digest() != _EXPECTED_CLARIFICATION_REGISTRY_DIGEST
    ):
        raise PassportHandoffError(
            "current P1 catalogs drifted from the closed handoff oracle"
        )
    if tuple(capability.identity.key for capability in method_space.capabilities) != tuple(
        row.capability_key for row in _ROWS
    ):
        raise PassportHandoffError(
            "P1 Method Space no longer matches the closed handoff table"
        )
    for capability, row in zip(method_space.capabilities, _ROWS, strict=True):
        if (
            capability.local_analysis_kind != row.local_analysis_kind
            or capability.claim_permissions != (row.claim_permission.value,)
            or capability.support.value != "local_compute"
            or capability.recommendation_evidence.value != "experimental"
            or capability.lifecycle.value != "proof_eligible"
        ):
            raise PassportHandoffError(
                "P1 capability metadata no longer matches the handoff table"
            )
    if (
        passport.method_space_version != _EXPECTED_METHOD_SPACE_VERSION
        or passport.method_space_digest != _EXPECTED_METHOD_SPACE_DIGEST
        or passport.ruleset_version != _EXPECTED_RULESET_VERSION
        or passport.clarification_registry_digest
        != _EXPECTED_CLARIFICATION_REGISTRY_DIGEST
    ):
        raise PassportHandoffError(
            "passport Method Space or clarification registry is stale"
        )


def _validate_semantics_and_roles(
    request: ResearchRequest,
    row: _HandoffRow,
) -> dict[TargetRole, tuple[str, ...]]:
    if request.surface is not ProductSurface.EXPERIMENTAL:
        raise PassportHandoffError("P1 handoff requires the experimental surface")
    if request.question.role_hints:
        raise PassportHandoffError("P1 handoff rejects extra question roles")
    _require_user_fact(
        request.question.research_goal,
        row.goal,
        "question.research_goal",
    )
    _require_user_fact(
        request.question.causal_intent,
        CausalIntent.NONCAUSAL,
        "question.causal_intent",
    )
    _require_user_fact(request.estimand.template, row.template, "estimand.template")
    _require_user_fact(
        request.estimand.claim_basis,
        row.claim_basis,
        "estimand.claim_basis",
    )
    _require_user_fact(
        request.estimand.effect_scale,
        row.effect_scale,
        "estimand.effect_scale",
    )
    if row.association_target is None:
        _require_not_applicable(
            request.estimand.association_target,
            "estimand.association_target",
        )
    else:
        _require_user_fact(
            request.estimand.association_target,
            row.association_target,
            "estimand.association_target",
        )
    if row.contrast is None:
        _require_not_applicable(request.estimand.contrast, "estimand.contrast")
    else:
        _require_user_fact(
            request.estimand.contrast,
            row.contrast,
            "estimand.contrast",
        )
    _require_user_fact(
        request.study.dependence_structure,
        row.dependence,
        "study.dependence_structure",
    )

    actual_roles = tuple(binding.role for binding in request.estimand.target_roles)
    if actual_roles != row.target_roles or len(set(actual_roles)) != len(actual_roles):
        raise PassportHandoffError(
            "target roles do not exactly match the selected capability"
        )
    values: dict[TargetRole, tuple[str, ...]] = {}
    available = set(request.available_variable_ids)
    for binding in request.estimand.target_roles:
        fact = binding.variable_ids
        if (
            fact.state is not FactState.USER_CONFIRMED
            or not isinstance(fact.value, tuple)
            or not fact.value
            or len(set(fact.value)) != len(fact.value)
        ):
            raise PassportHandoffError(
                f"target role {binding.role.value} is not exact user authority"
            )
        if not set(fact.value).issubset(available):
            raise PassportHandoffError(
                f"target role {binding.role.value} references an unavailable variable"
            )
        values[binding.role] = fact.value

    expected_study_roles = (StudyRole.CLUSTER, StudyRole.WEIGHT)
    actual_study_roles = tuple(
        binding.role for binding in request.study.design_roles
    )
    if actual_study_roles != expected_study_roles:
        raise PassportHandoffError(
            "study roles do not exactly match the unweighted P1 boundary"
        )
    for binding in request.study.design_roles:
        if (
            binding.variable_ids.state is not FactState.USER_CONFIRMED
            or binding.variable_ids.value != ()
        ):
            raise PassportHandoffError(
                "cluster and weight roles must be explicitly confirmed empty"
            )
    return values


def _require_one(values: tuple[str, ...], field: str) -> str:
    if len(values) != 1:
        raise PassportHandoffError(f"{field} requires exactly one variable")
    return values[0]


def _build_params(
    row: _HandoffRow,
    request: ResearchRequest,
    roles: dict[TargetRole, tuple[str, ...]],
) -> dict[str, object]:
    if row.capability_key == _SUMMARY_KEY:
        return {
            "schema_version": 1,
            "variables": list(roles[TargetRole.OUTCOME]),
            "group": None,
            "include_missing_counts": True,
            "language": request.question.language.value,
        }
    if row.capability_key == _FREQUENCY_KEY:
        return {
            "schema_version": 1,
            "mode": "frequency",
            "variables": list(roles[TargetRole.OUTCOME]),
            "language": request.question.language.value,
        }
    if row.capability_key in {_PEARSON_KEY, _SPEARMAN_KEY}:
        outcome = _require_one(roles[TargetRole.OUTCOME], "outcome role")
        predictor = _require_one(
            roles[TargetRole.FOCAL_PREDICTOR],
            "focal predictor role",
        )
        if outcome == predictor:
            raise PassportHandoffError(
                "outcome and focal predictor must be distinct"
            )
        return {
            "schema_version": 1,
            "pairs": [[outcome, predictor]],
            "method": (
                "pearson" if row.capability_key == _PEARSON_KEY else "spearman"
            ),
            "missing_policy": "pairwise",
            "p_adjust": "none",
        }
    if row.capability_key == _WELCH_KEY:
        outcome = _require_one(roles[TargetRole.OUTCOME], "outcome role")
        group = _require_one(roles[TargetRole.GROUP], "group role")
        if outcome == group:
            raise PassportHandoffError("outcome and group roles must be distinct")
        return {
            "schema_version": 1,
            "dv": outcome,
            "group": group,
            "routing_policy": {"preset": "always_welch"},
        }
    if row.capability_key == _PAIRED_KEY:
        outcome = _require_one(roles[TargetRole.OUTCOME], "outcome role")
        repeated = roles[TargetRole.REPEATED_MEASURE]
        order = request.study.repeated_measure_order
        if (
            len(repeated) != 2
            or order.state is not FactState.USER_CONFIRMED
            or order.value != repeated
            or outcome != repeated[-1]
        ):
            raise PassportHandoffError(
                "paired outcome, repeated role, and repeated order do not match"
            )
        return {
            "schema_version": 1,
            "before": repeated[0],
            "after": repeated[1],
            "routing_policy": {"preset": "classic"},
        }
    raise PassportHandoffError("capability has no exact P1 handoff row")


def _validate_current_step_schema(
    step_type: str,
    params: dict[str, object],
) -> None:
    if step_type == "stats.descriptives_table1":
        from modori.steps.descriptives_table1 import DescriptivesTableStep

        step_class = DescriptivesTableStep
    elif step_type == "stats.frequency_crosstab":
        from modori.steps.frequency_crosstab import FrequencyCrosstabStep

        step_class = FrequencyCrosstabStep
    elif step_type == "stats.correlation":
        from modori.steps.correlation import CorrelationStep

        step_class = CorrelationStep
    elif step_type in {"stats.compare_groups", "stats.paired_comparison"}:
        from modori.steps.statistics import CompareGroupsStep, PairedComparisonStep

        step_class = (
            CompareGroupsStep
            if step_type == "stats.compare_groups"
            else PairedComparisonStep
        )
    else:  # pragma: no cover - the closed row table prevents this branch.
        raise PassportHandoffError("handoff row names an unknown step type")
    try:
        migrated = step_class.migrate_params(dict(params))
        step_class.validate_params(migrated)
    except (TypeError, ValueError) as exc:
        raise PassportHandoffError(
            "exact handoff params fail the current step schema"
        ) from exc


def map_passport_to_step(
    passport: AnalysisPassport,
    request: ResearchRequest,
    *,
    current_dataset_fingerprint: str,
) -> PassportStepMapping:
    """Map one current V2 local passport through the sole six-row P1 oracle."""

    if not isinstance(passport, AnalysisPassport):
        raise PassportHandoffError("passport must be an AnalysisPassport")
    if not isinstance(request, ResearchRequest):
        raise PassportHandoffError("request must be a ResearchRequest")
    if passport.envelope.schema_version != 2:
        raise PassportHandoffError("handoff requires a version 2 passport")
    if (
        not isinstance(current_dataset_fingerprint, str)
        or _DIGEST_RE.fullmatch(current_dataset_fingerprint) is None
    ):
        raise PassportHandoffError("current dataset fingerprint is malformed")
    if current_dataset_fingerprint != request.current_dataset_fingerprint:
        raise PassportHandoffError("current dataset fingerprint is stale")
    if current_dataset_fingerprint != request.study.dataset_fingerprint:
        raise PassportHandoffError(
            "current dataset fingerprint does not match the bound study"
        )
    try:
        validate_passport_request_binding(passport, request)
    except ResearchServiceError as exc:
        raise PassportHandoffError(
            "passport does not bind the current request"
        ) from exc
    if passport.action is not PrimaryAction.RECOMMEND_LOCAL:
        raise PassportHandoffError(
            "only a recommend-local passport can enter handoff"
        )
    _validate_catalog_identity(passport)
    payload = passport.recommend_local
    if payload is None or len(payload.capability_keys) != 1:
        raise PassportHandoffError(
            "handoff requires exactly one local capability"
        )
    capability_key = payload.capability_keys[0]
    row = _ROWS_BY_KEY.get(capability_key)
    if row is None:
        raise PassportHandoffError(
            "capability is outside the exact six-row P1 handoff"
        )
    if (
        payload.local_analysis_kinds != (row.local_analysis_kind,)
        or payload.claim_permissions != (row.claim_permission,)
        or payload.experimental is not True
        or payload.auto_selected is not False
        or payload.requires_explicit_configure_confirm_run is not True
    ):
        raise PassportHandoffError(
            "passport local payload does not match the exact handoff row"
        )
    roles = _validate_semantics_and_roles(request, row)
    params = _build_params(row, request, roles)
    _validate_current_step_schema(row.step_type, params)
    try:
        params_bytes = canonical_bytes(params)
        artifact = LedgerArtifact.from_value(passport)
        return PassportStepMapping.create(
            passport_artifact_id=artifact.artifact_id,
            passport_digest=passport.digest(),
            capability_key=capability_key,
            dataset_fingerprint=current_dataset_fingerprint,
            step_type=row.step_type,
            canonical_step_params=params_bytes,
        )
    except (CanonicalizationError, LedgerContractError, ValueError, TypeError) as exc:
        raise PassportHandoffError(
            "passport handoff could not be sealed"
        ) from exc
