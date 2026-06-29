from __future__ import annotations

from collections.abc import Callable

from modori.knowledge import Library, load_library
from modori.ui.contracts import ExplainResult
from modori.ui.help_keys import ui_entity_to_library_key


class ExplanationService:
    def __init__(self, library_factory: Callable[[], Library] | None = None) -> None:
        self._library_factory = library_factory or load_library
        self._library: Library | None = None

    def explain(self, entity_key: str, language: str) -> ExplainResult:
        library = self._get_library()
        library_key = ui_entity_to_library_key(entity_key)
        slug = library.resolve_help_key(library_key)
        if slug is None:
            return self._missing(slug=None)
        try:
            content = library.explain(slug, language)
        except KeyError:
            return self._missing(slug=slug)
        return ExplainResult(
            ok=True,
            slug=slug,
            title=str(content.get("title", "")),
            content=content,
        )

    def _get_library(self) -> Library:
        if self._library is None:
            self._library = self._library_factory()
        return self._library

    @staticmethod
    def _missing(slug: str | None) -> ExplainResult:
        return ExplainResult(
            ok=False,
            slug=slug,
            title="",
            content={},
            error_code="library_missing",
            message_ko="설명 항목을 찾을 수 없습니다.",
        )
