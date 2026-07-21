from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from scripts import installer_smoke
from scripts.installer_contract import (
    ASSUMED_INSTALL_ROOT_CHARS,
    DOWNGRADE_PROBE_VERSION,
    PRODUCTION_APP_ID,
    SAFE_PATH_BUDGET_CHARS,
    SMOKE_APP_ID,
    sha256_file,
)


_LONGEST_RELATIVE_PAYLOAD_PATH = (
    "_internal/PySide6/qml/QtQuick/Controls/FluentWinUI3/light/images/"
    "pageindicatordelegate-indicator-delegate-current-pressed@3x.png"
)


def _manifest_payload(
    installer: Path,
    probe: Path,
    *,
    longest_relative_path: str = _LONGEST_RELATIVE_PAYLOAD_PATH,
) -> dict[str, Any]:
    return {
        "channel": "internal-smoke",
        "app_id": SMOKE_APP_ID,
        "smoke_only": True,
        "version": "0.1.0",
        "installer": {
            "filename": installer.name,
            "sha256": sha256_file(installer),
        },
        "downgrade_probe": {
            "version": DOWNGRADE_PROBE_VERSION,
            "filename": probe.name,
            "sha256": sha256_file(probe),
        },
        "payload_paths": {
            "file_count": 4376,
            "longest_relative_path": longest_relative_path,
            "longest_relative_path_chars": len(longest_relative_path),
            "assumed_install_root_chars": ASSUMED_INSTALL_ROOT_CHARS,
            "safe_path_budget_chars": SAFE_PATH_BUDGET_CHARS,
            "computed_max_chars": (
                ASSUMED_INSTALL_ROOT_CHARS + 1 + len(longest_relative_path)
            ),
        },
    }


def _manifest(
    path: Path,
    installer: Path,
    probe: Path,
    *,
    app_id: str = SMOKE_APP_ID,
    longest_relative_path: str = _LONGEST_RELATIVE_PAYLOAD_PATH,
) -> dict[str, Any]:
    payload = _manifest_payload(
        installer,
        probe,
        longest_relative_path=longest_relative_path,
    )
    payload["app_id"] = app_id
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _set_nested(payload: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    target = payload
    for key in path[:-1]:
        nested = target[key]
        assert isinstance(nested, dict)
        target = nested
    target[path[-1]] = value


def _inputs(
    tmp_path: Path,
    *,
    longest_relative_path: str = _LONGEST_RELATIVE_PAYLOAD_PATH,
) -> tuple[Path, Path, Path]:
    installer = tmp_path / "smoke.exe"
    probe = tmp_path / "probe.exe"
    manifest = tmp_path / "manifest.json"
    installer.write_bytes(b"smoke")
    probe.write_bytes(b"probe")
    _manifest(
        manifest,
        installer,
        probe,
        longest_relative_path=longest_relative_path,
    )
    return installer, manifest, probe


def _patch_smoke_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    smoke_root = workspace / ".tmp" / "installer-smoke"
    monkeypatch.setattr(installer_smoke, "WORKSPACE", workspace)
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    return workspace, smoke_root


def _create_directory_junction(junction: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"directory junctions are unavailable: {completed.stderr}")
    assert junction.is_junction()


def _write_exercised_user_state(
    adapter: installer_smoke.LifecycleAdapter,
) -> None:
    adapter.user_state_dir.mkdir(parents=True)
    (adapter.user_state_dir / "sentinel.json").write_text(
        "preserve",
        encoding="utf-8",
    )
    (adapter.user_state_dir / "cache").mkdir()
    (adapter.user_state_dir / "matplotlib").mkdir()


def _write_durable_evidence_for_command(command: list[str]) -> None:
    if len(command) <= 1 or "--evidence-dir" not in command:
        return
    evidence_dir = Path(command[command.index("--evidence-dir") + 1])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if command[1].endswith("package_engine_smoke.py"):
        (evidence_dir / "reference.xlsx").write_bytes(b"xlsx-evidence")
        state_root = Path(command[command.index("--state-root") + 1]).resolve()
        payload = {
            "ok": True,
            "cache_dir": str(state_root / "cache"),
            "v1_statistics_smoke": {"ok": True},
        }
    elif command[1].endswith("package_public_data_smoke.py"):
        cases = [
            {
                "name": "kosis-two-row-csv",
                "ok": True,
                "warnings": ["집계/합계 행 1개를 감지했습니다."],
                "full_import": {},
            },
            {
                "name": "kosis-two-row-drop",
                "ok": True,
                "full_import": {
                    "sample_rows": [{"행정구역별(1)": "서울"}],
                },
            },
            {
                "name": "cp949-public-csv",
                "ok": True,
                "full_import": {
                    "warnings": ["CSV 인코딩: cp949"],
                },
            },
            {
                "name": "notice-only-xlsx-reject",
                "ok": True,
                "status": "expected_reject",
                "preview_error": "expected",
                "full_import_error": "expected",
            },
        ]
        payload = {
            "ok": True,
            "case_count": len(cases),
            "cases": cases,
        }
    else:
        return
    (evidence_dir / "result.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _patch_recording_adapter(
    monkeypatch: pytest.MonkeyPatch,
    adapter: installer_smoke.LifecycleAdapter,
    events: list[str],
) -> None:
    monkeypatch.setattr(
        adapter,
        "require_no_existing_registration",
        lambda: events.append("preflight"),
    )
    monkeypatch.setattr(
        adapter,
        "require_installed",
        lambda _version: events.append("installed"),
    )
    monkeypatch.setattr(
        adapter,
        "require_user_state_exercised",
        lambda: events.append("state-exercised"),
    )
    monkeypatch.setattr(
        adapter,
        "plant_stale_probe",
        lambda: events.append("planted"),
    )
    monkeypatch.setattr(
        adapter,
        "require_repaired",
        lambda _version: events.append("repaired"),
    )
    monkeypatch.setattr(adapter, "record_executable_hash", lambda: "A" * 64)
    monkeypatch.setattr(
        adapter,
        "require_downgrade_unchanged",
        lambda _version, _sha: events.append("downgrade-rejected"),
    )
    monkeypatch.setattr(
        adapter,
        "require_uninstalled",
        lambda: events.append("uninstalled"),
    )
    monkeypatch.setattr(
        adapter,
        "verify_and_remove_user_state",
        lambda *_args: events.append("state-preserved"),
    )


def test_smoke_refuses_production_identity_before_running(tmp_path: Path) -> None:
    installer = tmp_path / "smoke.exe"
    probe = tmp_path / "probe.exe"
    manifest = tmp_path / "manifest.json"
    installer.write_bytes(b"smoke")
    probe.write_bytes(b"probe")
    _manifest(manifest, installer, probe, app_id=PRODUCTION_APP_ID)
    called = False

    def runner(_command: list[str]) -> int:
        nonlocal called
        called = True
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
    )

    assert result == 2
    assert called is False


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    [
        (("channel",), "internal"),
        (("app_id",), PRODUCTION_APP_ID),
        (("smoke_only",), False),
        (("version",), "0.1"),
        (("installer", "filename"), "other-smoke.exe"),
        (("installer", "sha256"), "0" * 64),
        (("downgrade_probe", "version"), "0.0.8"),
        (("downgrade_probe", "filename"), "other-probe.exe"),
        (("downgrade_probe", "sha256"), "F" * 64),
        (("payload_paths",), []),
        (("payload_paths", "longest_relative_path"), 7),
        (("payload_paths", "longest_relative_path_chars"), 127),
    ],
    ids=[
        "channel",
        "app-id",
        "smoke-only",
        "release-version",
        "installer-filename",
        "installer-hash",
        "downgrade-version",
        "probe-filename",
        "probe-hash",
        "payload-paths-shape",
        "longest-relative-path-shape",
        "longest-relative-path-length",
    ],
)
def test_invalid_manifest_evidence_fails_before_any_runner_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field_path: tuple[str, ...],
    invalid_value: object,
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    payload = _manifest_payload(installer, probe)
    _set_nested(payload, field_path, invalid_value)
    _write_manifest(manifest, payload)
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    calls: list[list[str]] = []
    registrations: list[str] = []
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: registrations.append("queried") or None,
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 0,
    )

    assert result == 2
    assert calls == []
    assert registrations == []
    assert not smoke_root.exists()


