"""Offline target runner for the portable Decision Ledger benchmark kit."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
import uuid


_SCRIPT_DIR = Path(__file__).resolve().parent
_PAYLOAD_ROOT = _SCRIPT_DIR.parent
sys.dont_write_bytecode = True
if str(_PAYLOAD_ROOT) not in sys.path:
    sys.path.insert(0, str(_PAYLOAD_ROOT))

from scripts.office_research_memory_kit import (  # noqa: E402
    KitContractError,
    canonical_json_bytes,
    evaluate_measurements,
)
from scripts.verify_office_research_memory_kit import (  # noqa: E402
    KitVerificationError,
    VerifiedKit,
    verify_kit,
)


_RESULT_SCHEMA_ID = "modori.office_research_memory_benchmark"
_MEASUREMENT_RE = re.compile(r"^[0-9a-f]{32}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:$")
_TOP_HARDWARE_FIELDS = frozenset(
    {
        "ac_power",
        "drive_type",
        "hypervisor_present",
        "logical_cpu_count",
        "machine",
        "manufacturer",
        "model",
        "physical_core_count",
        "physical_memory_bytes",
        "storage",
        "windows_version",
    }
)
_STORAGE_FIELDS = frozenset(
    {"bus_type", "filesystem", "free_bytes", "friendly_name", "media_type"}
)
_PRIVACY_DENYLIST = frozenset(
    {
        "computer_name",
        "host_name",
        "installed_programs",
        "ip_address",
        "kit_root",
        "mac_address",
        "network",
        "path",
        "serial_number",
        "user_name",
        "user_profile",
    }
)
_DRIVE_TYPES = {
    0: "unknown",
    1: "no_root",
    2: "removable",
    3: "fixed",
    4: "remote",
    5: "cdrom",
    6: "ramdisk",
}


class OfficeBenchmarkError(RuntimeError):
    """Raised when the portable measurement cannot produce valid evidence."""


@dataclass(frozen=True)
class MeasurementReceipt:
    result: Mapping[str, object]
    json_path: Path
    digest_path: Path
    summary_path: Path


class _DuplicateKey(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _text(value: object, field: str, *, lower: bool = False) -> str:
    if not isinstance(value, str):
        raise OfficeBenchmarkError(f"{field} must be text")
    if value != unicodedata.normalize("NFC", value):
        raise OfficeBenchmarkError(f"{field} must use NFC text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise OfficeBenchmarkError(f"{field} must use valid UTF-8") from exc
    normalized = value.strip() or "unknown"
    return normalized.lower() if lower else normalized


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise OfficeBenchmarkError(f"{field} must be an integer")
    return value


def _privacy_scan(value: object) -> None:
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, item in current.items():
                if str(key).lower() in _PRIVACY_DENYLIST:
                    raise OfficeBenchmarkError("hardware probe contains a privacy field")
                stack.append(item)
        elif isinstance(current, list):
            stack.extend(current)


def parse_hardware_probe(raw: str) -> dict[str, object]:
    """Parse only the closed, non-identifying hardware evidence schema."""

    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 64 * 1024:
        raise OfficeBenchmarkError("hardware probe output is invalid or oversized")
    try:
        parsed = json.loads(raw, object_pairs_hook=_pairs_hook)
    except (_DuplicateKey, json.JSONDecodeError) as exc:
        raise OfficeBenchmarkError("hardware probe output is not strict JSON") from exc
    _privacy_scan(parsed)
    if not isinstance(parsed, dict) or set(parsed) != _TOP_HARDWARE_FIELDS:
        raise OfficeBenchmarkError("hardware probe top-level field set is invalid")
    storage = parsed["storage"]
    if not isinstance(storage, dict) or set(storage) != _STORAGE_FIELDS:
        raise OfficeBenchmarkError("hardware probe storage field set is invalid")
    ac_power = parsed["ac_power"]
    hypervisor = parsed["hypervisor_present"]
    if not isinstance(ac_power, bool) or not isinstance(hypervisor, bool):
        raise OfficeBenchmarkError("hardware probe boolean field is invalid")
    media = _text(storage["media_type"], "storage.media_type", lower=True)
    if media in {"unspecified", "unclassified", "unknown"}:
        media = "unknown"
    result = {
        "ac_power": ac_power,
        "drive_type": _text(parsed["drive_type"], "drive_type", lower=True),
        "hypervisor_present": hypervisor,
        "logical_cpu_count": _integer(
            parsed["logical_cpu_count"], "logical_cpu_count", minimum=1
        ),
        "machine": _text(parsed["machine"], "machine", lower=True),
        "manufacturer": _text(parsed["manufacturer"], "manufacturer"),
        "model": _text(parsed["model"], "model"),
        "physical_core_count": _integer(
            parsed["physical_core_count"], "physical_core_count", minimum=1
        ),
        "physical_memory_bytes": _integer(
            parsed["physical_memory_bytes"],
            "physical_memory_bytes",
            minimum=1,
        ),
        "storage": {
            "bus_type": _text(storage["bus_type"], "storage.bus_type", lower=True),
            "filesystem": _text(
                storage["filesystem"], "storage.filesystem", lower=True
            ),
            "free_bytes": _integer(storage["free_bytes"], "storage.free_bytes"),
            "friendly_name": _text(
                storage["friendly_name"], "storage.friendly_name"
            ),
            "media_type": media,
        },
        "windows_version": _text(parsed["windows_version"], "windows_version"),
    }
    try:
        canonical_json_bytes(result)
    except KitContractError as exc:
        raise OfficeBenchmarkError("hardware probe is not canonicalizable") from exc
    return result


class _SystemPowerStatus(ctypes.Structure):
    _fields_ = [
        ("ac_line_status", ctypes.c_ubyte),
        ("battery_flag", ctypes.c_ubyte),
        ("battery_life_percent", ctypes.c_ubyte),
        ("system_status_flag", ctypes.c_ubyte),
        ("battery_life_time", ctypes.c_ulong),
        ("battery_full_life_time", ctypes.c_ulong),
    ]


def _is_ac_power() -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_status = kernel32.GetSystemPowerStatus
    get_status.argtypes = [ctypes.POINTER(_SystemPowerStatus)]
    get_status.restype = ctypes.c_int
    status = _SystemPowerStatus()
    if not get_status(ctypes.byref(status)):
        raise OfficeBenchmarkError("power_status_probe_failed")
    if status.ac_line_status == 255:
        raise OfficeBenchmarkError("power_status_unknown")
    return status.ac_line_status == 1


def _drive_type(root: Path) -> str:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_drive_type = kernel32.GetDriveTypeW
    get_drive_type.argtypes = [ctypes.c_wchar_p]
    get_drive_type.restype = ctypes.c_uint
    return _DRIVE_TYPES.get(int(get_drive_type(root.anchor)), "unknown")


_POWERSHELL_PROBE = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$computer = Get-CimInstance Win32_ComputerSystem
$processors = @(Get-CimInstance Win32_Processor)
$coreCount = [int](($processors | Measure-Object -Property NumberOfCores -Sum).Sum)
$partition = Get-Partition -DriveLetter '__DRIVE__'
$disks = @($partition | Get-Disk | Sort-Object -Property Number -Unique)
$busType = 'Unknown'
$mediaType = 'Unknown'
$friendlyName = 'Unknown'
if ($disks.Count -eq 1) {
    $disk = $disks[0]
    $busType = [string]$disk.BusType
    $friendlyName = [string]$disk.FriendlyName
    $physical = @(Get-PhysicalDisk | Where-Object {
        [string]$_.DeviceId -eq [string]$disk.Number
    })
    if ($physical.Count -eq 1) {
        $mediaType = [string]$physical[0].MediaType
        if ([string]::IsNullOrWhiteSpace($friendlyName)) {
            $friendlyName = [string]$physical[0].FriendlyName
        }
    }
}
$volume = Get-Volume -DriveLetter '__DRIVE__'
[ordered]@{
    hypervisor_present = [bool]$computer.HypervisorPresent
    logical_cpu_count = [int]$computer.NumberOfLogicalProcessors
    manufacturer = [string]$computer.Manufacturer
    model = [string]$computer.Model
    physical_core_count = $coreCount
    physical_memory_bytes = [uint64]$computer.TotalPhysicalMemory
    storage = [ordered]@{
        bus_type = $busType
        filesystem = [string]$volume.FileSystem
        friendly_name = $friendlyName
        media_type = $mediaType
    }
} | ConvertTo-Json -Compress -Depth 4
"""


