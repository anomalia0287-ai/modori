from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from modori.app import AppBootstrap
from modori.ui.controller import UiController


def package_launch_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    cache_dir = Path(".tmp") / "packaged-launch-cache"
    settings_path = Path(".tmp") / "packaged-launch-settings.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    env["MODORI_CACHE_DIR"] = str(cache_dir.resolve())
    env["MODORI_SETTINGS_PATH"] = str(settings_path.resolve())
    return env


def run_launch_smoke(
    executable: str | Path,
    *,
    timeout_seconds: float = 8.0,
    working_directory: str | Path = "C:/Users/V/Desktop",
) -> int:
    del timeout_seconds, working_directory
    exe_path = Path(executable).resolve()
    if not exe_path.is_file():
        print(f"Packaged executable does not exist: {exe_path}", file=sys.stderr)
        return 2
    qml_root = _packaged_qml_root(exe_path)
    if not qml_root.is_file():
        print(f"Packaged QML root does not exist: {qml_root}", file=sys.stderr)
        return 1
    return _load_packaged_qml_root(qml_root)


def _packaged_qml_root(exe_path: Path) -> Path:
    return exe_path.parent / "_internal" / "modori" / "ui" / "qml" / "Main.qml"


def _load_packaged_qml_root(qml_root: Path) -> int:
    env = package_launch_environment()
    os.environ["QT_QPA_PLATFORM"] = env["QT_QPA_PLATFORM"]
    os.environ["MODORI_CACHE_DIR"] = env["MODORI_CACHE_DIR"]
    os.environ["MODORI_SETTINGS_PATH"] = env["MODORI_SETTINGS_PATH"]
    _app = QGuiApplication.instance() or QGuiApplication(["packaged-launch-smoke"])
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    controller = UiController(reduce_effects=True if bootstrap.reduceEffects else None)
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    engine.rootContext().setContextProperty("uiController", controller)
    engine.load(QUrl.fromLocalFile(str(qml_root)))
    if not engine.rootObjects():
        print(f"Packaged QML root failed to load: {qml_root}", file=sys.stderr)
        return 1
    print("package-launch-smoke-ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the packaged Modori executable.")
    parser.add_argument(
        "executable",
        nargs="?",
        default=str(Path("dist") / "Modori" / "Modori.exe"),
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--working-directory", default="C:/Users/V/Desktop")
    args = parser.parse_args(argv)

    return run_launch_smoke(
        args.executable,
        timeout_seconds=args.timeout,
        working_directory=args.working_directory,
    )


if __name__ == "__main__":
    raise SystemExit(main())
