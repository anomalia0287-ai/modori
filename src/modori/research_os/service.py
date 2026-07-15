from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import unicodedata

from modori.research_os.contracts import (
    CausalIntent,
    ContractError,
    EstimandSpec,
    Fact,
    FactState,
    QuestionSpec,
    SchemaEnvelope,
    StudyRole,
    StudySpec,
    TargetRole,
    canonical_digest,
)
from modori.research_os.clarification import (
    ClarificationError,
    ClarificationRegistry,
    ClarificationSpec,
)
from modori.research_os.decision_evidence import DecisionEvidenceRef
from modori.research_os.method_space import (
    LifecycleStatus,
    MethodSpace,
    RecommendationEvidence,
    RouteEvidence,
    SupportStatus,
)
from modori.research_os.p1_catalog import build_p1_method_space
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.passport import (
    AbstainPayload,
    AnalysisPassport,
    ClaimClass,
    ClarifyPayload,
    ComponentRevisionRef,
    RecommendLocalPayload,
    RouteExternalPayload,
)
from modori.research_os.resolver import (
    C1Resolver,
    PrimaryAction,
    ProductSurface,
    ResolutionContext,
    ResolutionDecision,
)


class ResearchServiceError(ValueError):
    """Raised when a structure-only service request is malformed."""


_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")

_RECOVERY_BY_REASON = {
    "integrity:project_id_mismatch": "align_component_project_ids",
    "integrity:dataset_fingerprint_mismatch": "rebind_specs_to_current_dataset",
    "integrity:unknown_variable_reference": "repair_variable_role_bindings",
    "integrity:invalid_fact_value": "repair_malformed_fact_value",
    "unsupported_causal_target": (
        "declare_noncausal_or_use_external_causal_workflow"
    ),
    "clarification_budget_exhausted": (
        "resolve_blocking_facts_or_restart_question_budget"
    ),
    "clarification_answer_unavailable": (
        "complete_structured_intake_or_revise_scope"
    ),
    "planner_search_limit_exceeded": (
        "complete_structured_intake_or_reduce_method_space"
    ),
    "integrity:no_decision_relevant_clarification": (
        "repair_clarification_registry"
    ),
    "integrity:invalid_planner_result": "repair_clarification_planner",
    "no_surface_authorized_capability": (
        "enable_experimental_surface_or_wait_for_validation"
    ),
    "no_verified_external_route": "verify_external_route_or_revise_target",
    "no_stable_supported_capability": (
        "revise_target_or_expand_verified_method_space"
    ),
}
_UNMAPPED_RECOVERY = "manual_review_required_for_unmapped_abstention"


@dataclass(frozen=True)
class ResearchRequest:
    question: QuestionSpec
    estimand: EstimandSpec
    study: StudySpec
    current_dataset_fingerprint: str
    available_variable_ids: tuple[str, ...]
    surface: ProductSurface = ProductSurface.EXPERIMENTAL
    question_budget_remaining: int = 3
    decision_evidence_refs: tuple[DecisionEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.question, QuestionSpec):
            raise ResearchServiceError("question must be a QuestionSpec")
        if not isinstance(self.estimand, EstimandSpec):
            raise ResearchServiceError("estimand must be an EstimandSpec")
        if not isinstance(self.study, StudySpec):
            raise ResearchServiceError("study must be a StudySpec")
        if not isinstance(self.current_dataset_fingerprint, str) or not _FINGERPRINT_RE.fullmatch(
            self.current_dataset_fingerprint
        ):
            raise ResearchServiceError(
                "current_dataset_fingerprint must be a lowercase SHA-256 digest"
            )
        if type(self.question_budget_remaining) is not int:
            raise ResearchServiceError(
                "question_budget_remaining must be an integer"
            )
        if self.question_budget_remaining < 0:
            raise ResearchServiceError(
                "question_budget_remaining cannot be negative"
            )
        if self.question_budget_remaining > 3:
            raise ResearchServiceError("question_budget_remaining cannot exceed 3")
        if not isinstance(self.available_variable_ids, tuple):
            raise ResearchServiceError("available_variable_ids must be a tuple")
        if len(set(self.available_variable_ids)) != len(self.available_variable_ids):
            raise ResearchServiceError("available_variable_ids cannot contain duplicates")
        for variable_id in self.available_variable_ids:
            if not isinstance(variable_id, str) or not variable_id.strip():
                raise ResearchServiceError(
                    "available_variable_ids must contain non-empty strings"
                )
            if variable_id != unicodedata.normalize("NFC", variable_id):
                raise ResearchServiceError(
                    "available_variable_ids must use canonical NFC Unicode"
                )
        if not isinstance(self.decision_evidence_refs, tuple):
            raise ResearchServiceError("decision_evidence_refs must be a tuple")
        if any(
            not isinstance(reference, DecisionEvidenceRef)
            for reference in self.decision_evidence_refs
        ):
            raise ResearchServiceError(
                "decision_evidence_refs must contain DecisionEvidenceRef values"
            )
        evidence_ids = tuple(
            reference.evidence_id for reference in self.decision_evidence_refs
        )
        evidence_digests = tuple(
            reference.evidence_digest for reference in self.decision_evidence_refs
        )
        sequences = tuple(
            reference.event_sequence for reference in self.decision_evidence_refs
        )
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ResearchServiceError(
                "decision_evidence_refs cannot repeat an evidence ID"
            )
        if len(set(evidence_digests)) != len(evidence_digests):
            raise ResearchServiceError(
                "decision_evidence_refs cannot repeat an evidence digest"
            )
        if sequences != tuple(sorted(sequences)) or len(set(sequences)) != len(
            sequences
        ):
            raise ResearchServiceError(
                "decision_evidence_refs must have strictly increasing event sequences"
            )
        if self.decision_evidence_refs:
            project_ids = {
                self.question.envelope.project_id,
                self.estimand.envelope.project_id,
                self.study.envelope.project_id,
            }
            if len(project_ids) != 1:
                raise ResearchServiceError(
                    "decision evidence requires aligned component project IDs"
                )
            project_id = next(iter(project_ids))
            if any(
                reference.project_id != project_id
                for reference in self.decision_evidence_refs
            ):
                raise ResearchServiceError(
                    "decision evidence project ID must match request components"
                )


