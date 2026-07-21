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


def test_theme_uses_approved_royal_blue_ivory_and_supported_aurora_values() -> None:
    colors = theme_literal_colors()
    source = THEME_PATH.read_text(encoding="utf-8")

    assert colors["entryBrand"] == "#173B7A"
    assert colors["entryCanvas"] == "#F7F3EA"
    assert colors["entryCard"] == "#FFFDF8"
    assert colors["entryPrimary"] == "#2F5DA8"
    assert colors["entryText"] == "#17233A"
    assert "readonly property color canvasCream: workspaceCanvas" in source
    assert "readonly property color surfaceCream: workspaceCard" in source
    assert "readonly property color brandWordmark: workspaceBrand" in source
    assert colors["auroraGlassTop"] == "#AACFD3"
    assert colors["auroraGlassMiddle"] == "#D5E1E1"
    assert colors["auroraGlassBottom"] == "#E8D7DC"
    assert colors["auroraNeutralTop"] == "#BCC9CA"
    assert colors["auroraNeutralMiddle"] == "#D5DCDC"
    assert colors["auroraNeutralBottom"] == "#E1DDDC"
    assert colors["auroraTiffanyBloom"] == "#69CEC6"
    assert colors["auroraIceBloom"] == "#B8DDE8"
    assert colors["auroraLilacBloom"] == "#CFC4E2"
    assert colors["auroraRoseBloom"] == "#E1BEC5"
    assert colors["auroraGlassVeil"] == "#FFFFFF"
    assert "headerTiffany" not in colors
    assert "readonly property color lineStrong: workspaceDividerStrong" in source
    assert "readonly property color lineSubtle: workspaceDivider" in source
    assert "readonly property color lineGrid: workspaceDivider" in source
    assert "readonly property color scrollRailSurface: workspaceDivider" in source
    assert "readonly property color scrollThumbSurface: workspaceTextMuted" in source
    assert "readonly property color scrollThumbActiveSurface: workspacePrimary" in source


def test_pure_white_is_not_used_as_an_application_or_scroll_surface() -> None:
    colors = theme_literal_colors()
    pure_white_roles = {name for name, value in colors.items() if value == "#FFFFFF"}

    assert pure_white_roles == {"auroraGlassVeil"}


def test_wordmark_is_black_uppercase_gothic_and_letter_spaced() -> None:
    wordmark = qml_text("components/BrandWordmark.qml")

    assert "FontLoader" not in wordmark
    assert "Parisienne" not in wordmark
    assert "font.family: theme.brandFontFamily" in wordmark
    assert "font.capitalization: Font.AllUppercase" in wordmark
    assert "font.letterSpacing: theme.brandLetterSpacing" in wordmark
    assert "font.weight: Font.DemiBold" in wordmark
    assert "property color foregroundColor: theme.brandWordmark" in wordmark
    assert "color: root.foregroundColor" in wordmark
    assert "Accessible.name: text" in wordmark
    assert "Theme {" in wordmark


def test_entry_work_and_splash_reuse_brand_wordmark() -> None:
    for relative in (
        "screens/EntryScreen.qml",
        "screens/WorkScreen.qml",
        "screens/SplashScreen.qml",
    ):
        source = qml_text(relative)
        assert "BrandWordmark {" in source
        assert 'appBootstrap.text("app.title", appBootstrap.language)' in source


def test_work_header_and_entry_use_the_approved_royal_blue_ivory_system() -> None:
    work = qml_text("screens/WorkScreen.qml")
    entry = qml_text("screens/EntryScreen.qml")
    results = qml_text("components/ResultsPanel.qml")
    pipeline = qml_text("components/PipelineRail.qml")

    assert "AuroraGlassSurface {" not in work
    assert 'objectName: "workspaceCommandSurface"' in work
    assert "reduceEffects: root.reduceEffects" in work
    assert "fillColor: theme.workspaceCard" in work
    assert "foregroundColor: theme.workspaceBrand" in work
    assert 'objectName: "workspaceCommandDivider"' in work
    assert "Layout.rightMargin: theme.workWordmarkCommandGap" in work
    assert 'objectName: "entryBrandPanel"' in entry
    assert "anchors.fill: parent" in entry
    assert "anchors.centerIn: parent" not in entry
    assert "AuroraGlassSurface" not in entry
    assert "width: Math.round(parent.width * theme.entryBrandRatio)" in entry
    assert "color: theme.entryBrand" in entry
    assert "color: theme.entryCanvas" in entry
    assert 'objectName: "entryTaskPanel"' in entry
    assert "model: uiController.recentFilesModel" in entry
    assert "fillColor: theme.workspaceCard" in results
    assert 'objectName: "workspacePipelineTopDivider"' in pipeline
    assert "AuroraGlassSurface" not in pipeline


def test_shared_aurora_surface_is_static_and_tiffany_is_removable() -> None:
    surface = qml_text("components/AuroraGlassSurface.qml")

    assert "property bool reduceEffects: false" in surface
    assert "property bool tiffanyBloomEnabled: true" in surface
    assert "property bool bottomAnchorVisible: false" in surface
    assert "root.tiffanyBloomEnabled && !root.reduceEffects" in surface
    assert "theme.auroraTiffanyBloom" in surface
    assert "theme.auroraGlassVeil" in surface
    assert "visible: root.bottomAnchorVisible" in surface
    assert "NumberAnimation" not in surface
    assert "Behavior on" not in surface


def test_aurora_surface_is_used_only_in_approved_regions() -> None:
    users = []
    for path in sorted(QML_ROOT.rglob("*.qml")):
        if path.name == "AuroraGlassSurface.qml":
            continue
        if "AuroraGlassSurface {" in path.read_text(encoding="utf-8"):
            users.append(str(path.relative_to(QML_ROOT)).replace("\\", "/"))

    assert users == []


def test_scrollbar_uses_visible_fills_without_an_extra_outline() -> None:
    scrollbar = qml_text("components/AppScrollBar.qml")

    assert "color: theme.scrollRailSurface" in scrollbar
    assert "root.engaged ? theme.scrollThumbActiveSurface : theme.scrollThumbSurface" in scrollbar
    assert "border.color" not in scrollbar
    assert "color: theme.lineSubtle" not in scrollbar
    assert "theme.textMuted" not in scrollbar
    assert "theme.actionTeal" not in scrollbar
