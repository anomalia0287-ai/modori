from __future__ import annotations

import subprocess

from scripts import package_launch_smoke


def test_package_launch_smoke_reports_missing_executable(capsys) -> None:
    result = package_launch_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_launch_smoke_passes_when_process_stays_running(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    calls: list[dict[str, object]] = []

    class FakeProcess:
        def wait(self, timeout: float | None = None) -> int:
            raise subprocess.TimeoutExpired("Modori.exe", timeout)

        def kill(self) -> None:
            calls.append({"kill": True})

    def fake_popen(command, *, cwd, env):
        calls.append({"command": command, "cwd": cwd, "env": env})
        return FakeProcess()

    monkeypatch.setattr(package_launch_smoke.subprocess, "Popen", fake_popen)

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    assert result == 0
    assert calls[0]["command"] == [str(exe.resolve())]
    assert calls[0]["env"]["QT_QPA_PLATFORM"] == "offscreen"
    assert calls[-1] == {"kill": True}


def test_package_launch_smoke_fails_when_process_exits_immediately(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    class FakeProcess:
        def wait(self, timeout: float | None = None) -> int:
            return 1

    monkeypatch.setattr(
        package_launch_smoke.subprocess,
        "Popen",
        lambda command, *, cwd, env: FakeProcess(),
    )

    result = package_launch_smoke.run_launch_smoke(exe, timeout_seconds=0.01)

    assert result == 1
