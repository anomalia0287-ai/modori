# Live Multi-Round Research OS UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The owner forbids subagents, so execute inline with a fresh review checkpoint after every task.

**Goal:** Connect Modori's deterministic Research OS to the live local product for exactly six supported research tasks through a durable, multi-round, passport-bound flow that can clarify, recommend, abstain, prepare an exact configuration, and require a separate explicit run.

**Architecture:** Keep `modori.research_os` pure, keep durable authority in `modori.research_memory`, and add a narrow `modori.research_flow` application layer for dataset identity, task lifecycle, exact handoff, and non-inferential preflight. Expose one composed `ResearchFlowController` QObject from `UiController`; QML receives only closed presentation models and commands, while legacy heuristic candidates remain separately labelled and never share a passport, reason, or preparation object.

**Tech Stack:** Python 3.12.10; SQLite 3.49.1 STRICT tables; pandas/numpy; PySide6 6.11.1 and QML; pytest; Ruff; Bandit; the existing Decision Ledger, AnalysisPassport V2, deterministic C1 resolver, serialized worker, calculation steps, and local packaging toolchain.

## Global Constraints

- Design authority: `docs/superpowers/specs/2026-07-17-live-multi-round-research-os-ui-design.md`.
- Implementation baseline: `6513acff6b518ee4b289c5ed77ddbcdc69b661a0` on `codex/research-os-release-integration`.
- Work only in `C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration`. Do not modify either source worktree.
- Do not switch branches, merge, push, open a pull request, delete a worktree, or alter the frozen P0 evidence.
- Do not use subagents. Run every task inline and review the diff before its commit.
- No SLM, LLM, cloud model, network request, telemetry, new package, or actual user dataset.
- Preserve the exact inventory: 6 capabilities, 67 rules, 15 active clarification questions, 0 verified external routes, and at most 3 passport questions.
- `RouteReady` remains reserved but unreachable in P1. Any route-producing result is a contract failure.
- No Research OS question, candidate, abstention, or route appears before a verified durable passport receipt.
- CASUAL and PRO consume the same committed passport and action; they may differ only in presentation depth.
- Legacy heuristic candidates remain in a separate collapsed surface and never provide Research OS rationale or preparation.
- The sole capability-to-step mapping is Section 12 of the design. No `auto` correlation, `modern` routing substitution, role swap, or nearby-method fallback.
- Preflight may block preparation but cannot run inference, create or upgrade a recommendation, switch a method, add a step, or retain a statistic.
- Prepare does not mutate the pipeline. Confirm configures the exact step. Run is a later explicit command.
- A changed dataset or foreign pipeline version fails closed into `replan_required`. Carried values are editable drafts until reconfirmed.
- The task index stores only the six approved fields. It stores no path, filename, label, free text, answer, passport, raw value, URL, or command.
- P1 implements no task-delete UI or store delete method. The unfulfilled whole-ledger destruction obligation remains explicit; do not claim retention-control or secure erasure.
- Preserve `UiController` limits: at most 560 class lines, 60 methods, and 45 lines in the longest method.
- Main-thread acknowledgement enters a visible busy state within 100 ms.
- The full fingerprint worker retains its approved 10-second internal budget; the
  30-second user-visible identity ceiling does not replace or weaken that deadline.
- Run tests with `-p no:cacheprovider` so sandbox-denied pytest cache writes cannot obscure results.
- Never lower a threshold, broaden a file-operation allowlist, remove an assertion, add an exclusion, or increase skips to obtain green.

---

## Why this is one product plan

Dataset identity, task allocation, ledger commits, passport projection, exact handoff,
preflight, and the live UI form one authority chain: a later stage is invalid without
the exact receipt produced by the prior stage. Splitting those into independently
shippable plans would make false provenance easier. The sealed HP measurement kit is
different: it is a transport and supply-chain instrument with no product authority, so
it has its own sequential plan:
`docs/superpowers/plans/2026-07-17-live-research-os-office-benchmark.md`.

## File map

### Pure Research OS

- Create `src/modori/research_os/p1_intake.py`: closed six-profile intake contract and exact profile-to-QuestionSpec/EstimandSpec/StudySpec construction.
- Modify `src/modori/research_os/__init__.py`: export only the new typed intake API.

### Durable memory

- Create `src/modori/research_memory/sqlite_policy.py`: the shared application-owned SQLite path and defensive-connection primitives extracted without weakening the ledger.
- Create `src/modori/research_memory/task_index.py`: strict non-authoritative ResearchTaskIndex and transactional active/readonly allocation.
- Modify `src/modori/research_memory/ledger_store.py`: delegate only the extracted common primitives.
- Modify `src/modori/research_memory/promotion.py`: add one exact passport-retraction append operation.
- Modify `src/modori/research_memory/__init__.py`: export the closed task-index and retraction types.

### Application layer

- Create `src/modori/research_flow/__init__.py`: deliberate public API.
- Create `src/modori/research_flow/contracts.py`: identities, dispositions, preparations, durable-decision receipts, and reachable state set.
- Create `src/modori/research_flow/fingerprint.py`: streaming full-dataset and source-schema identities.
- Create `src/modori/research_flow/task_session.py`: index/ledger open-or-resume lifecycle.
- Create `src/modori/research_flow/coordinator.py`: commit-before-publish initial, answer, retraction, and replan orchestration.
- Create `src/modori/research_flow/handoff.py`: the six-row exact passport-to-step oracle.
- Create `src/modori/research_flow/preflight.py`: read-only adapter over shared step-input validators.

### Calculation validation

- Create `src/modori/steps/input_validation.py`: typed, non-inferential structural validation shared by preflight and Run.
- Modify `src/modori/steps/descriptives_table1.py`, `frequency_crosstab.py`, `correlation.py`, and `statistics.py`: call the shared validators before inferential work while preserving current errors and results.

### UI and QML

- Create `src/modori/ui/research_flow_presenter.py`: closed bilingual projections, including the existing verified question-rationale view.
- Create `src/modori/ui/research_flow_controller.py`: the sole Research OS QObject/state owner and serialized-worker boundary.
- Create `src/modori/ui/research_preparation_editor.py`: exact confirmed preparation-to-pipeline adapter.
- Modify `src/modori/ui/controller_services.py` and `controller.py`: compose and expose one QObject, update self-authored pipeline versions, and preserve the facade budget.
- Modify `src/modori/ui/pipeline_ops.py`: support exact paired-comparison construction/result binding.
- Modify `src/modori/ui/session.py`: retain Research OS-assisted provenance and invalidate it on relevant drift.
- Create `src/modori/ui/qml/components/ResearchFlowPanel.qml`, `ResearchQuestionCard.qml`, and `ResearchCandidateCard.qml`.
- Modify `src/modori/ui/qml/components/GuideRail.qml` and `src/modori/ui/qml/screens/WorkScreen.qml`: guided embedding, PRO opt-in rail, and separately collapsed legacy candidates.
- Modify `src/modori/ui/strings.py` and only necessary existing semantic theme roles.

### Tests and evidence

- Create focused tests named in each task below.
- Create `docs/qa/live-research-os-p1-evidence.md` only after all local and target gates are known.
- Update `docs/security/file-operations-audit-2026-06-29.md` only for the exact task-index path operation.

---

### Task 1: Freeze the application-layer contracts and dependency direction

**Files:**

- Create: `src/modori/research_flow/__init__.py`
- Create: `src/modori/research_flow/contracts.py`
- Create: `tests/test_research_flow_contracts.py`
- Modify: `tests/test_research_memory_architecture.py`

**Interfaces:**

- Produces: `ResearchFlowState`, `P1_REACHABLE_STATES`, `StaticBoundary`, `DatasetIdentity`, `PreflightDisposition`, `FlowErrorKind`.
- Produces later-extensible frozen contracts without importing UI, filesystem, SQLite, network, subprocess, or calculation code.

- [x] **Step 1: Write the failing closed-state and identity tests**

```python
def test_route_ready_is_reserved_but_not_p1_reachable() -> None:
    assert ResearchFlowState.ROUTE_READY.value == "route_ready"
    assert ResearchFlowState.ROUTE_READY not in P1_REACHABLE_STATES
    assert ResearchFlowState.CANDIDATE_READY in P1_REACHABLE_STATES


def test_dataset_identity_rejects_unordered_or_duplicate_variable_ids() -> None:
    with pytest.raises(ResearchFlowContractError, match="variable_ids"):
        DatasetIdentity(
            fingerprint_contract_id="modori.dataset-fingerprint.v1",
            dataset_fingerprint="a" * 64,
            source_schema_fingerprint="b" * 64,
            variable_ids=("score", "score"),
            pipeline_version=4,
        )


def test_research_flow_package_has_no_ui_or_persistence_import() -> None:
    forbidden = ("modori.ui", "modori.research_memory", "sqlite3", "PySide6")
    assert architecture_import_violations(Path("src/modori/research_flow/contracts.py"), forbidden) == []
```

- [x] **Step 2: Run the tests and confirm the missing package fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_contracts.py tests/test_research_memory_architecture.py -q -p no:cacheprovider
```

Expected: collection fails because `modori.research_flow` does not exist.

- [x] **Step 3: Implement the closed contracts**

Use exactly these state values:

```python
class ResearchFlowState(str, Enum):
    IDLE = "idle"
    FINGERPRINTING = "fingerprinting"
    INTAKE_CAUSAL = "intake_causal"
    CAUSAL_SCOPE_NOTICE = "causal_scope_notice"
    INTAKE_BLOCKED = "intake_blocked"
    INTAKE_PROFILE = "intake_profile"
    INTAKE_ROLES = "intake_roles"
    SCOPE_BOUNDARY = "scope_boundary"
    COMMITTING = "committing"
    CLARIFY_READY = "clarify_ready"
    HANDOFF_PREFLIGHT = "handoff_preflight"
    CANDIDATE_READY = "candidate_ready"
    PREPARATION_BLOCKED = "preparation_blocked"
    ABSTAIN_READY = "abstain_ready"
    ROUTE_READY = "route_ready"
    MEMORY_UNAVAILABLE = "memory_unavailable"
    FAILURE = "failure"
    CORRUPTION = "corruption"
    REPLAN_REQUIRED = "replan_required"
    RECOVERY_PENDING = "recovery_pending"
    RETRACTED = "retracted"
    CANCELLED = "cancelled"
    PREPARE_REVIEW = "prepare_review"
    CONFIRMED = "confirmed"
    MANUAL_RUN = "manual_run"


P1_REACHABLE_STATES = frozenset(ResearchFlowState) - {
    ResearchFlowState.ROUTE_READY,
}


class StaticBoundary(str, Enum):
    CAUSAL_SCOPE_NOTICE = "causal_scope_notice"
    CAUSAL_INTENT_UNKNOWN = "causal_intent_unknown"
    SCOPE_BOUNDARY = "scope_boundary"


