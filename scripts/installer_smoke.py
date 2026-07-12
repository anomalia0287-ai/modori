from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
import uuid
import winreg
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

if __package__:
    from scripts.installer_contract import (
        DOWNGRADE_PROBE_VERSION,
        SAFE_PATH_BUDGET_CHARS,
        SMOKE_APP_ID,
        sha256_file,
    )
else:
    from installer_contract import (  # type: ignore[import-not-found]
        DOWNGRADE_PROBE_VERSION,
        SAFE_PATH_BUDGET_CHARS,
        SMOKE_APP_ID,
        sha256_file,
    )

WORKSPACE = Path(__file__).resolve().parents[1]
SMOKE_ROOT = WORKSPACE / ".tmp" / "installer-smoke"
UNINSTALL_ROOT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_RUN_ROOT_PATTERN = re.compile(r"^r-[0-9a-f]{12}$")
_UNINSTALL_POLL_INTERVAL_SECONDS = 0.05
# Inno 6.7.3's second phase completed about 1.1 seconds after signaling the
# first phase; keep the condition wait finite with ample evidence-safe margin.
_UNINSTALL_WAIT_TIMEOUT_SECONDS = 10.0
_REPARSE_POINT_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_link_or_junction(path: Path) -> bool:
    try:
        is_junction = getattr(path, "is_junction", None)
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return (
            path.is_symlink()
            or bool(is_junction and is_junction())
            or bool(attributes & _REPARSE_POINT_ATTRIBUTE)
        )
    except OSError:
        return True


