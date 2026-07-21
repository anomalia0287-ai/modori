# Modori Build Week Submission Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Subagents are prohibited for this release lane.

**Goal:** Close an honest, reproducible, source-only Modori OpenAI Build Week submission candidate by the owner's internal hard deadline of 2026-07-21 KST.

**Architecture:** Preserve the current release work as its own auditable commit, then merge the exact functional-usability candidate while resolving only the two semantic overlaps by hand. Treat repository behavior as the authority for README, Devpost, demo, and verification claims; keep historical B4-R evidence bound to its original kit and record fresh final-source evidence separately.

**Tech Stack:** CPython 3.12.10, PySide6/QML, pytest, Ruff, PyInstaller one-folder packaging, Markdown/SRT/SVG release evidence, Git linked worktree.

## Global Constraints

- Work only in `C:\Users\V\.codex\worktrees\49c6\TongTong` on `codex/modori-build-week-release-p0`.
- Preserve the dirty state observed at `eaa0e802a0c64f6619297432f129be4d198a79ea`; do not reset, discard, or overwrite it.
- Integrate functional candidate `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` without blanket ours/theirs resolution, whole-tree copying, or unreviewed cherry-picking.
- Freeze functionality: exactly six bounded deterministic local research tasks; no runtime LLM/SLM; no new cell-direct-edit feature; no verified external route.
- The raw imported table remains read-only. Transformations are explicit pipeline steps, and changed data requires re-import/review/replanning as applicable.
- Recommendations remain `EXPERIMENTAL`, never auto-selected or auto-run. Calculation begins only through the separate confirmed Run action.
- Do not claim recommendation validity, expert equivalence, SPSS superiority, broad social-science coverage, complete accessibility, complete bilingual support, a B5 HP pass, or stable cold-render performance.
- Publish GPL-3.0-only source and no prebuilt binary for this submission.
- Do not lower a test or performance threshold to create a pass.
- Historical B4-R evidence remains bound to commit `989d5c5829e3d3de69ebda0f4fc88e6f76d16112` and kit SHA-256 `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43`.
- The owner alone supplies the primary-thread `/feedback` Session ID, records and uploads the public YouTube demo, and performs the final Devpost review and submit action.
- Before push, public-default merge/change, or final submission, report the exact command plan and possible losses.

---

### Task 1: Seal the observed release work

