from __future__ import annotations

from dataclasses import replace
import json

import pytest

from scripts.office_research_memory_kit import (
    RUNTIME_SPEC,
    KitContractError,
    ManifestEntry,
    canonical_json_bytes,
    evaluate_measurements,
    manifest_bytes,
    parse_manifest,
)


def _hardware(
    *,
    media_type: str = "hdd",
    bus_type: str = "sata",
    cores: int = 2,
    memory_gib: int = 8,
    ac_power: bool = True,
    drive_type: str = "fixed",
) -> dict[str, object]:
    return {
        "windows_version": "Windows 10.0.19045",
        "machine": "amd64",
        "logical_cpu_count": 4,
        "physical_core_count": cores,
        "physical_memory_bytes": memory_gib * 1024**3,
        "ac_power": ac_power,
        "drive_type": drive_type,
        "storage": {
            "bus_type": bus_type,
            "media_type": media_type,
            "friendly_name": "Synthetic Test Disk",
            "filesystem": "ntfs",
            "free_bytes": 50 * 1024**3,
        },
    }


def _run(
    *,
    open_max_us: int = 900_000,
    append_p95_us: int = 40_000,
    bundle_max_us: int = 1_900_000,
    peak_bytes: int = 180 * 1024**2,
) -> dict[str, object]:
    return {
        "schema_id": "modori.research_memory_benchmark",
        "schema_version": 1,
        "environment": {"effective_logical_cpu_count": 4},
        "open_replay": {
            "max_us": open_max_us,
            "process_peak_working_set_bytes": peak_bytes,
        },
        "durable_append": {"p95_us": append_p95_us},
        "bundle_validation": {"max_us": bundle_max_us},
    }


def test_manifest_is_canonical_sorted_and_rejects_traversal() -> None:
    entries = (
        ManifestEntry("payload/src/modori/__init__.py", 2, "b" * 64),
        ManifestEntry("runtime/python.exe", 3, "a" * 64),
    )
    raw = manifest_bytes(entries)
    assert parse_manifest(raw) == tuple(sorted(entries, key=lambda item: item.path))
    assert json.loads(raw)["entries"][0]["path"] == (
        "payload/src/modori/__init__.py"
    )
    with pytest.raises(KitContractError, match="relative"):
        ManifestEntry("../outside", 1, "c" * 64)
    with pytest.raises(KitContractError, match="relative"):
        ManifestEntry("C:/outside", 1, "c" * 64)


def test_manifest_rejects_duplicates_and_noncanonical_bytes() -> None:
    entry = ManifestEntry("runtime/python.exe", 3, "a" * 64)
    with pytest.raises(KitContractError, match="duplicate"):
        manifest_bytes((entry, entry))
    raw = manifest_bytes((entry,))
    with pytest.raises(KitContractError, match="canonical"):
        parse_manifest(raw.replace(b"{", b"{ ", 1))


def test_canonical_json_rejects_float_non_nfc_and_invalid_keys() -> None:
    with pytest.raises(KitContractError, match="float"):
        canonical_json_bytes({"value": 1.5})
    with pytest.raises(KitContractError, match="NFC"):
        canonical_json_bytes({"value": "한"})
    with pytest.raises(KitContractError, match="key"):
        canonical_json_bytes({"UPPER": "value"})


def test_runtime_pin_matches_official_archive_and_inventory() -> None:
    assert RUNTIME_SPEC.version == "3.12.10"
    assert RUNTIME_SPEC.sqlite_version == "3.49.1"
    assert RUNTIME_SPEC.url == (
        "https://www.python.org/ftp/python/3.12.10/"
        "python-3.12.10-embed-amd64.zip"
    )
    assert RUNTIME_SPEC.sha256 == (
        "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
    )
    assert len(RUNTIME_SPEC.expected_files) == 35
    assert {
        "LICENSE.txt",
        "_sqlite3.pyd",
        "python.exe",
        "python312._pth",
        "python312.dll",
        "python312.zip",
        "sqlite3.dll",
    } <= set(RUNTIME_SPEC.expected_files)
    with pytest.raises(KitContractError, match="digest"):
        replace(RUNTIME_SPEC, sha256="wrong")


def test_three_hdd_runs_pass_only_when_every_worst_case_passes() -> None:
    hardware = _hardware(media_type="hdd", bus_type="sata")
    runs = tuple(
        _run(open_max_us=2_900_000, append_p95_us=140_000) for _ in range(3)
    )
    result = evaluate_measurements(hardware, runs)
    assert result == {
        "measurement_complete": True,
        "provisional_gate_pass": True,
        "office_hardware_claim_allowed": False,
        "reason_codes": [],
        "thresholds": {
            "bundle_validation_max_us": 2_000_000,
            "durable_append_p95_us": 150_000,
            "open_replay_max_us": 3_000_000,
            "peak_working_set_bytes": 192 * 1024**2,
        },
    }


def test_ssd_gate_uses_every_outer_run_not_a_favorable_average() -> None:
    runs = (_run(), _run(open_max_us=1_000_001), _run())
    result = evaluate_measurements(_hardware(media_type="ssd"), runs)
    assert result["provisional_gate_pass"] is False
    assert result["reason_codes"] == ["open_replay_exceeded"]


def test_above_target_cpu_or_unknown_storage_never_provisionally_passes() -> None:
    result = evaluate_measurements(
        _hardware(media_type="unknown", bus_type="unknown", cores=4),
        tuple(_run() for _ in range(3)),
    )
    assert result["measurement_complete"] is True
    assert result["provisional_gate_pass"] is False
    assert result["office_hardware_claim_allowed"] is False
    assert result["reason_codes"] == [
        "cpu_profile_above_target",
        "storage_profile_unqualified",
    ]


@pytest.mark.parametrize(
    ("hardware", "reason"),
    [
        (_hardware(memory_gib=16), "memory_profile_above_target"),
        (_hardware(ac_power=False), "ac_power_required"),
        (_hardware(drive_type="removable"), "execution_volume_unqualified"),
        (
            _hardware(media_type="hdd", bus_type="usb"),
            "storage_profile_unqualified",
        ),
    ],
)
def test_hardware_profile_failures_are_explicit(
    hardware: dict[str, object],
    reason: str,
) -> None:
    result = evaluate_measurements(hardware, tuple(_run() for _ in range(3)))
    assert result["provisional_gate_pass"] is False
    assert reason in result["reason_codes"]


def test_measurement_requires_exactly_three_typed_runs() -> None:
    result = evaluate_measurements(_hardware(), (_run(), _run()))
    assert result["measurement_complete"] is False
    assert result["reason_codes"] == ["measurement_incomplete"]
    malformed = _run()
    del malformed["bundle_validation"]
    with pytest.raises(KitContractError, match="bundle_validation"):
        evaluate_measurements(_hardware(), (_run(), _run(), malformed))
