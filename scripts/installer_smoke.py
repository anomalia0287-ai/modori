from __future__ import annotations

import argparse
import hashlib
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
    from scripts.package_smoke_contract import (
        engine_payload_has_contract,
        public_data_payload_has_contract,
    )
else:
    from installer_contract import (  # type: ignore[import-not-found]
        DOWNGRADE_PROBE_VERSION,
        SAFE_PATH_BUDGET_CHARS,
        SMOKE_APP_ID,
        sha256_file,
    )
    from package_smoke_contract import (  # type: ignore[import-not-found]
        engine_payload_has_contract,
        public_data_payload_has_contract,
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
_ENGINE_EVIDENCE_DIRECTORY = "engine-smoke"
_PUBLIC_DATA_EVIDENCE_DIRECTORY = "public-data-smoke"
_ENGINE_EVIDENCE_FILES = frozenset({"reference.xlsx", "result.json"})
_PUBLIC_DATA_EVIDENCE_FILES = frozenset({"result.json"})


def _absolute_lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _configured_smoke_paths() -> tuple[Path, Path, Path]:
    workspace = _absolute_lexical_path(WORKSPACE)
    temporary_root = workspace / ".tmp"
    smoke_root = temporary_root / "installer-smoke"
    if _absolute_lexical_path(SMOKE_ROOT) != smoke_root:
        raise RuntimeError("Smoke root must be WORKSPACE/.tmp/installer-smoke")
    return workspace, temporary_root, smoke_root


def _validated_directory(
    path: Path,
    *,
    resolved_parent: Path | None = None,
) -> Path:
    try:
        status = path.lstat()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Smoke boundary directory is missing: {path}") from exc
    except OSError as exc:
        raise RuntimeError(
            f"Smoke boundary directory could not be inspected: {path}"
        ) from exc
    attributes = getattr(status, "st_file_attributes", 0)
    if (
        stat.S_ISLNK(status.st_mode)
        or bool(attributes & _REPARSE_POINT_ATTRIBUTE)
        or not stat.S_ISDIR(status.st_mode)
    ):
        raise RuntimeError(
            "Smoke boundary component is a link, junction/reparse point, "
            f"or non-directory: {path}"
        )
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(
            f"Smoke boundary directory could not be resolved: {path}"
        ) from exc
    if resolved_parent is not None and resolved.parent != resolved_parent:
        raise RuntimeError(f"Smoke boundary directory escaped its parent: {path}")
    return resolved


def _prepare_smoke_root() -> Path:
    workspace, temporary_root, smoke_root = _configured_smoke_paths()
    resolved_workspace = _validated_directory(workspace)
    resolved_parent = resolved_workspace
    for component in (temporary_root, smoke_root):
        try:
            component.lstat()
        except FileNotFoundError:
            component.mkdir()
        except OSError as exc:
            raise RuntimeError(
                f"Smoke boundary component could not be inspected: {component}"
            ) from exc
        resolved_parent = _validated_directory(
            component,
            resolved_parent=resolved_parent,
        )
    return resolved_parent


def _validate_smoke_run_root(run_root: Path) -> Path:
    workspace, temporary_root, smoke_root = _configured_smoke_paths()
    resolved_workspace = _validated_directory(workspace)
    resolved_temporary_root = _validated_directory(
        temporary_root,
        resolved_parent=resolved_workspace,
    )
    resolved_smoke_root = _validated_directory(
        smoke_root,
        resolved_parent=resolved_temporary_root,
    )
    lexical_run_root = _absolute_lexical_path(run_root)
    if (
        lexical_run_root.parent != smoke_root
        or _RUN_ROOT_PATTERN.fullmatch(lexical_run_root.name) is None
    ):
        raise RuntimeError("Smoke run root is not a UUID child of the smoke root")
    return _validated_directory(
        lexical_run_root,
        resolved_parent=resolved_smoke_root,
    )


def _directory_identity(path: Path) -> tuple[int, int]:
    try:
        status = path.lstat()
    except OSError as exc:
        raise RuntimeError(
            f"Smoke boundary identity could not be inspected: {path}"
        ) from exc
    return status.st_dev, status.st_ino


@dataclass(frozen=True)
class _SmokeRunBoundary:
    run_root: Path
    identities: tuple[tuple[int, int], ...]

    @property
    def paths(self) -> tuple[Path, ...]:
        return (*_configured_smoke_paths(), self.run_root)

    @classmethod
    def capture(cls, run_root: Path) -> _SmokeRunBoundary:
        lexical_run_root = _absolute_lexical_path(run_root)
        _validate_smoke_run_root(lexical_run_root)
        boundary = cls(
            run_root=lexical_run_root,
            identities=tuple(
                _directory_identity(path)
                for path in (*_configured_smoke_paths(), lexical_run_root)
            ),
        )
        boundary.revalidate()
        return boundary

    def revalidate(self) -> None:
        _validate_smoke_run_root(self.run_root)
        if tuple(_directory_identity(path) for path in self.paths) != self.identities:
            raise RuntimeError("Smoke root or run directory was replaced")


@dataclass(frozen=True)
class _SmokeEvidenceBoundary:
    run_boundary: _SmokeRunBoundary
    directory: Path
    identity: tuple[int, int]

    @classmethod
    def create(
        cls,
        run_boundary: _SmokeRunBoundary,
        name: str,
    ) -> _SmokeEvidenceBoundary:
        if name not in {
            _ENGINE_EVIDENCE_DIRECTORY,
            _PUBLIC_DATA_EVIDENCE_DIRECTORY,
        }:
            raise ValueError(f"Unknown smoke evidence directory: {name}")
        run_boundary.revalidate()
        directory = run_boundary.run_root / name
        if _path_entry_exists(directory):
            raise RuntimeError(f"Smoke evidence directory collision: {directory}")
        try:
            directory.mkdir()
        except FileExistsError as exc:
            raise RuntimeError(
                f"Smoke evidence directory collision: {directory}"
            ) from exc
        run_boundary.revalidate()
        resolved_run_root = _validate_smoke_run_root(run_boundary.run_root)
        _validated_directory(directory, resolved_parent=resolved_run_root)
        evidence_boundary = cls(
            run_boundary=run_boundary,
            directory=directory,
            identity=_directory_identity(directory),
        )
        evidence_boundary.revalidate()
        return evidence_boundary

    def revalidate(self) -> Path:
        self.run_boundary.revalidate()
        resolved_run_root = _validate_smoke_run_root(self.run_boundary.run_root)
        resolved_directory = _validated_directory(
            self.directory,
            resolved_parent=resolved_run_root,
        )
        if _directory_identity(self.directory) != self.identity:
            raise RuntimeError("Smoke evidence directory was replaced")
        return resolved_directory

    def _capture_exact_files(
        self,
        expected_names: frozenset[str],
    ) -> tuple[dict[str, bytes], tuple[tuple[str, int, str], ...]]:
        resolved_directory = self.revalidate()
        try:
            entries = list(self.directory.iterdir())
        except OSError as exc:
            raise RuntimeError(
                f"Durable smoke evidence could not be inventoried: {self.directory}"
            ) from exc
        actual_names = {entry.name for entry in entries}
        if len(entries) != len(actual_names) or actual_names != expected_names:
            raise RuntimeError(
                "Durable smoke evidence inventory mismatch: "
                f"expected={sorted(expected_names)}; actual={sorted(actual_names)}"
            )

        contents: dict[str, bytes] = {}
        final_signatures: dict[str, tuple[int, int, int, int, int, int, int]] = {}
        for entry in entries:
            try:
                before = entry.lstat()
                attributes = getattr(before, "st_file_attributes", 0)
                if (
                    stat.S_ISLNK(before.st_mode)
                    or bool(attributes & _REPARSE_POINT_ATTRIBUTE)
                    or not stat.S_ISREG(before.st_mode)
                ):
                    raise RuntimeError(
                        "Durable smoke evidence entry is not a regular "
                        f"non-reparse file: {entry}"
                    )
                resolved_entry = entry.resolve(strict=True)
                if resolved_entry.parent != resolved_directory:
                    raise RuntimeError(
                        f"Durable smoke evidence escaped its directory: {entry}"
                    )
                data = entry.read_bytes()
                after = entry.lstat()
            except OSError as exc:
                raise RuntimeError(
                    f"Durable smoke evidence could not be read: {entry}"
                ) from exc
            before_signature = (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
                getattr(before, "st_file_attributes", 0),
            )
            after_signature = (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
                getattr(after, "st_file_attributes", 0),
            )
            if before_signature != after_signature or len(data) != before.st_size:
                raise RuntimeError(
                    f"Durable smoke evidence changed while reading: {entry}"
                )
            if not data:
                raise RuntimeError(f"Durable smoke evidence is empty: {entry}")
            contents[entry.name] = data
            final_signatures[entry.name] = after_signature
        try:
            final_entries = list(self.directory.iterdir())
        except OSError as exc:
            raise RuntimeError(
                f"Durable smoke evidence could not be reinventoried: {self.directory}"
            ) from exc
        final_names = {entry.name for entry in final_entries}
        if len(final_entries) != len(final_names) or final_names != expected_names:
            raise RuntimeError(
                "Durable smoke evidence inventory mismatch after reading: "
                f"expected={sorted(expected_names)}; actual={sorted(final_names)}"
            )
        for entry in final_entries:
            try:
                status = entry.lstat()
                attributes = getattr(status, "st_file_attributes", 0)
                resolved_entry = entry.resolve(strict=True)
            except OSError as exc:
                raise RuntimeError(
                    f"Durable smoke evidence changed after reading: {entry}"
                ) from exc
            signature = (
                status.st_dev,
                status.st_ino,
                status.st_mode,
                status.st_size,
                status.st_mtime_ns,
                status.st_ctime_ns,
                attributes,
            )
            if (
                stat.S_ISLNK(status.st_mode)
                or bool(attributes & _REPARSE_POINT_ATTRIBUTE)
                or not stat.S_ISREG(status.st_mode)
                or resolved_entry.parent != resolved_directory
                or signature != final_signatures[entry.name]
            ):
                raise RuntimeError(
                    f"Durable smoke evidence changed after reading: {entry}"
                )
        self.revalidate()
        snapshot = tuple(
            sorted(
                (
                    name,
                    len(data),
                    hashlib.sha256(data).hexdigest().upper(),
                )
                for name, data in contents.items()
            )
        )
        return contents, snapshot

    def require_exact_files(
        self,
        expected_names: frozenset[str],
    ) -> tuple[dict[str, bytes], tuple[tuple[str, int, str], ...]]:
        first_contents, first_snapshot = self._capture_exact_files(expected_names)
        second_contents, second_snapshot = self._capture_exact_files(expected_names)
        if first_snapshot != second_snapshot or first_contents != second_contents:
            raise RuntimeError(
                "Durable smoke evidence changed across final exact-file validation"
            )
        return second_contents, second_snapshot


def _require_durable_smoke_result(
    evidence: _SmokeEvidenceBoundary,
    *,
    expected_files: frozenset[str],
    smoke_kind: str,
    expected_cache_dir: Path | None = None,
    frozen_snapshot: tuple[tuple[str, int, str], ...] | None = None,
) -> tuple[tuple[str, int, str], ...]:
    contents, snapshot = evidence.require_exact_files(expected_files)
    try:
        payload = json.loads(contents["result.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Durable {smoke_kind} smoke evidence is not valid UTF-8 JSON"
        ) from exc
    if smoke_kind == "engine":
        if not engine_payload_has_contract(
            payload,
            expected_cache_dir=expected_cache_dir,
        ):
            raise RuntimeError(
                "Durable engine smoke evidence does not match the engine wrapper "
                "contract"
            )
    elif smoke_kind == "public-data":
        if not public_data_payload_has_contract(payload):
            raise RuntimeError(
                "Durable public-data smoke evidence does not match the hardened "
                "public-data contract"
            )
    else:
        raise ValueError(f"Unknown durable smoke kind: {smoke_kind}")
    if frozen_snapshot is not None and snapshot != frozen_snapshot:
        raise RuntimeError(
            f"Durable {smoke_kind} smoke evidence changed after initial validation"
        )
    return snapshot


def _run_at_validated_boundary(
    boundary: _SmokeRunBoundary,
    runner: Callable[[list[str]], int],
    command: list[str],
) -> int:
    boundary.revalidate()
    return runner(command)


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


@dataclass(frozen=True)
class _UserStateEntry:
    path: Path
    is_directory: bool
    identity: tuple[int, int, int, int]


def _user_state_entry_identity(status: os.stat_result) -> tuple[int, int, int, int]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        getattr(status, "st_file_attributes", 0),
    )


def _validated_user_state_inventory(
    user_state_dir: Path,
    resolved_user_state: Path,
) -> tuple[list[_UserStateEntry], list[_UserStateEntry]]:
    files: list[_UserStateEntry] = []
    directories: list[_UserStateEntry] = []
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
            try:
                status = descendant.lstat()
            except OSError as exc:
                raise RuntimeError(
                    f"Smoke user-state descendant could not be inspected: {descendant}"
                ) from exc
            attributes = getattr(status, "st_file_attributes", 0)
            if stat.S_ISLNK(status.st_mode) or bool(
                attributes & _REPARSE_POINT_ATTRIBUTE
            ):
                raise RuntimeError(
                    "Smoke user-state descendant is a link or junction/reparse "
                    f"point: {descendant}"
                )
            try:
                resolved_descendant = descendant.resolve(strict=True)
            except OSError as exc:
                raise RuntimeError(
                    f"Smoke user-state descendant could not be validated: {descendant}"
                ) from exc
            if resolved_user_state not in resolved_descendant.parents:
                raise RuntimeError(
                    f"Smoke user-state descendant escaped its root: {descendant}"
                )
            entry = _UserStateEntry(
                path=descendant,
                is_directory=stat.S_ISDIR(status.st_mode),
                identity=_user_state_entry_identity(status),
            )
            if entry.is_directory:
                directories.append(entry)
                pending.append(descendant)
            elif stat.S_ISREG(status.st_mode):
                files.append(entry)
            else:
                raise RuntimeError(
                    f"Smoke user-state descendant has an unsupported type: {descendant}"
                )
    return files, directories


def _require_same_user_state_entry(entry: _UserStateEntry) -> None:
    try:
        status = entry.path.lstat()
    except OSError as exc:
        raise RuntimeError(
            f"Smoke user-state entry changed before cleanup: {entry.path}"
        ) from exc
    attributes = getattr(status, "st_file_attributes", 0)
    if (
        stat.S_ISLNK(status.st_mode)
        or bool(attributes & _REPARSE_POINT_ATTRIBUTE)
        or stat.S_ISDIR(status.st_mode) != entry.is_directory
        or _user_state_entry_identity(status) != entry.identity
    ):
        raise RuntimeError(
            f"Smoke user-state entry was replaced before cleanup: {entry.path}"
        )


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
            uninstall_path = (
                registration.get("UninstallString") or "unknown uninstaller"
            )
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
                remaining.append(f"registry=HKEY_CURRENT_USER\\{uninstall_key()}")
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
            time.sleep(min(_UNINSTALL_POLL_INTERVAL_SECONDS, remaining_seconds))

    def verify_and_remove_user_state(
        self,
        run_boundary: _SmokeRunBoundary | None = None,
    ) -> None:
        raw_run_root = self.install_dir.parent
        active_run_boundary = run_boundary or _SmokeRunBoundary.capture(raw_run_root)
        active_run_boundary.revalidate()
        resolved_run_root = _validate_smoke_run_root(raw_run_root)
        lexical_user_state = _absolute_lexical_path(self.user_state_dir)
        if lexical_user_state.parent != _absolute_lexical_path(
            raw_run_root
        ) or _is_link_or_junction(lexical_user_state):
            raise RuntimeError("Smoke user-state directory escaped the smoke run root")
        resolved_user_state = _validated_directory(
            lexical_user_state,
            resolved_parent=resolved_run_root,
        )
        user_state_identity = _directory_identity(lexical_user_state)

        def revalidate_cleanup_boundary() -> None:
            active_run_boundary.revalidate()
            current_run_root = _validate_smoke_run_root(raw_run_root)
            _validated_directory(
                lexical_user_state,
                resolved_parent=current_run_root,
            )
            if _directory_identity(lexical_user_state) != user_state_identity:
                raise RuntimeError(
                    "Smoke user-state directory was replaced during cleanup"
                )

        revalidate_cleanup_boundary()
        self.require_user_state_exercised()
        files, directories = _validated_user_state_inventory(
            lexical_user_state,
            resolved_user_state,
        )
        revalidate_cleanup_boundary()
        for entry in files:
            revalidate_cleanup_boundary()
            _require_same_user_state_entry(entry)
            entry.path.unlink()
            revalidate_cleanup_boundary()
        for entry in sorted(
            directories,
            key=lambda item: len(item.path.parts),
            reverse=True,
        ):
            revalidate_cleanup_boundary()
            _require_same_user_state_entry(entry)
            entry.path.rmdir()
            revalidate_cleanup_boundary()
        revalidate_cleanup_boundary()
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
    if installer_payload.get("filename") != installer.name or installer_payload.get(
        "sha256"
    ) != sha256_file(installer):
        raise ValueError(
            "Smoke installer identity or SHA256 does not match its manifest"
        )
    if probe_payload.get("filename") != probe.name or probe_payload.get(
        "sha256"
    ) != sha256_file(probe):
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
        _prepare_smoke_root()
        if _RUN_ROOT_PATTERN.fullmatch(run_root.name) is None:
            raise RuntimeError("Smoke run root name is not r-<12hex>")
        try:
            run_root.mkdir()
        except FileExistsError as exc:
            raise RuntimeError(f"Smoke run root collision: {run_root}") from exc
        boundary = _SmokeRunBoundary.capture(run_root)
        adapter.user_state_dir.mkdir(parents=True)
        boundary.revalidate()
        (adapter.user_state_dir / "sentinel.json").write_text(
            "preserve",
            encoding="utf-8",
        )
        print(
            "installer-smoke-mutation: creating isolated current-user registration "
            f"{SMOKE_APP_ID} under {adapter.install_dir}"
        )

        install_log = run_root / "install.log"
        if (
            _run_at_validated_boundary(
                boundary,
                runner,
                setup_command(installer, adapter.install_dir, install_log),
            )
            != 0
        ):
            raise RuntimeError("Smoke installer returned nonzero")
        adapter.require_installed(version)

        state_root = str(Path(os.path.abspath(adapter.user_state_dir)))
        expected_cache_dir = adapter.user_state_dir.resolve(strict=True) / "cache"
        engine_evidence = _SmokeEvidenceBoundary.create(
            boundary,
            _ENGINE_EVIDENCE_DIRECTORY,
        )
        public_data_evidence = _SmokeEvidenceBoundary.create(
            boundary,
            _PUBLIC_DATA_EVIDENCE_DIRECTORY,
        )
        package_smoke_commands = [
            (
                [
                    sys.executable,
                    "scripts/package_launch_smoke.py",
                    str(adapter.executable),
                    "--state-root",
                    state_root,
                ],
                None,
                None,
                None,
            ),
            (
                [
                    sys.executable,
                    "scripts/package_engine_smoke.py",
                    str(adapter.executable),
                    "--state-root",
                    state_root,
                    "--evidence-dir",
                    str(engine_evidence.directory),
                ],
                engine_evidence,
                _ENGINE_EVIDENCE_FILES,
                "engine",
            ),
            (
                [
                    sys.executable,
                    "scripts/package_public_data_smoke.py",
                    str(adapter.executable),
                    "--state-root",
                    state_root,
                    "--evidence-dir",
                    str(public_data_evidence.directory),
                    "--fixture-dir",
                    str(WORKSPACE / "tests" / "fixtures" / "public_data_formats"),
                ],
                public_data_evidence,
                _PUBLIC_DATA_EVIDENCE_FILES,
                "public-data",
            ),
        ]
        evidence_snapshots: dict[str, tuple[tuple[str, int, str], ...]] = {}
        for command, evidence, expected_files, smoke_kind in package_smoke_commands:
            if _run_at_validated_boundary(boundary, runner, command) != 0:
                raise RuntimeError(
                    f"Installed package smoke failed: {' '.join(command)}"
                )
            if evidence is not None:
                assert expected_files is not None
                assert smoke_kind is not None
                evidence_snapshots[smoke_kind] = _require_durable_smoke_result(
                    evidence,
                    expected_files=expected_files,
                    smoke_kind=smoke_kind,
                    expected_cache_dir=(
                        expected_cache_dir if smoke_kind == "engine" else None
                    ),
                )

        adapter.require_user_state_exercised()
        adapter.plant_stale_probe()
        repair_log = run_root / "repair.log"
        if (
            _run_at_validated_boundary(
                boundary,
                runner,
                setup_command(installer, adapter.install_dir, repair_log),
            )
            != 0
        ):
            raise RuntimeError("Repair installer returned nonzero")
        adapter.require_repaired(version)

        installed_sha256 = adapter.record_executable_hash()
        downgrade_log = run_root / "downgrade.log"
        downgrade_result = _run_at_validated_boundary(
            boundary,
            runner,
            setup_command(probe, adapter.install_dir, downgrade_log),
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
        if (
            _run_at_validated_boundary(
                boundary,
                runner,
                uninstall_command,
            )
            != 0
        ):
            raise RuntimeError("Smoke uninstaller returned nonzero")
        adapter.require_uninstalled()
        boundary.revalidate()
        adapter.verify_and_remove_user_state(boundary)
        _require_durable_smoke_result(
            engine_evidence,
            expected_files=_ENGINE_EVIDENCE_FILES,
            smoke_kind="engine",
            expected_cache_dir=expected_cache_dir,
            frozen_snapshot=evidence_snapshots["engine"],
        )
        _require_durable_smoke_result(
            public_data_evidence,
            expected_files=_PUBLIC_DATA_EVIDENCE_FILES,
            smoke_kind="public-data",
            frozen_snapshot=evidence_snapshots["public-data"],
        )
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