class PreflightDisposition(str, Enum):
    PREPARE_READY = "prepare_ready"
    PREPARE_BLOCKED = "prepare_blocked"
    STALE = "stale"
    FAILURE = "failure"


class FlowErrorKind(str, Enum):
    UNAVAILABLE = "unavailable"
    FAILURE = "failure"
    CORRUPTION = "corruption"
    STALE = "stale"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class DatasetIdentity:
    fingerprint_contract_id: str
    dataset_fingerprint: str
    source_schema_fingerprint: str
    variable_ids: tuple[str, ...]
    pipeline_version: int
```

`DatasetIdentity` validates lowercase SHA-256 digests, a nonnegative integer
`pipeline_version`, unique NFC variable IDs in exact dataset-column order, and the
literal contract ID `modori.dataset-fingerprint.v1`. `FlowErrorKind` has exactly
`unavailable`, `failure`, `corruption`, `stale`, and `unsupported`.
`StaticBoundary` has only `causal_scope_notice`, `causal_intent_unknown`, and
`scope_boundary`; none is a durable decision or may carry a passport digest.

- [x] **Step 4: Add architecture assertions**

Keep `modori.research_os` independent of `research_memory` and `research_flow`.
Permit `research_flow` to depend inward on `research_os` and `core`, but forbid it from
importing `modori.ui`. Permit persistence imports only in the later
`task_session.py` boundary; `contracts.py` and `fingerprint.py` stay persistence-free.

- [x] **Step 5: Run the focused gate**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_contracts.py tests/test_research_os_architecture.py tests/test_research_memory_architecture.py -q -p no:cacheprovider
```

Expected: all tests pass.

- [x] **Step 6: Commit**

```powershell
git add -- src/modori/research_flow/__init__.py src/modori/research_flow/contracts.py tests/test_research_flow_contracts.py tests/test_research_memory_architecture.py
git commit -m "feat: define live Research OS flow contracts"
```

---

### Task 2: Implement the full-current-dataset fingerprint contract

**Files:**

- Create: `src/modori/research_flow/fingerprint.py`
- Create: `tests/test_research_flow_fingerprint.py`
- Modify: `src/modori/research_flow/__init__.py`

**Interfaces:**

- Produces: `SourceSchemaDescriptor`.
- Produces: `fingerprint_dataset(dataset: Dataset, source_schema: SourceSchemaDescriptor, *, pipeline_version: int, cancel_requested: Callable[[], bool], max_cells: int = 5_000_000) -> DatasetIdentity`.
- Raises: `FingerprintCancelled`, `FingerprintLimitError`, or `FingerprintContractError`; never falls back to schema-only identity.

- [x] **Step 1: Write the typed-value and metamorphic failing tests**

Build a fixture containing bool, integer, float, `-0.0`, missing, NFC/NFD text,
naive date, UTC date, categorical metadata, labels, declared missing codes, and mixed
column order. Assert:

```python
first = fingerprint_dataset(dataset, source_schema, pipeline_version=7, cancel_requested=lambda: False)
second = fingerprint_dataset(dataset, source_schema, pipeline_version=7, cancel_requested=lambda: False)
assert first == second
assert first.variable_ids == tuple(str(column) for column in dataset.df.columns)

assert fingerprint_dataset(row_reordered, source_schema, pipeline_version=7, cancel_requested=lambda: False).dataset_fingerprint != first.dataset_fingerprint
assert fingerprint_dataset(column_reordered, source_schema, pipeline_version=7, cancel_requested=lambda: False).dataset_fingerprint != first.dataset_fingerprint
assert fingerprint_dataset(label_changed, source_schema, pipeline_version=7, cancel_requested=lambda: False).dataset_fingerprint != first.dataset_fingerprint
assert fingerprint_dataset(nfc_equivalent, source_schema, pipeline_version=7, cancel_requested=lambda: False).dataset_fingerprint == first.dataset_fingerprint
```

Also assert that a changed file type, sheet/layout selection, source-column order, or
included-column order changes only `source_schema_fingerprint` when the current
Dataset remains identical.

- [x] **Step 2: Write cancellation and resource-limit tests**

```python
with pytest.raises(FingerprintCancelled):
    fingerprint_dataset(dataset, source_schema, pipeline_version=2, cancel_requested=lambda: True)

with pytest.raises(FingerprintLimitError, match="5"):
    fingerprint_dataset(six_cell_dataset, source_schema, pipeline_version=2, cancel_requested=lambda: False, max_cells=5)
```

Assert the cancellation callback is checked at least once per 8,192 cells and before
final digest publication. Assert the worker deadline remains 10 seconds and a deadline
failure returns typed unavailability without publishing or caching a partial digest.

- [x] **Step 3: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_fingerprint.py -q -p no:cacheprovider
```

Expected: FAIL because `fingerprint_dataset` is absent.

- [x] **Step 4: Implement a length-framed streaming encoder**

The SHA-256 stream begins with the ASCII contract ID and uses one-byte type tags plus
unsigned 64-bit big-endian lengths. Encode:

- missing as one fixed marker;
- booleans before integers so `True` never aliases `1`;
- arbitrary Python/numpy integers as canonical signed decimal ASCII;
- finite floats as big-endian IEEE-754 binary64, normalizing `-0.0` to `+0.0`;
- infinities as distinct positive/negative tokens and every NaN/NA as missing;
- text after Unicode NFC;
- datetime/date/timedelta as typed ISO-8601 or signed nanoseconds, never locale text;
- ordered columns, row count, variable metadata, then values in row-major order.

Metadata includes name, label, measure, value-label pairs sorted by encoded key,
declared missing values in declared order, and dtype. Exclude `origin_step_id` because
it is pipeline bookkeeping rather than dataset meaning; lock this exclusion with a
metamorphic test.

`SourceSchemaDescriptor` contains only:

```python
@dataclass(frozen=True)
class SourceSchemaDescriptor:
    source_type: str
    sheet_name: str | None
    header_row_index: int | None
    header_row_count: int | None
    data_start_row_index: int | None
    source_columns: tuple[str, ...]
    included_columns: tuple[str, ...]
```

It contains no path or filename.

- [x] **Step 5: Run deterministic, mutation, and 5-million-cell bounded tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_fingerprint.py -q -p no:cacheprovider
```

Expected: all tests pass and peak auxiliary memory remains O(column metadata), not a
second full canonical dataset.

- [x] **Step 6: Commit**

```powershell
git add -- src/modori/research_flow/__init__.py src/modori/research_flow/fingerprint.py tests/test_research_flow_fingerprint.py
git commit -m "feat: bind Research OS to full dataset identity"
```

---

### Task 3: Extract shared hardened SQLite policy without changing ledger behaviour

**Files:**

- Create: `src/modori/research_memory/sqlite_policy.py`
- Create: `tests/test_research_memory_sqlite_policy.py`
- Modify: `src/modori/research_memory/ledger_store.py`
- Modify: `tests/test_research_memory_architecture.py`
- Test: all `tests/test_research_memory_ledger_store.py` and crash-recovery tests

**Interfaces:**

- Produces internal `validate_managed_sqlite_path(...) -> Path`.
- Produces internal `configure_managed_connection(connection, *, query_only: bool, authorizer: Callable[..., int] | None) -> None`.
- The ledger's public API, schema bytes, schema fingerprint, exceptions, PRAGMAs, and on-disk output remain unchanged.

- [x] **Step 1: Add characterization tests before moving code**

Capture the current accept/reject matrix for local absolute paths, missing parents,
UNC, remote drive, symlink, junction/reparse point, wrong suffix, file replacement,
`foreign_keys`, `trusted_schema`, `defensive`, WAL, `synchronous=FULL`,
`busy_timeout`, authorizer denials, and read-only query mode. Record a fresh ledger's
schema fingerprint and canonical exported bundle digest as golden values inside the
test.

- [x] **Step 2: Run the characterization cohort**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_memory_ledger_store.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_sqlite_policy.py -q -p no:cacheprovider
```

Expected: only the new import fails; every pre-existing ledger test passes.

- [x] **Step 3: Move only common path/connection primitives**

Move the bodies of current `_is_unc`, `_is_remote_drive`, `_validated_path`,
`_configure_durability`, and the common portion of `_configure_connection` into
`sqlite_policy.py`. Keep ledger schema SQL, schema validation, authorizer policy,
application ID, user version, data-version binding, and integrity checks in
`ledger_store.py`.

The call shape is fixed:

```python
path = validate_managed_sqlite_path(
    candidate,
    expected_parent=managed_parent,
    expected_filename=None,
    required_suffix=".sqlite3",
)
configure_managed_connection(
    connection,
    query_only=query_only,
    authorizer=ledger_authorizer,
)
```

`expected_parent` must already be an application-derived absolute local path. No
public caller may supply an arbitrary root through a UI or imported payload.

- [x] **Step 4: Prove byte and failure equivalence**

Run the characterization cohort again, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_memory_architecture.py tests/test_research_memory_ledger_contracts.py tests/test_research_memory_ledger_store.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_performance.py -q -p no:cacheprovider
```

Expected: all pass; the golden schema/bundle digests are unchanged.

- [x] **Step 5: Commit**

```powershell
git add -- src/modori/research_memory/sqlite_policy.py src/modori/research_memory/ledger_store.py tests/test_research_memory_sqlite_policy.py tests/test_research_memory_architecture.py
git commit -m "refactor: share hardened SQLite policy"
```

---

### Task 4: Add the strict non-authoritative ResearchTaskIndex

**Files:**

- Create: `src/modori/research_memory/task_index.py`
- Create: `tests/test_research_task_index.py`
- Modify: `src/modori/research_memory/__init__.py`
- Modify: `tests/test_research_memory_architecture.py`
- Modify later in Task 15: `tests/test_file_operation_audit.py` and the audit document

**Interfaces:**

- Produces: `ResearchTaskRecord` and `ResearchTaskState.ACTIVE | READONLY`.
- Produces: `default_task_index_path() -> Path`.
- Produces: `ResearchTaskIndex.open_or_create()` at `default_task_index_path()`; there is
  no public arbitrary-path parameter.
- Produces: `locate_active(fingerprint_contract_id: str, dataset_fingerprint: str) -> ResearchTaskRecord | None`.
- Produces: `allocate(..., task_project_id: str, created_at_utc: str | None, replaces_task_project_id: str | None = None) -> ResearchTaskRecord`.
- Produces: `mark_readonly(task_project_id: str) -> ResearchTaskRecord` and `verify(full_integrity: bool = False)`.

- [x] **Step 1: Write the exact schema-inventory test**

The database has one STRICT table and only its required auto/unique indexes:

