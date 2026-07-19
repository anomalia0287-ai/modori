from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def test_theme_exposes_cream_nacre_semantic_tokens() -> None:
    theme = qml_text("theme/Theme.qml")
    expected_color_tokens = {
        "canvasCream",
        "surfaceCream",
        "surfaceRaised",
        "surfaceQuiet",
        "pearlIce",
        "pearlRose",
        "pearlLilac",
        "bronzeFocus",
        "bronzeAction",
        "bronzeHover",
        "focusRing",
        "semanticGlow",
        "textStrong",
        "textBody",
        "textMuted",
        "onBrand",
        "warning",
        "warningSurface",
        "danger",
        "dangerSurface",
    }
    expected_int_tokens = {
        "controlHeight",
        "iconButtonSize",
        "settingsDialogWidth",
        "resultDetailWidth",
        "commandSurfaceHeight",
        "pipelineCompactHeight",
    }

    for token in expected_color_tokens:
        assert f"readonly property color {token}" in theme
    for token in expected_int_tokens:
        assert f"readonly property int {token}" in theme


def test_theme_does_not_use_pure_white_or_black_for_primary_surfaces() -> None:
    theme = qml_text("theme/Theme.qml").upper()
    assert 'CANVASCREAM: "#FFFFFF"' not in theme
    assert 'SURFACECREAM: "#FFFFFF"' not in theme
    assert 'TEXTSTRONG: "#000000"' not in theme


def test_reusable_visual_components_are_real_qml_controls() -> None:
    expected = {
        "PearlSurface.qml": "Rectangle",
        "AppButton.qml": "Button",
        "AppIconButton.qml": "Button",
        "PreferenceSwitch.qml": "Switch",
        "ModeSegment.qml": "RowLayout",
        "StateBadge.qml": "Rectangle",
    }
    for filename, marker in expected.items():
        path = QML_ROOT / "components" / filename
        assert path.is_file()
        source = path.read_text(encoding="utf-8")
        assert marker in source
        assert "Theme {" in source
        assert "MouseArea" not in source


def test_entry_uses_full_bleed_royal_blue_surface_and_structured_actions() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert 'objectName: "entryBrandPanel"' in entry
    assert "color: theme.entryBrand" in entry
    assert "color: theme.entryCanvas" in entry
    assert 'appBootstrap.text("entry.promise", appBootstrap.language)' in entry
    assert entry.count("EntryModeCard {") == 2
    assert "model: uiController.recentFilesModel" in entry
    assert "gradient: Gradient" not in entry


def test_recent_file_rows_are_width_bounded_and_middle_elided() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert "width: ListView.view.width" in entry
    assert "elide: Text.ElideMiddle" in entry
    assert "clip: true" in entry
