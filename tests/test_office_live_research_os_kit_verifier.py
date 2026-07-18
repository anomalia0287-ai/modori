from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile

import pytest

from scripts.live_research_os_office_benchmark import (
    ACCEPTANCE_FIXTURE_DIGEST,
    OfficeBenchmarkProtocol,
    protocol_digest,
)
from scripts.live_research_os_office_kit import (
    BUILDER_CONTRACT_VERSION,
    VERIFIER_CONTRACT_VERSION,
    KitIdentity,
    ManifestEntry,
    PackageLockEntry,
    identity_bytes,
    kit_name,
    manifest_bytes,
    package_lock_bytes,
    sha256_bytes,
)
from scripts.verify_office_live_research_os_kit import (
    KitVerificationError,
    probe_runtime_identity,
    verify_kit,
)
import scripts.verify_office_live_research_os_kit as verifier_module


BOOTSTRAP_FILES = {
    "MANIFEST.json",
    "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd",
    "VERIFY-AND-RUN.ps1",
}


def _package_lock() -> bytes:
    return package_lock_bytes(
        tuple(
            PackageLockEntry(name, version)
            for name, version in (
                ("numpy", "2.5.0"),
                ("pandas", "3.0.3"),
                ("pyinstaller", "6.21.0"),
                ("pyinstaller-hooks-contrib", "2026.2"),
                ("pyside6", "6.11.1"),
                ("pyside6-addons", "6.11.1"),
                ("pyside6-essentials", "6.11.1"),
                ("shiboken6", "6.11.1"),
            )
        )
    )


def _identity() -> KitIdentity:
    lock = _package_lock()
    return KitIdentity(
        source_commit="a" * 40,
        source_date_epoch=1_752_000_000,
        protocol_digest=protocol_digest(OfficeBenchmarkProtocol()),
        fixture_digest=ACCEPTANCE_FIXTURE_DIGEST,
        python_version="3.12.10",
        sqlite_version="3.49.1",
        pyside_version="6.11.1",
        numpy_version="2.5.0",
        pandas_version="3.0.3",
        pyinstaller_version="6.21.0",
        pyinstaller_bootloader_sha256="b" * 64,
        package_lock_sha256=sha256_bytes(lock),
        executable_path="runtime/ModoriLiveResearchOSBenchmark.exe",
        runtime_layout="pyinstaller_onefolder_console",
        builder_contract_version=BUILDER_CONTRACT_VERSION,
        verifier_contract_version=VERIFIER_CONTRACT_VERSION,
        result_schema_id="modori.live_research_os_office_benchmark",
        result_schema_version=1,
    )


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _manifest(root: Path) -> bytes:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in BOOTSTRAP_FILES:
            continue
        raw = path.read_bytes()
        entries.append(
            ManifestEntry(
                relative,
                len(raw),
                hashlib.sha256(raw).hexdigest(),
            )
        )
    return manifest_bytes(tuple(entries))


