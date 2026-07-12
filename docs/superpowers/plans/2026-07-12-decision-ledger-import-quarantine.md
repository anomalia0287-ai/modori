# Decision Ledger and Import Quarantine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The current root session is the exclusive writer; the user prohibits subagents.

**Goal:** Implement a project-local SQLite Decision Ledger, canonical hash chain and recovery, authority-free evidence-bundle quarantine, local promotion, and destructive/performance verification without giving Research OS execution authority.

**Architecture:** `modori.research_os` stays a pure decision core. A new outer `modori.research_memory` package owns canonical persistence contracts, an application-created SQLite store, strict JSON evidence exchange, quarantine, and coordination with the existing transition service. Imported proposals remain separate `ImportedAssertion` artifacts and cannot enter the active C1 fact graph.

**Tech Stack:** Python 3.12 standard library (`json`, `hashlib`, `sqlite3`, `dataclasses`, `enum`, `pathlib`, `unicodedata`), SQLite 3.49.1 with a 3.37 floor, pytest, ruff. No new dependency.

## Global Constraints

- Exclusive worktree: `C:\Users\V\.codex\worktrees\b39f\TongTong`.
- Exclusive branch: `codex/research-os-contract-design`.
- Do not merge, push, switch branches, modify another worktree, or use subagents.
- Preserve `tests/test_research_os_architecture.py`: `modori.research_os` must not import SQLite, filesystem, network, UI, calculation, subprocess, or `modori.research_memory` modules.
- Do not modify the recommendation UI, calculation engine, benchmark corpus, package payload, VM payload, or model artifacts.
- Do not add a dependency, generative model, archive parser, raw SQLite import, trusted-project bypass, automatic execution, or direct pipeline mutation.
- V1 rejects `QuestionSpec.local_text` and `AnswerValueKind.TEXT` from durable memory and evidence bundles.
- Imported assertions stay outside the active `Fact` graph and never satisfy C1.
- Every production behavior follows RED → verify RED → GREEN → verify GREEN → refactor.
- Starting evidence: `1729 passed, 5 skipped` with `MODORI_RSCRIPT=C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe`; `ruff check src tests` clean; design commit `3e37212`.
- The plan implements storage and quarantine foundations only. QML and end-user file-opening integration remain excluded.

---

### Task 1: Constrained canonical JSON and hash domains

**Files:**
- Create: `src/modori/research_memory/__init__.py`
- Create: `src/modori/research_memory/canonical.py`
- Create: `tests/test_research_memory_canonical.py`

**Interfaces:**
- Produces: `CanonicalizationError`, `CANONICALIZATION_ID`, `HASH_ALGORITHM`, `ZERO_HASH`, `canonical_bytes(value)`, `canonical_digest(value)`, `event_hash(sequence, previous_event_hash, body_digest)`, and `artifact_id(kind, body)`.
- Consumes: only JSON-compatible Python values.

- [ ] **Step 1: Write failing canonical-profile tests**

```python
def test_canonical_bytes_are_stable_utf8_without_whitespace() -> None:
    assert canonical_bytes({"z": "한글", "a": [True, 1, None]}) == (
        '{"a":[true,1,null],"z":"한글"}'.encode("utf-8")
    )


@pytest.mark.parametrize(
    "value, message",
    [
        ({"value": 1.5}, "floats"),
        ({"value": 9007199254740992}, "safe integer"),
        ({"한글": "value"}, "ASCII keys"),
        ({"value": unicodedata.normalize("NFD", "한글")}, "NFC"),
    ],
)
def test_canonical_profile_rejects_ambiguous_values(value: object, message: str) -> None:
    with pytest.raises(CanonicalizationError, match=message):
        canonical_bytes(value)
```

- [ ] **Step 2: Verify RED**

Run: `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests/test_research_memory_canonical.py -q -p no:cacheprovider`

Expected: import failure because `modori.research_memory` does not exist.

- [ ] **Step 3: Implement the minimal canonical profile**

```python
CANONICALIZATION_ID = "modori-cjson-v1"
HASH_ALGORITHM = "sha-256"
ZERO_HASH = "0" * 64
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_EVENT_DOMAIN = b"modori.decision-ledger.event.v1\0"
_ARTIFACT_DOMAIN = b"modori.decision-ledger.artifact.v1\0"


def canonical_bytes(value: object) -> bytes:
    normalized = _validate_and_copy(value, depth=0)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
```

