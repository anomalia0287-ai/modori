from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath

import pytest

from scripts.office_research_memory_kit import (
    RUNTIME_SPEC,
    ManifestEntry,
    canonical_json_bytes,
    manifest_bytes,
)
from scripts.verify_office_research_memory_kit import (
    KitVerificationError,
    verify_kit,
)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _identity() -> dict[str, object]:
    return {
        "builder_version": 1,
        "runtime": {
            "archive_sha256": RUNTIME_SPEC.sha256,
            "sqlite_version": RUNTIME_SPEC.sqlite_version,
            "url": RUNTIME_SPEC.url,
            "version": RUNTIME_SPEC.version,
        },
        "schema_id": "modori.office_benchmark_kit_identity",
        "schema_version": 1,
        "source_commit": "a" * 40,
        "source_date_epoch": 1_752_000_000,
    }


def _refresh_manifest(root: Path) -> None:
    excluded = {
        "MANIFEST.json",
        "RUN-MODORI-BENCHMARK.cmd",
        "VERIFY-AND-RUN.ps1",
    }
    entries: list[ManifestEntry] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded or relative.split("/", 1)[0] in {"results", "work"}:
            continue
        data = path.read_bytes()
        entries.append(
            ManifestEntry(
                path=relative,
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
    (root / "MANIFEST.json").write_bytes(manifest_bytes(tuple(entries)))


def _fake_kit(tmp_path: Path) -> Path:
    root = (tmp_path / "portable kit 한글").resolve()
    root.mkdir(parents=True)
    (root / "results").mkdir()
    (root / "work").mkdir()
    _write(root / "RUN-MODORI-BENCHMARK.cmd", b"@echo off\r\n")
    _write(root / "VERIFY-AND-RUN.ps1", b"Write-Output 'ok'\r\n")
    _write(root / "README-KO.txt", "안내".encode())
    _write(root / "KIT-IDENTITY.json", canonical_json_bytes(_identity()))
    _write(root / "payload" / "scripts" / "runner.py", b"pass\n")
    for runtime_name in RUNTIME_SPEC.expected_files:
        _write(root / "runtime" / PurePosixPath(runtime_name), runtime_name.encode())
    _refresh_manifest(root)
    return root


def test_verify_kit_accepts_manifested_files_and_ignores_owned_results(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    _write(root / "results" / "prior-result.json", b"{}")
    _write(root / "work" / "interrupted" / "diagnostic.txt", b"owned")
    verified = verify_kit(root)
    assert verified.root == root
    assert verified.identity["source_commit"] == "a" * 40
    assert len(verified.entries) == 38


def test_verify_kit_rejects_an_extra_immutable_file(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    _write(root / "payload" / "extra.py", b"pass\n")
    with pytest.raises(KitVerificationError, match="unexpected"):
        verify_kit(root)


@pytest.mark.parametrize(
    "target",
    ["runtime/python.exe", "KIT-IDENTITY.json", "payload/scripts/runner.py"],
)
def test_verify_kit_rejects_one_byte_mutation(tmp_path: Path, target: str) -> None:
    root = _fake_kit(tmp_path)
    path = root / PurePosixPath(target)
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(KitVerificationError, match="digest|size"):
        verify_kit(root)


def test_verify_kit_rejects_missing_or_extra_runtime_member(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    (root / "runtime" / "python.exe").unlink()
    _refresh_manifest(root)
    with pytest.raises(KitVerificationError, match="runtime inventory"):
        verify_kit(root)

    root = _fake_kit(tmp_path / "second")
    _write(root / "runtime" / "surprise.dll", b"x")
    _refresh_manifest(root)
    with pytest.raises(KitVerificationError, match="runtime inventory"):
        verify_kit(root)


def test_verify_kit_rejects_semantically_forged_identity(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    identity = _identity()
    identity["runtime"]["archive_sha256"] = "b" * 64
    _write(root / "KIT-IDENTITY.json", canonical_json_bytes(identity))
    _refresh_manifest(root)
    with pytest.raises(KitVerificationError, match="runtime identity"):
        verify_kit(root)


def test_verify_kit_rejects_noncanonical_identity_even_when_manifested(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    raw = json.dumps(_identity(), indent=2).encode()
    _write(root / "KIT-IDENTITY.json", raw)
    _refresh_manifest(root)
    with pytest.raises(KitVerificationError, match="canonical"):
        verify_kit(root)


def test_verify_kit_rejects_missing_or_linked_bootstrap(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    (root / "RUN-MODORI-BENCHMARK.cmd").unlink()
    with pytest.raises(KitVerificationError, match="bootstrap"):
        verify_kit(root)

    root = _fake_kit(tmp_path / "linked")
    bootstrap = root / "RUN-MODORI-BENCHMARK.cmd"
    bootstrap.unlink()
    try:
        os.symlink(root / "README-KO.txt", bootstrap)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(KitVerificationError, match="link"):
        verify_kit(root)


def test_verify_kit_rejects_manifested_link_without_following_it(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    target = root / "payload" / "scripts" / "runner.py"
    target.unlink()
    try:
        os.symlink(root / "README-KO.txt", target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(KitVerificationError, match="link"):
        verify_kit(root)
