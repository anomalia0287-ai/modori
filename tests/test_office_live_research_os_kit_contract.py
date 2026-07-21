from __future__ import annotations

from dataclasses import replace
import json

import pytest

from scripts.live_research_os_office_kit import (
    BUILDER_CONTRACT_VERSION,
    KIT_IDENTITY_SCHEMA_ID,
    KIT_IDENTITY_SCHEMA_VERSION,
    MANIFEST_SCHEMA_ID,
    MANIFEST_SCHEMA_VERSION,
    PACKAGE_LOCK_SCHEMA_ID,
    PACKAGE_LOCK_SCHEMA_VERSION,
    VERIFIER_CONTRACT_VERSION,
    KitContractError,
    KitIdentity,
    ManifestEntry,
    PackageLockEntry,
    canonical_json_bytes,
    identity_bytes,
    kit_name,
    manifest_bytes,
    package_lock_bytes,
    parse_identity,
    parse_manifest,
    parse_package_lock,
    sha256_bytes,
)


SOURCE_COMMIT = "1" * 40
PROTOCOL_DIGEST = "2" * 64
FIXTURE_DIGEST = "3" * 64
BOOTLOADER_DIGEST = "4" * 64


def _lock() -> bytes:
    return package_lock_bytes(
        (
            PackageLockEntry("numpy", "2.5.0"),
            PackageLockEntry("pandas", "3.0.3"),
            PackageLockEntry("pyinstaller", "6.21.0"),
            PackageLockEntry("pyside6", "6.11.1"),
        )
    )


def _identity(**changes: object) -> KitIdentity:
    values: dict[str, object] = {
        "source_commit": SOURCE_COMMIT,
        "source_date_epoch": 1_752_000_000,
        "protocol_digest": PROTOCOL_DIGEST,
        "fixture_digest": FIXTURE_DIGEST,
        "python_version": "3.12.10",
        "sqlite_version": "3.49.1",
        "pyside_version": "6.11.1",
        "numpy_version": "2.5.0",
        "pandas_version": "3.0.3",
        "pyinstaller_version": "6.21.0",
        "pyinstaller_bootloader_sha256": BOOTLOADER_DIGEST,
        "package_lock_sha256": sha256_bytes(_lock()),
        "executable_path": "runtime/ModoriLiveResearchOSBenchmark.exe",
        "runtime_layout": "pyinstaller_onefolder_console",
        "builder_contract_version": BUILDER_CONTRACT_VERSION,
        "verifier_contract_version": VERIFIER_CONTRACT_VERSION,
        "result_schema_id": "modori.live_research_os_office_benchmark",
        "result_schema_version": 1,
    }
    values.update(changes)
    return KitIdentity(**values)


def test_identity_is_closed_canonical_and_binds_every_runtime_input() -> None:
    identity = _identity()
    raw = identity_bytes(identity)
    assert parse_identity(raw) == identity
    assert raw == canonical_json_bytes(identity.to_mapping())
    assert json.loads(raw) == {
        "builder_contract_version": 1,
        "executable_path": "runtime/ModoriLiveResearchOSBenchmark.exe",
        "fixture_digest": FIXTURE_DIGEST,
        "numpy_version": "2.5.0",
        "package_lock_sha256": sha256_bytes(_lock()),
        "pandas_version": "3.0.3",
        "protocol_digest": PROTOCOL_DIGEST,
        "pyinstaller_bootloader_sha256": BOOTLOADER_DIGEST,
        "pyinstaller_version": "6.21.0",
        "pyside_version": "6.11.1",
        "python_version": "3.12.10",
        "result_schema_id": "modori.live_research_os_office_benchmark",
        "result_schema_version": 1,
        "runtime_layout": "pyinstaller_onefolder_console",
        "schema_id": KIT_IDENTITY_SCHEMA_ID,
        "schema_version": KIT_IDENTITY_SCHEMA_VERSION,
        "source_commit": SOURCE_COMMIT,
        "source_date_epoch": 1_752_000_000,
        "sqlite_version": "3.49.1",
        "verifier_contract_version": 1,
    }


