# Evidence Bundle Resource Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` in the current session. The user explicitly prohibited
> subagent dispatch for this worktree.

**Goal:** Reject adversarial evidence-bundle allocation amplification before
`json.loads` while retaining the 16 MiB and 10,000-event contract and the recovered
performance margin.

**Architecture:** A byte-level structural preflight skips quoted content with
`bytes.find`, counts container entries and decoded-node equivalents, and stops depth or
resource overflow before object construction. The existing parsed-value walk then
applies path-aware semantic limits and all current string and forbidden-key checks.

**Tech Stack:** Python 3.12.10 standard library, pytest, Ruff, deterministic Windows
portable-kit builder

## Global Constraints

- Work only on `codex/research-os-contract-design` in the assigned worktree.
- Do not use subagents, switch branches, merge, push, or touch another worktree.
- Keep the 16 MiB, 10,000-event, 30,000-artifact, depth-8, 512-character,
  1-second open/replay, 2-second bundle, and 192 MiB product gates.
- Do not add a parser dependency, subprocess authority, file access, archive support,
  or a second trusted dataset fingerprint.
- Every production change follows a witnessed RED then GREEN cycle.
- Do not deliver a replacement ZIP until the full suite, resource attack, performance,
  reproducibility, smoke, and mutation gates all pass.

---

### Task 1: Correct the authoritative design contract

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-decision-ledger-import-quarantine-design.md`

**Interfaces:**
- Consumes: the completed implementation audit and the resource-preflight design
- Produces: one noncontradictory V1 wire and resource contract

- [ ] **Step 1: Replace the stale top-level wire list**

Document the implemented exact fields: schema ID/version, canonicalization ID, hash
algorithm, source project ID, optional export timestamp, nested head, artifacts, and
events. State that quarantine derives the dataset fingerprint from the verified typed
snapshot and StudySpec rather than trusting a redundant top-level copy.

- [ ] **Step 2: Replace the contradictory resource bullets**

Document these exact limits:

```text
file bytes: 16 MiB
events: 10,000
artifacts: 30,000
nesting depth: 8
event wire bytes: 8 KiB
artifact canonical body bytes: 128 KiB
ordinary decoded string: 512 code points
pre-parse single container: 30,000 entries
post-parse non-top-level collection: 10,000 entries
total decoded nodes including object keys: 1,000,000
```

Explain that top-level artifacts use the 30,000 exception, top-level events use
10,000, and the 16 MiB byte limit is the total string-code-point ceiling.

- [ ] **Step 3: Self-review and commit**

Run `git diff --check` and verify that Sections 7.1 and 7.2 no longer contradict each
other or `2026-07-12-evidence-bundle-resource-preflight-design.md`.

Commit:

```powershell
git add -- docs/superpowers/specs/2026-07-12-decision-ledger-import-quarantine-design.md
git commit -m "docs: reconcile evidence bundle resource contract"
```

---

### Task 2: Add allocation preflight with TDD

**Files:**
- Modify: `tests/test_research_memory_evidence_bundle.py`
- Modify: `src/modori/research_memory/evidence_bundle.py`

**Interfaces:**
- Produces: `_scan_json_structure(raw: bytes, limits: EvidenceBundleLimits) -> None`
- Extends: `EvidenceBundleLimits.max_collection_items`,
  `.max_preparse_container_items`, and `.max_items`
- Preserves: `EvidenceBundle.from_bytes` and every existing closed error code

- [ ] **Step 1: Write failing default-budget tests**

Add:

```python
def test_bundle_resource_defaults_bound_preparse_allocation() -> None:
    limits = EvidenceBundleLimits()
    assert limits.max_collection_items == 10_000
    assert limits.max_preparse_container_items == 30_000
    assert limits.max_items == 1_000_000
```

Expected RED: the first two attributes do not exist and `max_items` is 2,000,000.

- [ ] **Step 2: Write failing decoder-guard tests**

Add a helper that turns any decoder call into a test failure, then exercise container,
depth, and total-node ceilings with injected small limits:

```python
def _decoder_must_not_run(*_args, **_kwargs):
    pytest.fail("json decoder ran before structural resource rejection")


