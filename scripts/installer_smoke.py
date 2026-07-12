from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
import winreg
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from scripts.installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        SMOKE_APP_ID,
        sha256_file,
    )
else:
    from installer_contract import (  # type: ignore[import-not-found]
        DOWNGRADE_PROBE_VERSION,
        SMOKE_APP_ID,
        sha256_file,
    )

WORKSPACE = Path(__file__).resolve().parents[1]
SMOKE_ROOT = WORKSPACE / ".tmp" / "installer-smoke"
UNINSTALL_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_RUN_ROOT_PATTERN = re.compile(r"^run-[0-9a-f]{32}$")


def uninstall_key(app_id: str = SMOKE_APP_ID) -> str:
    return f"{UNINSTALL_ROOT}\\{app_id}_is1"


def read_smoke_registration() -> dict[str, str] | None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_key())
    except FileNotFoundError:
        return None

    with key:
        registration: dict[str, str] = {}
        for name in (
            "DisplayName",
            "DisplayVersion",
            "InstallLocation",
            "UninstallString",
        ):
            try:
                registration[name] = str(winreg.QueryValueEx(key, name)[0])
            except FileNotFoundError:
                registration[name] = ""
        return registration


def run_command(command: list[str]) -> int:
    return subprocess.run(command, cwd=WORKSPACE, check=False).returncode


@dataclass
class LifecycleAdapter:
    install_dir: Path
    user_state_dir: Path
    start_menu_shortcut: Path

    @classmethod
    def for_real_run(cls, root: Path) -> LifecycleAdapter:
        return cls(
            install_dir=root / "install",
            user_state_dir=root / "user-state",
            start_menu_shortcut=(
                Path(os.environ["APPDATA"])
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Modori Installer Smoke.lnk"
            ),
        )

    @classmethod
    def for_test(cls, root: Path) -> LifecycleAdapter:
        return cls(root / "install", root / "user-state", root / "shortcut.lnk")

    @property
    def executable(self) -> Path:
        return self.install_dir / "Modori" / "Modori.exe"

    @property
    def stale_probe(self) -> Path:
        return self.install_dir / "Modori" / "orphan-stale-probe.bin"

    @property
    def uninstaller(self) -> Path:
        return self.install_dir / "unins000.exe"

    @property
    def qml_root(self) -> Path:
        return (
            self.install_dir
            / "Modori"
            / "_internal"
            / "modori"
            / "ui"
            / "qml"
            / "Main.qml"
        )

    def require_no_existing_registration(self) -> None:
        registration = read_smoke_registration()
        if registration is not None:
            uninstall_path = registration.get("UninstallString") or "unknown uninstaller"
            raise RuntimeError(
                "An existing Modori Installer Smoke registration must be removed "
                f"first: {uninstall_path}"
            )

    def require_installed(self, expected_version: str) -> None:
        registration = read_smoke_registration()
        if registration is None:
            raise RuntimeError("Smoke uninstall registration was not created")
        if registration.get("DisplayName") != "Modori Installer Smoke":
            raise RuntimeError("Unexpected smoke DisplayName")
        if registration.get("DisplayVersion") != expected_version:
            raise RuntimeError("Unexpected smoke DisplayVersion")
        install_location = Path(registration.get("InstallLocation", "")).resolve()
        if install_location != self.install_dir.resolve():
            raise RuntimeError("Smoke InstallLocation escaped the isolated directory")
        if not self.executable.is_file() or not self.qml_root.is_file():
            raise RuntimeError("Installed executable or QML root is missing")
        if not self.uninstaller.is_file() or not self.start_menu_shortcut.is_file():
            raise RuntimeError("Uninstaller or smoke shortcut is missing")

    def plant_stale_probe(self) -> None:
        self.stale_probe.write_bytes(b"must be removed by InstallDelete")

    def require_repaired(self, expected_version: str) -> None:
        self.require_installed(expected_version)
        if self.stale_probe.exists():
            raise RuntimeError("Repair left the stale-file probe installed")

    def record_executable_hash(self) -> str:
        return sha256_file(self.executable)

    def require_downgrade_unchanged(
        self,
        expected_version: str,
        expected_sha256: str,
    ) -> None:
        self.require_installed(expected_version)
        if sha256_file(self.executable) != expected_sha256:
            raise RuntimeError("Downgrade attempt changed the installed executable")

    def require_uninstalled(self) -> None:
        if read_smoke_registration() is not None:
            raise RuntimeError("Smoke uninstall registration remains")
        if (
            (self.install_dir / "Modori").exists()
            or self.uninstaller.exists()
            or self.start_menu_shortcut.exists()
        ):
            raise RuntimeError("Smoke installer-owned files remain")

    def verify_and_remove_user_state(self) -> None:
        sentinel = self.user_state_dir / "sentinel.json"
        resolved_smoke_root = SMOKE_ROOT.resolve()
        resolved_run_root = self.install_dir.resolve().parent
        resolved_user_state = self.user_state_dir.resolve()
        resolved_sentinel = sentinel.resolve()
        if (
            resolved_run_root.parent != resolved_smoke_root
            or _RUN_ROOT_PATTERN.fullmatch(resolved_run_root.name) is None
        ):
            raise RuntimeError("Smoke run root is not a UUID child of the smoke root")
        if resolved_user_state.parent != resolved_run_root:
            raise RuntimeError("Smoke user-state directory escaped the smoke run root")
        if resolved_user_state not in resolved_sentinel.parents or not sentinel.is_file():
            raise RuntimeError("Smoke user-state sentinel was not preserved")
        if sentinel.read_bytes() != b"preserve":
            raise RuntimeError("Smoke user-state sentinel contents changed")
        if set(self.user_state_dir.iterdir()) != {sentinel}:
            raise RuntimeError("Smoke user-state directory contains unexpected files")
        sentinel.unlink()
        self.user_state_dir.rmdir()


