# Live Research OS Office Benchmark Legacy-Path Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Subagents are forbidden for this repository task.

**Goal:** Replace the revoked `0cae87d` HP candidate with a source-pinned office kit that works under the target's legacy Win32 path boundary, reports the exact failing phase, and passes every unchanged local, adversarial, package, and performance gate before another HP run.

**Architecture:** Keep result publication below the verified kit, but derive all synthetic Decision Ledger work below the short application-owned sibling `<extraction-parent>/w`. Compute the complete frozen dynamic-path inventory in UTF-16 units before any child starts, shorten failed-run quarantine without weakening its marker binding, and carry only closed stage codes across child/process/bootstrap boundaries. Remove the obsolete archive `work` capability and prevent the PowerShell wrapper from publishing a second generic diagnostic after a typed runner diagnostic.

**Tech Stack:** Python 3.12.10; pathlib; SQLite/WAL; PyInstaller; PowerShell 5.1; canonical JSON/SHA-256; pytest; Ruff; Bandit; the existing 300-case mutation corpus and 20-cold/30-warm release protocol.

## Global Constraints

- Work only in `C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration` on `codex/research-os-release-integration`.
- Do not switch, merge, push, delete a worktree, or modify another checkout.
- Use no subagents and do not weaken the 30,000 ms, 100 ms, 20-cold, 30-warm, fixture, integrity, privacy, or package gates.
- Do not change Windows registry/policy, require elevation, add network access, inspect user files, or accept a caller-selected release workspace.
- Dynamic path lengths are UTF-16 code units; the fixed non-null budget is `240`.
- Release results are written only to `<kit-root>/results`; synthetic work is written only to `<kit-root>.parent/w`.
- The archive has exactly one mutable root, `results`; a `work` member or extracted `work` subtree is invalid.
- Diagnostics contain only closed reason codes, never raw paths, usernames, exception text, dataset values, or free text.
- The old `0cae87d` archive remains revoked for target evidence even if its development-PC result passed.
- Build evidence only from a clean committed HEAD; documentation after the build must distinguish kit source commit from later evidence commit.

---

### Task 1: Freeze the short workspace, complete path budget, and stage errors

**Files:**

- Modify: `scripts/run_office_live_research_os_benchmark.py`
- Modify: `scripts/live_research_os_office_benchmark.py`
- Modify: `tests/test_live_research_os_office_benchmark_runner.py`
- Modify: `tests/test_live_research_os_office_benchmark_contract.py`

**Interfaces:**

- Produces: `LEGACY_DYNAMIC_PATH_BUDGET_UNITS: Final[int] = 240`.
- Produces: `release_working_root(kit_root: Path) -> Path`.
- Produces: `release_dynamic_path_budget_units(working_root: Path, *, run_id: str) -> int`.
- Produces: `_ensure_release_dynamic_path_budget(working_root: Path, *, run_id: str) -> None`.
- Produces: `_STAGE_FAILURE_CODES`, the closed union accepted by
  `BenchmarkStageError`.
- Produces: `BenchmarkStageError(reason_code: str)` whose code is preserved by `_closed_failure_code()`.
- Preserves: `run_complete_benchmark()` and `execute_release_benchmark()` public call shapes.

- [ ] **Step 1: Write failing path and workspace tests**

Add tests that construct a target-style root and assert the old projection is over the
budget while the sibling projection is not:

```python
def test_release_workspace_removes_immutable_kit_name_from_dynamic_paths(
    tmp_path: Path,
) -> None:
    parent = Path(r"C:\Users\V\AppData\Local\MBL-0123456789ab")
    kit_root = parent / "modori-live-research-os-office-kit-0123456789ab-py31210"
    old = kit_root / "work"
    short = parent / "w"

    assert release_dynamic_path_budget_units(old, run_id=RUN_ID) > 240
    assert release_dynamic_path_budget_units(short, run_id=RUN_ID) <= 240
```