Validation handles Boolean before integer, rejects float and non-string map keys,
requires lowercase ASCII schema keys, NFC strings, valid UTF-8, and the safe integer
range. Hash functions validate 64-character lowercase hex and use fixed-width
big-endian sequence bytes plus the frozen domain prefixes.

- [ ] **Step 4: Add golden hash and domain-separation tests**

```python
def test_event_hash_changes_for_sequence_previous_hash_and_body() -> None:
    body = canonical_digest({"schema_id": "modori.decision_event"})
    baseline = event_hash(1, ZERO_HASH, body)
    assert baseline != event_hash(2, ZERO_HASH, body)
    assert baseline != event_hash(1, "a" * 64, body)
    assert baseline != artifact_id("question_spec", b"{}")
```

- [ ] **Step 5: Verify focused tests and lint**

Run the focused pytest command and:

`C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m ruff check src/modori/research_memory tests/test_research_memory_canonical.py`

Expected: all focused tests pass and lint reports zero errors.

- [ ] **Step 6: Commit**

Commit message: `feat: add canonical ledger hashing`

---

### Task 2: Immutable ledger, artifact, and snapshot contracts

**Files:**
- Create: `src/modori/research_memory/ledger_contracts.py`
- Modify: `src/modori/research_memory/__init__.py`
- Create: `tests/test_research_memory_ledger_contracts.py`

**Interfaces:**
- Produces: `LedgerContractError`, `LedgerEventKind`, `LedgerArtifactKind`, `LedgerHead`, `LedgerArtifact`, `LedgerEvent`, `ResearchRequestSnapshot`, `LedgerCommit`, `LedgerReceipt`, `ImportSourceRecord`, and `ImportedAssertion`.
- Consumes: existing immutable Research OS contracts and the Task 1 canonical API.

- [ ] **Step 1: Write failing strict-event tests**

```python
def test_event_body_is_content_addressed_and_chained() -> None:
    event = LedgerEvent.create(
        project_id="project-1",
        event_id="event:project:1",
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=("a" * 64,),
        payload={"resulting_snapshot_artifact_id": "a" * 64},
        previous_event_hash=ZERO_HASH,
        recorded_at_utc=None,
    )
    assert event.verify() is None
    assert event.previous_event_hash == ZERO_HASH
    assert event.event_hash != event.body_digest
```

Tests also reject unknown payload keys, unsorted/duplicate subjects, wrong project or
sequence types, a non-genesis zero previous hash, bad timestamps, and forged hashes.

- [ ] **Step 2: Verify RED**

Run: `C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests/test_research_memory_ledger_contracts.py -q -p no:cacheprovider`

Expected: import failure because `ledger_contracts.py` does not exist.

- [ ] **Step 3: Implement closed enums and exact payload schemas**

```python
class LedgerEventKind(str, Enum):
    PROJECT_CREATED = "project_created"
    CLARIFICATION_ANSWERED = "clarification_answered"
    REVISION_ACCEPTED = "revision_accepted"
    FACT_INVALIDATED = "fact_invalidated"
    PASSPORT_COMMITTED = "passport_committed"
    DECISION_RETRACTED = "decision_retracted"
    IMPORT_ACCEPTED_AS_ASSERTIONS = "import_accepted_as_assertions"
    MIGRATION_APPLIED = "migration_applied"


class LedgerArtifactKind(str, Enum):
    QUESTION_SPEC = "question_spec"
    ESTIMAND_SPEC = "estimand_spec"
    STUDY_SPEC = "study_spec"
    ANALYSIS_PASSPORT = "analysis_passport"
    CLARIFICATION_ANSWER = "clarification_answer"
    REVISION_ACCEPTANCE = "revision_acceptance"
    DECISION_EVIDENCE_REF = "decision_evidence_ref"
    REQUEST_SNAPSHOT = "request_snapshot"
    IMPORTED_ASSERTION = "imported_assertion"
```

Every event kind maps to an exact required-key set. Every state-bearing event contains
`resulting_snapshot_artifact_id`. Subject IDs are unique and sorted. `LedgerEvent`
stores canonical body bytes, body digest, previous hash, and event hash and verifies
all four representations agree.

- [ ] **Step 4: Implement typed artifacts and request snapshots**

