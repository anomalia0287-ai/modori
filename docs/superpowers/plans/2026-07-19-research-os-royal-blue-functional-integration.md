# Research OS × Royal Blue Functional Integration Plan

> Execute in this worktree only. Do not modify the four read-only reference
> worktrees named in the handoff. Do not push, merge, or replace release artifacts.

**Goal:** Preserve the complete Royal Blue/Aurora entry and workspace UI on top of
Research OS baseline `eaa0e802...`, prove the novice research path end to end, and
implement only the smallest audit-proven functional gate.

**Architecture:** Sequentially replay the seven source commits. Treat current
Research OS provenance, durable transitions, and manual execution as authoritative;
port Royal Blue locale and presentation behavior around them. After integration,
audit one production-path task and use TDD for the smallest reproduced gap.

**Runtime:** Python 3.12, PySide6/Qt 6.11, pytest, QML runtime, SQLite 3.49, local R
runtime where an actual statistical run requires it.

## Task 1: Freeze the pre-integration design and branch evidence

**Files:**

- Add: `docs/superpowers/specs/2026-07-19-research-os-royal-blue-functional-integration-design.md`
- Add: `docs/qa/research-os-royal-blue-functional-integration-ledger.json`
- Add: `docs/superpowers/plans/2026-07-19-research-os-royal-blue-functional-integration.md`

### Step 1: Validate the machine-readable ledger

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
python -m json.tool docs/qa/research-os-royal-blue-functional-integration-ledger.json > $null
```

Expected: exit 0, 25 entries, 12 `textual_conflict_preview: true` entries.

### Step 2: Recheck branch and baseline binding

Run:

```powershell
git branch --show-current
git merge-base HEAD eaa0e802a0c64f6619297432f129be4d198a79ea
git status --short
```

Expected: `codex/research-os-functional-usability`, exact baseline merge base, only
the three planned documentation files changed.

### Step 3: Commit the integration design

Commit only the three files with a message describing the frozen semantic
integration design. No product code enters this commit.

## Task 2: Replay entry design and plan

### Step 1: Cherry-pick source documentation in order

```powershell
git cherry-pick -x 55fe9791d2b38de6b1de93ba99ad8f0b417015fc
git cherry-pick -x 11a1280fa0d4ef9063401a3d9b25e814d81a2708
```

Expected: clean documentation-only commits. Verify `git diff-tree --stat HEAD` after
each and stop if product code appears.

## Task 3: Integrate bilingual entry implementation

**Primary shared files:**

- `src/modori/app.py`
- `src/modori/ui/controller.py`
- `src/modori/ui/recommendation_controller.py`
- `src/modori/ui/strings.py`
- `src/modori/ui/qml/components/GuideRail.qml`
- `src/modori/ui/qml/components/PipelineRail.qml`
- `src/modori/ui/qml/screens/WorkScreen.qml`
- shared entry, result, security, and metadata tests recorded in the ledger

### Step 1: Start the source replay

```powershell
git cherry-pick -x 64801e66cce82063f0cc68c978c27e4b6fa80ac6
```

Expected: conflicts. Record the actual unmerged path set before resolving.

### Step 2: Resolve Python contracts

- Keep current ResearchFlow and preparation architecture.
- Add localization modules/mixin and localized result/import/model behavior.
- Port English recommendation formatters to the current candidate DTO.
- Do not reintroduce `default_candidate`, candidate `level`, or auto-run.
- Add a language re-presentation API for ResearchFlow only through failing tests.

### Step 3: Resolve QML contracts

- Keep the production `ResearchFlowPanel` and legacy separation in `GuideRail`.
- Apply entry language bindings and Royal Blue presentation delta.
- Preserve separate Prepare, Confirm, Run, and report actions.

### Step 4: Resolve tests as assertion unions

Keep every applicable current assertion and every non-conflicting Royal Blue
assertion. Where a literal conflicts with a later measured accessibility contract,
update the Royal Blue assertion and record the reason in the ledger.

### Step 5: Focused verification

Run at minimum:

```powershell
python -m pytest -p no:cacheprovider \
  tests/ui/test_qml_string_catalog.py \
  tests/ui/test_controller.py \
  tests/ui/test_recommendations.py \
  tests/ui/test_research_flow_controller.py \
  tests/ui/test_research_flow_qml.py \
  tests/ui/test_release_research_os_integration_boundary.py \
  tests/ui/test_result_binding.py \
  tests/ui/test_security_privacy.py \
  tests/ui/test_variable_metadata_editing.py -q
```

Expected: all pass. Also search the merged code for removed APIs and conflict
markers. Continue the cherry-pick only after focused tests pass.

## Task 4: Replay workspace design and plan

```powershell
git cherry-pick -x 847c09505c655a4b36bf5e36af511a7f1fac4413
git cherry-pick -x bca88558818096ef258a635146e920633a6dff7a
```

Expected: documentation-only commits in exact order.

## Task 5: Integrate Royal Blue workspace implementation

**Primary shared files:**

- `src/modori/ui/qml/theme/Theme.qml`
- `src/modori/ui/qml/components/AppButton.qml`
- `src/modori/ui/qml/components/DataGridView.qml`
- `src/modori/ui/qml/components/GuideRail.qml`
- `src/modori/ui/qml/components/PipelineRail.qml`
- `src/modori/ui/qml/screens/WorkScreen.qml`
- visual, mode, grid, security, and file-audit tests in the ledger

### Step 1: Start the workspace replay

```powershell
git cherry-pick -x 9db213cf8c13713608fb8e98aabb44447057be50
```

### Step 2: Resolve theme and controls

Port Royal Blue tokens and layouts. Preserve current warning `#865F1B`, primary
focus `onBrand`, non-primary `focusRing`, accessible names, reduced-motion behavior,
and semantic warning/danger separation.

