from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import zipfile

import pytest

from scripts.build_office_research_memory_kit import (
    PAYLOAD_SOURCE_MAP,
    TEMPLATE_SOURCE_FILES,
    BuildRequest,
    KitBuildError,
    SourceSnapshot,
    build_kit,
)
from scripts.office_research_memory_kit import RuntimeSpec, parse_manifest


def _runtime_archive(
    path: Path,
    *,
    traversal: bool = False,
    symlink: bool = False,
) -> tuple[Path, RuntimeSpec]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("LICENSE.txt", "license")
        archive.writestr("python.exe", "runtime")
        if traversal:
            archive.writestr("../escape.dll", "escape")
        if symlink:
            info = zipfile.ZipInfo("linked.dll")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "python.exe")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, RuntimeSpec(
        version="3.12.10",
        sqlite_version="3.49.1",
        url=(
            "https://www.python.org/ftp/python/3.12.10/"
            "python-3.12.10-embed-amd64.zip"
        ),
        sha256=digest,
        expected_files=("LICENSE.txt", "python.exe"),
    )


def _source_snapshot() -> SourceSnapshot:
    files = {path: f"source:{path}\n".encode() for path in PAYLOAD_SOURCE_MAP}
    files.update(
        {
            TEMPLATE_SOURCE_FILES["cmd"]: (
                b"@echo off\nrem __POWERSHELL_SHA256__\n"
            ),
            TEMPLATE_SOURCE_FILES["powershell"]: (
                b"$ManifestDigest = '__MANIFEST_SHA256__'\n"
            ),
            TEMPLATE_SOURCE_FILES["readme"]: "사용 안내\n".encode(),
        }
    )
    return SourceSnapshot(
        commit="1" * 40,
        source_date_epoch=1_752_000_000,
        files=files,
    )


def _request(
    tmp_path: Path,
    *,
    runtime_archive: Path | None = None,
    runtime_spec: RuntimeSpec | None = None,
) -> BuildRequest:
    if runtime_archive is None or runtime_spec is None:
        runtime_archive, runtime_spec = _runtime_archive(tmp_path / "runtime.zip")
    return BuildRequest(
        output_dir=(tmp_path / "dist").resolve(),
        runtime_archive=runtime_archive.resolve(),
        runtime_spec=runtime_spec,
        snapshot=_source_snapshot(),
        validate_runtime=False,
    )


def _archive_file(result, relative: str) -> bytes:
    with zipfile.ZipFile(result.archive) as archive:
        return archive.read(f"{result.kit_name}/{relative}")


def test_builder_rejects_wrong_runtime_digest(tmp_path: Path) -> None:
    runtime, spec = _runtime_archive(tmp_path / "runtime.zip")
    runtime.write_bytes(runtime.read_bytes() + b"x")
    with pytest.raises(KitBuildError, match="runtime digest"):
        build_kit(_request(tmp_path, runtime_archive=runtime, runtime_spec=spec))


@pytest.mark.parametrize("mutation", ["traversal", "symlink"])
def test_builder_rejects_unsafe_runtime_members(
    tmp_path: Path,
    mutation: str,
) -> None:
    runtime, spec = _runtime_archive(
        tmp_path / "runtime.zip",
        traversal=mutation == "traversal",
        symlink=mutation == "symlink",
    )
    with pytest.raises(KitBuildError, match="runtime archive"):
        build_kit(_request(tmp_path, runtime_archive=runtime, runtime_spec=spec))


def test_identical_inputs_produce_identical_zip_bytes(tmp_path: Path) -> None:
    runtime, spec = _runtime_archive(tmp_path / "runtime.zip")
    first = build_kit(
        _request(tmp_path / "one", runtime_archive=runtime, runtime_spec=spec)
    )
    second = build_kit(
        _request(tmp_path / "two", runtime_archive=runtime, runtime_spec=spec)
    )
    assert first.archive.read_bytes() == second.archive.read_bytes()
    assert first.archive_sha256 == second.archive_sha256
    assert first.digest_file.read_text(encoding="ascii") == (
        f"{first.archive_sha256}  {first.archive.name}\n"
    )


