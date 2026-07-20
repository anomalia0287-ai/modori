import re
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")


def qml_sources() -> list[Path]:
    return sorted(path for path in QML_ROOT.rglob("*.qml") if path.name != "Theme.qml")


def test_non_theme_qml_does_not_define_literal_colors() -> None:
    color_literal = re.compile(r"#[0-9A-Fa-f]{3,8}")
    offenders = {
        str(path.relative_to(QML_ROOT)): sorted(set(color_literal.findall(path.read_text(encoding="utf-8"))))
        for path in qml_sources()
        if color_literal.search(path.read_text(encoding="utf-8"))
    }

    assert offenders == {}


def test_visual_qml_surfaces_use_theme_object() -> None:
    themed_files = {
        "Main.qml",
        "components/AppButton.qml",
        "components/AppIconButton.qml",
        "components/AuroraGlassSurface.qml",
        "components/BrandWordmark.qml",
        "components/DataGridView.qml",
        "components/DataTable.qml",
        "components/ExplainPopover.qml",
        "components/GuideRail.qml",
        "components/LoadingOverlay.qml",
        "components/ModeSegment.qml",
        "components/PearlSurface.qml",
        "components/PipelineRail.qml",
        "components/PreferenceSwitch.qml",
        "components/ResultsPanel.qml",
        "components/ResearchCandidateCard.qml",
        "components/ResearchFlowPanel.qml",
        "components/ResearchQuestionCard.qml",
        "components/StateBadge.qml",
        "components/TransformPanel.qml",
        "components/VariableTable.qml",
        "dialogs/ImportDialog.qml",
        "dialogs/ReportExportDialog.qml",
        "dialogs/ResultDetailDialog.qml",
        "dialogs/SettingsDialog.qml",
        "screens/EntryScreen.qml",
        "screens/SplashScreen.qml",
        "screens/WorkScreen.qml",
    }

    for relative in themed_files:
        text = (QML_ROOT / relative).read_text(encoding="utf-8")
        assert "Theme {" in text
        assert "theme." in text


def test_theme_exposes_layout_and_typography_tokens() -> None:
    theme = (QML_ROOT / "theme/Theme.qml").read_text(encoding="utf-8")
    expected_tokens = {
        "spaceNone",
        "spaceGridRow",
        "spaceGridColumn",
        "fontHero",
        "fontSplashTitle",
        "fontSubtitle",
        "fontOverlay",
        "windowDefaultWidth",
        "windowDefaultHeight",
        "headerHeight",
        "pipelineHeight",
        "resultsPanelPreferredWidth",
        "guideRailPreferredWidth",
        "guideRailMinimumWidth",
        "guideRailMaximumWidth",
        "dialogViewportMargin",
        "importDialogMaxWidth",
        "importDialogMaxHeight",
        "popoverWidth",
        "popoverBodyHeight",
        "progressWidth",
        "tableCellWidth",
        "tableCellHeight",
        "gridHeaderHeight",
        "gridRowLabelWidth",
        "gridStatusHeight",
        "variableCellWidth",
        "variableCellHeight",
        "fieldWidthTiny",
        "fieldWidthSmall",
        "fieldWidthMedium",
        "badgeHeight",
        "tablePreviewHeight",
        "chartPreviewHeight",
        "radiusPill",
    }

    missing = {token for token in expected_tokens if f"readonly property int {token}" not in theme}

    assert missing == set()


def test_theme_exposes_effect_and_opacity_tokens() -> None:
    theme = (QML_ROOT / "theme/Theme.qml").read_text(encoding="utf-8")
    expected_int_tokens = {
        "screenTransitionDuration",
        "splashFastDelayMs",
        "splashDelayMs",
    }
    expected_real_tokens = {
        "brandLetterSpacing",
        "auroraTiffanyOpacity",
        "auroraChromaticOpacity",
        "auroraVeilOpacity",
        "auroraSheenOpacity",
        "auroraAnchorOpacity",
        "opacityHigh",
        "opacityPrivacy",
        "opacitySplashPrivacy",
        "opacitySoft",
        "stateBorderAlpha",
        "resultSummaryLineHeight",
    }

    missing_int = {token for token in expected_int_tokens if f"readonly property int {token}" not in theme}
    missing_real = {token for token in expected_real_tokens if f"readonly property real {token}" not in theme}

    assert missing_int == set()
    assert missing_real == set()


def test_non_theme_qml_does_not_define_visual_metric_literals() -> None:
    metric_literal = re.compile(
        r"(?m)^\s*(?:"
        r"(?:rowSpacing|columnSpacing|spacing|padding|radius|width|height):\s*\d+"
        r"|anchors\.(?:margins|leftMargin|rightMargin|topMargin|bottomMargin):\s*\d+"
        r"|Layout\.(?:preferredWidth|preferredHeight|minimumWidth|maximumWidth|leftMargin|rightMargin|topMargin|bottomMargin):\s*\d+"
        r"|font\.pixelSize:\s*\d+"
        r"|implicitWidth:\s*\d+"
        r"|implicitHeight:\s*\d+"
        r")"
    )
    viewport_magic = re.compile(r"parent\.(?:width|height)\s*-\s*\d+|Math\.min\([^\n]*\d{2,}")
    offenders = {}
    for path in qml_sources():
        text = path.read_text(encoding="utf-8")
        matches = metric_literal.findall(text) + viewport_magic.findall(text)
        if matches:
            offenders[str(path.relative_to(QML_ROOT))] = matches

    assert offenders == {}


