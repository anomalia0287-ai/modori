from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QImage


QML_ROOT = Path("src/modori/ui/qml")
THEME_PATH = QML_ROOT / "theme/Theme.qml"


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def theme_literal_colors() -> dict[str, str]:
    return {
        name: value.upper()
        for name, value in re.findall(
            r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"',
            THEME_PATH.read_text(encoding="utf-8"),
        )
    }


def test_entry_palette_and_split_are_exact_theme_roles() -> None:
    colors = theme_literal_colors()
    theme = THEME_PATH.read_text(encoding="utf-8")
    entry = qml_text("screens/EntryScreen.qml")

    assert colors["entryBrand"] == "#173B7A"
    assert colors["entryCanvas"] == "#F7F3EA"
    assert colors["entryCard"] == "#FFFDF8"
    assert colors["entryPrimary"] == "#2F5DA8"
    assert colors["entryText"] == "#17233A"
    assert "readonly property real entryBrandRatio: 0.37" in theme
    assert "width: Math.round(parent.width * theme.entryBrandRatio)" in entry
    assert "color: theme.entryBrand" in entry
    assert "color: theme.entryCanvas" in entry


def test_entry_reuses_all_existing_actions_and_routes_without_new_navigation() -> None:
    entry = qml_text("screens/EntryScreen.qml")
    main = qml_text("Main.qml")

    for signal in (
        "signal guidedRequested()",
        "signal standardRequested()",
        "signal openDataRequested()",
        "signal recentFileRequested(int index)",
        "signal settingsRequested()",
    ):
        assert signal in entry

    assert entry.count("root.guidedRequested()") == 1
    assert entry.count("root.standardRequested()") == 1
    assert entry.count("root.openDataRequested()") == 1
    assert entry.count("root.recentFileRequested(index)") == 1
    assert entry.count("root.settingsRequested()") == 1
    assert "onGuidedRequested:" in main
    assert "onStandardRequested:" in main
    assert "onOpenDataRequested:" in main
    assert "onRecentFileRequested:" in main
    assert "onSettingsRequested:" in main


def test_entry_structure_matches_reference_without_fabricated_recent_metadata() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert 'appBootstrap.text("entry.heading", appBootstrap.language)' in entry
    assert entry.count("EntryModeCard {") == 2
    assert entry.count("LanguageChoiceButton {") == 2
    assert 'appBootstrap.text("entry.guided_badge", appBootstrap.language)' not in entry
    assert 'appBootstrap.text("entry.guided_description", appBootstrap.language)' in entry
    assert "model: uiController.recentFilesModel" in entry
    assert "required property string display" in entry
    assert "text: recentFileDelegate.display" in entry
    assert "implicitHeight: Math.min(count, 3) * theme.entryRecentRowHeight" in entry
    assert "recentFilesText.split" not in entry
    for invented_token in (
        "rowCount",
        "columnCount",
        "lastOpened",
        "timestamp",
        "오늘",
        "어제",
    ):
        assert invented_token not in entry


def test_mode_card_uses_border_background_marker_and_accessible_checked_state() -> None:
    card = qml_text("components/EntryModeCard.qml")

    assert "Accessible.role: Accessible.RadioButton" in card
    assert "Accessible.checked: control.selected" in card
    assert "theme.entryCardSelected" in card
    assert "theme.entryPrimary" in card
    assert "theme.borderWidthFocus" in card
    assert 'Qt.resolvedUrl("../assets/icons/check.svg")' in card
    assert "visible: control.selected" in card
    assert "activeFocus" in card
    assert "wrapMode: Text.WordWrap" in card
    assert "elide: Text.ElideRight" not in card
    assert "Math.max(theme.entryModeCardHeight" in card


def test_language_choice_is_keyboard_focusable_and_semantically_checked() -> None:
    choice = qml_text("components/LanguageChoiceButton.qml")

    assert "focusPolicy: Qt.TabFocus" in choice
    assert "Accessible.role: Accessible.RadioButton" in choice
    assert "Accessible.checked: control.selected" in choice
    assert "theme.entryPrimary" in choice
    assert "activeFocus" in choice


def test_native_capture_harness_emits_all_required_1366_by_768_states(tmp_path) -> None:
    output = tmp_path / "entry-captures"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/capture_entry_states.py",
            "--output",
            str(output),
        ],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for state in (
        "ko-casual",
        "ko-pro",
        "en-casual",
        "en-pro",
        "ko-focus",
        "en-focus",
    ):
        image = QImage(str(output / f"{state}.png"))
        assert not image.isNull(), state
        assert (image.width(), image.height()) == (1366, 768)
    assert not (output / "ui-settings.json").exists()
