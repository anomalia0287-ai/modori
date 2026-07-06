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


def test_import_preview_failure_sets_visible_error(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "notes.txt"
    data_path.write_text("not,data\n", encoding="utf-8")
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is False

    assert controller.importPreviewText == "지원하지 않는 파일 형식입니다."
    assert controller.lastError == "지원하지 않는 파일 형식입니다."


def test_confirm_import_without_preview_sets_visible_error() -> None:
    from modori.ui.controller import UiController

    controller = UiController()

    assert controller.confirmPendingImport() is False

    assert controller.importPreviewText == "가져올 파일이 선택되지 않았습니다."
    assert controller.lastError == "가져올 파일이 선택되지 않았습니다."


def test_confirm_import_binds_preview_models_before_analysis_runs(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True
    assert controller.confirmPendingImport() is True

    assert controller.dataModel is not None
    assert controller.dataModel.rowCount() == 20
    assert controller.dataModel.columnCount() == 9
    assert controller.variableModel is not None
    assert controller.variableModel.rowCount() == 9
    assert controller.dataViewNotice == "가져온 데이터 미리보기: 20행 · 9열"
    assert controller.resultSummary == ""


def test_confirm_import_keeps_public_data_warning_visible_in_data_notice(tmp_path) -> None:
    from modori.ui.controller import UiController

    data_path = tmp_path / "public-with-preamble.csv"
    data_path.write_text(
        "\n".join(
            [
                "서울시 인구 현황",
                "자료기준일: 2024-12-31",
                "단위: 명",
                "자치구,연도,인구",
                "종로구,2024,140000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True
    assert controller.confirmPendingImport() is True

    assert "가져온 데이터 미리보기: 1행 · 3열" in controller.dataViewNotice
    assert "표 헤더 앞의 안내 행 3개" in controller.dataViewNotice


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


def test_recent_file_entry_reopens_existing_file(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(settings_path))
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)

    first = UiController()
    assert first.openDataFilePath(str(data_path)) is True

    second = UiController()
    assert second.openRecentFileAt(0) is True

    assert second.pipeline is not None
    assert second.lastError == ""
    assert "survey.csv" in second.recentFilesText


def test_recent_file_entry_reports_missing_file(tmp_path, monkeypatch) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(settings_path))
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)

    first = UiController()
    assert first.openDataFilePath(str(data_path)) is True
    data_path.unlink()

    second = UiController()
    assert second.openRecentFileAt(0) is False

    assert second.lastError == "최근 파일을 찾을 수 없습니다."
    assert second.pipeline is None


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