def test_identity_rejects_unknown_noncanonical_duplicate_and_unsupported_values() -> (
    None
):
    raw = identity_bytes(_identity())
    unknown = dict(json.loads(raw))
    unknown["extra"] = "forbidden"
    with pytest.raises(KitContractError, match="fields"):
        parse_identity(canonical_json_bytes(unknown))
    with pytest.raises(KitContractError, match="canonical"):
        parse_identity(raw.replace(b"{", b"{ ", 1))
    duplicate = raw.replace(
        b'"schema_id":',
        b'"schema_id":"duplicate","schema_id":',
        1,
    )
    with pytest.raises(KitContractError, match="strict JSON"):
        parse_identity(duplicate)
    with pytest.raises(KitContractError, match="runtime layout"):
        replace(_identity(), runtime_layout="onefile")
    with pytest.raises(KitContractError, match="contract version"):
        replace(_identity(), builder_contract_version=2)


def test_manifest_roundtrip_is_sorted_complete_and_case_unique() -> None:
    entries = (
        ManifestEntry("runtime/_internal/python312.dll", 3, "a" * 64),
        ManifestEntry("KIT-IDENTITY.json", 2, "b" * 64),
        ManifestEntry("runtime/ModoriLiveResearchOSBenchmark.exe", 1, "c" * 64),
    )
    raw = manifest_bytes(entries)
    parsed = parse_manifest(raw)
    assert parsed == tuple(sorted(entries, key=lambda entry: entry.path))
    assert json.loads(raw)["schema_id"] == MANIFEST_SCHEMA_ID
    assert json.loads(raw)["schema_version"] == MANIFEST_SCHEMA_VERSION
    with pytest.raises(KitContractError, match="case-colliding"):
        manifest_bytes(
            (
                ManifestEntry("runtime/Qt6Core.dll", 1, "a" * 64),
                ManifestEntry("runtime/qt6core.dll", 1, "b" * 64),
            )
        )


def test_manifest_accepts_standard_office_and_license_member_names() -> None:
    entries = (
        ManifestEntry(
            "runtime/_internal/docx/templates/default-docx-template/[Content_Types].xml",
            1,
            "a" * 64,
        ),
        ManifestEntry("runtime/_internal/licenses/Third Party (BSD).txt", 2, "b" * 64),
    )
    assert parse_manifest(manifest_bytes(entries)) == tuple(
        sorted(entries, key=lambda entry: entry.path)
    )


@pytest.mark.parametrize(
    "path",
    (
        "../escape.dll",
        "/absolute.dll",
        "C:/absolute.dll",
        "runtime\\backslash.dll",
        "runtime/file.dll:stream",
        "runtime/CON",
        "runtime/com1.txt",
        "runtime/trailing. ",
        "runtime//double.dll",
    ),
)
def test_manifest_rejects_traversal_absolute_ads_device_and_ambiguous_paths(
    path: str,
) -> None:
    with pytest.raises(KitContractError, match="path"):
        ManifestEntry(path, 1, "a" * 64)


def test_package_lock_is_canonical_sorted_and_normalizes_names() -> None:
    raw = _lock()
    entries = parse_package_lock(raw)
    assert entries == tuple(sorted(entries, key=lambda entry: entry.name))
    parsed = json.loads(raw)
    assert parsed["schema_id"] == PACKAGE_LOCK_SCHEMA_ID
    assert parsed["schema_version"] == PACKAGE_LOCK_SCHEMA_VERSION
    with pytest.raises(KitContractError, match="duplicate"):
        package_lock_bytes(
            (
                PackageLockEntry("PySide6", "6.11.1"),
                PackageLockEntry("pyside6", "6.11.1"),
            )
        )
    with pytest.raises(KitContractError, match="canonical"):
        parse_package_lock(raw + b"\n")


def test_canonical_json_rejects_floats_unsafe_integers_non_nfc_and_bad_keys() -> None:
    with pytest.raises(KitContractError, match="float"):
        canonical_json_bytes({"value": 1.5})
    with pytest.raises(KitContractError, match="safe range"):
        canonical_json_bytes({"value": 9_007_199_254_740_992})
    with pytest.raises(KitContractError, match="NFC"):
        canonical_json_bytes({"value": "한"})
    with pytest.raises(KitContractError, match="key"):
        canonical_json_bytes({"UPPER": "value"})


def test_kit_name_is_commit_and_python_pinned() -> None:
    assert kit_name(SOURCE_COMMIT, "3.12.10") == (
        "modori-live-research-os-office-kit-111111111111-py31210"
    )
    with pytest.raises(KitContractError, match="commit"):
        kit_name("short", "3.12.10")
    with pytest.raises(KitContractError, match="Python"):
        kit_name(SOURCE_COMMIT, "3.13.0")
