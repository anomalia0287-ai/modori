from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from modori.research_memory.canonical import canonical_bytes
from scripts.run_constrained_research_memory_benchmark import (
    ConstraintError,
    WindowsJobConstraint,
    _select_lowest_affinity_mask,
    build_constrained_payload,
)


def test_select_lowest_affinity_mask_uses_only_available_processors() -> None:
    assert _select_lowest_affinity_mask(0b10110, 2) == 0b00110
    assert _select_lowest_affinity_mask(0b10110, 3) == 0b10110
    with pytest.raises(ConstraintError, match="available"):
        _select_lowest_affinity_mask(0b00100, 2)
    with pytest.raises(ConstraintError, match="positive"):
        _select_lowest_affinity_mask(0b00100, 0)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object gate")
def test_windows_job_enforces_two_cpu_affinity_and_eight_gibibyte_memory_limit() -> None:
    child_code = r"""
import ctypes
import json
import sys

print("ready", flush=True)
if sys.stdin.readline().strip() != "go":
    raise SystemExit(2)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
get_current_process = kernel32.GetCurrentProcess
get_current_process.argtypes = []
get_current_process.restype = ctypes.c_void_p
get_affinity = kernel32.GetProcessAffinityMask
get_affinity.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(ctypes.c_size_t),
]
get_affinity.restype = ctypes.c_int
process_mask = ctypes.c_size_t()
system_mask = ctypes.c_size_t()
if not get_affinity(
    get_current_process(),
    ctypes.byref(process_mask),
    ctypes.byref(system_mask),
):
    raise SystemExit(3)
print(json.dumps({"cpu_count": process_mask.value.bit_count()}), flush=True)
"""
    process = subprocess.Popen(
        [getattr(sys, "_base_executable", sys.executable), "-c", child_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    lease: WindowsJobConstraint | None = None
    try:
        assert process.stdout.readline().strip() == "ready"
        lease = WindowsJobConstraint.attach(
            process,
            cpu_count=2,
            memory_limit_bytes=8 * 1024 * 1024 * 1024,
        )
        evidence = lease.evidence
        assert evidence.observed_cpu_count == 2
        assert evidence.process_memory_limit_bytes == 8 * 1024 * 1024 * 1024
        assert evidence.job_memory_limit_bytes == 8 * 1024 * 1024 * 1024
        process.stdin.write("go\n")
        process.stdin.flush()
        observed = json.loads(process.stdout.readline())
        assert observed == {"cpu_count": 2}
        assert process.wait(timeout=20) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        if lease is not None:
            lease.close()


def test_constrained_payload_refuses_to_claim_real_office_hardware() -> None:
    benchmark = {
        "schema_id": "modori.research_memory_benchmark",
        "schema_version": 1,
        "environment": {
            "effective_logical_cpu_count": 2,
            "storage_type": "unclassified",
        },
    }
    payload = build_constrained_payload(
        benchmark,
        requested_cpu_count=2,
        observed_cpu_count=2,
        requested_memory_limit_bytes=8 * 1024 * 1024 * 1024,
        observed_process_memory_limit_bytes=8 * 1024 * 1024 * 1024,
        observed_job_memory_limit_bytes=8 * 1024 * 1024 * 1024,
        affinity_mask=3,
        job_limit_flags=0x2310,
    )
    assert payload["evidence_level"] == "process_constrained_host"
    assert payload["office_hardware_claim_allowed"] is False
    assert payload["limitations"] == [
        "host_os_cache_not_limited",
        "not_a_vm",
        "storage_not_throttled",
    ]
    assert canonical_bytes(payload)


def test_constrained_payload_rejects_child_affinity_mismatch() -> None:
    benchmark = {
        "schema_id": "modori.research_memory_benchmark",
        "schema_version": 1,
        "environment": {
            "effective_logical_cpu_count": 16,
            "storage_type": "unclassified",
        },
    }
    with pytest.raises(ConstraintError, match="child.*CPU affinity"):
        build_constrained_payload(
            benchmark,
            requested_cpu_count=2,
            observed_cpu_count=2,
            requested_memory_limit_bytes=8 * 1024 * 1024 * 1024,
            observed_process_memory_limit_bytes=8 * 1024 * 1024 * 1024,
            observed_job_memory_limit_bytes=8 * 1024 * 1024 * 1024,
            affinity_mask=3,
            job_limit_flags=0x2310,
        )