@pytest.mark.parametrize(
    ("raw", "limits", "code"),
    [
        (
            b"[0,0,0,0,0]",
            replace(
                EvidenceBundleLimits(),
                max_preparse_container_items=4,
            ),
            EvidenceBundleErrorCode.ITEM_LIMIT,
        ),
        (
            b"[" * 9 + b"0" + b"]" * 9,
            EvidenceBundleLimits(),
            EvidenceBundleErrorCode.NESTING_LIMIT,
        ),
        (
            b"[[{},{},{}],[{},{},{}]]",
            replace(EvidenceBundleLimits(), max_items=8),
            EvidenceBundleErrorCode.ITEM_LIMIT,
        ),
    ],
)
def test_structure_budget_rejects_before_json_allocation(
    monkeypatch,
    raw: bytes,
    limits: EvidenceBundleLimits,
    code: EvidenceBundleErrorCode,
) -> None:
    monkeypatch.setattr(evidence_bundle.json, "loads", _decoder_must_not_run)
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(raw, limits=limits)
    assert caught.value.code is code
```

Expected RED: current code calls `json.loads` before all three structural checks.

- [ ] **Step 3: Write failing semantic collection and huge-integer tests**

```python
def test_nested_collection_limit_is_distinct_from_top_level_artifacts() -> None:
    nested = canonical_bytes({"value": [None] * 10_001})
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(nested)
    assert caught.value.code is EvidenceBundleErrorCode.ITEM_LIMIT

    top_artifacts = canonical_bytes({"artifacts": [None] * 30_000})
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(top_artifacts)
    assert caught.value.code is EvidenceBundleErrorCode.SCHEMA_INVALID


def test_oversized_integer_is_a_closed_invalid_number() -> None:
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(b"9" * 10_000)
    assert caught.value.code is EvidenceBundleErrorCode.INVALID_NUMBER
```

Expected RED: the nested list reaches `unknown_field`, and Python's integer digit guard
escapes as a raw `ValueError`.

- [ ] **Step 4: Implement the exact limits and integer closure**

Set:

```python
max_collection_items: int = 10_000
max_preparse_container_items: int = 30_000
max_items: int = 1_000_000
```

Wrap `int(raw)` in `_parse_integer` so any `ValueError` becomes `_InvalidNumber`.

- [ ] **Step 5: Implement the structural scanner**

Use this state machine before `json.loads` and after strict UTF-8 decoding:

```python
def _scan_json_structure(raw: bytes, limits: EvidenceBundleLimits) -> None:
    stack: list[list[int]] = []
    total_items = 1
    index = 0
    while index < len(raw):
        character = raw[index]
        if character == 34:
            if stack:
                stack[-1][2] = 1
            search = index + 1
            while True:
                closing = raw.find(b'"', search)
                if closing < 0:
                    return
                slash = closing - 1
                while slash > index and raw[slash] == 92:
                    slash -= 1
                if (closing - 1 - slash) % 2 == 0:
                    index = closing + 1
                    break
                search = closing + 1
            continue
        if character in (91, 123):
            if stack:
                stack[-1][2] = 1
            stack.append([character, 0, 0])
            if len(stack) > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
        elif character == 44 and stack:
            frame = stack[-1]
            frame[1] += 1
            container_limit = (
                limits.max_collection_items
                if frame[0] == 123
                else limits.max_preparse_container_items
            )
            if frame[1] + 1 > container_limit:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle contains an oversized container",
                )
            total_items += 2 if frame[0] == 123 else 1
            if total_items > limits.max_items:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle exceeds its total item limit",
                )
        elif character in (93, 125) and stack:
            kind, commas, has_content = stack.pop()
            if has_content:
                container_limit = (
                    limits.max_collection_items
                    if kind == 123
                    else limits.max_preparse_container_items
                )
                if commas + 1 > container_limit:
                    _raise(
                        EvidenceBundleErrorCode.ITEM_LIMIT,
                        "evidence bundle contains an oversized container",
                    )
                total_items += 2 if kind == 123 else 1
                if total_items > limits.max_items:
                    _raise(
                        EvidenceBundleErrorCode.ITEM_LIMIT,
                        "evidence bundle exceeds its total item limit",
                    )
        elif character not in (9, 10, 13, 32) and stack:
            stack[-1][2] = 1
        index += 1
