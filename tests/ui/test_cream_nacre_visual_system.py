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
        "pearlMint",
        "pearlRose",
        "pearlLilac",
        "focusRing",
        "semanticGlow",
        "textStrong",
        "textBody",
        "textMuted",
        "warning",
        "danger",
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


def test_entry_uses_one_ambient_pearl_surface_and_structured_actions() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert "PearlSurface" in entry
    assert 'objectName: "entryStartSurface"' in entry
    assert 'appBootstrap.text("entry.promise")' in entry
    assert "AppButton" in entry
    assert "model.display" in entry
    assert "gradient: Gradient" not in entry


def test_recent_file_rows_are_width_bounded_and_middle_elided() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert "contentWidth: availableWidth" in entry
    assert "width: recentFilesScroll.availableWidth" in entry
    assert "textElide: Text.ElideMiddle" in entry
