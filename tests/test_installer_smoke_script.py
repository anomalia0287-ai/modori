from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import pytest

from scripts import installer_smoke
from scripts.installer_contract import (
    DOWNGRADE_PROBE_VERSION,
    PRODUCTION_APP_ID,
    SMOKE_APP_ID,
    sha256_file,
)


def _manifest_payload(installer: Path, probe: Path) -> dict[str, Any]:
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
    }


def _manifest(
    path: Path,
    installer: Path,
    probe: Path,
    *,
    app_id: str = SMOKE_APP_ID,
) -> dict[str, Any]:
    payload = _manifest_payload(installer, probe)
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


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    installer = tmp_path / "smoke.exe"
    probe = tmp_path / "probe.exe"
    manifest = tmp_path / "manifest.json"
    installer.write_bytes(b"smoke")
    probe.write_bytes(b"probe")
    _manifest(manifest, installer, probe)
    return installer, manifest, probe


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
        lambda: events.append("state-preserved"),
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

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 0,
    )

    assert result == 2
    assert calls == []
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


def test_real_adapter_keeps_install_and_user_state_in_separate_run_subtrees(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    run_root = tmp_path / "runs" / f"run-{'a' * 32}"

    adapter = installer_smoke.LifecycleAdapter.for_real_run(run_root)

    assert adapter.install_dir == run_root / "install"
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


def test_user_state_cleanup_removes_only_the_sentinel_and_empty_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    run_root = smoke_root / f"run-{'a' * 32}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    adapter.user_state_dir.mkdir(parents=True)
    sentinel = adapter.user_state_dir / "sentinel.json"
    sentinel.write_text("preserve", encoding="utf-8")
    log_path = run_root / "install.log"
    log_path.write_text("evidence", encoding="utf-8")

    adapter.verify_and_remove_user_state()

    assert not sentinel.exists()
    assert not adapter.user_state_dir.exists()
    assert log_path.read_text(encoding="utf-8") == "evidence"


def test_user_state_cleanup_refuses_extra_state_without_removing_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    run_root = smoke_root / f"run-{'b' * 32}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    adapter.user_state_dir.mkdir(parents=True)
    sentinel = adapter.user_state_dir / "sentinel.json"
    extra_state = adapter.user_state_dir / "unexpected.json"
    sentinel.write_text("preserve", encoding="utf-8")
    extra_state.write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unexpected files"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()
    assert extra_state.is_file()


def test_user_state_cleanup_refuses_a_directory_outside_the_run_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    run_root = smoke_root / f"run-{'c' * 32}"
    outside = tmp_path / "outside"
    adapter = installer_smoke.LifecycleAdapter(
        install_dir=run_root / "install",
        user_state_dir=outside,
        start_menu_shortcut=run_root / "shortcut.lnk",
    )
    outside.mkdir()
    sentinel = outside / "sentinel.json"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(RuntimeError, match="escaped the smoke run root"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()


@pytest.mark.parametrize(
    "run_root",
    [
        Path("outside") / f"run-{'d' * 32}",
        Path("runs") / "run-not-a-uuid",
    ],
    ids=["outside-smoke-root", "non-uuid-root"],
)
def test_user_state_cleanup_requires_a_uuid_root_below_smoke_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run_root: Path,
) -> None:
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path / run_root)
    adapter.user_state_dir.mkdir(parents=True)
    sentinel = adapter.user_state_dir / "sentinel.json"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(RuntimeError, match="UUID child of the smoke root"):
        adapter.verify_and_remove_user_state()

    assert sentinel.is_file()


def test_user_state_cleanup_requires_the_original_sentinel_contents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
    run_root = smoke_root / f"run-{'e' * 32}"
    adapter = installer_smoke.LifecycleAdapter.for_test(run_root)
    adapter.user_state_dir.mkdir(parents=True)
    sentinel = adapter.user_state_dir / "sentinel.json"
    sentinel.write_text("changed", encoding="utf-8")

    with pytest.raises(RuntimeError, match="contents changed"):
        adapter.verify_and_remove_user_state()

    assert sentinel.read_text(encoding="utf-8") == "changed"


def test_smoke_repairs_stale_file_rejects_downgrade_and_uninstalls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    calls: list[list[str]] = []
    events: list[str] = []

    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", tmp_path / "runs")
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    _patch_recording_adapter(monkeypatch, adapter, events)

    def runner(command: list[str]) -> int:
        calls.append(command)
        return 7 if command[0] == str(probe.resolve()) else 0

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=runner,
        lifecycle_adapter=adapter,
    )

    assert result == 0
    assert events == [
        "preflight",
        "installed",
        "planted",
        "repaired",
        "downgrade-rejected",
        "uninstalled",
        "state-preserved",
    ]
    assert calls[1:4] == [
        [
            sys.executable,
            "scripts/package_launch_smoke.py",
            str(adapter.executable),
        ],
        [
            sys.executable,
            "scripts/package_engine_smoke.py",
            str(adapter.executable),
        ],
        [
            sys.executable,
            "scripts/package_public_data_smoke.py",
            str(adapter.executable),
            "--fixture-dir",
            str(
                installer_smoke.WORKSPACE
                / "tests"
                / "fixtures"
                / "public_data_formats"
            ),
        ],
    ]
    assert [call[0] for call in calls].count(str(installer.resolve())) == 2
    assert calls[5][0] == str(probe.resolve())
    install_log = next(item[5:] for item in calls[0] if item.startswith("/LOG="))
    repair_log = next(item[5:] for item in calls[4] if item.startswith("/LOG="))
    downgrade_log = next(item[5:] for item in calls[5] if item.startswith("/LOG="))
    run_root = Path(install_log).parent
    assert re.fullmatch(r"run-[0-9a-f]{32}", run_root.name)
    assert Path(repair_log) == run_root / "repair.log"
    assert Path(downgrade_log) == run_root / "downgrade.log"
    assert f"/DIR={adapter.install_dir.resolve()}" in calls[0]
    assert calls[6] == [
        str(adapter.uninstaller),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        f"/LOG={(run_root / 'uninstall.log').resolve()}",
    ]


def test_successful_downgrade_probe_is_a_lifecycle_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    events: list[str] = []
    calls: list[list[str]] = []
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", tmp_path / "runs")
    adapter = installer_smoke.LifecycleAdapter.for_test(tmp_path)
    _patch_recording_adapter(monkeypatch, adapter, events)

    result = installer_smoke.run_installer_smoke(
        installer,
        manifest,
        probe,
        runner=lambda command: calls.append(command) or 0,
        lifecycle_adapter=adapter,
    )

    assert result == 1
    assert events == ["preflight", "installed", "planted", "repaired"]
    assert calls[-1][0] == str(probe.resolve())
    assert all(call[0] != str(adapter.uninstaller) for call in calls)


def test_lifecycle_failure_preserves_logs_and_user_state_for_diagnosis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    installer, manifest, probe = _inputs(tmp_path)
    smoke_root = tmp_path / "runs"
    monkeypatch.setattr(installer_smoke, "SMOKE_ROOT", smoke_root)
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

    run_roots = list(smoke_root.glob("run-*"))
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
    assert observed == [
        (Path("smoke.exe"), Path("smoke.json"), Path("probe.exe"))
    ]
