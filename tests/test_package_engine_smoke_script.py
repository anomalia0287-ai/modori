from __future__ import annotations

import json
import subprocess

from scripts import package_engine_smoke


def test_package_engine_smoke_reports_missing_executable(capsys) -> None:
    result = package_engine_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_engine_smoke_passes_when_payload_is_ok(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    def fake_run(command, check, timeout):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": True, "v1_statistics_smoke": {"ok": True}}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)

    assert result == 0


def test_package_engine_smoke_fails_when_payload_is_not_ok(monkeypatch, tmp_path, capsys) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    def fake_run(command, check, timeout):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "last_error": "engine"}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)

    captured = capsys.readouterr()
    assert result == 1
    assert "engine" in captured.err
