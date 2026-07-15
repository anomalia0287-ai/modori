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


def test_theme_uses_approved_ivory_tiffany_and_rose_bronze_values() -> None:
    colors = theme_literal_colors()

    assert colors["canvasCream"] == "#FEFDFC"
    assert colors["surfaceCream"] == "#FEFDFC"
    assert colors["surfaceRaised"] == "#FBF9F7"
    assert colors["surfaceQuiet"] == "#FBF9F7"
    assert colors["headerTiffany"] == "#81D8D0"
    assert colors["brandWordmark"] == "#B9856E"
    assert colors["lineStrong"] == "#B9856E"
    assert colors["lineSubtle"] == "#D7B9AA"
    assert colors["lineGrid"] == "#D7B9AA"
    assert colors["scrollRailSurface"] == "#FFFFFF"
    assert colors["scrollThumbSurface"] == "#FFFFFF"


def test_pure_white_surface_roles_are_scoped_to_scrollbars() -> None:
    colors = theme_literal_colors()
    pure_white_roles = {name for name, value in colors.items() if value == "#FFFFFF"}

    assert pure_white_roles == {
        "onBrand",
        "scrollRailSurface",
        "scrollThumbSurface",
    }


def test_wordmark_component_owns_font_loading_and_brand_color() -> None:
    wordmark = qml_text("components/BrandWordmark.qml")

    assert "FontLoader" in wordmark
    assert 'Qt.resolvedUrl("../assets/fonts/Parisienne-Regular.ttf")' in wordmark
    assert "font.family: parisienne.name" in wordmark
    assert "font.weight: Font.Normal" in wordmark
    assert "color: theme.brandWordmark" in wordmark
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
        assert 'appBootstrap.text("app.title")' in source


def test_work_header_and_entry_sheet_use_approved_surface_roles() -> None:
    work = qml_text("screens/WorkScreen.qml")
    entry = qml_text("screens/EntryScreen.qml")

    assert "fillColor: theme.headerTiffany" in work
    assert 'objectName: "entryStartSurface"' in entry
    assert "fillColor: theme.surfaceQuiet" in entry


def test_scrollbar_uses_white_surfaces_rose_bronze_edges_and_tiffany_active_state() -> None:
    scrollbar = qml_text("components/AppScrollBar.qml")

    assert "color: theme.scrollRailSurface" in scrollbar
    assert "border.color: theme.lineSubtle" in scrollbar
    assert "root.engaged ? theme.headerTiffany : theme.scrollThumbSurface" in scrollbar
    assert "border.color: theme.lineStrong" in scrollbar
    assert "theme.textMuted" not in scrollbar
    assert "theme.actionTeal" not in scrollbar