def _path_entry_exists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _validated_user_state_inventory(
    user_state_dir: Path,
    resolved_user_state: Path,
) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    directories: list[Path] = []
    pending = [user_state_dir]
    while pending:
        directory = pending.pop()
        try:
            descendants = list(directory.iterdir())
        except OSError as exc:
            raise RuntimeError(
                f"Smoke user-state directory could not be inspected: {directory}"
            ) from exc
        for descendant in descendants:
            if _is_link_or_junction(descendant):
                raise RuntimeError(
                    "Smoke user-state descendant is a link or junction/reparse "
                    f"point: {descendant}"
                )
            try:
                resolved_descendant = descendant.resolve(strict=True)
                is_directory = descendant.is_dir()
                is_file = descendant.is_file()
            except OSError as exc:
                raise RuntimeError(
                    f"Smoke user-state descendant could not be validated: {descendant}"
                ) from exc
            if resolved_user_state not in resolved_descendant.parents:
                raise RuntimeError(
                    f"Smoke user-state descendant escaped its root: {descendant}"
                )
            if is_directory:
                directories.append(descendant)
                pending.append(descendant)
            elif is_file:
                files.append(descendant)
            else:
                raise RuntimeError(
                    f"Smoke user-state descendant has an unsupported type: {descendant}"
                )
    return files, directories


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
            install_dir=root / "i",
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

    def require_user_state_exercised(self) -> None:
        sentinel = self.user_state_dir / "sentinel.json"
        if not sentinel.is_file():
            raise RuntimeError("Smoke user state sentinel is missing")
        if sentinel.read_bytes() != b"preserve":
            raise RuntimeError("Smoke user state sentinel contents changed")
        for name in ("cache", "matplotlib"):
            path = self.user_state_dir / name
            if not path.is_dir():
                raise RuntimeError(f"Smoke user state directory is missing: {path}")

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
        deadline = time.monotonic() + _UNINSTALL_WAIT_TIMEOUT_SECONDS
        while True:
            remaining: list[str] = []
            if read_smoke_registration() is not None:
                remaining.append(
                    f"registry=HKEY_CURRENT_USER\\{uninstall_key()}"
                )
            for name, path in (
                ("install root", self.install_dir),
                ("Modori subtree", self.install_dir / "Modori"),
                ("uninstaller", self.uninstaller),
                ("Start Menu shortcut", self.start_menu_shortcut),
            ):
                if _path_entry_exists(path):
                    remaining.append(f"{name}={path}")
            if not remaining:
                return

            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                raise RuntimeError(
                    "Smoke installer-owned state remains after "
                    f"{_UNINSTALL_WAIT_TIMEOUT_SECONDS:.1f} seconds: "
                    + ", ".join(remaining)
                )
            time.sleep(
                min(_UNINSTALL_POLL_INTERVAL_SECONDS, remaining_seconds)
            )

    def verify_and_remove_user_state(self) -> None:
        self.require_user_state_exercised()
        raw_run_root = self.install_dir.parent
        resolved_smoke_root = SMOKE_ROOT.resolve()
        resolved_run_root = raw_run_root.resolve()
        resolved_user_state = self.user_state_dir.resolve(strict=True)
        if (
            not SMOKE_ROOT.is_dir()
            or _is_link_or_junction(SMOKE_ROOT)
            or not raw_run_root.is_dir()
            or _is_link_or_junction(raw_run_root)
            or resolved_run_root.parent != resolved_smoke_root
            or _RUN_ROOT_PATTERN.fullmatch(resolved_run_root.name) is None
        ):
            raise RuntimeError("Smoke run root is not a UUID child of the smoke root")
        if (
            self.user_state_dir.parent.resolve() != resolved_run_root
            or resolved_user_state.parent != resolved_run_root
            or _is_link_or_junction(self.user_state_dir)
        ):
            raise RuntimeError("Smoke user-state directory escaped the smoke run root")
        files, directories = _validated_user_state_inventory(
            self.user_state_dir,
            resolved_user_state,
        )
        for path in files:
            path.unlink()
        for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            path.rmdir()
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
    path_payload = payload.get("payload_paths")
    version = payload.get("version")
    if (
        payload.get("channel") != "internal-smoke"
        or payload.get("app_id") != SMOKE_APP_ID
        or payload.get("smoke_only") is not True
        or not isinstance(version, str)
        or _VERSION_PATTERN.fullmatch(version) is None
        or not isinstance(installer_payload, dict)
        or not isinstance(probe_payload, dict)
        or not isinstance(path_payload, dict)
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
    longest_path = path_payload.get("longest_relative_path")
    longest_path_chars = path_payload.get("longest_relative_path_chars")
    if (
        not isinstance(longest_path, str)
        or not longest_path
        or type(longest_path_chars) is not int
        or longest_path_chars != len(longest_path)
    ):
        raise ValueError("Installer smoke payload path evidence is invalid")
    posix_path = PurePosixPath(longest_path)
    windows_path = PureWindowsPath(longest_path)
    if (
        posix_path.is_absolute()
        or bool(windows_path.drive)
        or bool(windows_path.root)
        or "\\" in longest_path
        or any(part in ("", ".", "..") for part in longest_path.split("/"))
    ):
        raise ValueError("Installer smoke payload path evidence is invalid")
    return payload


def require_smoke_path_budget(
    payload: dict[str, object],
    install_dir: Path,
) -> None:
    path_payload = payload["payload_paths"]
    assert isinstance(path_payload, dict)
    longest_path_chars = path_payload["longest_relative_path_chars"]
    assert type(longest_path_chars) is int
    payload_root = (install_dir / "Modori").resolve()
    computed_chars = len(str(payload_root)) + 1 + longest_path_chars
    if computed_chars > SAFE_PATH_BUDGET_CHARS:
        raise ValueError(
            "Installer smoke path budget exceeded: "
            f"{computed_chars} > {SAFE_PATH_BUDGET_CHARS}: {payload_root}"
        )


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
        run_root = SMOKE_ROOT / f"r-{uuid.uuid4().hex[:12]}"
        adapter = lifecycle_adapter or LifecycleAdapter.for_real_run(run_root)
        require_smoke_path_budget(payload, adapter.install_dir)
        adapter.require_no_existing_registration()
        run_root.mkdir(parents=True)
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

        state_root = str(adapter.user_state_dir.resolve())
        package_smoke_commands = [
            [
                sys.executable,
                "scripts/package_launch_smoke.py",
                str(adapter.executable),
                "--state-root",
                state_root,
            ],
            [
                sys.executable,
                "scripts/package_engine_smoke.py",
                str(adapter.executable),
                "--state-root",
                state_root,
            ],
            [
                sys.executable,
                "scripts/package_public_data_smoke.py",
                str(adapter.executable),
                "--state-root",
                state_root,
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

        adapter.require_user_state_exercised()
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
