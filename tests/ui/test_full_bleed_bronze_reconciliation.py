import re
from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")
THEME_PATH = QML_ROOT / "theme/Theme.qml"


def qml_text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def theme_literal_colors() -> dict[str, str]:
    source = THEME_PATH.read_text(encoding="utf-8")
    return {
        name: value.upper()
        for name, value in re.findall(
            r'readonly property color (\w+): "(#[0-9A-Fa-f]{6})"',
            source,
        )
    }


def test_shared_darker_neutral_is_thirty_percent_farther_from_canvas() -> None:
    colors = theme_literal_colors()

    assert colors["canvasCream"] == "#FEFDFC"
    assert colors["surfaceRaised"] == "#FAF8F5"
    assert colors["surfaceQuiet"] == "#FAF8F5"
    assert colors["gridColumnHeaderSurface"] == "#FAF8F5"
    assert colors["gridRowHeaderSurface"] == "#FAF8F5"


def test_theme_uses_bronze_for_interaction_and_removes_teal_roles() -> None:
    colors = theme_literal_colors()

    for role in (
        "bronzeDeep",
        "bronzeHover",
        "bronzeAction",
        "bronzeFocus",
        "bronzeWash",
        "glassListSurface",
        "glassListHoverSurface",
        "footerGlassTop",
        "footerGlassMiddle",
        "footerGlassBottom",
    ):
        assert role in colors

    for role in ("deepTeal", "brandTeal", "actionTeal", "aqua"):
        assert role not in colors


def test_non_theme_qml_has_no_legacy_teal_role_references() -> None:
    forbidden = ("theme.deepTeal", "theme.brandTeal", "theme.actionTeal", "theme.aqua")

    offenders = {}
    for path in sorted(QML_ROOT.rglob("*.qml")):
        if path == THEME_PATH:
            continue
        source = path.read_text(encoding="utf-8")
        matches = [role for role in forbidden if role in source]
        if matches:
            offenders[str(path.relative_to(QML_ROOT)).replace("\\", "/")] = matches

    assert offenders == {}


def test_aurora_blends_with_hue_preserving_fades_and_has_footer_treatment() -> None:
    surface = qml_text("components/AuroraGlassSurface.qml")

    assert 'property string surfaceTreatment: "brand"' in surface
    assert 'root.surfaceTreatment === "footer"' in surface
    assert "theme.auroraTiffanyTransparent" in surface
    assert "theme.auroraIceTransparent" in surface
    assert "theme.auroraLilacTransparent" in surface
    assert "theme.auroraRoseTransparent" in surface
    assert "theme.footerGlassTop" in surface
    assert "theme.footerGlassMiddle" in surface
    assert "theme.footerGlassBottom" in surface
    assert "theme.transparent" not in surface


def test_entry_screen_is_a_full_window_split_not_a_centered_card() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert 'objectName: "entryBrandPanel"' in entry
    assert 'objectName: "entryTaskPanel"' in entry
    assert "width: Math.round(parent.width * theme.entryBrandRatio)" in entry
    assert "color: theme.entryBrand" in entry
    assert "color: theme.entryCanvas" in entry
    assert "anchors.centerIn: parent" not in entry
    assert "anchors.horizontalCenter: parent.horizontalCenter" in entry
    assert "entryStartMaxWidth" not in entry
    assert "entryStartMaxHeight" not in entry
    assert "AuroraGlassSurface" not in entry


def test_alternate_candidates_are_distinct_glass_rows() -> None:
    guide = qml_text("components/GuideRail.qml")
    button = qml_text("components/AppButton.qml")
    candidate_section = guide[
        guide.index("Repeater {", guide.index('appBootstrap.text("guide.other_recommendations", appBootstrap.language)')) :
        guide.index('appBootstrap.text("guide.manual_selection", appBootstrap.language)')
    ]

    assert 'variant: "glass"' in candidate_section
    assert 'control.variant === "glass"' in button
    assert 'objectName: "glassRowSeparator"' in button
    assert "visible: control.glassVariant" in button
    assert (
        "anchors.margins: control.activeFocus ? theme.borderWidthFocus : theme.spaceNone"
        in button
    )
    assert "property bool selected: false" in button


def test_results_panel_uses_one_panel_plane() -> None:
    results = qml_text("components/ResultsPanel.qml")

    assert "fillColor: theme.surfaceCream" in results[:500]
    assert re.search(r'Item\s*\{\s*objectName: "resultsReportPreview"', results)
    assert not re.search(
        r'PearlSurface\s*\{\s*objectName: "resultsReportPreview"',
        results,
    )


def test_pipeline_is_a_full_width_neutral_aurora_footer() -> None:
    pipeline = qml_text("components/PipelineRail.qml")
    work = qml_text("screens/WorkScreen.qml")

    assert re.match(r"(?:import[^\n]*\n)+\n?AuroraGlassSurface\s*\{", pipeline)
    assert 'surfaceTreatment: "footer"' in pipeline
    assert "tiffanyBloomEnabled: false" in pipeline
    assert "radius: theme.spaceNone" in pipeline
    assert "id: mainWorkspace" in work
    assert "Layout.margins: theme.workOuterMargin" in work
    assert work.index("id: mainWorkspace") < work.index("PipelineRail {")
