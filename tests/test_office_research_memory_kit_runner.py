from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.office_research_memory_kit import (
    canonical_json_bytes,
    evaluate_measurements,
)
from scripts.run_office_research_memory_benchmark import (
    OfficeBenchmarkError,
    parse_hardware_probe,
    run_benchmark_child,
    run_office_measurement,
    write_result_files,
)
from tests.test_office_research_memory_kit_contract import _hardware, _run
from tests.test_office_research_memory_kit_verifier import _fake_kit


def _probe_payload() -> dict[str, object]:
    return {
        "ac_power": True,
        "drive_type": "fixed",
        "hypervisor_present": False,
        "logical_cpu_count": 4,
        "machine": "AMD64",
        "manufacturer": "Example",
        "model": "OfficeBook",
        "physical_core_count": 2,
        "physical_memory_bytes": 8 * 1024**3,
        "storage": {
            "bus_type": "SATA",
            "filesystem": "NTFS",
            "free_bytes": 50 * 1024**3,
            "friendly_name": "Example Disk",
            "media_type": "HDD",
        },
        "windows_version": "Windows 10.0.19045",
    }


def test_hardware_probe_parser_keeps_only_approved_normalized_fields() -> None:
    profile = parse_hardware_probe(json.dumps(_probe_payload()))
    assert profile["machine"] == "amd64"
    assert profile["storage"]["media_type"] == "hdd"
    assert profile["storage"]["bus_type"] == "sata"
    encoded = canonical_json_bytes(profile).decode("utf-8")
    assert "computer_name" not in encoded
    assert "serial" not in encoded


@pytest.mark.parametrize(
    "forbidden",
    ["computer_name", "user_name", "user_profile", "serial_number", "ip_address"],
)
def test_hardware_probe_rejects_privacy_fields(forbidden: str) -> None:
    payload = _probe_payload()
    payload[forbidden] = "private"
    with pytest.raises(OfficeBenchmarkError, match="privacy|field"):
        parse_hardware_probe(json.dumps(payload))


def test_hardware_probe_rejects_unknown_fields_and_noncanonical_numbers() -> None:
    payload = _probe_payload()
    payload["unexpected"] = None
    with pytest.raises(OfficeBenchmarkError, match="field"):
        parse_hardware_probe(json.dumps(payload))
    payload = _probe_payload()
    payload["physical_memory_bytes"] = 8.5
    with pytest.raises(OfficeBenchmarkError, match="integer"):
        parse_hardware_probe(json.dumps(payload))


def test_office_measurement_uses_exactly_three_child_runs_and_writes_results(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    calls: list[int] = []

    def child(_verified, _measurement_id: str, run_index: int):
        calls.append(run_index)
        return _run(open_max_us=2_500_000, append_p95_us=100_000)

    receipt = run_office_measurement(
        root,
        hardware_probe=lambda _root: parse_hardware_probe(
            json.dumps(_probe_payload())
        ),
        child_executor=child,
        measurement_id="a" * 32,
        now_utc=lambda: "2026-07-12T08:00:00Z",
    )
    assert calls == [1, 2, 3]
    assert receipt.result["measurement_id"] == "a" * 32
    assert len(receipt.result["runs"]) == 3
    assert receipt.result["evaluation"]["provisional_gate_pass"] is True
    assert receipt.result["evaluation"]["office_hardware_claim_allowed"] is False
    assert receipt.json_path.read_bytes() == canonical_json_bytes(receipt.result)
    assert receipt.digest_path.read_text(encoding="ascii").endswith(
        f"  {receipt.json_path.name}\n"
    )
    assert "제품 주장 권한: 없음" in receipt.summary_path.read_text(encoding="utf-8")


def test_battery_power_refuses_before_any_child_run(tmp_path: Path) -> None:
    root = _fake_kit(tmp_path)
    payload = _probe_payload()
    payload["ac_power"] = False
    calls = 0

    def child(_verified, _measurement_id: str, _run_index: int):
        nonlocal calls
        calls += 1
        return _run()

    with pytest.raises(OfficeBenchmarkError, match="AC power"):
        run_office_measurement(
            root,
            hardware_probe=lambda _root: parse_hardware_probe(json.dumps(payload)),
            child_executor=child,
            measurement_id="b" * 32,
        )
    assert calls == 0


def test_result_writer_never_overwrites_or_escapes_results(tmp_path: Path) -> None:
    results = (tmp_path / "results").resolve()
    results.mkdir()
    hardware = _hardware()
    runs = (_run(), _run(), _run())
    result = {
        "schema_id": "modori.office_research_memory_benchmark",
        "schema_version": 1,
        "measurement_id": "c" * 32,
        "hardware": hardware,
        "runs": list(runs),
        "evaluation": evaluate_measurements(hardware, runs),
    }
    first = write_result_files(results, "c" * 32, result)
    assert all(path.parent == results for path in first)
    with pytest.raises(OfficeBenchmarkError, match="exists"):
        write_result_files(results, "c" * 32, result)
    with pytest.raises(OfficeBenchmarkError, match="measurement"):
        write_result_files(results, "../escape", result)


def test_invalid_summary_contract_leaves_no_partial_result_files(
    tmp_path: Path,
) -> None:
    results = (tmp_path / "results").resolve()
    results.mkdir()
    invalid = {
        "schema_id": "modori.office_research_memory_benchmark",
        "schema_version": 1,
        "measurement_id": "e" * 32,
        "hardware": _hardware(),
        "runs": [_run(), _run(), _run()],
        "evaluation": {"office_hardware_claim_allowed": False},
    }
    with pytest.raises(OfficeBenchmarkError, match="summary"):
        write_result_files(results, "e" * 32, invalid)
    assert tuple(results.iterdir()) == ()


def test_measurement_does_not_leak_absolute_paths_or_host_identifiers(
    tmp_path: Path,
) -> None:
    root = _fake_kit(tmp_path)
    receipt = run_office_measurement(
        root,
        hardware_probe=lambda _root: parse_hardware_probe(
            json.dumps(_probe_payload())
        ),
        child_executor=lambda *_args: _run(),
        measurement_id="d" * 32,
        now_utc=lambda: "2026-07-12T08:00:00Z",
    )
    encoded = receipt.json_path.read_text(encoding="utf-8")
    assert str(tmp_path) not in encoded
    assert "computer_name" not in encoded
    assert "user_name" not in encoded


def test_child_uses_owned_temp_and_keeps_localized_stderr_as_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fake_kit(tmp_path)
    captured: dict[str, object] = {}

    def completed(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=canonical_json_bytes(_run()) + b"\n",
            stderr=b"",
        )

    monkeypatch.setattr(subprocess, "run", completed)
    from scripts.verify_office_research_memory_kit import verify_kit

    payload = run_benchmark_child(verify_kit(root), "f" * 32, 1)
    assert payload["schema_id"] == "modori.research_memory_benchmark"
    assert "encoding" not in captured
    assert "errors" not in captured
    environment = captured["env"]
    assert environment["TEMP"] == str(root / "work")
    assert environment["TMP"] == str(root / "work")
    assert captured["command"][1:3] == ["-B", "-I"]


def test_child_binary_stderr_is_reduced_to_a_typed_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _fake_kit(tmp_path)

    def failed(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=b"",
            stderr=b"\xc8localized",
        )

    monkeypatch.setattr(subprocess, "run", failed)
    from scripts.verify_office_research_memory_kit import verify_kit

    with pytest.raises(OfficeBenchmarkError, match="benchmark_child_exit_1"):
        run_benchmark_child(verify_kit(root), "f" * 32, 1)
