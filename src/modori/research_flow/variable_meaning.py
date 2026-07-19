"""Immutable, dataset-bound review of P1 variable meanings and roles."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Literal
import unicodedata

from modori.core import Dataset, Variable
from modori.research_os import P1RoleBindings, P1TaskProfile


_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
_CLOSED_ROLE_RE = re.compile(r"[a-z][a-z0-9_]*\Z")
_SCHEMA_ID = "modori.variable_meaning_review"
_SCHEMA_VERSION = 1


class VariableMeaningReviewError(ValueError):
    """Raised when a meaning review cannot be sealed exactly."""


def _nfc_text(
    value: object,
    field_name: str,
    *,
    blank: bool = False,
) -> str:
    if not isinstance(value, str):
        raise VariableMeaningReviewError(f"{field_name} must be a string")
    if not blank and not value:
        raise VariableMeaningReviewError(f"{field_name} must not be empty")
    if value != unicodedata.normalize("NFC", value):
        raise VariableMeaningReviewError(f"{field_name} must use NFC Unicode")
    return value


def _number_text(value: object, field_name: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise VariableMeaningReviewError(f"{field_name} must be numeric") from exc
    if number == 0.0:
        number = 0.0
    return format(number, ".17g")


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class VariableMeaningRow:
    role: str
    variable_id: str
    label: str | None
    measure: str
    value_labels: tuple[tuple[str, str], ...]
    missing_codes: tuple[str, ...]
    storage_dtype: str
    evidence_source: Literal["current_dataset_metadata"]
    concept_definition_status: Literal["not_recorded"]
    unit_status: Literal["not_recorded"]

    def __post_init__(self) -> None:
        role = _nfc_text(self.role, "role")
        if _CLOSED_ROLE_RE.fullmatch(role) is None:
            raise VariableMeaningReviewError("role must be a closed identifier")
        _nfc_text(self.variable_id, "variable_id")
        if self.label is not None:
            _nfc_text(self.label, "label", blank=True)
        if self.measure not in {"nominal", "ordinal", "scale"}:
            raise VariableMeaningReviewError("measure is not closed")
        if not isinstance(self.value_labels, tuple):
            raise VariableMeaningReviewError("value_labels must be a tuple")
        for value, label in self.value_labels:
            _nfc_text(value, "value label value")
            _nfc_text(label, "value label")
        if len({value for value, _label in self.value_labels}) != len(
            self.value_labels
        ):
            raise VariableMeaningReviewError("value label values cannot repeat")
        if not isinstance(self.missing_codes, tuple):
            raise VariableMeaningReviewError("missing_codes must be a tuple")
        for code in self.missing_codes:
            _nfc_text(code, "missing code")
        if len(set(self.missing_codes)) != len(self.missing_codes):
            raise VariableMeaningReviewError("missing codes cannot repeat")
        _nfc_text(self.storage_dtype, "storage_dtype")
        if self.evidence_source != "current_dataset_metadata":
            raise VariableMeaningReviewError("evidence source is not closed")
        if self.concept_definition_status != "not_recorded":
            raise VariableMeaningReviewError("concept definition status is not closed")
        if self.unit_status != "not_recorded":
            raise VariableMeaningReviewError("unit status is not closed")

    def to_mapping(self) -> dict[str, object]:
        return {
            "role": self.role,
            "variable_id": self.variable_id,
            "label": self.label,
            "measure": self.measure,
            "value_labels": [list(item) for item in self.value_labels],
            "missing_codes": list(self.missing_codes),
            "storage_dtype": self.storage_dtype,
            "evidence_source": self.evidence_source,
            "concept_definition_status": self.concept_definition_status,
            "unit_status": self.unit_status,
        }


@dataclass(frozen=True)
class VariableMeaningReview:
    dataset_fingerprint: str
    pipeline_version: int
    profile_id: str
    rows: tuple[VariableMeaningRow, ...]
    review_digest: str
    schema_id: str = field(default=_SCHEMA_ID, init=False)
    schema_version: int = field(default=_SCHEMA_VERSION, init=False)

    def __post_init__(self) -> None:
        if _DIGEST_RE.fullmatch(self.dataset_fingerprint) is None:
            raise VariableMeaningReviewError("dataset fingerprint is malformed")
        if type(self.pipeline_version) is not int or self.pipeline_version < 0:
            raise VariableMeaningReviewError(
                "pipeline_version must be a nonnegative integer"
            )
        try:
            P1TaskProfile(self.profile_id)
        except ValueError as exc:
            raise VariableMeaningReviewError("profile_id is outside P1") from exc
        if not isinstance(self.rows, tuple) or not self.rows:
            raise VariableMeaningReviewError("review requires at least one row")
        if any(not isinstance(row, VariableMeaningRow) for row in self.rows):
            raise VariableMeaningReviewError(
                "rows must contain VariableMeaningRow values"
            )
        for row in self.rows:
            row.__post_init__()
        identities = tuple((row.role, row.variable_id) for row in self.rows)
        if len(set(identities)) != len(identities):
            raise VariableMeaningReviewError("review rows cannot repeat")
        variable_ids = tuple(row.variable_id for row in self.rows)
        if len(set(variable_ids)) != len(variable_ids):
            raise VariableMeaningReviewError(
                "one variable cannot occupy multiple reviewed roles"
            )
        if _DIGEST_RE.fullmatch(self.review_digest) is None:
            raise VariableMeaningReviewError("review_digest is malformed")
        if self.review_digest != self.compute_digest(
            dataset_fingerprint=self.dataset_fingerprint,
            pipeline_version=self.pipeline_version,
            profile_id=self.profile_id,
            rows=self.rows,
        ):
            raise VariableMeaningReviewError(
                "review_digest does not bind the complete review"
            )

    @property
    def provenance_ref(self) -> str:
        return f"variable-meaning-review:v1:{self.review_digest}"

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "dataset_fingerprint": self.dataset_fingerprint,
            "pipeline_version": self.pipeline_version,
            "profile_id": self.profile_id,
            "rows": [row.to_mapping() for row in self.rows],
        }

    @classmethod
    def compute_digest(
        cls,
        *,
        dataset_fingerprint: str,
        pipeline_version: int,
        profile_id: str,
        rows: tuple[VariableMeaningRow, ...],
    ) -> str:
        return _canonical_digest(
            {
                "schema_id": _SCHEMA_ID,
                "schema_version": _SCHEMA_VERSION,
                "dataset_fingerprint": dataset_fingerprint,
                "pipeline_version": pipeline_version,
                "profile_id": profile_id,
                "rows": [row.to_mapping() for row in rows],
            }
        )

    @classmethod
    def create(
        cls,
        *,
        dataset_fingerprint: str,
        pipeline_version: int,
        profile_id: str,
        rows: tuple[VariableMeaningRow, ...],
    ) -> VariableMeaningReview:
        return cls(
            dataset_fingerprint=dataset_fingerprint,
            pipeline_version=pipeline_version,
            profile_id=profile_id,
            rows=rows,
            review_digest=cls.compute_digest(
                dataset_fingerprint=dataset_fingerprint,
                pipeline_version=pipeline_version,
                profile_id=profile_id,
                rows=rows,
            ),
        )


def _role_pairs(
    profile: P1TaskProfile,
    roles: P1RoleBindings,
) -> tuple[tuple[str, str], ...]:
    if profile in {
        P1TaskProfile.NUMERIC_DISTRIBUTION,
        P1TaskProfile.CATEGORY_FREQUENCY,
    }:
        valid = (
            bool(roles.outcome)
            and not roles.group
            and not roles.focal_predictor
            and not roles.repeated_measure_order
        )
        pairs = tuple(("outcome", value) for value in roles.outcome)
    elif profile is P1TaskProfile.INDEPENDENT_TWO_GROUP_MEAN:
        valid = (
            len(roles.outcome) == 1
            and len(roles.group) == 1
            and not roles.focal_predictor
            and not roles.repeated_measure_order
        )
        pairs = (
            ("outcome", roles.outcome[0]) if roles.outcome else ("outcome", ""),
            ("group", roles.group[0]) if roles.group else ("group", ""),
        )
    elif profile is P1TaskProfile.PAIRED_TWO_TIME_MEAN_CHANGE:
        valid = (
            not roles.outcome
            and not roles.group
            and not roles.focal_predictor
            and len(roles.repeated_measure_order) == 2
        )
        pairs = (
            (
                "before",
                roles.repeated_measure_order[0] if roles.repeated_measure_order else "",
            ),
            (
                "after",
                roles.repeated_measure_order[1]
                if len(roles.repeated_measure_order) > 1
                else "",
            ),
        )
    else:
        valid = (
            len(roles.outcome) == 1
            and not roles.group
            and len(roles.focal_predictor) == 1
            and not roles.repeated_measure_order
        )
        pairs = (
            ("outcome", roles.outcome[0]) if roles.outcome else ("outcome", ""),
            (
                "focal_predictor",
                roles.focal_predictor[0] if roles.focal_predictor else "",
            ),
        )
    if not valid:
        raise VariableMeaningReviewError(
            f"{profile.value} roles do not match the closed P1 shape"
        )
    variable_ids = tuple(variable_id for _role, variable_id in pairs)
    if len(set(variable_ids)) != len(variable_ids):
        raise VariableMeaningReviewError(
            "one variable cannot occupy multiple reviewed roles"
        )
    return pairs


def _meaning_row(role: str, variable_id: str, variable: Variable) -> VariableMeaningRow:
    label = variable.label
    if label is not None:
        label = _nfc_text(label, "variable label", blank=True)
    value_labels = tuple(
        sorted(
            (
                (
                    _number_text(value, "value label value"),
                    _nfc_text(text, "value label"),
                )
                for value, text in variable.value_labels.items()
            ),
            key=lambda item: item[0],
        )
    )
    missing_codes = tuple(
        sorted(
            (_number_text(value, "missing code") for value in variable.missing_values),
            key=str,
        )
    )
    return VariableMeaningRow(
        role=role,
        variable_id=variable_id,
        label=label,
        measure=variable.measure.value,
        value_labels=value_labels,
        missing_codes=missing_codes,
        storage_dtype=_nfc_text(variable.dtype, "storage dtype"),
        evidence_source="current_dataset_metadata",
        concept_definition_status="not_recorded",
        unit_status="not_recorded",
    )


def build_variable_meaning_review(
    dataset: Dataset,
    *,
    dataset_fingerprint: str,
    pipeline_version: int,
    profile: P1TaskProfile,
    roles: P1RoleBindings,
) -> VariableMeaningReview:
    """Seal exactly the metadata and P1 roles a user must review before commit."""

    if not isinstance(dataset, Dataset):
        raise VariableMeaningReviewError("dataset must be a Dataset")
    if not isinstance(profile, P1TaskProfile):
        raise VariableMeaningReviewError("profile must be a P1TaskProfile")
    if not isinstance(roles, P1RoleBindings):
        raise VariableMeaningReviewError("roles must be P1RoleBindings")
    if _DIGEST_RE.fullmatch(dataset_fingerprint) is None:
        raise VariableMeaningReviewError("dataset fingerprint is malformed")
    if type(pipeline_version) is not int or pipeline_version < 0:
        raise VariableMeaningReviewError(
            "pipeline_version must be a nonnegative integer"
        )
    pairs = _role_pairs(profile, roles)
    rows: list[VariableMeaningRow] = []
    for role, variable_id in pairs:
        try:
            variable = dataset.variables[variable_id]
        except KeyError as exc:
            raise VariableMeaningReviewError(
                f"review variable is not in the current dataset: {variable_id}"
            ) from exc
        rows.append(_meaning_row(role, variable_id, variable))
    return VariableMeaningReview.create(
        dataset_fingerprint=dataset_fingerprint,
        pipeline_version=pipeline_version,
        profile_id=profile.value,
        rows=tuple(rows),
    )
