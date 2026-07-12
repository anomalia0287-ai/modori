# Office Benchmark Performance Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. The user explicitly
> excluded subagent dispatch for this worktree.

**Goal:** Preserve every Decision Ledger and quarantine security invariant while
recovering the failed open/replay and evidence-bundle timing margins, returning stable
preflight diagnostics, and producing a newly sealed kit for the same laptop.

**Architecture:** Reuse canonical payload bytes already produced during event
validation, move bundle depth enforcement into the existing iterative resource walk,
and map three bounded preflight conditions to declared process exits. No schema,
workload, threshold, dependency, or claim-authority change is allowed.

**Tech Stack:** Python 3.12.10, stdlib `json`/`hashlib`/`sqlite3`, pytest, Ruff,
PowerShell 5.1-compatible bootstrap, deterministic ZIP builder

## Global Constraints

- Work only on `codex/research-os-contract-design` in the assigned worktree.
- Do not switch, merge, push, remove the worktree, or touch another worktree.
- Do not dispatch subagents.
- Keep 10,000 events, 16 MiB, 1 s SSD open, 2 s bundle, 50 ms SSD append p95,
  and 192 MiB peak limits unchanged.
- Do not trust imported or stored authority, skip canonical validation, add a native
  dependency, transmit data, or grant product-claim authority.
- Use red-green TDD for each production change and commit each independently reviewable
  result.

---

### Task 1: Reuse canonical event payload bytes

**Files:**
- Modify: `tests/test_research_memory_ledger_contracts.py`
- Modify: `src/modori/research_memory/ledger_contracts.py`

**Interfaces:**
- Consumes: `canonical_bytes(value: object) -> bytes`
- Produces: `_validate_payload(event_kind, payload, subjects) -> tuple[dict[str,
  object], bytes]`
- Preserves: the public `LedgerEvent.create` signature and all wire bytes and hashes

- [ ] **Step 1: Write the failing call-count regression**

Add the module import and a test that wraps the real canonicalizer:

```python
import modori.research_memory.ledger_contracts as ledger_contracts


def test_event_create_reuses_the_single_canonical_payload(monkeypatch) -> None:
    calls: list[object] = []
    original = ledger_contracts.canonical_bytes

    def counted(value: object) -> bytes:
        calls.append(value)
        return original(value)

    monkeypatch.setattr(ledger_contracts, "canonical_bytes", counted)
    payload = {"resulting_snapshot_artifact_id": "a" * 64}
    event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=("a" * 64,),
        payload=payload,
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    assert len(calls) == 2
    assert event.payload_bytes == original(payload)
    assert LedgerEvent.from_mapping(event.to_mapping()) == event
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest tests/test_research_memory_ledger_contracts.py::test_event_create_reuses_the_single_canonical_payload -q
```

Expected: failure showing three canonicalization calls instead of two.

- [ ] **Step 3: Implement one canonical payload**

Change only the payload serialization and return shape so all intervening typed checks
remain byte-for-byte unchanged:

```diff
-) -> dict[str, object]:
+) -> tuple[dict[str, object], bytes]:
     _require_exact_keys(payload, _PAYLOAD_FIELDS[event_kind], f"{event_kind.value} payload")
-    copied = json.loads(canonical_bytes(dict(payload)).decode("utf-8"))
+    payload_bytes = canonical_bytes(dict(payload))
+    copied = json.loads(payload_bytes.decode("utf-8"))
-    return copied
+    return copied, payload_bytes
```

In `LedgerEvent.create`, apply this exact reuse while leaving full-body canonicalization
and both hash calculations unchanged:

```diff
-        payload_mapping = _validate_payload(
+        payload_mapping, canonical_payload = _validate_payload(
             event_kind,
             _require_mapping(payload, "event payload"),
             subject_artifact_ids,
         )
         body_bytes = canonical_bytes(body)
         body_digest = hashlib.sha256(body_bytes).hexdigest()
         return cls(
-            payload_bytes=canonical_bytes(payload_mapping),
+            payload_bytes=canonical_payload,
```

- [ ] **Step 4: Run GREEN and security neighbors**

Run:

