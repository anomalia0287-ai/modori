from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from modori.research_os.contracts import (
    CausalIntent,
    ContractError,
    EstimandSpec,
    Fact,
    FactState,
    QuestionSpec,
    StudyRole,
    StudySpec,
    TargetRole,
)
from modori.research_os.method_space import MethodSpace
from modori.research_os.p1_catalog import build_p1_method_space
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


@dataclass(frozen=True)
class ResearchRequest:
    question: QuestionSpec
    estimand: EstimandSpec
    study: StudySpec
    current_dataset_fingerprint: str
    available_variable_ids: tuple[str, ...]
    surface: ProductSurface = ProductSurface.EXPERIMENTAL
    question_budget_remaining: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.question, QuestionSpec):
            raise ResearchServiceError("question must be a QuestionSpec")
        if not isinstance(self.estimand, EstimandSpec):
            raise ResearchServiceError("estimand must be an EstimandSpec")
        if not isinstance(self.study, StudySpec):
            raise ResearchServiceError("study must be a StudySpec")
        if not _FINGERPRINT_RE.fullmatch(self.current_dataset_fingerprint):
            raise ResearchServiceError(
                "current_dataset_fingerprint must be a lowercase SHA-256 digest"
            )
        if self.question_budget_remaining < 0:
            raise ResearchServiceError(
                "question_budget_remaining cannot be negative"
            )
        if len(set(self.available_variable_ids)) != len(self.available_variable_ids):
            raise ResearchServiceError("available_variable_ids cannot contain duplicates")
        for variable_id in self.available_variable_ids:
            if not isinstance(variable_id, str) or not variable_id.strip():
                raise ResearchServiceError(
                    "available_variable_ids must contain non-empty strings"
                )


class ResearchOsService:
    """Resolve approved structures without accepting data or executing analysis."""

    def __init__(self, method_space: MethodSpace | None = None) -> None:
        self._method_space = method_space or build_p1_method_space()
        self._resolver = C1Resolver(self._method_space)

    @property
    def method_space_digest(self) -> str:
        return self._method_space.digest()

    def resolve(self, request: ResearchRequest) -> ResolutionDecision:
        integrity_errors = self._integrity_errors(request)
        context = ResolutionContext(
            facts=self._facts_from_specs(request),
            surface=request.surface,
            integrity_errors=integrity_errors,
            question_budget_remaining=request.question_budget_remaining,
        )
        decision = self._resolver.resolve(context)
        if integrity_errors:
            return decision
        if self._is_confirmed_causal_request(request.question):
            return ResolutionDecision(
                action=PrimaryAction.ABSTAIN,
                reason_codes=("unsupported_causal_target",),
                rule_trace=decision.rule_trace,
            )
        return decision

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
