from __future__ import annotations

import os
import sys

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.ui.controller import UiController
from modori.ui.resources import root_qml_path
from modori.ui.strings import UI_STRINGS_KO


class AppBootstrap(QObject):
    reduceEffectsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._reduce_effects = os.environ.get("MODORI_REDUCE_EFFECTS") == "1"

    @Property(bool, notify=reduceEffectsChanged)
    def reduceEffects(self) -> bool:
        return self._reduce_effects

    @Slot(str, result=str)
    def text(self, key: str) -> str:
        return UI_STRINGS_KO.get(key, key)


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    controller = UiController(reduce_effects=True if bootstrap.reduceEffects else None)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str(root_qml_path())))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
