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
