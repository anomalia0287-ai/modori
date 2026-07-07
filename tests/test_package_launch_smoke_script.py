from __future__ import annotations

from scripts import package_launch_smoke


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
