from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.installer_contract import (
    ASSUMED_INSTALL_ROOT_CHARS,
    PRODUCTION_APP_ID,
    SAFE_PATH_BUDGET_CHARS,
    FileEvidence,
    build_manifest,
    make_source_identity,
    measure_payload_paths,
    read_project_version,
    sha256_file,
    write_checksum_file,
    write_manifest,
)


def test_project_version_is_three_numeric_components(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")

    assert read_project_version(project) == "0.1.0"
    identity = make_source_identity("0.1.0", "a" * 40, dirty=False)
    assert identity.windows_file_version == "0.1.0.0"
    assert identity.build_identity == f"0.1.0-g{'a' * 12}"


@pytest.mark.parametrize("version", ["0.1", "0.1.0.0", "v0.1.0", "0.1.beta"])
def test_project_version_rejects_unsupported_forms(tmp_path: Path, version: str) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(f'[project]\nversion = "{version}"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="three numeric components"):
        read_project_version(project)


def test_payload_path_budget_records_current_shape(tmp_path: Path) -> None:
    root = tmp_path / "Modori"
    longest = Path("_internal") / ("a" * 100) / ("b" * 17)
    target = root / longest
    target.parent.mkdir(parents=True)
    target.write_bytes(b"payload")

    evidence = measure_payload_paths(root)

    assert evidence.file_count == 1
    assert evidence.longest_relative_path == longest.as_posix()
    assert evidence.longest_relative_path_chars == len(longest.as_posix())
    assert evidence.assumed_install_root_chars == ASSUMED_INSTALL_ROOT_CHARS
    assert evidence.safe_path_budget_chars == SAFE_PATH_BUDGET_CHARS
    assert evidence.computed_max_chars <= SAFE_PATH_BUDGET_CHARS


def test_payload_path_budget_rejects_future_overflow(tmp_path: Path) -> None:
    root = tmp_path / "Modori"
    target = root / ("a" * 100) / ("b" * 60)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"payload")

    with pytest.raises(ValueError, match="path budget"):
        measure_payload_paths(root)


def test_manifest_and_checksum_use_measured_uppercase_sha256(tmp_path: Path) -> None:
    package = tmp_path / "Modori.exe"
    installer = tmp_path / "Modori-Setup-0.1.0-gaaaaaaaaaaaa.exe"
    script = tmp_path / "modori.iss"
    package.write_bytes(b"package")
    installer.write_bytes(b"installer")
    script.write_text("[Setup]\n", encoding="utf-8")
    identity = make_source_identity("0.1.0", "a" * 40, dirty=False)
    paths_root = tmp_path / "payload"
    paths_root.mkdir()
    (paths_root / "file.bin").write_bytes(b"x")
    path_evidence = measure_payload_paths(paths_root)
    package_evidence = FileEvidence.from_path("dist/Modori/Modori.exe", package)
    installer_evidence = FileEvidence.from_path(installer.name, installer)
    script_evidence = FileEvidence.from_path("installer/modori.iss", script)

    manifest = build_manifest(
        identity=identity,
        app_id=PRODUCTION_APP_ID,
        channel="internal",
        smoke_only=False,
        tools={"inno_setup": "6.7.3", "pyinstaller": "6.21.0", "python": "3.12.10"},
        package_executable=package_evidence,
        installer=installer_evidence,
        installer_script=script_evidence,
        payload_paths=path_evidence,
        installed_lifecycle_smoke=True,
        installed_lifecycle_app_id="{97d13afd-818d-40c5-80ee-ce53eea57c0c}",
        built_at="2026-07-12T12:00:00+09:00",
    )
    manifest_path = tmp_path / "release-manifest.json"
    checksum_path = tmp_path / "SHA256SUMS.txt"
    write_manifest(manifest_path, manifest)
    write_checksum_file(checksum_path, installer_evidence)

    emitted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert emitted["git_dirty"] is False
    assert emitted["installer_script"]["sha256"] == sha256_file(script)
    assert emitted["verification"]["installed_lifecycle_smoke"] is True
    assert manifest_path.read_text(encoding="utf-8").endswith("\n")
    assert checksum_path.read_text(encoding="utf-8") == (
        f"{installer_evidence.sha256}  {installer.name}\n"
    )
