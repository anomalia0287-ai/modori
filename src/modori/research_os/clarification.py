from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any
import unicodedata

from modori.research_os.contracts import canonical_digest


class ClarificationError(ValueError):
    """Raised when a clarification contract is malformed or incomplete."""


class AnswerKind(str, Enum):
    YES_NO = "yes_no"
    SINGLE_CHOICE = "single_choice"
    VARIABLE_SINGLE = "variable_single"
    VARIABLE_MULTI = "variable_multi"
    ORDERED_VARIABLES = "ordered_variables"
    LEVEL_CHOICE = "level_choice"
    BOUNDED_TEXT = "bounded_text"
    CONFLICT_RESOLUTION = "conflict_resolution"


class ClarificationTrigger(str, Enum):
    ACTION_CHANGE = "action_change"
    METHOD_IDENTITY_CHANGE = "method_identity_change"
    ROLE_CHANGE = "role_change"
    DESIGN_CHANGE = "design_change"
    ESTIMAND_CHANGE = "estimand_change"
    CLAIM_BOUNDARY_CHANGE = "claim_boundary_change"
    DATA_POLICY_CHANGE = "data_policy_change"


class ClarificationLifecycle(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class BranchMatchKind(str, Enum):
    CHOICE_VALUES = "choice_values"
    EMPTY_VARIABLES = "empty_variables"
    NONEMPTY_VARIABLES = "nonempty_variables"
    ANSWERED = "answered"
    NOT_SURE = "not_sure"


_CHOICE_KINDS = {
    AnswerKind.YES_NO,
    AnswerKind.SINGLE_CHOICE,
    AnswerKind.LEVEL_CHOICE,
    AnswerKind.CONFLICT_RESOLUTION,
}
_OPEN_KINDS = set(AnswerKind) - _CHOICE_KINDS
_REFERENCE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_CHOICE_VALUE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_METHOD_MARKERS = (
    "pearson",
    "spearman",
    "welch",
    "t-test",
    "t test",
    "t검정",
    "t 검정",
    "anova",
)


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClarificationError(f"{field_name} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise ClarificationError(f"{field_name} must use canonical NFC Unicode")
    return value


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ClarificationError(f"{context} unknown field(s): {', '.join(unknown)}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise ClarificationError(f"{context} missing field(s): {', '.join(missing)}")


def _require_mapping(value: object, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClarificationError(f"{context} must be an object")
    return value


def _decode_enum(enum_type: type[Enum], value: object, context: str) -> Enum:
    if not isinstance(value, str):
        raise ClarificationError(f"{context} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ClarificationError(f"{context} has unknown value: {value!r}") from exc


@dataclass(frozen=True)
class AnswerChoice:
    value: str
    label_ko: str
    label_en: str

    def __post_init__(self) -> None:
        _require_text(self.value, "choice value")
        if not _CHOICE_VALUE_RE.fullmatch(self.value):
            raise ClarificationError("choice value must be a lowercase closed identifier")
        _require_text(self.label_ko, "choice label_ko")
        _require_text(self.label_en, "choice label_en")

    def to_mapping(self) -> dict[str, str]:
        return {
            "value": self.value,
            "label_ko": self.label_ko,
            "label_en": self.label_en,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AnswerChoice:
        payload = _require_mapping(payload, "AnswerChoice")
        _require_exact_keys(
            payload,
            frozenset({"value", "label_ko", "label_en"}),
            "AnswerChoice",
        )
        return cls(
            value=_require_text(payload["value"], "choice value"),
            label_ko=_require_text(payload["label_ko"], "choice label_ko"),
            label_en=_require_text(payload["label_en"], "choice label_en"),
        )


@dataclass(frozen=True)
class ClarificationBranch:
    branch_id: str
    match_kind: BranchMatchKind
    choice_values: tuple[str, ...]
    effects: tuple[ClarificationTrigger, ...]

    def __post_init__(self) -> None:
        _require_text(self.branch_id, "branch_id")
        if not _CHOICE_VALUE_RE.fullmatch(self.branch_id):
            raise ClarificationError("branch_id must be a lowercase closed identifier")
        if not isinstance(self.match_kind, BranchMatchKind):
            raise ClarificationError("match_kind must be a BranchMatchKind")
        if not isinstance(self.choice_values, tuple):
            raise ClarificationError("choice_values must be a tuple")
        for value in self.choice_values:
            _require_text(value, "branch choice value")
            if not _CHOICE_VALUE_RE.fullmatch(value):
                raise ClarificationError(
                    "branch choice value must be a lowercase closed identifier"
                )
        if len(set(self.choice_values)) != len(self.choice_values):
            raise ClarificationError("branch choice_values cannot contain duplicates")
        if self.match_kind is BranchMatchKind.CHOICE_VALUES:
            if not self.choice_values:
                raise ClarificationError(
                    "choice_values branch requires at least one choice"
                )
        elif self.choice_values:
            raise ClarificationError(
                f"{self.match_kind.value} branch cannot carry choice_values"
            )
        if not isinstance(self.effects, tuple) or not self.effects:
            raise ClarificationError("branch effects must be a non-empty tuple")
        if any(not isinstance(effect, ClarificationTrigger) for effect in self.effects):
            raise ClarificationError(
                "branch effects must contain ClarificationTrigger values"
            )
        if len(set(self.effects)) != len(self.effects):
            raise ClarificationError("branch effects cannot contain duplicates")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "match_kind": self.match_kind.value,
            "choice_values": list(self.choice_values),
            "effects": [effect.value for effect in self.effects],
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarificationBranch:
        payload = _require_mapping(payload, "ClarificationBranch")
        _require_exact_keys(
            payload,
            frozenset({"branch_id", "match_kind", "choice_values", "effects"}),
            "ClarificationBranch",
        )
        raw_values = payload["choice_values"]
        raw_effects = payload["effects"]
        if not isinstance(raw_values, list):
            raise ClarificationError("branch choice_values must be a list")
        if not isinstance(raw_effects, list):
            raise ClarificationError("branch effects must be a list")
        return cls(
            branch_id=_require_text(payload["branch_id"], "branch_id"),
            match_kind=_decode_enum(
                BranchMatchKind,
                payload["match_kind"],
                "branch match_kind",
            ),  # type: ignore[arg-type]
            choice_values=tuple(
                _require_text(value, "branch choice value") for value in raw_values
            ),
            effects=tuple(
                _decode_enum(ClarificationTrigger, effect, "branch effect")
                for effect in raw_effects
            ),  # type: ignore[arg-type]
        )
@dataclass(frozen=True)
class ClarificationSpec:
    question_id: str
    version: int
    fact_address: str
    answer_kind: AnswerKind
    template_ko: str
    template_en: str
    why_ko: str
    why_en: str
    choices: tuple[AnswerChoice, ...]
    triggers: tuple[ClarificationTrigger, ...]
    not_sure_enabled: bool
    dependencies: tuple[str, ...]
    branches: tuple[ClarificationBranch, ...]
    lifecycle: ClarificationLifecycle

    def __post_init__(self) -> None:
        _require_text(self.question_id, "question_id")
        if not _REFERENCE_RE.fullmatch(self.question_id) or "." in self.question_id:
            raise ClarificationError("question_id must be a lowercase closed identifier")
        if type(self.version) is not int or self.version < 1:
            raise ClarificationError("version must be a positive integer")
        _require_text(self.fact_address, "fact_address")
        if not _REFERENCE_RE.fullmatch(self.fact_address) or "." not in self.fact_address:
            raise ClarificationError("fact_address must be a dotted lowercase address")
        if not isinstance(self.answer_kind, AnswerKind):
            raise ClarificationError("answer_kind must be an AnswerKind")
        for field_name in ("template_ko", "template_en", "why_ko", "why_en"):
            _require_text(getattr(self, field_name), field_name)
        self._validate_method_neutrality()
        if not isinstance(self.choices, tuple):
            raise ClarificationError("choices must be a tuple")
        if any(not isinstance(choice, AnswerChoice) for choice in self.choices):
            raise ClarificationError("choices must contain AnswerChoice values")
        values = tuple(choice.value for choice in self.choices)
        if len(set(values)) != len(values):
            raise ClarificationError("clarification has a duplicate choice value")
        if self.answer_kind in _CHOICE_KINDS and len(self.choices) < 2:
            raise ClarificationError("choice answer kind requires at least two choices")
        if self.answer_kind in _OPEN_KINDS and self.choices:
            raise ClarificationError(
                "open answer kind cannot define hard-coded choices"
            )
        if not isinstance(self.triggers, tuple):
            raise ClarificationError("triggers must be a tuple")
        if not self.triggers:
            raise ClarificationError("clarification requires at least one trigger")
        if any(not isinstance(trigger, ClarificationTrigger) for trigger in self.triggers):
            raise ClarificationError(
                "triggers must contain ClarificationTrigger values"
            )
        if len(set(self.triggers)) != len(self.triggers):
            raise ClarificationError("clarification has a duplicate trigger")
        if self.not_sure_enabled is not True:
            raise ClarificationError("not_sure_enabled must be true")
        self._validate_dependencies()
        self._validate_branches(values)

    def _validate_dependencies(self) -> None:
        if not isinstance(self.dependencies, tuple):
            raise ClarificationError("dependencies must be a tuple")
        for dependency in self.dependencies:
            _require_text(dependency, "dependency")
            if not _REFERENCE_RE.fullmatch(dependency) or "." not in dependency:
                raise ClarificationError(
                    "dependency must be a dotted lowercase address"
                )
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ClarificationError("clarification has a duplicate dependency")
        if self.fact_address in self.dependencies:
            raise ClarificationError("clarification cannot depend on its own fact")

    def _validate_branches(self, choice_values: tuple[str, ...]) -> None:
        if not isinstance(self.lifecycle, ClarificationLifecycle):
            raise ClarificationError("lifecycle must be a ClarificationLifecycle")
        if not isinstance(self.branches, tuple):
            raise ClarificationError("branches must be a tuple")
        if any(not isinstance(branch, ClarificationBranch) for branch in self.branches):
            raise ClarificationError(
                "branches must contain ClarificationBranch values"
            )
        branch_ids = tuple(branch.branch_id for branch in self.branches)
        if len(set(branch_ids)) != len(branch_ids):
            raise ClarificationError("clarification has a duplicate branch_id")
        for branch in self.branches:
            if not set(branch.effects).issubset(self.triggers):
                raise ClarificationError(
                    "branch effects must be declared by clarification triggers"
                )
        if self.lifecycle is not ClarificationLifecycle.ACTIVE:
            return
        not_sure_count = sum(
            branch.match_kind is BranchMatchKind.NOT_SURE
            for branch in self.branches
        )
        if not_sure_count != 1:
            raise ClarificationError(
                "active clarification requires exactly one not_sure branch"
            )
        match_kinds = {branch.match_kind for branch in self.branches}
        if self.answer_kind in _CHOICE_KINDS:
            covered = tuple(
                value
                for branch in self.branches
                if branch.match_kind is BranchMatchKind.CHOICE_VALUES
                for value in branch.choice_values
            )
            if len(set(covered)) != len(covered):
                raise ClarificationError("choice is covered by multiple branches")
            unknown = sorted(set(covered) - set(choice_values))
            if unknown:
                raise ClarificationError(
                    f"branch covers unregistered choice(s): {', '.join(unknown)}"
                )
            missing = sorted(set(choice_values) - set(covered))
            if missing:
                raise ClarificationError(
                    f"active clarification has uncovered choice(s): {', '.join(missing)}"
                )
            forbidden = match_kinds - {
                BranchMatchKind.CHOICE_VALUES,
                BranchMatchKind.NOT_SURE,
            }
            if forbidden:
                raise ClarificationError(
                    "choice clarification has an incompatible branch kind"
                )
        elif self.answer_kind is AnswerKind.VARIABLE_MULTI:
            for required in (
                BranchMatchKind.EMPTY_VARIABLES,
                BranchMatchKind.NONEMPTY_VARIABLES,
            ):
                count = sum(
                    branch.match_kind is required for branch in self.branches
                )
                if count == 0:
                    raise ClarificationError(
                        f"variable_multi requires a {required.value} branch"
                    )
                if count != 1:
                    raise ClarificationError(
                        f"variable_multi requires exactly one {required.value} branch"
                    )
            allowed = {
                BranchMatchKind.EMPTY_VARIABLES,
                BranchMatchKind.NONEMPTY_VARIABLES,
                BranchMatchKind.NOT_SURE,
            }
            if match_kinds - allowed:
                raise ClarificationError(
                    "variable_multi has an incompatible branch kind"
                )
        else:
            answered_count = sum(
                branch.match_kind is BranchMatchKind.ANSWERED
                for branch in self.branches
            )
            if answered_count == 0:
                raise ClarificationError(
                    "open clarification requires an answered branch"
                )
            if answered_count != 1:
                raise ClarificationError(
                    "open clarification requires exactly one answered branch"
                )
            allowed = {BranchMatchKind.ANSWERED, BranchMatchKind.NOT_SURE}
            if match_kinds - allowed:
                raise ClarificationError(
                    "open clarification has an incompatible branch kind"
                )

    def _validate_method_neutrality(self) -> None:
        combined = " ".join(
            (self.template_ko, self.template_en, self.why_ko, self.why_en)
        ).casefold()
        if any(marker in combined for marker in _METHOD_MARKERS):
            raise ClarificationError(
                "clarification text cannot name a statistical method name"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "version": self.version,
            "fact_address": self.fact_address,
            "answer_kind": self.answer_kind.value,
            "template_ko": self.template_ko,
            "template_en": self.template_en,
            "why_ko": self.why_ko,
            "why_en": self.why_en,
            "choices": [choice.to_mapping() for choice in self.choices],
            "triggers": [trigger.value for trigger in self.triggers],
            "not_sure_enabled": self.not_sure_enabled,
            "dependencies": list(self.dependencies),
            "branches": [branch.to_mapping() for branch in self.branches],
            "lifecycle": self.lifecycle.value,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarificationSpec:
        payload = _require_mapping(payload, "ClarificationSpec")
        allowed = frozenset(
            {
                "question_id",
                "version",
                "fact_address",
                "answer_kind",
                "template_ko",
                "template_en",
                "why_ko",
                "why_en",
                "choices",
                "triggers",
                "not_sure_enabled",
                "dependencies",
                "branches",
                "lifecycle",
            }
        )
        _require_exact_keys(payload, allowed, "ClarificationSpec")
        if type(payload["version"]) is not int:
            raise ClarificationError("version must be a positive integer")
        raw_choices = payload["choices"]
        raw_triggers = payload["triggers"]
        raw_dependencies = payload["dependencies"]
        raw_branches = payload["branches"]
        if not isinstance(raw_choices, list):
            raise ClarificationError("choices must be a list")
        if not isinstance(raw_triggers, list):
            raise ClarificationError("triggers must be a list")
        if not isinstance(raw_dependencies, list):
            raise ClarificationError("dependencies must be a list")
        if not isinstance(raw_branches, list):
            raise ClarificationError("branches must be a list")
        if type(payload["not_sure_enabled"]) is not bool:
            raise ClarificationError("not_sure_enabled must be a boolean")
        return cls(
            question_id=_require_text(payload["question_id"], "question_id"),
            version=payload["version"],
            fact_address=_require_text(payload["fact_address"], "fact_address"),
            answer_kind=_decode_enum(
                AnswerKind,
                payload["answer_kind"],
                "answer_kind",
            ),  # type: ignore[arg-type]
            template_ko=_require_text(payload["template_ko"], "template_ko"),
            template_en=_require_text(payload["template_en"], "template_en"),
            why_ko=_require_text(payload["why_ko"], "why_ko"),
            why_en=_require_text(payload["why_en"], "why_en"),
            choices=tuple(
                AnswerChoice.from_mapping(_require_mapping(item, "AnswerChoice"))
                for item in raw_choices
            ),
            triggers=tuple(
                _decode_enum(ClarificationTrigger, item, "trigger")
                for item in raw_triggers
            ),  # type: ignore[arg-type]
            not_sure_enabled=payload["not_sure_enabled"],
            dependencies=tuple(
                _require_text(dependency, "dependency")
                for dependency in raw_dependencies
            ),
            branches=tuple(
                ClarificationBranch.from_mapping(
                    _require_mapping(branch, "ClarificationBranch")
                )
                for branch in raw_branches
            ),
            lifecycle=_decode_enum(
                ClarificationLifecycle,
                payload["lifecycle"],
                "lifecycle",
            ),  # type: ignore[arg-type]
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())


@dataclass(frozen=True)
class ClarificationRegistry:
    questions: tuple[ClarificationSpec, ...]
    required_question_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.questions, tuple):
            raise ClarificationError("questions must be a tuple")
        if any(not isinstance(question, ClarificationSpec) for question in self.questions):
            raise ClarificationError("questions must contain ClarificationSpec values")
        question_ids = tuple(question.question_id for question in self.questions)
        if len(set(question_ids)) != len(question_ids):
            raise ClarificationError("registry has a duplicate question_id")
        if not isinstance(self.required_question_ids, tuple):
            raise ClarificationError("required_question_ids must be a tuple")
        for question_id in self.required_question_ids:
            _require_text(question_id, "required question ID")
        if len(set(self.required_question_ids)) != len(self.required_question_ids):
            raise ClarificationError("required_question_ids cannot contain duplicates")
        if self.required_question_ids != tuple(sorted(self.required_question_ids)):
            raise ClarificationError("required_question_ids must be sorted")
        missing = sorted(set(self.required_question_ids) - set(question_ids))
        if missing:
            raise ClarificationError(
                f"registry missing question(s): {', '.join(missing)}"
            )
        unused = sorted(set(question_ids) - set(self.required_question_ids))
        if unused:
            raise ClarificationError(
                f"registry has unused question(s): {', '.join(unused)}"
            )

    @property
    def question_ids(self) -> tuple[str, ...]:
        return tuple(question.question_id for question in self.questions)

    def get(self, question_id: str) -> ClarificationSpec:
        _require_text(question_id, "question_id")
        for question in self.questions:
            if question.question_id == question_id:
                return question
        raise ClarificationError(f"unknown clarification question: {question_id}")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "questions": [question.to_mapping() for question in self.questions],
            "required_question_ids": list(self.required_question_ids),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ClarificationRegistry:
        payload = _require_mapping(payload, "ClarificationRegistry")
        _require_exact_keys(
            payload,
            frozenset({"questions", "required_question_ids"}),
            "ClarificationRegistry",
        )
        raw_questions = payload["questions"]
        raw_required = payload["required_question_ids"]
        if not isinstance(raw_questions, list):
            raise ClarificationError("questions must be a list")
        if not isinstance(raw_required, list):
            raise ClarificationError("required_question_ids must be a list")
        return cls(
            questions=tuple(
                ClarificationSpec.from_mapping(
                    _require_mapping(item, "ClarificationSpec")
                )
                for item in raw_questions
            ),
            required_question_ids=tuple(
                _require_text(item, "required question ID") for item in raw_required
            ),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())
