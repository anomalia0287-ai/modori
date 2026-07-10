from __future__ import annotations

import json
import os
from pathlib import Path
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

    r_root = tmp_path / ".tools" / "r-env"
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(r_root / "Scripts" / "Rscript.exe"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))
    captured_environment = {}

    def fake_run(command, check, timeout, env):
        captured_environment.update(env)
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "opened": True,
                    "rerun": True,
                    "waited": True,
                    "status": "ready",
                    "v1_statistics_smoke": {
                        "ok": True,
                        "checks": [
                            {
                                "key": "logistic_regression",
                                "ok": True,
                                "analysis_type": "LogisticRegressionResult",
                            }
                        ],
                    },
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)

    assert result == 0
    assert "MODORI_RSCRIPT" not in captured_environment
    assert str(r_root).casefold() not in captured_environment["PATH"].casefold()
    assert captured_environment["MPLCONFIGDIR"]
    assert captured_environment["MODORI_CACHE_DIR"]
    assert captured_environment["MODORI_SETTINGS_PATH"]


def test_package_engine_smoke_rejects_missing_logistic_evidence(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "opened": True,
                    "rerun": True,
                    "waited": True,
                    "status": "ready",
                    "v1_statistics_smoke": {"ok": True, "checks": []},
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)

    captured = capsys.readouterr()
    assert result == 1
    assert "logistic_regression" in captured.err


def test_package_engine_smoke_fails_when_payload_is_not_ok(
    monkeypatch, tmp_path, capsys
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "last_error": "engine"}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)

    captured = capsys.readouterr()
    assert result == 1
    assert "engine" in captured.err


def test_package_engine_smoke_rejects_stale_output(
    monkeypatch, tmp_path, capsys
) -> None:
    original_directory = Path.cwd()
    monkeypatch.chdir(tmp_path)
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    output = tmp_path / ".tmp" / "packaged-engine-smoke" / "result.json"
    output.parent.mkdir(parents=True)
    output.write_text(
        json.dumps(
            {
                "ok": True,
                "opened": True,
                "rerun": True,
                "waited": True,
                "status": "ready",
                "v1_statistics_smoke": {
                    "ok": True,
                    "checks": [
                        {
                            "key": "logistic_regression",
                            "ok": True,
                            "analysis_type": "LogisticRegressionResult",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_run(command, check, timeout, env=None):
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)
    monkeypatch.chdir(original_directory)

    assert result == 1
    assert "did not produce a fresh result" in capsys.readouterr().err