def _fake_kit(tmp_path: Path) -> Path:
    identity = _identity()
    root = (
        tmp_path / kit_name(identity.source_commit, identity.python_version)
    ).resolve()
    (root / "results").mkdir(parents=True)
    (root / "work").mkdir()
    _write(root / "README-KO.txt", "합성 벤치마크".encode())
    _write(root / "PACKAGE-LOCK.json", _package_lock())
    _write(root / "KIT-IDENTITY.json", identity_bytes(identity))
    _write(root / identity.executable_path, b"MZ-fake-runtime")
    _write(root / "runtime/_internal/python312.dll", b"python")
    _write(root / "runtime/_internal/base_library.zip", b"PK\x05\x06" + b"\x00" * 18)
    _write(root / "runtime/_internal/PySide6/Qt6Core.dll", b"qt")
    _write(root / "runtime/_internal/numpy-core.pyd", b"numpy")
    _write(root / "runtime/_internal/pandas-core.pyd", b"pandas")
    _write(
        root / "runtime/_internal/LIVE-RESEARCH-OS-RUNTIME-IDENTITY.json",
        identity_bytes(identity),
    )
    manifest = _manifest(root)
    _write(root / "MANIFEST.json", manifest)
    powershell = (
        f"$manifest='{sha256_bytes(manifest)}'\n"
        f"$identity='{sha256_bytes(identity_bytes(identity))}'\n"
    ).encode()
    _write(root / "VERIFY-AND-RUN.ps1", powershell)
    command = f"@echo off\r\nrem {sha256_bytes(powershell)}\r\n".encode()
    _write(root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd", command)
    return root


def _write_zip(root: Path, target: Path, *, reverse: bool = False) -> Path:
    entries: list[tuple[str, Path, bool]] = [(f"{root.name}/", root, True)]
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        is_directory = path.is_dir()
        name = f"{root.name}/{relative}" + ("/" if is_directory else "")
        entries.append((name, path, is_directory))
    entries.sort(key=lambda item: item[0], reverse=reverse)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path, is_directory in entries:
            info = zipfile.ZipInfo(name, date_time=(2025, 7, 9, 0, 0, 0))
            info.create_system = 3
            if is_directory:
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                archive.writestr(info, b"")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, path.read_bytes())
    return target


def _archive_with_sidecar(root: Path, tmp_path: Path) -> tuple[Path, Path]:
    archive = _write_zip(root, tmp_path / f"{root.name}.zip")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = archive.with_name(archive.name + ".sha256")
    sidecar.write_bytes(f"{digest}  {archive.name}\n".encode("ascii"))
    return archive, sidecar


def _probe_calls():
    calls: list[tuple[Path, KitIdentity]] = []

    def probe(root: Path, identity: KitIdentity) -> None:
        assert (root / identity.executable_path).read_bytes() == b"MZ-fake-runtime"
        calls.append((root, identity))

    return calls, probe


def test_verifier_accepts_extracted_root_and_zip_sidecar(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path / "root")
    calls, probe = _probe_calls()
    extracted = verify_kit(root, runtime_probe=probe)
    assert extracted.source_kind == "directory"
    assert extracted.identity == _identity()
    assert extracted.runtime_verified is True

    archive, sidecar = _archive_with_sidecar(root, tmp_path)
    zipped = verify_kit(archive, sidecar=sidecar, runtime_probe=probe)
    assert zipped.source_kind == "zip"
    assert zipped.archive_sha256 == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert zipped.member_count > len(zipped.manifest_entries)
    assert len(calls) == 2