Add a real temporary-directory test proving `release_working_root(kit_root)` returns
exactly `kit_root.parent / "w"`, a non-BMP component test proving UTF-16 counting, a
long-parent test proving `dynamic_path_budget_exceeded`, an assertion that no child
executor was called, and an updated release-publisher assertion:

```python
assert captured["working_root"] == kit_root.parent / "w"
```

- [ ] **Step 2: Run the focused RED tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py -q -p no:cacheprovider
```

Expected: FAIL because the sibling projection and UTF-16 dynamic budget interfaces do
not exist and the executor still selects `kit_root/work`.

- [ ] **Step 3: Implement the fixed path projection and budget**

Add the fixed constant and UTF-16 helper:

```python
LEGACY_DYNAMIC_PATH_BUDGET_UNITS: Final[int] = 240


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le", errors="strict")) // 2
```

`release_working_root()` must validate the kit root and its exact parent, derive only
`parent / "w"`, reject an existing file/link/reparse/remote/cloud target, and return a
possibly not-yet-created absolute path. The dynamic candidate inventory must derive the
longest generated P1 child ID from `P1TaskProfile`, include active and `q/<nonce>`
quarantine layouts, all markers, task index, Decision Ledger, and `-wal`, `-shm`, and
`-journal` suffixes. `_ensure_release_dynamic_path_budget()` raises this fixed message:

```python
raise BenchmarkStageError("dynamic_path_budget_exceeded")
```

Call it in `run_complete_benchmark()` immediately after the marked root is initialized
and before quarantine, fixture construction, or child launch. Change quarantine from
`quarantine/<run-id>-<nonce>` to `q/<nonce>` while retaining and rechecking the original
run marker inside the moved directory.

- [ ] **Step 4: Write failing stage-diagnostic tests**

Inject failures at child-root validation, fixture construction, identity sampling,
acknowledgement, scenario fingerprinting, and durable scenario execution. Assert the
exact closed codes:

```python
expected = {
    "child_root_failure",
    "fixture_build_failure",
    "identity_sample_failure",
    "acknowledgement_failure",
    "scenario_fingerprint_failure",
    "scenario_execution_failure",
}
assert observed == expected
assert b"C:\\" not in stderr
assert b"Traceback" not in stderr
```

Also assert that a parent receiving `child process failed: scenario_execution_failure`
preserves that exact code, while an unregistered or padded code is rejected.

- [ ] **Step 5: Run the stage RED tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_live_research_os_office_benchmark_runner.py -q -p no:cacheprovider
```

Expected: FAIL because unknown child failures still collapse to
`product_authority_failure`.

- [ ] **Step 6: Implement typed closed-stage propagation**

Add `BenchmarkStageError` and a small wrapper that preserves an existing specific
closed reason before applying its broader stage reason:

```python
class BenchmarkStageError(BenchmarkRunnerError):
    def __init__(self, reason_code: str) -> None:
        if reason_code not in _STAGE_FAILURE_CODES:
            _fail("stage failure reason is not in the closed inventory")
        super().__init__(reason_code)
        self.reason_code = reason_code
```

Extend the runner child inventory and the benchmark contract inventory with the five
new child-stage codes and `dynamic_path_budget_exceeded`. `_closed_failure_code()` must
walk the cause chain for `BenchmarkStageError`, accept the exact
`child process failed: <code>` form only for registered codes, preserve existing
fingerprint/acknowledgement reasons, and otherwise remain fail-closed. Wrap each phase
in `run_child_mode()` without changing its timing boundaries or successful output.