**Files:**
- Create: `docs/build-week/INTEGRATION_LEDGER.md`
- Create: `docs/superpowers/plans/2026-07-20-modori-build-week-submission-closure.md`
- Preserve and commit: `pyproject.toml`, `src/modori/ui/controller.py`, `src/modori/ui/run_validation.py`, `tests/ui/test_research_flow_controller.py`, `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `constraints/build-week-windows-py312.txt`, `docs/build-week/**`

**Interfaces:**
- Consumes: dirty working tree rooted at `eaa0e802a0c64f6619297432f129be4d198a79ea`.
- Produces: one commit that makes every observed release artifact recoverable before integration.

- [ ] **Step 1: Confirm identity and inventory**

Run:

```powershell
git rev-parse HEAD
git branch --show-current
git status --porcelain=v2
```

Expected: HEAD `eaa0e802a0c64f6619297432f129be4d198a79ea`, branch `codex/modori-build-week-release-p0`, the four tracked modifications and release-document additions recorded in `INTEGRATION_LEDGER.md`.

- [ ] **Step 2: Verify the two affected test modules**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\ui\test_run_validation.py tests\ui\test_research_flow_controller.py
```

Expected: `54 passed` and exit code `0` on the observed pre-integration tree.

- [ ] **Step 3: Stage only the recorded release paths**

Run:

```powershell
git add -- pyproject.toml src/modori/ui/controller.py src/modori/ui/run_validation.py tests/ui/test_research_flow_controller.py README.md LICENSE THIRD_PARTY_NOTICES.md constraints docs/build-week docs/superpowers/plans/2026-07-20-modori-build-week-submission-closure.md
git diff --cached --check
git diff --cached --stat
```

Expected: no whitespace error; no file outside the listed release paths.

- [ ] **Step 4: Commit the preservation point**

Run:

```powershell
git commit -m "docs: seal Build Week source release baseline"
```

Expected: a new commit with the full recorded release work and no unstaged original dirty change.

### Task 2: Integrate the functional-usability candidate by meaning

**Files:**
- Merge: all paths reachable from `eaa0e802..b368cdcf`
- Resolve: `src/modori/ui/controller.py`
- Resolve: `tests/ui/test_research_flow_controller.py`
- Update: `docs/build-week/INTEGRATION_LEDGER.md`

**Interfaces:**
- Consumes: sealed release commit plus functional candidate `b368cdcf208d04509717826bc6b0ab7e7b72ba7e`.
- Produces: one merge commit whose final behavior uses the live pipeline provider and the real import-to-export novice E2E.

- [ ] **Step 1: Begin a history-preserving local merge without committing**

Run:

```powershell
git merge --no-ff --no-commit b368cdcf208d04509717826bc6b0ab7e7b72ba7e
```

Expected: additions from all twelve functional-usability commits and conflicts limited to the two recorded overlapping paths. If any other conflict appears, stop and add it to the ledger before resolution.

- [ ] **Step 2: Resolve controller semantics**

The final `ResearchPreparationEditor` construction must be:

```python
preparation_editor = ResearchPreparationEditor(
    pipeline_ops_provider=lambda: owner._services.pipeline_ops,
    version_provider=lambda: owner.pipeline_version,
    current_dataset_fingerprint=runtime.current_dataset_fingerprint,
    commit_pipeline_change=lambda preparation: _commit_research_preparation(
        owner,
        preparation,
    ),
)
```

Remove the release-side `_CurrentPipelineOperations` adapter from the final tree. Retain all unrelated localization and functional-candidate changes.

- [ ] **Step 3: Resolve test semantics**

Retain `test_imported_pipeline_can_confirm_research_preparation_without_running`, including import, variable-meaning review, explicit confirmation without worker submission, separate Run, and Word export assertions. Remove the narrower release-side `test_ui_controller_confirms_against_replaced_import_pipeline` from the final tree because the retained E2E subsumes it.

- [ ] **Step 4: Verify the semantic boundary before completing the merge**

Run:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\ui\test_run_validation.py tests\ui\test_research_flow_controller.py tests\ui\test_research_os_novice_e2e.py
git diff --cached --check
git status --short
```

Expected: all selected tests pass; exactly the intended merge changes are staged; no conflict marker remains.

- [ ] **Step 5: Complete the merge commit**

Run:

```powershell
git commit -m "merge: integrate Research OS functional usability"
```

Expected: a two-parent commit preserving both the sealed release baseline and `b368cdcf` ancestry.

### Task 3: Align every submission surface with the integrated product

**Files:**
- Modify: `README.md`
- Modify: `docs/build-week/BUILD_WEEK_DELTA.md`
- Modify: `docs/build-week/CLAIM_MATRIX.md`
- Modify: `docs/build-week/DEMO_SCRIPT.md`
- Modify: `docs/build-week/DEVPOST_SUBMISSION.md`
- Modify: `docs/build-week/RELEASE_CHECKLIST.md`
- Modify: `docs/build-week/VERIFICATION.md`
- Modify: `docs/build-week/assets/modori-build-week-demo.en.srt`

**Interfaces:**
- Consumes: integrated QML, controller contracts, novice E2E, local verification results.
- Produces: one consistent English judge path, claim authority, demo packet, and owner checklist.

- [ ] **Step 1: Update product and judge-path facts**

Document the Royal Blue entry/workspace integration, Variable Meaning Gate, explicit no-calculation confirmation, separate Run, Word export, and drift/replanning behavior. State explicitly that the imported raw table is read-only, transformations are pipeline steps, and changed source data is re-imported and reviewed; do not imply spreadsheet-style direct cell editing.

- [ ] **Step 2: Preserve non-claims and separate evidence identities**

Keep the B4-R `3233 passed, 13 skipped` result tied only to its historical kit. Record the `b368cdcf` candidate observation `3289 passed, 5 skipped` as candidate evidence until replaced by the final merged-source gate. Record cold-render observations as mixed `292–303 ms` failures and `200–217 ms` passes, explicitly not stable characterization and not a release pass.

- [ ] **Step 3: Retarget the demo to the actual UI**

Keep total duration below three minutes. Show entry/local boundary, synthetic import, variable metadata review, Research OS intake, Variable Meaning Gate, experimental candidate, configuration confirmation without calculation, separate Run, result, and Word export. Keep narration and SRT text identical and preserve all non-claims.

- [ ] **Step 4: Put owner-only blockers first**

The checklist must put these three actions at the top with the internal 2026-07-21 KST deadline: primary-thread `/feedback` Session ID; public YouTube recording/upload; signed-out Devpost/repository/video review and final submission.

- [ ] **Step 5: Run deterministic documentation checks**

Run repository link, SRT/SVG syntax, claim scans, and `git diff --check` using the exact documented release commands. Expected: no broken repository-local link, malformed subtitle/XML asset, forbidden claim, or whitespace error.

### Task 4: Produce fresh final-source verification

**Files:**
- Modify: `docs/build-week/VERIFICATION.md`
- Modify: `docs/build-week/RELEASE_CHECKLIST.md`

**Interfaces:**
- Consumes: final integrated source tree and Python 3.12.10 environment.
- Produces: commit-bound commands, counts, durations, hashes, and explicit pending rows.

- [ ] **Step 1: Run fast static and launch gates**

Run compile, Ruff, package metadata, source launch smoke, and the judge smoke cohort. Record exact exit codes and output identities.

- [ ] **Step 2: Run the full non-gallery test suite once**

Run the repository's final non-gallery command without altering markers or thresholds. Record the exact passed/skipped/failed counts and duration. If it fails, separate the cause; do not rerun merely to manufacture a pass.

- [ ] **Step 3: Run packaging and packaged judge smokes**

Build the unsigned local one-folder package and run launch, engine, public-data, and novice-path checks. Do not publish the binary. Record exact artifact identity and SHA-256 only if the build and all named smokes finish successfully.

- [ ] **Step 4: Record visual performance honestly**

Carry forward both observed cold-render bands and run only the planned final measurement. Do not lower the 250 ms gate. Classify performance as uncharacterized if mixed results remain.

- [ ] **Step 5: Update verification evidence**

Replace final-source pending rows only where this run produced exact evidence. Leave absent R, HP, public URL, Session ID, or owner-review rows pending rather than inferring success.

### Task 5: Commit the final local candidate and report the public execution plan

**Files:**
- Commit: all reviewed submission and verification changes from Tasks 3–4.

**Interfaces:**
- Consumes: clean verified integrated source candidate.
- Produces: local release-candidate commit and a no-surprise external publication plan.

- [ ] **Step 1: Verify staged scope and final identity**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected: only reviewed submission and evidence changes remain.

- [ ] **Step 2: Commit the local release candidate**

Run:

```powershell
git add -- README.md docs/build-week
git commit -m "docs: close Build Week submission candidate"
```

Expected: clean worktree and a commit whose recorded verification hashes match its documented source identity, or an explicit documented reason why a post-commit hash record requires one final evidence-only commit.

- [ ] **Step 3: Report before external mutation**

Report the exact branch, commits, proposed remote ref, proposed public-default integration method, signed-out audit sequence, and rollback path. Do not push, change the public default, upload, or submit until this report has been delivered.