### Step 3: Verify workspace and Research OS together

Run at minimum:

```powershell
python -m pytest -p no:cacheprovider \
  tests/test_file_operation_audit.py \
  tests/ui/test_compact_control_system.py \
  tests/ui/test_cream_nacre_visual_system.py \
  tests/ui/test_data_grid_qml.py \
  tests/ui/test_human_operated_qml_flow.py \
  tests/ui/test_mode_action_surfaces.py \
  tests/ui/test_qml_visual_contract.py \
  tests/ui/test_research_flow_qml.py \
  tests/ui/test_security_privacy.py -q
```

Then run the actual ResearchFlow visual gallery outside the sandbox if Qt/pytest
temporary-directory ACLs require it.

## Task 6: Integrate variable editor/entry refinement

```powershell
git cherry-pick -x 7a1ec2fd79ec4b8cf81c9d9008f7699a98124e2e
```

Review all four source paths, especially the shared human-operated flow test. Keep
machine roles for variable key and measurement level, localized headings, and the
Step-backed metadata update path.

Run:

```powershell
python -m pytest -p no:cacheprovider \
  tests/ui/test_data_transform_qml.py \
  tests/ui/test_human_operated_qml_flow.py \
  tests/ui/test_data_grid_qml.py \
  tests/ui/test_variable_metadata_editing.py -q
```

## Task 7: Close the integration ledger

For each of the 25 entries:

- set the actual resolution and status;
- add the full integrated blob OID;
- add focused test evidence;
- record any intentional source-token supersession;
- prove all required presences and forbidden absences.

Add a verification test that loads the JSON, checks exact paths/counts, verifies
integrated blob OIDs against the current tree, and rejects unverified entries.

## Task 8: Audit one novice task through the production path

### Step 1: Choose a synthetic fixture

Use a small local fixture with explicit labels, measurement levels, and a known
noncausal P1 route. Prefer a two-group mean or two-variable association because it
exercises distinct roles and can produce clarification or abstention.

### Step 2: Add audit instrumentation/tests without changing product behavior

Create an end-to-end test that captures:

- import confirmation and variable model;
- visible variable-meaning/metadata review opportunities;
- selected task/profile and role inputs;
- committed initial request and clarification events;
- active passport digest and planner trace;
- state outcome (`recommend`, `clarify`, or `abstain`);
- exact preparation method, roles, and parameters;
- zero runs before explicit Run;
- one run after explicit Run;
- result/evidence model;
- `.docx` creation and package-content assertions;
- stale-data or invalid-input recovery.

### Step 3: Inspect the actual local ledger

Open the task SQLite file read-only after the UI flow and verify the displayed
sequence/passport digest matches the committed head. Prove the legacy recommendation
state has no passport fields and is not used by the ResearchFlow candidate card.

### Step 4: Write the audit result

Add `docs/qa/research-os-royal-blue-novice-flow-audit.md` separating:

- verified behavior;
- reproduced usability/safety gaps;
- inferences;
- still-unverified behavior.

## Task 9: Select the smallest required gate

Use the design decision rule. Candidate ordering is evidence-driven, not fixed.

If the Variable Meaning Gate remains the highest-severity reproduced gap, its
minimum contract is:

- show the exact selected variable ID, label, measurement level, and role before
  initial authority is committed;
- require a distinct explicit confirmation for the current dataset fingerprint and
  selected role set;
- reject missing, stale, changed, duplicate, or out-of-dataset variables;
- remain local and deterministic;
- do not infer meaning, suggest a model, or run analysis;
- bind the confirmation into the initial request's provenance so role facts cannot
  claim authority from free-text entry alone.

Do not implement this contract unless the audit proves it is necessary and no
smaller existing control suffices.

## Task 10: Implement the selected gate with TDD

### Step 1: Write RED tests

Cover controller state, QML reachability, current-fingerprint binding, stale
invalidation, ledger/passport provenance, language/mode parity, abstention, and
zero-run behavior. Run the exact tests and capture the expected failures.

### Step 2: Implement the smallest production change

Prefer one closed typed gate state and one explicit UI action. Avoid new method
families, direct cell editing, broad schema changes, or heuristic inference.

### Step 3: Run GREEN and regression tests

Run the new tests, all Research OS boundary tests, all integration-focused tests,
and the end-to-end novice flow.

### Step 4: Refactor without widening scope

Remove duplication only after GREEN. Re-run the same tests after refactoring.

## Task 11: Final verification

Run fresh commands with no pytest result cache:

1. integration-ledger validator;
2. localization and QML test groups;
3. Research OS/Memory test groups;
4. real QML runtime and visual gallery;
5. novice end-to-end audit including Word output and recovery;
6. full repository suite;
7. conflict-marker/removed-API/network-route searches;
8. `git status`, ordered source-commit trailers, tree/blob hashes, and branch name.

Record exact commands, counts, skips, environment limits, output hashes, and any
remaining unverified claim. Do not report completion from stale or partial results.