def probe_windows_hardware(kit_root: Path) -> dict[str, object]:
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise OfficeBenchmarkError("windows_x64_required")
    drive = kit_root.drive
    if not _DRIVE_RE.fullmatch(drive):
        raise OfficeBenchmarkError("local_drive_letter_required")
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not system_root:
        raise OfficeBenchmarkError("windows_system_root_unavailable")
    powershell = (
        Path(system_root)
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )
    if not powershell.is_file():
        raise OfficeBenchmarkError("windows_powershell_unavailable")
    script = _POWERSHELL_PROBE.replace("__DRIVE__", drive[0].upper())
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            [
                str(powershell),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="strict",
            timeout=30,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise OfficeBenchmarkError("hardware_probe_failed") from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise OfficeBenchmarkError("hardware_probe_failed")
    try:
        probed = json.loads(completed.stdout, object_pairs_hook=_pairs_hook)
    except (_DuplicateKey, json.JSONDecodeError) as exc:
        raise OfficeBenchmarkError("hardware_probe_returned_invalid_json") from exc
    if not isinstance(probed, dict) or not isinstance(probed.get("storage"), dict):
        raise OfficeBenchmarkError("hardware_probe_returned_invalid_schema")
    try:
        free_bytes = shutil.disk_usage(kit_root).free
    except OSError as exc:
        raise OfficeBenchmarkError("free_space_probe_failed") from exc
    probed.update(
        {
            "ac_power": _is_ac_power(),
            "drive_type": _drive_type(kit_root),
            "machine": platform.machine(),
            "windows_version": platform.platform(),
        }
    )
    probed["storage"]["free_bytes"] = int(free_bytes)
    return parse_hardware_probe(canonical_json_bytes(probed).decode("utf-8"))


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_measurement_id(value: str) -> str:
    if not isinstance(value, str) or not _MEASUREMENT_RE.fullmatch(value):
        raise OfficeBenchmarkError("measurement ID is invalid")
    return value


def _write_exclusive(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise OfficeBenchmarkError("result file already exists") from exc
    except OSError as exc:
        raise OfficeBenchmarkError("result file could not be written") from exc


def _summary_text(result: Mapping[str, object]) -> str:
    try:
        hardware = result["hardware"]
        evaluation = result["evaluation"]
        measurement_id = result["measurement_id"]
    except KeyError as exc:
        raise OfficeBenchmarkError("result summary field is missing") from exc
    if not isinstance(hardware, Mapping) or not isinstance(evaluation, Mapping):
        raise OfficeBenchmarkError("result summary input is invalid")
    required_evaluation = {
        "measurement_complete",
        "office_hardware_claim_allowed",
        "provisional_gate_pass",
        "reason_codes",
    }
    if not required_evaluation <= set(evaluation):
        raise OfficeBenchmarkError("result summary evaluation field is missing")
    try:
        storage = hardware["storage"]
        physical_core_count = hardware["physical_core_count"]
        physical_memory_bytes = hardware["physical_memory_bytes"]
    except KeyError as exc:
        raise OfficeBenchmarkError("result summary hardware field is missing") from exc
    if not isinstance(storage, Mapping):
        raise OfficeBenchmarkError("result storage summary input is invalid")
    reasons = evaluation["reason_codes"]
    if not isinstance(reasons, list) or not all(
        isinstance(reason, str) for reason in reasons
    ):
        raise OfficeBenchmarkError("result reason summary input is invalid")
    if evaluation["office_hardware_claim_allowed"] is not False:
        raise OfficeBenchmarkError("result summary cannot grant product claim authority")
    reason_text = ", ".join(str(item) for item in reasons) if reasons else "없음"
    lines = [
        "Modori Decision Ledger 사무용 하드웨어 측정 장부",
        f"측정 ID: {measurement_id}",
        f"CPU 물리 코어: {physical_core_count}",
        f"메모리 바이트: {physical_memory_bytes}",
        f"저장장치: {storage.get('media_type')} / {storage.get('bus_type')}",
        f"측정 완료: {str(evaluation['measurement_complete']).lower()}",
        f"잠정 성능 기준 통과: {str(evaluation['provisional_gate_pass']).lower()}",
        "제품 주장 권한: 없음",
        f"판정 코드: {reason_text}",
        "이 장부는 실제 사용자 파일이나 연구 데이터를 포함하지 않습니다.",
    ]
    return "\n".join(lines) + "\n"


def write_result_files(
    results_dir: Path,
    measurement_id: str,
    result: Mapping[str, object],
) -> tuple[Path, Path, Path]:
    measurement_id = _require_measurement_id(measurement_id)
    if not isinstance(results_dir, Path):
        raise OfficeBenchmarkError("results directory must be a Path")
    resolved = results_dir.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink():
        raise OfficeBenchmarkError("results directory is invalid")
    stem = f"modori-office-benchmark-{measurement_id}"
    json_path = resolved / f"{stem}.json"
    digest_path = resolved / f"{stem}.json.sha256"
    summary_path = resolved / f"{stem}.summary-ko.txt"
    paths = (json_path, digest_path, summary_path)
    if any(path.exists() for path in paths):
        raise OfficeBenchmarkError("result file already exists")
    try:
        raw = canonical_json_bytes(dict(result))
    except KitContractError as exc:
        raise OfficeBenchmarkError("result is outside the canonical profile") from exc
    summary_bytes = _summary_text(result).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    _write_exclusive(json_path, raw)
    _write_exclusive(
        digest_path,
        f"{digest}  {json_path.name}\n".encode("ascii"),
    )
    _write_exclusive(summary_path, summary_bytes)
    return paths


def _parse_child_payload(raw: bytes) -> Mapping[str, object]:
    if not isinstance(raw, bytes) or not raw or len(raw) > 32 * 1024 * 1024:
        raise OfficeBenchmarkError("benchmark_child_output_invalid")
    encoded = raw.strip()
    try:
        decoded = encoded.decode("utf-8", errors="strict")
        parsed = json.loads(decoded, object_pairs_hook=_pairs_hook)
    except (_DuplicateKey, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficeBenchmarkError("benchmark_child_output_invalid") from exc
    if not isinstance(parsed, dict):
        raise OfficeBenchmarkError("benchmark_child_output_invalid")
    try:
        if canonical_json_bytes(parsed) != encoded:
            raise OfficeBenchmarkError("benchmark_child_output_noncanonical")
    except KitContractError as exc:
        raise OfficeBenchmarkError("benchmark_child_output_noncanonical") from exc
    return parsed


def run_benchmark_child(
    verified: VerifiedKit,
    measurement_id: str,
    run_index: int,
) -> Mapping[str, object]:
    measurement_id = _require_measurement_id(measurement_id)
    if type(run_index) is not int or not 1 <= run_index <= 3:
        raise OfficeBenchmarkError("benchmark child index is invalid")
    runtime = verified.root / "runtime" / "python.exe"
    runner = (
        verified.root
        / "payload"
        / "scripts"
        / "run_office_research_memory_benchmark.py"
    )
    command = [
        str(runtime),
        "-B",
        "-I",
        str(runner),
        "--child-run",
        measurement_id,
        str(run_index),
    ]
    minimal_environment = {
        key: os.environ[key]
        for key in ("COMSPEC", "PATHEXT", "SystemRoot", "WINDIR")
        if key in os.environ
    }
    owned_temp = str(verified.root / "work")
    minimal_environment["TEMP"] = owned_temp
    minimal_environment["TMP"] = owned_temp
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            cwd=verified.root,
            env=minimal_environment,
            capture_output=True,
            check=False,
            timeout=1800,
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise OfficeBenchmarkError("benchmark_child_timeout") from exc
    except OSError as exc:
        raise OfficeBenchmarkError("benchmark_child_start_failed") from exc
    if completed.returncode != 0 or completed.stderr.strip():
        raise OfficeBenchmarkError(f"benchmark_child_exit_{completed.returncode}")
    return _parse_child_payload(completed.stdout)


def run_office_measurement(
    kit_root: Path,
    *,
    hardware_probe: Callable[[Path], dict[str, object]] | None = None,
    child_executor: Callable[
        [VerifiedKit, str, int], Mapping[str, object]
    ]
    | None = None,
    measurement_id: str | None = None,
    now_utc: Callable[[], str] = _now_utc,
) -> MeasurementReceipt:
    verified = verify_kit(kit_root)
    hardware = (hardware_probe or probe_windows_hardware)(verified.root)
    if hardware.get("ac_power") is not True:
        raise OfficeBenchmarkError("AC power is required")
    if hardware.get("drive_type") != "fixed":
        raise OfficeBenchmarkError("fixed internal execution volume is required")
    storage = hardware.get("storage")
    if not isinstance(storage, Mapping) or storage.get("free_bytes", 0) < 2 * 1024**3:
        raise OfficeBenchmarkError("at least 2 GiB free space is required")
    identifier = _require_measurement_id(measurement_id or uuid.uuid4().hex)
    started = now_utc()
    executor = child_executor or run_benchmark_child
    runs: list[Mapping[str, object]] = []
    for run_index in range(1, 4):
        runs.append(executor(verified, identifier, run_index))
    evaluation = evaluate_measurements(hardware, tuple(runs))
    identity = json.loads(canonical_json_bytes(dict(verified.identity)))
    result: dict[str, object] = {
        "completed_at_utc": now_utc(),
        "evaluation": evaluation,
        "hardware": hardware,
        "kit_identity": identity,
        "measurement_id": identifier,
        "runs": list(runs),
        "schema_id": _RESULT_SCHEMA_ID,
        "schema_version": 1,
        "started_at_utc": started,
    }
    json_path, digest_path, summary_path = write_result_files(
        verified.root / "results",
        identifier,
        result,
    )
    return MeasurementReceipt(
        result=result,
        json_path=json_path,
        digest_path=digest_path,
        summary_path=summary_path,
    )


def _child_run(kit_root: Path, measurement_id: str, run_index: int) -> int:
    verified = verify_kit(kit_root)
    measurement_id = _require_measurement_id(measurement_id)
    if not 1 <= run_index <= 3:
        raise OfficeBenchmarkError("benchmark child index is invalid")
    work_parent = (verified.root / "work").resolve(strict=True)
    name = f"modori-office-benchmark-{measurement_id}-run-{run_index}"
    work_root = (work_parent / name).resolve(strict=False)
    if work_root.parent != work_parent or not name.startswith(
        "modori-office-benchmark-"
    ):
        raise OfficeBenchmarkError("benchmark child work path is invalid")
    if work_root.exists():
        raise OfficeBenchmarkError("benchmark child work path already exists")
    source_root = verified.root / "payload" / "src"
    scripts_root = verified.root / "payload" / "scripts"
    sys.path.insert(0, str(source_root))
    sys.path.insert(0, str(scripts_root))
    from benchmark_research_memory import run_benchmark

    try:
        payload = run_benchmark(root=work_root)
    finally:
        if work_root.parent != work_parent or not work_root.name.startswith(
            "modori-office-benchmark-"
        ):
            raise OfficeBenchmarkError("refusing unsafe benchmark cleanup")
        if work_root.exists():
            shutil.rmtree(work_root)
    print(canonical_json_bytes(payload).decode("utf-8"))
    return 0


def _kit_root_from_script() -> Path:
    path = Path(__file__).resolve()
    if path.parent.name != "scripts" or path.parent.parent.name != "payload":
        raise OfficeBenchmarkError("runner is not inside a portable kit")
    return path.parents[2]


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        kit_root = _kit_root_from_script()
        if arguments and arguments[0] == "--child-run":
            if len(arguments) != 3:
                raise OfficeBenchmarkError("benchmark child arguments are invalid")
            return _child_run(kit_root, arguments[1], int(arguments[2]))
        if arguments:
            raise OfficeBenchmarkError("unsupported launcher arguments")
        print("[1/5] 키트 무결성을 확인합니다.", flush=True)
        print("[2/5] 노트북 하드웨어와 AC 전원을 확인합니다.", flush=True)
        print("[3/5] 합성 벤치마크를 세 번 실행합니다.", flush=True)
        receipt = run_office_measurement(kit_root)
        print("[4/5] 결과 장부와 SHA-256을 검증했습니다.", flush=True)
        print(f"[5/5] 완료: {receipt.json_path.name}", flush=True)
        return 0
    except (OfficeBenchmarkError, KitVerificationError, ValueError) as exc:
        print(f"오류 코드: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
