from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QUrl, qInstallMessageHandler
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from modori.app import AppBootstrap
from modori.ui.controller import UiController
from modori.ui.resources import root_qml_path

from tests.ui.test_end_to_end_ui_flow import write_reference_csv


QML_ROOT = Path("src/modori/ui/qml")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _component_errors(component: QQmlComponent) -> str:
    return "\n".join(error.toString() for error in component.errors())


def _significant_warnings(messages: list[str]) -> list[str]:
    allowed_substrings = (
        "Cannot find font directory",
        "QFontDatabase",
        "OpenThemeData() failed for theme",
        "The current style does not support customization of this control",
        "This plugin does not support propagateSizeHints()",
    )
    return [
        message
        for message in messages
        if not any(token in message for token in allowed_substrings)
    ]


def test_significant_warnings_fail_on_generic_qml_runtime_problems() -> None:
    messages = [
        "qrc:/Main.qml:12:9: Binding loop detected for property \"width\"",
        "qrc:/Main.qml:20:3: ReferenceError: missingThing is not defined",
        "QFontDatabase: Cannot find font directory C:/Windows/Fonts",
        "The current style does not support customization of this control",
        "This plugin does not support propagateSizeHints()",
    ]

    assert _significant_warnings(messages) == [
        'qrc:/Main.qml:12:9: Binding loop detected for property "width"',
        "qrc:/Main.qml:20:3: ReferenceError: missingThing is not defined",
    ]


def _load_main_with_warnings(
    ui_controller: UiController,
) -> tuple[QQmlApplicationEngine, object, list[str]]:
    app = _app()
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    try:
        engine.rootContext().setContextProperty("appBootstrap", bootstrap)
        engine.rootContext().setContextProperty("uiController", ui_controller)
        engine.load(QUrl.fromLocalFile(str(root_qml_path())))
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]
        root.setProperty("currentScreen", "work")
        app.processEvents()
        assert _significant_warnings(messages) == []
        return engine, root, messages
    finally:
        qInstallMessageHandler(previous_handler)


def test_data_grid_view_qml_loads_without_runtime_errors() -> None:
    app = _app()
    engine = QQmlEngine()
    bootstrap = AppBootstrap()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/DataGridView.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)

        obj = component.create()
        assert obj is not None, _component_errors(component)
        app.processEvents()
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
        assert _significant_warnings(messages) == []
    finally:
        qInstallMessageHandler(previous_handler)


@pytest.mark.parametrize("reduce_effects", [False, True])
def test_splash_qml_loads_without_runtime_errors(reduce_effects: bool) -> None:
    app = _app()
    engine = QQmlEngine()
    bootstrap = AppBootstrap()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "screens/SplashScreen.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)

        obj = component.createWithInitialProperties({"reduceEffects": reduce_effects})
        assert obj is not None, _component_errors(component)
        app.processEvents()
        progress = obj.findChild(QObject, "splashProgress")
        assert progress is not None
        assert progress.property("indeterminate") is (not reduce_effects)
        assert progress.property("value") == (1 if reduce_effects else 0)
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
        assert _significant_warnings(messages) == []
    finally:
        qInstallMessageHandler(previous_handler)


def test_brand_wordmark_loads_gothic_uppercase_style_without_runtime_errors() -> None:
    app = _app()
    engine = QQmlEngine()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/BrandWordmark.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)
        obj = component.create()
        assert obj is not None, _component_errors(component)
        QTest.qWait(100)
        app.processEvents()
        font = obj.property("font")
        assert font.family() == "Segoe UI"
        assert font.capitalization() == QFont.Capitalization.AllUppercase
        assert font.letterSpacing() == pytest.approx(2.4, abs=0.02)
        assert font.weight() == QFont.Weight.DemiBold
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)


def test_aurora_glass_surface_loads_with_switchable_layers() -> None:
    app = _app()
    engine = QQmlEngine()
    messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str((QML_ROOT / "components/AuroraGlassSurface.qml").resolve())),
    )

    try:
        assert component.status() == QQmlComponent.Status.Ready, _component_errors(component)
        obj = component.create()
        assert obj is not None, _component_errors(component)
        assert obj.property("tiffanyBloomEnabled") is True
        assert obj.property("bottomAnchorVisible") is False
        assert obj.property("reduceEffects") is False
        assert obj.setProperty("tiffanyBloomEnabled", False)
        assert obj.setProperty("reduceEffects", True)
        QTest.qWait(50)
        app.processEvents()
        assert obj.property("tiffanyBloomEnabled") is False
        assert obj.property("reduceEffects") is True
        assert _significant_warnings(messages) == []
        obj.deleteLater()
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)


def test_main_qml_loads_work_screen_with_shared_grid() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_loads_work_screen_with_imported_data_models(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    write_reference_csv(data_path)
    controller = UiController(reduce_effects=True)

    assert controller.chooseMode("guided") is True
    assert controller.openDataFilePath(str(data_path)) is True
    assert controller.dataModel is not None
    assert controller.dataModel.rowCount() > 0
    assert controller.variableModel is not None
    assert controller.variableModel.rowCount() > 0

    engine, root, messages = _load_main_with_warnings(controller)

    try:
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_settings_dialog() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        dialog = root.findChild(QObject, "settingsDialog")
        assert dialog is not None
        assert QMetaObject.invokeMethod(dialog, "open") is True
        _app().processEvents()
        assert dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_import_dialog() -> None:
    controller = UiController(reduce_effects=True)
    assert controller.previewDataFilePath(
        str((Path("tests/fixtures/psych_bfi.csv")).resolve())
    ) is True
    engine, root, messages = _load_main_with_warnings(controller)

    try:
        dialog = root.findChild(QObject, "importDialog")
        assert dialog is not None
        assert QMetaObject.invokeMethod(dialog, "open") is True
        _app().processEvents()
        assert dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine


def test_main_qml_exposes_openable_result_and_report_dialogs() -> None:
    engine, root, messages = _load_main_with_warnings(UiController(reduce_effects=True))

    try:
        result_dialog = root.findChild(QObject, "resultDetailDialog")
        report_dialog = root.findChild(QObject, "reportExportDialog")
        assert result_dialog is not None
        assert report_dialog is not None

        assert QMetaObject.invokeMethod(result_dialog, "open") is True
        _app().processEvents()
        assert result_dialog.property("opened") is True
        assert QMetaObject.invokeMethod(result_dialog, "close") is True
        _app().processEvents()

        assert QMetaObject.invokeMethod(report_dialog, "open") is True
        _app().processEvents()
        assert report_dialog.property("opened") is True
        assert _significant_warnings(messages) == []
    finally:
        root.deleteLater()
        _app().processEvents()
        del engine
