from __future__ import annotations

import re
from pathlib import Path


QML = Path("src/modori/ui/qml")


def _colors() -> dict[str, str]:
    source = (QML / "theme/Theme.qml").read_text(encoding="utf-8")
    return dict(
        re.findall(
            r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"',
            source,
        )
    )


def test_workspace_uses_approved_entry_palette_and_preserves_semantic_colors() -> None:
    colors = _colors()

    assert colors["entryBrand"] == "#173B7A"
    assert colors["entryCanvas"] == "#F7F3EA"
    assert colors["entryCard"] == "#FFFDF8"
    assert colors["entryPrimary"] == "#2F5DA8"
    assert colors["entryText"] == "#17233A"
    assert colors["warning"] == "#865F1B"
    assert colors["warningSurface"] == "#F5E8C8"
    assert colors["danger"] == "#A33D4B"
    assert colors["dangerSurface"] == "#F5E2E3"

    theme = (QML / "theme/Theme.qml").read_text(encoding="utf-8")
    for declaration in (
        "readonly property color workspaceBrand: entryBrand",
        "readonly property color workspaceCanvas: entryCanvas",
        "readonly property color workspaceCard: entryCard",
        "readonly property color workspacePrimary: entryPrimary",
        "readonly property color workspaceText: entryText",
        "readonly property color workspaceFocus: workspacePrimary",
        "readonly property color workspaceOnPrimary: workspaceCard",
    ):
        assert declaration in theme


def test_shared_controls_use_workspace_interaction_roles() -> None:
    button = (QML / "components/AppButton.qml").read_text(encoding="utf-8")
    checkbox = (QML / "components/AppCheckBox.qml").read_text(encoding="utf-8")
    radio = (QML / "components/AppRadioButton.qml").read_text(encoding="utf-8")
    switch = (QML / "components/PreferenceSwitch.qml").read_text(encoding="utf-8")
    field = (QML / "components/AppTextField.qml").read_text(encoding="utf-8")
    spin = (QML / "components/AppSpinBox.qml").read_text(encoding="utf-8")

    assert "theme.workspacePrimary" in button
    assert "theme.workspacePrimaryHover" in button
    assert "theme.workspacePrimaryPressed" in button
    assert "theme.workspacePrimary" in checkbox
    assert "theme.workspacePrimary" in radio
    assert "theme.workspacePrimary" in switch
    assert "theme.workspacePrimary" in field
    assert "theme.workspacePrimary" in spin
    assert "theme.bronzeAction" not in "\n".join(
        (button, checkbox, radio, switch, field, spin)
    )


def test_selected_surfaces_and_current_grid_cell_use_workspace_primary() -> None:
    pearl = (QML / "components/PearlSurface.qml").read_text(encoding="utf-8")
    grid = (QML / "components/DataGridView.qml").read_text(encoding="utf-8")
    badge = (QML / "components/StateBadge.qml").read_text(encoding="utf-8")

    assert "color: theme.workspacePrimary" in pearl
    assert "isCurrentCell ? theme.workspacePrimary : theme.lineGrid" in grid
    assert "theme.workspacePrimary" in badge


def test_work_screen_preserves_three_columns_and_uses_ivory_blue_roles() -> None:
    work = (QML / "screens/WorkScreen.qml").read_text(encoding="utf-8")

    assert work.index("GuideRail {") < work.index("id: centerWorkspace")
    assert work.index("id: centerWorkspace") < work.index("ResultsPanel {")
    assert "AuroraGlassSurface {" not in work
    assert "fillColor: theme.workspaceCanvas" in work
    assert "fillColor: theme.workspaceCard" in work
    assert "theme.workspaceSelected" in work
    assert "theme.workspacePrimary" in work
    for signal in (
        "signal openDataRequested()",
        "signal reportRequested()",
        "signal dataSheetRequested()",
        "signal settingsRequested()",
    ):
        assert signal in work


def test_guide_width_and_english_candidate_copy_fit_acceptance_viewport() -> None:
    work = (QML / "screens/WorkScreen.qml").read_text(encoding="utf-8")
    theme = (QML / "theme/Theme.qml").read_text(encoding="utf-8")

    assert 'appBootstrap.language === "en"' in work
    assert "theme.guideRailEnglishPreferredWidth" in work
    assert "theme.guideRailPreferredWidth" in work
    assert "readonly property int guideRailEnglishPreferredWidth: 300" in theme

    from modori.ui.strings_en import UI_STRINGS_EN

    assert (
        UI_STRINGS_EN["guide.other_recommendations"]
        == "Other experimental candidates"
    )


def test_work_tabs_and_mode_segment_use_non_color_selection_cues() -> None:
    work = (QML / "screens/WorkScreen.qml").read_text(encoding="utf-8")
    mode = (QML / "components/ModeChoiceButton.qml").read_text(encoding="utf-8")

    for object_name in ("workDataTab", "workVariableTab", "workTransformTab"):
        assert f'objectName: "{object_name}"' in work
    assert work.count("color: theme.workspacePrimary") >= 3
    assert work.count("height: theme.borderWidthFocus") >= 3
    assert "control.selected ? theme.workspaceSelected" in mode
    assert "color: theme.workspacePrimary" in mode
    assert "Accessible.checked: control.selected" in mode


def test_pipeline_and_results_remove_pastel_work_treatments() -> None:
    pipeline = (QML / "components/PipelineRail.qml").read_text(encoding="utf-8")
    results = (QML / "components/ResultsPanel.qml").read_text(encoding="utf-8")

    assert re.search(r"(?:import[^\n]*\n)+\n?PearlSurface\s*\{", pipeline)
    assert "AuroraGlassSurface" not in pipeline
    assert 'objectName: "workspacePipelineTopDivider"' in pipeline
    assert "color: theme.workspacePrimary" in pipeline
    assert 'variant: "primary"' in pipeline
    assert "fillColor: theme.workspaceCard" in results[:300]
    assert "theme.workspaceBrand" in results


def test_native_workspace_capture_produces_six_logical_1366_by_768_states(
    tmp_path: Path,
) -> None:
    from PIL import Image

    from scripts.capture_work_states import main

    output = tmp_path / "work-captures"
    assert main(["--output", str(output)]) == 0

    for state in (
        "ko-casual",
        "ko-pro",
        "en-casual",
        "en-pro",
        "ko-focus",
        "en-focus",
    ):
        with Image.open(output / f"{state}.png") as captured:
            assert captured.size == (1366, 768)
