from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal


ActionClass = Literal[
    "recommendation_eligible",
    "clarification_required",
    "abstention_required",
]
ActionKind = Literal["recommend", "clarify", "abstain"]
RecommendationLevel = Literal["strong", "candidate", "caution", "none"]


class BenchmarkContractError(ValueError):
    pass


def _require_nonempty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _reject_unknown_keys(mapping: Mapping[str, object], allowed: set[str]) -> None:
    unknown = sorted(str(key) for key in mapping if key not in allowed)
    if unknown:
        raise BenchmarkContractError(f"unknown keys: {', '.join(unknown)}")


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise BenchmarkContractError(f"{field_name} must be a list of strings")
    result = tuple(_require_nonempty_string(item, field_name) for item in value)
    if len(set(result)) != len(result):
        raise BenchmarkContractError(f"{field_name} contains duplicate values")
    return result


@dataclass(frozen=True)
class RecommendationIdentity:
    family: str
    roles: tuple[tuple[str, tuple[str, ...]], ...]
    design_mode: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "family", _require_nonempty_string(self.family, "family"))
        object.__setattr__(
            self,
            "design_mode",
            _require_nonempty_string(self.design_mode, "design mode"),
        )
        normalized_roles: list[tuple[str, tuple[str, ...]]] = []
        seen: set[str] = set()
        for raw_name, raw_values in self.roles:
            name = _require_nonempty_string(raw_name, "role name")
            if name in seen:
                raise BenchmarkContractError(f"duplicate role: {name}")
            seen.add(name)
            values = _string_tuple(raw_values, f"role {name}")
            if not values:
                raise BenchmarkContractError(f"role {name} must contain a value")
            normalized_roles.append((name, values))
        if not normalized_roles:
            raise BenchmarkContractError("roles must not be empty")
        object.__setattr__(self, "roles", tuple(sorted(normalized_roles)))

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> RecommendationIdentity:
        _reject_unknown_keys(mapping, {"family", "roles", "design_mode"})
        raw_roles = mapping.get("roles")
        if not isinstance(raw_roles, Mapping):
            raise BenchmarkContractError("roles must be an object")
        roles = tuple(
            (str(name), _string_tuple(values, f"role {name}"))
            for name, values in raw_roles.items()
        )
        return cls(
            family=_require_nonempty_string(mapping.get("family"), "family"),
            roles=roles,
            design_mode=_require_nonempty_string(
                mapping.get("design_mode"),
                "design mode",
            ),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "family": self.family,
            "roles": {name: list(values) for name, values in self.roles},
            "design_mode": self.design_mode,
        }


@dataclass(frozen=True)
class PrimaryAction:
    kind: ActionKind | str
    value: RecommendationIdentity | str

    def validate(self) -> None:
        if self.kind == "recommend":
            if not isinstance(self.value, RecommendationIdentity):
                raise BenchmarkContractError("recommend action requires an identity")
            return
        if self.kind == "clarify":
            _require_nonempty_string(self.value, "clarification fact ID")
            return
        if self.kind == "abstain":
            _require_nonempty_string(self.value, "abstention reason code")
            return
        raise BenchmarkContractError(f"unknown action kind: {self.kind}")

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> PrimaryAction:
        _reject_unknown_keys(mapping, {"kind", "value"})
        kind = _require_nonempty_string(mapping.get("kind"), "action kind")
        raw_value = mapping.get("value")
        value: RecommendationIdentity | str
        if kind == "recommend":
            if not isinstance(raw_value, Mapping):
                raise BenchmarkContractError("recommend action requires an identity")
            value = RecommendationIdentity.from_mapping(raw_value)
        else:
            value = _require_nonempty_string(raw_value, "action value")
        action = cls(kind=kind, value=value)
        action.validate()
        return action

    def to_mapping(self) -> dict[str, object]:
        self.validate()
        value: object = (
            self.value.to_mapping()
            if isinstance(self.value, RecommendationIdentity)
            else self.value
        )
        return {"kind": self.kind, "value": value}


