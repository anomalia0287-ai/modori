from __future__ import annotations

import ctypes
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import time
import uuid

_SOURCE_ROOT = Path(__file__).parent.parent / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from modori.research_memory.canonical import (  # noqa: E402
    ZERO_HASH,
    canonical_bytes,
    canonical_digest,
)
from modori.research_memory.evidence_bundle import (  # noqa: E402
    EvidenceBundle,
    EvidenceBundleError,
    EvidenceBundleLimits,
)
from modori.research_memory.ledger_contracts import (  # noqa: E402
    ImportedAssertion,
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerCommit,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    ResearchRequestSnapshot,
)
from modori.research_memory.ledger_store import DecisionLedgerStore  # noqa: E402
from modori.research_os import (  # noqa: E402
    CaptureMode,
    EstimandSpec,
    Fact,
    Language,
    ProductSurface,
    QuestionSpec,
    ResearchRequest,
    SchemaEnvelope,
    StudySpec,
)


def _envelope(schema_id: str, object_id: str) -> SchemaEnvelope:
    return SchemaEnvelope(
        schema_id=schema_id,
        schema_version=1,
        project_id="benchmark-project",
        object_id=object_id,
        revision=1,
        supersedes_revision=None,
        created_event_ref=f"event:{object_id}:1",
    )


def _unknown() -> Fact[object]:
    return Fact.unknown(reason_code="benchmark_unknown")


def _benchmark_request() -> ResearchRequest:
    question = QuestionSpec(
        envelope=_envelope("modori.question_spec", "question-1"),
        capture_mode=CaptureMode.STRUCTURED,
        language=Language.KO,
        local_text=None,
        research_goal=_unknown(),
        causal_intent=_unknown(),
    )
    estimand = EstimandSpec(
        envelope=_envelope("modori.estimand_spec", "estimand-1"),
        template=_unknown(),
        claim_basis=_unknown(),
        target_population=_unknown(),
        unit_of_analysis=_unknown(),
        target_roles=(),
        contrast=_unknown(),
        time_scope=_unknown(),
        effect_scale=_unknown(),
        association_target=_unknown(),
    )
    study = StudySpec(
        envelope=_envelope("modori.study_spec", "study-1"),
        dataset_fingerprint="a" * 64,
        source_schema_fingerprint="b" * 64,
        unit_of_observation=_unknown(),
        unit_of_analysis=_unknown(),
        design_family=_unknown(),
        data_layout=_unknown(),
        temporal_structure=_unknown(),
        dependence_structure=_unknown(),
        assignment_mechanism=_unknown(),
        sampling_design=_unknown(),
        design_roles=(),
        repeated_measure_order=_unknown(),
        missing_code_meanings=(),
    )
    return ResearchRequest(
        question=question,
        estimand=estimand,
        study=study,
        current_dataset_fingerprint="a" * 64,
        available_variable_ids=(),
        surface=ProductSurface.EXPERIMENTAL,
        question_budget_remaining=3,
    )


