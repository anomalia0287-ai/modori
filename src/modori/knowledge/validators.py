from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from modori.knowledge.loader import Library
from modori.knowledge.models import LibraryEntry, VerificationStatus
from modori.knowledge.registry import normalize_help_key


_KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    slug: str | None = None
    field: str | None = None
    value: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    name: str
    issues: tuple[ValidationIssue, ...] = ()
    needs_review: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_slug_integrity(entries: Iterable[LibraryEntry]) -> ValidationReport:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for entry in entries:
        if not _KEBAB_CASE.fullmatch(entry.slug):
            issues.append(
                ValidationIssue(
                    code="invalid_slug",
                    message=f"Slug is not kebab-case: {entry.slug}",
                    slug=entry.slug,
                )
            )
        if entry.slug in seen and entry.slug not in duplicates:
            duplicates.add(entry.slug)
            issues.append(
                ValidationIssue(
                    code="duplicate_slug",
                    message=f"Duplicate slug: {entry.slug}",
                    slug=entry.slug,
                )
            )
        seen.add(entry.slug)
    return ValidationReport(name="slug_integrity", issues=tuple(issues))


def validate_link_integrity(library: Library) -> ValidationReport:
    issues: list[ValidationIssue] = []
    slugs = library.all_slugs()
    for entry in library.entries():
        for field_name in ("assumptions", "alternatives", "related"):
            for linked_slug in getattr(entry, field_name):
                if linked_slug not in slugs:
                    issues.append(
                        ValidationIssue(
                            code="missing_entry_link",
                            message=f"{entry.slug}.{field_name} points to missing entry: {linked_slug}",
                            slug=entry.slug,
                            field=field_name,
                            value=linked_slug,
                        )
                    )
    for entity_key, target_slug in library.help_keys.items():
        if target_slug not in slugs:
            issues.append(
                ValidationIssue(
                    code="missing_help_key_target",
                    message=f"HELP_KEYS[{entity_key!r}] points to missing entry: {target_slug}",
                    field="HELP_KEYS",
                    value=target_slug,
                )
            )
    return ValidationReport(name="link_integrity", issues=tuple(issues))


def validate_coverage(
    engine_vocabulary: Iterable[str],
    help_keys: Mapping[str, str],
    library: Library,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    slugs = library.all_slugs()
    for entity_key in sorted(set(engine_vocabulary)):
        normalized_key = normalize_help_key(entity_key)
        target_slug = help_keys.get(entity_key)
        if target_slug is None and normalized_key is not None:
            target_slug = help_keys.get(normalized_key)
        if target_slug is None:
            issues.append(
                ValidationIssue(
                    code="missing_vocabulary_key",
                    message=f"Engine vocabulary key has no HELP_KEYS mapping: {entity_key}",
                    field="HELP_KEYS",
                    value=entity_key,
                )
            )
            continue
        if target_slug not in slugs:
            issues.append(
                ValidationIssue(
                    code="missing_help_key_target",
                    message=f"Engine vocabulary key {entity_key} points to missing entry: {target_slug}",
                    field="HELP_KEYS",
                    value=target_slug,
                )
            )
    return ValidationReport(name="coverage", issues=tuple(issues))


def validate_citation_honesty(library: Library) -> ValidationReport:
    issues: list[ValidationIssue] = []
    needs_review: list[str] = []
    for entry in library.entries():
        if entry.verification_status is VerificationStatus.NEEDS_REVIEW:
            needs_review.append(entry.slug)
        if (
            entry.verification_status is VerificationStatus.VERIFIED
            and not any(reference.verified for reference in entry.references)
        ):
            issues.append(
                ValidationIssue(
                    code="verified_without_verified_reference",
                    message=f"Verified entry has no verified reference: {entry.slug}",
                    slug=entry.slug,
                    field="references",
                )
            )
    return ValidationReport(
        name="citation_honesty",
        issues=tuple(issues),
        needs_review=tuple(needs_review),
    )
