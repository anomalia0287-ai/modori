from __future__ import annotations

from modori.knowledge import LibraryLoadError
from modori.ui.explanation_service import ExplanationService


class FakeLibrary:
    def __init__(self) -> None:
        self.resolved_keys: list[str] = []
        self.explained: list[tuple[str, str]] = []
        self.slugs: dict[str, str | None] = {"cronbach_alpha": "cronbach-alpha"}

    def resolve_help_key(self, key: str) -> str | None:
        self.resolved_keys.append(key)
        return self.slugs.get(key)

    def explain(self, slug: str, language: str) -> dict[str, object]:
        self.explained.append((slug, language))
        return {"title": "Cronbach alpha", "summary": "Internal consistency"}


def test_explanation_service_resolves_ui_entity_and_returns_content() -> None:
    library = FakeLibrary()

    result = ExplanationService(library_factory=lambda: library).explain(
        "ui.result.cronbach_alpha",
        "ko",
    )

    assert result.ok is True
    assert result.slug == "cronbach-alpha"
    assert result.title == "Cronbach alpha"
    assert result.content["summary"] == "Internal consistency"
    assert library.resolved_keys == ["cronbach_alpha"]
    assert library.explained == [("cronbach-alpha", "ko")]


def test_explanation_service_reports_missing_help_key() -> None:
    library = FakeLibrary()
    library.slugs = {}

    result = ExplanationService(library_factory=lambda: library).explain(
        "ui.result.cronbach_alpha",
        "ko",
    )

    assert result.ok is False
    assert result.error_code == "library_missing"
    assert result.message_ko == "설명 항목을 찾을 수 없습니다."


def test_explanation_service_reports_missing_entry_after_resolution() -> None:
    class MissingEntryLibrary(FakeLibrary):
        def explain(self, slug: str, language: str) -> dict[str, object]:
            raise KeyError(slug)

    result = ExplanationService(library_factory=MissingEntryLibrary).explain(
        "ui.result.cronbach_alpha",
        "ko",
    )

    assert result.ok is False
    assert result.slug == "cronbach-alpha"
    assert result.error_code == "library_missing"


def test_explanation_service_bounds_unavailable_library_failure() -> None:
    def unavailable_library():
        raise LibraryLoadError("private path must not reach product copy")

    result = ExplanationService(library_factory=unavailable_library).explain(
        "ui.result.cronbach_alpha",
        "ko",
    )

    assert result.ok is False
    assert result.slug is None
    assert result.error_code == "library_unavailable"
    assert result.message_ko == "설명 근거를 불러올 수 없습니다."
    assert "private path" not in result.message_ko