```sql
CREATE TABLE research_tasks(
    task_project_id TEXT PRIMARY KEY NOT NULL,
    fingerprint_contract_id TEXT NOT NULL,
    dataset_fingerprint TEXT NOT NULL,
    task_ordinal INTEGER NOT NULL CHECK(task_ordinal >= 1),
    state TEXT NOT NULL CHECK(state IN ('active','readonly')),
    created_at_utc TEXT NULL,
    UNIQUE(fingerprint_contract_id, dataset_fingerprint, task_ordinal)
) STRICT
```

Add a unique partial index over
`(fingerprint_contract_id, dataset_fingerprint) WHERE state='active'`. Reject every
extra table, trigger, view, column, malformed SQL, wrong application ID/user version,
or schema fingerprint.

- [x] **Step 2: Write allocation, clock, and concurrency failing tests**

Assert:

```python
first = index.allocate(contract, digest, task_project_id="task:a", created_at_utc=None)
assert first.task_ordinal == 1
assert first.created_at_utc is None

with pytest.raises(TaskIndexConflictError):
    index.allocate(contract, digest, task_project_id="task:b", created_at_utc=None)

second = index.allocate(
    contract,
    digest,
    task_project_id="task:b",
    created_at_utc="2026-07-17T00:00:00Z",
    replaces_task_project_id="task:a",
)
assert second.task_ordinal == 2
assert index.get("task:a").state is ResearchTaskState.READONLY
```

Use racing connections to prove one active row and one ordinal winner. Prove
`created_at_utc=None` does not change identity/order, an injected UTC value is
display-only, invalid UTC is rejected, and there is no local-time fallback.

- [x] **Step 3: Write integrity, path, resource, and import-denial tests**

Cover the 10,000-row limit; external database modification; WAL/SHM; quick/full
integrity; row forgery; reparse/remote paths; query-only verification; unknown fields;
and absence of any bundle/import/promote/delete API. Reaching 10,000 returns typed
`resource_limit` unavailability and never evicts a row.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_task_index.py tests/test_research_memory_architecture.py -q -p no:cacheprovider
```

Expected: FAIL because `task_index.py` is absent.

- [x] **Step 5: Implement the index with `BEGIN IMMEDIATE` allocation**

Use the shared SQLite policy, an application-specific ID distinct from the Decision
Ledger, schema fingerprint verification, `PRAGMA data_version` checks, and a closed
authorizer. Allocation computes `MAX(task_ordinal)+1` inside the same immediate
transaction that optionally changes the exact expected active task to readonly.
An unexpected active task or changed data version fails; it is never overwritten.

- [x] **Step 6: Run focused persistence and adversarial tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_task_index.py tests/test_research_memory_architecture.py tests/test_research_memory_ledger_store.py tests/test_research_memory_crash_recovery.py -q -p no:cacheprovider
```

Expected: all pass.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/research_memory/task_index.py src/modori/research_memory/__init__.py tests/test_research_task_index.py tests/test_research_memory_architecture.py
git commit -m "feat: add local Research OS task index"
```

### Task 5: Build the pure six-profile structured intake

**Files:**

- Create: `src/modori/research_os/p1_intake.py`
- Modify: `src/modori/research_os/__init__.py`
- Create: `tests/test_research_os_p1_intake.py`
- Modify: `tests/test_research_os_architecture.py`

**Interfaces:**

```python
class P1TaskProfile(str, Enum):
    NUMERIC_DISTRIBUTION = "numeric_distribution"
    CATEGORY_FREQUENCY = "category_frequency"
    INDEPENDENT_TWO_GROUP_MEAN = "independent_two_group_mean"
    PAIRED_TWO_TIME_MEAN_CHANGE = "paired_two_time_mean_change"
    LINEAR_CO_MOVEMENT = "linear_co_movement"
    RANK_CO_MOVEMENT = "rank_co_movement"

@dataclass(frozen=True)
class P1RoleBindings:
    outcome: tuple[str, ...] = ()
    group: tuple[str, ...] = ()
    focal_predictor: tuple[str, ...] = ()
    repeated_measure_order: tuple[str, ...] = ()

@dataclass(frozen=True)
class P1IntakeDraft:
    profile: P1TaskProfile
    roles: P1RoleBindings

def build_p1_request(
    draft: P1IntakeDraft,
    *,
    task_project_id: str,
    initial_event_id: str,
    dataset_fingerprint: str,
    source_schema_fingerprint: str,
    available_variable_ids: tuple[str, ...],
    language: Language,
) -> ResearchRequest: ...

def build_causal_abstention_request(
    *,
    task_project_id: str,
    initial_event_id: str,
    dataset_fingerprint: str,
    source_schema_fingerprint: str,
    available_variable_ids: tuple[str, ...],
    language: Language,
) -> ResearchRequest: ...
```

The module remains pure. It receives primitive identities and constructs only existing
`QuestionSpec`, `EstimandSpec`, `StudySpec`, and `ResearchRequest` values. It does not
import `DatasetIdentity`, SQLite, filesystem, UI, or calculation code.
The task project ID and preallocated initial event ID bind every component envelope;
the separate source-schema fingerprint is never fabricated from the dataset digest.

- [x] **Step 1: Write exact profile-mapping failure tests**

For every Section 8.2 row, assert the exact facts, their authority
`user_confirmed`, role cardinality and order, the unchanged unknown fields, surface
`experimental`, and question budget `3`. Assert that:

- the paired profile binds `outcome=(after,)`,
  `repeated_measure=(before, after)`, and the same repeated order;
- association roles preserve the user-confirmed outcome/predictor orientation without
  implying time, prediction, or causation;
- the initial builder rejects weight/cluster fields because those facts belong to later
  planner questions, while transition tests prove an explicit `none` answer creates a
  user-confirmed empty tuple that remains distinguishable from an omitted binding;
- undeclared roles, duplicate IDs, unavailable IDs, wrong cardinalities, causal intent,
  and unsupported profiles fail closed; and
- only `build_causal_abstention_request()` creates the minimal confirmed causal request
  that resolves to `unsupported_causal_target`.

- [x] **Step 2: Write closure and mutation tests**

Walk all six intake requests through the current resolver and
`ClarificationTransitionService`. Safe `cluster -> dependence -> weight` answers must
reach exactly summary, frequency, Pearson, or Spearman within three questions; safe
`cluster -> weight` answers must reach exactly Welch or paired t within two. Mutate one
declared fact, method-space digest, registry digest, question budget, empty-role
authority, and before/after order; each mutation must change or invalidate the result,
never silently preserve the intended capability. `Not sure`, nonempty weight, and
nonempty cluster branches must block or abstain without substituting an unweighted,
independent, or otherwise nearby capability.

- [x] **Step 3: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_os_p1_intake.py tests/test_research_os_architecture.py tests/test_research_os_transitions.py -q -p no:cacheprovider
```

Expected: FAIL because the closed intake module is absent.

- [x] **Step 4: Implement only the approved mappings**

Use one immutable mapping table corresponding exactly to design Section 8.2. Do not
derive a profile from variable metadata, labels, distributions, or a nearby method.
Keep profile construction separate from the causal-abstention constructor so the UI's
static causal notice can remain a no-write state.

- [x] **Step 5: Re-run focused pure-layer tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_os_p1_intake.py tests/test_research_os_service.py tests/test_research_os_transitions.py tests/test_research_os_architecture.py -q -p no:cacheprovider
```

Expected: all pass, with the six intended terminal capabilities reproduced within the
fixed budget.

- [x] **Step 6: Commit**

```powershell
git add -- src/modori/research_os/p1_intake.py src/modori/research_os/__init__.py tests/test_research_os_p1_intake.py tests/test_research_os_architecture.py
git commit -m "feat: add bounded Research OS intake"
```

### Task 6: Implement crash-recoverable task sessions and exact passport retraction

**Files:**

- Create: `src/modori/research_flow/task_session.py`
- Modify: `src/modori/research_memory/promotion.py`
- Modify: `src/modori/research_memory/__init__.py`
- Create: `tests/test_research_flow_task_session.py`
- Modify: `tests/test_research_memory_promotion.py`
- Modify: `tests/test_research_memory_crash_recovery.py`
- Modify: `tests/test_research_memory_passport_state.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class ResearchTaskHandle:
    record: ResearchTaskRecord
    ledger_path: Path

class ResearchTaskSessionStore:
    def open_or_allocate(
        self,
        identity: DatasetIdentity,
        *,
        expected_active_task_id: str | None,
    ) -> ResearchTaskHandle: ...

    def start_replan(
        self,
        previous: ResearchTaskHandle,
        new_identity: DatasetIdentity,
    ) -> ResearchTaskHandle: ...

class ResearchMemoryCoordinator:
    def retract_current_passport(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        passport: AnalysisPassport,
        *,
        event_id: str,
        recorded_at_utc: str | None = None,
    ) -> PromotionReceipt: ...
```

- [x] **Step 1: Characterize the ledger-before-index recovery protocol**

Write tests for every observable session boundary:

1. generate a closed task ID and derive its application-owned ledger path;
2. create and fully verify a genuine empty ledger before publishing any locator;
3. allocate the active index row; and
4. fully reverify the located ledger and return a handle only after classifying it as
   genuine empty or verified initialized state.

Inject a crash before and after each boundary. Because two SQLite databases cannot be
made honestly atomic, an active locator must never precede the ledger it names. After
such a crash, a missing ledger would be indistinguishable from deleted authoritative
history. A crash before locator allocation may leave only a fully verified empty,
authority-free orphan and spends no ordinal. A crash after locator allocation resumes
the exact active row, inspects the ledger, exposes only a genuine empty ledger to Task 7
for initialization, and reuses a verified initialized ledger. The session layer does
not append a request itself. It must never allocate a second ordinal merely because the
locator receipt was lost, and it never recreates a missing ledger behind an active row.

- [x] **Step 2: Test correction, drift, and readonly history**

Assert that correction of a consumed answer and data-drift replanning allocate a fresh
task ID and ordinal, mark the previous row readonly, and never modify the previous
ledger. A mismatch in the expected active ID, fingerprint contract, dataset digest, or
ledger project ID fails closed. Missing, foreign, reparse-point, externally changed, or
corrupt ledgers remain unavailable/corrupt rather than being recreated over history.

- [x] **Step 3: Test `decision_retracted` at the public coordinator boundary**

Start with a verified current V2 passport, call the new method, and assert exact event
kind, previous-head binding, exact snapshot-only subject closure, reference to the
retracted passport-commit event, and deterministic state folding. Reject a consumed,
stale, foreign, already retracted, or non-current passport. Prove the passport artifact
remains immutable in history, the request snapshot survives, and no answer event is
reversed.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_task_session.py tests/test_research_memory_promotion.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_passport_state.py -q -p no:cacheprovider
```

Expected: FAIL because the session adapter and retraction operation do not exist.

- [x] **Step 5: Implement the smallest recoverable protocol**