```python
@dataclass(frozen=True)
class ResearchRequestSnapshot:
    project_id: str
    question_artifact_id: str
    estimand_artifact_id: str
    study_artifact_id: str
    decision_evidence_artifact_ids: tuple[str, ...]
    current_dataset_fingerprint: str
    available_variable_ids: tuple[str, ...]
    surface: ProductSurface
    question_budget_remaining: int
```

`LedgerArtifact.from_value()` supports the seven existing Research OS artifact types,
`ResearchRequestSnapshot`, and `ImportedAssertion`. It rejects non-null
`QuestionSpec.local_text` and text answer values. `decode_value()` invokes the exact
existing `from_mapping()` decoder and rechecks semantic and storage identities.

`ResearchRequestSnapshot.capture(request)` returns the snapshot plus every component
and evidence artifact. `restore(artifact_lookup)` reconstructs a `ResearchRequest` and
requires matching project IDs and exact decision-evidence order.

- [ ] **Step 5: Add round-trip and authority tests**

```python
def test_snapshot_roundtrip_never_adds_imported_assertions_to_request() -> None:
    snapshot, artifacts = ResearchRequestSnapshot.capture(_request())
    restored = snapshot.restore({item.artifact_id: item for item in artifacts})
    assert restored == _request()
    assert all(
        artifact.artifact_kind is not LedgerArtifactKind.IMPORTED_ASSERTION
        for artifact in artifacts
    )
```

- [ ] **Step 6: Run focused tests and lint, then commit**

Expected: focused tests pass; ruff is clean.

Commit message: `feat: define immutable decision ledger contracts`

---

### Task 3: Hardened project-local SQLite ledger

**Files:**
- Create: `src/modori/research_memory/ledger_store.py`
- Modify: `src/modori/research_memory/__init__.py`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Create: `tests/test_research_memory_ledger_store.py`

**Interfaces:**
- Produces: `LedgerStoreError`, `LedgerPathError`, `LedgerConflictError`, `LedgerIntegrityError`, `LedgerRuntimeError`, `LedgerVerificationReport`, `default_ledger_path(project_id)`, and `DecisionLedgerStore` with `create`, `open`, `append`, `verify`, `head`, `load_request`, `events`, `artifacts`, and context-manager methods.
- Consumes: Task 2 contracts, `modori.path_policy`, Python 3.12 `sqlite3`.

- [ ] **Step 1: Write failing path and runtime tests**

```python
def test_store_rejects_relative_unc_and_wrong_suffix_paths(tmp_path: Path) -> None:
    with pytest.raises(LedgerPathError):
        DecisionLedgerStore.create(Path("relative.sqlite3"), "project-1")
    with pytest.raises(LedgerPathError):
        DecisionLedgerStore.create(Path(r"\\server\share\ledger.sqlite3"), "project-1")
    with pytest.raises(LedgerPathError):
        DecisionLedgerStore.create(tmp_path / "ledger.db", "project-1")


def test_store_requires_supported_python_sqlite_controls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ledger_store, "_has_required_runtime", lambda: False)
    with pytest.raises(LedgerRuntimeError, match="Python 3.12"):
        DecisionLedgerStore.create(_path(tmp_path), "project-1")
```

- [ ] **Step 2: Verify RED**

Run the focused store test; expect import failure.

- [ ] **Step 3: Implement path and SQLite connection policy**

The store resolves an absolute `.sqlite3` file through `resolve_secure_file_path`,
rejects links/junctions, UNC and Windows `DRIVE_REMOTE`, creates only the owned parent,
then verifies Python/SQLite feature floors before creating the database.

Connection initialization enables defensive mode, disables trusted schema, triggers,
views, writable schema and loadable extensions, sets runtime limits including attached
databases to zero, and applies WAL/FULL/foreign-key/cell-size/mmap/busy settings.

- [ ] **Step 4: Write failing schema and atomic-append tests**

```python
def test_append_commits_events_artifacts_and_snapshot_atomically(tmp_path: Path) -> None:
    store = DecisionLedgerStore.create(_path(tmp_path), "project-1")
    commit = _genesis_commit(_request())
    receipt = store.append(commit)
    assert receipt.head.sequence == 1
    assert store.load_request() == _request()
    assert tuple(event.sequence for event in store.events()) == (1,)


def test_stale_expected_head_rolls_back_every_write(tmp_path: Path) -> None:
    store = _initialized_store(tmp_path)
    before = store.verify()
    with pytest.raises(LedgerConflictError, match="head"):
        store.append(replace(_next_commit(store), expected_head=LedgerHead.genesis()))
    assert store.verify() == before
```