```

- [ ] **Step 6: Make the parsed walk path-aware**

Change its stack entries to `(value, depth, collection_limit)`. Mappings always use
`max_collection_items`. At depth 1 only, the `artifacts` child receives
`max_artifacts`, the `events` child receives `max_events`, and every other child
receives `max_collection_items`. Lists reject when `len(current) > collection_limit`.
Retain total-node, depth, string-length, and forbidden-key checks verbatim.

- [ ] **Step 7: Run GREEN and commit**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider tests/test_research_memory_evidence_bundle.py tests/test_research_memory_quarantine.py tests/test_research_memory_promotion.py -q
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check src/modori/research_memory/evidence_bundle.py tests/test_research_memory_evidence_bundle.py
git diff --check
```

Commit:

```powershell
git add -- src/modori/research_memory/evidence_bundle.py tests/test_research_memory_evidence_bundle.py
git commit -m "sec: bound evidence allocation before parsing"
```

---

### Task 3: Re-run resource, security, and performance gates

**Files:**
- Verify only

**Interfaces:**
- Consumes: committed preflight implementation
- Produces: attack peak, valid-bundle latency, mutation, crash, full-suite, and lint
  evidence

- [ ] **Step 1: Repeat the five-million-object child attack**

Use the same 5,000,000 empty-object and 15,000,001-byte input. Require
`item_limit`, peak working set below 201,326,592 bytes, and elapsed time below 500,000
us. Do not include input construction in the parser elapsed time; do include it in the
process peak.

- [ ] **Step 2: Run two same-host valid benchmarks**

Run `scripts/benchmark_research_memory.py` twice. Require both bundle maxima below the
frozen pre-optimization 2,682,439 us. Record open/replay without changing its threshold.

- [ ] **Step 3: Run focused and full gates**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
$env:MPLCONFIGDIR=(Resolve-Path 'matplotlib-cache').Path
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -p no:cacheprovider -q
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check .
git diff --check
git status --short
```

Expected: all tests pass with only predeclared skips, Ruff and diff are clean, and the
worktree is clean after the committed change.

---

### Task 4: Replace and attack the sealed delivery

**Files:**
- Generate, do not commit: `dist/modori-office-benchmark-kit-<commit>-py31210.zip`
- Generate, do not commit: matching `.zip.sha256`

**Interfaces:**
- Consumes: the clean final commit and pinned official Python archive
- Produces: the only current USB delivery pair

- [ ] **Step 1: Build twice and compare exact bytes**

Verify the cached runtime SHA-256 remains
`4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`.
Build into two fresh `.tmp` directories using the exact full HEAD and require equal ZIP
bytes, equal SHA-256, clean CRC, sorted 74-entry inventory, and matching internal
identity.

- [ ] **Step 2: Run the clean Windows kit twice**

Use a normal non-reparse `.tmp` extraction and the real CMD bootstrap. Because the
Codex sandbox denies read-only WMI, request only the same bounded unsandboxed hardware
probe used by the prior smoke. Require two exit-zero runs, distinct measurement IDs,
matching result sidecars, recomputed evaluations, empty `work`, zero `__pycache__`, and
`office_hardware_claim_allowed=false`.

- [ ] **Step 3: Repeat five one-byte mutations**

Mutate runtime, runner, identity, manifest, and PowerShell in separate copies. Require
the exact existing failure code, nonzero exit, and zero benchmark JSONs in every case.

- [ ] **Step 4: Replace dist and clean bounded temporary roots**

Verify every deletion target resolves below `.tmp` or exactly inside `dist`. Leave only
the newest ZIP and sidecar, recompute the final hash and CRC from `dist`, and confirm
`git status --short` and `git diff --check` are empty.

- [ ] **Step 5: Obtain the same-laptop rerun**

The operator extracts the newest ZIP under `%LOCALAPPDATA%\ModoriBench-<commit>` on AC
power and returns JSON, sidecar, Korean summary, and any bootstrap error. Independently
recompute all gates. A repeated failure triggers the approved stop rule; thresholds
and validation are never weakened.