def _capture() -> tuple[tuple[LedgerArtifact, ...], LedgerArtifact]:
    _snapshot, artifacts = ResearchRequestSnapshot.capture(_benchmark_request())
    snapshot_artifact = next(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    return artifacts, snapshot_artifact


def _genesis_commit() -> LedgerCommit:
    artifacts, snapshot = _capture()
    event = LedgerEvent.create(
        project_id="benchmark-project",
        event_id="event:benchmark:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(sorted(item.artifact_id for item in artifacts)),
        payload={"resulting_snapshot_artifact_id": snapshot.artifact_id},
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    return LedgerCommit(
        expected_head=LedgerHead.genesis(),
        events=(event,),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot.artifact_id,
    )


def _batch_commit(
    head: LedgerHead,
    *,
    count: int,
) -> LedgerCommit:
    artifacts, snapshot = _capture()
    events: list[LedgerEvent] = []
    previous = head.event_hash
    for sequence in range(head.sequence + 1, head.sequence + count + 1):
        event = LedgerEvent.create(
            project_id="benchmark-project",
            event_id=f"event:benchmark:{sequence}",
            sequence=sequence,
            event_kind=LedgerEventKind.FACT_INVALIDATED,
            subject_artifact_ids=(snapshot.artifact_id,),
            payload={
                "fact_address": "study.dependence_structure",
                "reason_code": "benchmark_tick",
                "resulting_snapshot_artifact_id": snapshot.artifact_id,
            },
            previous_event_hash=previous,
            recorded_at_utc=None,
        )
        events.append(event)
        previous = event.event_hash
    return LedgerCommit(
        expected_head=head,
        events=tuple(events),
        artifacts=artifacts,
        resulting_snapshot_artifact_id=snapshot.artifact_id,
    )


def _build_batched_ledger(path: Path, *, event_count: int) -> None:
    if event_count < 1:
        raise ValueError("event_count must be positive")
    with DecisionLedgerStore.create(path, "benchmark-project") as store:
        store.append(_genesis_commit())
        remaining = event_count - 1
        while remaining:
            batch = min(1_000, remaining)
            store.append(_batch_commit(store.head, count=batch))
            remaining -= batch


def _append_durable_events(
    path: Path,
    *,
    append_count: int,
    warmup_count: int = 0,
) -> tuple[int, ...]:
    if append_count < 1:
        raise ValueError("append_count must be positive")
    timings: list[int] = []
    with DecisionLedgerStore.create(path, "benchmark-project") as store:
        store.append(_genesis_commit())
        for _ in range(warmup_count):
            store.append(_batch_commit(store.head, count=1))
        for _ in range(append_count):
            commit = _batch_commit(store.head, count=1)
            started = time.perf_counter_ns()
            store.append(commit)
            timings.append((time.perf_counter_ns() - started) // 1_000)
    return tuple(timings)


def _percentile(values: tuple[int, ...], numerator: int, denominator: int) -> int:
    ordered = sorted(values)
    index = max(0, (len(ordered) * numerator + denominator - 1) // denominator - 1)
    return ordered[index]


def _timing_summary(values: tuple[int, ...]) -> dict[str, int]:
    return {
        "repetitions": len(values),
        "median_us": _percentile(values, 1, 2),
        "p95_us": _percentile(values, 95, 100),
        "max_us": max(values),
    }


def _physical_memory_bytes() -> int:
    if os.name != "nt":
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        return page_size * pages

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 0
    return int(status.total_physical)


def _effective_logical_cpu_count() -> int:
    """Return CPUs this process can actually run on, not the host inventory."""
    if os.name != "nt":
        get_affinity = getattr(os, "sched_getaffinity", None)
        if get_affinity is not None:
            count = len(get_affinity(0))
        else:
            count = os.cpu_count() or 1
        if count < 1:
            raise RuntimeError("process exposes no effective logical CPUs")
        return count

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = ctypes.c_void_p
    get_process_affinity_mask = kernel32.GetProcessAffinityMask
    get_process_affinity_mask.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    get_process_affinity_mask.restype = ctypes.c_int
    process_mask = ctypes.c_size_t()
    system_mask = ctypes.c_size_t()
    if not get_process_affinity_mask(
        get_current_process(),
        ctypes.byref(process_mask),
        ctypes.byref(system_mask),
    ):
        raise OSError(
            ctypes.get_last_error(),
            "GetProcessAffinityMask failed while recording benchmark evidence",
        )
    count = process_mask.value.bit_count()
    if count < 1:
        raise RuntimeError("process exposes no effective logical CPUs")
    return count


def _peak_working_set_bytes() -> int:
    if os.name != "nt":
        import resource

        peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return peak if sys.platform == "darwin" else peak * 1024

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("size", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t),
            ("quota_nonpaged_pool_usage", ctypes.c_size_t),
            ("page_file_usage", ctypes.c_size_t),
            ("peak_page_file_usage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.size = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = ctypes.c_void_p
    get_process_memory_info = kernel32.K32GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCounters),
        ctypes.c_ulong,
    ]
    get_process_memory_info.restype = ctypes.c_int
    process = get_current_process()
    if not get_process_memory_info(
        process,
        ctypes.byref(counters),
        counters.size,
    ):
        return 0
    return int(counters.peak_working_set_size)


def _near_limit_parser_case(target_bytes: int) -> dict[str, object]:
    maximum = EvidenceBundleLimits().max_bytes
    target = min(maximum, max(16, target_bytes))
    item = '"' + "x" * 512 + '"'
    count = max(1, (target - 2) // (len(item) + 1))
    raw = ("[" + ",".join([item] * count) + "]").encode("utf-8")
    while len(raw) > target and count > 1:
        count -= 1
        raw = ("[" + ",".join([item] * count) + "]").encode("utf-8")
    started = time.perf_counter_ns()
    outcome = "unexpected_accept"
    try:
        EvidenceBundle.from_bytes(raw)
    except EvidenceBundleError as exc:
        outcome = exc.code.value
    return {
        "input_bytes": len(raw),
        "elapsed_us": (time.perf_counter_ns() - started) // 1_000,
        "outcome_code": outcome,
    }


def _padded_bundle_bytes(
    bundle: EvidenceBundle,
    *,
    target_bytes: int,
) -> bytes:
    limits = EvidenceBundleLimits()
    target = min(max(1, target_bytes), limits.max_bytes - 1_024)
    base_bytes = bundle.to_bytes()
    if len(base_bytes) >= target:
        return base_bytes
    padding_artifacts: list[LedgerArtifact] = []
    estimated = len(base_bytes)
    padding_value = ["x" * limits.max_string_length] * 240
    available_padding_events = max(0, len(bundle.events) - 1)
    for index in range(min(available_padding_events, limits.max_artifacts)):
        source_artifact_id = canonical_digest({"padding_index": index})
        assertion = ImportedAssertion(
            assertion_id=f"padding:{source_artifact_id}",
            project_id=bundle.source_project_id,
            source_project_id="synthetic-source",
            source_bundle_digest="c" * 64,
            source_artifact_id=source_artifact_id,
            fact_address=f"benchmark.padding_{index}",
            foreign_fact_state="inferred",
            value=padding_value,
            provenance_refs=(source_artifact_id,),
        )
        artifact = LedgerArtifact.from_value(assertion)
        increment = len(canonical_bytes(artifact.to_mapping())) + 68
        if estimated + increment > target:
            break
        padding_artifacts.append(artifact)
        estimated += increment
    if not padding_artifacts:
        return base_bytes
    rebuilt_events: list[LedgerEvent] = []
    previous = ZERO_HASH
    for index, original in enumerate(bundle.events):
        extra = (
            (padding_artifacts[index - 1].artifact_id,)
            if 1 <= index <= len(padding_artifacts)
            else ()
        )
        rebuilt = LedgerEvent.create(
            project_id=original.project_id,
            event_id=original.event_id,
            sequence=original.sequence,
            event_kind=original.event_kind,
            subject_artifact_ids=tuple(
                sorted((*original.subject_artifact_ids, *extra))
            ),
            payload=original.payload,
            previous_event_hash=previous,
            recorded_at_utc=original.recorded_at_utc,
        )
        rebuilt_events.append(rebuilt)
        previous = rebuilt.event_hash
    padded = EvidenceBundle.create(
        source_project_id=bundle.source_project_id,
        head=LedgerHead(
            sequence=rebuilt_events[-1].sequence,
            event_hash=rebuilt_events[-1].event_hash,
        ),
        artifacts=tuple((*bundle.artifacts, *padding_artifacts)),
        events=tuple(rebuilt_events),
        exported_at_utc=bundle.exported_at_utc,
    )
    raw = padded.to_bytes()
    if len(raw) > limits.max_bytes:
        raise RuntimeError("synthetic benchmark bundle exceeded its byte contract")
    return raw


def run_benchmark(
    *,
    root: Path,
    open_event_count: int = 10_000,
    durable_append_count: int = 1_000,
    parser_target_bytes: int = 16 * 1024 * 1024,
    bundle_target_bytes: int = 16 * 1024 * 1024,
) -> dict[str, object]:
    open_path = root / "open" / "decision-ledger.sqlite3"
    durable_path = root / "durable" / "decision-ledger.sqlite3"
    _build_batched_ledger(open_path, event_count=open_event_count)
    with DecisionLedgerStore.open(open_path, "benchmark-project"):
        pass
    open_timings: list[int] = []
    for _ in range(5):
        started = time.perf_counter_ns()
        with DecisionLedgerStore.open(open_path, "benchmark-project"):
            pass
        open_timings.append((time.perf_counter_ns() - started) // 1_000)
    store = DecisionLedgerStore.open(open_path, "benchmark-project")
    try:
        store.verify(full_integrity=True)
        full_integrity_timings: list[int] = []
        report = None
        for _ in range(3):
            started = time.perf_counter_ns()
            report = store.verify(full_integrity=True)
            full_integrity_timings.append((time.perf_counter_ns() - started) // 1_000)
        if report is None:
            raise RuntimeError("full-integrity benchmark produced no report")
        bundle = store.export_evidence_bundle(exported_at_utc=None)
        bundle_bytes = _padded_bundle_bytes(
            bundle,
            target_bytes=bundle_target_bytes,
        )
        EvidenceBundle.from_bytes(bundle_bytes)
        bundle_validation_timings: list[int] = []
        parsed_bundle = None
        for _ in range(3):
            started = time.perf_counter_ns()
            parsed_bundle = EvidenceBundle.from_bytes(bundle_bytes)
            bundle_validation_timings.append(
                (time.perf_counter_ns() - started) // 1_000
            )
        if parsed_bundle is None:
            raise RuntimeError("bundle benchmark produced no parsed bundle")
        if parsed_bundle.to_bytes() != bundle_bytes:
            raise RuntimeError("validated benchmark bundle changed its canonical bytes")
    finally:
        store.close()
    append_timings = _append_durable_events(
        durable_path,
        append_count=durable_append_count,
        warmup_count=10,
    )
    return {
        "schema_id": "modori.research_memory_benchmark",
        "schema_version": 1,
        "environment": {
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "machine": platform.machine() or "unknown",
            "processor": platform.processor() or "unknown",
            "logical_cpu_count": os.cpu_count() or 1,
            "effective_logical_cpu_count": _effective_logical_cpu_count(),
            "physical_memory_bytes": _physical_memory_bytes(),
            "storage_type": "unclassified",
        },
        "open_replay": _timing_summary(tuple(open_timings))
        | {
            "event_count": report.event_count,
            "warmup_count": 1,
            "process_peak_working_set_bytes": _peak_working_set_bytes(),
        },
        "full_integrity_verify": _timing_summary(tuple(full_integrity_timings))
        | {
            "event_count": report.event_count,
            "warmup_count": 1,
        },
        "bundle_validation": _timing_summary(tuple(bundle_validation_timings))
        | {
            "event_count": len(parsed_bundle.events),
            "artifact_count": len(parsed_bundle.artifacts),
            "input_bytes": len(bundle_bytes),
            "warmup_count": 1,
        },
        "durable_append": _timing_summary(append_timings)
        | {
            "count": len(append_timings),
            "warmup_count": 10,
        },
        "parser_near_limit": _near_limit_parser_case(parser_target_bytes),
    }


def main() -> int:
    temporary_parent = (_SOURCE_ROOT.parent / ".test-tmp").absolute()
    root = temporary_parent / f"research-memory-benchmark-{uuid.uuid4().hex}"
    try:
        payload = run_benchmark(root=root)
    finally:
        expected_prefix = "research-memory-benchmark-"
        if root.parent != temporary_parent or not root.name.startswith(expected_prefix):
            raise RuntimeError("refusing to clean an unverified benchmark directory")
        if root.exists():
            shutil.rmtree(root)
    print(canonical_bytes(payload).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