- [ ] **Step 5: Implement exact STRICT schema and append transaction**

Create `ledger_meta`, `ledger_artifacts`, `ledger_events`, `event_artifacts`,
`ledger_head`, `materialized_request`, and `import_sources` without triggers or views.
Store and verify the exact schema inventory/fingerprint. `append()` follows the nine
transaction steps in the design, uses `BEGIN IMMEDIATE`, checks every artifact and
event before insertion, verifies replay before commit, and returns only after commit.

- [ ] **Step 6: Write failing corruption and derived-rebuild tests**

Use a separately opened test connection before reopening the store to mutate a derived
head or materialized row and assert deterministic rebuild. Mutating an authoritative
event, artifact, schema row, project ID, or hash must raise `LedgerIntegrityError` and
must not rewrite the file.

- [ ] **Step 7: Implement verification, replay, and fallback result**

`open()` performs quick check, foreign-key check, application/user/schema validation,
complete artifact and event verification, replay, and derived comparison. Only derived
rows can be rebuilt. `verify()` returns counts, head, snapshot ID, Python and SQLite
versions, and `derived_rebuilt` without raw content.

- [ ] **Step 8: Update filesystem audit and architecture assertions**

Add only `src/modori/research_memory/ledger_store.py` to the audited file-operation
allowlist, documenting its single owned-directory `mkdir` and SQLite-created files.
No delete-capable operation is added.

- [ ] **Step 9: Run focused tests, file-operation audit, and lint; commit**

Commit message: `feat: add hardened sqlite decision ledger`

---

### Task 4: Canonical evidence bundle and complete-chain validation

**Files:**
- Create: `src/modori/research_memory/evidence_bundle.py`
- Modify: `src/modori/research_memory/__init__.py`
- Create: `tests/test_research_memory_evidence_bundle.py`

**Interfaces:**
- Produces: `EvidenceBundleErrorCode`, `EvidenceBundleError`, `EvidenceBundleLimits`, and `EvidenceBundle` with `create`, `from_bytes`, `to_bytes`, and `verify`.
- Consumes: Task 1 canonical API and Task 2 typed artifacts/events.

- [ ] **Step 1: Write failing strict-parser tests**

```python
@pytest.mark.parametrize(
    "mutator, code",
    [
        (lambda raw: b"\xef\xbb\xbf" + raw, EvidenceBundleErrorCode.INVALID_UTF8),
        (duplicate_schema_key, EvidenceBundleErrorCode.DUPLICATE_KEY),
        (add_unknown_field, EvidenceBundleErrorCode.UNKNOWN_FIELD),
        (break_canonical_whitespace, EvidenceBundleErrorCode.NONCANONICAL),
        (nest_nine_levels, EvidenceBundleErrorCode.NESTING_LIMIT),
    ],
)
def test_bundle_rejects_ambiguous_wire_forms(mutator, code) -> None:
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(mutator(_bundle().to_bytes()))
    assert caught.value.code is code
```

- [ ] **Step 2: Verify RED**

Run the focused bundle tests; expect import failure.

- [ ] **Step 3: Implement byte/depth/JSON/resource gates**

`from_bytes()` checks 16 MiB before decoding, rejects BOM and invalid UTF-8, scans
bracket depth outside strings before `json.loads`, uses `object_pairs_hook` for
duplicates, rejects floats/constants during parse, counts strings/items, validates
exact top-level keys, and requires `canonical_bytes(parsed) == raw`.

- [ ] **Step 4: Write failing chain and artifact tests**

Tests cover sequence gaps, duplicates, reorder, fork, truncation, bad genesis/hash/head,
wrong project, unresolved subjects, wrong artifact bytes/digests, local text, text
answers, path/URL/command keys, SQLite magic, ZIP magic, and missing complete history.

- [ ] **Step 5: Implement typed complete-chain validation and deterministic export**

`EvidenceBundle.create()` accepts a complete sequence beginning at one, validates every
artifact and subject, requires the last hash and sequence to equal the declared head,
and sorts artifacts deterministically by artifact ID while preserving event order.
`to_bytes()` emits one exact canonical document.

- [ ] **Step 6: Run focused tests and lint; commit**

Commit message: `feat: add canonical evidence bundle`

---

### Task 5: Authority-free import quarantine and mutation corpus

