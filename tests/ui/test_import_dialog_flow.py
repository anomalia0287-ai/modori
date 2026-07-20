import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QPoint, QPointF, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


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
    assert "uiController.importRecoveryAvailable" in main
    assert "uiController.confirmPendingImport" in main
    assert "uiController.importPreviewText" in dialog
    assert "dialog.import.confirm" in dialog


def test_import_dialog_exposes_recovery_sheet_selector() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "uiController.importRecoveryAvailable" in dialog
    assert "uiController.importSheetNames" in dialog
    assert "uiController.importSelectedSheet" in dialog
    assert "dialog.import.sheet_recovery" in dialog
    assert "AppComboBox {" in dialog
    assert "sheetName.currentText" in dialog
    assert "root.settingsExpanded = uiController.importRecoveryAvailable" in dialog


def test_import_corrections_are_progressively_disclosed() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "property bool settingsExpanded" in dialog
    assert 'appBootstrap.text("dialog.import.settings", appBootstrap.language)' in dialog
    assert "visible: root.settingsExpanded" in dialog
    assert "dialog.import.preserve_metadata_detail" in dialog


def test_import_preview_and_column_picker_keep_bounded_widths() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "Layout.maximumWidth: theme.importPreviewColumnWidth" in dialog
    assert "Layout.minimumWidth: theme.importSettingsColumnMinimumWidth" in dialog


def test_import_column_picker_exposes_complete_elided_name() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")
    column_section = dialog[dialog.index("id: columnList"):]
    repeater = _qml_object_block(column_section, "Repeater {")
    checkbox = _qml_object_block(repeater, "AppCheckBox {")

    assert "Accessible.name: modelData.name" in checkbox
    assert "hoverEnabled: true" in checkbox
    assert "ToolTip.visible: hovered && contentItem.truncated" in checkbox
    assert "ToolTip.text: modelData.name" in checkbox
    assert "ToolTip.delay: theme.tooltipDelayMs" in checkbox


def test_import_column_tooltip_runtime_exposes_complete_elided_name() -> None:
    app = _app()
    view = QQuickView()
    component = QQmlComponent(view.engine())
    column_name = "response_text_that_must_remain_readable_after_import"
    component.setData(
        f'''\
import QtQuick
import QtQuick.Controls
import "../../src/modori/ui/qml/components"

Item {{
    width: 180
    height: 80

    AppCheckBox {{
        id: probe
        objectName: "importColumnProbe"
        width: 150
        height: 36
        text: "{column_name}"
        hoverEnabled: true

        ToolTip {{
            objectName: "importColumnTooltip"
            visible: probe.hovered && probe.contentItem.truncated
            text: probe.text
            delay: 0
        }}
    }}
}}
'''.encode(),
        QUrl.fromLocalFile(str((Path.cwd() / "tests/ui").resolve()) + "/"),
    )

    assert component.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in component.errors()
    ]
    root = component.create()
    assert root is not None
    view.setContent(QUrl(), component, root)
    view.setGeometry(0, 0, 180, 80)
    view.show()
    QTest.qWait(150)
    app.processEvents()

    probe = root.findChild(QQuickItem, "importColumnProbe")
    assert probe is not None
    content_item = probe.property("contentItem")
    assert content_item.property("truncated") is True
    scene_point = probe.mapToScene(QPointF(probe.width() - 8, probe.height() / 2))
    QTest.mouseMove(view, QPoint(round(scene_point.x()), round(scene_point.y())))
    QTest.qWait(100)
    app.processEvents()

    tooltip = root.findChild(QObject, "importColumnTooltip")
    assert probe.property("hovered") is True
    assert tooltip is not None
    assert tooltip.property("visible") is True
    assert tooltip.property("text") == column_name

    view.close()
    view.deleteLater()
    app.processEvents()


def test_import_dialog_keeps_one_rounded_frame_and_uses_shared_scrollbars() -> None:
    dialog = qml_text("dialogs/ImportDialog.qml")

    assert "background: PearlSurface {" in dialog
    assert "outlined: true" in dialog
    assert "outlineColor: theme.lineDialog" in dialog
    assert "color: theme.transparent" in dialog
    assert dialog.count("ScrollBar.vertical: AppScrollBar {") == 4
    assert dialog.count("height: parent ? parent.height : implicitHeight") == 4
    assert dialog.count("ScrollBar.horizontal.policy: ScrollBar.AlwaysOff") == 4
    assert "color: theme.surfaceRaised" in dialog
    assert "border.width: theme.spaceNone" in dialog


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
