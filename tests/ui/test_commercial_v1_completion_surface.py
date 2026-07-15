from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_splash_screen_exists_and_is_wired() -> None:
    splash = Path("src/modori/ui/qml/screens/SplashScreen.qml")
    main = qml_text("Main.qml")

    assert splash.is_file()
    text = splash.read_text(encoding="utf-8")
    assert "import QtQuick.Controls.Basic" in text
    assert "PearlSurface" in text
    assert "theme.orange" not in text
    assert "GradientStop" not in text
    assert "theme.splashProgressWidth" in text
    assert "theme.splashProgressHeight" in text
    assert "root.reduceEffects" in text
    assert 'appBootstrap.text("splash.subtitle")' in text
    assert 'appBootstrap.text("privacy.local")' in text
    assert "SplashScreen" in main


def test_recent_files_surface_updates_after_import(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(tmp_path / "settings.json"))
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.recentFilesText == ""
    assert controller.recentFilesModel is controller.recentFilesModel
    assert controller.openDataFilePath(str(data_path)) is True

    assert "survey.csv" in controller.recentFilesText
    assert controller.recentFilesModel.rowCount() == 1
    assert controller.recentFilesModel.data(controller.recentFilesModel.index(0, 0)) == "survey.csv"
    assert controller.recentFilesModel is controller.recentFilesModel


def test_entry_screen_displays_recent_files() -> None:
    entry = qml_text("screens/EntryScreen.qml")

    assert "uiController.recentFilesModel" in entry
    assert "recentFilesText.split" not in entry
    assert "entry.recent" in entry


def test_data_table_discloses_read_only_edit_policy() -> None:
    data_table = qml_text("components/DataTable.qml")

    assert 'appBootstrap.text("data.edit_policy")' in data_table


def test_qa_document_records_current_verdict() -> None:
    qa = Path("docs/specs/04-ui-shell-commercial-v1-qa.md").read_text(encoding="utf-8")

    assert "Final repository-local verification" in qa
    assert "267 passed, 2 skipped" in qa
    assert "Commercial v1 verdict" in qa
    assert "Repository-local #04 UI Shell commercial-v1 implementation gate is passed" in qa
