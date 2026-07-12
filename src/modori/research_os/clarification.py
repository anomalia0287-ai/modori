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
            }
        )
        _require_exact_keys(payload, allowed, "ClarificationSpec")
        if type(payload["version"]) is not int:
            raise ClarificationError("version must be a positive integer")
        raw_choices = payload["choices"]
        raw_triggers = payload["triggers"]
        if not isinstance(raw_choices, list):
            raise ClarificationError("choices must be a list")
        if not isinstance(raw_triggers, list):
            raise ClarificationError("triggers must be a list")
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