@pytest.mark.parametrize(
    "longest_relative_path",
    [
        "D:/x",
        "D:x",
        "//server/share/x",
        r"\\server\share\x",
        "/x",
        r"\x",
    ],
    ids=[
        "drive-absolute",
        "drive-relative",
        "unc-forward-slash",
        "unc-backslash",
        "rooted-forward-slash",
        "rooted-backslash",
    ],
)
def test_drive_unc_and_rooted_path_evidence_fails_before_mutation_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    longest_relative_path: str,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path=longest_relative_path,
    )
    smoke_root = tmp_path / "runs"
    events: list[str] = []
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: events.append("registration") or None,
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda _command: events.append("runner") or 1,
    )

    assert result == 2
    assert events == []
    assert not smoke_root.exists()


def test_invalid_json_is_validation_failure_before_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    manifest.write_text("{", encoding="utf-8")
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    calls: list[list[str]] = []

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 0,
    )

    assert result == 2
    assert calls == []
    assert not smoke_root.exists()


def test_setup_command_uses_only_isolated_silent_safety_flags(tmp_path: Path) -> None:
    installer = tmp_path / "smoke.exe"
    install_dir = tmp_path / "run" / "install"
    log_path = tmp_path / "run" / "install.log"

    command = installer_smoke.setup_command(installer, install_dir, log_path)

    assert command == [
        str(installer.resolve()),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOFORCECLOSEAPPLICATIONS",
        "/NORESTARTAPPLICATIONS",
        f"/DIR={install_dir.resolve()}",
        f"/LOG={log_path.resolve()}",
    ]


def test_real_run_setup_dir_reduces_observed_267_path_to_budget() -> None:
    run_uuid = UUID("123456789abcdef0123456789abcdef0")
    synthetic_smoke_root = Path("C:/") / ("s" * 83)
    old_install_dir = synthetic_smoke_root / f"run-{run_uuid.hex}" / "install"
    old_destination = (
        old_install_dir / "Modori" / _LONGEST_RELATIVE_PAYLOAD_PATH
    ).resolve()
    compact_run_root = synthetic_smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_real_run(compact_run_root)
    setup = installer_smoke.setup_command(
        Path("smoke.exe"),
        adapter.install_dir,
        compact_run_root / "install.log",
    )
    destination = (
        adapter.install_dir / "Modori" / _LONGEST_RELATIVE_PAYLOAD_PATH
    ).resolve()

    assert len(_LONGEST_RELATIVE_PAYLOAD_PATH) == 128
    assert synthetic_smoke_root.is_absolute()
    assert len(str(synthetic_smoke_root)) == 86
    assert len(str(old_destination)) == 267
    assert adapter.install_dir == compact_run_root / "i"
    assert f"/DIR={adapter.install_dir.resolve()}" in setup
    assert len(str(destination)) == 239
    assert len(str(old_destination)) - len(str(destination)) == 28
    assert len(str(destination)) <= SAFE_PATH_BUDGET_CHARS


