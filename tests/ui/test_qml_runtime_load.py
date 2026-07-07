from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine

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
    )
    return [
        message
        for message in messages
        if ("ReferenceError" in message or "TypeError" in message)
        and not any(token in message for token in allowed_substrings)
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