def test_non_theme_qml_does_not_define_visual_effect_literals() -> None:
    visual_effect_literal = re.compile(
        r"(?m)^\s*(?:"
        r"interval:\s*\d+"
        r"|opacity:\s*\d+\.\d+"
        r"|lineHeight:\s*\d+\.\d+"
        r"|border\.color:\s*Qt\.rgba\([^\n]*,\s*\d+\.\d+\)"
        r")"
    )
    offenders = {}
    for path in qml_sources():
        text = path.read_text(encoding="utf-8")
        matches = visual_effect_literal.findall(text)
        if matches:
            offenders[str(path.relative_to(QML_ROOT))] = matches

    assert offenders == {}


def test_passive_surfaces_are_borderless_and_selected_surfaces_use_one_edge() -> None:
    surface = (QML_ROOT / "components/PearlSurface.qml").read_text(encoding="utf-8")

    assert "property bool outlined: false" in surface
    assert "property color outlineColor: theme.lineSubtle" in surface
    assert "border.width: root.outlined ? theme.borderWidth : theme.spaceNone" in surface
    assert 'objectName: "selectedSurfaceIndicator"' in surface
    assert "anchors.bottom: parent.bottom" in surface
    assert "color: theme.workspacePrimary" in surface
    assert "visible: root.selected" in surface


def test_work_tabs_use_bottom_emphasis_without_persistent_frames() -> None:
    work = (QML_ROOT / "screens/WorkScreen.qml").read_text(encoding="utf-8")

    for tab_id in ("dataTab", "variableTab", "transformTab"):
        assert f"border.color: {tab_id}.activeFocus" not in work
    assert work.count("focusPolicy: Qt.TabFocus") == 3
    assert work.count("color: theme.workspacePrimary") >= 3
    assert work.count("anchors.bottom: parent.bottom") >= 3


def test_loading_and_screen_changes_use_truthful_reduced_motion_feedback() -> None:
    main = (QML_ROOT / "Main.qml").read_text(encoding="utf-8")
    overlay = (QML_ROOT / "components/LoadingOverlay.qml").read_text(encoding="utf-8")
    work = (QML_ROOT / "screens/WorkScreen.qml").read_text(encoding="utf-8")

    assert "property bool transientLoading: false" in main
    assert "function runWithLoading(callback)" in main
    assert "Qt.callLater" in main
    assert main.count("Behavior on opacity") == 3
    assert "theme.screenTransitionDuration" in main
    assert "root.reduceEffects ? theme.spaceNone" in main
    assert "BusyIndicator" in overlay
    assert "property bool reduceEffects: false" in overlay
    assert "visible: !root.reduceEffects" in overlay
    assert "reduceEffects: root.reduceEffects" in work[work.index("LoadingOverlay {"):]


def test_research_flow_actions_keep_accessible_names_and_keyboard_focus_contracts() -> (
    None
):
    panel = (QML_ROOT / "components/ResearchFlowPanel.qml").read_text(encoding="utf-8")
    question = (QML_ROOT / "components/ResearchQuestionCard.qml").read_text(
        encoding="utf-8"
    )
    candidate = (QML_ROOT / "components/ResearchCandidateCard.qml").read_text(
        encoding="utf-8"
    )
    button = (QML_ROOT / "components/AppButton.qml").read_text(encoding="utf-8")

    for source in (panel, question, candidate):
        assert "AppButton" in source
        assert "Accessible.name" in source
    assert "control.activeFocus" in button
    assert "theme.focusRing" in button
    assert 'control.variant === "primary" ? theme.onBrand : theme.focusRing' in button
    assert "control.enabled" in button
    assert "hoverEnabled: true" in button


def test_research_failure_recovery_surface_is_wrapped_and_accessible() -> None:
    panel = (QML_ROOT / "components/ResearchFlowPanel.qml").read_text(
        encoding="utf-8"
    )

    assert 'objectName: "researchFailureRecovery"' in panel
    assert 'root.flowState === "failure"' in panel
    assert 'root.flowState === "memory_unavailable"' in panel
    assert 'root.flowState === "corruption"' in panel
    assert 'root.flowState === "replan_required"' in panel
    failure_surface = panel[panel.index('objectName: "researchFailureRecovery"') :]
    assert "Accessible.name" in failure_surface
    assert "Accessible.Grouping" in failure_surface
    assert "Text.Wrap" in failure_surface