def test_real_adapter_keeps_install_and_user_state_in_separate_run_subtrees(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    run_root = tmp_path / "runs" / f"r-{'a' * 12}"

    adapter = installer_smoke.LifecycleAdapter.for_real_run(run_root)

    assert adapter.install_dir == run_root / "i"
    assert adapter.user_state_dir == run_root / "user-state"
    assert adapter.install_dir.parent == adapter.user_state_dir.parent == run_root
    assert adapter.user_state_dir not in adapter.install_dir.parents
    assert adapter.install_dir not in adapter.user_state_dir.parents
    assert adapter.start_menu_shortcut == (
        appdata
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Modori Installer Smoke.lnk"
    )


def test_fixed_uninstall_key_uses_only_smoke_identity() -> None:
    assert installer_smoke.uninstall_key() == (
        installer_smoke.UNINSTALL_ROOT + f"\\{SMOKE_APP_ID}_is1"
    )


def test_existing_registration_blocks_with_manual_cleanup_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    uninstall_path = tmp_path / "unins000.exe"
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: {"UninstallString": str(uninstall_path)},
    )

    with pytest.raises(RuntimeError, match=re.escape(str(uninstall_path))):
        adapter.require_no_existing_registration()


def test_existing_registration_preflight_creates_no_run_evidence_or_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    run_uuid = UUID("1" * 32)
    smoke_root = tmp_path / "runs"
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    uninstall_path = tmp_path / "existing-unins000.exe"
    calls: list[list[str]] = []
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: {"UninstallString": str(uninstall_path)},
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 0,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert not smoke_root.exists()
    assert not run_root.exists()
    assert not adapter.user_state_dir.exists()
    assert str(uninstall_path) in capsys.readouterr().err


def test_over_budget_smoke_root_fails_before_registration_state_or_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    payload = _manifest_payload(installer, probe)
    payload_paths = payload["payload_paths"]
    assert isinstance(payload_paths, dict)
    payload_paths["safe_path_budget_chars"] = 10_000
    _write_manifest(manifest, payload)
    smoke_root = tmp_path / ("overlong-" + "x" * 180)
    run_uuid = UUID("3" * 32)
    events: list[str] = []
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: events.append("registration") or None,
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda _command: events.append("runner") or 1,
    )

    assert result == 2
    assert events == []
    assert not smoke_root.exists()
    assert "path budget" in capsys.readouterr().err


def test_compact_run_collision_fails_closed_before_state_or_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("4" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    run_root.mkdir(parents=True)
    marker = run_root / "preserve.txt"
    marker.write_text("existing", encoding="utf-8")
    registrations: list[str] = []
    calls: list[list[str]] = []
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: registrations.append("queried") or None,
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
    )

    assert result == 1
    assert registrations == ["queried"]
    assert calls == []
    assert marker.read_text(encoding="utf-8") == "existing"
    assert not (run_root / "user-state").exists()


def test_invalid_compact_run_name_fails_before_run_root_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        installer_smoke.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex="not-a-uuid-value"),
    )

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
    )

    assert result == 1
    assert calls == []
    assert smoke_root.is_dir()
    assert list(smoke_root.iterdir()) == []


@pytest.mark.parametrize(
    "junction_component",
    [".tmp", "installer-smoke"],
)
def test_smoke_root_rejects_junction_before_outside_write_or_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    junction_component: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("a" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "preserve.txt"
    marker.write_text("keep", encoding="utf-8")
    if junction_component == ".tmp":
        junction = workspace / ".tmp"
    else:
        (workspace / ".tmp").mkdir()
        junction = smoke_root
    _create_directory_junction(junction, outside)
    calls: list[list[str]] = []
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert "link, junction/reparse point" in capsys.readouterr().err
    assert marker.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in outside.iterdir()) == ["preserve.txt"]


