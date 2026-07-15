from pathlib import Path


QML_ROOT = Path("src/modori/ui/qml")


def text(relative: str) -> str:
    return QML_ROOT.joinpath(relative).read_text(encoding="utf-8")


def test_settings_entry_is_functional_on_entry_and_work_screens() -> None:
    main = text("Main.qml")
    entry = text("screens/EntryScreen.qml")
    work = text("screens/WorkScreen.qml")

    assert "SettingsDialog" in main
    assert "onSettingsRequested: settingsDialog.open()" in main
    for source in (entry, work):
        assert "signal settingsRequested()" in source
        assert "AppIconButton" in source
        assert "root.settingsRequested()" in source
        assert 'appBootstrap.text("settings.title")' in source


def test_settings_sheet_owns_existing_persistent_preferences() -> None:
    dialog = text("dialogs/SettingsDialog.qml")

    assert dialog.count("PreferenceSwitch") == 3
    assert "uiController.explainModeEnabled" in dialog
    assert "uiController.setExplainModeEnabled" in dialog
    assert "uiController.reduceEffects" in dialog
    assert "uiController.setReduceEffects" in dialog
    assert "uiController.recentFilesEnabled" in dialog
    assert "uiController.setRecentFilesEnabled" in dialog


def test_settings_icon_and_license_are_packaged() -> None:
    icon = QML_ROOT / "assets/icons/settings.svg"
    license_file = QML_ROOT / "assets/icons/LUCIDE-LICENSE.txt"
    package = Path("pyproject.toml").read_text(encoding="utf-8")

    assert icon.is_file()
    assert "<svg" in icon.read_text(encoding="utf-8")
    assert license_file.is_file()
    assert "ISC License" in license_file.read_text(encoding="utf-8")
    assert '"qml/assets/icons/*.svg"' in package
    assert '"qml/assets/icons/*.txt"' in package
