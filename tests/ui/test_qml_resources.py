from pathlib import Path


def test_root_qml_resource_resolves_from_package() -> None:
    from modori.ui.resources import root_qml_path

    root = root_qml_path()

    assert root.name == "Main.qml"
    assert root.is_file()
    assert "src" in root.parts
    assert root.parts[-4:] == ("modori", "ui", "qml", "Main.qml")


def test_app_launcher_uses_qml_not_legacy_widgets() -> None:
    source = Path("src/modori/app.py").read_text(encoding="utf-8")

    assert "QGuiApplication" in source
    assert "QQmlApplicationEngine" in source
    assert "QMainWindow" not in source
    assert "QWidget" not in source
    assert "QApplication" not in source


def test_settings_icon_and_license_resolve_from_package_source() -> None:
    qml_root = Path("src/modori/ui/qml")

    assert (qml_root / "assets/icons/settings.svg").is_file()
    assert (qml_root / "assets/icons/LUCIDE-LICENSE.txt").is_file()


def test_parisienne_font_and_license_are_packaged() -> None:
    qml_root = Path("src/modori/ui/qml")
    font = qml_root / "assets/fonts/Parisienne-Regular.ttf"
    license_file = qml_root / "assets/fonts/OFL.txt"
    package = Path("pyproject.toml").read_text(encoding="utf-8")

    assert font.is_file()
    assert font.read_bytes()[:4] == b"\x00\x01\x00\x00"
    assert license_file.is_file()
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_file.read_text(encoding="utf-8")
    assert '"qml/assets/fonts/*.ttf"' in package
    assert '"qml/assets/fonts/*.txt"' in package


def test_research_os_qml_components_resolve_from_package_source() -> None:
    component_root = Path("src/modori/ui/qml/components")

    for name in (
        "ResearchFlowPanel.qml",
        "ResearchQuestionCard.qml",
        "ResearchCandidateCard.qml",
    ):
        assert (component_root / name).is_file()