- [ ] **Step 7: Run the focused GREEN tests and static checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py tests/test_research_flow_coordinator.py tests/test_research_memory_crash_recovery.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts/run_office_live_research_os_benchmark.py scripts/live_research_os_office_benchmark.py tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py
.\.venv\Scripts\python.exe -m ruff format --check scripts/run_office_live_research_os_benchmark.py scripts/live_research_os_office_benchmark.py tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py
git diff --check
```

Expected: all tests and static checks pass with no threshold or protocol diff.

- [ ] **Step 8: Commit Task 1**

```powershell
git add -- scripts/run_office_live_research_os_benchmark.py scripts/live_research_os_office_benchmark.py tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py
git commit -m "fix: bound office benchmark dynamic paths"
```

---

### Task 2: Remove obsolete archive work authority and preserve one diagnostic

**Files:**

- Modify: `scripts/build_office_live_research_os_kit.py`
- Modify: `scripts/verify_office_live_research_os_kit.py`
- Modify: `scripts/office_live_research_os_kit/VERIFY-AND-RUN.ps1.in`
- Modify: `scripts/office_live_research_os_kit/README-KO.txt`
- Modify: `tests/test_office_live_research_os_kit_builder.py`
- Modify: `tests/test_office_live_research_os_kit_verifier.py`
- Modify: `tests/test_office_live_research_os_kit_architecture.py`

**Interfaces:**

- Consumes: release work is now `kit_root.parent / "w"`.
- Produces: ZIP/extracted kit mutable inventory `frozenset({"results"})`.
- Produces: runtime identity probes use a verifier-owned `TemporaryDirectory`, never a
  kit `work` directory.
- Produces: PowerShell publishes a wrapper bootstrap file only when the failed runtime
  did not publish exactly one new typed diagnostic.

- [ ] **Step 1: Write failing package-boundary tests**

Change fake kits and builder assertions to require `results/` and forbid `work/`.
Assert both directory and ZIP verification reject an empty or populated `work` subtree.
Update the probe test to require a temporary environment outside the supplied kit:

```python
assert Path(kwargs["env"]["LOCALAPPDATA"]) != root / "work"
assert kwargs["env"]["LOCALAPPDATA"] == kwargs["env"]["TEMP"]
assert kwargs["env"]["TEMP"] == kwargs["env"]["TMP"]
assert not Path(kwargs["env"]["TEMP"]).is_relative_to(root)
```

Add a bootstrap source contract asserting it snapshots pre-run diagnostic names and,
on runtime failure, suppresses only the second file when exactly one new
`bootstrap-error-*.txt` exists.

- [ ] **Step 2: Run the package RED tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_architecture.py -q -p no:cacheprovider
```

Expected: FAIL because the builder/verifier/template still require `work` and the
wrapper always writes `runner_exit_22` as another file.

- [ ] **Step 3: Implement the package and probe boundary**

Build only `results/`, set verifier `_MUTABLE_ROOTS = frozenset({"results"})`, and make
all work members ordinary unexpected inventory. In `probe_runtime_identity()`, create
one verifier-owned local `TemporaryDirectory` around both fixed identity calls and pass
that path to `_probe_environment()`; preserve its no-network/minimal-environment rules.

In PowerShell, collect the set of existing diagnostic filenames immediately before the
`--release` invocation. If the runtime exits nonzero, compute only newly created regular
`bootstrap-error-*.txt` files. Exactly one new file causes a no-write wrapper exit;
zero or more than one causes the existing generic closed wrapper diagnostic. Do not
read or echo raw exception text.

- [ ] **Step 4: Parse PowerShell and run package GREEN tests**

Run:

```powershell
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'scripts/office_live_research_os_kit/VERIFY-AND-RUN.ps1.in'),[ref]$t,[ref]$e) > $null; if($e.Count){$e | Out-String | Write-Error; exit 1}"
.\.venv\Scripts\python.exe -m pytest tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_architecture.py tests/test_office_live_research_os_kit_contract.py tests/test_office_live_research_os_kit_runner.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check scripts/build_office_live_research_os_kit.py scripts/verify_office_live_research_os_kit.py tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_architecture.py
git diff --check
```

