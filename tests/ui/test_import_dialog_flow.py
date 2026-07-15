import re
from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def _qml_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _qml_block_at(text: str, opening_brace: int) -> str:
    depth = 0
    for index in range(opening_brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening_brace : index + 1]
    raise AssertionError("QML block was not closed")


def _qml_object_block(text: str, marker: str) -> str:
    marker_index = text.index(marker)
    return _qml_block_at(text, text.index("{", marker_index))


def _qml_handler_block(text: str, marker: str) -> str:
    marker_index = text.index(marker)
    return _qml_block_at(text, text.index("{", marker_index))


def _controller_method_calls(block: str) -> list[str]:
    return re.findall(r"uiController\.([A-Za-z_]\w*)\s*\(", block)


def _assert_no_hidden_run_calls(block: str) -> None:
    forbidden_run_methods = {
        "rerunNow",
        "runPreparedRecommendationNow",
        "runPreparedRecommendation",
    }
    assert not (set(_controller_method_calls(block)) & forbidden_run_methods)


def test_controller_previews_file_before_confirming_import(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True
    assert "미리 읽은 데이터: 20행 · 9개 변수" in controller.importPreviewText
    assert controller.pipeline is None

    assert controller.confirmPendingImport() is True
    assert controller.pipeline is not None


def test_main_qml_uses_import_dialog_before_importing() -> None:
    main = qml_text("Main.qml")
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "ImportDialog" in main
    assert "uiController.previewDataFilePath" in main
    assert "uiController.confirmPendingImport" in main
    assert "uiController.importPreviewText" in dialog
    assert "dialog.import.confirm" in dialog


def test_import_corrections_are_progressively_disclosed() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "property bool settingsExpanded" in dialog
    assert 'appBootstrap.text("dialog.import.settings")' in dialog
    assert "visible: root.settingsExpanded" in dialog
    assert "dialog.import.preserve_metadata_detail" in dialog


def test_import_preview_and_column_picker_keep_bounded_widths() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "Layout.maximumWidth: theme.importPreviewColumnWidth" in dialog
    assert "Layout.minimumWidth: theme.importSettingsColumnMinimumWidth" in dialog


def test_import_and_recent_file_paths_do_not_start_analysis_automatically() -> None:
    main = qml_text("Main.qml")

    recent_block = _qml_handler_block(main, "onRecentFileRequested:")
    file_dialog_block = _qml_object_block(main, "FileDialog {")
    file_dialog_accepted_block = _qml_handler_block(file_dialog_block, "onAccepted:")
    import_block = _qml_handler_block(main, "onImportAccepted:")

    _assert_no_hidden_run_calls(recent_block)
    _assert_no_hidden_run_calls(file_dialog_block)
    _assert_no_hidden_run_calls(file_dialog_accepted_block)
    _assert_no_hidden_run_calls(import_block)

    assert "openRecentFileAt" in _controller_method_calls(recent_block)
    assert "previewDataFilePath" in _controller_method_calls(file_dialog_accepted_block)
    assert "confirmPendingImport" in _controller_method_calls(import_block)
