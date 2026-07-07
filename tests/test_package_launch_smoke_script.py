from __future__ import annotations

import json
import subprocess

from scripts import package_launch_smoke


def test_package_launch_smoke_reports_missing_executable(capsys) -> None:
    result = package_launch_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_launch_smoke_passes_when_packaged_launch_smoke_reports_ready(
    monkeypatch,
    tmp_path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    calls: list[dict[str, object]] = []

    def fake_run(command, *, check, timeout, cwd, env):
        del check
        calls.append({"command": command, "timeout": timeout, "cwd": cwd, "env": env})
        output_path = command[-1]
        output_path.write_text(
            json.dumps({"ok": True, "root_objects": 1}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_launch_smoke.subprocess, "run", fake_run)

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    assert result == 0
    assert calls[0]["command"][:2] == [str(exe.resolve()), "--launch-smoke"]
    assert calls[0]["command"][-1].name == "result.json"
    assert calls[0]["env"]["QT_QPA_PLATFORM"] == "offscreen"
    assert calls[0]["timeout"] == 0.01


def test_package_launch_smoke_fails_when_packaged_launch_smoke_fails(
    monkeypatch,
    tmp_path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    def fake_run(command, *, check, timeout, cwd, env):
        del check, timeout, cwd, env
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(package_launch_smoke.subprocess, "run", fake_run)

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    assert result == 1