Inject ID and UTC-clock factories. Keep index status changes transactional inside the
index, and ledger commits transactional inside the ledger; do not describe them as one
cross-database transaction. Precreate and fully verify the authority-free empty ledger,
then transactionally publish its locator; never publish a locator first. Reuse
`default_ledger_path()` and the verified store rather than adding an arbitrary path
parameter. Implement retraction with the current ledger contracts and passport-state
fold, not with deletion or mutation.

- [x] **Step 6: Run focused recovery and authority tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_task_session.py tests/test_research_memory_promotion.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_passport_state.py tests/test_research_memory_ledger_store.py -q -p no:cacheprovider
```

Expected: all pass, including every poison point and reopen.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/research_flow/task_session.py src/modori/research_memory/promotion.py src/modori/research_memory/__init__.py tests/test_research_flow_task_session.py tests/test_research_memory_promotion.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_passport_state.py
git commit -m "feat: add recoverable research task sessions"
```

### Task 7: Orchestrate durable multi-round decisions before publication

**Files:**

- Create: `src/modori/research_flow/coordinator.py`
- Preserve unchanged: `src/modori/research_flow/contracts.py`
- Modify: `src/modori/research_flow/__init__.py`
- Modify: `src/modori/research_memory/task_index.py`
- Create: `tests/test_research_flow_coordinator.py`
- Create: `tests/test_research_flow_concurrency.py`
- Modify: `tests/test_research_memory_crash_recovery.py`
- Modify: `tests/test_research_task_index.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DurableDecision:
    task_project_id: str
    request: ResearchRequest
    passport: AnalysisPassport
    passport_artifact_id: str
    passport_digest: str
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str
    action: PrimaryAction


@dataclass(frozen=True)
class DurablePendingDecision:
    task_project_id: str
    request: ResearchRequest
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str
    reason_code: Literal["decision_not_committed"]


@dataclass(frozen=True)
class DurableRetraction:
    task_project_id: str
    request: ResearchRequest
    retracted_passport_artifact_id: str
    retracted_passport_digest: str
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str


DurableFlowRecord = DurableDecision | DurablePendingDecision | DurableRetraction


class LiveResearchFlowCoordinator:
    def commit_initial(
        self,
        handle: ResearchTaskHandle,
        request: ResearchRequest,
    ) -> DurableDecision: ...

    def commit_answer(
        self,
        handle: ResearchTaskHandle,
        answer: ClarificationAnswerEvent,
    ) -> DurableDecision: ...

    def retract_current(self, handle: ResearchTaskHandle) -> DurableRetraction: ...

    def recover_current(self, handle: ResearchTaskHandle) -> DurableFlowRecord: ...

    def resume_pending(
        self,
        handle: ResearchTaskHandle,
        pending: DurablePendingDecision,
    ) -> DurableDecision: ...
```

The durable record types live in `coordinator.py`, not in the pure
`research_flow/contracts.py` module. Their constructors must recompute the exact
Decision Ledger passport artifact ID, so placing them in the pure module would either
introduce a memory-layer dependency there or duplicate the ledger hash domain. Keeping
the memory-bound receipt contracts beside the coordinator preserves the existing pure
contract architecture without weakening constructor validation.

`DurableDecision` contains only a verified current request, V2 passport, ledger receipt
identity, and closed disposition. Its constructor rejects any action, digest, event, or
request binding that disagrees with the passport/receipt; it is not yet a UI model.
`recover_current()` is read-only. A request/answer commit with no later passport returns
`DurablePendingDecision`; only the explicit `resume_pending()` action may complete it.
A retracted current passport returns `DurableRetraction` and is never replanned or
reissued automatically. Its view offers only a fresh-task/replan entry and direct
analysis; answer, Prepare, and Resume are absent.

- [x] **Step 1: Write commit-before-publication contract tests**

For initial commit, each answer, retraction, and recovery, poison:

- request initialization;
- resolver/planner return;
- passport construction;
- passport append;
- post-append readback and audit; and
- answer append.

No method may return a question, candidate, or abstention until the corresponding
request/passport has a durable receipt and has been re-read as current. A failed later
stage leaves the prior verified decision recoverable. No automatic retry loop is
allowed.

Crash after a request or answer receipt but before passport receipt must recover as
`DurablePendingDecision` with no question/candidate. Crash after `decision_retracted`
must recover as `DurableRetraction`. An explicit pending-resume may append the missing
passport once; retraction has no resume-to-same-passport path.

- [x] **Step 2: Write replay, race, and budget tests**

Race two initial calls, double clicks, two answer calls, and two windows. Exactly one
unconsumed clarify passport may be current; a duplicate may return the exact same
verified artifact but cannot create a second question or spend budget twice. Reject
stale/replayed/consumed/foreign answers, wrong revision IDs, duplicate event IDs,
modified artifacts, and a fourth question. `Not sure` stays typed and either advances
to another committed decision or honest abstention. Serialize the ledger's one-private-
writer contract with an exact-active-record TaskIndex lease that changes no index row.
SQLite `BUSY` or `LOCKED` is a typed conflict, never ledger or index corruption.
Exhaustively walk every closed answer-branch class selected by all six P1 profiles.
The frozen closure is 108 reachable states and 74 terminal paths; every live answer
must remain a ready transition with `requires_acceptance=false`. Any future exposure of
an estimand-changing answer fails this task rather than manufacturing user acceptance.

- [x] **Step 3: Write frozen-inventory and route-unreachability tests**

At construction and every recovery, assert 6 capabilities, 67 rules, 15 active questions,
and 0 routes. No service result may become `RouteReady`; attempted injection of a route
disposition is a contract failure. This test is deliberately redundant with Task 1 so
catalog drift cannot make a reserved state live accidentally.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_coordinator.py tests/test_research_flow_concurrency.py tests/test_research_memory_crash_recovery.py -q -p no:cacheprovider
```

Expected: FAIL because the application coordinator is absent.

- [x] **Step 5: Implement the authority chain by composition**

Compose the existing deterministic service, transition service, memory coordinator,
passport auditor/state fold, and task session. Allocate the event ID before sealing the
passport, append atomically inside the ledger, verify the receipt and current artifact,
then return. Do not duplicate planner search or expose a raw store outside this layer.
If opening succeeds but the mandatory post-open full verification fails, close the
SQLite handle before classifying the failure; Windows race tests must prove no file
handle survives teardown. Hold a zero-row-mutation `BEGIN IMMEDIATE` lease on the exact
active TaskIndex record while one Decision Ledger private writer is open. The lease is
only cross-process serialization: it grants no fact or decision authority, makes no
cross-database atomicity claim, and is released automatically on process death. A
ledger commit that survives process death still recovers through the same pending or
complete-decision rules.

- [x] **Step 6: Run focused multi-round and memory tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_coordinator.py tests/test_research_flow_task_session.py tests/test_research_flow_concurrency.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_passport_state.py tests/test_research_os_transitions.py -q -p no:cacheprovider
```

Expected: all pass, including recovery from every injected boundary.

Pre-commit evidence on 2026-07-17: Ruff passed; the exact Task 7 gate plus the P1
closure test passed 211 tests; the adjacent flow, intake, resolver, ledger, promotion,
and crash-recovery gate passed 416 tests. Both pytest runs disabled the cache provider.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/research_flow/coordinator.py src/modori/research_flow/contracts.py src/modori/research_flow/__init__.py tests/test_research_flow_coordinator.py tests/test_research_flow_concurrency.py tests/test_research_memory_crash_recovery.py
git commit -m "feat: add durable multi-round research flow"
```

### Task 8: Enforce the exact six-row passport-to-step handoff

**Files:**

- Create: `src/modori/research_flow/handoff.py`
- Modify: `src/modori/research_flow/contracts.py`
- Modify: `src/modori/research_flow/__init__.py`
- Create: `tests/test_research_flow_handoff.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class PassportStepMapping:
    passport_artifact_id: str
    passport_digest: str
    capability_key: str
    dataset_fingerprint: str
    step_type: str
    canonical_step_params: bytes
    experimental: Literal[True]
    requires_explicit_configure_confirm_run: Literal[True]
    mapping_digest: str


@dataclass(frozen=True)
class PassportBoundPreparation:
    passport_artifact_id: str
    passport_digest: str
    capability_key: str
    dataset_fingerprint: str
    step_type: str
    canonical_step_params: bytes
    mapping_digest: str
    preflight_disposition: PreflightDisposition
    experimental: Literal[True]
    requires_explicit_configure_confirm_run: Literal[True]
    preparation_digest: str


def map_passport_to_step(
    passport: AnalysisPassport,
    request: ResearchRequest,
    *,
    current_dataset_fingerprint: str,
) -> PassportStepMapping: ...
```

- [x] **Step 1: Write a byte-canonical oracle test for all six rows**

Assert the exact Section 12 step type and params after canonicalization:

- summary -> `stats.descriptives_table1`, explicit missing counts and language;
- frequency -> `stats.frequency_crosstab`, mode `frequency` and language;
- Pearson/Spearman -> `stats.correlation`, exact ordered pair, explicit method,
  `pairwise`, and `none` adjustment;
- Welch -> `stats.compare_groups`, exact roles and `always_welch`; and
- paired t -> `stats.paired_comparison`, exact before/after and `classic`.

Pass each result through the current step schema migrator and validator.

- [x] **Step 2: Write adversarial identity and mutation tests**

Kill mutants for `pearson -> auto`, `spearman -> auto`, `always_welch -> modern`,
`classic -> modern`, outcome/predictor swap, outcome/group swap, before/after swap,
missing or extra language, omitted/extra params, a future schema version, unknown or
nearby capability, extra role, duplicate role, mismatched repeated order, changed
fingerprint, wrong request binding, and a foreign/non-current passport. Every case must
return typed handoff failure; no nearby-method fallback is permitted.

- [x] **Step 3: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_handoff.py tests/test_research_os_passport.py tests/test_research_os_passport_audit.py -q -p no:cacheprovider
```

Expected: FAIL because the exact mapper does not exist.

- [x] **Step 4: Implement a closed immutable mapping table**

Bind the intermediate `PassportStepMapping` to passport artifact ID/digest, capability
key, dataset digest, exact step type, canonical params, experimental status, and
explicit configure/confirm/run requirement. Compute `mapping_digest` over every
normative mapping field. It has no preflight disposition and is not yet a preparation
or visible candidate. Task 9 alone may combine a verified mapping with preflight into a
`PassportBoundPreparation`. Keep both contracts structurally separate from legacy
`RecommendationPreparation`.

Pin the accepted P1 Method Space version, ruleset version, Method Space digest, and
clarification-registry digest in the handoff oracle. A live catalog with the same
capability IDs but changed semantics is not accepted merely because a new passport
matches it; catalog evolution must update and revalidate this table explicitly. Recheck
that every mapped variable is present in the current request inventory and that the
StudySpec fingerprint still equals the current request fingerprint.

