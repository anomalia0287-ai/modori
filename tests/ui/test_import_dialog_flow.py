from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_controller_previews_file_before_confirming_import(tmp_path) -> None:
    from tests.ui.test_end_to_end_ui_flow import write_reference_csv
    from modori.ui.controller import UiController

    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController()

    assert controller.previewDataFilePath(str(data_path)) is True
    assert "20 cases" in controller.importPreviewText
    assert "9 variables" in controller.importPreviewText
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
