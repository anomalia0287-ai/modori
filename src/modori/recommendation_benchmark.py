from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from statistics import NormalDist, median
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
        if (
            self.action_class == "recommendation_eligible"
            and self.required_clarification_facts
        ):
            raise BenchmarkContractError(
                "recommendation-eligible gold must not include clarification facts"
            )
        if (
            self.action_class == "recommendation_eligible"
            and self.acceptable_abstention_reasons
        ):
            raise BenchmarkContractError(
                "recommendation-eligible gold must not include abstention reasons"
            )
        if self.action_class == "clarification_required" and self.acceptable_recommendations:
            raise BenchmarkContractError(
                "clarification-required gold must not include recommendations"
            )
        if (
            self.action_class == "clarification_required"
            and self.acceptable_abstention_reasons
        ):
            raise BenchmarkContractError(
                "clarification-required gold must not include abstention reasons"
            )
        if self.action_class == "abstention_required" and self.acceptable_recommendations:
            raise BenchmarkContractError(
                "abstention-required gold must not include recommendations"
            )
        if self.action_class == "abstention_required" and self.required_clarification_facts:
            raise BenchmarkContractError(
                "abstention-required gold must not include clarification facts"
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
            if self.primary_action.value != self.candidates[0]:
                raise BenchmarkContractError(
                    "recommended default must be the first candidate"
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


@dataclass(frozen=True)
class RateMetric:
    successes: int
    total: int
    rate: float | None
    status: str
    lower_bound: float | None = None


@dataclass(frozen=True)
class BenchmarkScore:
    scorer_fingerprint: str
    recommendation_top1: RateMetric
    top3_case_hit: RateMetric
    recommendation_coverage: RateMetric
    clarification_accuracy: RateMetric
    abstention_accuracy: RateMetric
    primary_action_accuracy: RateMetric
    strong_precision: RateMetric
    question_efficiency: RateMetric
    errors_by_severity: tuple[tuple[str, int], ...]


def wilson_lower_bound(
    successes: int,
    total: int,
    confidence_level: float,
) -> float | None:
    if not isinstance(successes, int) or not isinstance(total, int):
        raise BenchmarkContractError("successes and total must be integers")
    if total < 0 or successes < 0 or successes > total:
        raise BenchmarkContractError("successes must be between zero and total")
    if not 0.5 < confidence_level < 1.0:
        raise BenchmarkContractError("confidence level must be between 0.5 and 1")
    if total == 0:
        return None
    z = NormalDist().inv_cdf(confidence_level)
    proportion = successes / total
    denominator = 1.0 + (z * z / total)
    center = (proportion + z * z / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - half_width)


def _rate_metric(
    successes: int,
    total: int,
    confidence_level: float,
    *,
    zero_status: str = "insufficient_evidence",
) -> RateMetric:
    if total == 0:
        return RateMetric(
            successes=0,
            total=0,
            rate=None,
            status=zero_status,
            lower_bound=None,
        )
    return RateMetric(
        successes=successes,
        total=total,
        rate=successes / total,
        status="ok",
        lower_bound=wilson_lower_bound(successes, total, confidence_level),
    )


def _record_key(record: GoldRecord | PredictionRecord) -> tuple[str, str]:
    return record.case_id, record.evidence_stage


def _index_unique(
    records: Sequence[GoldRecord] | Sequence[PredictionRecord],
    record_name: str,
) -> dict[tuple[str, str], GoldRecord | PredictionRecord]:
    indexed: dict[tuple[str, str], GoldRecord | PredictionRecord] = {}
    for record in records:
        key = _record_key(record)
        if key in indexed:
            raise BenchmarkContractError(
                f"duplicate {record_name} case-stage: {key[0]} / {key[1]}"
            )
        indexed[key] = record
    return indexed


def _primary_action_correct(gold: GoldRecord, prediction: PredictionRecord) -> bool:
    action = prediction.primary_action
    if gold.action_class == "recommendation_eligible":
        return action.kind == "recommend" and action.value in gold.acceptable_recommendations
    if gold.action_class == "clarification_required":
        return action.kind == "clarify" and action.value in gold.required_clarification_facts
    return (
        action.kind == "abstain"
        and action.value in gold.acceptable_abstention_reasons
    )


def score_predictions(
    gold_records: Sequence[GoldRecord],
    predictions: Sequence[PredictionRecord],
    config: ScorerConfig,
) -> BenchmarkScore:
    if not gold_records:
        raise BenchmarkContractError("gold records must not be empty")
    gold_by_key = _index_unique(gold_records, "gold")
    prediction_by_key = _index_unique(predictions, "prediction")
    gold_keys = set(gold_by_key)
    prediction_keys = set(prediction_by_key)
    missing = sorted(gold_keys - prediction_keys)
    if missing:
        raise BenchmarkContractError(f"missing predictions: {missing}")
    unexpected = sorted(prediction_keys - gold_keys)
    if unexpected:
        raise BenchmarkContractError(f"unexpected predictions: {unexpected}")

    recommendation_total = 0
    recommendation_correct = 0
    top3_correct = 0
    recommendation_covered = 0
    clarification_total = 0
    clarification_correct = 0
    abstention_total = 0
    abstention_correct = 0
    primary_correct = 0
    strong_total = 0
    strong_correct = 0
    question_total = 0
    question_correct = 0
    errors = {severity: 0 for severity in ("E1", "E2", "E3", "E4", "E5")}

    for key in sorted(gold_by_key):
        raw_gold = gold_by_key[key]
        raw_prediction = prediction_by_key[key]
        if not isinstance(raw_gold, GoldRecord) or not isinstance(
            raw_prediction,
            PredictionRecord,
        ):
            raise AssertionError("benchmark index type mismatch")
        gold = raw_gold
        prediction = raw_prediction
        action_correct = _primary_action_correct(gold, prediction)
        primary_correct += int(action_correct)
        if not action_correct:
            errors[gold.failure_severity] += 1

        if gold.action_class == "recommendation_eligible":
            recommendation_total += 1
            recommendation_correct += int(action_correct)
            top3_correct += int(
                any(
                    candidate in gold.acceptable_recommendations
                    for candidate in prediction.candidates[:3]
                )
            )
            recommendation_covered += int(prediction.primary_action.kind == "recommend")
        elif gold.action_class == "clarification_required":
            clarification_total += 1
            clarification_correct += int(action_correct)
        else:
            abstention_total += 1
            abstention_correct += int(action_correct)

        if prediction.level == "strong":
            strong_total += 1
            strong_correct += int(
                gold.action_class == "recommendation_eligible" and action_correct
            )

        for question in prediction.questions:
            question_total += 1
            question_correct += int(question in gold.required_clarification_facts)

    confidence_level = config.confidence_level
    return BenchmarkScore(
        scorer_fingerprint=scorer_fingerprint(config),
        recommendation_top1=_rate_metric(
            recommendation_correct,
            recommendation_total,
            confidence_level,
        ),
        top3_case_hit=_rate_metric(
            top3_correct,
            recommendation_total,
            confidence_level,
        ),
        recommendation_coverage=_rate_metric(
            recommendation_covered,
            recommendation_total,
            confidence_level,
        ),
        clarification_accuracy=_rate_metric(
            clarification_correct,
            clarification_total,
            confidence_level,
        ),
        abstention_accuracy=_rate_metric(
            abstention_correct,
            abstention_total,
            confidence_level,
        ),
        primary_action_accuracy=_rate_metric(
            primary_correct,
            len(gold_by_key),
            confidence_level,
        ),
        strong_precision=_rate_metric(
            strong_correct,
            strong_total,
            confidence_level,
        ),
        question_efficiency=_rate_metric(
            question_correct,
            question_total,
            confidence_level,
            zero_status="not_applicable",
        ),
        errors_by_severity=tuple(errors.items()),
    )


def _wilson_interval(
    successes: int,
    total: int,
    confidence_level: float,
) -> tuple[float, float]:
    z = NormalDist().inv_cdf((1.0 + confidence_level) / 2.0)
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def newcombe_paired_difference_interval(
    baseline_correct: Sequence[bool],
    candidate_correct: Sequence[bool],
    confidence_level: float,
) -> tuple[float, float]:
    if len(baseline_correct) != len(candidate_correct):
        raise BenchmarkContractError("paired correctness inputs must have equal length")
    if not baseline_correct:
        raise BenchmarkContractError("paired correctness inputs require at least one case")
    if not 0.5 < confidence_level < 1.0:
        raise BenchmarkContractError("confidence level must be between 0.5 and 1")
    if any(type(value) is not bool for value in baseline_correct) or any(
        type(value) is not bool for value in candidate_correct
    ):
        raise BenchmarkContractError("paired correctness inputs must contain booleans")

    e = sum(
        candidate and baseline
        for baseline, candidate in zip(
            baseline_correct,
            candidate_correct,
            strict=True,
        )
    )
    f = sum(
        candidate and not baseline
        for baseline, candidate in zip(
            baseline_correct,
            candidate_correct,
            strict=True,
        )
    )
    g = sum(
        baseline and not candidate
        for baseline, candidate in zip(
            baseline_correct,
            candidate_correct,
            strict=True,
        )
    )
    n = len(baseline_correct)
    h = n - e - f - g
    candidate_rate = (e + f) / n
    baseline_rate = (e + g) / n
    candidate_low, candidate_high = _wilson_interval(
        e + f,
        n,
        confidence_level,
    )
    baseline_low, baseline_high = _wilson_interval(
        e + g,
        n,
        confidence_level,
    )

    phi_denominator = math.sqrt(
        (e + f) * (g + h) * (e + g) * (f + h)
    )
    raw_phi_numerator = e * h - f * g
    if phi_denominator == 0:
        phi = 0.0
    elif raw_phi_numerator > 0:
        phi = max(raw_phi_numerator - n / 2.0, 0.0) / phi_denominator
    else:
        phi = raw_phi_numerator / phi_denominator

    candidate_down = candidate_rate - candidate_low
    candidate_up = candidate_high - candidate_rate
    baseline_down = baseline_rate - baseline_low
    baseline_up = baseline_high - baseline_rate
    lower_distance = math.sqrt(
        max(
            0.0,
            candidate_down * candidate_down
            - 2.0 * phi * candidate_down * baseline_up
            + baseline_up * baseline_up,
        )
    )
    upper_distance = math.sqrt(
        max(
            0.0,
            candidate_up * candidate_up
            - 2.0 * phi * candidate_up * baseline_down
            + baseline_down * baseline_down,
        )
    )
    difference = candidate_rate - baseline_rate
    return (
        max(-1.0, difference - lower_distance),
        min(1.0, difference + upper_distance),
    )


@dataclass(frozen=True)
class ReviewerAnnotation:
    case_id: str
    evidence_stage: str
    action_class: ActionClass | str
    acceptable_recommendations: tuple[RecommendationIdentity, ...] = ()
    required_clarification_facts: tuple[str, ...] = ()
    acceptable_abstention_reasons: tuple[str, ...] = ()
    active_minutes: float = 0.0
    failure_severity: str = "E3"

    def __post_init__(self) -> None:
        validated = GoldRecord(
            case_id=self.case_id,
            evidence_stage=self.evidence_stage,
            action_class=self.action_class,
            acceptable_recommendations=self.acceptable_recommendations,
            required_clarification_facts=self.required_clarification_facts,
            acceptable_abstention_reasons=self.acceptable_abstention_reasons,
            failure_severity=self.failure_severity,
        )
        object.__setattr__(self, "case_id", validated.case_id)
        object.__setattr__(self, "evidence_stage", validated.evidence_stage)
        if not math.isfinite(self.active_minutes) or self.active_minutes <= 0.0:
            raise BenchmarkContractError(
                "reviewer active minutes must be finite and positive"
            )


@dataclass(frozen=True)
class ReviewerSubmission:
    reviewer_id: str
    annotations: tuple[ReviewerAnnotation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reviewer_id",
            _require_nonempty_string(self.reviewer_id, "reviewer ID"),
        )
        if not self.annotations:
            raise BenchmarkContractError("reviewer annotations must not be empty")
        keys = [_record_key(annotation) for annotation in self.annotations]
        if len(set(keys)) != len(keys):
            raise BenchmarkContractError("reviewer submission contains duplicate case-stages")


@dataclass(frozen=True)
class AdjudicationRecord:
    case_id: str
    evidence_stage: str
    resolution_minutes: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_nonempty_string(self.case_id, "case ID"))
        object.__setattr__(
            self,
            "evidence_stage",
            _require_nonempty_string(self.evidence_stage, "evidence stage"),
        )
        if not math.isfinite(self.resolution_minutes) or self.resolution_minutes < 0.0:
            raise BenchmarkContractError(
                "adjudication minutes must be finite and non-negative"
            )


@dataclass(frozen=True)
class AgreementReport:
    case_count: int
    primary_action_alpha: float | None
    primary_action_status: str
    recommendation_jaccard: float | None
    recommendation_exact: float | None
    clarification_jaccard: float | None
    clarification_exact: float | None


@dataclass(frozen=True)
class LabelingRates:
    reviewer_hourly: float
    adjudicator_hourly: float
    setup_cost: float = 0.0
    data_steward_cost: float = 0.0
    project_management_cost: float = 0.0

    def __post_init__(self) -> None:
        for name in ("reviewer_hourly", "adjudicator_hourly"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise BenchmarkContractError(f"{name} must be finite and positive")
        for name in ("setup_cost", "data_steward_cost", "project_management_cost"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise BenchmarkContractError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class CostProjection:
    pilot_case_count: int
    stage_case_count: int
    median_reviewer_minutes: float
    median_adjudication_minutes: float
    projected_reviewer_hours: float
    projected_adjudication_hours: float
    projected_expert_hours_with_contingency: float
    base_labor_cost: float
    contingency_cost: float
    fixed_cost: float
    total_cost: float


def _submission_index(
    submission: ReviewerSubmission,
) -> dict[tuple[str, str], ReviewerAnnotation]:
    return {_record_key(annotation): annotation for annotation in submission.annotations}


def _paired_submission_indices(
    reviewer_a: ReviewerSubmission,
    reviewer_b: ReviewerSubmission,
) -> tuple[
    dict[tuple[str, str], ReviewerAnnotation],
    dict[tuple[str, str], ReviewerAnnotation],
]:
    if reviewer_a.reviewer_id == reviewer_b.reviewer_id:
        raise BenchmarkContractError("submissions require different reviewer IDs")
    index_a = _submission_index(reviewer_a)
    index_b = _submission_index(reviewer_b)
    if set(index_a) != set(index_b):
        raise BenchmarkContractError("reviewer submissions must cover identical case-stages")
    return index_a, index_b


def _nominal_krippendorff_alpha(
    labels_a: Sequence[str],
    labels_b: Sequence[str],
) -> tuple[float | None, str]:
    case_count = len(labels_a)
    disagreements = sum(a != b for a, b in zip(labels_a, labels_b, strict=True))
    observed_disagreement = disagreements / case_count
    counts: dict[str, int] = {}
    for label in (*labels_a, *labels_b):
        counts[label] = counts.get(label, 0) + 1
    observation_count = 2 * case_count
    expected_disagreement = 1.0 - sum(
        count * (count - 1) for count in counts.values()
    ) / (observation_count * (observation_count - 1))
    if expected_disagreement == 0.0:
        return None, "not_estimable"
    return 1.0 - observed_disagreement / expected_disagreement, "ok"


def _set_agreement(
    sets_a: Sequence[frozenset[object]],
    sets_b: Sequence[frozenset[object]],
) -> tuple[float | None, float | None]:
    jaccard_values: list[float] = []
    exact_values: list[float] = []
    for first, second in zip(sets_a, sets_b, strict=True):
        union = first | second
        if not union:
            continue
        jaccard_values.append(len(first & second) / len(union))
        exact_values.append(float(first == second))
    if not jaccard_values:
        return None, None
    return sum(jaccard_values) / len(jaccard_values), sum(exact_values) / len(
        exact_values
    )


def reviewer_agreement(
    reviewer_a: ReviewerSubmission,
    reviewer_b: ReviewerSubmission,
) -> AgreementReport:
    index_a, index_b = _paired_submission_indices(reviewer_a, reviewer_b)
    keys = sorted(index_a)
    labels_a = [str(index_a[key].action_class) for key in keys]
    labels_b = [str(index_b[key].action_class) for key in keys]
    alpha, alpha_status = _nominal_krippendorff_alpha(labels_a, labels_b)
    recommendation_jaccard, recommendation_exact = _set_agreement(
        [frozenset(index_a[key].acceptable_recommendations) for key in keys],
        [frozenset(index_b[key].acceptable_recommendations) for key in keys],
    )
    clarification_jaccard, clarification_exact = _set_agreement(
        [frozenset(index_a[key].required_clarification_facts) for key in keys],
        [frozenset(index_b[key].required_clarification_facts) for key in keys],
    )
    return AgreementReport(
        case_count=len(keys),
        primary_action_alpha=alpha,
        primary_action_status=alpha_status,
        recommendation_jaccard=recommendation_jaccard,
        recommendation_exact=recommendation_exact,
        clarification_jaccard=clarification_jaccard,
        clarification_exact=clarification_exact,
    )


def project_labeling_cost(
    reviewers: Sequence[ReviewerSubmission],
    adjudications: Sequence[AdjudicationRecord],
    *,
    stage_case_count: int,
    rates: LabelingRates,
    contingency: float = 0.25,
) -> CostProjection:
    if len(reviewers) != 2:
        raise BenchmarkContractError("cost projection requires exactly two reviewers")
    reviewer_a, reviewer_b = reviewers
    index_a, index_b = _paired_submission_indices(reviewer_a, reviewer_b)
    if len(index_a) != 20:
        raise BenchmarkContractError("cost projection requires exactly 20 pilot cases")
    if not isinstance(stage_case_count, int) or stage_case_count <= 0:
        raise BenchmarkContractError("stage case count must be a positive integer")
    if not math.isfinite(contingency) or not 0.0 <= contingency <= 1.0:
        raise BenchmarkContractError("contingency must be between zero and one")

    adjudication_by_key: dict[tuple[str, str], AdjudicationRecord] = {}
    for record in adjudications:
        key = _record_key(record)
        if key in adjudication_by_key:
            raise BenchmarkContractError("duplicate adjudication case-stage")
        adjudication_by_key[key] = record
    if set(adjudication_by_key) != set(index_a) or set(index_a) != set(index_b):
        raise BenchmarkContractError(
            "adjudications must cover both complete reviewer submissions"
        )

    reviewer_minutes = [
        annotation.active_minutes
        for submission in reviewers
        for annotation in submission.annotations
    ]
    adjudication_minutes = [
        adjudication_by_key[key].resolution_minutes for key in sorted(adjudication_by_key)
    ]
    median_reviewer_minutes = float(median(reviewer_minutes))
    median_adjudication_minutes = float(median(adjudication_minutes))
    projected_reviewer_hours = (
        stage_case_count * 2.0 * median_reviewer_minutes / 60.0
    )
    projected_adjudication_hours = (
        stage_case_count * median_adjudication_minutes / 60.0
    )
    base_expert_hours = projected_reviewer_hours + projected_adjudication_hours
    base_labor_cost = (
        projected_reviewer_hours * rates.reviewer_hourly
        + projected_adjudication_hours * rates.adjudicator_hourly
    )
    contingency_cost = base_labor_cost * contingency
    fixed_cost = rates.setup_cost + rates.data_steward_cost + rates.project_management_cost
    return CostProjection(
        pilot_case_count=len(index_a),
        stage_case_count=stage_case_count,
        median_reviewer_minutes=median_reviewer_minutes,
        median_adjudication_minutes=median_adjudication_minutes,
        projected_reviewer_hours=projected_reviewer_hours,
        projected_adjudication_hours=projected_adjudication_hours,
        projected_expert_hours_with_contingency=base_expert_hours
        * (1.0 + contingency),
        base_labor_cost=base_labor_cost,
        contingency_cost=contingency_cost,
        fixed_cost=fixed_cost,
        total_cost=base_labor_cost + contingency_cost + fixed_cost,
    )