class ResearchOsService:
    """Resolve approved structures without accepting data or executing analysis."""

    def __init__(
        self,
        method_space: MethodSpace | None = None,
        clarification_registry: ClarificationRegistry | None = None,
    ) -> None:
        self._method_space = method_space or build_p1_method_space()
        self._clarification_registry = (
            clarification_registry or build_p1_clarification_registry()
        )
        if not isinstance(self._method_space, MethodSpace):
            raise ResearchServiceError("method_space must be a MethodSpace")
        if not isinstance(self._clarification_registry, ClarificationRegistry):
            raise ResearchServiceError(
                "clarification_registry must be a ClarificationRegistry"
            )
        required_question_ids = {
            rule.clarification_id
            for rule in self._method_space.rules
            if rule.clarification_id is not None
        }
        if set(self._clarification_registry.question_ids) != required_question_ids:
            raise ResearchServiceError(
                "clarification registry must exactly cover Method Space questions"
            )
        self._resolver = C1Resolver(
            self._method_space,
            self._clarification_registry,
        )

    @property
    def method_space_digest(self) -> str:
        return self._method_space.digest()

    @property
    def method_space_version(self) -> str:
        return self._method_space.version

    @property
    def ruleset_version(self) -> str:
        return self._method_space.ruleset_version

    def resolve(self, request: ResearchRequest) -> ResolutionDecision:
        integrity_errors = self._integrity_errors(request)
        context = ResolutionContext(
            facts=self._facts_from_specs(request),
            surface=request.surface,
            integrity_errors=integrity_errors,
            question_budget_remaining=request.question_budget_remaining,
        )
        resolve_context = self._resolver.resolve
        decision = resolve_context(context)
        if integrity_errors:
            return decision
        if self._is_confirmed_causal_request(request.question):
            return ResolutionDecision(
                action=PrimaryAction.ABSTAIN,
                reason_codes=("unsupported_causal_target",),
                rule_trace=decision.rule_trace,
            )
        return decision

    def plan(
        self,
        request: ResearchRequest,
        passport_envelope: SchemaEnvelope,
    ) -> AnalysisPassport:
        """Bind one resolver decision to an authority-free immutable passport."""

        self._validate_passport_binding(request, passport_envelope)
        resolve_request = self.resolve
        decision = resolve_request(request)
        recommend_local: RecommendLocalPayload | None = None
        clarify: ClarifyPayload | None = None
        route_external: RouteExternalPayload | None = None
        abstain: AbstainPayload | None = None

        if decision.action is PrimaryAction.RECOMMEND_LOCAL:
            recommend_local = self._recommend_payload(decision)
        elif decision.action is PrimaryAction.CLARIFY:
            clarify = self._clarify_payload(decision)
        elif decision.action is PrimaryAction.ROUTE_EXTERNAL:
            route_external = self._route_payload(decision)
        else:
            abstain = self._abstain_payload(decision)

        return AnalysisPassport(
            envelope=passport_envelope,
            question_ref=self._component_ref(request.question),
            estimand_ref=self._component_ref(request.estimand),
            study_ref=self._component_ref(request.study),
            dataset_fingerprint=request.current_dataset_fingerprint,
            method_space_version=self._method_space.version,
            method_space_digest=self._method_space.digest(),
            ruleset_version=self._method_space.ruleset_version,
            resolver_decision_digest=canonical_digest(
                {"semantic_signature": decision.semantic_signature}
            ),
            decision_evidence_digests=tuple(
                reference.evidence_digest
                for reference in request.decision_evidence_refs
            ),
            recommend_local=recommend_local,
            clarify=clarify,
            route_external=route_external,
            abstain=abstain,
        )

    def clarifications_for(
        self,
        decision: ResolutionDecision,
    ) -> tuple[ClarificationSpec, ...]:
        """Return exact neutral questions for a clarify decision, or none."""

        if not isinstance(decision, ResolutionDecision):
            raise ResearchServiceError("decision must be a ResolutionDecision")
        if decision.action is not PrimaryAction.CLARIFY:
            return ()
        if len(decision.clarification_ids) != len(
            decision.blocking_fact_addresses
        ):
            raise ResearchServiceError(
                "clarification IDs and blocking facts must have equal length"
            )
        questions: list[ClarificationSpec] = []
        for question_id, fact_address in zip(
            decision.clarification_ids,
            decision.blocking_fact_addresses,
            strict=True,
        ):
            try:
                question = self._clarification_registry.get(question_id)
            except ClarificationError as exc:
                raise ResearchServiceError(
                    f"resolver referenced an unregistered question: {question_id}"
                ) from exc
            if question.fact_address != fact_address:
                raise ResearchServiceError(
                    f"clarification fact address mismatch for {question_id}"
                )
            questions.append(question)
        return tuple(questions)

    @staticmethod
    def _validate_passport_binding(
        request: ResearchRequest,
        passport_envelope: SchemaEnvelope,
    ) -> None:
        if not isinstance(request, ResearchRequest):
            raise ResearchServiceError("request must be a ResearchRequest")
        if not isinstance(passport_envelope, SchemaEnvelope):
            raise ResearchServiceError(
                "passport_envelope must be a SchemaEnvelope"
            )
        if (
            passport_envelope.schema_id != "modori.analysis_passport"
            or passport_envelope.schema_version != 1
        ):
            raise ResearchServiceError(
                "passport envelope must use modori.analysis_passport version 1"
            )
        component_project_ids = {
            request.question.envelope.project_id,
            request.estimand.envelope.project_id,
            request.study.envelope.project_id,
        }
        if len(component_project_ids) != 1:
            raise ResearchServiceError("component project IDs must match")
        if passport_envelope.project_id not in component_project_ids:
            raise ResearchServiceError(
                "passport project ID must match all request components"
            )

    @staticmethod
    def _component_ref(
        spec: QuestionSpec | EstimandSpec | StudySpec,
    ) -> ComponentRevisionRef:
        return ComponentRevisionRef(
            schema_id=spec.envelope.schema_id,
            object_id=spec.envelope.object_id,
            revision=spec.envelope.revision,
            digest=spec.digest(),
        )

    def _recommend_payload(
        self,
        decision: ResolutionDecision,
    ) -> RecommendLocalPayload:
        capabilities = {
            capability.identity.key: capability
            for capability in self._method_space.capabilities
        }
        local_analysis_kinds: list[str] = []
        claim_permissions: list[ClaimClass] = []
        experimental = False
        for capability_key in decision.capability_keys:
            capability = capabilities.get(capability_key)
            if (
                capability is None
                or capability.support is not SupportStatus.LOCAL_COMPUTE
                or capability.local_analysis_kind is None
            ):
                raise ResearchServiceError(
                    "resolver returned an invalid local capability"
                )
            local_analysis_kinds.append(capability.local_analysis_kind)
            for permission in capability.claim_permissions:
                try:
                    claim_class = ClaimClass(permission)
                except ValueError as exc:
                    raise ResearchServiceError(
                        f"capability has an unknown claim permission: {permission}"
                    ) from exc
                if claim_class not in claim_permissions:
                    claim_permissions.append(claim_class)
            experimental = experimental or (
                capability.recommendation_evidence
                is not RecommendationEvidence.VALIDATED
                or capability.lifecycle is not LifecycleStatus.RELEASED
            )
        return RecommendLocalPayload(
            capability_keys=decision.capability_keys,
            local_analysis_kinds=tuple(local_analysis_kinds),
            claim_permissions=tuple(claim_permissions),
            experimental=experimental,
        )

    def _clarify_payload(self, decision: ResolutionDecision) -> ClarifyPayload:
        self.clarifications_for(decision)
        return ClarifyPayload(
            question_ids=decision.clarification_ids,
            blocking_fact_addresses=decision.blocking_fact_addresses,
        )

    def _route_payload(self, decision: ResolutionDecision) -> RouteExternalPayload:
        routes = {route.route_id: route for route in self._method_space.routes}
        privacy_boundaries: list[str] = []
        for route_id in decision.route_ids:
            route = routes.get(route_id)
            if (
                route is None
                or route.recommendation_evidence
                is not RecommendationEvidence.VALIDATED
                or route.route_evidence is not RouteEvidence.ROUNDTRIP_VERIFIED
                or route.lifecycle is not LifecycleStatus.RELEASED
            ):
                raise ResearchServiceError(
                    "resolver returned an unverified external route"
                )
            privacy_boundaries.append(route.privacy_boundary)
        return RouteExternalPayload(
            route_ids=decision.route_ids,
            privacy_boundary_ids=tuple(privacy_boundaries),
        )

    @staticmethod
    def _abstain_payload(decision: ResolutionDecision) -> AbstainPayload:
        recovery_requirements: list[str] = []
        for reason_code in decision.reason_codes:
            requirement = _RECOVERY_BY_REASON.get(reason_code, _UNMAPPED_RECOVERY)
            if requirement not in recovery_requirements:
                recovery_requirements.append(requirement)
        return AbstainPayload(
            reason_codes=decision.reason_codes,
            recovery_requirement_ids=tuple(recovery_requirements),
        )

    @staticmethod
    def _integrity_errors(request: ResearchRequest) -> tuple[str, ...]:
        errors: list[str] = []
        project_ids = {
            request.question.envelope.project_id,
            request.estimand.envelope.project_id,
            request.study.envelope.project_id,
        }
        if len(project_ids) != 1:
            errors.append("project_id_mismatch")
        if request.current_dataset_fingerprint != request.study.dataset_fingerprint:
            errors.append("dataset_fingerprint_mismatch")
        available = set(request.available_variable_ids)
        try:
            request.estimand.validate_variable_references(available)
            request.study.validate_variable_references(available)
        except ContractError:
            errors.append("unknown_variable_reference")
        return tuple(errors)

    @staticmethod
    def _is_confirmed_causal_request(question: QuestionSpec) -> bool:
        return (
            question.causal_intent.state
            in {
                FactState.OBSERVED,
                FactState.USER_CONFIRMED,
            }
            and question.causal_intent.value is CausalIntent.CAUSAL
        )

    @staticmethod
    def _missing_role_fact(role: str) -> Fact[tuple[str, ...]]:
        return Fact.unknown(reason_code=f"missing_{role}_role_binding")

    def _facts_from_specs(self, request: ResearchRequest) -> dict[str, Fact[Any]]:
        question = request.question
        estimand = request.estimand
        study = request.study
        facts: dict[str, Fact[Any]] = {
            "question.research_goal": question.research_goal,
            "question.causal_intent": question.causal_intent,
            "estimand.template": estimand.template,
            "estimand.claim_basis": estimand.claim_basis,
            "estimand.target_population": estimand.target_population,
            "estimand.unit_of_analysis": estimand.unit_of_analysis,
            "estimand.contrast": estimand.contrast,
            "estimand.time_scope": estimand.time_scope,
            "estimand.effect_scale": estimand.effect_scale,
            "estimand.association_target": estimand.association_target,
            "study.unit_of_observation": study.unit_of_observation,
            "study.unit_of_analysis": study.unit_of_analysis,
            "study.design_family": study.design_family,
            "study.data_layout": study.data_layout,
            "study.temporal_structure": study.temporal_structure,
            "study.dependence_structure": study.dependence_structure,
            "study.assignment_mechanism": study.assignment_mechanism,
            "study.sampling_design": study.sampling_design,
            "study.repeated_measure_order": study.repeated_measure_order,
        }
        target_roles = {binding.role: binding.variable_ids for binding in estimand.target_roles}
        for role in TargetRole:
            facts[f"estimand.role.{role.value}"] = target_roles.get(
                role,
                self._missing_role_fact(role.value),
            )
        design_roles = {binding.role: binding.variable_ids for binding in study.design_roles}
        for role in StudyRole:
            facts[f"study.role.{role.value}"] = design_roles.get(
                role,
                self._missing_role_fact(role.value),
            )
        return facts