@pytest.mark.parametrize(
    "file_component",
    [".tmp", "installer-smoke"],
)
def test_smoke_root_rejects_non_directory_component_before_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    file_component: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("b" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    if file_component == ".tmp":
        blocked_path = workspace / ".tmp"
    else:
        (workspace / ".tmp").mkdir()
        blocked_path = smoke_root
    blocked_path.write_text("preserve", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert "or non-directory" in capsys.readouterr().err
    assert blocked_path.read_text(encoding="utf-8") == "preserve"


def test_smoke_revalidates_exclusive_run_root_before_sentinel_or_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("5" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "preserve.txt"
    marker.write_text("keep", encoding="utf-8")
    calls: list[list[str]] = []
    real_mkdir = Path.mkdir

    def replacing_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        real_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        if path == run_root:
            path.rmdir()
            _create_directory_junction(path, outside)

    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(Path, "mkdir", replacing_mkdir)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert "link, junction/reparse point" in capsys.readouterr().err
    assert marker.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in outside.iterdir()) == ["preserve.txt"]


def _replace_run_root_with_junction(
    run_root: Path,
    user_state_dir: Path,
    outside: Path,
) -> None:
    sentinel = user_state_dir / "sentinel.json"
    if sentinel.exists():
        sentinel.unlink()
    if user_state_dir.exists():
        user_state_dir.rmdir()
    run_root.rmdir()
    _create_directory_junction(run_root, outside)


def test_smoke_revalidates_run_root_after_sentinel_before_install_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("6" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "preserve.txt"
    marker.write_text("keep", encoding="utf-8")
    calls: list[list[str]] = []
    real_write_text = Path.write_text

    def replacing_write_text(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        written = real_write_text(
            path,
            data,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
        if path == adapter.user_state_dir / "sentinel.json":
            _replace_run_root_with_junction(
                run_root,
                adapter.user_state_dir,
                outside,
            )
        return written

    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(Path, "write_text", replacing_write_text)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert marker.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in outside.iterdir()) == ["preserve.txt"]


def test_smoke_rejects_regular_run_root_replacement_before_install_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("8" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    calls: list[list[str]] = []
    real_write_text = Path.write_text

    def replacing_write_text(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        written = real_write_text(
            path,
            data,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )
        if path == adapter.user_state_dir / "sentinel.json":
            path.unlink()
            adapter.user_state_dir.rmdir()
            run_root.rmdir()
            run_root.mkdir()
        return written

    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(Path, "write_text", replacing_write_text)
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 1,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert calls == []
    assert run_root.is_dir()
    assert not (run_root / "user-state" / "sentinel.json").exists()


@pytest.mark.parametrize(
    ("replace_after", "blocked_phase"),
    [
        ("install", "package-launch"),
        ("package-launch", "package-engine"),
        ("package-engine", "package-public-data"),
        ("package-public-data", "repair"),
        ("repair", "downgrade"),
        ("downgrade", "uninstall"),
    ],
)
def test_smoke_revalidates_run_root_before_each_lifecycle_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replace_after: str,
    blocked_phase: str,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("7" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "preserve.txt"
    marker.write_text("keep", encoding="utf-8")
    events: list[str] = []
    phases: list[str] = []
    _patch_recording_adapter(monkeypatch, adapter, events)
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)

    def command_phase(command: list[str]) -> str:
        if command[0] == str(installer.resolve()):
            return (
                "repair"
                if any(item.endswith("repair.log") for item in command)
                else "install"
            )
        if command[0] == str(probe.resolve()):
            return "downgrade"
        if command[0] == str(adapter.uninstaller):
            return "uninstall"
        package_script = Path(command[1]).stem
        return {
            "package_launch_smoke": "package-launch",
            "package_engine_smoke": "package-engine",
            "package_public_data_smoke": "package-public-data",
        }[package_script]

    def runner(command: list[str]) -> int:
        phase = command_phase(command)
        phases.append(phase)
        _write_durable_evidence_for_command(command)
        if phase == replace_after:
            _replace_run_root_with_junction(
                run_root,
                adapter.user_state_dir,
                outside,
            )
        return 7 if phase == "downgrade" else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert phases[-1] == replace_after
    assert blocked_phase not in phases
    assert marker.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in outside.iterdir()) == ["preserve.txt"]


def test_installed_adapter_requires_expected_registration_and_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    for path in (
        adapter.executable,
        adapter.qml_root,
        adapter.uninstaller,
        adapter.start_menu_shortcut,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: {
            "DisplayName": "Modori Installer Smoke",
            "DisplayVersion": "0.1.0",
            "InstallLocation": str(adapter.install_dir),
            "UninstallString": str(adapter.uninstaller),
        },
    )

    adapter.require_installed("0.1.0")


@pytest.mark.parametrize(
    ("registration_update", "message"),
    [
        ({"DisplayName": "Modori"}, "DisplayName"),
        ({"DisplayVersion": "0.0.9"}, "DisplayVersion"),
        ({"InstallLocation": "C:\\outside"}, "escaped"),
    ],
)
def test_installed_adapter_rejects_wrong_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    registration_update: dict[str, str],
    message: str,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    registration = {
        "DisplayName": "Modori Installer Smoke",
        "DisplayVersion": "0.1.0",
        "InstallLocation": str(adapter.install_dir),
        "UninstallString": str(adapter.uninstaller),
    }
    registration.update(registration_update)
    monkeypatch.setattr(
        installer_smoke,
        "read_smoke_registration",
        lambda: registration,
    )

    with pytest.raises(RuntimeError, match=message):
        adapter.require_installed("0.1.0")


def test_repair_and_downgrade_checks_detect_payload_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    adapter.executable.parent.mkdir(parents=True)
    adapter.executable.write_bytes(b"installed")
    checked_versions: list[str] = []
    monkeypatch.setattr(
        adapter,
        "require_installed",
        lambda version: checked_versions.append(version),
    )
    adapter.plant_stale_probe()

    with pytest.raises(RuntimeError, match="stale-file probe"):
        adapter.require_repaired("0.1.0")

    adapter.stale_probe.unlink()
    adapter.require_repaired("0.1.0")
    installed_sha256 = adapter.record_executable_hash()
    adapter.require_downgrade_unchanged("0.1.0", installed_sha256)
    adapter.executable.write_bytes(b"downgraded")

    with pytest.raises(RuntimeError, match="changed the installed executable"):
        adapter.require_downgrade_unchanged("0.1.0", installed_sha256)

    assert checked_versions == ["0.1.0", "0.1.0", "0.1.0", "0.1.0"]


def test_uninstall_waits_for_transient_inno_self_delete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    adapter.uninstaller.parent.mkdir(parents=True)
    adapter.uninstaller.write_bytes(b"inno-first-phase")
    monkeypatch.setattr(installer_smoke, "read_smoke_registration", lambda: None)
    elapsed = 0.0
    sleeps: list[float] = []

    def monotonic() -> float:
        return elapsed

    def sleep(seconds: float) -> None:
        nonlocal elapsed
        sleeps.append(seconds)
        elapsed += seconds
        if len(sleeps) == 2:
            adapter.uninstaller.unlink()
            adapter.install_dir.rmdir()

    monkeypatch.setattr(
        installer_smoke,
        "time",
        SimpleNamespace(monotonic=monotonic, sleep=sleep),
        raising=False,
    )

    adapter.require_uninstalled()

    assert sleeps == [0.05, 0.05]


def test_uninstall_timeout_names_persistent_owned_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    adapter.uninstaller.parent.mkdir(parents=True)
    adapter.uninstaller.write_bytes(b"persistent")
    monkeypatch.setattr(installer_smoke, "read_smoke_registration", lambda: None)
    elapsed = 0.0
    sleeps: list[float] = []

    def monotonic() -> float:
        return elapsed

    def sleep(seconds: float) -> None:
        nonlocal elapsed
        sleeps.append(seconds)
        elapsed += seconds

    monkeypatch.setattr(
        installer_smoke,
        "time",
        SimpleNamespace(monotonic=monotonic, sleep=sleep),
        raising=False,
    )

    with pytest.raises(RuntimeError) as exc_info:
        adapter.require_uninstalled()

    assert str(adapter.uninstaller) in str(exc_info.value)
    assert "10.0 seconds" in str(exc_info.value)
    assert sum(sleeps) == pytest.approx(10.0)
    assert 1 < len(sleeps) <= 201


def test_uninstall_timeout_rejects_unknown_install_root_residual(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    residual = adapter.install_dir / "unexpected-residual.bin"
    residual.parent.mkdir(parents=True)
    residual.write_bytes(b"persistent")
    monkeypatch.setattr(installer_smoke, "read_smoke_registration", lambda: None)
    elapsed = 0.0
    sleeps: list[float] = []

    def monotonic() -> float:
        return elapsed

    def sleep(seconds: float) -> None:
        nonlocal elapsed
        sleeps.append(seconds)
        elapsed += seconds

    monkeypatch.setattr(
        installer_smoke,
        "time",
        SimpleNamespace(monotonic=monotonic, sleep=sleep),
        raising=False,
    )

    with pytest.raises(RuntimeError) as exc_info:
        adapter.require_uninstalled()

    assert str(adapter.install_dir) in str(exc_info.value)
    assert "10.0 seconds" in str(exc_info.value)
    assert sum(sleeps) == pytest.approx(10.0)
    assert 1 < len(sleeps) <= 201


def test_uninstall_timeout_rejects_dangling_install_root_symlink(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    adapter.install_dir.symlink_to(
        tmp_path / "missing-install-target",
        target_is_directory=True,
    )
    assert adapter.install_dir.is_symlink()
    assert not adapter.install_dir.exists()
    monkeypatch.setattr(installer_smoke, "read_smoke_registration", lambda: None)
    elapsed = 0.0
    sleeps: list[float] = []

    def monotonic() -> float:
        return elapsed

    def sleep(seconds: float) -> None:
        nonlocal elapsed
        sleeps.append(seconds)
        elapsed += seconds

    monkeypatch.setattr(
        installer_smoke,
        "time",
        SimpleNamespace(monotonic=monotonic, sleep=sleep),
        raising=False,
    )

    with pytest.raises(RuntimeError) as exc_info:
        adapter.require_uninstalled()

    assert str(adapter.install_dir) in str(exc_info.value)
    assert "10.0 seconds" in str(exc_info.value)
    assert sum(sleeps) == pytest.approx(10.0)


def test_uninstall_check_returns_without_sleep_when_state_is_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    monkeypatch.setattr(installer_smoke, "read_smoke_registration", lambda: None)
    sleeps: list[float] = []
    monkeypatch.setattr(
        installer_smoke,
        "time",
        SimpleNamespace(monotonic=lambda: 0.0, sleep=sleeps.append),
        raising=False,
    )

    adapter.require_uninstalled()

    assert sleeps == []


@pytest.mark.parametrize("missing_name", ["sentinel.json", "cache", "matplotlib"])
def test_user_state_exercised_requires_sentinel_and_routed_directories(
    tmp_path: Path,
    missing_name: str,
) -> None:
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    _write_exercised_user_state(adapter)
    missing_path = adapter.user_state_dir / missing_name
    if missing_path.is_dir():
        missing_path.rmdir()
    else:
        missing_path.unlink()

    with pytest.raises(RuntimeError, match="user state"):
        adapter.require_user_state_exercised()


def test_user_state_cleanup_removes_nested_routed_state_and_preserves_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'a' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    nested_cache = adapter.user_state_dir / "cache" / "charts" / "preview.png"
    nested_cache.parent.mkdir()
    nested_cache.write_bytes(b"chart")
    matplotlib_state = adapter.user_state_dir / "matplotlib" / "fontlist.json"
    matplotlib_state.write_text("{}", encoding="utf-8")
    settings = adapter.user_state_dir / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    log_path = run_root / "install.log"
    log_path.write_text("evidence", encoding="utf-8")

    adapter.verify_and_remove_user_state()

    assert not adapter.user_state_dir.exists()
    assert log_path.read_text(encoding="utf-8") == "evidence"


def test_user_state_cleanup_refuses_escaped_symlink_without_removing_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'b' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    sentinel = adapter.user_state_dir / "sentinel.json"
    outside = tmp_path / "outside-symlink-target"
    outside.mkdir()
    outside_marker = outside / "preserve.txt"
    outside_marker.write_text("keep", encoding="utf-8")
    escaped_link = adapter.user_state_dir / "cache" / "escaped-link"
    try:
        escaped_link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="link or junction/reparse"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()
    assert escaped_link.is_symlink()
    assert outside_marker.read_text(encoding="utf-8") == "keep"


def test_user_state_cleanup_refuses_escaped_junction_without_removing_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'f' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    sentinel = adapter.user_state_dir / "sentinel.json"
    outside = tmp_path / "outside-junction-target"
    outside.mkdir()
    outside_marker = outside / "preserve.txt"
    outside_marker.write_text("keep", encoding="utf-8")
    junction = adapter.user_state_dir / "cache" / "escaped-junction"
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"directory junctions are unavailable: {completed.stderr}")
    assert junction.is_junction()

    with pytest.raises(RuntimeError, match="link or junction/reparse"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()
    assert junction.is_junction()
    assert outside_marker.read_text(encoding="utf-8") == "keep"


def test_user_state_cleanup_rejects_replaced_tmp_ancestor_without_outside_delete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'1' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    original_tmp = workspace / ".tmp-original"
    (workspace / ".tmp").rename(original_tmp)

    outside = tmp_path / "outside-tmp-target"
    outside_run_root = outside / "installer-smoke" / run_root.name
    outside_adapter = installer_smoke.LifecycleAdapter.for_test(outside_run_root)
    _write_exercised_user_state(outside_adapter)
    outside_marker = outside_adapter.user_state_dir / "preserve.txt"
    outside_marker.write_text("keep", encoding="utf-8")
    _create_directory_junction(workspace / ".tmp", outside)

    with pytest.raises(RuntimeError, match="link|junction|reparse|replaced"):
        adapter.verify_and_remove_user_state()

    assert outside_marker.read_text(encoding="utf-8") == "keep"
    assert (outside_adapter.user_state_dir / "sentinel.json").is_file()
    assert (
        original_tmp
        / "installer-smoke"
        / run_root.name
        / "user-state"
        / "sentinel.json"
    ).is_file()


def test_user_state_cleanup_revalidates_boundary_after_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'2' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    outside = tmp_path / "outside-inventory-target"
    outside.mkdir()
    outside_sentinel = outside / "sentinel.json"
    outside_sentinel.write_text("preserve", encoding="utf-8")
    (outside / "cache").mkdir()
    (outside / "matplotlib").mkdir()
    outside_marker = outside / "preserve.txt"
    outside_marker.write_text("keep", encoding="utf-8")
    original_state = run_root / "user-state-original"
    real_inventory = installer_smoke._validated_user_state_inventory

    def replace_after_inventory(*args, **kwargs):
        inventory = real_inventory(*args, **kwargs)
        adapter.user_state_dir.rename(original_state)
        _create_directory_junction(adapter.user_state_dir, outside)
        return inventory

    monkeypatch.setattr(
        installer_smoke,
        "_validated_user_state_inventory",
        replace_after_inventory,
    )

    with pytest.raises(RuntimeError, match="replaced|link|junction|reparse"):
        adapter.verify_and_remove_user_state()

    assert outside_sentinel.read_text(encoding="utf-8") == "preserve"
    assert (outside / "cache").is_dir()
    assert (outside / "matplotlib").is_dir()
    assert outside_marker.read_text(encoding="utf-8") == "keep"


def test_user_state_cleanup_refuses_a_directory_outside_the_run_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'c' * 12}"
    run_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    adapter = installer_smoke.LifecycleAdapter(
        install_dir=run_root / "install",
        user_state_dir=outside,
        start_menu_shortcut=run_root / "shortcut.lnk",
    )
    _write_exercised_user_state(adapter)
    sentinel = outside / "sentinel.json"

    with pytest.raises(RuntimeError, match="escaped the smoke run root"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()


@pytest.mark.parametrize(
    "run_root_kind",
    [
        "outside-smoke-root",
        "non-uuid-root",
    ],
)
def test_user_state_cleanup_requires_a_uuid_root_below_smoke_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run_root_kind: str,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    smoke_root.mkdir(parents=True)
    run_root = (
        tmp_path / "outside" / f"r-{'d' * 12}"
        if run_root_kind == "outside-smoke-root"
        else smoke_root / "r-not-a-uuid"
    )
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    sentinel = adapter.user_state_dir / "sentinel.json"

    with pytest.raises(RuntimeError, match="UUID child of the smoke root"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()


def test_user_state_cleanup_requires_the_original_sentinel_contents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'e' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    _write_exercised_user_state(adapter)
    sentinel = adapter.user_state_dir / "sentinel.json"
    sentinel.write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="contents changed"):
        adapter.verify_and_remove_user_state()

    assert sentinel.read_text(encoding="utf-8") == "changed"


def test_smoke_repairs_stale_file_rejects_downgrade_and_uninstalls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    run_uuid = UUID("2" * 32)
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    timeline: list[str | tuple[str, ...]] = []
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)
    monkeypatch.setattr(
        adapter,
        "require_no_existing_registration",
        lambda: timeline.append("preflight"),
    )
    monkeypatch.setattr(
        adapter,
        "require_installed",
        lambda _version: timeline.append("installed"),
    )
    monkeypatch.setattr(
        adapter,
        "require_user_state_exercised",
        lambda: timeline.append("state-exercised"),
        raising=False,
    )
    monkeypatch.setattr(
        adapter,
        "plant_stale_probe",
        lambda: timeline.append("plant"),
    )
    monkeypatch.setattr(
        adapter,
        "require_repaired",
        lambda _version: timeline.append("repaired"),
    )

    def record_hash() -> str:
        timeline.append("record-hash")
        return "A" * 64

    monkeypatch.setattr(adapter, "record_executable_hash", record_hash)
    monkeypatch.setattr(
        adapter,
        "require_downgrade_unchanged",
        lambda _version, _sha: timeline.append("unchanged"),
    )
    monkeypatch.setattr(
        adapter,
        "require_uninstalled",
        lambda: timeline.append("uninstalled"),
    )
    real_state_cleanup = adapter.verify_and_remove_user_state

    def verify_and_remove_real_state(
        run_boundary: installer_smoke._SmokeRunBoundary | None = None,
    ) -> None:
        timeline.append("state-cleanup")
        real_state_cleanup(run_boundary)

    monkeypatch.setattr(
        adapter,
        "verify_and_remove_user_state",
        verify_and_remove_real_state,
    )

    def runner(command: list[str]) -> int:
        timeline.append(tuple(command))
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        if len(command) > 1 and command[1].endswith("package_engine_smoke.py"):
            (adapter.user_state_dir / "cache").mkdir(exist_ok=True)
        _write_durable_evidence_for_command(command)
        log_argument = next(
            (item for item in command if item.startswith("/LOG=")),
            None,
        )
        if log_argument is not None:
            Path(log_argument[5:]).write_text("preserved-log", encoding="utf-8")
        return 7 if command[0] == str(probe.resolve()) else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 0
    install_command = tuple(
        installer_smoke.setup_command(
            installer,
            adapter.install_dir,
            run_root / "install.log",
        )
    )
    repair_command = tuple(
        installer_smoke.setup_command(
            installer,
            adapter.install_dir,
            run_root / "repair.log",
        )
    )
    downgrade_command = tuple(
        installer_smoke.setup_command(
            probe,
            adapter.install_dir,
            run_root / "downgrade.log",
        )
    )
    launch_command = (
        sys.executable,
        "scripts/package_launch_smoke.py",
        str(adapter.executable),
        "--state-root",
        str(adapter.user_state_dir.resolve()),
    )
    engine_command = (
        sys.executable,
        "scripts/package_engine_smoke.py",
        str(adapter.executable),
        "--state-root",
        str(adapter.user_state_dir.resolve()),
        "--evidence-dir",
        str((run_root / "engine-smoke").resolve()),
    )
    public_data_command = (
        sys.executable,
        "scripts/package_public_data_smoke.py",
        str(adapter.executable),
        "--state-root",
        str(adapter.user_state_dir.resolve()),
        "--evidence-dir",
        str((run_root / "public-data-smoke").resolve()),
        "--fixture-dir",
        str(installer_smoke.WORKSPACE / "tests" / "fixtures" / "public_data_formats"),
    )
    uninstall_command = (
        str(adapter.uninstaller),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        f"/LOG={(run_root / 'uninstall.log').resolve()}",
    )
    assert timeline == [
        "preflight",
        install_command,
        "installed",
        launch_command,
        engine_command,
        public_data_command,
        "state-exercised",
        "plant",
        repair_command,
        "repaired",
        "record-hash",
        downgrade_command,
        "unchanged",
        uninstall_command,
        "uninstalled",
        "state-cleanup",
        "state-exercised",
    ]
    assert adapter.install_dir == run_root / "install"
    assert not (adapter.user_state_dir / "sentinel.json").exists()
    assert not adapter.user_state_dir.exists()
    assert run_root.is_dir()
    assert sorted(path.name for path in run_root.iterdir()) == [
        "downgrade.log",
        "engine-smoke",
        "install.log",
        "public-data-smoke",
        "repair.log",
        "uninstall.log",
    ]
    assert sorted(path.name for path in (run_root / "engine-smoke").iterdir()) == [
        "reference.xlsx",
        "result.json",
    ]
    assert sorted(path.name for path in (run_root / "public-data-smoke").iterdir()) == [
        "result.json"
    ]
    assert all(
        (run_root / name).read_text(encoding="utf-8") == "preserved-log"
        for name in (
            "install.log",
            "repair.log",
            "downgrade.log",
            "uninstall.log",
        )
    )


def test_lifecycle_rejects_successful_engine_command_without_created_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, _smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path / "adapter")
    calls: list[list[str]] = []
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)
    monkeypatch.setattr(adapter, "require_installed", lambda _version: None)

    def runner(command: list[str]) -> int:
        calls.append(command)
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        _write_durable_evidence_for_command(command)
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert "Smoke user state directory is missing" in capsys.readouterr().err
    assert not (adapter.user_state_dir / "cache").exists()
    assert (adapter.user_state_dir / "matplotlib").is_dir()
    assert not adapter.stale_probe.exists()
    assert sum(call[0] == str(installer.resolve()) for call in calls) == 1
    assert {
        Path(call[1]).name
        for call in calls
        if len(call) > 1 and call[1].startswith("scripts/package_")
    } == {
        "package_launch_smoke.py",
        "package_engine_smoke.py",
        "package_public_data_smoke.py",
    }


def test_lifecycle_rejects_missing_durable_engine_evidence_before_public_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("8" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    events: list[str] = []
    calls: list[list[str]] = []
    _patch_recording_adapter(monkeypatch, adapter, events)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)

    def runner(command: list[str]) -> int:
        calls.append(command)
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        if len(command) > 1 and command[1].endswith("package_engine_smoke.py"):
            (adapter.user_state_dir / "cache").mkdir(exist_ok=True)
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events == ["preflight", "installed"]
    assert any(
        len(call) > 1 and call[1].endswith("package_engine_smoke.py") for call in calls
    )
    assert not any(
        len(call) > 1 and call[1].endswith("package_public_data_smoke.py")
        for call in calls
    )
    assert all(not any(item.endswith("repair.log") for item in call) for call in calls)
    assert "durable smoke evidence" in capsys.readouterr().err.lower()


def test_lifecycle_rejects_malformed_durable_engine_evidence_before_public_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("6" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    events: list[str] = []
    calls: list[list[str]] = []
    _patch_recording_adapter(monkeypatch, adapter, events)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)

    def runner(command: list[str]) -> int:
        calls.append(command)
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        if len(command) > 1 and command[1].endswith("package_engine_smoke.py"):
            (adapter.user_state_dir / "cache").mkdir(exist_ok=True)
            evidence_dir = Path(command[command.index("--evidence-dir") + 1])
            (evidence_dir / "reference.xlsx").write_bytes(b"xlsx-evidence")
            (evidence_dir / "result.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "v1_statistics_smoke": {"ok": False},
                    }
                ),
                encoding="utf-8",
            )
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events == ["preflight", "installed"]
    assert not any(
        len(call) > 1 and call[1].endswith("package_public_data_smoke.py")
        for call in calls
    )
    assert "engine wrapper contract" in capsys.readouterr().err


def test_lifecycle_rejects_wrapper_incompatible_public_evidence_before_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("3" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    events: list[str] = []
    _patch_recording_adapter(monkeypatch, adapter, events)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)

    def runner(command: list[str]) -> int:
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        if len(command) > 1 and command[1].endswith("package_engine_smoke.py"):
            (adapter.user_state_dir / "cache").mkdir(exist_ok=True)
        _write_durable_evidence_for_command(command)
        if len(command) > 1 and command[1].endswith("package_public_data_smoke.py"):
            evidence_dir = Path(command[command.index("--evidence-dir") + 1])
            (evidence_dir / "result.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "case_count": 1,
                        "cases": [{"name": "fixture", "ok": True}],
                    }
                ),
                encoding="utf-8",
            )
        return 7 if command[0] == str(probe.resolve()) else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events == ["preflight", "installed"]
    assert "hardened public-data contract" in capsys.readouterr().err


