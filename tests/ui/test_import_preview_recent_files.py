def test_import_preview_lists_variables_and_inferred_measures(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True

    preview = controller.importPreviewText
    assert "20 cases" in preview
    assert "9 variables" in preview
    assert "q1" in preview
    assert "group" in preview
    assert "ordinal" in preview


def test_recent_files_persist_to_settings_file(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(settings_path))
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)

    first = UiController()
    assert first.openDataFilePath(str(data_path)) is True
    assert "survey.csv" in first.recentFilesText

    second = UiController()
    assert "survey.csv" in second.recentFilesText


def test_recent_files_can_be_disabled_and_cleared(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(settings_path))
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)

    controller = UiController()
    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.setRecentFilesEnabled(False) is True
    assert controller.recentFilesText == ""

    reloaded = UiController()
    assert reloaded.recentFilesText == ""
    assert reloaded.recentFilesEnabled is False