- [x] **Step 5: Run exact mapping and step-schema tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_flow_handoff.py tests/test_descriptives_table1_step.py tests/test_frequency_crosstab_step.py tests/test_correlation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: all pass with every Section 12 row accepted and every mutant rejected.

Pre-commit evidence on 2026-07-17: the handoff/passport gate passed 74 tests; the
handoff plus all five current step-schema suites passed 123 tests; the adjacent flow,
coordinator, concurrency, intake, passport, and architecture gate passed 226 tests.
The focused handoff suite passed 45 tests and Ruff passed. All pytest runs disabled the
cache provider. Four added fail-first cases proved that an unavailable variable, a
StudySpec/current-fingerprint mismatch, and `stale`/`failure` preparation artifacts had
previously crossed the standalone contracts; all now fail closed. Ten malformed,
noncanonical, duplicate-key, non-finite, or future-version parameter byte forms are
also rejected.

- [x] **Step 6: Commit**

```powershell
git add -- src/modori/research_flow/handoff.py src/modori/research_flow/contracts.py src/modori/research_flow/__init__.py tests/test_research_flow_handoff.py
git commit -m "feat: bind passports to exact analysis steps"
```

### Task 9: Share non-inferential structural validation with explicit Run

**Files:**

- Create: `src/modori/steps/input_validation.py`
- Modify: `src/modori/steps/descriptives_table1.py`
- Modify: `src/modori/steps/frequency_crosstab.py`
- Modify: `src/modori/steps/correlation.py`
- Modify: `src/modori/steps/statistics.py`
- Modify: `src/modori/research_flow/contracts.py`
- Create: `src/modori/research_flow/preflight.py`
- Modify: `src/modori/research_flow/__init__.py`
- Create: `tests/test_step_input_validation.py`
- Create: `tests/test_research_flow_preflight.py`
- Modify: `tests/test_descriptives_table1_step.py`
- Modify: `tests/test_frequency_crosstab_step.py`
- Modify: `tests/test_correlation_step.py`
- Modify: `tests/test_compare_groups_step.py`
- Modify: `tests/test_paired_comparison_step.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class StepInputIssue:
    code: str
    role: str | None = None
    variable_id: str | None = None


@dataclass(frozen=True)
class PreflightResult:
    disposition: PreflightDisposition
    issues: tuple[StepInputIssue, ...]
    preparation: PassportBoundPreparation | None
    captured_pipeline_version: int

def validate_step_input(
    dataset: Dataset,
    step_type: str,
    canonical_params: Mapping[str, object],
) -> tuple[StepInputIssue, ...]: ...

def preflight_mapped_step(
    mapping: PassportStepMapping,
    dataset: Dataset,
    *,
    captured_pipeline_version: int,
    current_pipeline_version: Callable[[], int],
) -> PreflightResult: ...
```

- [x] **Step 1: Freeze existing Run-boundary behaviour**

Add characterization fixtures for the six exact mappings and their current structural
rejections: missing/duplicate variables, role collisions, storage/measure mismatch,
empty data, missing/invalid numeric values, too few complete pairs, zero variance,
wrong group cardinality, too-small groups, paired label collision, and zero paired-
difference variance. Record closed reason codes in tests while preserving the current
public step errors and valid numerical outputs.

- [x] **Step 2: Write preflight/Run parity failure tests**

For each accepted and rejected fixture, call the shared validator through preflight and
through the explicit step Run boundary. Assert identical structural disposition/reason
code. Add the P1-only semantic condition that Pearson requires SCALE variables while
Spearman accepts the current SCALE/ORDINAL engine set; blocking Pearson must never
produce Spearman.

- [x] **Step 3: Prove preflight cannot perform inference or mutate the pipeline**

Poison scipy/statistical routines, report/chart construction, effect and interval
functions, and pipeline append/replace methods. Preflight may inspect bounded counts,
finite values, unique groups, and variance feasibility only. It must retain no statistic
and return only `prepare_ready`, `prepare_blocked`, `stale`, or `failure`. A pipeline-
version change during validation returns `stale` and discards the result.

For `prepare_ready` or `prepare_blocked`, seal a `PassportBoundPreparation` containing
the mapping fields, exact preflight disposition, experimental/configure-confirm-run
flags, and `preparation_digest` over all normative fields. `stale` and `failure` return
no preparation. Only a ready preparation may enter Task 12 review; a blocked one exists
only as inspectable evidence for the closed blocked projection.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_step_input_validation.py tests/test_research_flow_preflight.py tests/test_descriptives_table1_step.py tests/test_frequency_crosstab_step.py tests/test_correlation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: FAIL because the shared validator and preflight adapter are absent.

- [x] **Step 5: Extract validators before inference**

Move only structural checks into `input_validation.py`. Make each affected step invoke
the same function before inference; do not fork a second approximation for preflight.
Translate typed issues back into the step's existing error surface so unrelated callers
do not change. Keep P1's stricter Pearson measure gate in the preparation preflight,
explicitly layered over the shared engine contract.

- [x] **Step 6: Re-run parity and calculation regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_step_input_validation.py tests/test_research_flow_preflight.py tests/test_descriptives_table1_step.py tests/test_frequency_crosstab_step.py tests/test_correlation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: all pass; established valid calculation outputs remain byte/number equivalent
within their existing assertions.

Pre-commit evidence on 2026-07-17: the exact shared-validation/preflight plus five-step
calculation gate passed 198 tests. The adjacent flow, coordinator, concurrency,
passport, P1 catalog/intake, pipeline, architecture, and Research Memory gate passed
643 tests with 1 declared skip. Ruff check and format check passed for all nine changed
Python files. Every structural rejection fixture has shared-validator, preflight, and
explicit-Run reason-code parity. Fail-first tests additionally exposed and closed a
seal-time pipeline-version race, multi-variable error-message truncation, boolean and
datetime values crossing continuous-variable storage gates, and legacy non-NFC/blank
column IDs losing the existing direct-Run error surface. A fresh base
`modori.research_flow` import was also proved not to load the statistical inference
stack.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/steps/input_validation.py src/modori/steps/descriptives_table1.py src/modori/steps/frequency_crosstab.py src/modori/steps/correlation.py src/modori/steps/statistics.py src/modori/research_flow/contracts.py src/modori/research_flow/preflight.py src/modori/research_flow/__init__.py tests/test_step_input_validation.py tests/test_research_flow_preflight.py tests/test_descriptives_table1_step.py tests/test_frequency_crosstab_step.py tests/test_correlation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py
git commit -m "refactor: share Research OS preflight validation"
```

### Task 10: Project verified decisions into closed CASUAL and PRO views

**Files:**

- Create: `src/modori/ui/research_flow_presenter.py`
- Modify: `src/modori/ui/strings.py`
- Create: `tests/ui/test_research_flow_presenter.py`
- Verify: `tests/ui/test_question_rationale_presenter.py`
- Verify: `tests/test_question_rationale_adversarial.py`

**Interfaces:**

```python
class ResearchUiCommand(str, Enum):
    START = "start"
    CAUSAL_NO = "causal_no"
    CAUSAL_YES = "causal_yes"
    CAUSAL_NOT_SURE = "causal_not_sure"
    CAUSAL_RECORD = "causal_record"
    BACK = "back"
    SELECT_PROFILE = "select_profile"
    SUBMIT_ROLES = "submit_roles"
    ANSWER = "answer"
    ANSWER_NOT_SURE = "answer_not_sure"
    RETRACT = "retract"
    RESUME = "resume"
    REPLAN = "replan"
    CANCEL = "cancel"
    PREPARE = "prepare"


@dataclass(frozen=True)
class ResearchUiAction:
    command: ResearchUiCommand
    label: str
    enabled: bool


@dataclass(frozen=True)
class ResearchOptionView:
    option_id: str
    label: str
    selected: bool
    enabled: bool


@dataclass(frozen=True)
class ResearchCandidateView:
    capability_label: str
    method_label: str
    claim_boundary: str
    role_rows: tuple[tuple[str, str], ...]
    review_status: str
    persistent_boundary: str


@dataclass(frozen=True)
class ResearchFlowView:
    state: ResearchFlowState
    mode: ControllerMode
    language: Language
    title: str
    body: str
    stage_text: str
    badge_text: str
    decision_identity_digest: str
    visible_passport_digest: str
    primary_action: ResearchUiAction | None
    secondary_actions: tuple[ResearchUiAction, ...]
    options: tuple[ResearchOptionView, ...]
    question: QuestionRationaleView | None
    candidate: ResearchCandidateView | None
    evidence_rows: tuple[tuple[str, str], ...]


def present_durable_record(
    record: DurableFlowRecord,
    *,
    mode: ControllerMode,
    language: Language,
    preflight: PreflightResult | None,
    variable_labels: Mapping[str, str] | None = None,
) -> ResearchFlowView: ...

def present_static_boundary(
    boundary: StaticBoundary,
    *,
    mode: ControllerMode,
    language: Language,
) -> ResearchFlowView: ...
```

Use the repository's existing identities: `ControllerMode.GUIDED` is CASUAL MODE and
`ControllerMode.STANDARD` is PRO MODE. Do not add `"casual"` or `"pro"` runtime values.

- [x] **Step 1: Write provenance and mode-invariance tests**

CASUAL and PRO must carry the same internal `decision_identity_digest`, disposition,
capability, roles, and next command. CASUAL leaves `visible_passport_digest` blank; PRO
shows only the approved abbreviation. CASUAL hides evidence detail; PRO adds closed method/role/
claim-boundary/evidence fields but cannot change the action. Questions must come only
from the committed `QuestionCopy` through `project_current_question_rationale()` and
the existing `QuestionRationalePresenter`. Poison planner search and legacy
`recommendationReason`; neither may be called or copied.

- [x] **Step 2: Write the closed bilingual state catalog tests**

Cover available question, ready candidate, static causal notice, causal recorded
abstention, scope boundary, intake block, preflight block, recovery pending, retracted,
memory unavailable, failure, corruption, stale/replan, cancellation, and busy stages.
Require Korean and English
catalog entries, forbid free-form fallback, and distinguish unavailable from failure,
corruption, stale, and unsupported. `RouteReady` must be rejected rather than rendered.

- [x] **Step 3: Freeze experimental and no-auto-run vocabulary**

Every candidate view must contain the semantic identities for `실험적 후보`, `검토
상태`, `검증 중인 분석 후보 · 자동 실행 안 함`, and `구성 검토로 이동`. Forbid
“best,” “correct,” “expert,” confidence/trust percentages, recommendation validity,
assumption satisfaction, or causal-effect language. A preflight block says no analysis
ran and cannot rename a different method as a candidate.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_presenter.py tests/ui/test_question_rationale_presenter.py tests/test_question_rationale_adversarial.py -q -p no:cacheprovider
```