@dataclass(frozen=True)
class GoldRecord:
    case_id: str
    evidence_stage: str
    action_class: ActionClass | str
    acceptable_recommendations: tuple[RecommendationIdentity, ...] = ()
    required_clarification_facts: tuple[str, ...] = ()
    acceptable_abstention_reasons: tuple[str, ...] = ()
    failure_severity: str = "E3"

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_nonempty_string(self.case_id, "case ID"))
        object.__setattr__(
            self,
            "evidence_stage",
            _require_nonempty_string(self.evidence_stage, "evidence stage"),
        )
        if self.action_class not in {
            "recommendation_eligible",
            "clarification_required",
            "abstention_required",
        }:
            raise BenchmarkContractError(f"unknown action class: {self.action_class}")
        if self.action_class == "recommendation_eligible" and not self.acceptable_recommendations:
            raise BenchmarkContractError(
                "recommendation-eligible gold requires an acceptable recommendation"
            )
        if self.action_class == "clarification_required" and not self.required_clarification_facts:
            raise BenchmarkContractError(
                "clarification-required gold requires a clarification fact"
            )
        if self.action_class == "abstention_required" and not self.acceptable_abstention_reasons:
            raise BenchmarkContractError(
                "abstention-required gold requires an abstention reason"
            )
        if self.failure_severity not in {"E1", "E2", "E3", "E4", "E5"}:
            raise BenchmarkContractError("failure severity must be E1 through E5")
        object.__setattr__(
            self,
            "required_clarification_facts",
            _string_tuple(self.required_clarification_facts, "clarification facts"),
        )
        object.__setattr__(
            self,
            "acceptable_abstention_reasons",
            _string_tuple(self.acceptable_abstention_reasons, "abstention reasons"),
        )
        if len(set(self.acceptable_recommendations)) != len(
            self.acceptable_recommendations
        ):
            raise BenchmarkContractError("acceptable recommendations contain duplicates")

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> GoldRecord:
        _reject_unknown_keys(
            mapping,
            {
                "case_id",
                "evidence_stage",
                "action_class",
                "acceptable_recommendations",
                "required_clarification_facts",
                "acceptable_abstention_reasons",
                "failure_severity",
            },
        )
        raw_recommendations = mapping.get("acceptable_recommendations", ())
        if isinstance(raw_recommendations, str) or not isinstance(
            raw_recommendations,
            Sequence,
        ):
            raise BenchmarkContractError("acceptable recommendations must be a list")
        recommendations: list[RecommendationIdentity] = []
        for raw in raw_recommendations:
            if not isinstance(raw, Mapping):
                raise BenchmarkContractError(
                    "acceptable recommendation entries must be objects"
                )
            recommendations.append(RecommendationIdentity.from_mapping(raw))
        return cls(
            case_id=_require_nonempty_string(mapping.get("case_id"), "case ID"),
            evidence_stage=_require_nonempty_string(
                mapping.get("evidence_stage"),
                "evidence stage",
            ),
            action_class=_require_nonempty_string(
                mapping.get("action_class"),
                "action class",
            ),
            acceptable_recommendations=tuple(recommendations),
            required_clarification_facts=_string_tuple(
                mapping.get("required_clarification_facts", ()),
                "clarification facts",
            ),
            acceptable_abstention_reasons=_string_tuple(
                mapping.get("acceptable_abstention_reasons", ()),
                "abstention reasons",
            ),
            failure_severity=_require_nonempty_string(
                mapping.get("failure_severity", "E3"),
                "failure severity",
            ),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "evidence_stage": self.evidence_stage,
            "action_class": self.action_class,
            "acceptable_recommendations": [
                recommendation.to_mapping()
                for recommendation in self.acceptable_recommendations
            ],
            "required_clarification_facts": list(self.required_clarification_facts),
            "acceptable_abstention_reasons": list(
                self.acceptable_abstention_reasons
            ),
            "failure_severity": self.failure_severity,
        }


@dataclass(frozen=True)
class PredictionRecord:
    case_id: str
    evidence_stage: str
    primary_action: PrimaryAction
    candidates: tuple[RecommendationIdentity, ...] = ()
    level: RecommendationLevel | str = "none"
    questions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_nonempty_string(self.case_id, "case ID"))
        object.__setattr__(
            self,
            "evidence_stage",
            _require_nonempty_string(self.evidence_stage, "evidence stage"),
        )
        self.primary_action.validate()
        if len(self.candidates) > 3:
            raise BenchmarkContractError("prediction may contain at most three candidates")
        if len(set(self.candidates)) != len(self.candidates):
            raise BenchmarkContractError("prediction contains duplicate candidates")
        if self.level not in {"strong", "candidate", "caution", "none"}:
            raise BenchmarkContractError(f"unknown recommendation level: {self.level}")
        if self.primary_action.kind == "recommend":
            if self.primary_action.value not in self.candidates:
                raise BenchmarkContractError(
                    "recommended default must appear in candidates"
                )
            if self.level == "none":
                raise BenchmarkContractError("recommend action requires a level")
        elif self.level != "none":
            raise BenchmarkContractError("non-recommend action level must be none")
        object.__setattr__(self, "questions", _string_tuple(self.questions, "questions"))

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, object]) -> PredictionRecord:
        _reject_unknown_keys(
            mapping,
            {
                "case_id",
                "evidence_stage",
                "primary_action",
                "candidates",
                "level",
                "questions",
            },
        )
        raw_action = mapping.get("primary_action")
        if not isinstance(raw_action, Mapping):
            raise BenchmarkContractError("primary action must be an object")
        raw_candidates = mapping.get("candidates", ())
        if isinstance(raw_candidates, str) or not isinstance(raw_candidates, Sequence):
            raise BenchmarkContractError("candidates must be a list")
        candidates: list[RecommendationIdentity] = []
        for raw in raw_candidates:
            if not isinstance(raw, Mapping):
                raise BenchmarkContractError("candidate entries must be objects")
            candidates.append(RecommendationIdentity.from_mapping(raw))
        return cls(
            case_id=_require_nonempty_string(mapping.get("case_id"), "case ID"),
            evidence_stage=_require_nonempty_string(
                mapping.get("evidence_stage"),
                "evidence stage",
            ),
            primary_action=PrimaryAction.from_mapping(raw_action),
            candidates=tuple(candidates),
            level=_require_nonempty_string(mapping.get("level", "none"), "level"),
            questions=_string_tuple(mapping.get("questions", ()), "questions"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "evidence_stage": self.evidence_stage,
            "primary_action": self.primary_action.to_mapping(),
            "candidates": [candidate.to_mapping() for candidate in self.candidates],
            "level": self.level,
            "questions": list(self.questions),
        }


@dataclass(frozen=True)
class ScorerConfig:
    schema_version: int = 1
    scorer_version: str = "recommendation-scorer-v1"
    confidence_level: float = 0.95
    metric_contract: str = field(default="recommendation-action-stratified-v1")

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise BenchmarkContractError("unsupported scorer schema version")
        _require_nonempty_string(self.scorer_version, "scorer version")
        _require_nonempty_string(self.metric_contract, "metric contract")
        if not 0.5 < self.confidence_level < 1.0:
            raise BenchmarkContractError("confidence level must be between 0.5 and 1")


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def scorer_fingerprint(config: ScorerConfig) -> str:
    payload = canonical_json(asdict(config)).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
