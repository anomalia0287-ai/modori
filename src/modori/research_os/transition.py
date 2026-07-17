from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any, TypeVar

from modori.research_os.clarification import (
    AnswerKind,
    BranchMatchKind,
    ClarificationError,
    ClarificationLifecycle,
    ClarificationRegistry,
    ClarificationSpec,
)
from modori.research_os.contracts import (
    AssociationTarget,
    CausalIntent,
    ClaimBasis,
    ContrastKind,
    ContractError,
    DependenceKind,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    FactState,
    QuestionSpec,
    ResearchGoal,
    SchemaEnvelope,
    StaleSnapshot,
    StudyRole,
    StudyRoleBinding,
    StudySpec,
    TargetRole,
    TargetRoleBinding,
    canonical_digest,
)
from modori.research_os.decision_evidence import (
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    DecisionEvidenceKind,
    DecisionEvidenceRef,
    RevisionAcceptanceCertificate,
)
from modori.research_os.p1_clarifications import build_p1_clarification_registry
from modori.research_os.passport import (
    AnalysisPassport,
    ClarifyPayloadV2,
    ComponentRevisionRef,
)
from modori.research_os.passport_audit import (
    PassportRegistryAuditStatus,
    audit_passport_registry,
)
from modori.research_os.resolver import PrimaryAction
from modori.research_os.service import (
    ResearchRequest,
    ResearchServiceError,
    validate_passport_request_binding,
)


class TransitionError(ValueError):
    """Raised when clarification evidence cannot create a safe revision."""


class PassportMigrationRequired(TransitionError):
    """Raised when historical V1 authority needs a fresh V2 replan."""


_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_CHOICE_ANSWER_KINDS = {
    AnswerKind.YES_NO,
    AnswerKind.SINGLE_CHOICE,
    AnswerKind.LEVEL_CHOICE,
    AnswerKind.CONFLICT_RESOLUTION,
}
_CURRENT_FACT_STATES = {
    FactState.OBSERVED,
    FactState.INFERRED,
    FactState.USER_CONFIRMED,
}
_QUESTION_FACTS = {
    "question.research_goal": ("research_goal", ResearchGoal),
    "question.causal_intent": ("causal_intent", CausalIntent),
}
_ESTIMAND_FACTS = {
    "estimand.template": ("template", EstimandTemplate),
    "estimand.claim_basis": ("claim_basis", ClaimBasis),
    "estimand.contrast": ("contrast", ContrastKind),
    "estimand.effect_scale": ("effect_scale", EffectScale),
    "estimand.association_target": ("association_target", AssociationTarget),
}
_TARGET_ROLE_FACTS = {
    "estimand.role.outcome": TargetRole.OUTCOME,
    "estimand.role.focal_predictor": TargetRole.FOCAL_PREDICTOR,
    "estimand.role.group": TargetRole.GROUP,
    "estimand.role.repeated_measure": TargetRole.REPEATED_MEASURE,
}
_STUDY_FACTS = {
    "study.dependence_structure": ("dependence_structure", DependenceKind),
}
_STUDY_ROLE_FACTS = {
    "study.role.weight": StudyRole.WEIGHT,
    "study.role.cluster": StudyRole.CLUSTER,
}
_T = TypeVar("_T")