def test_static_failure_happens_before_runtime_probe(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    executable = root / _identity().executable_path
    executable.write_bytes(executable.read_bytes() + b"x")
    called = False

    def probe(_root: Path, _identity_value: KitIdentity) -> None:
        nonlocal called
        called = True

    with pytest.raises(KitVerificationError, match="manifest|digest|size"):
        verify_kit(root, runtime_probe=probe)
    assert called is False


@pytest.mark.parametrize(
    "target",
    (
        "KIT-IDENTITY.json",
        "PACKAGE-LOCK.json",
        "runtime/_internal/python312.dll",
        "VERIFY-AND-RUN.ps1",
    ),
)
def test_extracted_verifier_rejects_immutable_mutation(
    tmp_path: Path, target: str
) -> None:
    root = _fake_kit(tmp_path)
    path = root / PurePosixPath(target)
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(KitVerificationError):
        verify_kit(root, runtime_probe=lambda *_args: None)


def test_verifier_rejects_extra_source_bytecode_and_mutable_zip_content(
    tmp_path: Path,
) -> None:
    for relative in ("runtime/extra.py", "runtime/extra.pyc", "work/forged.json"):
        root = _fake_kit(tmp_path / relative.replace("/", "_"))
        _write(root / PurePosixPath(relative), b"x")
        if not relative.startswith("work/"):
            _write(root / "MANIFEST.json", _manifest(root))
        archive, sidecar = _archive_with_sidecar(root, root.parent)
        with pytest.raises(KitVerificationError, match="source|bytecode|mutable"):
            verify_kit(archive, sidecar=sidecar, runtime_probe=lambda *_args: None)


def test_zip_verifier_rejects_stale_sidecar_and_unsorted_archive(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path / "source")
    archive, sidecar = _archive_with_sidecar(root, tmp_path)
    sidecar.write_bytes(f"{'0' * 64}  {archive.name}\n".encode("ascii"))
    with pytest.raises(KitVerificationError, match="sidecar|digest"):
        verify_kit(archive, sidecar=sidecar, runtime_probe=lambda *_args: None)

    unsorted = _write_zip(root, tmp_path / "unsorted.zip", reverse=True)
    unsorted_sidecar = unsorted.with_name(unsorted.name + ".sha256")
    unsorted_sidecar.write_bytes(
        (
            f"{hashlib.sha256(unsorted.read_bytes()).hexdigest()}  {unsorted.name}\n"
        ).encode("ascii")
    )
    with pytest.raises(KitVerificationError, match="sorted"):
        verify_kit(
            unsorted,
            sidecar=unsorted_sidecar,
            runtime_probe=lambda *_args: None,
        )


def test_outer_digest_rejects_command_bootstrap_mutation(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path / "source")
    archive, sidecar = _archive_with_sidecar(root, tmp_path)
    command = root / "RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd"
    command.write_bytes(command.read_bytes() + b"x")
    replacement = tmp_path / "mutated" / archive.name
    replacement.parent.mkdir()
    _write_zip(root, replacement)
    with pytest.raises(KitVerificationError, match="sidecar|digest"):
        verify_kit(replacement, sidecar=sidecar, runtime_probe=lambda *_args: None)


def test_extracted_verifier_rejects_linked_member(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    path = root / "runtime/_internal/python312.dll"
    path.unlink()
    try:
        os.symlink(root / "README-KO.txt", path)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(KitVerificationError, match="link|reparse"):
        verify_kit(root, runtime_probe=lambda *_args: None)


def test_verifier_rejects_empty_immutable_and_preseeded_mutable_directories(
    tmp_path: Path,
) -> None:
    extracted = _fake_kit(tmp_path / "extracted")
    (extracted / "runtime/unexpected-empty").mkdir()
    with pytest.raises(KitVerificationError, match="directory|inventory"):
        verify_kit(extracted, runtime_probe=lambda *_args: None)

    root = _fake_kit(tmp_path / "zipped")
    (root / "work/preseeded").mkdir()
    archive, sidecar = _archive_with_sidecar(root, tmp_path)
    with pytest.raises(KitVerificationError, match="mutable|directory|inventory"):
        verify_kit(archive, sidecar=sidecar, runtime_probe=lambda *_args: None)


def test_runtime_probe_uses_only_two_literal_identity_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _fake_kit(tmp_path)
    identity = _identity()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def completed(command, **kwargs):
        calls.append((command, kwargs))
        stdout = (
            identity_bytes(identity) + b"\n"
            if command[-1] == "--self-identity"
            else b""
        )
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(verifier_module.subprocess, "run", completed)
    probe_runtime_identity(root, identity)
    executable = str((root / identity.executable_path).resolve())
    assert [call[0] for call in calls] == [
        [executable, "--self-identity"],
        [executable, "--verify-kit-identity"],
    ]
    for _command, kwargs in calls:
        assert kwargs["cwd"] == root
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["timeout"] == 120
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PYTHONHOME" not in kwargs["env"]
        assert kwargs["env"]["LOCALAPPDATA"] == str(root / "work")
        assert kwargs["env"]["TEMP"] == str(root / "work")
        assert kwargs["env"]["TMP"] == str(root / "work")
        if "SystemRoot" in os.environ:
            assert kwargs["env"]["PATH"] == str(
                Path(os.environ["SystemRoot"]) / "System32"
            )