Expected: FAIL because the composed Research OS presenter is absent.

- [x] **Step 5: Implement immutable presentation models and catalogs**

Keep raw passports, mutable requests, SQLite handles, datasets, and paths out of the
view. Ordinary CASUAL views omit full fingerprints and raw variable IDs; labels are
resolved locally by the controller only for the current screen. Static boundary views
are explicitly non-authoritative and cannot masquerade as a committed decision.

`variable_labels` is therefore an optional presenter input, not durable authority. It
is required only when PRO renders role rows; missing, blank, non-NFC, or raw-ID-equal
labels are rejected instead of falling back to a variable ID. CASUAL never consumes
the mapping.

- [x] **Step 6: Run focused projection and integrity tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_presenter.py tests/ui/test_question_rationale_presenter.py tests/test_question_rationale_projection.py tests/test_question_rationale_adversarial.py tests/test_experimental_recommendation_boundary.py -q -p no:cacheprovider
```

Expected: all pass with identical action authority across modes.

Evidence on 2026-07-17: the requested focused projection/integrity command passed
`150 passed`; the presenter-only contract passed `66 passed`; Ruff check passed and
Ruff format reported all three changed Python files already formatted. The full UI
regression passed `628 passed` when run with permission to create `.test-tmp`; the
sandboxed attempt was invalidated by test-fixture write denials. The initial RED failed
because `modori.ui.research_flow_presenter` did not exist.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/ui/research_flow_presenter.py src/modori/ui/strings.py tests/ui/test_research_flow_presenter.py docs/superpowers/plans/2026-07-17-live-multi-round-research-os-ui.md
git commit -m "feat: project verified Research OS decisions"
```

### Task 11: Add one asynchronous ResearchFlowController boundary

**Files:**

- Create: `src/modori/ui/research_flow_controller.py`
- Modify: `src/modori/research_memory/task_index.py`
- Modify: `src/modori/research_flow/task_session.py`
- Modify: `src/modori/research_flow/coordinator.py`
- Modify: `src/modori/ui/controller_services.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `tests/test_research_task_index.py`
- Modify: `tests/test_research_flow_task_session.py`
- Modify: `tests/test_research_flow_coordinator.py`
- Modify: `tests/ui/test_controller_services.py`
- Modify: `tests/ui/test_controller.py`
- Create: `tests/ui/test_research_flow_controller.py`
- Modify: `tests/ui/test_architecture_guards.py`
- Modify: `tests/ui/test_security_privacy.py`

**Interface:**

`UiController` exposes one `researchFlow` QObject. That object owns one closed
`stateModel`, `busy`, and typed commands for start, causal choice/record/back, profile,
roles, answer, retract, replan, cancel, Prepare, and mode change. It does not expose
stores, passports, requests, datasets, arbitrary paths, or a generic execute method.

- [x] **Step 1: Write lifecycle and main-thread failure tests**

Using a controllable fake worker, assert each command acknowledges and enters the
correct busy/static state without doing fingerprint, filesystem, SQLite, resolver,
audit, handoff, or preflight work on the calling thread. Capture the pipeline version
at submission; discard every late result after pipeline/version change. Cancellation
before commit leaves no authoritative state; cancellation after commit recovers the
last verified decision and never auto-retries.

On startup/reopen, read-only recovery publishes a verified current decision, a closed
retracted state, or recovery-pending without a question/candidate. Only the explicit
Resume command schedules `resume_pending()`; it is single-shot and cannot revive a
retracted passport.

- [x] **Step 2: Prove the causal notice and out-of-scope boundary perform no write**

Poison all task-index, ledger-path, directory, SQLite, and append entry points. Selecting
causal `Yes`, `돌아가기`, causal `Not sure`, or “none of these tasks” must not touch any
of them. Only `이 제한을 기록하고 계속` may schedule the minimal causal request and
later publish its passport-backed abstention.

- [x] **Step 3: Write drift, error taxonomy, and direct-analysis continuity tests**

Before answer, Prepare, Confirm handoff, and Run handoff, change the pipeline version or
dataset fingerprint and require `replan_required`. Exercise unavailable, failure,
corruption, unsupported, and cancelled results without collapsing them. In every state,
existing direct-analysis commands remain usable. No zero-route result can expose a route
command.

- [x] **Step 4: Write facade, dependency, and privacy budget tests**

Require one composed QObject, no second large mixin, and the existing `UiController`
limits of 560 class lines, 60 methods, and 45 lines in its longest method. Assert no
network/subprocess/dynamic loader import and no path, filename, raw value, free text,
URL, or command reaches task/index/ledger contracts. Build source-schema identity from
the current import-step source type, selected sheet/layout, canonical source columns,
and order, never from a path.

- [x] **Step 5: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_controller.py tests/ui/test_controller_services.py tests/ui/test_controller.py tests/ui/test_architecture_guards.py tests/ui/test_security_privacy.py -q -p no:cacheprovider
```

Expected: FAIL because the QObject and composition do not exist.

- [x] **Step 6: Implement by composing the serialized worker**

Reuse `SerializedEngineWorker`; do not add a thread pool or parallel ledger writers.
Run fingerprinting, ledger operations, resolver/planner, passport audit, handoff, and
preflight in serialized jobs. Publish only `ResearchFlowView` values. Cache fingerprint
only under exact `(pipeline_version, fingerprint_contract_id)` and discard a cache entry
on any self-authored or external pipeline change.

- [x] **Step 7: Run controller and existing UI regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_controller.py tests/ui/test_controller_services.py tests/ui/test_controller.py tests/ui/test_architecture_guards.py tests/ui/test_error_stale_state_ui.py tests/ui/test_security_privacy.py -q -p no:cacheprovider
```

Expected: all pass; measured fake-worker command acknowledgement remains below the
test's 100 ms bound without using a relaxed target-machine claim.

Evidence on 2026-07-17: the initial RED failed because the controller module did not
exist. Two later hardening RED tests also failed as intended before the mode-pair
question-authority check and immutable cross-thread label snapshot were added. The
controller file passed `22` tests; the focused controller/service/facade/architecture/
stale/privacy suite passed `89`; the complete UI suite passed `654`; and the ledger,
task-session, coordinator, concurrency, fingerprint, handoff, preflight, presenter,
and controller regression set passed `368`. The subprocess import-isolation test in
that last set was run with this worktree's `src` exported explicitly to child Python
processes; without it the child could not import this uninstalled worktree, so that
attempt was invalid rather than a product failure. Ruff check and format passed, and
`git diff --check` reported no whitespace errors.

Direct audit found and fixed two defects before this checkpoint: pending durable
records initially bypassed source-schema drift rejection, and default runtime
construction initially loaded resolver catalogs on the UI thread. Common durable
drift validation now covers decision, pending, and retraction records, while the
coordinator is constructed lazily inside the serialized worker. `UiController` remains
within its frozen facade budget at `548` class lines, `54` methods, and a longest method
of `44` lines. This evidence establishes a responsive, authority-preserving UI
boundary; it does not establish recommendation validity and it does not add automatic
analysis execution.

- [x] **Step 8: Commit**

```powershell
git add -- src/modori/ui/research_flow_controller.py src/modori/ui/controller_services.py src/modori/ui/controller.py tests/ui/test_research_flow_controller.py tests/ui/test_controller_services.py tests/ui/test_controller.py tests/ui/test_architecture_guards.py tests/ui/test_security_privacy.py
git commit -m "feat: expose asynchronous Research OS flow"
```

### Task 12: Implement exact Prepare, Confirm, and separate Run

**Files:**

- Create: `src/modori/ui/research_preparation_editor.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/ui/session.py`
- Modify: `src/modori/ui/research_flow_controller.py`
- Create: `tests/ui/test_research_preparation_editor.py`
- Modify: `tests/ui/test_pipeline_ops.py`
- Modify: `tests/ui/test_session.py`
- Modify: `tests/ui/test_research_flow_controller.py`
- Modify: `tests/ui/test_experimental_recommendation_flow.py`

Implementation review also required a narrow correction to
`research_flow/contracts.py`, `handoff.py`, and `preflight.py` so the preparation
retains the verified source `mapping_digest`, plus the existing report contracts and
tests so Research OS provenance remains distinct and is rendered exactly once. The
preparation digest contract advances to in-memory schema version 2; no persisted or
exported artifact requires migration.

**Interfaces:**

```python
@dataclass(frozen=True)
class PreparationReview:
    preparation: PassportBoundPreparation
    captured_pipeline_version: int
    settings_rows: tuple[tuple[str, str], ...]


class ResearchPreparationEditor:
    def review(
        self,
        preparation: PassportBoundPreparation,
        *,
        pipeline_version: int,
    ) -> PreparationReview: ...

    def confirm(
        self,
        review: PreparationReview,
        *,
        pipeline_version: int,
    ) -> CommandResult: ...
```

- [x] **Step 1: Write the no-mutation Prepare test**

Selecting a Research OS candidate and invoking Prepare must only open a review model of
the exact mapped settings. Assert unchanged steps, results, selection, pipeline version,
and run tracker. The review contains the passport/preparation digest, experimental and
no-auto-run boundary, exact roles/method/policy, and no editable method substitution.

- [x] **Step 2: Write exact Confirm tests for all six capabilities**

Confirm adds exactly one mapped step using existing pipeline operations and increments
the pipeline version once. Add the missing exact paired-comparison construction/result
binding in `pipeline_ops.py`; do not change the engine schema. Assert Pearson/Spearman,
`always_welch`, `classic`, language, and before/after identity byte-for-byte. Record
Research OS-assisted provenance separately from legacy recommendation provenance.

- [x] **Step 3: Write confirmation invalidation and separate-Run tests**

Mode change, role/method/param edit, fingerprint change, pipeline mutation, stale
passport, retraction, or changed preparation digest invalidates pending confirmation.
Confirm must recheck binding and preflight. It never submits an engine job. Only the
existing later explicit Run command executes the configured step. A manual edit after
Confirm remains a normal user-authored pipeline change and cannot retain the original
passport-bound claim.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_preparation_editor.py tests/ui/test_pipeline_ops.py tests/ui/test_session.py tests/ui/test_research_flow_controller.py tests/ui/test_experimental_recommendation_flow.py -q -p no:cacheprovider
```

Expected: FAIL because the exact Research OS editor and paired pipeline operation are
absent.

- [x] **Step 5: Implement exact review and confirmation**

Delegate pipeline construction to typed operations; never accept a QML-provided raw
step mapping as authority. Store only the provenance identities needed to invalidate
the review and render status. Preserve current direct/manual and legacy Prepare flows as
separate types and commands.

