from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts import package_engine_smoke


def test_package_engine_smoke_reports_missing_executable(capsys) -> None:
    result = package_engine_smoke.main(["does-not-exist.exe"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Packaged executable does not exist" in captured.err


def test_package_engine_smoke_passes_when_payload_is_ok(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    state_root = tmp_path / "state"

    def fake_run(command, check, timeout, env):
        cache_path = Path(env["MODORI_CACHE_DIR"])
        assert not cache_path.exists()
        cache_path.mkdir(parents=True)
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "cache_dir": str(cache_path.resolve()),
                    "v1_statistics_smoke": {"ok": True},
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(
        exe,
        timeout_seconds=0.01,
        state_root=state_root,
    )

    assert result == 0


def test_package_engine_smoke_isolates_workspace_reference_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    r_root = tmp_path / ".tools" / "r-env"
    r_bin = r_root / "Library" / "bin"
    monkeypatch.setenv("MODORI_RSCRIPT", str(r_root / "Scripts" / "Rscript.exe"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(r_bin), "C:\\Windows"]))
    captured_environment: dict[str, str] = {}
    state_root = tmp_path / "state"

    def fake_run(command, check, timeout, env=None):
        if env is not None:
            captured_environment.update(env)
        cache_path = Path(env["MODORI_CACHE_DIR"])
        assert not cache_path.exists()
        cache_path.mkdir(parents=True)
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "cache_dir": str(cache_path.resolve()),
                    "v1_statistics_smoke": {"ok": True},
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(
        exe,
        timeout_seconds=0.01,
        state_root=state_root,
    )

    assert result == 0
    assert captured_environment
    assert "MODORI_RSCRIPT" not in captured_environment
    assert str(r_root).casefold() not in captured_environment["PATH"].casefold()
    assert captured_environment["MPLCONFIGDIR"]
    assert captured_environment["MODORI_CACHE_DIR"]
    assert captured_environment["MODORI_SETTINGS_PATH"]


def test_package_engine_smoke_cli_routes_exact_state_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    original_directory = Path.cwd()
    monkeypatch.chdir(tmp_path)
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    state_root = tmp_path / "state-parent" / ".." / "state"
    captured_environment: dict[str, str] = {}

    def fake_run(command, check, timeout, env):
        captured_environment.update(env)
        cache_path = Path(env["MODORI_CACHE_DIR"])
        assert not cache_path.exists()
        cache_path.mkdir(parents=True)
        output_path = command[3]
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "cache_dir": str(cache_path.resolve()),
                    "v1_statistics_smoke": {"ok": True},
                },
                handle,
            )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    try:
        result = package_engine_smoke.main(
            [str(exe), "--state-root", str(state_root), "--timeout", "0.01"]
        )
    finally:
        monkeypatch.chdir(original_directory)

    resolved_root = state_root.resolve()
    assert result == 0
    assert captured_environment["MODORI_CACHE_DIR"] == str(resolved_root / "cache")
    assert captured_environment["MODORI_SETTINGS_PATH"] == str(
        resolved_root / "settings.json"
    )
    assert captured_environment["MPLCONFIGDIR"] == str(resolved_root / "matplotlib")
    assert captured_environment["QT_QPA_PLATFORM"] == "offscreen"


@pytest.mark.parametrize(
    "cache_evidence",
    ["missing", "mismatch", "not-created"],
)
def test_package_engine_smoke_rejects_invalid_cache_evidence(
    monkeypatch,
    tmp_path: Path,
    cache_evidence: str,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    state_root = tmp_path / "state"

    def fake_run(command, check, timeout, env):
        cache_path = Path(env["MODORI_CACHE_DIR"])
        assert not cache_path.exists()
        if cache_evidence != "not-created":
            cache_path.mkdir(parents=True)
        payload: dict[str, object] = {
            "ok": True,
            "v1_statistics_smoke": {"ok": True},
        }
        if cache_evidence == "mismatch":
            payload["cache_dir"] = str((state_root / "other-cache").resolve())
        elif cache_evidence == "not-created":
            payload["cache_dir"] = str(cache_path.resolve())
        output_path = command[3]
        Path(output_path).write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(
        exe,
        timeout_seconds=0.01,
        state_root=state_root,
    )

    assert result == 1


def test_package_engine_smoke_rejects_linked_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    state_root = tmp_path / "state"
    cache_path = state_root / "cache"
    outside = tmp_path / "outside-cache"
    outside.mkdir()
    cache_path.parent.mkdir(parents=True)
    try:
        cache_path.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")

    def fake_run(command, check, timeout, env):
        assert Path(env["MODORI_CACHE_DIR"]) == cache_path
        output_path = command[3]
        Path(output_path).write_text(
            json.dumps(
                {
                    "ok": True,
                    "cache_dir": str(outside.resolve()),
                    "v1_statistics_smoke": {"ok": True},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(
        exe,
        timeout_seconds=0.01,
        state_root=state_root,
    )

    assert result == 1


def test_package_engine_smoke_rejects_linked_state_ancestor_before_subprocess(
    monkeypatch,
    tmp_path: Path,
) -> None:
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    outside = tmp_path / "outside-state"
    outside.mkdir()
    state_link = tmp_path / "state-link"
    try:
        state_link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    calls: list[list[str]] = []

    def fake_run(command, check, timeout, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match="link or junction/reparse"):
        package_engine_smoke.run_engine_smoke(
            exe,
            timeout_seconds=0.01,
            state_root=state_link / "missing-child",
        )

    assert calls == []
    assert list(outside.iterdir()) == []


def test_package_engine_smoke_fails_when_payload_is_not_ok(monkeypatch, tmp_path, capsys) -> None:
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
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    original_directory = Path.cwd()
    monkeypatch.chdir(tmp_path)
    exe = tmp_path / "Modori.exe"
    exe.write_text("", encoding="utf-8")
    output = Path(".tmp") / "packaged-engine-smoke" / "result.json"
    output.parent.mkdir(parents=True)
    output.write_text(
        json.dumps({"ok": True, "v1_statistics_smoke": {"ok": True}}),
        encoding="utf-8",
    )

    def fake_run(command, check, timeout, env):
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(package_engine_smoke.subprocess, "run", fake_run)

    result = package_engine_smoke.run_engine_smoke(exe, timeout_seconds=0.01)
    monkeypatch.chdir(original_directory)

    assert result == 1
    assert "did not produce a fresh result" in capsys.readouterr().err
