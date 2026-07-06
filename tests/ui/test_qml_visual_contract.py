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
        "components/DataTable.qml",
        "components/ExplainPopover.qml",
        "components/GuideRail.qml",
        "components/LoadingOverlay.qml",
        "components/PipelineRail.qml",
        "components/ResultsPanel.qml",
        "components/TransformPanel.qml",
        "components/VariableTable.qml",
        "dialogs/ImportDialog.qml",
        "dialogs/ReportExportDialog.qml",
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
        "splashFastDelayMs",
        "splashDelayMs",
    }
    expected_real_tokens = {
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
