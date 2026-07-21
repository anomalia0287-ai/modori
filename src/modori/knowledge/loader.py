from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml

from modori.knowledge.models import LibraryEntry, LibraryLoadError, VerificationStatus
from modori.knowledge.registry import HELP_KEYS, normalize_help_key


def _default_entries_dir(module_file: str | Path) -> Path:
    module_path = Path(module_file).resolve()
    packaged_entries = module_path.parents[2] / "library" / "entries"
    if packaged_entries.is_dir():
        return packaged_entries
    return module_path.parents[3] / "library" / "entries"


DEFAULT_ENTRIES_DIR = _default_entries_dir(__file__)


class Library:
    def __init__(
        self,
        entries: list[LibraryEntry] | tuple[LibraryEntry, ...],
        *,
        help_keys: Mapping[str, str] | None = None,
    ) -> None:
        self._entries = tuple(entries)
        self._by_slug = {entry.slug: entry for entry in self._entries}
        self.help_keys = dict(help_keys or HELP_KEYS)

    def entries(self) -> tuple[LibraryEntry, ...]:
        return self._entries

    def get(self, slug: str) -> LibraryEntry:
        try:
            return self._by_slug[slug]
        except KeyError as exc:
            raise KeyError(f"Unknown library entry: {slug}") from exc

    def explain(self, slug: str, language: str) -> dict[str, object]:
        entry = self.get(slug)
        lang = _language_base(language)
        suffix = "_ko" if lang == "ko" else "_en"
        return {
            "slug": entry.slug,
            "kind": entry.kind.value,
            "verification_status": entry.verification_status.value,
            "title": getattr(entry, f"title{suffix}"),
            "summary": getattr(entry, f"summary{suffix}"),
            "interpretation": getattr(entry, f"interpretation{suffix}"),
            "when_to_use": getattr(entry, f"when_to_use{suffix}"),
            "how_to_report": getattr(entry, f"how_to_report{suffix}"),
            "pitfalls": getattr(entry, f"pitfalls{suffix}"),
            "assumptions": list(entry.assumptions),
            "alternatives": list(entry.alternatives),
            "related": list(entry.related),
            "references": [
                {
                    "citation": reference.citation,
                    "locator": reference.locator,
                    "verified": reference.verified,
                }
                for reference in entry.references
            ],
        }

    def resolve_help_key(self, entity_key: str) -> str | None:
        direct = self.help_keys.get(entity_key)
        if direct is not None:
            return direct
        normalized = normalize_help_key(entity_key)
        if normalized is None:
            return None
        return self.help_keys.get(normalized)

    def all_slugs(self) -> set[str]:
        return set(self._by_slug)

    def needs_review(self) -> list[LibraryEntry]:
        return [
            entry
            for entry in self._entries
            if entry.verification_status is VerificationStatus.NEEDS_REVIEW
        ]


def load_library(
    entries_dir: str | Path | None = None,
    *,
    help_keys: Mapping[str, str] | None = None,
) -> Library:
    root = Path(entries_dir) if entries_dir is not None else DEFAULT_ENTRIES_DIR
    if not root.exists() or not root.is_dir():
        raise LibraryLoadError(f"Library entries directory does not exist: {root}")

    entries: list[LibraryEntry] = []
    for path in sorted(root.glob("*.yaml")):
        payload = _load_yaml_mapping(path)
        entry = LibraryEntry.from_mapping(payload, source=str(path))
        if path.stem != entry.slug:
            raise LibraryLoadError(f"Entry slug must match file name at {path}: {entry.slug}")
        entries.append(entry)
    return Library(entries, help_keys=help_keys)


def _language_base(language: str) -> str:
    base = language.lower().split("-")[0]
    if base not in {"ko", "en"}:
        raise ValueError("Library language must be one of: ko, ko-KR, en, en-US")
    return base


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LibraryLoadError(f"YAML parse error at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LibraryLoadError(f"Library entry YAML must parse to an object: {path}")
    return payload
