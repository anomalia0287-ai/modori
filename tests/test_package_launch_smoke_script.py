from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import package_launch_smoke


def test_package_launch_smoke_defers_modori_runtime_import_until_env_setup() -> None:
    workspace = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import scripts.package_launch_smoke; "
                "assert 'modori.app' not in sys.modules; "
                "assert 'modori.ui.controller' not in sys.modules"
            ),
        ],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_package_launch_smoke_reports_missing_executable(capsys) -> None:
    result = package_launch_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_launch_smoke_passes_when_packaged_qml_root_loads(
    monkeypatch,
    tmp_path,
) -> None:
    exe = tmp_path / "Modori" / "Modori.exe"
    qml_root = exe.parent / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    qml_root.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    qml_root.write_text("import QtQuick\nItem {}\n", encoding="utf-8")
    calls = []

    def fake_load_packaged_qml_root(path):
        calls.append(path)
        return 0

    monkeypatch.setattr(
        package_launch_smoke,
        "_load_packaged_qml_root",
        fake_load_packaged_qml_root,
    )

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    assert result == 0
    assert calls == [qml_root.resolve()]


def test_package_launch_smoke_fails_when_packaged_qml_root_is_missing(
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori" / "Modori.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    captured = capsys.readouterr()
    assert result == 1
    assert "Packaged QML root does not exist" in captured.err


def test_package_launch_smoke_cli_routes_explicit_state_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "Modori" / "Modori.exe"
    qml_root = exe.parent / "_internal" / "modori" / "ui" / "qml" / "Main.qml"
    qml_root.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    qml_root.write_text("import QtQuick\nItem {}\n", encoding="utf-8")
    state_root = tmp_path / "state"
    calls: list[tuple[Path, str | Path | None]] = []

    def fake_load_packaged_qml_root(
        path: Path,
        *,
        state_root: str | Path | None = None,
    ) -> int:
        calls.append((path, state_root))
        return 0

    monkeypatch.setattr(
        package_launch_smoke,
        "_load_packaged_qml_root",
        fake_load_packaged_qml_root,
    )

    result = package_launch_smoke.main(
        [str(exe), "--state-root", str(state_root)]
    )

    assert result == 0
    assert calls == [(qml_root.resolve(), str(state_root))]


def test_package_launch_environment_routes_exact_state_paths_and_strips_r(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "state-parent" / ".." / "state"
    r_root = tmp_path / ".tools" / "r-env"
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(r_root / "Scripts" / "Rscript.exe"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))

    env = package_launch_smoke.package_launch_environment(state_root=state_root)

    resolved_root = state_root.resolve()
    assert env["MODORI_CACHE_DIR"] == str(resolved_root / "cache")
    assert env["MODORI_SETTINGS_PATH"] == str(resolved_root / "settings.json")
    assert env["MPLCONFIGDIR"] == str(resolved_root / "matplotlib")
    assert env["QT_QPA_PLATFORM"] == "offscreen"
    assert "MODORI_RSCRIPT" not in env
    assert str(r_root).casefold() not in env["PATH"].casefold()


def test_package_launch_smoke_rejects_linked_state_before_qml_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = tmp_path / "Main.qml"
    qml_root.write_text("import QtQuick\nItem {}\n", encoding="utf-8")
    outside = tmp_path / "outside-state"
    outside.mkdir()
    state_link = tmp_path / "state-link"
    try:
        state_link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    runtime_calls: list[str] = []

    class UnexpectedQGuiApplication:
        @staticmethod
        def instance():
            runtime_calls.append("instance")
            return object()

    class UnexpectedQmlEngine:
        def rootContext(self):
            return SimpleNamespace(setContextProperty=lambda *_args: None)

        def load(self, _url):
            runtime_calls.append("load")

        def rootObjects(self):
            return [object()]

    class FakeBootstrap:
        reduceEffects = False

    class FakeController:
        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr(
        package_launch_smoke,
        "QGuiApplication",
        UnexpectedQGuiApplication,
    )
    monkeypatch.setattr(package_launch_smoke, "QQmlApplicationEngine", UnexpectedQmlEngine)
    monkeypatch.setitem(
        sys.modules,
        "modori.app",
        SimpleNamespace(AppBootstrap=FakeBootstrap),
    )
    monkeypatch.setitem(
        sys.modules,
        "modori.ui.controller",
        SimpleNamespace(UiController=FakeController),
    )

    with pytest.raises(ValueError, match="link or junction/reparse"):
        package_launch_smoke._load_packaged_qml_root(
            qml_root,
            state_root=state_link / "missing-child",
        )

    assert runtime_calls == []
    assert list(outside.iterdir()) == []