**Files:**
- Create: `src/modori/research_memory/quarantine.py`
- Modify: `src/modori/research_memory/__init__.py`
- Create: `tests/test_research_memory_quarantine.py`
- Create: `tests/fixtures/research-memory/README.md`

**Interfaces:**
- Produces: `QuarantineStage`, `QuarantineDisposition`, `QuarantineReasonCode`, `QuarantineFinding`, `QuarantineResult`, and `EvidenceBundleQuarantine.inspect(raw, *, local_dataset_fingerprint)`.
- Consumes: typed bundles and existing Research OS spec decoders.

- [ ] **Step 1: Write failing stage and downgrade tests**

```python
def test_foreign_user_confirmation_becomes_external_assertion_only() -> None:
    result = EvidenceBundleQuarantine.inspect(
        _bundle_with_confirmed_dependence(),
        local_dataset_fingerprint="d" * 64,
    )
    assert result.stage is QuarantineStage.ASSERTION_READY
    assertion = _assertion(result, "study.dependence_structure")
    assert assertion.foreign_fact_state == "user_confirmed"
    assert not hasattr(assertion, "local_fact")
    assert not hasattr(result, "research_request")
```

Dataset mismatch yields `HELD`, not silent remapping. Invalid bytes yield `REJECTED`
with a closed reason and no partially decoded bundle.

- [ ] **Step 2: Verify RED**

Run focused quarantine tests; expect import failure.

- [ ] **Step 3: Implement immutable quarantine states and assertion extraction**

Explicit extractors map QuestionSpec, EstimandSpec, StudySpec, target roles, and study
roles to closed fact addresses. Values use already canonical JSON mappings. Assertions
record foreign state, source artifact ID, provenance references, and value, but expose
no method that creates or replaces a `Fact`.

- [ ] **Step 4: Build 300 deterministic mutations**

Generate mutations in test memory from one valid canonical bundle across the ten
families in the design. Assert each mutation is rejected or held with its predeclared
closed code. The fixture directory stores only the mutation manifest and construction
rules, not 300 generated files.

- [ ] **Step 5: Add attack-surface architecture tests**

Assert quarantine code imports no `sqlite3`, `zipfile`, `tarfile`, `pickle`, `subprocess`,
network, browser, UI, calculation, or plugin modules; does not call file APIs; and has
no return type or field that can carry a ResearchRequest, Pipeline, command, path, URL,
or execution token.

- [ ] **Step 6: Run focused tests and lint; commit**

Commit message: `feat: quarantine imported decision evidence`

---

### Task 6: Atomic local coordination and assertion promotion

**Files:**
- Create: `src/modori/research_memory/promotion.py`
- Modify: `src/modori/research_memory/__init__.py`
- Create: `tests/test_research_memory_promotion.py`

**Interfaces:**
- Produces: `PromotionError`, `PromotionReceipt`, and `ResearchMemoryCoordinator` with `initialize`, `commit_ready_answer`, `commit_accepted_answer`, and `promote_imported_assertions`.
- Consumes: existing `ClarificationTransitionService`, ledger store, quarantine result, and typed contracts.

- [ ] **Step 1: Write failing initialization and ready-answer tests**

```python
def test_initialize_persists_genesis_and_exact_request(tmp_path: Path) -> None:
    store = DecisionLedgerStore.create(_path(tmp_path), "project-1")
    receipt = ResearchMemoryCoordinator().initialize(
        store,
        _request(),
        event_id="event:project:1",
        recorded_at_utc=None,
    )
    assert receipt.request == _request()
    assert store.head.sequence == 1
    assert store.load_request() == _request()


def test_ready_answer_returns_only_after_durable_commit(tmp_path: Path) -> None:
    store, request = _initialized(tmp_path)
    answer = _ready_answer(request, sequence=2)
    receipt = ResearchMemoryCoordinator().commit_ready_answer(
        store, request, _passport(request), answer
    )
    assert receipt.request.decision_evidence_refs[-1].evidence_digest == answer.digest()
    assert store.load_request() == receipt.request
```

- [ ] **Step 2: Verify RED**

Run focused promotion tests; expect import failure.

- [ ] **Step 3: Implement pure-transition then atomic-store coordination**

The coordinator verifies store/request/project/head alignment, calls the existing pure
transition service, captures every artifact and resulting snapshot, constructs the
ledger events with the answer/certificate sequences, and calls one `store.append()`.
It returns the committed request only after the store receipt exists. It has no execute,
run, pipeline, network, browser, or arbitrary file API.