- [x] **Step 6: Run preparation, pipeline, and statistics regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_preparation_editor.py tests/ui/test_pipeline_ops.py tests/ui/test_session.py tests/ui/test_research_flow_controller.py tests/ui/test_experimental_recommendation_flow.py tests/test_correlation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py -q -p no:cacheprovider
```

Expected: all pass; no test observes analysis execution during Prepare or Confirm.

Fail-first evidence included the absent editor and production wiring; a missing paired
operation; four self-resealed method/routing/order mutants; a host-commit callback
failure; review-time version/fingerprint/preflight drift; retraction; a missing atomic
host-commit requirement; confirmed state reverting to a candidate on mode change; and
duplicate Research OS disclosure paragraphs. The preparation-only digest initially
could not distinguish a before/after swap after resealing. The corrected version-2
preparation binds the source mapping digest, and the sole handoff oracle rechecks that
continuity and the closed six-row parameter contract at review, confirmation, and the
pipeline operation boundary.

Final evidence on 2026-07-17, using the worktree-local pinned `.venv` and disabling the
pytest cache provider:

- Task 12 functional/statistical/report/architecture/security cohort: `210 passed`;
- complete UI cohort: `680 passed`;
- complete repository cohort: `3001 passed, 13 skipped`;
- changed and new Python files: Ruff format and check passed; and
- `git diff --check` and the complete direct-file-operation audit passed.

An earlier whole-suite diagnostic used the system Python and correctly failed three
PyInstaller and one NumPy version gate; those results were not treated as product
failures or as final evidence. The same run exposed a real pre-existing omission of
`research_memory/task_index.py` from the central file-operation audit. Its fixed
`%LOCALAPPDATA%\Modori\research-task-index.sqlite3` parent-creation boundary is now
listed and documented without weakening the audit set.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/ui/research_preparation_editor.py src/modori/ui/pipeline_ops.py src/modori/ui/session.py src/modori/ui/research_flow_controller.py tests/ui/test_research_preparation_editor.py tests/ui/test_pipeline_ops.py tests/ui/test_session.py tests/ui/test_research_flow_controller.py tests/ui/test_experimental_recommendation_flow.py
git commit -m "feat: confirm passport-bound analysis preparation"
```

### Task 13: Land the functional QML surface without blending provenance

**Files:**

- Create: `src/modori/ui/qml/components/ResearchFlowPanel.qml`
- Create: `src/modori/ui/qml/components/ResearchQuestionCard.qml`
- Create: `src/modori/ui/qml/components/ResearchCandidateCard.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/strings.py`
- Create: `tests/ui/test_research_flow_qml.py`
- Modify: `tests/ui/test_qml_resources.py`
- Modify: `tests/ui/test_qml_string_catalog.py`
- Modify: `tests/ui/test_qml_runtime_load.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_human_operated_qml_flow.py`

- [x] **Step 1: Write the production-component state tests**

Instantiate the real components against closed synthetic `stateModel` values for:
transformation-first notice, fingerprint busy, causal question, causal static notice,
profile cards, ordered role selection, committed clarify with rationale, not-sure,
candidate ready, preparation blocked, recorded abstention, memory unavailable, failure,
corruption, recovery pending, retracted, stale/replan, cancellation, and successful
preparation review. Assert the
visible and absent regions and that `RouteReady` has no render/action path.

- [x] **Step 2: Write layout, mode, provenance, and accessibility tests**

Require one question per screen, keyboard order, visible focus, accessible names,
screen-reader roles/status announcements, long Korean/English wrapping, 200% scale,
minimum-window scrolling, reduced-effects behaviour, and default/hover/focus/disabled/
pressed controls. CASUAL embeds the flow in the guide rail. PRO opens the same flow from
an explicit header action into the left rail; direct analysis stays reachable. The
legacy quick-candidate area is collapsed, separately labelled, retains its experimental
wording, and never shares selection, rationale, or preparation with Research OS.

- [x] **Step 3: Write Prepare/Confirm/Run interaction tests**

Drive QML signals through the real controller. Prepare opens the exact review without
pipeline mutation; Confirm configures once; Run remains a separate enabled action only
after configuration. Mode switch and drift invalidate the pending review visibly. The
static causal notice's back action causes no write; its explicit record action alone
enters busy/commit state.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_qml.py tests/ui/test_qml_resources.py tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py tests/ui/test_human_operated_qml_flow.py -q -p no:cacheprovider
```

Expected: FAIL because the new QML components are absent.

- [x] **Step 5: Implement the smallest state-complete surface**

Bind only to `uiController.researchFlow` and closed string identities. Reuse current
theme roles and existing accessible controls; add a semantic theme role only when no
existing role expresses the state. Do not embed a planner, raw passport mapping,
fingerprint, store, arbitrary path, or generic method selector in QML.

- [x] **Step 6: Run QML and human-operated regression tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_qml.py tests/ui/test_qml_resources.py tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py tests/ui/test_human_operated_qml_flow.py tests/ui/test_smoke_qml.py tests/ui/test_cream_nacre_visual_system.py -q -p no:cacheprovider
```

Expected: all pass in offscreen runtime mode.

Fail-first evidence was `29 failed, 50 passed`: all new production components,
closed strings, mode integration, and state render paths were absent. The first green
pass exposed and corrected a missing explicit QML delegate index. The complete UI
cohort then found four real compatibility regressions: the intended fifth compact
header command was not reflected in the visual contract, and two reused legacy string
identities caused source-level provenance sections to overlap. The corrected surface
uses distinct Research OS, legacy quick-candidate, and direct-manual identities.

Final evidence on 2026-07-17, using the worktree-local pinned `.venv` and disabling the
pytest cache provider:

- production Research OS QML state and real-controller interaction tests: `33 passed`;
- planned QML, string, runtime, human-operated, smoke, and Aurora cohort: `96 passed`;
- complete UI cohort: `716 passed`;
- all nineteen synthetic closed states loaded without significant QML runtime warnings;
- Ruff format/check passed for the new Python test; and
- `git diff --check` passed.

The real-controller QML tests prove that static causal Back schedules no write while
explicit Record schedules one commit; paired roles preserve before/after order;
closed and variable clarification answers cannot invent an option; Prepare makes no
pipeline change; Confirm configures exactly once; and no QML Research OS component can
invoke Run. Qt lint also exposed an initially shadowed `QQuickItem.state` property; it
was renamed `flowState` before the final regression run.

- [x] **Step 7: Commit**

```powershell
git add -- src/modori/ui/qml/components/ResearchFlowPanel.qml src/modori/ui/qml/components/ResearchQuestionCard.qml src/modori/ui/qml/components/ResearchCandidateCard.qml src/modori/ui/qml/components/GuideRail.qml src/modori/ui/qml/screens/WorkScreen.qml src/modori/ui/strings.py tests/ui/test_research_flow_qml.py tests/ui/test_qml_resources.py tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py tests/ui/test_qml_visual_contract.py tests/ui/test_human_operated_qml_flow.py
git commit -m "feat: add live Research OS QML flow"
```

### Task 14: Apply the dual-key visual finish with synthetic evidence only

**Files:**

- Create: `tests/fixtures/research_flow_visual_states.json`
- Create: `scripts/capture_research_flow_gallery.py`
- Create: `scripts/build_research_flow_visual_review_packet.py`
- Create: `tests/ui/test_research_flow_visual_gallery.py`
- Modify: `tests/ui/test_qml_visual_contract.py`
- Modify: `tests/ui/test_cream_nacre_visual_system.py`
- Modify as defect evidence requires: `src/modori/ui/qml/components/AppButton.qml`
- Modify as accepted: the three new Research OS QML components and existing semantic theme roles only

- [x] **Step 1: Freeze the gallery manifest before the first capture**

Freeze a `1024 x 640` minimum logical viewport, the existing
`1180 x 760` reference viewport, Korean and English, scale factors `1.0`, `1.25`, `1.5`,
and `2.0`, reduced-effects on and off, and the pre-change render/interaction baseline.
The checked-in state manifest requires capture from a clean commit but does not embed a
self-referential commit hash; the generated gallery manifest records the exact current
HEAD for every item. Include the applicable twelve canonical states from the
visual-finish design plus P1 causal notice, candidate,
preflight block, recovery pending, retracted, stale/replan, recorded abstention,
collapsed/expanded disclosure, and
the default/hover/keyboard-focus/disabled/pressed interaction strip. Do not reinterpret
these values after seeing a defect.

- [x] **Step 2: Write capture, privacy, and production-exclusion failure tests**

The gallery must instantiate the production QML component/property contract with
synthetic fixtures. Each item records state ID, locale, mode, interaction state,
viewport, scale, reduced-effects, fixture ID, source commit, and expected present/absent
regions. Captures are cropped to application content, strip metadata, and are scanned
for usernames, paths, filenames, project/ledger IDs, recent items, free text, and raw
data. Fixture injection, capture scripts, and review assets must be absent from the
production package.

- [x] **Step 3: Add deterministic contrast and geometry gates**

Extend the checked-in foreground/background pair manifest for every new text, control,
focus, state, and meaningful graphic. Calculate exact sRGB/alpha-composited ratios from
theme tokens, rejecting unrounded `4.499:1` and `2.999:1` boundaries. Test geometry,
clipping, focus order, accessible names, long copy, minimum viewport, all scale factors,
and reduced effects from source/runtime state, never by sampling screenshot colours.