def test_lifecycle_revalidates_durable_evidence_after_uninstall_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_uuid = UUID("4" * 32)
    run_root = smoke_root / f"r-{run_uuid.hex[:12]}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    events: list[str] = []
    _patch_recording_adapter(monkeypatch, adapter, events)
    monkeypatch.setattr(installer_smoke.uuid, "uuid4", lambda: run_uuid)

    def runner(command: list[str]) -> int:
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            (adapter.user_state_dir / "matplotlib").mkdir(exist_ok=True)
        if len(command) > 1 and command[1].endswith("package_engine_smoke.py"):
            (adapter.user_state_dir / "cache").mkdir(exist_ok=True)
        _write_durable_evidence_for_command(command)
        if command[0] == str(adapter.uninstaller):
            (run_root / "engine-smoke" / "result.json").write_text(
                json.dumps({"ok": False, "last_error": "tampered"}),
                encoding="utf-8",
            )
        return 7 if command[0] == str(probe.resolve()) else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events[-2:] == ["uninstalled", "state-preserved"]
    assert "durable engine smoke evidence" in capsys.readouterr().err.lower()


@pytest.mark.parametrize("injection_read", [1, 3])
def test_durable_evidence_reinventories_after_reading_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    injection_read: int,
) -> None:
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'5' * 12}"
    run_root.mkdir(parents=True)
    run_boundary = installer_smoke._SmokeRunBoundary.capture(run_root)
    evidence = installer_smoke._SmokeEvidenceBoundary.create(
        run_boundary,
        installer_smoke._ENGINE_EVIDENCE_DIRECTORY,
    )
    (evidence.directory / "reference.xlsx").write_bytes(b"xlsx-evidence")
    (evidence.directory / "result.json").write_text(
        json.dumps(
            {
                "ok": True,
                "cache_dir": "cache",
                "v1_statistics_smoke": {"ok": True},
            }
        ),
        encoding="utf-8",
    )
    real_read_bytes = Path.read_bytes
    injected = False
    read_count = 0

    def add_extra_entry_after_read(path: Path) -> bytes:
        nonlocal injected, read_count
        data = real_read_bytes(path)
        if path.parent == evidence.directory:
            read_count += 1
        if read_count == injection_read and not injected:
            (evidence.directory / "unexpected.bin").write_bytes(b"unexpected")
            injected = True
        return data

    monkeypatch.setattr(Path, "read_bytes", add_extra_entry_after_read)

    with pytest.raises(RuntimeError, match="inventory mismatch"):
        evidence.require_exact_files(installer_smoke._ENGINE_EVIDENCE_FILES)

    assert injected is True