def _require_reference(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransitionError(f"{field_name} must be a non-empty string")
    if not _REFERENCE_RE.fullmatch(value):
        raise TransitionError(f"{field_name} must be a closed reference")
    return value


def _require_digest(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise TransitionError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def _component_ref(spec: QuestionSpec | EstimandSpec | StudySpec) -> ComponentRevisionRef:
    return ComponentRevisionRef(
        schema_id=spec.envelope.schema_id,
        object_id=spec.envelope.object_id,
        revision=spec.envelope.revision,
        digest=spec.digest(),
    )


def _next_envelope(source: SchemaEnvelope, event_ref: str) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=source.schema_id,
        schema_version=source.schema_version,
        project_id=source.project_id,
        object_id=source.object_id,
        revision=source.revision + 1,
        supersedes_revision=source.revision,
        created_event_ref=event_ref,
    )


def _unknown_fact(question_id: str) -> Fact[Any]:
    return Fact.unknown(reason_code=f"user_not_sure:{question_id}")


def _confirmed_fact(value: _T, event_id: str) -> Fact[_T]:
    return Fact.user_confirmed(value, provenance_refs=(event_id,))


def _invalidate_fact(fact: Fact[_T], question_id: str) -> Fact[_T]:
    reason = f"invalidated_by:{question_id}"
    if fact.state in _CURRENT_FACT_STATES:
        return Fact.stale(
            StaleSnapshot(
                value=fact.value,
                provenance_refs=fact.provenance_refs,
                invalidation_reason=reason,
            ),
            reason_code=reason,
        )
    if fact.state is FactState.STALE:
        return fact
    return Fact.unknown(reason_code=reason)


@dataclass(frozen=True)
class RevisionCandidate:
    project_id: str
    source_passport_digest: str
    answer_event_id: str
    answer_event_sequence: int
    answer_event_digest: str
    base_question_ref: ComponentRevisionRef
    base_estimand_ref: ComponentRevisionRef
    base_study_ref: ComponentRevisionRef
    base_evidence_digests: tuple[str, ...]
    dataset_fingerprint: str
    proposed_question: QuestionSpec | None
    proposed_estimand: EstimandSpec | None
    proposed_study: StudySpec | None
    next_question_budget_remaining: int
    requires_acceptance: bool
    acceptance_certificate_id: str | None

    def __post_init__(self) -> None:
        _require_reference(self.project_id, "project_id")
        _require_digest(self.source_passport_digest, "source_passport_digest")
        _require_reference(self.answer_event_id, "answer_event_id")
        if type(self.answer_event_sequence) is not int or self.answer_event_sequence < 1:
            raise TransitionError("answer_event_sequence must be a positive integer")
        _require_digest(self.answer_event_digest, "answer_event_digest")
        for reference, field_name in (
            (self.base_question_ref, "base_question_ref"),
            (self.base_estimand_ref, "base_estimand_ref"),
            (self.base_study_ref, "base_study_ref"),
        ):
            if not isinstance(reference, ComponentRevisionRef):
                raise TransitionError(f"{field_name} must be a ComponentRevisionRef")
        if not isinstance(self.base_evidence_digests, tuple):
            raise TransitionError("base_evidence_digests must be a tuple")
        for digest in self.base_evidence_digests:
            _require_digest(digest, "base_evidence_digests")
        if len(set(self.base_evidence_digests)) != len(self.base_evidence_digests):
            raise TransitionError("base_evidence_digests cannot contain duplicates")
        _require_digest(self.dataset_fingerprint, "dataset_fingerprint")
        proposals = (
            self.proposed_question,
            self.proposed_estimand,
            self.proposed_study,
        )
        if not any(proposal is not None for proposal in proposals):
            raise TransitionError("revision candidate must change at least one component")
        expected_types = (
            (self.proposed_question, QuestionSpec, "proposed_question"),
            (self.proposed_estimand, EstimandSpec, "proposed_estimand"),
            (self.proposed_study, StudySpec, "proposed_study"),
        )
        for proposal, proposal_type, field_name in expected_types:
            if proposal is not None and not isinstance(proposal, proposal_type):
                raise TransitionError(f"{field_name} has the wrong type")
            if proposal is not None and proposal.envelope.project_id != self.project_id:
                raise TransitionError(f"{field_name} project ID mismatch")
        if self.proposed_study is not None and (
            self.proposed_study.dataset_fingerprint != self.dataset_fingerprint
        ):
            raise TransitionError("proposed_study dataset fingerprint mismatch")
        if type(self.next_question_budget_remaining) is not int or not (
            0 <= self.next_question_budget_remaining <= 3
        ):
            raise TransitionError(
                "next_question_budget_remaining must be an integer from 0 to 3"
            )
        if type(self.requires_acceptance) is not bool:
            raise TransitionError("requires_acceptance must be a boolean")
        if self.requires_acceptance is not (self.proposed_estimand is not None):
            raise TransitionError(
                "requires_acceptance must exactly match an estimand revision"
            )
        if self.requires_acceptance:
            _require_reference(
                self.acceptance_certificate_id,
                "acceptance_certificate_id",
            )
        elif self.acceptance_certificate_id is not None:
            raise TransitionError(
                "ready candidate cannot reserve an acceptance certificate"
            )
        expected_event_ref = (
            self.acceptance_certificate_id
            if self.requires_acceptance
            else self.answer_event_id
        )
        for proposal, base_ref, field_name in (
            (self.proposed_question, self.base_question_ref, "proposed_question"),
            (self.proposed_estimand, self.base_estimand_ref, "proposed_estimand"),
            (self.proposed_study, self.base_study_ref, "proposed_study"),
        ):
            if proposal is None:
                continue
            envelope = proposal.envelope
            if (
                envelope.schema_id != base_ref.schema_id
                or envelope.object_id != base_ref.object_id
                or envelope.revision != base_ref.revision + 1
                or envelope.supersedes_revision != base_ref.revision
            ):
                raise TransitionError(
                    f"{field_name} must be the exact next revision of its base"
                )
            if envelope.created_event_ref != expected_event_ref:
                raise TransitionError(
                    f"{field_name} created_event_ref does not match transition evidence"
                )

    @property
    def changed_component_digests(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                proposal.digest()
                for proposal in (
                    self.proposed_question,
                    self.proposed_estimand,
                    self.proposed_study,
                )
                if proposal is not None
            )
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "source_passport_digest": self.source_passport_digest,
            "answer_event_id": self.answer_event_id,
            "answer_event_sequence": self.answer_event_sequence,
            "answer_event_digest": self.answer_event_digest,
            "base_question_ref": self.base_question_ref.to_mapping(),
            "base_estimand_ref": self.base_estimand_ref.to_mapping(),
            "base_study_ref": self.base_study_ref.to_mapping(),
            "base_evidence_digests": list(self.base_evidence_digests),
            "dataset_fingerprint": self.dataset_fingerprint,
            "proposed_question": (
                None
                if self.proposed_question is None
                else self.proposed_question.to_mapping()
            ),
            "proposed_estimand": (
                None
                if self.proposed_estimand is None
                else self.proposed_estimand.to_mapping()
            ),
            "proposed_study": (
                None
                if self.proposed_study is None
                else self.proposed_study.to_mapping()
            ),
            "next_question_budget_remaining": self.next_question_budget_remaining,
            "requires_acceptance": self.requires_acceptance,
            "acceptance_certificate_id": self.acceptance_certificate_id,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


class ClarificationTransitionService:
    """Validate local answers and produce immutable planning revisions only."""

    def __init__(self, registry: ClarificationRegistry | None = None) -> None:
        self._registry = registry or build_p1_clarification_registry()
        if not isinstance(self._registry, ClarificationRegistry):
            raise TransitionError("registry must be a ClarificationRegistry")

    @property
    def clarification_registry_digest(self) -> str:
        return self._registry.digest()

    def propose(
        self,
        request: ResearchRequest,
        passport: AnalysisPassport,
        answer: ClarificationAnswerEvent,
        *,
        acceptance_certificate_id: str | None = None,
    ) -> RevisionCandidate:
        question = self._validate_source(request, passport, answer)
        self._validate_answer(request, question, answer.answer_value)
        answer_fact = self._fact_from_answer(question, answer)
        will_change_estimand = question.fact_address.startswith("estimand.") or self._question_answer_changes_estimand(
            request,
            question,
            answer_fact,
        )
        if will_change_estimand:
            if acceptance_certificate_id is None:
                raise TransitionError(
                    "estimand revision requires acceptance_certificate_id"
                )
            event_ref = _require_reference(
                acceptance_certificate_id,
                "acceptance_certificate_id",
            )
            if event_ref == answer.event_id or any(
                reference.evidence_id == event_ref
                for reference in request.decision_evidence_refs
            ):
                raise TransitionError(
                    "acceptance certificate ID has already been used"
                )
        else:
            if acceptance_certificate_id is not None:
                raise TransitionError(
                    "ready revision cannot reserve acceptance_certificate_id"
                )
            event_ref = answer.event_id
        try:
            proposed_question, proposed_estimand, proposed_study = self._apply_answer(
                request,
                question,
                answer,
                event_ref,
            )
            available = set(request.available_variable_ids)
            if proposed_estimand is not None:
                proposed_estimand.validate_variable_references(available)
            if proposed_study is not None:
                proposed_study.validate_variable_references(available)
        except ContractError as exc:
            raise TransitionError(f"answer would create an invalid revision: {exc}") from exc
        requires_acceptance = proposed_estimand is not None
        if requires_acceptance != will_change_estimand:
            raise TransitionError("transition acceptance classification drifted")
        return RevisionCandidate(
            project_id=answer.project_id,
            source_passport_digest=answer.source_passport_digest,
            answer_event_id=answer.event_id,
            answer_event_sequence=answer.event_sequence,
            answer_event_digest=answer.digest(),
            base_question_ref=_component_ref(request.question),
            base_estimand_ref=_component_ref(request.estimand),
            base_study_ref=_component_ref(request.study),
            base_evidence_digests=tuple(
                reference.evidence_digest
                for reference in request.decision_evidence_refs
            ),
            dataset_fingerprint=request.current_dataset_fingerprint,
            proposed_question=proposed_question,
            proposed_estimand=proposed_estimand,
            proposed_study=proposed_study,
            next_question_budget_remaining=max(
                0,
                request.question_budget_remaining - 1,
            ),
            requires_acceptance=requires_acceptance,
            acceptance_certificate_id=(
                acceptance_certificate_id if requires_acceptance else None
            ),
        )

    def _validate_source(
        self,
        request: ResearchRequest,
        passport: AnalysisPassport,
        answer: ClarificationAnswerEvent,
    ) -> ClarificationSpec:
        if not isinstance(request, ResearchRequest):
            raise TransitionError("request must be a ResearchRequest")
        if not isinstance(passport, AnalysisPassport):
            raise TransitionError("passport must be an AnalysisPassport")
        if not isinstance(answer, ClarificationAnswerEvent):
            raise TransitionError("answer must be a ClarificationAnswerEvent")
        if passport.envelope.schema_version == 1:
            raise PassportMigrationRequired(
                "version 1 passport requires a fresh version 2 plan"
            )
        if (
            passport.action is not PrimaryAction.CLARIFY
            or not isinstance(passport.clarify, ClarifyPayloadV2)
        ):
            raise TransitionError(
                "source passport must have a version 2 clarify action"
            )
        if answer.source_passport_digest != passport.digest():
            raise TransitionError("source passport digest mismatch")
        component_project_ids = {
            request.question.envelope.project_id,
            request.estimand.envelope.project_id,
            request.study.envelope.project_id,
        }
        if len(component_project_ids) != 1:
            raise TransitionError("source component project IDs must match")
        if answer.project_id != passport.envelope.project_id:
            raise TransitionError("answer project ID does not match passport")
        if answer.project_id != request.question.envelope.project_id:
            raise TransitionError("answer project ID does not match request")
        if request.question_budget_remaining == 0:
            raise TransitionError("clarification question budget is exhausted")
        expected_refs = (
            (passport.question_ref, _component_ref(request.question)),
            (passport.estimand_ref, _component_ref(request.estimand)),
            (passport.study_ref, _component_ref(request.study)),
        )
        if any(passport_ref != request_ref for passport_ref, request_ref in expected_refs):
            raise TransitionError("source component revision no longer matches passport")
        if passport.dataset_fingerprint != request.current_dataset_fingerprint:
            raise TransitionError("source dataset fingerprint no longer matches passport")
        request_evidence_digests = tuple(
            reference.evidence_digest for reference in request.decision_evidence_refs
        )
        if passport.decision_evidence_digests != request_evidence_digests:
            raise TransitionError(
                "source decision evidence no longer matches passport"
            )
        try:
            validate_passport_request_binding(passport, request)
        except ResearchServiceError as exc:
            raise TransitionError(f"source request binding is stale: {exc}") from exc
        audit = audit_passport_registry(passport, self._registry)
        if audit.status is not PassportRegistryAuditStatus.VERIFIED:
            raise TransitionError(
                f"source clarification registry is stale: {audit.reason_code}"
            )
        reference = passport.clarify.clarification_ref
        answer_identity = (
            (answer.question_id, reference.question_id, "question ID"),
            (answer.question_version, reference.question_version, "question version"),
            (answer.question_digest, reference.question_digest, "question digest"),
            (answer.fact_address, reference.fact_address, "fact address"),
        )
        for actual, expected, field_name in answer_identity:
            if actual != expected:
                raise TransitionError(
                    f"answer {field_name} does not match clarify passport"
                )
        try:
            question = self._registry.get(reference.question_id)
        except ClarificationError as exc:  # pragma: no cover - audit closes this path.
            raise TransitionError("answer references an unknown question") from exc
        if question.lifecycle is not ClarificationLifecycle.ACTIVE:
            raise TransitionError("clarification question is not active")
        if any(
            reference.evidence_id == answer.event_id
            for reference in request.decision_evidence_refs
        ):
            raise TransitionError("answer event ID has already been used")
        if any(
            reference.evidence_digest == answer.digest()
            for reference in request.decision_evidence_refs
        ):
            raise TransitionError("answer event digest has already been used")
        if request.decision_evidence_refs and answer.event_sequence <= (
            request.decision_evidence_refs[-1].event_sequence
        ):
            raise TransitionError(
                "answer event sequence must be later than existing evidence"
            )
        return question

    @staticmethod
    def _validate_answer(
        request: ResearchRequest,
        question: ClarificationSpec,
        value: AnswerValue,
    ) -> None:
        if value.kind is AnswerValueKind.NOT_SURE:
            match_kind = BranchMatchKind.NOT_SURE
        elif question.answer_kind in _CHOICE_ANSWER_KINDS:
            if value.kind is not AnswerValueKind.CHOICE:
                raise TransitionError("clarification requires a choice answer")
            allowed = {choice.value for choice in question.choices}
            if value.choice_value not in allowed:
                raise TransitionError("answer contains an unregistered choice")
            match_kind = BranchMatchKind.CHOICE_VALUES
        elif question.answer_kind in {
            AnswerKind.VARIABLE_SINGLE,
            AnswerKind.VARIABLE_MULTI,
            AnswerKind.ORDERED_VARIABLES,
        }:
            if value.kind is not AnswerValueKind.VARIABLES:
                raise TransitionError("clarification requires a variables answer")
            unknown = sorted(
                set(value.variable_ids) - set(request.available_variable_ids)
            )
            if unknown:
                raise TransitionError(
                    f"answer contains unknown variable(s): {', '.join(unknown)}"
                )
            if question.answer_kind is AnswerKind.VARIABLE_SINGLE and len(
                value.variable_ids
            ) != 1:
                raise TransitionError("answer requires exactly one variable")
            if question.fact_address == "estimand.role.repeated_measure" and len(
                value.variable_ids
            ) == 1:
                raise TransitionError(
                    "repeated-measure role requires zero or at least two variables"
                )
            if question.answer_kind is AnswerKind.ORDERED_VARIABLES and len(
                value.variable_ids
            ) < 2:
                raise TransitionError("ordered answer requires at least two variables")
            match_kind = (
                BranchMatchKind.EMPTY_VARIABLES
                if not value.variable_ids
                and question.answer_kind is AnswerKind.VARIABLE_MULTI
                else (
                    BranchMatchKind.NONEMPTY_VARIABLES
                    if question.answer_kind is AnswerKind.VARIABLE_MULTI
                    else BranchMatchKind.ANSWERED
                )
            )
        elif question.answer_kind is AnswerKind.BOUNDED_TEXT:
            if value.kind is not AnswerValueKind.TEXT:
                raise TransitionError("clarification requires a text answer")
            match_kind = BranchMatchKind.ANSWERED
        else:  # pragma: no cover - closed enum and sets cover all current kinds.
            raise TransitionError("unsupported clarification answer kind")
        matching = [
            branch
            for branch in question.branches
            if branch.match_kind is match_kind
            and (
                match_kind is not BranchMatchKind.CHOICE_VALUES
                or value.choice_value in branch.choice_values
            )
        ]
        if len(matching) != 1:
            raise TransitionError("answer does not match exactly one decision branch")

    def _apply_answer(
        self,
        request: ResearchRequest,
        question: ClarificationSpec,
        answer: ClarificationAnswerEvent,
        event_ref: str,
    ) -> tuple[QuestionSpec | None, EstimandSpec | None, StudySpec | None]:
        fact = self._fact_from_answer(question, answer)
        proposed_question: QuestionSpec | None = None
        proposed_estimand: EstimandSpec | None = None
        proposed_study: StudySpec | None = None
        address = question.fact_address
        if address in _QUESTION_FACTS:
            field_name, _ = _QUESTION_FACTS[address]
            source_fact = getattr(request.question, field_name)
            proposed_question = replace(
                request.question,
                envelope=_next_envelope(request.question.envelope, event_ref),
                **{field_name: fact},
            )
            if self._fact_semantics_changed(source_fact, fact):
                if address == "question.research_goal":
                    proposed_estimand = self._invalidate_estimand(
                        request.estimand,
                        question.question_id,
                        event_ref,
                        all_method_facts=True,
                    )
                else:
                    proposed_estimand = self._invalidate_estimand(
                        request.estimand,
                        question.question_id,
                        event_ref,
                        all_method_facts=False,
                    )
        elif address in _ESTIMAND_FACTS:
            field_name, _ = _ESTIMAND_FACTS[address]
            changes: dict[str, Any] = {field_name: fact}
            if address == "estimand.template" and (
                self._fact_semantics_changed(request.estimand.template, fact)
            ):
                invalidated = self._invalidate_estimand(
                    request.estimand,
                    question.question_id,
                    event_ref,
                    all_method_facts=True,
                )
                changes.update(
                    {
                        "claim_basis": invalidated.claim_basis,
                        "target_roles": invalidated.target_roles,
                        "contrast": invalidated.contrast,
                        "effect_scale": invalidated.effect_scale,
                        "association_target": invalidated.association_target,
                    }
                )
            proposed_estimand = replace(
                request.estimand,
                envelope=_next_envelope(request.estimand.envelope, event_ref),
                **changes,
            )
        elif address in _TARGET_ROLE_FACTS:
            proposed_estimand = replace(
                request.estimand,
                envelope=_next_envelope(request.estimand.envelope, event_ref),
                target_roles=self._replace_target_role(
                    request.estimand.target_roles,
                    _TARGET_ROLE_FACTS[address],
                    fact,
                ),
            )
        elif address in _STUDY_FACTS:
            field_name, _ = _STUDY_FACTS[address]
            changes = {field_name: fact}
            if (
                address == "study.dependence_structure"
                and answer.answer_value.kind is not AnswerValueKind.NOT_SURE
            ):
                if fact.value is DependenceKind.INDEPENDENT:
                    changes["repeated_measure_order"] = Fact.not_applicable(
                        reason_code="independent_has_no_repeated_order"
                    )
                elif fact.value is DependenceKind.PAIRED and (
                    request.study.repeated_measure_order.state
                    is FactState.NOT_APPLICABLE
                ):
                    changes["repeated_measure_order"] = Fact.unknown(
                        reason_code="paired_requires_repeated_order"
                    )
            proposed_study = replace(
                request.study,
                envelope=_next_envelope(request.study.envelope, event_ref),
                **changes,
            )
        elif address in _STUDY_ROLE_FACTS:
            proposed_study = replace(
                request.study,
                envelope=_next_envelope(request.study.envelope, event_ref),
                design_roles=self._replace_study_role(
                    request.study.design_roles,
                    _STUDY_ROLE_FACTS[address],
                    fact,
                ),
            )
        elif address == "study.repeated_measure_order":
            proposed_study = replace(
                request.study,
                envelope=_next_envelope(request.study.envelope, event_ref),
                repeated_measure_order=fact,
            )
        else:
            raise TransitionError(f"unsupported P1 fact address: {address}")
        return proposed_question, proposed_estimand, proposed_study

    @staticmethod
    def _fact_semantics_changed(source: Fact[Any], proposed: Fact[Any]) -> bool:
        if proposed.state not in _CURRENT_FACT_STATES:
            return False
        return (
            source.state not in _CURRENT_FACT_STATES
            or source.value != proposed.value
        )

    def _question_answer_changes_estimand(
        self,
        request: ResearchRequest,
        question: ClarificationSpec,
        proposed: Fact[Any],
    ) -> bool:
        field = _QUESTION_FACTS.get(question.fact_address)
        if field is None:
            return False
        source = getattr(request.question, field[0])
        return self._fact_semantics_changed(source, proposed)

    @staticmethod
    def _fact_from_answer(
        question: ClarificationSpec,
        answer: ClarificationAnswerEvent,
    ) -> Fact[Any]:
        value = answer.answer_value
        if value.kind is AnswerValueKind.NOT_SURE:
            return _unknown_fact(question.question_id)
        if value.kind is AnswerValueKind.CHOICE:
            enum_type: type[Enum] | None = None
            if question.fact_address in _QUESTION_FACTS:
                enum_type = _QUESTION_FACTS[question.fact_address][1]
            elif question.fact_address in _ESTIMAND_FACTS:
                enum_type = _ESTIMAND_FACTS[question.fact_address][1]
            elif question.fact_address in _STUDY_FACTS:
                enum_type = _STUDY_FACTS[question.fact_address][1]
            if enum_type is None or value.choice_value is None:
                raise TransitionError("choice answer has no closed fact decoder")
            try:
                decoded = enum_type(value.choice_value)
            except ValueError as exc:
                raise TransitionError("choice cannot decode to target fact") from exc
            return _confirmed_fact(decoded, answer.event_id)
        if value.kind is AnswerValueKind.VARIABLES:
            if (
                question.fact_address == "estimand.role.repeated_measure"
                and not value.variable_ids
            ):
                return Fact.not_applicable(
                    reason_code="user_confirmed_no_repeated_measure_role"
                )
            return _confirmed_fact(value.variable_ids, answer.event_id)
        if value.text_value is None:
            raise TransitionError("text answer is missing text_value")
        return _confirmed_fact(value.text_value, answer.event_id)

    @staticmethod
    def _invalidate_estimand(
        estimand: EstimandSpec,
        question_id: str,
        event_ref: str,
        *,
        all_method_facts: bool,
    ) -> EstimandSpec:
        changes: dict[str, Any] = {
            "claim_basis": _invalidate_fact(estimand.claim_basis, question_id),
        }
        if all_method_facts:
            changes.update(
                {
                    "template": _invalidate_fact(estimand.template, question_id),
                    "target_roles": tuple(
                        replace(
                            binding,
                            variable_ids=_invalidate_fact(
                                binding.variable_ids,
                                question_id,
                            ),
                        )
                        for binding in estimand.target_roles
                    ),
                    "contrast": _invalidate_fact(estimand.contrast, question_id),
                    "effect_scale": _invalidate_fact(
                        estimand.effect_scale,
                        question_id,
                    ),
                    "association_target": _invalidate_fact(
                        estimand.association_target,
                        question_id,
                    ),
                }
            )
        return replace(
            estimand,
            envelope=_next_envelope(estimand.envelope, event_ref),
            **changes,
        )

    @staticmethod
    def _replace_target_role(
        bindings: tuple[TargetRoleBinding, ...],
        role: TargetRole,
        fact: Fact[Any],
    ) -> tuple[TargetRoleBinding, ...]:
        by_role = {binding.role: binding for binding in bindings}
        by_role[role] = TargetRoleBinding(role=role, variable_ids=fact)
        return tuple(by_role[key] for key in sorted(by_role, key=lambda item: item.value))

    @staticmethod
    def _replace_study_role(
        bindings: tuple[StudyRoleBinding, ...],
        role: StudyRole,
        fact: Fact[Any],
    ) -> tuple[StudyRoleBinding, ...]:
        by_role = {binding.role: binding for binding in bindings}
        by_role[role] = StudyRoleBinding(role=role, variable_ids=fact)
        return tuple(by_role[key] for key in sorted(by_role, key=lambda item: item.value))

    @staticmethod
    def build_acceptance_certificate(
        candidate: RevisionCandidate,
        *,
        event_sequence: int,
    ) -> RevisionAcceptanceCertificate:
        if not isinstance(candidate, RevisionCandidate):
            raise TransitionError("candidate must be a RevisionCandidate")
        if not candidate.requires_acceptance:
            raise TransitionError("ready candidate does not require acceptance")
        if type(event_sequence) is not int or event_sequence <= (
            candidate.answer_event_sequence
        ):
            raise TransitionError(
                "acceptance event sequence must be later than answer"
            )
        return RevisionAcceptanceCertificate(
            certificate_id=candidate.acceptance_certificate_id or "",
            project_id=candidate.project_id,
            event_sequence=event_sequence,
            candidate_digest=candidate.digest(),
            answer_event_digest=candidate.answer_event_digest,
            accepted_component_digests=candidate.changed_component_digests,
        )

    def commit_ready(
        self,
        request: ResearchRequest,
        candidate: RevisionCandidate,
    ) -> ResearchRequest:
        self._validate_commit_base(request, candidate)
        if candidate.requires_acceptance:
            raise TransitionError("candidate requires acceptance before commit")
        answer_ref = self._answer_evidence_ref(candidate)
        return self._committed_request(
            request,
            candidate,
            (answer_ref,),
        )

    def commit_accepted(
        self,
        request: ResearchRequest,
        candidate: RevisionCandidate,
        certificate: RevisionAcceptanceCertificate,
    ) -> ResearchRequest:
        self._validate_commit_base(request, candidate)
        if not candidate.requires_acceptance:
            raise TransitionError("ready candidate cannot use acceptance")
        if not isinstance(certificate, RevisionAcceptanceCertificate):
            raise TransitionError(
                "certificate must be a RevisionAcceptanceCertificate"
            )
        if certificate.certificate_id != candidate.acceptance_certificate_id:
            raise TransitionError("acceptance certificate ID mismatch")
        if certificate.project_id != candidate.project_id:
            raise TransitionError("acceptance certificate project mismatch")
        if certificate.event_sequence <= candidate.answer_event_sequence:
            raise TransitionError("acceptance must be later than answer")
        if certificate.candidate_digest != candidate.digest():
            raise TransitionError("acceptance candidate digest mismatch")
        if certificate.answer_event_digest != candidate.answer_event_digest:
            raise TransitionError("acceptance answer event digest mismatch")
        if certificate.accepted_component_digests != (
            candidate.changed_component_digests
        ):
            raise TransitionError("acceptance component digest mismatch")
        answer_ref = self._answer_evidence_ref(candidate)
        acceptance_ref = DecisionEvidenceRef(
            evidence_id=certificate.certificate_id,
            project_id=certificate.project_id,
            evidence_kind=DecisionEvidenceKind.REVISION_ACCEPTANCE,
            event_sequence=certificate.event_sequence,
            evidence_digest=certificate.digest(),
            subject_digests=certificate.accepted_component_digests,
        )
        return self._committed_request(
            request,
            candidate,
            (answer_ref, acceptance_ref),
        )

    @staticmethod
    def _answer_evidence_ref(candidate: RevisionCandidate) -> DecisionEvidenceRef:
        return DecisionEvidenceRef(
            evidence_id=candidate.answer_event_id,
            project_id=candidate.project_id,
            evidence_kind=DecisionEvidenceKind.CLARIFICATION_ANSWER,
            event_sequence=candidate.answer_event_sequence,
            evidence_digest=candidate.answer_event_digest,
            subject_digests=(candidate.digest(),),
        )

    @staticmethod
    def _validate_commit_base(
        request: ResearchRequest,
        candidate: RevisionCandidate,
    ) -> None:
        if not isinstance(request, ResearchRequest):
            raise TransitionError("request must be a ResearchRequest")
        if not isinstance(candidate, RevisionCandidate):
            raise TransitionError("candidate must be a RevisionCandidate")
        if candidate.project_id != request.question.envelope.project_id:
            raise TransitionError("candidate project no longer matches request")
        if (
            candidate.base_question_ref != _component_ref(request.question)
            or candidate.base_estimand_ref != _component_ref(request.estimand)
            or candidate.base_study_ref != _component_ref(request.study)
        ):
            raise TransitionError("candidate base component revision is stale")
        if candidate.dataset_fingerprint != request.current_dataset_fingerprint:
            raise TransitionError("candidate base dataset is stale")
        current_evidence = tuple(
            reference.evidence_digest for reference in request.decision_evidence_refs
        )
        if candidate.base_evidence_digests != current_evidence:
            raise TransitionError("candidate base decision evidence is stale")
        if candidate.next_question_budget_remaining != max(
            0,
            request.question_budget_remaining - 1,
        ):
            raise TransitionError("candidate question budget is stale")

    @staticmethod
    def _committed_request(
        request: ResearchRequest,
        candidate: RevisionCandidate,
        new_evidence: tuple[DecisionEvidenceRef, ...],
    ) -> ResearchRequest:
        return replace(
            request,
            question=candidate.proposed_question or request.question,
            estimand=candidate.proposed_estimand or request.estimand,
            study=candidate.proposed_study or request.study,
            question_budget_remaining=candidate.next_question_budget_remaining,
            decision_evidence_refs=request.decision_evidence_refs + new_evidence,
        )