- [x] **Step 4: Run the tests and confirm failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_visual_gallery.py tests/ui/test_qml_visual_contract.py tests/ui/test_cream_nacre_visual_system.py tests/test_package_public_data_smoke_script.py -q -p no:cacheprovider
```

Expected: FAIL because the P1 gallery manifest and capture harness are absent.

- [x] **Step 5: Implement the harness and owner-side first visual pass**

Implement the production-component capture harness and make the first bounded owner
pass over hierarchy, rhythm, wrapping, alignment, state distinction, and interaction
affordance without changing closed copy, state meaning, provenance, or authority. Run
the Step 4 cohort to green and review `git diff --check`, then:

```powershell
git add -- docs/superpowers/plans/2026-07-17-live-multi-round-research-os-ui.md tests/fixtures/research_flow_visual_states.json scripts/capture_research_flow_gallery.py scripts/build_research_flow_visual_review_packet.py tests/ui/test_research_flow_visual_gallery.py tests/ui/test_qml_visual_contract.py tests/ui/test_cream_nacre_visual_system.py src/modori/ui/qml/components/AppButton.qml src/modori/ui/qml/components/ResearchFlowPanel.qml src/modori/ui/qml/theme/Theme.qml
git commit -m "test: add Research OS visual gallery"
```

An unchanged listed path contributes nothing to the commit; no path outside this
reviewed set is staged.

Fail-first evidence included an absent gallery/capture contract and, after the first
native Windows owner capture, four targeted failures for three observed defects: long
status badges could squeeze the `Research OS` heading out of view; the Mode A contact
sheet used an offscreen Qt platform with zero font families; and a primary button's
focus ring reused its own fill colour. The bounded fixes use a responsive header grid,
native-font fail-closed packet rendering in an isolated process, and an on-brand inner
focus ring with a separately declared exact contrast pair. They do not change closed
copy, state meaning, provenance, or authority.

First-pass evidence on 2026-07-18, using synthetic fixtures and the worktree-local
pinned `.venv`:

- all 29 native Windows captures were inspected individually;
- every generated item used one source commit, a production Windows renderer, and a
  non-empty 387-family font database, with zero expected-region, property, or horizontal
  overflow mismatches;
- the targeted defect gate moved from `4 failed` to `4 passed`;
- the Task 14 focused Research OS/QML/human-operated cohort passed `94` tests;
- the complete UI cohort passed `727` tests;
- the package-exclusion cohort passed `12` tests; and
- Ruff check and `git diff --check` passed for the changed Python and repository diff.

The first clean committed capture exposed a comparability gap before Step 6 could be
accepted: `render_ms` included test-process/QML construction and therefore was not the
pre-change product-response measure named by the frozen 250 ms/200 ms gates. The
thresholds were not changed. The harness now records `state_render_ms` from scene show
to stable state and `interaction_response_ms` from input to stable response, while
retaining total capture time as diagnostic evidence. The generated-gallery test applies
nearest-rank p95 directly to those two fields. Full `WorkScreen` construction remains a
separate cold shell diagnostic and is never averaged with component or interaction
response. Final committed capture evidence is recorded only after Step 6.

- [x] **Step 6: Capture the committed first pass**

Require a clean worktree, then generate `.visual-qa/research-flow/` from the exact
manifest. Verify every image and generated item manifest names the current HEAD. Inspect
at native size and side by side; if an owner defect is fixed, commit it and regenerate
the complete gallery before building any review packet.

The clean first-pass recapture at `f4d35cdce705a0fa447a9b2a3dfb3d987cbb939a`
produced 29 native Windows items and a digest-bound Mode A packet. Every item named that
one commit, used `production-windows` with 387 available font families, and reported
zero missing regions, unexpected regions, property mismatches, horizontal overflow,
title clipping, OS chrome, or non-production component substitutions. All 29 images
and the readable contact sheet were inspected. Nearest-rank p95 was `242.801 ms` for
state stabilization against the frozen `250 ms` gate and `31.517 ms` for interaction
response against the frozen `200 ms` gate. Total test-process/QML construction time
remains diagnostic only and was not substituted for either response measure.

- [x] **Step 7: Run bounded advisory review**

Build a Mode A packet containing only sanitized synthetic images, a one-page visual
brief, immutable/forbidden change lists, and viewport/scaling constraints. A fresh
session may propose measured/annotated changes but receives no source or product data.
If a source-aware Mode B audit is warranted, provide only a separate read-only,
manifested, digest-bound subset of components, theme tokens, contrast declarations, and
tests. Classify each finding `accept`, `adapt`, or `reject`; reproduce technical claims
locally. No reviewer writes this worktree. External review unavailability does not
block the owner-side gallery/rubric.

The sanitized Mode A packet was built with the native Windows font database and
reviewed owner-side without disclosing source or user data. No fresh external visual
reviewer was available, which is explicitly non-blocking. The warranted source-aware
technical audit stayed local and read-only in scope: exact theme-token contrast,
header geometry, focus treatment, privacy fields, platform fidelity, and package
exclusion were verified by deterministic tests and the rendered evidence. No advisory
finding was accepted without a local reproduction.

- [x] **Step 8: Apply only accepted findings and re-run focused gates**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/test_research_flow_visual_gallery.py tests/ui/test_research_flow_qml.py tests/ui/test_qml_visual_contract.py tests/ui/test_cream_nacre_visual_system.py tests/ui/test_qml_runtime_load.py tests/ui/test_human_operated_qml_flow.py -q -p no:cacheprovider
```

Expected: all pass. At this point the rendered images are provisional if accepted code
changes are still uncommitted.

The first post-capture cohort exposed one measurement-test defect: a six-item shortcut
used nearest-rank p95, which equals the maximum for that sample size and therefore
passed or failed on a single scheduler outlier. The frozen `250 ms` threshold was not
changed. The regression fixture now renders all 29 frozen states, matching the evidence
population on which p95 is defined. The full-matrix performance test passed in
`38.56 s`, and the complete Step 8 cohort then passed `94` tests in `64.68 s`.

- [x] **Step 9: Commit accepted polish, if any**

```powershell
git add -- src/modori/ui/qml/components/ResearchFlowPanel.qml src/modori/ui/qml/components/ResearchQuestionCard.qml src/modori/ui/qml/components/ResearchCandidateCard.qml src/modori/ui/qml/theme/Theme.qml tests/ui/test_research_flow_visual_gallery.py tests/ui/test_qml_visual_contract.py tests/ui/test_cream_nacre_visual_system.py
git commit -m "style: finish live Research OS surface"
```

Skip this commit when no finding was accepted. In either case, stage only actually
changed paths; omit `Theme.qml` or any test/component absent from the reviewed diff.

Accepted visual and evidence changes were committed in bounded slices:
`df462e4` adds the 29-state native gallery and the reproduced visual fixes, while
`f4d35cd` separates response gates from diagnostic capture construction. The final
full-population p95 regression correction and this execution record form a test/docs
follow-up only; they do not change product copy, state meaning, provenance, authority,
or any recommendation rule.

- [x] **Step 10: Recapture and verify the final committed gallery**

Require a clean worktree, regenerate every state, and rerun the Step 8 cohort. Every
final item must identify the one current HEAD, privacy scan must pass, and no rendered
or packet artifact is staged. A polished pre-commit screenshot is not final evidence.

At committed HEAD `6b8188380c04c456bc1485851596a47d88ea0aed`, the clean
recapture and packet both named that exact commit for all 29 items. Every item used the
native Windows renderer and production component contract with 387 font families;
all structural, privacy, clipping, overflow, and substitution counters were zero.
Nearest-rank p95 was `222.688 ms` for state stabilization (maximum `237.448 ms`) and
`31.533 ms` for interaction response, both inside the unchanged gates. The contact
sheet and all 29 current-run images were inspected, and the Step 8 cohort passed
`94` tests in `61.93 s`. Generated `.visual-qa` evidence remained ignored and unstaged.

### Task 15: Close local security, packaging, and full-regression gates

**Files:**

- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `tests/test_package_public_data_smoke_script.py`
- Modify: `tests/test_package_windows_script.py`
- Modify: `tests/test_quality_gate_script.py`
- Do not yet create: `docs/qa/live-research-os-p1-evidence.md`

- [ ] **Step 1: Add the exact file-operation and package failure tests**

Permit only the fixed application-owned ResearchTaskIndex operation and the already
approved per-task ledger derivation. Reject an arbitrary caller path, directory-wide
allowlist, symlink/junction/reparse point, remote drive, import, delete, bundle, dynamic
loader, or network operation. Assert the packaged application includes the new runtime
modules and QML but excludes gallery fixtures/scripts, review packets, ledger contents,
user data, and `.visual-qa`.

- [ ] **Step 2: Run the tests and confirm the audit is incomplete**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_file_operation_audit.py tests/test_package_public_data_smoke_script.py tests/test_package_windows_script.py tests/test_quality_gate_script.py -q -p no:cacheprovider
```

Expected: FAIL until the exact operation and package inventory are documented and
handled.

- [ ] **Step 3: Update only the narrow audit and package contracts**

Document the operation, fixed root, input provenance, path proof, reparse/remote checks,
concurrency, failure mode, and retained lifecycle limitation. Do not add task deletion
or claim secure erasure. Update package discovery only as required for the runtime QML
and Python modules; do not weaken package-content assertions.

- [ ] **Step 4: Run focused security and package checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_file_operation_audit.py tests/ui/test_security_privacy.py tests/test_package_public_data_smoke_script.py tests/test_package_windows_script.py tests/test_quality_gate_script.py -q -p no:cacheprovider
```

Expected: all pass.

- [ ] **Step 5: Commit the exact audit/package delta**

```powershell
git add -- docs/security/file-operations-audit-2026-06-29.md tests/test_file_operation_audit.py tests/test_package_public_data_smoke_script.py tests/test_package_windows_script.py tests/test_quality_gate_script.py
git commit -m "test: audit live Research OS file operations"
```

Stage only files actually changed by this task.

- [ ] **Step 6: Run frozen-inventory and adversarial gates at committed HEAD**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_research_os_p1_catalog.py tests/test_research_flow_coordinator.py tests/test_research_flow_concurrency.py tests/test_research_flow_handoff.py tests/test_research_flow_preflight.py tests/test_research_memory_crash_recovery.py tests/test_research_memory_ledger_store.py tests/test_research_memory_passport_state.py tests/ui/test_research_flow_controller.py tests/ui/test_research_flow_qml.py tests/ui/test_research_flow_visual_gallery.py -q -p no:cacheprovider
```

Expected: all pass with exact 6/67/15/0 inventory, no active-passport race, every poison
point recovered, all mapping mutants killed, and no route state.

- [ ] **Step 7: Run the complete local quality and packaged-launch gate**

Do not spend GitHub Actions quota. Run locally:

```powershell
.\.venv\Scripts\python.exe scripts/quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
```

Expected: compile/import, Ruff, Bandit, launch smoke, complete pytest, dependency check,
package check/build, packaged launch/engine/public-data smokes, and slow statistical gate
all exit zero. Explain every skip, warning, resource increase, and package-content delta;
do not dismiss or hide one.

- [ ] **Step 8: Review the complete diff and stop at the local-evidence boundary**

Require a clean worktree, record the exact HEAD and local command outputs outside the
product package, and compare every design stop condition. If an authority, mapping,
preflight, security, accessibility, packaging, or full-suite gate remains red after one
focused evidence-backed repair, disable the live Research OS surface rather than relax
the contract. Do not create the P1 evidence document or claim completion yet: the
separate target-HP plan below is mandatory.

---

## Deferred lifecycle decision (not hidden in P1)

Whole-task versus delete-all retention controls remain unimplemented. Their future
design must coordinate the index row, ledger database, WAL/SHM files, closed handles,
application-owned path proof, concurrent readers, crash recovery, and the explicit
nonclaim of forensic secure erasure. `decision_retracted` is not deletion. Until that
slice is approved and implemented, product copy and release evidence must say that
task-history destruction is unavailable.

## Execution and handoff

Execute this plan inline with `superpowers:executing-plans`; the owner has forbidden
subagents. After each task, inspect `git diff --check`, the exact staged diff, focused
test output, and repository status before committing. Never use `git add -A`.

Only after Task 15 passes at a clean committed HEAD, execute
`docs/superpowers/plans/2026-07-17-live-research-os-office-benchmark.md`. A product-plan
failure stops the sequence; it cannot be averaged away by a benchmark result.
