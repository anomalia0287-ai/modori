from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

if __package__:
    from scripts.package_environment import (
        packaged_subprocess_environment,
        without_workspace_reference_runtime,
    )
else:
    from package_environment import (  # type: ignore[import-not-found]
        packaged_subprocess_environment,
        without_workspace_reference_runtime,
    )


def package_launch_environment(
    state_root: str | Path | None = None,
) -> dict[str, str]:
    if state_root is not None:
        return packaged_subprocess_environment(
            "packaged-launch-runtime",
            state_root=state_root,
        )
    env = without_workspace_reference_runtime()
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
    state_root: str | Path | None = None,
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
    library_root = _packaged_library_entries_root(exe_path)
    if not library_root.is_dir():
        print(
            f"Packaged library entries do not exist: {library_root}",
            file=sys.stderr,
        )
        return 1
    if state_root is None:
        return _load_packaged_qml_root(qml_root)
    return _load_packaged_qml_root(qml_root, state_root=state_root)


def _packaged_qml_root(exe_path: Path) -> Path:
    return exe_path.parent / "_internal" / "modori" / "ui" / "qml" / "Main.qml"


def _packaged_library_entries_root(exe_path: Path) -> Path:
    return exe_path.parent / "_internal" / "library" / "entries"


def _load_packaged_qml_root(
    qml_root: Path,
    *,
    state_root: str | Path | None = None,
) -> int:
    env = package_launch_environment(state_root=state_root)
    os.environ.update(env)
    for key in ("MODORI_RSCRIPT", "R_HOME", "R_LIBS", "R_LIBS_USER"):
        if key not in env:
            os.environ.pop(key, None)
    from modori.app import AppBootstrap
    from modori.knowledge import LibraryLoadError, load_library
    from modori.ui.controller import UiController

    library_entries = qml_root.parents[3] / "library" / "entries"
    try:
        library = load_library(library_entries)
    except (LibraryLoadError, OSError, UnicodeError):
        print("Packaged library entries failed to load.", file=sys.stderr)
        return 1

    _app = QGuiApplication.instance() or QGuiApplication(["packaged-launch-smoke"])
    engine = QQmlApplicationEngine()
    bootstrap = AppBootstrap()
    controller = UiController(
        reduce_effects=True if bootstrap.reduceEffects else None,
        library=library,
    )
    explanation = controller.explain("ui.result.cronbach_alpha", "ko")
    if not explanation.ok:
        print("Packaged explanation probe failed.", file=sys.stderr)
        return 1
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
    parser.add_argument("--state-root")
    args = parser.parse_args(argv)

    return run_launch_smoke(
        args.executable,
        timeout_seconds=args.timeout,
        working_directory=args.working_directory,
        state_root=args.state_root,
    )


if __name__ == "__main__":
    raise SystemExit(main())