Expected: parser, tests, Ruff, and diff check pass.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- scripts/build_office_live_research_os_kit.py scripts/verify_office_live_research_os_kit.py scripts/office_live_research_os_kit/VERIFY-AND-RUN.ps1.in scripts/office_live_research_os_kit/README-KO.txt tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_architecture.py
git commit -m "fix: close office kit legacy work boundary"
```

---

### Task 3: Reconcile operator and file-operation contracts

**Files:**

- Modify: `docs/qa/live-research-os-office-benchmark-runbook.md`
- Modify: `docs/security/file-operations-audit-2026-06-29.md`
- Modify: `tests/test_file_operation_audit.py`
- Modify: `tests/test_office_live_research_os_kit_architecture.py`

**Interfaces:**

- Consumes: exact work root `<extraction-parent>/w`, exact quarantine `w/q`, only
  `results` inside the kit, `dynamic_path_budget_exceeded`, and one diagnostic file per
  failed invocation.
- Produces: nondeveloper instructions naming only files/folders the operator touches.

- [ ] **Step 1: Write failing documentation-contract tests**

Require the runbook to state:

```text
<MBL 폴더>\w
240 UTF-16
dynamic_path_budget_exceeded
results 폴더
한 실행에서 새 오류 문서 하나
```

Require the file-operation audit row to name the exact sibling `w`, `q/<nonce>`, marked
ownership, dynamic preflight, result-only kit mutation, no registry/network/user data,
and exact cleanup boundary. Remove the obsolete `kit's own work` assertion.

- [ ] **Step 2: Run documentation RED tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_file_operation_audit.py tests/test_office_live_research_os_kit_architecture.py -q -p no:cacheprovider
```

Expected: FAIL against the old `kit/work` wording.

- [ ] **Step 3: Update runbook, README, and audit without broad warnings**

Mark the old `0cae87d` identity revoked, remove its transfer/hash instructions, and say
the replacement identity will be inserted only after a clean committed build. Explain
that users still extract to the short `MBL-<commit>` parent; the executable creates the
sibling `w` itself, so the user does not create, copy, inspect, or return it. On failure,
return the one newly created bootstrap file. Do not mention OEM partitions or unrelated
folders except the existing concise non-interference statement.

- [ ] **Step 4: Run documentation GREEN tests and commit**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_file_operation_audit.py tests/test_office_live_research_os_kit_architecture.py -q -p no:cacheprovider
git diff --check
```

Then:

```powershell
git add -- docs/qa/live-research-os-office-benchmark-runbook.md docs/security/file-operations-audit-2026-06-29.md tests/test_file_operation_audit.py tests/test_office_live_research_os_kit_architecture.py
git commit -m "docs: update office benchmark path boundary"
```

---

### Task 4: Rebuild, attack, run, and verify the replacement kit

**Files:**

- Generate, do not commit: `.tmp/live-os-repack-{1,2,3}/live-research-os-office/*`
- Generate, do not commit: `dist/live-research-os-office/*.zip`
- Generate, do not commit: fresh local run outputs below a short ignored `.tmp` or
  `%LOCALAPPDATA%` directory
- Modify after evidence exists: `docs/qa/live-research-os-office-benchmark-runbook.md`
- Modify after evidence exists: `docs/superpowers/plans/2026-07-18-office-benchmark-legacy-path-recovery.md`

**Interfaces:**

- Consumes: clean committed HEAD after Tasks 1-3.
- Produces: one selected ZIP/sidecar, three-repack byte identity, 300 rejected attacks,
  one independently verified full local result, and a complete product quality gate.

- [ ] **Step 1: Run the complete pre-build verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_live_research_os_office_benchmark_runner.py tests/test_live_research_os_office_benchmark_contract.py tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_runner.py tests/test_office_live_research_os_kit_architecture.py tests/test_file_operation_audit.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m bandit -q -r src scripts
git diff --check
git status --short
```

Expected: all commands pass and status is clean. Do not build from dirty source.

- [ ] **Step 2: Build three independent source-pinned kits**

Let `$commit = git rev-parse HEAD`. Build into three ignored parents whose final child
has the required exact name:

```powershell
.\.venv\Scripts\python.exe scripts/build_office_live_research_os_kit.py --source-commit $commit --output-dir .tmp/live-os-repack-1/live-research-os-office
.\.venv\Scripts\python.exe scripts/build_office_live_research_os_kit.py --source-commit $commit --output-dir .tmp/live-os-repack-2/live-research-os-office
.\.venv\Scripts\python.exe scripts/build_office_live_research_os_kit.py --source-commit $commit --output-dir .tmp/live-os-repack-3/live-research-os-office
```

Hash all three ZIPs and require one distinct SHA-256 and byte-identical sidecars. Copy
only repack 1's exact ZIP and sidecar into an otherwise empty
`dist/live-research-os-office`; do not retain the revoked archive there.

- [ ] **Step 3: Independently verify and execute all 300 attacks**

Run the verifier/builder/architecture cohort against the selected archive:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_office_live_research_os_kit_verifier.py tests/test_office_live_research_os_kit_builder.py tests/test_office_live_research_os_kit_architecture.py -q -p no:cacheprovider
```

