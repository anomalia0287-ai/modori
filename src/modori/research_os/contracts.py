from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Generic, TypeVar
import unicodedata


T = TypeVar("T")


class ContractError(ValueError):
    """Raised when a canonical Research OS contract is invalid."""


class FactState(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    USER_CONFIRMED = "user_confirmed"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"
    STALE = "stale"


_CURRENT_STATES = {
    FactState.OBSERVED,
    FactState.INFERRED,
    FactState.USER_CONFIRMED,
}


def _require_nonblank(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field_name} must be a non-empty string")
    if value != unicodedata.normalize("NFC", value):
        raise ContractError(f"{field_name} must use canonical NFC Unicode")


def _require_exact_keys(
    payload: Mapping[str, Any],
    allowed: frozenset[str],
    context: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ContractError(f"{context} unknown field(s): {', '.join(unknown)}")
    missing = sorted(allowed - set(payload))
    if missing:
        raise ContractError(f"{context} missing field(s): {', '.join(missing)}")


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{context} must be an object")
    return value


def _decode_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ContractError("fact value must be a string")
    if value != unicodedata.normalize("NFC", value):
        raise ContractError("fact value must use canonical NFC Unicode")
    return value


def _decode_string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractError("fact value must be a list of strings")
    decoded = tuple(_decode_text(item) for item in value)
    if len(set(decoded)) != len(decoded):
        raise ContractError("fact value cannot contain duplicate variable IDs")
    return decoded


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise ContractError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _canonical_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validate_provenance_refs(refs: tuple[str, ...]) -> None:
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            raise ContractError("provenance reference must be a non-empty string")


@dataclass(frozen=True)
class StaleSnapshot(Generic[T]):
    value: T
    provenance_refs: tuple[str, ...]
    invalidation_reason: str

    def __post_init__(self) -> None:
        if self.value is None:
            raise ContractError("stale snapshot requires its prior value")
        if not self.provenance_refs:
            raise ContractError("stale snapshot requires original provenance")
        _validate_provenance_refs(self.provenance_refs)
        _require_nonblank(self.invalidation_reason, "invalidation_reason")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "value": _canonical_value(self.value),
            "provenance_refs": list(self.provenance_refs),
            "invalidation_reason": self.invalidation_reason,
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        value_decoder: Callable[[Any], T],
    ) -> StaleSnapshot[T]:
        payload = _require_mapping(payload, "StaleSnapshot")
        _require_exact_keys(
            payload,
            frozenset({"value", "provenance_refs", "invalidation_reason"}),
            "StaleSnapshot",
        )
        refs = payload["provenance_refs"]
        if not isinstance(refs, list):
            raise ContractError("StaleSnapshot provenance_refs must be a list")
        return cls(
            value=value_decoder(payload["value"]),
            provenance_refs=tuple(_decode_text(ref) for ref in refs),
            invalidation_reason=_decode_text(payload["invalidation_reason"]),
        )


@dataclass(frozen=True)
class Fact(Generic[T]):
    state: FactState
    value: T | None = None
    alternatives: tuple[T, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    reason_code: str | None = None
    stale_snapshot: StaleSnapshot[T] | None = None

    def __post_init__(self) -> None:
        _validate_provenance_refs(self.provenance_refs)
        if self.reason_code is not None:
            _require_nonblank(self.reason_code, "reason_code")

        if self.state in _CURRENT_STATES:
            self._validate_current()
        elif self.state is FactState.UNKNOWN:
            self._validate_unknown()
        elif self.state is FactState.CONFLICT:
            self._validate_conflict()
        elif self.state is FactState.NOT_APPLICABLE:
            self._validate_not_applicable()
        elif self.state is FactState.STALE:
            self._validate_stale()
        else:  # pragma: no cover - Enum construction prevents this branch.
            raise ContractError(f"unsupported fact state: {self.state!r}")

    def _validate_current(self) -> None:
        state_name = self.state.value
        if self.value is None:
            raise ContractError(f"{state_name} fact requires one value")
        if not self.provenance_refs:
            raise ContractError(f"{state_name} fact requires provenance")
        if self.alternatives:
            raise ContractError(f"{state_name} fact cannot carry alternatives")
        if self.stale_snapshot is not None:
            raise ContractError(f"{state_name} fact cannot carry stale_snapshot")

    def _validate_unknown(self) -> None:
        if (
            self.value is not None
            or self.alternatives
            or self.provenance_refs
            or self.stale_snapshot is not None
        ):
            raise ContractError(
                "unknown fact cannot carry a value, alternatives, provenance, "
                "or stale_snapshot"
            )

    def _validate_conflict(self) -> None:
        if self.value is not None or self.stale_snapshot is not None:
            raise ContractError(
                "conflict fact cannot carry a resolved value or stale_snapshot"
            )
        distinct: list[T] = []
        for alternative in self.alternatives:
            if alternative not in distinct:
                distinct.append(alternative)
        if len(distinct) < 2:
            raise ContractError(
                "conflict fact requires at least two distinct alternatives"
            )
        if len(self.provenance_refs) < 2:
            raise ContractError(
                "conflict fact requires provenance for incompatible alternatives"
            )

    def _validate_not_applicable(self) -> None:
        if self.value is not None or self.alternatives or self.stale_snapshot is not None:
            raise ContractError(
                "not_applicable fact cannot carry an active value, alternatives, "
                "or stale_snapshot"
            )
        if self.reason_code is None:
            raise ContractError("not_applicable fact requires reason_code")

    def _validate_stale(self) -> None:
        if self.value is not None or self.alternatives or self.provenance_refs:
            raise ContractError(
                "stale fact cannot carry an active value, alternatives, or provenance"
            )
        if self.stale_snapshot is None:
            raise ContractError("stale fact requires stale_snapshot")
        if self.reason_code is None:
            raise ContractError("stale fact requires reason_code")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "value": _canonical_value(self.value),
            "alternatives": [_canonical_value(item) for item in self.alternatives],
            "provenance_refs": list(self.provenance_refs),
            "reason_code": self.reason_code,
            "stale_snapshot": (
                None if self.stale_snapshot is None else self.stale_snapshot.to_mapping()
            ),
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        value_decoder: Callable[[Any], T],
    ) -> Fact[T]:
        payload = _require_mapping(payload, "Fact")
        _require_exact_keys(
            payload,
            frozenset(
                {
                    "state",
                    "value",
                    "alternatives",
                    "provenance_refs",
                    "reason_code",
                    "stale_snapshot",
                }
            ),
            "Fact",
        )
        try:
            state = FactState(str(payload["state"]))
        except ValueError as exc:
            raise ContractError(f"Fact has unknown state: {payload['state']!r}") from exc
        raw_alternatives = payload["alternatives"]
        raw_refs = payload["provenance_refs"]
        if not isinstance(raw_alternatives, list):
            raise ContractError("Fact alternatives must be a list")
        if not isinstance(raw_refs, list):
            raise ContractError("Fact provenance_refs must be a list")
        raw_value = payload["value"]
        raw_snapshot = payload["stale_snapshot"]
        reason_code = payload["reason_code"]
        if reason_code is not None:
            reason_code = _decode_text(reason_code)
        return cls(
            state=state,
            value=None if raw_value is None else value_decoder(raw_value),
            alternatives=tuple(value_decoder(item) for item in raw_alternatives),
            provenance_refs=tuple(_decode_text(ref) for ref in raw_refs),
            reason_code=reason_code,
            stale_snapshot=(
                None
                if raw_snapshot is None
                else StaleSnapshot.from_mapping(
                    _require_mapping(raw_snapshot, "Fact stale_snapshot"),
                    value_decoder,
                )
            ),
        )

    @classmethod
    def observed(cls, value: T, *, provenance_refs: tuple[str, ...]) -> Fact[T]:
        return cls(
            state=FactState.OBSERVED,
            value=value,
            provenance_refs=provenance_refs,
        )

    @classmethod
    def inferred(cls, value: T, *, provenance_refs: tuple[str, ...]) -> Fact[T]:
        return cls(
            state=FactState.INFERRED,
            value=value,
            provenance_refs=provenance_refs,
        )

    @classmethod
    def user_confirmed(
        cls,
        value: T,
        *,
        provenance_refs: tuple[str, ...],
    ) -> Fact[T]:
        return cls(
            state=FactState.USER_CONFIRMED,
            value=value,
            provenance_refs=provenance_refs,
        )

    @classmethod
    def unknown(cls, *, reason_code: str | None = None) -> Fact[T]:
        return cls(state=FactState.UNKNOWN, reason_code=reason_code)

    @classmethod
    def conflict(
        cls,
        alternatives: tuple[T, ...],
        *,
        provenance_refs: tuple[str, ...],
        reason_code: str | None = None,
    ) -> Fact[T]:
        return cls(
            state=FactState.CONFLICT,
            alternatives=alternatives,
            provenance_refs=provenance_refs,
            reason_code=reason_code,
        )

    @classmethod
    def not_applicable(cls, *, reason_code: str) -> Fact[T]:
        return cls(
            state=FactState.NOT_APPLICABLE,
            reason_code=reason_code,
        )

    @classmethod
    def stale(
        cls,
        snapshot: StaleSnapshot[T],
        *,
        reason_code: str,
    ) -> Fact[T]:
        return cls(
            state=FactState.STALE,
            reason_code=reason_code,
            stale_snapshot=snapshot,
        )


@dataclass(frozen=True)
class SchemaEnvelope:
    schema_id: str
    schema_version: int
    project_id: str
    object_id: str
    revision: int
    supersedes_revision: int | None
    created_event_ref: str

    def __post_init__(self) -> None:
        _require_nonblank(self.schema_id, "schema_id")
        _require_nonblank(self.project_id, "project_id")
        _require_nonblank(self.object_id, "object_id")
        _require_nonblank(self.created_event_ref, "created_event_ref")
        if self.schema_version < 1:
            raise ContractError("schema_version must be at least 1")
        if self.revision < 1:
            raise ContractError("revision must be at least 1")
        if self.supersedes_revision is not None and not (
            1 <= self.supersedes_revision < self.revision
        ):
            raise ContractError(
                "supersedes_revision must be positive and lower than revision"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "object_id": self.object_id,
            "revision": self.revision,
            "supersedes_revision": self.supersedes_revision,
            "created_event_ref": self.created_event_ref,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SchemaEnvelope:
        payload = _require_mapping(payload, "SchemaEnvelope")
        allowed = frozenset(
            {
                "schema_id",
                "schema_version",
                "project_id",
                "object_id",
                "revision",
                "supersedes_revision",
                "created_event_ref",
            }
        )
        _require_exact_keys(payload, allowed, "SchemaEnvelope")
        supersedes = payload["supersedes_revision"]
        if supersedes is not None and not isinstance(supersedes, int):
            raise ContractError("supersedes_revision must be an integer or null")
        if not isinstance(payload["schema_version"], int):
            raise ContractError("schema_version must be an integer")
        if not isinstance(payload["revision"], int):
            raise ContractError("revision must be an integer")
        return cls(
            schema_id=_decode_text(payload["schema_id"]),
            schema_version=payload["schema_version"],
            project_id=_decode_text(payload["project_id"]),
            object_id=_decode_text(payload["object_id"]),
            revision=payload["revision"],
            supersedes_revision=supersedes,
            created_event_ref=_decode_text(payload["created_event_ref"]),
        )


class CaptureMode(str, Enum):
    FREE_TEXT = "free_text"
    STRUCTURED = "structured"
    HYBRID = "hybrid"


class Language(str, Enum):
    KO = "ko"
    EN = "en"
    MIXED = "mixed"
    UND = "und"


class ResearchGoal(str, Enum):
    DESCRIBE = "describe"
    COMPARE = "compare"
    ASSOCIATE = "associate"
    PREDICT = "predict"
    ESTIMATE_EFFECT = "estimate_effect"
    EVALUATE_MEASUREMENT = "evaluate_measurement"
    EXPLORE_STRUCTURE = "explore_structure"
    EXAMINE_PROCESS = "examine_process"
    OTHER_SPECIFIED = "other_specified"


class CausalIntent(str, Enum):
    NONCAUSAL = "noncausal"
    CAUSAL = "causal"


class RoleHint(str, Enum):
    OUTCOME = "outcome"
    EXPOSURE = "exposure"
    GROUP = "group"
    PREDICTOR = "predictor"
    COVARIATE = "covariate"
    MEDIATOR = "mediator"
    MODERATOR = "moderator"
    ITEM = "item"
    REPEATED_MEASURE = "repeated_measure"
    UNSPECIFIED = "unspecified"


class EstimandTemplate(str, Enum):
    SUMMARY = "summary"
    FREQUENCY_DISTRIBUTION = "frequency_distribution"
    GROUP_CONTRAST = "group_contrast"
    WITHIN_UNIT_CHANGE = "within_unit_change"
    ASSOCIATION = "association"
    CONDITIONAL_ASSOCIATION = "conditional_association"
    PREDICTION_TARGET = "prediction_target"
    INTERNAL_CONSISTENCY_COEFFICIENT = "internal_consistency_coefficient"
    LATENT_STRUCTURE_TARGET = "latent_structure_target"
    INDIRECT_ASSOCIATION = "indirect_association"
    CONDITIONAL_INDIRECT_ASSOCIATION = "conditional_indirect_association"
    CAUSAL_EFFECT = "causal_effect"
    OTHER_SPECIFIED = "other_specified"


class ClaimBasis(str, Enum):
    DESCRIPTIVE = "descriptive"
    ASSOCIATIONAL = "associational"
    PREDICTIVE = "predictive"
    MEASUREMENT = "measurement"
    EXPLORATORY = "exploratory"
    CAUSAL = "causal"


class TargetRole(str, Enum):
    OUTCOME = "outcome"
    EXPOSURE = "exposure"
    GROUP = "group"
    FOCAL_PREDICTOR = "focal_predictor"
    MEDIATOR = "mediator"
    MODERATOR = "moderator"
    ITEM_SET = "item_set"
    REPEATED_MEASURE = "repeated_measure"


class ContrastKind(str, Enum):
    PAIRWISE = "pairwise"
    OMNIBUS = "omnibus"
    TREND = "trend"
    REFERENCE_LEVEL = "reference_level"
    USER_SPECIFIED = "user_specified"
    NOT_APPLICABLE = "not_applicable"


class EffectScale(str, Enum):
    DISTRIBUTION = "distribution"
    MEAN = "mean"
    MEDIAN = "median"
    PROBABILITY = "probability"
    PROPORTION = "proportion"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    CORRELATION = "correlation"
    SLOPE = "slope"
    ODDS = "odds"
    RISK = "risk"
    COEFFICIENT_ALPHA = "coefficient_alpha"
    OMEGA_TOTAL = "omega_total"
    OMEGA_HIERARCHICAL = "omega_hierarchical"
    LATENT_STRUCTURE = "latent_structure"
    INDIRECT_EFFECT = "indirect_effect"
    PREDICTION_METRIC = "prediction_metric"
    OTHER_SPECIFIED = "other_specified"


class AssociationTarget(str, Enum):
    PRODUCT_MOMENT = "product_moment"
    RANK_MONOTONIC = "rank_monotonic"
    NOT_APPLICABLE = "not_applicable"


class UnitKind(str, Enum):
    PERSON = "person"
    HOUSEHOLD = "household"
    ORGANIZATION = "organization"
    EVENT = "event"
    ENCOUNTER = "encounter"
    ITEM_RESPONSE = "item_response"
    TIMEPOINT = "timepoint"
    AGGREGATE_CELL = "aggregate_cell"
    GEOGRAPHIC_UNIT = "geographic_unit"
    OTHER_SPECIFIED = "other_specified"


class DesignFamily(str, Enum):
    OBSERVATIONAL = "observational"
    RANDOMIZED_EXPERIMENT = "randomized_experiment"
    QUASI_EXPERIMENT = "quasi_experiment"
    MEASUREMENT_STUDY = "measurement_study"
    DESCRIPTIVE_ADMINISTRATIVE = "descriptive_administrative"
    AGGREGATE_ECOLOGICAL = "aggregate_ecological"
    MIXED_DESIGN = "mixed_design"
    OTHER_SPECIFIED = "other_specified"


class DataLayout(str, Enum):
    UNIT_ROWS = "unit_rows"
    LONG_REPEATED = "long_repeated"
    WIDE_REPEATED = "wide_repeated"
    AGGREGATE_ROWS = "aggregate_rows"
    CONTINGENCY_COUNTS = "contingency_counts"
    MATRIX = "matrix"
    MIXED = "mixed"


class TemporalStructure(str, Enum):
    SINGLE_WAVE = "single_wave"
    REPEATED_PANEL = "repeated_panel"
    REPEATED_CROSS_SECTION = "repeated_cross_section"
    EVENT_HISTORY = "event_history"
    ROLLING = "rolling"
    OTHER_SPECIFIED = "other_specified"


class DependenceKind(str, Enum):
    INDEPENDENT = "independent"
    PAIRED = "paired"
    REPEATED_WITHIN_UNIT = "repeated_within_unit"
    CLUSTERED = "clustered"
    NESTED = "nested"
    CROSSED = "crossed"
    SPATIAL = "spatial"
    NETWORK = "network"


class AssignmentMechanism(str, Enum):
    RANDOMIZED = "randomized"
    AS_IF_RANDOM = "as_if_random"
    NONRANDOMIZED = "nonrandomized"
    UNKNOWN = "unknown"


class SamplingDesign(str, Enum):
    CENSUS = "census"
    PROBABILITY_SIMPLE = "probability_simple"
    PROBABILITY_STRATIFIED = "probability_stratified"
    PROBABILITY_CLUSTER = "probability_cluster"
    PROBABILITY_MULTISTAGE = "probability_multistage"
    QUOTA = "quota"
    CONVENIENCE = "convenience"
    PURPOSIVE = "purposive"
    ADMINISTRATIVE = "administrative"
    UNKNOWN = "unknown"


class StudyRole(str, Enum):
    PAIR_ID = "pair_id"
    REPEATED_UNIT = "repeated_unit"
    TIME = "time"
    CLUSTER = "cluster"
    STRATUM = "stratum"
    WEIGHT = "weight"


def _decode_enum(enum_type: type[T]) -> Callable[[Any], T]:
    def decode(value: Any) -> T:
        try:
            return enum_type(str(value))
        except ValueError as exc:
            raise ContractError(
                f"unknown {enum_type.__name__} value: {value!r}"
            ) from exc

    return decode


@dataclass(frozen=True)
class RoleHintBinding:
    concept_id: str
    role: RoleHint

    def __post_init__(self) -> None:
        _require_nonblank(self.concept_id, "concept_id")

    def to_mapping(self) -> dict[str, Any]:
        return {"concept_id": self.concept_id, "role": self.role.value}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RoleHintBinding:
        payload = _require_mapping(payload, "RoleHintBinding")
        _require_exact_keys(
            payload,
            frozenset({"concept_id", "role"}),
            "RoleHintBinding",
        )
        return cls(
            concept_id=_decode_text(payload["concept_id"]),
            role=_decode_enum(RoleHint)(payload["role"]),
        )


@dataclass(frozen=True)
class TargetRoleBinding:
    role: TargetRole
    variable_ids: Fact[tuple[str, ...]]

    def __post_init__(self) -> None:
        if self.variable_ids.state in _CURRENT_STATES and not self.variable_ids.value:
            raise ContractError(f"target role {self.role.value} requires a variable")

    def to_mapping(self) -> dict[str, Any]:
        return {"role": self.role.value, "variable_ids": self.variable_ids.to_mapping()}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> TargetRoleBinding:
        payload = _require_mapping(payload, "TargetRoleBinding")
        _require_exact_keys(
            payload,
            frozenset({"role", "variable_ids"}),
            "TargetRoleBinding",
        )
        return cls(
            role=_decode_enum(TargetRole)(payload["role"]),
            variable_ids=Fact.from_mapping(
                _require_mapping(payload["variable_ids"], "target variable_ids"),
                _decode_string_tuple,
            ),
        )


@dataclass(frozen=True)
class StudyRoleBinding:
    role: StudyRole
    variable_ids: Fact[tuple[str, ...]]

    def to_mapping(self) -> dict[str, Any]:
        return {"role": self.role.value, "variable_ids": self.variable_ids.to_mapping()}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> StudyRoleBinding:
        payload = _require_mapping(payload, "StudyRoleBinding")
        _require_exact_keys(
            payload,
            frozenset({"role", "variable_ids"}),
            "StudyRoleBinding",
        )
        return cls(
            role=_decode_enum(StudyRole)(payload["role"]),
            variable_ids=Fact.from_mapping(
                _require_mapping(payload["variable_ids"], "study variable_ids"),
                _decode_string_tuple,
            ),
        )


@dataclass(frozen=True)
class MissingCodeMeaning:
    variable_id: str
    code: str
    meaning: str

    def __post_init__(self) -> None:
        _require_nonblank(self.variable_id, "variable_id")
        _require_nonblank(self.code, "code")
        _require_nonblank(self.meaning, "meaning")

    def to_mapping(self) -> dict[str, str]:
        return {
            "variable_id": self.variable_id,
            "code": self.code,
            "meaning": self.meaning,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> MissingCodeMeaning:
        payload = _require_mapping(payload, "MissingCodeMeaning")
        _require_exact_keys(
            payload,
            frozenset({"variable_id", "code", "meaning"}),
            "MissingCodeMeaning",
        )
        return cls(
            variable_id=_decode_text(payload["variable_id"]),
            code=_decode_text(payload["code"]),
            meaning=_decode_text(payload["meaning"]),
        )


def _require_schema(envelope: SchemaEnvelope, schema_id: str) -> None:
    if envelope.schema_id != schema_id:
        raise ContractError(
            f"expected schema_id {schema_id!r}, got {envelope.schema_id!r}"
        )
    if envelope.schema_version != 1:
        raise ContractError(f"{schema_id} supports only schema_version 1")


def _fact_field(
    payload: Mapping[str, Any],
    field_name: str,
    decoder: Callable[[Any], T],
) -> Fact[T]:
    return Fact.from_mapping(
        _require_mapping(payload[field_name], field_name),
        decoder,
    )


@dataclass(frozen=True)
class QuestionSpec:
    envelope: SchemaEnvelope
    capture_mode: CaptureMode
    language: Language
    local_text: str | None
    research_goal: Fact[ResearchGoal]
    causal_intent: Fact[CausalIntent]
    role_hints: tuple[RoleHintBinding, ...] = ()

    def __post_init__(self) -> None:
        _require_schema(self.envelope, "modori.question_spec")
        if self.local_text is not None:
            _decode_text(self.local_text)
        identities = [(binding.concept_id, binding.role) for binding in self.role_hints]
        if len(set(identities)) != len(identities):
            raise ContractError("QuestionSpec contains duplicate role hints")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_mapping(),
            "capture_mode": self.capture_mode.value,
            "language": self.language.value,
            "local_text": self.local_text,
            "research_goal": self.research_goal.to_mapping(),
            "causal_intent": self.causal_intent.to_mapping(),
            "role_hints": [binding.to_mapping() for binding in self.role_hints],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> QuestionSpec:
        payload = _require_mapping(payload, "QuestionSpec")
        allowed = frozenset(
            {
                "envelope",
                "capture_mode",
                "language",
                "local_text",
                "research_goal",
                "causal_intent",
                "role_hints",
            }
        )
        _require_exact_keys(payload, allowed, "QuestionSpec")
        raw_hints = payload["role_hints"]
        if not isinstance(raw_hints, list):
            raise ContractError("QuestionSpec role_hints must be a list")
        local_text = payload["local_text"]
        if local_text is not None:
            local_text = _decode_text(local_text)
        return cls(
            envelope=SchemaEnvelope.from_mapping(
                _require_mapping(payload["envelope"], "QuestionSpec envelope")
            ),
            capture_mode=_decode_enum(CaptureMode)(payload["capture_mode"]),
            language=_decode_enum(Language)(payload["language"]),
            local_text=local_text,
            research_goal=_fact_field(
                payload,
                "research_goal",
                _decode_enum(ResearchGoal),
            ),
            causal_intent=_fact_field(
                payload,
                "causal_intent",
                _decode_enum(CausalIntent),
            ),
            role_hints=tuple(
                RoleHintBinding.from_mapping(
                    _require_mapping(item, "QuestionSpec role hint")
                )
                for item in raw_hints
            ),
        )


@dataclass(frozen=True)
class EstimandSpec:
    envelope: SchemaEnvelope
    template: Fact[EstimandTemplate]
    claim_basis: Fact[ClaimBasis]
    target_population: Fact[str]
    unit_of_analysis: Fact[UnitKind]
    target_roles: tuple[TargetRoleBinding, ...]
    contrast: Fact[ContrastKind]
    time_scope: Fact[str]
    effect_scale: Fact[EffectScale]
    association_target: Fact[AssociationTarget]

    def __post_init__(self) -> None:
        _require_schema(self.envelope, "modori.estimand_spec")
        roles = [binding.role for binding in self.target_roles]
        if len(set(roles)) != len(roles):
            raise ContractError("EstimandSpec contains duplicate target role")
        template = self.template.value if self.template.state in _CURRENT_STATES else None
        association = (
            self.association_target.value
            if self.association_target.state in _CURRENT_STATES
            else None
        )
        if template is EstimandTemplate.ASSOCIATION:
            if association is AssociationTarget.NOT_APPLICABLE:
                raise ContractError(
                    "association estimand requires an active association_target"
                )
        elif association not in {None, AssociationTarget.NOT_APPLICABLE}:
            raise ContractError(
                "association_target must be not_applicable outside association estimands"
            )
        claim = (
            self.claim_basis.value
            if self.claim_basis.state in _CURRENT_STATES
            else None
        )
        if template is EstimandTemplate.CAUSAL_EFFECT and claim not in {
            None,
            ClaimBasis.CAUSAL,
        }:
            raise ContractError("causal_effect estimand requires causal claim_basis")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_mapping(),
            "template": self.template.to_mapping(),
            "claim_basis": self.claim_basis.to_mapping(),
            "target_population": self.target_population.to_mapping(),
            "unit_of_analysis": self.unit_of_analysis.to_mapping(),
            "target_roles": [binding.to_mapping() for binding in self.target_roles],
            "contrast": self.contrast.to_mapping(),
            "time_scope": self.time_scope.to_mapping(),
            "effect_scale": self.effect_scale.to_mapping(),
            "association_target": self.association_target.to_mapping(),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    def validate_variable_references(self, available: Set[str]) -> None:
        referenced: set[str] = set()
        for binding in self.target_roles:
            if binding.variable_ids.state in _CURRENT_STATES:
                referenced.update(binding.variable_ids.value or ())
            elif binding.variable_ids.state is FactState.CONFLICT:
                for alternative in binding.variable_ids.alternatives:
                    referenced.update(alternative)
        unknown = sorted(referenced - set(available))
        if unknown:
            raise ContractError(f"unknown variable reference(s): {', '.join(unknown)}")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> EstimandSpec:
        payload = _require_mapping(payload, "EstimandSpec")
        allowed = frozenset(
            {
                "envelope",
                "template",
                "claim_basis",
                "target_population",
                "unit_of_analysis",
                "target_roles",
                "contrast",
                "time_scope",
                "effect_scale",
                "association_target",
            }
        )
        _require_exact_keys(payload, allowed, "EstimandSpec")
        raw_roles = payload["target_roles"]
        if not isinstance(raw_roles, list):
            raise ContractError("EstimandSpec target_roles must be a list")
        return cls(
            envelope=SchemaEnvelope.from_mapping(
                _require_mapping(payload["envelope"], "EstimandSpec envelope")
            ),
            template=_fact_field(
                payload,
                "template",
                _decode_enum(EstimandTemplate),
            ),
            claim_basis=_fact_field(
                payload,
                "claim_basis",
                _decode_enum(ClaimBasis),
            ),
            target_population=_fact_field(payload, "target_population", _decode_text),
            unit_of_analysis=_fact_field(
                payload,
                "unit_of_analysis",
                _decode_enum(UnitKind),
            ),
            target_roles=tuple(
                TargetRoleBinding.from_mapping(
                    _require_mapping(item, "EstimandSpec target role")
                )
                for item in raw_roles
            ),
            contrast=_fact_field(
                payload,
                "contrast",
                _decode_enum(ContrastKind),
            ),
            time_scope=_fact_field(payload, "time_scope", _decode_text),
            effect_scale=_fact_field(
                payload,
                "effect_scale",
                _decode_enum(EffectScale),
            ),
            association_target=_fact_field(
                payload,
                "association_target",
                _decode_enum(AssociationTarget),
            ),
        )


_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class StudySpec:
    envelope: SchemaEnvelope
    dataset_fingerprint: str
    source_schema_fingerprint: str
    unit_of_observation: Fact[UnitKind]
    unit_of_analysis: Fact[UnitKind]
    design_family: Fact[DesignFamily]
    data_layout: Fact[DataLayout]
    temporal_structure: Fact[TemporalStructure]
    dependence_structure: Fact[DependenceKind]
    assignment_mechanism: Fact[AssignmentMechanism]
    sampling_design: Fact[SamplingDesign]
    design_roles: tuple[StudyRoleBinding, ...]
    repeated_measure_order: Fact[tuple[str, ...]]
    missing_code_meanings: tuple[MissingCodeMeaning, ...]

    def __post_init__(self) -> None:
        _require_schema(self.envelope, "modori.study_spec")
        for field_name, fingerprint in (
            ("dataset_fingerprint", self.dataset_fingerprint),
            ("source_schema_fingerprint", self.source_schema_fingerprint),
        ):
            if not _FINGERPRINT_RE.fullmatch(fingerprint):
                raise ContractError(
                    f"{field_name} must be a lowercase 64-character SHA-256 digest"
                )
        roles = [binding.role for binding in self.design_roles]
        if len(set(roles)) != len(roles):
            raise ContractError("StudySpec contains duplicate design role")
        missing_keys = [
            (meaning.variable_id, meaning.code)
            for meaning in self.missing_code_meanings
        ]
        if len(set(missing_keys)) != len(missing_keys):
            raise ContractError("StudySpec contains duplicate missing-code meaning")
        dependence = (
            self.dependence_structure.value
            if self.dependence_structure.state in _CURRENT_STATES
            else None
        )
        pair_binding = next(
            (binding for binding in self.design_roles if binding.role is StudyRole.PAIR_ID),
            None,
        )
        if (
            dependence is DependenceKind.INDEPENDENT
            and pair_binding is not None
            and pair_binding.variable_ids.state in _CURRENT_STATES
            and pair_binding.variable_ids.value
        ):
            raise ContractError("independent study cannot bind pair_id variables")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "envelope": self.envelope.to_mapping(),
            "dataset_fingerprint": self.dataset_fingerprint,
            "source_schema_fingerprint": self.source_schema_fingerprint,
            "unit_of_observation": self.unit_of_observation.to_mapping(),
            "unit_of_analysis": self.unit_of_analysis.to_mapping(),
            "design_family": self.design_family.to_mapping(),
            "data_layout": self.data_layout.to_mapping(),
            "temporal_structure": self.temporal_structure.to_mapping(),
            "dependence_structure": self.dependence_structure.to_mapping(),
            "assignment_mechanism": self.assignment_mechanism.to_mapping(),
            "sampling_design": self.sampling_design.to_mapping(),
            "design_roles": [binding.to_mapping() for binding in self.design_roles],
            "repeated_measure_order": self.repeated_measure_order.to_mapping(),
            "missing_code_meanings": [
                meaning.to_mapping() for meaning in self.missing_code_meanings
            ],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_mapping())

    def validate_variable_references(self, available: Set[str]) -> None:
        referenced: set[str] = set()
        for binding in self.design_roles:
            if binding.variable_ids.state in _CURRENT_STATES:
                referenced.update(binding.variable_ids.value or ())
            elif binding.variable_ids.state is FactState.CONFLICT:
                for alternative in binding.variable_ids.alternatives:
                    referenced.update(alternative)
        if self.repeated_measure_order.state in _CURRENT_STATES:
            referenced.update(self.repeated_measure_order.value or ())
        referenced.update(
            meaning.variable_id for meaning in self.missing_code_meanings
        )
        unknown = sorted(referenced - set(available))
        if unknown:
            raise ContractError(f"unknown variable reference(s): {', '.join(unknown)}")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> StudySpec:
        payload = _require_mapping(payload, "StudySpec")
        allowed = frozenset(
            {
                "envelope",
                "dataset_fingerprint",
                "source_schema_fingerprint",
                "unit_of_observation",
                "unit_of_analysis",
                "design_family",
                "data_layout",
                "temporal_structure",
                "dependence_structure",
                "assignment_mechanism",
                "sampling_design",
                "design_roles",
                "repeated_measure_order",
                "missing_code_meanings",
            }
        )
        _require_exact_keys(payload, allowed, "StudySpec")
        raw_roles = payload["design_roles"]
        raw_missing = payload["missing_code_meanings"]
        if not isinstance(raw_roles, list):
            raise ContractError("StudySpec design_roles must be a list")
        if not isinstance(raw_missing, list):
            raise ContractError("StudySpec missing_code_meanings must be a list")
        return cls(
            envelope=SchemaEnvelope.from_mapping(
                _require_mapping(payload["envelope"], "StudySpec envelope")
            ),
            dataset_fingerprint=_decode_text(payload["dataset_fingerprint"]),
            source_schema_fingerprint=_decode_text(
                payload["source_schema_fingerprint"]
            ),
            unit_of_observation=_fact_field(
                payload,
                "unit_of_observation",
                _decode_enum(UnitKind),
            ),
            unit_of_analysis=_fact_field(
                payload,
                "unit_of_analysis",
                _decode_enum(UnitKind),
            ),
            design_family=_fact_field(
                payload,
                "design_family",
                _decode_enum(DesignFamily),
            ),
            data_layout=_fact_field(
                payload,
                "data_layout",
                _decode_enum(DataLayout),
            ),
            temporal_structure=_fact_field(
                payload,
                "temporal_structure",
                _decode_enum(TemporalStructure),
            ),
            dependence_structure=_fact_field(
                payload,
                "dependence_structure",
                _decode_enum(DependenceKind),
            ),
            assignment_mechanism=_fact_field(
                payload,
                "assignment_mechanism",
                _decode_enum(AssignmentMechanism),
            ),
            sampling_design=_fact_field(
                payload,
                "sampling_design",
                _decode_enum(SamplingDesign),
            ),
            design_roles=tuple(
                StudyRoleBinding.from_mapping(
                    _require_mapping(item, "StudySpec design role")
                )
                for item in raw_roles
            ),
            repeated_measure_order=_fact_field(
                payload,
                "repeated_measure_order",
                _decode_string_tuple,
            ),
            missing_code_meanings=tuple(
                MissingCodeMeaning.from_mapping(
                    _require_mapping(item, "StudySpec missing code")
                )
                for item in raw_missing
            ),
        )
