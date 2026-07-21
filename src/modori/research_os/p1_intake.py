"""Closed, structure-only intake for the six approved Research OS P1 tasks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
import re
import unicodedata

from modori.research_os.contracts import (
    AssociationTarget,
    CaptureMode,
    CausalIntent,
    ClaimBasis,
    ContrastKind,
    DataLayout,
    DependenceKind,
    EffectScale,
    EstimandSpec,
    EstimandTemplate,
    Fact,
    Language,
    QuestionSpec,
    ResearchGoal,
    SchemaEnvelope,
    StudySpec,
    TargetRole,
    TargetRoleBinding,
    TemporalStructure,
)
from modori.research_os.resolver import ProductSurface
from modori.research_os.service import ResearchRequest


class P1IntakeError(ValueError):
    """Raised when tentative intake cannot become one approved P1 request."""


class P1TaskProfile(str, Enum):
    """The exact six noncausal research tasks supported by the P1 intake."""

    NUMERIC_DISTRIBUTION = "numeric_distribution"
    CATEGORY_FREQUENCY = "category_frequency"
    INDEPENDENT_TWO_GROUP_MEAN = "independent_two_group_mean"
    PAIRED_TWO_TIME_MEAN_CHANGE = "paired_two_time_mean_change"
    LINEAR_CO_MOVEMENT = "linear_co_movement"
    RANK_CO_MOVEMENT = "rank_co_movement"


_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_variable_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise P1IntakeError(f"{field} must be a tuple")
    seen: set[str] = set()
    for variable_id in value:
        if not isinstance(variable_id, str) or not variable_id.strip():
            raise P1IntakeError(f"{field} must contain non-empty variable IDs")
        if variable_id != unicodedata.normalize("NFC", variable_id):
            raise P1IntakeError(f"{field} variable IDs must use NFC Unicode")
        if variable_id in seen:
            raise P1IntakeError(f"{field} cannot contain duplicate variable IDs")
        seen.add(variable_id)
    return value


@dataclass(frozen=True)
class P1RoleBindings:
    """Tentative role answers; no study-design role can enter initial intake."""

    outcome: tuple[str, ...] = ()
    group: tuple[str, ...] = ()
    focal_predictor: tuple[str, ...] = ()
    repeated_measure_order: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        fields = (
            ("outcome", self.outcome),
            ("group", self.group),
            ("focal_predictor", self.focal_predictor),
            ("repeated_measure_order", self.repeated_measure_order),
        )
        flattened: list[str] = []
        for name, values in fields:
            flattened.extend(_require_variable_tuple(values, field=name))
        if len(flattened) != len(set(flattened)):
            raise P1IntakeError(
                "one variable ID cannot be duplicated across P1 intake roles"
            )


@dataclass(frozen=True)
class P1IntakeDraft:
    """Authority-free form state for one explicitly selected P1 profile."""

    profile: P1TaskProfile
    roles: P1RoleBindings

    def __post_init__(self) -> None:
        if not isinstance(self.profile, P1TaskProfile):
            raise P1IntakeError("profile must be a P1TaskProfile")
        if not isinstance(self.roles, P1RoleBindings):
            raise P1IntakeError("roles must be P1RoleBindings")


@dataclass(frozen=True)
class _ProfileDefinition:
    goal: ResearchGoal
    template: EstimandTemplate
    claim_basis: ClaimBasis
    effect_scale: EffectScale
    association_target: AssociationTarget | None
    contrast: ContrastKind | None
    dependence: DependenceKind | None
    data_layout: DataLayout | None
    temporal_structure: TemporalStructure | None
    role_shape: str


_PROFILE_DEFINITIONS = MappingProxyType(
    {
        P1TaskProfile.NUMERIC_DISTRIBUTION: _ProfileDefinition(
            goal=ResearchGoal.DESCRIBE,
            template=EstimandTemplate.SUMMARY,
            claim_basis=ClaimBasis.DESCRIPTIVE,
            effect_scale=EffectScale.DISTRIBUTION,
            association_target=None,
            contrast=None,
            dependence=None,
            data_layout=None,
            temporal_structure=None,
            role_shape="outcome_many",
        ),
        P1TaskProfile.CATEGORY_FREQUENCY: _ProfileDefinition(
            goal=ResearchGoal.DESCRIBE,
            template=EstimandTemplate.FREQUENCY_DISTRIBUTION,
            claim_basis=ClaimBasis.DESCRIPTIVE,
            effect_scale=EffectScale.DISTRIBUTION,
            association_target=None,
            contrast=None,
            dependence=None,
            data_layout=None,
            temporal_structure=None,
            role_shape="outcome_many",
        ),
        P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN: _ProfileDefinition(
            goal=ResearchGoal.COMPARE,
            template=EstimandTemplate.GROUP_CONTRAST,
            claim_basis=ClaimBasis.ASSOCIATIONAL,
            effect_scale=EffectScale.DIFFERENCE,
            association_target=None,
            contrast=ContrastKind.PAIRWISE,
            dependence=DependenceKind.INDEPENDENT,
            data_layout=None,
            temporal_structure=None,
            role_shape="outcome_group",
        ),
        P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE: _ProfileDefinition(
            goal=ResearchGoal.COMPARE,
            template=EstimandTemplate.WITHIN_UNIT_CHANGE,
            claim_basis=ClaimBasis.ASSOCIATIONAL,
            effect_scale=EffectScale.DIFFERENCE,
            association_target=None,
            contrast=ContrastKind.PAIRWISE,
            dependence=DependenceKind.PAIRED,
            data_layout=DataLayout.WIDE_REPEATED,
            temporal_structure=TemporalStructure.REPEATED_PANEL,
            role_shape="ordered_pair",
        ),
        P1TaskProfile.LINEAR_CO_MOVEMENT: _ProfileDefinition(
            goal=ResearchGoal.ASSOCIATE,
            template=EstimandTemplate.ASSOCIATION,
            claim_basis=ClaimBasis.ASSOCIATIONAL,
            effect_scale=EffectScale.CORRELATION,
            association_target=AssociationTarget.PRODUCT_MOMENT,
            contrast=None,
            dependence=None,
            data_layout=None,
            temporal_structure=None,
            role_shape="oriented_pair",
        ),
        P1TaskProfile.RANK_CO_MOVEMENT: _ProfileDefinition(
            goal=ResearchGoal.ASSOCIATE,
            template=EstimandTemplate.ASSOCIATION,
            claim_basis=ClaimBasis.ASSOCIATIONAL,
            effect_scale=EffectScale.CORRELATION,
            association_target=AssociationTarget.RANK_MONOTONIC,
            contrast=None,
            dependence=None,
            data_layout=None,
            temporal_structure=None,
            role_shape="oriented_pair",
        ),
    }
)


def _require_reference(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or not _REFERENCE_RE.fullmatch(value)
        or value != unicodedata.normalize("NFC", value)
    ):
        raise P1IntakeError(f"{field} must be a closed NFC reference")
    return value


def _require_digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise P1IntakeError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_language(value: object) -> Language:
    if not isinstance(value, Language):
        raise P1IntakeError("language must be a Language")
    return value


def _validate_available_variable_ids(value: object) -> tuple[str, ...]:
    variables = _require_variable_tuple(value, field="available_variable_ids")
    if len(variables) != len(set(variables)):
        raise P1IntakeError("available_variable_ids cannot contain duplicates")
    return variables


def _confirmed(value: object, provenance_ref: str) -> Fact[object]:
    return Fact.user_confirmed(value, provenance_refs=(provenance_ref,))


def _unknown(field: str) -> Fact[object]:
    return Fact.unknown(reason_code=f"p1_intake_not_confirmed:{field}")


def _envelope(
    schema_id: str,
    object_id: str,
    *,
    task_project_id: str,
    initial_event_id: str,
) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id=task_project_id,
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=initial_event_id,
    )


def _validate_roles(
    draft: P1IntakeDraft,
    definition: _ProfileDefinition,
    available: tuple[str, ...],
) -> None:
    roles = draft.roles
    shape = definition.role_shape
    if shape == "outcome_many":
        valid = (
            len(roles.outcome) >= 1
            and not roles.group
            and not roles.focal_predictor
            and not roles.repeated_measure_order
        )
    elif shape == "outcome_group":
        valid = (
            len(roles.outcome) == 1
            and len(roles.group) == 1
            and not roles.focal_predictor
            and not roles.repeated_measure_order
        )
    elif shape == "ordered_pair":
        valid = (
            not roles.outcome
            and not roles.group
            and not roles.focal_predictor
            and len(roles.repeated_measure_order) == 2
        )
    else:
        valid = (
            len(roles.outcome) == 1
            and not roles.group
            and len(roles.focal_predictor) == 1
            and not roles.repeated_measure_order
        )
    if not valid:
        raise P1IntakeError(
            f"{draft.profile.value} roles do not match its exact P1 cardinality"
        )
    referenced = {
        variable_id
        for values in (
            roles.outcome,
            roles.group,
            roles.focal_predictor,
            roles.repeated_measure_order,
        )
        for variable_id in values
    }
    unavailable = sorted(referenced - set(available))
    if unavailable:
        raise P1IntakeError(
            "P1 roles contain IDs outside available_variable_ids: "
            + ", ".join(unavailable)
        )


def _target_roles(
    draft: P1IntakeDraft,
    definition: _ProfileDefinition,
    *,
    role_confirmation_refs: tuple[str, ...] | None = None,
) -> tuple[TargetRoleBinding, ...]:
    profile_ref = f"intake:profile:{draft.profile.value}"
    validated_refs: tuple[str, ...] | None = None
    if role_confirmation_refs is not None:
        if not isinstance(role_confirmation_refs, tuple) or not role_confirmation_refs:
            raise P1IntakeError("role_confirmation_refs must be a non-empty tuple")
        validated_refs = tuple(
            _require_reference(reference, field="role_confirmation_refs")
            for reference in role_confirmation_refs
        )
        if len(set(validated_refs)) != len(validated_refs):
            raise P1IntakeError("role_confirmation_refs cannot contain duplicates")
    roles = draft.roles
    if definition.role_shape == "outcome_many":
        bindings = ((TargetRole.OUTCOME, roles.outcome),)
    elif definition.role_shape == "outcome_group":
        bindings = (
            (TargetRole.OUTCOME, roles.outcome),
            (TargetRole.GROUP, roles.group),
        )
    elif definition.role_shape == "ordered_pair":
        before, after = roles.repeated_measure_order
        bindings = (
            (TargetRole.OUTCOME, (after,)),
            (TargetRole.REPEATED_MEASURE, (before, after)),
        )
    else:
        bindings = (
            (TargetRole.OUTCOME, roles.outcome),
            (TargetRole.FOCAL_PREDICTOR, roles.focal_predictor),
        )
    return tuple(
        TargetRoleBinding(
            role=role,
            variable_ids=Fact.user_confirmed(
                variable_ids,
                provenance_refs=(
                    validated_refs
                    if validated_refs is not None
                    else (f"{profile_ref}:role:{role.value}",)
                ),
            ),
        )
        for role, variable_ids in bindings
    )


def _common_study(
    *,
    task_project_id: str,
    initial_event_id: str,
    dataset_fingerprint: str,
    source_schema_fingerprint: str,
    dependence_structure: Fact[DependenceKind],
    data_layout: Fact[DataLayout],
    temporal_structure: Fact[TemporalStructure],
    repeated_measure_order: Fact[tuple[str, ...]],
) -> StudySpec:
    return StudySpec(
        envelope=_envelope(
            "modori.study_spec",
            "study:initial",
            task_project_id=task_project_id,
            initial_event_id=initial_event_id,
        ),
        dataset_fingerprint=dataset_fingerprint,
        source_schema_fingerprint=source_schema_fingerprint,
        unit_of_observation=_unknown("study.unit_of_observation"),
        unit_of_analysis=_unknown("study.unit_of_analysis"),
        design_family=_unknown("study.design_family"),
        data_layout=data_layout,
        temporal_structure=temporal_structure,
        dependence_structure=dependence_structure,
        assignment_mechanism=_unknown("study.assignment_mechanism"),
        sampling_design=_unknown("study.sampling_design"),
        design_roles=(),
        repeated_measure_order=repeated_measure_order,
        missing_code_meanings=(),
    )


def build_p1_request(
    draft: P1IntakeDraft,
    *,
    task_project_id: str,
    initial_event_id: str,
    dataset_fingerprint: str,
    source_schema_fingerprint: str,
    available_variable_ids: tuple[str, ...],
    language: Language,
    role_confirmation_refs: tuple[str, ...] | None = None,
) -> ResearchRequest:
    """Build only the exact noncausal request named by an approved profile card."""

    if not isinstance(draft, P1IntakeDraft):
        raise P1IntakeError("draft must be a P1IntakeDraft")
    task_project_id = _require_reference(
        task_project_id,
        field="task_project_id",
    )
    initial_event_id = _require_reference(
        initial_event_id,
        field="initial_event_id",
    )
    dataset_fingerprint = _require_digest(
        dataset_fingerprint,
        field="dataset_fingerprint",
    )
    source_schema_fingerprint = _require_digest(
        source_schema_fingerprint,
        field="source_schema_fingerprint",
    )
    available = _validate_available_variable_ids(available_variable_ids)
    language = _require_language(language)
    definition = _PROFILE_DEFINITIONS.get(draft.profile)
    if definition is None:
        raise P1IntakeError("profile is outside the frozen P1 method space")
    _validate_roles(draft, definition, available)
    profile_ref = f"intake:profile:{draft.profile.value}"

    question = QuestionSpec(
        envelope=_envelope(
            "modori.question_spec",
            "question:initial",
            task_project_id=task_project_id,
            initial_event_id=initial_event_id,
        ),
        capture_mode=CaptureMode.STRUCTURED,
        language=language,
        local_text=None,
        research_goal=_confirmed(
            definition.goal,
            f"{profile_ref}:research_goal",
        ),
        causal_intent=_confirmed(
            CausalIntent.NONCAUSAL,
            "intake:causal_intent:noncausal",
        ),
        role_hints=(),
    )
    estimand = EstimandSpec(
        envelope=_envelope(
            "modori.estimand_spec",
            "estimand:initial",
            task_project_id=task_project_id,
            initial_event_id=initial_event_id,
        ),
        template=_confirmed(definition.template, f"{profile_ref}:template"),
        claim_basis=_confirmed(
            definition.claim_basis,
            f"{profile_ref}:claim_basis",
        ),
        target_population=_unknown("estimand.target_population"),
        unit_of_analysis=_unknown("estimand.unit_of_analysis"),
        target_roles=_target_roles(
            draft,
            definition,
            role_confirmation_refs=role_confirmation_refs,
        ),
        contrast=(
            Fact.not_applicable(reason_code="p1_profile_has_no_contrast")
            if definition.contrast is None
            else _confirmed(definition.contrast, f"{profile_ref}:contrast")
        ),
        time_scope=_unknown("estimand.time_scope"),
        effect_scale=_confirmed(
            definition.effect_scale,
            f"{profile_ref}:effect_scale",
        ),
        association_target=(
            Fact.not_applicable(reason_code="p1_profile_is_not_association")
            if definition.association_target is None
            else _confirmed(
                definition.association_target,
                f"{profile_ref}:association_target",
            )
        ),
    )
    study = _common_study(
        task_project_id=task_project_id,
        initial_event_id=initial_event_id,
        dataset_fingerprint=dataset_fingerprint,
        source_schema_fingerprint=source_schema_fingerprint,
        dependence_structure=(
            _unknown("study.dependence_structure")
            if definition.dependence is None
            else _confirmed(
                definition.dependence,
                f"{profile_ref}:dependence_structure",
            )
        ),
        data_layout=(
            _unknown("study.data_layout")
            if definition.data_layout is None
            else _confirmed(definition.data_layout, f"{profile_ref}:data_layout")
        ),
        temporal_structure=(
            _unknown("study.temporal_structure")
            if definition.temporal_structure is None
            else _confirmed(
                definition.temporal_structure,
                f"{profile_ref}:temporal_structure",
            )
        ),
        repeated_measure_order=(
            _unknown("study.repeated_measure_order")
            if definition.role_shape != "ordered_pair"
            else Fact.user_confirmed(
                draft.roles.repeated_measure_order,
                provenance_refs=(f"{profile_ref}:repeated_measure_order",),
            )
        ),
    )
    return ResearchRequest(
        question=question,
        estimand=estimand,
        study=study,
        current_dataset_fingerprint=dataset_fingerprint,
        available_variable_ids=available,
        surface=ProductSurface.EXPERIMENTAL,
        question_budget_remaining=3,
        decision_evidence_refs=(),
    )


def build_causal_abstention_request(
    *,
    task_project_id: str,
    initial_event_id: str,
    dataset_fingerprint: str,
    source_schema_fingerprint: str,
    available_variable_ids: tuple[str, ...],
    language: Language,
) -> ResearchRequest:
    """Build the minimal request only after explicit causal-limit recording."""

    task_project_id = _require_reference(
        task_project_id,
        field="task_project_id",
    )
    initial_event_id = _require_reference(
        initial_event_id,
        field="initial_event_id",
    )
    dataset_fingerprint = _require_digest(
        dataset_fingerprint,
        field="dataset_fingerprint",
    )
    source_schema_fingerprint = _require_digest(
        source_schema_fingerprint,
        field="source_schema_fingerprint",
    )
    available = _validate_available_variable_ids(available_variable_ids)
    language = _require_language(language)
    question = QuestionSpec(
        envelope=_envelope(
            "modori.question_spec",
            "question:initial",
            task_project_id=task_project_id,
            initial_event_id=initial_event_id,
        ),
        capture_mode=CaptureMode.STRUCTURED,
        language=language,
        local_text=None,
        research_goal=_unknown("question.research_goal"),
        causal_intent=_confirmed(
            CausalIntent.CAUSAL,
            "intake:causal_intent:causal",
        ),
        role_hints=(),
    )
    estimand = EstimandSpec(
        envelope=_envelope(
            "modori.estimand_spec",
            "estimand:initial",
            task_project_id=task_project_id,
            initial_event_id=initial_event_id,
        ),
        template=_unknown("estimand.template"),
        claim_basis=_unknown("estimand.claim_basis"),
        target_population=_unknown("estimand.target_population"),
        unit_of_analysis=_unknown("estimand.unit_of_analysis"),
        target_roles=(),
        contrast=_unknown("estimand.contrast"),
        time_scope=_unknown("estimand.time_scope"),
        effect_scale=_unknown("estimand.effect_scale"),
        association_target=_unknown("estimand.association_target"),
    )
    study = _common_study(
        task_project_id=task_project_id,
        initial_event_id=initial_event_id,
        dataset_fingerprint=dataset_fingerprint,
        source_schema_fingerprint=source_schema_fingerprint,
        dependence_structure=_unknown("study.dependence_structure"),
        data_layout=_unknown("study.data_layout"),
        temporal_structure=_unknown("study.temporal_structure"),
        repeated_measure_order=_unknown("study.repeated_measure_order"),
    )
    return ResearchRequest(
        question=question,
        estimand=estimand,
        study=study,
        current_dataset_fingerprint=dataset_fingerprint,
        available_variable_ids=available,
        surface=ProductSurface.EXPERIMENTAL,
        question_budget_remaining=3,
        decision_evidence_refs=(),
    )
