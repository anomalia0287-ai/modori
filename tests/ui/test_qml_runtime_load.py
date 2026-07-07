from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from modori.app import AppBootstrap


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
