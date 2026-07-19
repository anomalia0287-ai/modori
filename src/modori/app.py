from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.cache import cache_dir
from modori.public_data_smoke import run_public_data_import_smoke
from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController
from modori.ui.localization import localize_message
from modori.ui.resources import root_qml_path
from modori.ui.strings import UI_STRINGS_KO
from modori.ui.strings_en import UI_STRINGS_EN
from modori.v1_statistics_smoke import v1_statistics_smoke_payload


class AppBootstrap(QObject):
    languageChanged = Signal()
    reduceEffectsChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._language = "ko"
        self._reduce_effects = os.environ.get("MODORI_REDUCE_EFFECTS") == "1"

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._language

    @Slot(str, result=bool)
    def setLanguage(self, language: str) -> bool:
        normalized = str(language).lower()
        if normalized not in {"ko", "en"}:
            return False
        if normalized != self._language:
            self._language = normalized
            self.languageChanged.emit()
        return True

    @Property(bool, notify=reduceEffectsChanged)
    def reduceEffects(self) -> bool:
        return self._reduce_effects

    @Slot(str, result=str)
    @Slot(str, str, result=str)
    def text(self, key: str, language: str = "") -> str:
        selected = language if language in {"ko", "en"} else self._language
        catalog = UI_STRINGS_EN if selected == "en" else UI_STRINGS_KO
        return catalog.get(key, key)

    @Slot(str, result=str)
    @Slot(str, str, result=str)
    def localize(self, message: str, language: str = "") -> str:
        selected = language if language in {"ko", "en"} else self._language
        return localize_message(message, selected)

    @Slot(str, result=bool)
    def copyText(self, text: str) -> bool:
        if not text:
            return False
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(str(text))
        return True


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
    bootstrap.languageChanged.connect(
        lambda: controller.setUiLanguage(bootstrap.language)
    )
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str(root_qml_path())))
    if not engine.rootObjects():
        return 1
    return app.exec()


def _run_engine_smoke(data_path: Path, output_path: Path) -> int:
    payload: dict[str, object]
    try:
        runtime_cache_dir = cache_dir().resolve(strict=True)
        controller = UiController()
        opened = controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
        variable_model = controller.variableModel
        variable_keys = (
            [
                str(variable_model.data(variable_model.index(row, 0))).strip()
                for row in range(min(variable_model.rowCount(), 3))
            ]
            if variable_model is not None
            else []
        )
        configured = bool(
            opened.ok
            and variable_keys
            and controller.configureDescriptivesFromText(", ".join(variable_keys), "")
        )
        rerun = controller.rerun() if configured else None
        waited = controller.waitForLastRun(timeout=30) if rerun is not None else False
        v1_smoke = v1_statistics_smoke_payload()
        payload = {
            "ok": bool(
                opened.ok
                and rerun is not None
                and rerun.ok
                and waited
                and controller.status == "ready"
                and v1_smoke.get("ok") is True
            ),
            "cache_dir": str(runtime_cache_dir),
            "opened": opened.ok,
            "rerun": None if rerun is None else rerun.ok,
            "waited": waited,
            "status": controller.status,
            "last_error": controller.lastError,
            "result_summary_present": bool(controller.resultSummary),
            "data_rows": None if controller.dataModel is None else controller.dataModel.rowCount(),
            "data_columns": None if controller.dataModel is None else controller.dataModel.columnCount(),
            "v1_statistics_smoke": v1_smoke,
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
