"""Closed, authority-preserving presentation for the live Research OS flow."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import json
import re
from types import MappingProxyType
import unicodedata

from modori.research_flow import (
    DurableDecision,
    DurableFlowRecord,
    DurablePendingDecision,
    DurableRetraction,
    PassportStepMapping,
    PreflightDisposition,
    PreflightResult,
    ResearchFlowState,
    StaticBoundary,
    map_passport_to_step,
)
from modori.research_memory import (
    CommittedPassportRecord,
    PassportHistory,
    QuestionRationaleStatus,
    project_current_question_rationale,
)
from modori.research_os import (
    ClarificationError,
    ClarifyPayloadV2,
    Language,
    PrimaryAction,
    build_p1_clarification_registry,
)
from modori.ui.contracts import ControllerMode
from modori.ui.question_rationale_presenter import (
    QuestionRationalePresentationError,
    QuestionRationalePresenter,
    QuestionRationaleView,
)
from modori.ui.strings import RESEARCH_FLOW_STRINGS


class ResearchFlowPresentationError(ValueError):
    """Raised when a verified flow cannot enter the closed UI contract."""


class ResearchUiCommand(str, Enum):
    START = "start"
    CAUSAL_NO = "causal_no"
    CAUSAL_YES = "causal_yes"
    CAUSAL_NOT_SURE = "causal_not_sure"
    CAUSAL_RECORD = "causal_record"
    BACK = "back"
    SELECT_PROFILE = "select_profile"
    SUBMIT_ROLES = "submit_roles"
    CONFIRM_MEANINGS = "confirm_meanings"
    ANSWER = "answer"
    ANSWER_NOT_SURE = "answer_not_sure"
    RETRACT = "retract"
    RESUME = "resume"
    REPLAN = "replan"
    CANCEL = "cancel"
    PREPARE = "prepare"


_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_ABBREVIATED_DIGEST_RE = re.compile(r"[0-9a-f]{12}\Z")


def _require_text(value: object, field_name: str, *, blank: bool = False) -> str:
    if not isinstance(value, str):
        raise ResearchFlowPresentationError(f"{field_name} must be a string")
    if not blank and not value.strip():
        raise ResearchFlowPresentationError(f"{field_name} must not be blank")
    if value != unicodedata.normalize("NFC", value):
        raise ResearchFlowPresentationError(f"{field_name} must use NFC Unicode")
    return value


def _require_row_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise ResearchFlowPresentationError(f"{field_name} must be a tuple")
    for row in value:
        if (
            not isinstance(row, tuple)
            or len(row) != 2
            or any(not isinstance(item, str) or not item for item in row)
        ):
            raise ResearchFlowPresentationError(
                f"{field_name} must contain non-empty string pairs"
            )


@dataclass(frozen=True)
class ResearchUiAction:
    command: ResearchUiCommand
    label: str
    enabled: bool

    def __post_init__(self) -> None:
        if not isinstance(self.command, ResearchUiCommand):
            raise ResearchFlowPresentationError("command must be a ResearchUiCommand")
        _require_text(self.label, "action label")
        if type(self.enabled) is not bool:
            raise ResearchFlowPresentationError("action enabled must be a boolean")


@dataclass(frozen=True)
class ResearchOptionView:
    option_id: str
    label: str
    selected: bool
    enabled: bool

    def __post_init__(self) -> None:
        _require_text(self.option_id, "option_id")
        _require_text(self.label, "option label")
        if type(self.selected) is not bool or type(self.enabled) is not bool:
            raise ResearchFlowPresentationError(
                "option selected and enabled must be booleans"
            )


@dataclass(frozen=True)
class ResearchCandidateView:
    capability_label: str
    method_label: str
    claim_boundary: str
    role_rows: tuple[tuple[str, str], ...]
    review_status: str
    persistent_boundary: str

    def __post_init__(self) -> None:
        for field_name in (
            "capability_label",
            "method_label",
            "claim_boundary",
            "review_status",
            "persistent_boundary",
        ):
            _require_text(getattr(self, field_name), field_name)
        _require_row_tuple(self.role_rows, "role_rows")


@dataclass(frozen=True)
class ResearchFlowView:
    state: ResearchFlowState
    mode: ControllerMode
    language: Language
    title: str
    body: str
    stage_text: str
    badge_text: str
    decision_identity_digest: str
    visible_passport_digest: str
    primary_action: ResearchUiAction | None
    secondary_actions: tuple[ResearchUiAction, ...]
    options: tuple[ResearchOptionView, ...]
    question: QuestionRationaleView | None
    candidate: ResearchCandidateView | None
    evidence_rows: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.state, ResearchFlowState):
            raise ResearchFlowPresentationError("state must be a ResearchFlowState")
        if self.state is ResearchFlowState.ROUTE_READY:
            raise ResearchFlowPresentationError(
                "route_ready is unreachable in the P1 flow"
            )
        if not isinstance(self.mode, ControllerMode):
            raise ResearchFlowPresentationError("mode must be a ControllerMode")
        if self.language not in {Language.KO, Language.EN}:
            raise ResearchFlowPresentationError("language must be Korean or English")
        _require_text(self.title, "title")
        _require_text(self.body, "body")
        _require_text(self.stage_text, "stage_text", blank=True)
        _require_text(self.badge_text, "badge_text", blank=True)
        if (
            self.decision_identity_digest
            and _DIGEST_RE.fullmatch(self.decision_identity_digest) is None
        ):
            raise ResearchFlowPresentationError(
                "decision identity must be a lowercase SHA-256 digest"
            )
        if self.visible_passport_digest:
            if _ABBREVIATED_DIGEST_RE.fullmatch(self.visible_passport_digest) is None:
                raise ResearchFlowPresentationError(
                    "visible passport digest must use the approved abbreviation"
                )
            if not self.decision_identity_digest.startswith(
                self.visible_passport_digest
            ):
                raise ResearchFlowPresentationError(
                    "visible passport digest does not bind the decision"
                )
        if self.primary_action is not None and not isinstance(
            self.primary_action, ResearchUiAction
        ):
            raise ResearchFlowPresentationError(
                "primary_action must be a ResearchUiAction"
            )
        if not isinstance(self.secondary_actions, tuple) or any(
            not isinstance(action, ResearchUiAction)
            for action in self.secondary_actions
        ):
            raise ResearchFlowPresentationError(
                "secondary_actions must contain ResearchUiAction values"
            )
        commands = tuple(
            action.command
            for action in (
                *((self.primary_action,) if self.primary_action else ()),
                *self.secondary_actions,
            )
        )
        if len(commands) != len(set(commands)):
            raise ResearchFlowPresentationError("view actions cannot repeat")
        if not isinstance(self.options, tuple) or any(
            not isinstance(option, ResearchOptionView) for option in self.options
        ):
            raise ResearchFlowPresentationError(
                "options must contain ResearchOptionView values"
            )
        if self.question is not None and not isinstance(
            self.question, QuestionRationaleView
        ):
            raise ResearchFlowPresentationError(
                "question must be a QuestionRationaleView"
            )
        if self.candidate is not None and not isinstance(
            self.candidate, ResearchCandidateView
        ):
            raise ResearchFlowPresentationError(
                "candidate must be a ResearchCandidateView"
            )
        if (
            self.question is not None
            and self.state is not ResearchFlowState.CLARIFY_READY
        ):
            raise ResearchFlowPresentationError(
                "question authority requires clarify_ready"
            )
        if self.state is ResearchFlowState.CLARIFY_READY and self.question is None:
            raise ResearchFlowPresentationError(
                "clarify_ready requires a verified question"
            )
        candidate_states = {
            ResearchFlowState.CANDIDATE_READY,
            ResearchFlowState.PREPARATION_BLOCKED,
        }
        if self.candidate is not None and self.state not in candidate_states:
            raise ResearchFlowPresentationError(
                "candidate authority requires a candidate state"
            )
        if self.state in candidate_states and self.candidate is None:
            raise ResearchFlowPresentationError(
                "candidate state requires an exact candidate"
            )
        if self.question is not None and self.candidate is not None:
            raise ResearchFlowPresentationError(
                "question and candidate cannot share one view"
            )
        _require_row_tuple(self.evidence_rows, "evidence_rows")


@dataclass(frozen=True)
class _CandidateSpec:
    step_type: str
    capability_copy_key: str
    method_copy_key: str
    claim_copy_key: str
    role_shape: str


_SUMMARY_KEY = (
    "descriptive_summary:unweighted_summary:summary:independent_unweighted:roles-v1"
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

_CANDIDATE_SPECS = MappingProxyType(
    {
        _SUMMARY_KEY: _CandidateSpec(
            "stats.descriptives_table1",
            "capability.numeric_distribution",
            "method.descriptive_table",
            "claim.summary",
            "variables",
        ),
        _FREQUENCY_KEY: _CandidateSpec(
            "stats.frequency_crosstab",
            "capability.category_frequency",
            "method.frequency_table",
            "claim.frequency",
            "variables",
        ),
        _PEARSON_KEY: _CandidateSpec(
            "stats.correlation",
            "capability.linear_co_movement",
            "method.pearson",
            "claim.association",
            "pair",
        ),
        _SPEARMAN_KEY: _CandidateSpec(
            "stats.correlation",
            "capability.rank_co_movement",
            "method.spearman",
            "claim.association",
            "pair",
        ),
        _WELCH_KEY: _CandidateSpec(
            "stats.compare_groups",
            "capability.independent_two_group_mean",
            "method.welch",
            "claim.group_mean",
            "group",
        ),
        _PAIRED_KEY: _CandidateSpec(
            "stats.paired_comparison",
            "capability.paired_two_time_mean_change",
            "method.paired_t",
            "claim.paired_mean",
            "paired",
        ),
    }
)

_ACTION_COPY_KEYS = MappingProxyType(
    {
        ResearchUiCommand.START: "action.start",
        ResearchUiCommand.CAUSAL_NO: "action.causal_no",
        ResearchUiCommand.CAUSAL_YES: "action.causal_yes",
        ResearchUiCommand.CAUSAL_NOT_SURE: "action.causal_not_sure",
        ResearchUiCommand.CAUSAL_RECORD: "action.causal_record",
        ResearchUiCommand.BACK: "action.back",
        ResearchUiCommand.SELECT_PROFILE: "action.select_profile",
        ResearchUiCommand.SUBMIT_ROLES: "action.submit_roles",
        ResearchUiCommand.CONFIRM_MEANINGS: "action.confirm_meanings",
        ResearchUiCommand.ANSWER: "action.answer",
        ResearchUiCommand.ANSWER_NOT_SURE: "action.answer_not_sure",
        ResearchUiCommand.RETRACT: "action.retract",
        ResearchUiCommand.RESUME: "action.resume",
        ResearchUiCommand.REPLAN: "action.replan",
        ResearchUiCommand.CANCEL: "action.cancel",
        ResearchUiCommand.PREPARE: "action.prepare",
    }
)


def _validate_context(
    mode: object, language: object
) -> tuple[ControllerMode, Language]:
    if not isinstance(mode, ControllerMode):
        raise ResearchFlowPresentationError("mode must be a ControllerMode")
    if language not in {Language.KO, Language.EN}:
        raise ResearchFlowPresentationError("language must be Korean or English")
    return mode, language


def _copy(language: Language, key: str) -> str:
    try:
        value = RESEARCH_FLOW_STRINGS[language.value][key]
    except (KeyError, TypeError) as exc:
        raise ResearchFlowPresentationError(
            f"closed presentation catalog is missing {key}"
        ) from exc
    return _require_text(value, f"catalog value {key}")


def _action(
    command: ResearchUiCommand,
    language: Language,
    *,
    enabled: bool = True,
) -> ResearchUiAction:
    return ResearchUiAction(
        command=command,
        label=_copy(language, _ACTION_COPY_KEYS[command]),
        enabled=enabled,
    )


def _passport_abbreviation(
    mode: ControllerMode,
    digest: str,
) -> str:
    return digest[:12] if mode is ControllerMode.STANDARD else ""


def _state_copy(
    language: Language,
    state: ResearchFlowState,
) -> tuple[str, str]:
    return (
        _copy(language, f"state.{state.value}.title"),
        _copy(language, f"state.{state.value}.body"),
    )


def _base_view(
    *,
    state: ResearchFlowState,
    mode: ControllerMode,
    language: Language,
    title: str,
    body: str,
    stage_text: str = "",
    badge_text: str = "",
    decision_identity_digest: str = "",
    visible_passport_digest: str = "",
    primary_action: ResearchUiAction | None = None,
    secondary_actions: tuple[ResearchUiAction, ...] = (),
    options: tuple[ResearchOptionView, ...] = (),
    question: QuestionRationaleView | None = None,
    candidate: ResearchCandidateView | None = None,
    evidence_rows: tuple[tuple[str, str], ...] = (),
) -> ResearchFlowView:
    return ResearchFlowView(
        state=state,
        mode=mode,
        language=language,
        title=title,
        body=body,
        stage_text=stage_text,
        badge_text=badge_text,
        decision_identity_digest=decision_identity_digest,
        visible_passport_digest=visible_passport_digest,
        primary_action=primary_action,
        secondary_actions=secondary_actions,
        options=options,
        question=question,
        candidate=candidate,
        evidence_rows=evidence_rows,
    )


def _verified_question(
    record: DurableDecision,
    *,
    mode: ControllerMode,
    language: Language,
) -> tuple[QuestionRationaleView, tuple[ResearchOptionView, ...]]:
    payload = record.passport.clarify
    if not isinstance(payload, ClarifyPayloadV2):
        raise ResearchFlowPresentationError(
            "clarify decision is missing its sealed version 2 plan"
        )
    request_digest = record.passport.request_binding_digest
    registry_digest = record.passport.clarification_registry_digest
    if request_digest is None or registry_digest is None:
        raise ResearchFlowPresentationError(
            "clarify decision is missing its bound registry identity"
        )
    registry = build_p1_clarification_registry()
    history = PassportHistory(
        records=(
            CommittedPassportRecord(
                commit_event_id=record.committed_event_id,
                commit_sequence=record.committed_sequence,
                passport_artifact_id=record.passport_artifact_id,
                passport=record.passport,
            ),
        )
    )
    result = project_current_question_rationale(
        history,
        project_id=record.task_project_id,
        request_binding_digest=request_digest,
        clarification_registry_digest=registry_digest,
        registry=registry,
    )
    if result.status is not QuestionRationaleStatus.AVAILABLE:
        raise ResearchFlowPresentationError(
            "committed clarification rationale is unavailable or failed"
        )
    try:
        question = QuestionRationalePresenter().present(
            result,
            language=language.value,
            mode=mode.value,
        )
        spec = registry.get(payload.clarification_ref.question_id)
    except (QuestionRationalePresentationError, ClarificationError) as exc:
        raise ResearchFlowPresentationError(
            "committed clarification cannot enter the closed view"
        ) from exc
    if question is None:
        raise ResearchFlowPresentationError(
            "available clarification rationale produced no question"
        )
    options = tuple(
        ResearchOptionView(
            option_id=choice.value,
            label=choice.label_ko if language is Language.KO else choice.label_en,
            selected=False,
            enabled=True,
        )
        for choice in spec.choices
    )
    if spec.not_sure_enabled:
        options += (
            ResearchOptionView(
                option_id="not_sure",
                label=_copy(language, "option.not_sure"),
                selected=False,
                enabled=True,
            ),
        )
    return question, options


def _decode_params(mapping: PassportStepMapping) -> dict[str, object]:
    try:
        decoded = json.loads(mapping.canonical_step_params.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchFlowPresentationError(
            "canonical step settings cannot be decoded"
        ) from exc
    if not isinstance(decoded, dict):
        raise ResearchFlowPresentationError("canonical step settings must be an object")
    return decoded


def _one_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ResearchFlowPresentationError(
            f"canonical {field_name} must be one variable identity"
        )
    return value


def _role_id_rows(
    mapping: PassportStepMapping,
    spec: _CandidateSpec,
) -> tuple[tuple[str, str], ...]:
    params = _decode_params(mapping)
    if spec.role_shape == "variables":
        variables = params.get("variables")
        if not isinstance(variables, list) or not variables:
            raise ResearchFlowPresentationError(
                "canonical variables must be a non-empty list"
            )
        return tuple(
            ("role.variable", _one_string(value, "variables")) for value in variables
        )
    if spec.role_shape == "pair":
        pairs = params.get("pairs")
        if (
            not isinstance(pairs, list)
            or len(pairs) != 1
            or not isinstance(pairs[0], list)
            or len(pairs[0]) != 2
        ):
            raise ResearchFlowPresentationError(
                "canonical correlation pair is malformed"
            )
        return (
            ("role.outcome", _one_string(pairs[0][0], "outcome")),
            (
                "role.focal_predictor",
                _one_string(pairs[0][1], "focal predictor"),
            ),
        )
    if spec.role_shape == "group":
        return (
            ("role.outcome", _one_string(params.get("dv"), "outcome")),
            ("role.group", _one_string(params.get("group"), "group")),
        )
    if spec.role_shape == "paired":
        return (
            ("role.before", _one_string(params.get("before"), "before")),
            ("role.after", _one_string(params.get("after"), "after")),
        )
    raise ResearchFlowPresentationError("candidate role shape is not closed")


def _display_role_rows(
    id_rows: tuple[tuple[str, str], ...],
    *,
    language: Language,
    variable_labels: Mapping[str, str] | None,
) -> tuple[tuple[str, str], ...]:
    if variable_labels is None or not isinstance(variable_labels, Mapping):
        raise ResearchFlowPresentationError(
            "a local variable label mapping is required for the PRO view"
        )
    rows: list[tuple[str, str]] = []
    for role_key, variable_id in id_rows:
        label = variable_labels.get(variable_id)
        if (
            not isinstance(label, str)
            or not label.strip()
            or label == variable_id
            or label != unicodedata.normalize("NFC", label)
        ):
            raise ResearchFlowPresentationError(
                "a safe local variable label is missing"
            )
        rows.append((_copy(language, role_key), label))
    return tuple(rows)


def _validate_preparation_binding(
    mapping: PassportStepMapping,
    preflight: PreflightResult,
) -> None:
    preflight.__post_init__()
    mapping.__post_init__()
    preparation = preflight.preparation
    if preparation is None:
        return
    preparation.__post_init__()
    for field_name in (
        "passport_artifact_id",
        "passport_digest",
        "capability_key",
        "dataset_fingerprint",
        "step_type",
        "canonical_step_params",
        "experimental",
        "requires_explicit_configure_confirm_run",
    ):
        if getattr(preparation, field_name) != getattr(mapping, field_name):
            raise ResearchFlowPresentationError(
                "preflight preparation does not bind the exact passport mapping"
            )
    if preparation.preflight_disposition is not preflight.disposition:
        raise ResearchFlowPresentationError(
            "preflight preparation has a different disposition"
        )


def _candidate_projection(
    record: DurableDecision,
    preflight: PreflightResult,
    *,
    mode: ControllerMode,
    language: Language,
    variable_labels: Mapping[str, str] | None,
) -> tuple[ResearchCandidateView, tuple[tuple[str, str], ...]]:
    mapping = map_passport_to_step(
        record.passport,
        record.request,
        current_dataset_fingerprint=record.request.current_dataset_fingerprint,
    )
    if (
        mapping.passport_artifact_id != record.passport_artifact_id
        or mapping.passport_digest != record.passport_digest
    ):
        raise ResearchFlowPresentationError(
            "derived step mapping does not bind the durable decision"
        )
    _validate_preparation_binding(mapping, preflight)
    spec = _CANDIDATE_SPECS.get(mapping.capability_key)
    if spec is None or mapping.step_type != spec.step_type:
        raise ResearchFlowPresentationError(
            "candidate is outside the closed six-row handoff"
        )
    id_rows = _role_id_rows(mapping, spec)
    role_rows = (
        _display_role_rows(
            id_rows,
            language=language,
            variable_labels=variable_labels,
        )
        if mode is ControllerMode.STANDARD
        else ()
    )
    blocked = preflight.disposition is PreflightDisposition.PREPARE_BLOCKED
    candidate = ResearchCandidateView(
        capability_label=_copy(language, spec.capability_copy_key),
        method_label=_copy(language, spec.method_copy_key),
        claim_boundary=_copy(language, spec.claim_copy_key),
        role_rows=role_rows,
        review_status=_copy(
            language,
            "candidate.blocked_review_status" if blocked else "candidate.review_status",
        ),
        persistent_boundary=_copy(language, "candidate.no_auto_run"),
    )
    if mode is ControllerMode.GUIDED:
        return candidate, ()
    evidence: list[tuple[str, str]] = [
        (_copy(language, "evidence.passport"), record.passport_digest[:12]),
        (_copy(language, "evidence.capability"), candidate.capability_label),
        (_copy(language, "evidence.method"), candidate.method_label),
        (_copy(language, "evidence.claim_boundary"), candidate.claim_boundary),
        (
            _copy(language, "evidence.preflight"),
            _copy(
                language,
                "evidence.preflight_blocked" if blocked else "evidence.preflight_ready",
            ),
        ),
    ]
    if blocked:
        evidence.extend(
            (
                _copy(language, "evidence.blocked_condition"),
                _copy(language, f"issue.{issue.code}"),
            )
            for issue in preflight.issues
        )
    return candidate, tuple(evidence)


def present_durable_record(
    record: DurableFlowRecord,
    *,
    mode: ControllerMode,
    language: Language,
    preflight: PreflightResult | None,
    variable_labels: Mapping[str, str] | None = None,
) -> ResearchFlowView:
    """Project one revalidated durable record without changing its authority."""

    mode, language = _validate_context(mode, language)
    if not isinstance(
        record,
        (DurableDecision, DurablePendingDecision, DurableRetraction),
    ):
        raise ResearchFlowPresentationError(
            "record must be a durable Research OS result"
        )
    record.__post_init__()
    if not isinstance(record, DurableDecision):
        if preflight is not None:
            raise ResearchFlowPresentationError(
                "preflight belongs only to a local recommendation decision"
            )
        if isinstance(record, DurablePendingDecision):
            state = ResearchFlowState.RECOVERY_PENDING
            digest = ""
            badge_key = "badge.pending"
            primary = _action(ResearchUiCommand.RESUME, language)
        else:
            state = ResearchFlowState.RETRACTED
            digest = record.retracted_passport_digest
            badge_key = "badge.retracted"
            primary = _action(ResearchUiCommand.REPLAN, language)
        title, body = _state_copy(language, state)
        return _base_view(
            state=state,
            mode=mode,
            language=language,
            title=title,
            body=body,
            badge_text=_copy(language, badge_key),
            decision_identity_digest=digest,
            visible_passport_digest=(
                _passport_abbreviation(mode, digest) if digest else ""
            ),
            primary_action=primary,
        )

    digest = record.passport_digest
    visible_digest = _passport_abbreviation(mode, digest)
    if record.action is not PrimaryAction.RECOMMEND_LOCAL and preflight is not None:
        raise ResearchFlowPresentationError(
            "preflight belongs only to a local recommendation decision"
        )
    if record.action is PrimaryAction.CLARIFY:
        question, options = _verified_question(
            record,
            mode=mode,
            language=language,
        )
        state = ResearchFlowState.CLARIFY_READY
        title, body = _state_copy(language, state)
        return _base_view(
            state=state,
            mode=mode,
            language=language,
            title=title,
            body=body,
            badge_text=_copy(language, "badge.clarify"),
            decision_identity_digest=digest,
            visible_passport_digest=visible_digest,
            primary_action=_action(ResearchUiCommand.ANSWER, language),
            secondary_actions=(
                _action(ResearchUiCommand.ANSWER_NOT_SURE, language),
                _action(ResearchUiCommand.RETRACT, language),
            ),
            options=options,
            question=question,
        )
    if record.action is PrimaryAction.ABSTAIN:
        state = ResearchFlowState.ABSTAIN_READY
        title, body = _state_copy(language, state)
        return _base_view(
            state=state,
            mode=mode,
            language=language,
            title=title,
            body=body,
            badge_text=_copy(language, "badge.abstain"),
            decision_identity_digest=digest,
            visible_passport_digest=visible_digest,
            primary_action=_action(ResearchUiCommand.REPLAN, language),
        )
    if record.action is PrimaryAction.ROUTE_EXTERNAL:
        raise ResearchFlowPresentationError(
            "route action is unreachable in the P1 flow"
        )
    if record.action is not PrimaryAction.RECOMMEND_LOCAL:
        raise ResearchFlowPresentationError("decision action is not closed")
    if preflight is None:
        raise ResearchFlowPresentationError(
            "local recommendation requires one exact preflight"
        )
    if not isinstance(preflight, PreflightResult):
        raise ResearchFlowPresentationError("preflight must be a PreflightResult")
    if preflight.disposition is PreflightDisposition.STALE:
        preflight.__post_init__()
        state = ResearchFlowState.REPLAN_REQUIRED
        title, body = _state_copy(language, state)
        return _base_view(
            state=state,
            mode=mode,
            language=language,
            title=title,
            body=body,
            badge_text=_copy(language, "badge.stale"),
            decision_identity_digest=digest,
            visible_passport_digest=visible_digest,
            primary_action=_action(ResearchUiCommand.REPLAN, language),
        )
    if preflight.disposition is PreflightDisposition.FAILURE:
        preflight.__post_init__()
        state = ResearchFlowState.FAILURE
        title, body = _state_copy(language, state)
        return _base_view(
            state=state,
            mode=mode,
            language=language,
            title=title,
            body=body,
            badge_text=_copy(language, "badge.error"),
            decision_identity_digest=digest,
            visible_passport_digest=visible_digest,
            primary_action=_action(ResearchUiCommand.RESUME, language),
        )
    candidate, evidence = _candidate_projection(
        record,
        preflight,
        mode=mode,
        language=language,
        variable_labels=variable_labels,
    )
    if preflight.disposition is PreflightDisposition.PREPARE_READY:
        state = ResearchFlowState.CANDIDATE_READY
        primary = _action(ResearchUiCommand.PREPARE, language)
    elif preflight.disposition is PreflightDisposition.PREPARE_BLOCKED:
        state = ResearchFlowState.PREPARATION_BLOCKED
        primary = None
    else:  # pragma: no cover - the enum branches above are exhaustive.
        raise ResearchFlowPresentationError("preflight disposition is not closed")
    title, body = _state_copy(language, state)
    return _base_view(
        state=state,
        mode=mode,
        language=language,
        title=title,
        body=body,
        badge_text=_copy(language, "candidate.experimental_badge"),
        decision_identity_digest=digest,
        visible_passport_digest=visible_digest,
        primary_action=primary,
        candidate=candidate,
        evidence_rows=evidence,
    )


def present_static_boundary(
    boundary: StaticBoundary,
    *,
    mode: ControllerMode,
    language: Language,
) -> ResearchFlowView:
    """Present a write-free boundary with no passport authority."""

    mode, language = _validate_context(mode, language)
    if not isinstance(boundary, StaticBoundary):
        raise ResearchFlowPresentationError("boundary must be a StaticBoundary")
    if boundary is StaticBoundary.CAUSAL_SCOPE_NOTICE:
        state = ResearchFlowState.CAUSAL_SCOPE_NOTICE
        copy_prefix = "state.static_causal"
        primary = _action(ResearchUiCommand.CAUSAL_RECORD, language)
        secondary = (_action(ResearchUiCommand.BACK, language),)
    elif boundary is StaticBoundary.CAUSAL_INTENT_UNKNOWN:
        state = ResearchFlowState.INTAKE_BLOCKED
        copy_prefix = "state.static_causal_unknown"
        primary = _action(ResearchUiCommand.BACK, language)
        secondary = ()
    elif boundary is StaticBoundary.SCOPE_BOUNDARY:
        state = ResearchFlowState.SCOPE_BOUNDARY
        copy_prefix = "state.static_scope"
        primary = _action(ResearchUiCommand.BACK, language)
        secondary = ()
    else:  # pragma: no cover - enum branches are exhaustive.
        raise ResearchFlowPresentationError("static boundary is not closed")
    return _base_view(
        state=state,
        mode=mode,
        language=language,
        title=_copy(language, f"{copy_prefix}.title"),
        body=_copy(language, f"{copy_prefix}.body"),
        badge_text=_copy(language, "badge.scope"),
        primary_action=primary,
        secondary_actions=secondary,
    )


_TRANSIENT_COPY = MappingProxyType(
    {
        ResearchFlowState.IDLE: ("badge.local", ResearchUiCommand.START, None),
        ResearchFlowState.FINGERPRINTING: (
            "badge.local",
            ResearchUiCommand.CANCEL,
            "busy.fingerprinting",
        ),
        ResearchFlowState.INTAKE_CAUSAL: (
            "badge.local",
            ResearchUiCommand.CAUSAL_NO,
            None,
        ),
        ResearchFlowState.INTAKE_BLOCKED: (
            "badge.scope",
            ResearchUiCommand.BACK,
            None,
        ),
        ResearchFlowState.INTAKE_PROFILE: (
            "badge.local",
            ResearchUiCommand.SELECT_PROFILE,
            None,
        ),
        ResearchFlowState.INTAKE_ROLES: (
            "badge.local",
            ResearchUiCommand.SUBMIT_ROLES,
            None,
        ),
        ResearchFlowState.MEANING_REVIEWING: (
            "badge.local",
            ResearchUiCommand.CANCEL,
            "busy.meaning_reviewing",
        ),
        ResearchFlowState.VARIABLE_MEANING_REVIEW: (
            "badge.local",
            ResearchUiCommand.CONFIRM_MEANINGS,
            None,
        ),
        ResearchFlowState.COMMITTING: (
            "badge.local",
            ResearchUiCommand.CANCEL,
            "busy.committing",
        ),
        ResearchFlowState.HANDOFF_PREFLIGHT: (
            "badge.local",
            ResearchUiCommand.CANCEL,
            "busy.handoff_preflight",
        ),
        ResearchFlowState.MEMORY_UNAVAILABLE: (
            "badge.unavailable",
            ResearchUiCommand.RESUME,
            None,
        ),
        ResearchFlowState.FAILURE: (
            "badge.error",
            ResearchUiCommand.RESUME,
            None,
        ),
        ResearchFlowState.CORRUPTION: (
            "badge.integrity",
            ResearchUiCommand.BACK,
            None,
        ),
        ResearchFlowState.REPLAN_REQUIRED: (
            "badge.stale",
            ResearchUiCommand.REPLAN,
            None,
        ),
        ResearchFlowState.CANCELLED: (
            "badge.cancelled",
            ResearchUiCommand.RESUME,
            None,
        ),
        ResearchFlowState.PREPARE_REVIEW: ("badge.local", None, None),
        ResearchFlowState.CONFIRMED: ("badge.local", None, None),
        ResearchFlowState.MANUAL_RUN: ("badge.local", None, None),
    }
)


def present_transient_state(
    state: ResearchFlowState,
    *,
    mode: ControllerMode,
    language: Language,
) -> ResearchFlowView:
    """Present only non-authoritative in-memory controller states."""

    mode, language = _validate_context(mode, language)
    if not isinstance(state, ResearchFlowState):
        raise ResearchFlowPresentationError("state must be a ResearchFlowState")
    if state is ResearchFlowState.ROUTE_READY:
        raise ResearchFlowPresentationError("route_ready is unreachable in the P1 flow")
    row = _TRANSIENT_COPY.get(state)
    if row is None:
        raise ResearchFlowPresentationError(
            "durable or static authority cannot be presented as transient"
        )
    badge_key, command, stage_key = row
    title, body = _state_copy(language, state)
    secondary: tuple[ResearchUiAction, ...] = ()
    if state is ResearchFlowState.INTAKE_CAUSAL:
        secondary = (
            _action(ResearchUiCommand.CAUSAL_YES, language),
            _action(ResearchUiCommand.CAUSAL_NOT_SURE, language),
        )
    elif state is ResearchFlowState.VARIABLE_MEANING_REVIEW:
        secondary = (_action(ResearchUiCommand.BACK, language),)
    return _base_view(
        state=state,
        mode=mode,
        language=language,
        title=title,
        body=body,
        stage_text=_copy(language, stage_key) if stage_key else "",
        badge_text=_copy(language, badge_key),
        primary_action=_action(command, language) if command else None,
        secondary_actions=secondary,
    )