Expected: the architecture test reports all 300 mutations rejected before runtime,
result creation, or residual synthetic work. Confirm sorted unique members, CRC,
sidecar, manifest, embedded identity, runtime probe, source commit, and absence of a
`work/` member.

- [ ] **Step 4: Run the unchanged full local 20/30 protocol**

Extract the selected ZIP into a fresh short local non-reparse parent and run
`RUN-MODORI-LIVE-RESEARCH-OS-BENCHMARK.cmd`. Do not reduce repetitions or substitute a
direct Python call. Require exactly one of:

```text
valid result JSON + JSON.sha256 + summary-ko.txt
one bootstrap-error file and no result JSON
```

Independently call `verify_kit()` and `verify_returned_result()` from the committed
verifier. Expected for B4 completion: `valid_pass`, exact source/fixture/protocol
identity, all 98 separated rows passing, no closed error code, and synthetic work
containing only its root marker plus permitted empty quarantine state after cleanup.

- [ ] **Step 5: Run the unchanged complete product quality gate**

Run:

```powershell
.\.venv\Scripts\python.exe scripts/quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
```

Expected: exit zero. Record every warning, skip, transient rerun, count, and package
smoke; do not erase or reinterpret a failure.

- [ ] **Step 6: Record B4-R evidence and commit documentation**

Record source commit, ZIP name/size/SHA-256/member count/CRC, three-repack identity,
300-case counts, local result identifiers and separated p95/resource results, quality-
gate counts, warnings, and the revoked old identity. Replace the runbook's pending
artifact block with the exact new ZIP and sidecar only after all evidence is present.

Run documentation tests and `git diff --check`, then:

```powershell
git add -- docs/qa/live-research-os-office-benchmark-runbook.md docs/superpowers/plans/2026-07-18-office-benchmark-legacy-path-recovery.md
git commit -m "docs: record recovered office benchmark evidence"
```

- [ ] **Step 7: Audit the selected artifact after the documentation commit**

Re-hash and independently verify the unchanged selected ZIP/sidecar. Confirm its
embedded source commit is the earlier clean build commit, not the later evidence commit;
confirm `git status --short` is empty. Only then copy the exact pair into a newly named
USB folder and provide the user the exact local extraction and return-file paths.

---

## Self-review

- Spec coverage: short sibling work, shortened quarantine, UTF-16 budget, stage codes,
  duplicate-diagnostic suppression, archive boundary, runbook/audit, three repacks,
  300 attacks, full local run, quality gate, and HP handoff each map to a task.
- Placeholder scan: the plan contains no deferred implementation placeholder; the one
  pending artifact identity is intentionally produced only by Task 4 evidence and is
  not a code requirement.
- Type consistency: the three path interfaces and `BenchmarkStageError.reason_code`
  names are identical in Tasks 1-4.
- Claim discipline: B4-R completion still does not complete B5 or establish statistical
  accuracy, recommendation validity, expert equivalence, or SPSS superiority.

## Execution handoff

Execute inline in this task with `superpowers:executing-plans`; the user has already
approved this recovery and prohibited subagents. Review exact diffs and fresh command
output at every checkpoint. Stop only if an unchanged gate cannot be met without
changing its meaning.
