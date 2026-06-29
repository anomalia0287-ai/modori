from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LibraryLoadError(ValueError):
    """Raised when curated library content violates the strict schema."""


class EntryKind(Enum):
    METHOD = "method"
    CONCEPT = "concept"
    ASSUMPTION = "assumption"
    STATISTIC = "statistic"
    DIAGNOSTIC = "diagnostic"
    EFFECT_SIZE = "effect_size"


class VerificationStatus(Enum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class Reference:
    citation: str
    locator: str | None
    verified: bool

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], *, source: str) -> Reference:
        allowed = {"citation", "locator", "verified"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise LibraryLoadError(f"Unknown field(s) in reference at {source}: {unknown}")
        missing = sorted(allowed - set(payload))
        if missing:
            raise LibraryLoadError(f"Missing required reference field(s) at {source}: {missing}")
        citation = payload["citation"]
        locator = payload["locator"]
        verified = payload["verified"]
        if not isinstance(citation, str) or not citation.strip():
            raise LibraryLoadError(f"Reference citation must be a non-empty string at {source}")
        if locator is not None and not isinstance(locator, str):
            raise LibraryLoadError(f"Reference locator must be a string or null at {source}")
        if not isinstance(verified, bool):
            raise LibraryLoadError(f"Reference verified must be true/false at {source}")
        return cls(citation=citation, locator=locator, verified=verified)


@dataclass(frozen=True)
class LibraryEntry:
    slug: str
    kind: EntryKind
    title_ko: str
    title_en: str
    summary_ko: str
    summary_en: str
    interpretation_ko: str | None = None
    interpretation_en: str | None = None
    when_to_use_ko: str | None = None
    when_to_use_en: str | None = None
    how_to_report_ko: str | None = None
    how_to_report_en: str | None = None
    pitfalls_ko: str | None = None
    pitfalls_en: str | None = None
    assumptions: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.NEEDS_REVIEW

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], *, source: str) -> LibraryEntry:
        allowed = {
            "slug",
            "kind",
            "title_ko",
            "title_en",
            "summary_ko",
            "summary_en",
            "interpretation_ko",
            "interpretation_en",
            "when_to_use_ko",
            "when_to_use_en",
            "how_to_report_ko",
            "how_to_report_en",
            "pitfalls_ko",
            "pitfalls_en",
            "assumptions",
            "alternatives",
            "related",
            "references",
            "verification_status",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise LibraryLoadError(f"Unknown field(s) in entry at {source}: {unknown}")

        required = {"slug", "kind", "title_ko", "title_en", "summary_ko", "summary_en"}
        missing = sorted(required - set(payload))
        if missing:
            raise LibraryLoadError(f"Missing required entry field(s) at {source}: {missing}")

        try:
            kind = EntryKind(str(payload["kind"]))
        except ValueError as exc:
            raise LibraryLoadError(f"Invalid entry kind at {source}: {payload['kind']}") from exc

        status_value = payload.get("verification_status", VerificationStatus.NEEDS_REVIEW.value)
        try:
            verification_status = VerificationStatus(str(status_value))
        except ValueError as exc:
            raise LibraryLoadError(f"Invalid verification_status at {source}: {status_value}") from exc

        text_fields = {
            "slug",
            "title_ko",
            "title_en",
            "summary_ko",
            "summary_en",
        }
        for field_name in text_fields:
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise LibraryLoadError(f"{field_name} must be a non-empty string at {source}")

        optional_text_fields = {
            "interpretation_ko",
            "interpretation_en",
            "when_to_use_ko",
            "when_to_use_en",
            "how_to_report_ko",
            "how_to_report_en",
            "pitfalls_ko",
            "pitfalls_en",
        }
        for field_name in optional_text_fields:
            value = payload.get(field_name)
            if value is not None and not isinstance(value, str):
                raise LibraryLoadError(f"{field_name} must be a string or null at {source}")

        if kind in {EntryKind.METHOD, EntryKind.DIAGNOSTIC}:
            _require_non_empty_optional(payload, "when_to_use_ko", source)
            _require_non_empty_optional(payload, "when_to_use_en", source)
        if kind in {EntryKind.CONCEPT, EntryKind.STATISTIC, EntryKind.EFFECT_SIZE}:
            _require_non_empty_optional(payload, "interpretation_ko", source)
            _require_non_empty_optional(payload, "interpretation_en", source)

        assumptions = _read_slug_list(payload.get("assumptions", []), "assumptions", source)
        alternatives = _read_slug_list(payload.get("alternatives", []), "alternatives", source)
        related = _read_slug_list(payload.get("related", []), "related", source)
        references = _read_references(payload.get("references", []), source)

        return cls(
            slug=payload["slug"],
            kind=kind,
            title_ko=payload["title_ko"],
            title_en=payload["title_en"],
            summary_ko=payload["summary_ko"],
            summary_en=payload["summary_en"],
            interpretation_ko=payload.get("interpretation_ko"),
            interpretation_en=payload.get("interpretation_en"),
            when_to_use_ko=payload.get("when_to_use_ko"),
            when_to_use_en=payload.get("when_to_use_en"),
            how_to_report_ko=payload.get("how_to_report_ko"),
            how_to_report_en=payload.get("how_to_report_en"),
            pitfalls_ko=payload.get("pitfalls_ko"),
            pitfalls_en=payload.get("pitfalls_en"),
            assumptions=assumptions,
            alternatives=alternatives,
            related=related,
            references=references,
            verification_status=verification_status,
        )


def _require_non_empty_optional(payload: dict[str, Any], field_name: str, source: str) -> None:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise LibraryLoadError(f"{field_name} is required for this entry kind at {source}")


def _read_slug_list(value: Any, field_name: str, source: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise LibraryLoadError(f"{field_name} must be a list of non-empty strings at {source}")
    return list(value)


def _read_references(value: Any, source: str) -> list[Reference]:
    if not isinstance(value, list):
        raise LibraryLoadError(f"references must be a list at {source}")
    references: list[Reference] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise LibraryLoadError(f"references[{index}] must be an object at {source}")
        references.append(Reference.from_mapping(item, source=f"{source}:references[{index}]"))
    return references
