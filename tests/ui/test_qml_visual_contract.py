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
