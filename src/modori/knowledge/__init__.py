"""Deterministic offline research-methods knowledge library."""

from functools import lru_cache

from modori.knowledge.loader import Library, load_library
from modori.knowledge.models import (
    EntryKind,
    LibraryEntry,
    LibraryLoadError,
    Reference,
    VerificationStatus,
)
from modori.knowledge.registry import ENGINE_VOCABULARY, HELP_KEYS, USER_FACING_EXCLUDED_KEYS, normalize_help_key
from modori.knowledge.validators import (
    ValidationIssue,
    ValidationReport,
    validate_citation_honesty,
    validate_coverage,
    validate_link_integrity,
    validate_slug_integrity,
)


@lru_cache(maxsize=1)
def _default_library() -> Library:
    return load_library()


def resolve_help_key(entity_key: str) -> str | None:
    return _default_library().resolve_help_key(entity_key)


__all__ = [
    "ENGINE_VOCABULARY",
    "HELP_KEYS",
    "USER_FACING_EXCLUDED_KEYS",
    "EntryKind",
    "Library",
    "LibraryEntry",
    "LibraryLoadError",
    "Reference",
    "ValidationIssue",
    "ValidationReport",
    "VerificationStatus",
    "load_library",
    "normalize_help_key",
    "resolve_help_key",
    "validate_citation_honesty",
    "validate_coverage",
    "validate_link_integrity",
    "validate_slug_integrity",
]