def test_lifecycle_passes_swapped_state_root_lexically_without_following(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    run_root = smoke_root / f"r-{'9' * 12}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    outside = tmp_path / "outside-state"
    calls: list[list[str]] = []
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)

    def replace_user_state(_version: str) -> None:
        (adapter.user_state_dir / "sentinel.json").unlink()
        adapter.user_state_dir.rmdir()
        outside.mkdir()
        try:
            adapter.user_state_dir.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks are unavailable: {exc}")

    monkeypatch.setattr(adapter, "require_installed", replace_user_state)

    def runner(command: list[str]) -> int:
        calls.append(command)
        if len(command) > 1 and command[1].endswith("package_launch_smoke.py"):
            return 9
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    launch_command = next(
        call
        for call in calls
        if len(call) > 1 and call[1].endswith("package_launch_smoke.py")
    )
    state_argument = launch_command[launch_command.index("--state-root") + 1]
    lexical_state = str(Path(os.path.abspath(adapter.user_state_dir)))
    assert result == 1
    assert state_argument == lexical_state
    assert state_argument != str(outside.resolve())
    assert list(outside.iterdir()) == []


def test_successful_downgrade_probe_is_a_lifecycle_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    events: list[str] = []
    calls: list[list[str]] = []
    _patch_smoke_workspace(monkeypatch, tmp_path)
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    _patch_recording_adapter(monkeypatch, adapter, events)

    def runner(command: list[str]) -> int:
        calls.append(command)
        _write_durable_evidence_for_command(command)
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events == [
        "preflight",
        "installed",
        "state-exercised",
        "planted",
        "repaired",
    ]
    assert calls[-1][0] == str(probe.resolve())
    assert all(call[0] != str(adapter.uninstaller) for call in calls)


