def test_ui_help_keys_resolve_against_seed_library() -> None:
    from modori.knowledge import load_library, resolve_help_key
    from modori.ui.help_keys import UI_HELP_KEYS

    library = load_library()

    for ui_key, entity_key in UI_HELP_KEYS.items():
        slug = resolve_help_key(entity_key)
        assert slug is not None, ui_key
        assert library.get(slug).slug == slug


def test_non_explainable_chrome_is_explicit() -> None:
    from modori.ui.help_keys import NOT_EXPLAINABLE_UI_LABELS

    assert "파일" in NOT_EXPLAINABLE_UI_LABELS
    assert "보고서" in NOT_EXPLAINABLE_UI_LABELS
    assert "다시 실행" in NOT_EXPLAINABLE_UI_LABELS


def test_controller_explain_uses_local_library() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    result = controller.explain("ui.result.cronbach_alpha", "ko")

    assert result.ok is True
    assert result.slug == "cronbach-alpha"
    assert "Cronbach" in result.title
    assert result.content


def test_controller_explain_reports_missing_library_key() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    result = controller.explain("ui.missing", "ko")

    assert result.ok is False
    assert result.error_code == "library_missing"
    assert result.content == {}