```powershell
pytest tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py tests/test_research_memory_crash_recovery.py -q
```

Expected: every selected test passes.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/research_memory/ledger_contracts.py tests/test_research_memory_ledger_contracts.py
git commit -m "perf: reuse canonical ledger event payloads"
```

---

### Task 2: Enforce bundle depth in the resource walk

**Files:**
- Modify: `tests/test_research_memory_evidence_bundle.py`
- Modify: `src/modori/research_memory/evidence_bundle.py`

**Interfaces:**
- Consumes: parsed strict-JSON values and `EvidenceBundleLimits`
- Produces: one iterative `_walk_resources` pass enforcing depth, count, strings, and
  forbidden keys
- Preserves: every `EvidenceBundleErrorCode` and accepted canonical wire form

- [ ] **Step 1: Write the failing no-second-pass regression**

Add a module import and force any old raw scan to fail:

```python
import modori.research_memory.evidence_bundle as evidence_bundle


def test_bundle_depth_is_enforced_without_a_separate_raw_scan(monkeypatch) -> None:
    monkeypatch.setattr(
        evidence_bundle,
        "_scan_depth",
        lambda *_args: pytest.fail("separate raw depth scan was called"),
        raising=False,
    )
    raw = _bundle().to_bytes()
    assert EvidenceBundle.from_bytes(raw).to_bytes() == raw
```

Also add an extreme-depth preservation case:

```python
def test_bundle_decoder_recursion_is_closed_as_nesting_limit() -> None:
    raw = b"[" * 2048 + b"0" + b"]" * 2048
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(raw)
    assert caught.value.code is EvidenceBundleErrorCode.NESTING_LIMIT
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest tests/test_research_memory_evidence_bundle.py::test_bundle_depth_is_enforced_without_a_separate_raw_scan -q
```

Expected: failure because current `from_bytes` invokes `_scan_depth`.

- [ ] **Step 3: Implement the single iterative walk**

Replace the raw scan with a stack carrying container depth:

```python
def _walk_resources(value: object, *, limits: EvidenceBundleLimits) -> None:
    items = 0
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        items += 1
        if items > limits.max_items:
            _raise(
                EvidenceBundleErrorCode.ITEM_LIMIT,
                "evidence bundle exceeds its total item limit",
            )
        if isinstance(current, str):
            if len(current) > limits.max_string_length:
                _raise(
                    EvidenceBundleErrorCode.STRING_LIMIT,
                    "evidence bundle contains an oversized string",
                )
        elif isinstance(current, Mapping):
            if depth > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
            for key, item in current.items():
                if key in _FORBIDDEN_KEYS:
                    _raise(
                        EvidenceBundleErrorCode.FORBIDDEN_KEY,
                        "evidence bundle contains a forbidden authority-bearing key",
                    )
                stack.append((key, depth))
                stack.append((item, depth + 1 if isinstance(item, (Mapping, list)) else depth))
        elif isinstance(current, list):
            if depth > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
            stack.extend(
                (item, depth + 1 if isinstance(item, (Mapping, list)) else depth)
                for item in current
            )
```

Remove `_scan_depth(text, limits.max_depth)` from `from_bytes`, delete the unused raw
scanner, and catch `RecursionError` from `json.loads` as `NESTING_LIMIT`.

- [ ] **Step 4: Run GREEN and the quarantine attack suite**

Run:

```powershell
pytest tests/test_research_memory_evidence_bundle.py tests/test_research_memory_quarantine.py tests/test_research_memory_promotion.py -q
```

Expected: every selected test passes with unchanged closed outcome codes.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/research_memory/evidence_bundle.py tests/test_research_memory_evidence_bundle.py
git commit -m "perf: combine evidence resource and depth checks"
```

---

### Task 3: Preserve bounded preflight failure codes

**Files:**
- Modify: `tests/test_office_research_memory_kit_runner.py`
- Modify: `tests/test_office_research_memory_kit_architecture.py`
- Modify: `scripts/run_office_research_memory_benchmark.py`
- Modify: `scripts/office_benchmark_kit/VERIFY-AND-RUN.ps1.in`
- Modify: `scripts/office_benchmark_kit/README-KO.txt`
- Modify: `docs/qa/portable-office-benchmark-kit-runbook.md`