- [ ] **Step 4: Write failing accepted-answer two-event tests**

An acceptance-required transition must append answer sequence `n+1` and certificate
sequence `n+2` in one SQLite transaction. A forged, missing, reused, stale, or
wrong-project certificate leaves the head and snapshot unchanged.

- [ ] **Step 5: Write failing imported-promotion tests**

```python
def test_import_promotion_keeps_assertions_outside_active_request(tmp_path: Path) -> None:
    local = _local_unknown_request(project_id="local-project")
    result = _assertion_ready_quarantine(source_project_id="foreign-project")
    receipt = ResearchMemoryCoordinator().promote_imported_assertions(
        DecisionLedgerStore.create(_path(tmp_path), "local-project"),
        local,
        result,
        project_event_id="event:project:1",
        import_event_id="event:import:2",
    )
    assert receipt.request == local
    assert receipt.imported_assertions
    assert all(ref.project_id == "local-project" for ref in receipt.request.decision_evidence_refs)
    assert ResearchOsService().resolve(receipt.request).action is PrimaryAction.CLARIFY
```

Promotion requires a fresh local ID, exact local fingerprint, empty ledger, and
`ASSERTION_READY`. It writes genesis and import events atomically, stores source digest
and assertions, does not copy foreign event hashes as local hashes, and does not alter
any active Fact.

- [ ] **Step 6: Run focused transition, store, quarantine, and promotion tests; lint; commit**

Commit message: `feat: persist local decision transitions`

---

### Task 7: Crash, performance, architecture, and full verification gates

**Files:**
- Create: `tests/test_research_memory_architecture.py`
- Create: `tests/test_research_memory_crash_recovery.py`
- Create: `tests/test_research_memory_performance.py`
- Create: `scripts/benchmark_research_memory.py`
- Modify: `scripts/quality_gate.py` only if the existing gate has an explicit extension point; otherwise leave it unchanged and document the command in the final evidence.

**Interfaces:**
- Produces: a deterministic benchmark JSON payload on stdout only when the developer-only script is explicitly invoked.
- Consumes: the public Research Memory API.

- [ ] **Step 1: Add architecture tests before changing production code**

Lock dependency direction (`research_os` never imports `research_memory`), stdlib-only
Research Memory imports, no archive/network/UI/calculation imports, no quarantine I/O,
no persistence authority in assertion types, no use of `trust_project_file=True`, and
no public clear/delete method in this delivery.

- [ ] **Step 2: Add real subprocess crash harness**

The test starts a helper process that owns a ledger, uses a pipe to announce one of the
eight transaction stages, and is terminated by the parent at that exact stage. The
parent reopens and verifies that state is exactly old or complete-new. The post-commit,
pre-receipt case must reopen as complete-new even though the child returned no receipt.

No production test hook is added. The child process monkeypatches private SQLite
execution boundaries inside the test process only.

- [ ] **Step 3: Add local performance harness and provisional tests**

The benchmark creates deterministic structured requests and events in a caller-owned
temporary directory, records environment and median/p95/max/peak-memory, and prints
canonical JSON. It never writes repository benchmark data. Default pytest uses 1,000
events with generous regression ceilings; the explicit script runs 10,000-event open,
1,000 durable appends, and the 16 MiB parser case.

- [ ] **Step 4: Verify mutation and zero-tolerance gates**

Run all Research Memory focused tests and assert 300/300 mutations classified, all
eight crash stages valid, no imported authority crossing, no stale/cross-project reuse,
and calculation-only fallback availability.

- [ ] **Step 5: Run the explicit host benchmark**

Run:

`C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts/benchmark_research_memory.py`

Record the JSON result in the final response, not the repository. The host result is
internal engineering evidence only. Do not claim the office-PC gate until the same
script runs on the target office hardware or a faithfully constrained VM.

- [ ] **Step 6: Run focused and full verification**

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m ruff check src tests scripts
git diff --check
git status --short
```

Expected: all tests pass with only predeclared skips, ruff and diff checks are clean,
and status contains only intentional task changes before the final commit.

- [ ] **Step 7: Review every design requirement and stop rule**

Map each design section to code/tests. If an office-hardware target is unavailable,
report that single evidence gap precisely; do not weaken or relabel the gate. Any other
unmet zero-tolerance rule blocks completion.

- [ ] **Step 8: Commit**

Commit message: `test: lock decision memory safety gates`
