from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.public_data_smoke import run_public_data_import_smoke
from modori.ui.contracts import ImportOptions
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


def main(argv: Sequence[str] | None = None) -> int:
    selected_argv = list(sys.argv if argv is None else argv)
    if len(selected_argv) == 4 and selected_argv[1] == "--engine-smoke":
        return _run_engine_smoke(Path(selected_argv[2]), Path(selected_argv[3]))
    if len(selected_argv) == 4 and selected_argv[1] == "--public-data-smoke":
        return run_public_data_import_smoke(Path(selected_argv[2]), Path(selected_argv[3]))

    app = QGuiApplication(selected_argv)
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    controller = UiController(reduce_effects=True if bootstrap.reduceEffects else None)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str(root_qml_path())))
    if not engine.rootObjects():
        return 1
    return app.exec()


def _run_engine_smoke(data_path: Path, output_path: Path) -> int:
    payload: dict[str, object]
    try:
        controller = UiController()
        opened = controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
        if opened.ok:
            rerun = (
                controller.runPreparedRecommendation()
                if controller.recommendationCount > 0
                else controller.rerun()
            )
            waited = controller.waitForLastRun(timeout=30)
        else:
            rerun = None
            waited = False
        payload = {
            "ok": bool(opened.ok and waited and controller.status == "ready"),
            "opened": opened.ok,
            "rerun": None if rerun is None else rerun.ok,
            "waited": waited,
            "status": controller.status,
            "last_error": controller.lastError,
            "result_summary_present": bool(controller.resultSummary),
            "data_rows": None if controller.dataModel is None else controller.dataModel.rowCount(),
            "data_columns": None if controller.dataModel is None else controller.dataModel.columnCount(),
        }
    except Exception as exc:
        payload = {"ok": False, "exception": f"{type(exc).__name__}: {exc}"}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return 0 if payload.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
