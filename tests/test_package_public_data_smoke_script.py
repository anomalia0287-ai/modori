from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from scripts import package_public_data_smoke


def hardened_cases() -> list[dict[str, object]]:
    return [
        {
            "name": "kosis-two-row-csv",
            "ok": True,
            "status": "preview_and_full_import_ok",
            "warnings": ["집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다."],
            "full_import": {
                "row_count": 2,
                "warnings": ["집계/합계 행 1개를 감지했습니다. 필요한 경우 가져오기 창에서 제외할 수 있습니다."],
                "sample_rows": [{"행정구역별(1)": "전국"}],
            },
        },
        {
            "name": "kosis-two-row-drop",
            "ok": True,
            "status": "preview_and_full_import_ok",
            "warnings": ["집계/합계 행 1개를 제외했습니다."],
            "full_import": {
                "row_count": 1,
                "warnings": ["집계/합계 행 1개를 제외했습니다."],
                "sample_rows": [{"행정구역별(1)": "서울특별시"}],
            },
        },
        {
            "name": "cp949-public-csv",
            "ok": True,
            "status": "preview_and_full_import_ok",
            "warnings": ["CSV 인코딩: cp949"],
            "full_import": {
                "row_count": 2,
                "warnings": ["CSV 인코딩: cp949"],
                "sample_rows": [{"자치구": "종로구"}],
            },
        },
        {
            "name": "notice-only-xlsx-reject",
            "ok": True,
            "status": "expected_reject",
            "preview_error": "표 데이터가 없습니다.",
            "full_import_error": "표 데이터가 없습니다.",
        },
    ]


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

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            cases = hardened_cases()
            json.dump(
                {
                    "ok": True,
                    "case_count": len(cases),
                    "cases": cases,
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

    assert result == 0


def test_package_public_data_smoke_isolates_workspace_reference_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    r_root = tmp_path / ".tools" / "r-env"
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(r_root / "Scripts" / "Rscript.exe"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))
    captured_environment: dict[str, str] = {}

    def fake_run(command, check, timeout, env=None):
        if env is not None:
            captured_environment.update(env)
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            cases = hardened_cases()
            json.dump({"ok": True, "case_count": len(cases), "cases": cases}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )

    assert result == 0
    assert captured_environment
    assert "MODORI_RSCRIPT" not in captured_environment
    assert str(r_root).casefold() not in captured_environment["PATH"].casefold()
    assert captured_environment["MPLCONFIGDIR"]
    assert captured_environment["MODORI_CACHE_DIR"]
    assert captured_environment["MODORI_SETTINGS_PATH"]


def test_package_public_data_smoke_fails_when_contract_payload_is_not_ok(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": False,
                    "case_count": 8,
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


def test_package_public_data_smoke_fails_when_payload_lacks_hardened_evidence(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        cases = [
            {
                "name": "kosis-two-row-csv",
                "ok": True,
                "status": "preview_ok",
            }
        ]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": True, "case_count": len(cases), "cases": cases}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "preview_ok" in captured.err


def test_package_public_data_smoke_fails_when_case_count_does_not_match_cases(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "case_count": 9,
                    "cases": [{"name": "only-case", "ok": True}],
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
    assert "case_count" in captured.err


def test_package_public_data_smoke_fails_when_payload_has_no_cases(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()

    def fake_run(command, check, timeout, env):
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": True, "case_count": 0, "cases": []}, handle)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert '"cases": []' in captured.err


def test_package_public_data_smoke_rejects_stale_output(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    original_directory = Path.cwd()
    monkeypatch.chdir(tmp_path)
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    output = Path(".tmp") / "packaged-public-data-smoke" / "result.json"
    output.parent.mkdir(parents=True)
    cases = hardened_cases()
    output.write_text(
        json.dumps({"ok": True, "case_count": len(cases), "cases": cases}),
        encoding="utf-8",
    )

    def fake_run(command, check, timeout, env):
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_public_data_smoke.subprocess, "run", fake_run)

    result = package_public_data_smoke.run_public_data_smoke(
        exe,
        fixture_dir=fixture_dir,
        timeout_seconds=0.01,
    )
    monkeypatch.chdir(original_directory)

    assert result == 1
    assert "did not produce a fresh result" in capsys.readouterr().err
