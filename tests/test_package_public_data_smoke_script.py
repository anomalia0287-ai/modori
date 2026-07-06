from __future__ import annotations

import json
import subprocess

from scripts import package_public_data_smoke


def test_package_public_data_smoke_reports_missing_executable(capsys) -> None:
    result = package_public_data_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_public_data_smoke_reports_missing_fixture_dir(tmp_path, capsys) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")

    result = package_public_data_smoke.main(
        [str(exe), "--fixture-dir", str(tmp_path / "missing")]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "Public data smoke fixture directory does not exist" in captured.err


def test_package_public_data_smoke_passes_when_payload_is_ok(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": True, "case_count": 7}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )

    assert result == 0


def test_package_public_data_smoke_fails_when_contract_payload_is_not_ok(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": False,
                    "case_count": 7,
                    "cases": [{"name": "kosis-two-row-csv", "failures": ["columns"]}],
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "kosis-two-row-csv" in captured.err