**Interfaces:**
- Produces: `OfficeBenchmarkError.code: str` and `.exit_code: int`
- Produces: process exits 10, 11, and 12 for declared preflight failures
- Preserves: generic failures as `runner_exit_<number>` and all privacy restrictions

- [ ] **Step 1: Write failing typed-error and template tests**

Extend the battery test to capture the exception:

```python
root = _fake_kit(tmp_path)
payload = _probe_payload()
payload["ac_power"] = False
calls = 0

def child(_verified, _measurement_id: str, _run_index: int):
    nonlocal calls
    calls += 1
    return _run()

with pytest.raises(OfficeBenchmarkError, match="AC power") as caught:
    run_office_measurement(
        root,
        hardware_probe=lambda _root: parse_hardware_probe(json.dumps(payload)),
        child_executor=child,
        measurement_id="b" * 32,
    )
assert caught.value.code == "ac_power_required"
assert caught.value.exit_code == 10
assert calls == 0
```

Add an architecture assertion that the PowerShell template contains all three declared
code mappings and retains the generic fallback.

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest tests/test_office_research_memory_kit_runner.py::test_battery_power_refuses_before_any_child_run tests/test_office_research_memory_kit_architecture.py -q
```

Expected: the exception lacks typed fields and the template lacks mappings.

- [ ] **Step 3: Implement typed preflight exits and bootstrap mapping**

Give `OfficeBenchmarkError` validated fields with defaults that preserve existing call
sites:

```python
_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class OfficeBenchmarkError(RuntimeError):
    """Raised when the portable measurement cannot produce valid evidence."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "runner_error",
        exit_code: int = 1,
    ) -> None:
        if not isinstance(message, str) or not message:
            raise ValueError("office benchmark error message is invalid")
        if not isinstance(code, str) or not _ERROR_CODE_RE.fullmatch(code):
            raise ValueError("office benchmark error code is invalid")
        if type(exit_code) is not int or not 1 <= exit_code <= 255:
            raise ValueError("office benchmark exit code is invalid")
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
```

Use the declared exits at the exact preflight gates:

```python
if hardware.get("ac_power") is not True:
    raise OfficeBenchmarkError(
        "AC power is required",
        code="ac_power_required",
        exit_code=10,
    )
if hardware.get("drive_type") != "fixed":
    raise OfficeBenchmarkError(
        "fixed internal execution volume is required",
        code="fixed_internal_volume_required",
        exit_code=11,
    )
storage = hardware.get("storage")
if not isinstance(storage, Mapping) or storage.get("free_bytes", 0) < 2 * 1024**3:
    raise OfficeBenchmarkError(
        "at least 2 GiB free space is required",
        code="free_space_required",
        exit_code=12,
    )
```

Split `main` exception handling so typed errors return their declared exit while all
other caught failures return 1:

```python
except OfficeBenchmarkError as exc:
    print(f"오류 코드: {exc.code}", flush=True)
    return exc.exit_code
except (KitVerificationError, ValueError):
    print("오류 코드: runner_error", flush=True)
    return 1
```

In PowerShell, replace the generic runner check with the declared mapping followed by
the existing generic fallback:

```powershell
$runnerExit = $LASTEXITCODE
switch ($runnerExit) {
    10 { Stop-ModoriKit 'ac_power_required' }
    11 { Stop-ModoriKit 'fixed_internal_volume_required' }
    12 { Stop-ModoriKit 'free_space_required' }
}
if ($runnerExit -ne 0) {
    Stop-ModoriKit ("runner_exit_" + $runnerExit)
}
```

- [ ] **Step 4: Add exact operator guidance**

State in both Korean instructions that Desktop and Documents may be OneDrive-backed,
that no cloud-synchronized or reparse-point folder is valid, and that the safe normal
user path is created by opening `%LOCALAPPDATA%` and extracting below
`ModoriBench`. Do not instruct elevation, antivirus changes, or cloud-setting changes.

- [ ] **Step 5: Run GREEN**

Run:

```powershell
pytest tests/test_office_research_memory_kit_runner.py tests/test_office_research_memory_kit_architecture.py tests/test_office_research_memory_kit_builder.py -q
```

Expected: every selected test passes and deterministic builder tests remain green.

- [ ] **Step 6: Commit**

```powershell
git add -- scripts/run_office_research_memory_benchmark.py scripts/office_benchmark_kit/VERIFY-AND-RUN.ps1.in scripts/office_benchmark_kit/README-KO.txt docs/qa/portable-office-benchmark-kit-runbook.md tests/test_office_research_memory_kit_runner.py tests/test_office_research_memory_kit_architecture.py
git commit -m "fix: preserve portable benchmark preflight failures"
```

---

### Task 4: Prove security equivalence and measure the change

**Files:**
- Verify only; no production edits unless a failing invariant identifies a defect

**Interfaces:**
- Consumes: committed Tasks 1-3
- Produces: fresh unit, adversarial, crash, performance, lint, and diff evidence

- [ ] **Step 1: Run the complete focused safety gate**

```powershell
pytest tests/test_research_memory_canonical.py tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py tests/test_research_memory_evidence_bundle.py tests/test_research_memory_quarantine.py tests/test_research_memory_promotion.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_performance.py tests/test_research_memory_constrained_benchmark.py tests/test_office_research_memory_kit_contract.py tests/test_office_research_memory_kit_verifier.py tests/test_office_research_memory_kit_runner.py tests/test_office_research_memory_kit_builder.py tests/test_office_research_memory_kit_architecture.py -q
```

Expected: zero failures.

- [ ] **Step 2: Run the same-host benchmark once**

```powershell
$env:PYTHONPATH='src'
python scripts/benchmark_research_memory.py
```

Record the new open/replay and bundle maxima beside the frozen 1,473,427 us and
2,682,439 us baselines. Both must decrease. Do not edit thresholds if either does not.

- [ ] **Step 3: Run full repository verification**

```powershell
pytest -q
ruff check .
git diff --check
```

Expected: the repository's full pass count with zero failures, Ruff clean, and no diff
whitespace errors.

---

### Task 5: Seal and attack the replacement kit

**Files:**
- Generated, ignored delivery artifacts: `dist/`
- Generated, ignored verification material: `.tmp/`

**Interfaces:**
- Consumes: clean committed source and the pinned official Python runtime archive
- Produces: deterministic ZIP, SHA-256 sidecar, smoke result, and mutation evidence

- [ ] **Step 1: Build from the clean committed source twice**

Use
`.tmp/python-runtime/python-3.12.10-embed-amd64.zip` only after confirming its SHA-256
is `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
Build into two separate verified temporary output directories with the exact current
source commit and compare archive bytes and SHA-256 values.

- [ ] **Step 2: Execute the actual Windows bootstrap twice**

Extract each archive to a normal non-reparse directory below `.tmp`, set only
`MODORI_KIT_NONINTERACTIVE=1`, run `RUN-MODORI-BENCHMARK.cmd`, and independently check:

- command exit 0;
- exactly three outer runs;
- result and sidecar digest equality;
- source commit and runtime identity;
- recomputed evaluation equality;
- no bytecode and empty owned `work` directory;
- `office_hardware_claim_allowed=false`.

- [ ] **Step 3: Repeat one-byte mutation attacks**

In separate extracted copies mutate runtime, runner, identity, manifest, and PowerShell
bootstrap one byte at a time. Each must exit nonzero before creating a benchmark JSON.
Verify every deletion target resolves below `.tmp` before cleanup.

- [ ] **Step 4: Publish only the final deterministic pair**

Leave exactly the newest ZIP and `.zip.sha256` in `dist`, report their full names,
byte size, SHA-256, source commit, runtime identity, and validation evidence. Do not
push or merge.

- [ ] **Step 5: Obtain and adjudicate the target-laptop rerun**

The operator reruns from `%LOCALAPPDATA%\ModoriBench` on AC power and returns JSON,
sidecar, Korean summary, and any bootstrap error. Independently recompute all four
performance gates and three-run variation. A pass remains device evidence only; a
failure remains negative evidence and triggers the design's stop/reassessment rule.
