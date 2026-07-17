from __future__ import annotations

from collections.abc import Mapping
import ctypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


_SOURCE_ROOT = Path(__file__).parent.parent / "src"
_REPOSITORY_ROOT = _SOURCE_ROOT.parent
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from modori.research_memory.canonical import canonical_bytes  # noqa: E402


_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_AFFINITY = 0x00000010
_JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
_JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_REQUIRED_LIMIT_FLAGS = (
    _JOB_OBJECT_LIMIT_AFFINITY
    | _JOB_OBJECT_LIMIT_PROCESS_MEMORY
    | _JOB_OBJECT_LIMIT_JOB_MEMORY
    | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
)
_READY_TOKEN = "modori_constrained_benchmark_ready_v1"
_GO_TOKEN = "go"


class ConstraintError(RuntimeError):
    """Raised when Windows cannot prove the requested process constraints."""


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", ctypes.c_ulong),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", ctypes.c_ulong),
        ("affinity", ctypes.c_size_t),
        ("priority_class", ctypes.c_ulong),
        ("scheduling_class", ctypes.c_ulong),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _BasicLimitInformation),
        ("io_info", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


@dataclass(frozen=True)
class WindowsConstraintEvidence:
    observed_cpu_count: int
    affinity_mask: int
    process_memory_limit_bytes: int
    job_memory_limit_bytes: int
    job_limit_flags: int

    def __post_init__(self) -> None:
        if self.observed_cpu_count < 1:
            raise ConstraintError("observed_cpu_count must be positive")
        if self.affinity_mask < 1:
            raise ConstraintError("affinity_mask must be positive")
        if self.process_memory_limit_bytes < 1 or self.job_memory_limit_bytes < 1:
            raise ConstraintError("memory limits must be positive")
        if self.job_limit_flags & _REQUIRED_LIMIT_FLAGS != _REQUIRED_LIMIT_FLAGS:
            raise ConstraintError("required Windows Job Object flags are absent")


def _select_lowest_affinity_mask(available_mask: int, cpu_count: int) -> int:
    if type(cpu_count) is not int or cpu_count < 1:
        raise ConstraintError("cpu_count must be a positive integer")
    if type(available_mask) is not int or available_mask < 1:
        raise ConstraintError("available affinity mask must be positive")
    selected = 0
    remaining = cpu_count
    bit = 1
    while bit <= available_mask and remaining:
        if available_mask & bit:
            selected |= bit
            remaining -= 1
        bit <<= 1
    if remaining:
        raise ConstraintError("requested CPUs exceed the available affinity mask")
    return selected


def _kernel32() -> Any:
    if os.name != "nt":
        raise ConstraintError("Windows Job Objects are available only on Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    kernel32.SetInformationJobObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    kernel32.SetInformationJobObject.restype = ctypes.c_int
    kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel32.AssignProcessToJobObject.restype = ctypes.c_int
    kernel32.QueryInformationJobObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    kernel32.QueryInformationJobObject.restype = ctypes.c_int
    kernel32.GetProcessAffinityMask.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.GetProcessAffinityMask.restype = ctypes.c_int
    kernel32.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    kernel32.SetProcessAffinityMask.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32


def _windows_error(operation: str) -> ConstraintError:
    return ConstraintError(f"{operation} failed with Windows error {ctypes.get_last_error()}")


class WindowsJobConstraint:
    """Own a Job Object handle until the constrained child has exited."""

    def __init__(
        self,
        job_handle: int,
        evidence: WindowsConstraintEvidence,
    ) -> None:
        self._job_handle = job_handle
        self.evidence = evidence
        self._closed = False

    @classmethod
    def attach(
        cls,
        process: subprocess.Popen[str],
        *,
        cpu_count: int,
        memory_limit_bytes: int,
    ) -> WindowsJobConstraint:
        if type(memory_limit_bytes) is not int or memory_limit_bytes < 1:
            raise ConstraintError("memory_limit_bytes must be a positive integer")
        if process.poll() is not None:
            raise ConstraintError("cannot constrain a process that already exited")
        raw_process_handle = getattr(process, "_handle", None)
        if raw_process_handle is None:
            raise ConstraintError("subprocess does not expose a Windows process handle")
        process_handle = ctypes.c_void_p(int(raw_process_handle))
        kernel32 = _kernel32()
        process_mask = ctypes.c_size_t()
        system_mask = ctypes.c_size_t()
        if not kernel32.GetProcessAffinityMask(
            process_handle,
            ctypes.byref(process_mask),
            ctypes.byref(system_mask),
        ):
            raise _windows_error("GetProcessAffinityMask")
        selected_mask = _select_lowest_affinity_mask(process_mask.value, cpu_count)
        job_handle = kernel32.CreateJobObjectW(None, None)
        if not job_handle:
            raise _windows_error("CreateJobObjectW")
        try:
            limits = _ExtendedLimitInformation()
            limits.basic_limit_information.limit_flags = _REQUIRED_LIMIT_FLAGS
            limits.basic_limit_information.affinity = selected_mask
            limits.process_memory_limit = memory_limit_bytes
            limits.job_memory_limit = memory_limit_bytes
            if not kernel32.SetInformationJobObject(
                job_handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            ):
                raise _windows_error("SetInformationJobObject")
            if not kernel32.AssignProcessToJobObject(job_handle, process_handle):
                raise _windows_error("AssignProcessToJobObject")
            if not kernel32.SetProcessAffinityMask(process_handle, selected_mask):
                raise _windows_error("SetProcessAffinityMask")
            observed_limits = _ExtendedLimitInformation()
            returned_length = ctypes.c_ulong()
            if not kernel32.QueryInformationJobObject(
                job_handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(observed_limits),
                ctypes.sizeof(observed_limits),
                ctypes.byref(returned_length),
            ):
                raise _windows_error("QueryInformationJobObject")
            observed_process_mask = ctypes.c_size_t()
            observed_system_mask = ctypes.c_size_t()
            if not kernel32.GetProcessAffinityMask(
                process_handle,
                ctypes.byref(observed_process_mask),
                ctypes.byref(observed_system_mask),
            ):
                raise _windows_error("GetProcessAffinityMask after assignment")
            evidence = WindowsConstraintEvidence(
                observed_cpu_count=observed_process_mask.value.bit_count(),
                affinity_mask=observed_process_mask.value,
                process_memory_limit_bytes=int(observed_limits.process_memory_limit),
                job_memory_limit_bytes=int(observed_limits.job_memory_limit),
                job_limit_flags=int(
                    observed_limits.basic_limit_information.limit_flags
                ),
            )
            if evidence.observed_cpu_count != cpu_count:
                raise ConstraintError("Windows did not apply the requested CPU affinity")
            if (
                evidence.process_memory_limit_bytes != memory_limit_bytes
                or evidence.job_memory_limit_bytes != memory_limit_bytes
            ):
                raise ConstraintError("Windows did not apply the requested memory limits")
            return cls(int(job_handle), evidence)
        except Exception:
            kernel32.CloseHandle(job_handle)
            raise

    def close(self) -> None:
        if self._closed:
            return
        kernel32 = _kernel32()
        if not kernel32.CloseHandle(ctypes.c_void_p(self._job_handle)):
            raise _windows_error("CloseHandle")
        self._closed = True

    def __enter__(self) -> WindowsJobConstraint:
        if self._closed:
            raise ConstraintError("constraint lease is closed")
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


def build_constrained_payload(
    benchmark: Mapping[str, object],
    *,
    requested_cpu_count: int,
    observed_cpu_count: int,
    requested_memory_limit_bytes: int,
    observed_process_memory_limit_bytes: int,
    observed_job_memory_limit_bytes: int,
    affinity_mask: int,
    job_limit_flags: int,
) -> dict[str, object]:
    if benchmark.get("schema_id") != "modori.research_memory_benchmark":
        raise ConstraintError("child returned an unsupported benchmark payload")
    environment = benchmark.get("environment")
    if not isinstance(environment, Mapping):
        raise ConstraintError("child benchmark environment is absent")
    child_cpu_count = environment.get("effective_logical_cpu_count")
    if type(child_cpu_count) is not int or child_cpu_count != observed_cpu_count:
        raise ConstraintError("child did not observe the enforced CPU affinity")
    return {
        "schema_id": "modori.constrained_research_memory_benchmark",
        "schema_version": 1,
        "evidence_level": "process_constrained_host",
        "office_hardware_claim_allowed": False,
        "constraints": {
            "requested_cpu_count": requested_cpu_count,
            "observed_cpu_count": observed_cpu_count,
            "requested_memory_limit_bytes": requested_memory_limit_bytes,
            "observed_process_memory_limit_bytes": (
                observed_process_memory_limit_bytes
            ),
            "observed_job_memory_limit_bytes": observed_job_memory_limit_bytes,
            "affinity_mask_hex": format(affinity_mask, "#x"),
            "job_limit_flags": job_limit_flags,
        },
        "limitations": [
            "host_os_cache_not_limited",
            "not_a_vm",
            "storage_not_throttled",
        ],
        "benchmark": dict(benchmark),
    }


def run_constrained_benchmark() -> dict[str, object]:
    if os.name != "nt":
        raise ConstraintError("constrained benchmark runner requires Windows")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        (
            str(_SOURCE_ROOT),
            str(_REPOSITORY_ROOT),
            environment.get("PYTHONPATH", ""),
        )
    )
    child_code = (
        "import sys;"
        f"print('{_READY_TOKEN}',flush=True);"
        f"assert sys.stdin.readline().strip()=='{_GO_TOKEN}';"
        "from scripts.benchmark_research_memory import main;"
        "raise SystemExit(main())"
    )
    process = subprocess.Popen(
        [getattr(sys, "_base_executable", sys.executable), "-c", child_code],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.stdout is None or process.stdin is None:
        process.kill()
        raise ConstraintError("failed to create benchmark control pipes")
    lease: WindowsJobConstraint | None = None
    try:
        if process.stdout.readline().strip() != _READY_TOKEN:
            raise ConstraintError("benchmark child did not enter its ready state")
        requested_memory = 8 * 1024 * 1024 * 1024
        lease = WindowsJobConstraint.attach(
            process,
            cpu_count=2,
            memory_limit_bytes=requested_memory,
        )
        process.stdin.write(_GO_TOKEN + "\n")
        process.stdin.flush()
        process.stdin.close()
        remaining_stdout = process.stdout.read()
        stderr = "" if process.stderr is None else process.stderr.read()
        return_code = process.wait(timeout=900)
        if return_code != 0:
            raise ConstraintError(
                f"benchmark child failed with exit {return_code}: {stderr.strip()}"
            )
        lines = [line for line in remaining_stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            raise ConstraintError("benchmark child returned an ambiguous payload")
        try:
            benchmark = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise ConstraintError("benchmark child returned invalid JSON") from exc
        if not isinstance(benchmark, Mapping):
            raise ConstraintError("benchmark child payload must be an object")
        evidence = lease.evidence
        return build_constrained_payload(
            benchmark,
            requested_cpu_count=2,
            observed_cpu_count=evidence.observed_cpu_count,
            requested_memory_limit_bytes=requested_memory,
            observed_process_memory_limit_bytes=(
                evidence.process_memory_limit_bytes
            ),
            observed_job_memory_limit_bytes=evidence.job_memory_limit_bytes,
            affinity_mask=evidence.affinity_mask,
            job_limit_flags=evidence.job_limit_flags,
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=20)
        if lease is not None:
            lease.close()


def main() -> int:
    payload = run_constrained_benchmark()
    print(canonical_bytes(payload).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
