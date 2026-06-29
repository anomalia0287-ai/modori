from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.app import AppBootstrap
from modori.ui.controller import UiController
from modori.ui.resources import root_qml_path


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app = QGuiApplication(["modori-launch-smoke"])
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    controller = UiController(reduce_effects=True if bootstrap.reduceEffects else None)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str(root_qml_path())))
    if not engine.rootObjects():
        print("launch-smoke-failed: no QML root objects", file=sys.stderr)
        return 1

    QTimer.singleShot(0, app.quit)
    app.exec()
    print("launch-smoke-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