def test_builder_creates_a_complete_hash_chain(tmp_path: Path) -> None:
    result = build_kit(_request(tmp_path))
    manifest = _archive_file(result, "MANIFEST.json")
    powershell = _archive_file(result, "VERIFY-AND-RUN.ps1")
    command = _archive_file(result, "RUN-MODORI-BENCHMARK.cmd")
    manifest_digest = hashlib.sha256(manifest).hexdigest().encode()
    powershell_digest = hashlib.sha256(powershell).hexdigest().encode()
    assert manifest_digest in powershell
    assert powershell_digest in command
    assert b"__MANIFEST_SHA256__" not in powershell
    assert b"__POWERSHELL_SHA256__" not in command
    assert b"\r\n" in command
    assert b"\n" not in command.replace(b"\r\n", b"")
    entries = parse_manifest(manifest)
    paths = {entry.path for entry in entries}
    assert {
        "KIT-IDENTITY.json",
        "README-KO.txt",
        "runtime/LICENSE.txt",
        "runtime/python.exe",
    } <= paths
    assert "MANIFEST.json" not in paths
    assert "RUN-MODORI-BENCHMARK.cmd" not in paths
    assert "VERIFY-AND-RUN.ps1" not in paths


def test_archive_has_one_fixed_root_and_no_repository_material(tmp_path: Path) -> None:
    result = build_kit(_request(tmp_path))
    with zipfile.ZipFile(result.archive) as archive:
        names = tuple(info.filename for info in archive.infolist())
    assert names == tuple(sorted(names))
    assert all(name.startswith(result.kit_name + "/") for name in names)
    assert any(name.endswith("/results/") for name in names)
    assert any(name.endswith("/work/") for name in names)
    assert not any(".git" in name or ".venv" in name or "fixtures" in name for name in names)


def test_builder_rejects_incomplete_source_snapshot(tmp_path: Path) -> None:
    request = _request(tmp_path)
    incomplete = dict(request.snapshot.files)
    incomplete.pop(next(iter(PAYLOAD_SOURCE_MAP)))
    bad_snapshot = SourceSnapshot(
        commit=request.snapshot.commit,
        source_date_epoch=request.snapshot.source_date_epoch,
        files=incomplete,
    )
    with pytest.raises(KitBuildError, match="source snapshot"):
        build_kit(
            BuildRequest(
                output_dir=request.output_dir,
                runtime_archive=request.runtime_archive,
                runtime_spec=request.runtime_spec,
                snapshot=bad_snapshot,
                validate_runtime=False,
            )
        )


def test_builder_never_overwrites_an_existing_delivery(tmp_path: Path) -> None:
    request = _request(tmp_path)
    build_kit(request)
    with pytest.raises(KitBuildError, match="exists"):
        build_kit(request)


def test_payload_allowlist_is_closed_and_contains_no_data_or_environment() -> None:
    source_paths = set(PAYLOAD_SOURCE_MAP)
    assert "scripts/benchmark_research_memory.py" in source_paths
    assert "scripts/run_office_research_memory_benchmark.py" in source_paths
    assert "src/modori/research_memory/ledger_store.py" in source_paths
    assert "src/modori/research_os/contracts.py" in source_paths
    forbidden = re.compile(r"(?:^|/)(?:\.git|\.venv|tests|fixtures|data)(?:/|$)")
    assert not any(forbidden.search(path) for path in source_paths)


def test_identity_is_canonical_and_records_only_reproducible_inputs(
    tmp_path: Path,
) -> None:
    result = build_kit(_request(tmp_path))
    raw = _archive_file(result, "KIT-IDENTITY.json")
    identity = json.loads(raw)
    assert raw == json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert identity["source_commit"] == "1" * 40
    assert identity["source_date_epoch"] == 1_752_000_000
    assert "build_time" not in identity


def test_zip_digest_changes_after_one_byte_mutation(tmp_path: Path) -> None:
    result = build_kit(_request(tmp_path))
    mutated = io.BytesIO(result.archive.read_bytes() + b"x").getvalue()
    assert hashlib.sha256(mutated).hexdigest() != result.archive_sha256


def test_builder_cli_bootstraps_repository_imports_from_any_working_directory(
    tmp_path: Path,
) -> None:
    script = Path("scripts/build_office_research_memory_kit.py").resolve()
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        encoding="utf-8",
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--runtime-archive" in completed.stdout