def test_lifecycle_failure_preserves_logs_and_user_state_for_diagnosis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(
        tmp_path,
        longest_relative_path="Modori.exe",
    )
    _workspace, smoke_root = _patch_smoke_workspace(monkeypatch, tmp_path)
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path / "adapter")
    monkeypatch.setattr(adapter, "require_no_existing_registration", lambda: None)
    monkeypatch.setattr(
        adapter,
        "require_installed",
        lambda _version: (_ for _ in ()).throw(RuntimeError("missing installed EXE")),
    )

    def runner(command: list[str]) -> int:
        log_argument = next(
            (item for item in command if item.startswith("/LOG=")),
            None,
        )
        if log_argument is not None:
            log_path = Path(log_argument[5:])
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("diagnostic", encoding="utf-8")
        return 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    run_roots = list(smoke_root.glob("r-*"))
    assert result == 1
    assert len(run_roots) == 1
    assert (run_roots[0] / "install.log").read_text(encoding="utf-8") == "diagnostic"
    assert (adapter.user_state_dir / "sentinel.json").is_file()


def test_run_command_uses_workspace_without_raising_on_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        observed.update(command=command, cwd=cwd, check=check)
        return subprocess.CompletedProcess(command, 9)

    monkeypatch.setattr(installer_smoke.subprocess, "run", fake_run)

    assert installer_smoke.run_command(["setup.exe"]) == 9
    assert observed == {
        "command": ["setup.exe"],
        "cwd": installer_smoke.WORKSPACE,
        "check": False,
    }


def test_main_passes_cli_paths_to_lifecycle_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[Path, Path, Path]] = []

    def fake_smoke(installer: Path, manifest: Path, probe: Path) -> int:
        observed.append((installer, manifest, probe))
        return 7

    monkeypatch.setattr(installer_smoke, "run_installer_smoke", fake_smoke)

    result = installer_smoke.main(
        [
            "smoke.exe",
            "--manifest",
            "smoke.json",
            "--downgrade-probe",
            "probe.exe",
        ]
    )

    assert result == 7
    assert observed == [(Path("smoke.exe"), Path("smoke.json"), Path("probe.exe"))]