def validate_inputs(
    installer: Path,
    manifest_path: Path,
    probe: Path,
) -> dict[str, object]:
    decoded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Installer smoke manifest must be a JSON object")

    payload: dict[str, object] = decoded
    installer_payload = payload.get("installer")
    probe_payload = payload.get("downgrade_probe")
    version = payload.get("version")
    if (
        payload.get("channel") != "internal-smoke"
        or payload.get("app_id") != SMOKE_APP_ID
        or payload.get("smoke_only") is not True
        or not isinstance(version, str)
        or _VERSION_PATTERN.fullmatch(version) is None
        or not isinstance(installer_payload, dict)
        or not isinstance(probe_payload, dict)
        or probe_payload.get("version") != DOWNGRADE_PROBE_VERSION
    ):
        raise ValueError("Installer smoke input is not isolated smoke evidence")
    if (
        installer_payload.get("filename") != installer.name
        or installer_payload.get("sha256") != sha256_file(installer)
    ):
        raise ValueError(
            "Smoke installer identity or SHA256 does not match its manifest"
        )
    if (
        probe_payload.get("filename") != probe.name
        or probe_payload.get("sha256") != sha256_file(probe)
    ):
        raise ValueError(
            "Downgrade probe identity or SHA256 does not match its manifest"
        )
    return payload


def setup_command(installer: Path, install_dir: Path, log_path: Path) -> list[str]:
    return [
        str(installer.resolve()),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOFORCECLOSEAPPLICATIONS",
        "/NORESTARTAPPLICATIONS",
        f"/DIR={install_dir.resolve()}",
        f"/LOG={log_path.resolve()}",
    ]


def run_installer_smoke(
    installer: Path,
    manifest_path: Path,
    probe: Path,
    *,
    runner: Callable[[list[str]], int] = run_command,
    lifecycle_adapter: LifecycleAdapter | None = None,
) -> int:
    try:
        installer = installer.resolve()
        manifest_path = manifest_path.resolve()
        probe = probe.resolve()
        payload = validate_inputs(installer, manifest_path, probe)
        version = str(payload["version"])
        run_root = SMOKE_ROOT / f"run-{uuid.uuid4().hex}"
        run_root.mkdir(parents=True)
        adapter = lifecycle_adapter or LifecycleAdapter.for_real_run(run_root)
        adapter.require_no_existing_registration()
        adapter.user_state_dir.mkdir(parents=True)
        (adapter.user_state_dir / "sentinel.json").write_text(
            "preserve",
            encoding="utf-8",
        )
        print(
            "installer-smoke-mutation: creating isolated current-user registration "
            f"{SMOKE_APP_ID} under {adapter.install_dir}"
        )

        install_log = run_root / "install.log"
        if runner(setup_command(installer, adapter.install_dir, install_log)) != 0:
            raise RuntimeError("Smoke installer returned nonzero")
        adapter.require_installed(version)

        package_smoke_commands = [
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
                    WORKSPACE
                    / "tests"
                    / "fixtures"
                    / "public_data_formats"
                ),
            ],
        ]
        for command in package_smoke_commands:
            if runner(command) != 0:
                raise RuntimeError(
                    f"Installed package smoke failed: {' '.join(command)}"
                )

        adapter.plant_stale_probe()
        repair_log = run_root / "repair.log"
        if runner(setup_command(installer, adapter.install_dir, repair_log)) != 0:
            raise RuntimeError("Repair installer returned nonzero")
        adapter.require_repaired(version)

        installed_sha256 = adapter.record_executable_hash()
        downgrade_log = run_root / "downgrade.log"
        downgrade_result = runner(
            setup_command(probe, adapter.install_dir, downgrade_log)
        )
        if downgrade_result == 0:
            raise RuntimeError("Downgrade probe unexpectedly succeeded")
        adapter.require_downgrade_unchanged(version, installed_sha256)

        uninstall_command = [
            str(adapter.uninstaller),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/LOG={(run_root / 'uninstall.log').resolve()}",
        ]
        if runner(uninstall_command) != 0:
            raise RuntimeError("Smoke uninstaller returned nonzero")
        adapter.require_uninstalled()
        adapter.verify_and_remove_user_state()
    except (
        FileNotFoundError,
        KeyError,
        OSError,
        RuntimeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"installer-smoke-failed: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, (ValueError, json.JSONDecodeError)) else 1
    print(f"installer-smoke-ok: {run_root}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the isolated Modori installer lifecycle."
    )
    parser.add_argument("installer")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--downgrade-probe", required=True)
    args = parser.parse_args(argv)
    return run_installer_smoke(
        Path(args.installer),
        Path(args.manifest),
        Path(args.downgrade_probe),
    )


if __name__ == "__main__":
    raise SystemExit(main())
