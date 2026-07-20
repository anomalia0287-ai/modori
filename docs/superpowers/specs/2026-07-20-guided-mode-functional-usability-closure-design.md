# Guided Mode Functional Usability Closure Design

**Date:** 2026-07-20
**Status:** In progress; U-01 through U-05 verified closed, U-06 active P0
**Baseline:** `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` on `codex/research-os-functional-usability`
**Release boundary:** no push, merge, default-branch change, or frozen Build Week artifact replacement

## 1. Objective

Make Modori's bounded Research OS path useful and understandable to a novice without
weakening safety, provenance, or deterministic execution boundaries.

The product promise has two inseparable parts:

1. **Useful:** get data in, understand what Modori needs, reach a supported analysis,
   inspect the exact configuration, run it, recover, and keep the output.
2. **Bounded:** experimental guidance remains separate from the calculation engine;
   unsupported claims may abstain; nothing is silently selected or run; assisted
   provenance is committed before display or export.

Safety is necessary, but repeated warnings are not a substitute for a successful
workflow.

## 2. Confirmed Repository State

- Controller modes are `guided` and `standard`; each process starts in `standard`.
- User-facing copy says `GUIDED MODE` and `PRO MODE`; internal values remain `guided`
  and `standard`.
- Guided and standard Research OS views retain equivalent state, actions, options, and
  decision authority. Standard exposes more role/evidence detail.
- Guided mode does not automatically select, prepare, confirm, or run an analysis.
  `Prepare`, confirmation, and `Run` remain separate.
- Guided entry now carries the experimental/manual-review disclosure once, and the
  open guide retains one quiet status. Candidate and preparation stages use
  action-specific copy without weakening explicit Prepare, Confirm, and Run steps.
- All seven audited abstentions were `unsupported_causal_target`. The same user data
  reached `candidate_ready` with supported non-causal questions. Generic abstention UI
  hid the distinction.
- Normal Excel files work, including multi-row headers. A recoverable workbook fails
  before the dialog opens when its default sheet is empty or a notice even though a
  data sheet exists.
- `DataGridView.qml` fixes every column at 120 pixels and right-elides long text. It has
  no bounded auto-fit or manual resizing.
- The detached table reuses the current `dataModel`; it is not an immutable raw view.
- Research OS ordinary failures discard actionable detail and render a generic state.
- Repeated Word export to the same path can silently replace an earlier document.
- Variable Meaning Gate identifies missing meaning but lacks a complete in-flow repair
  route for concept/unit metadata.
- Unrestricted raw-cell mutation is outside the immediate boundary. A reproducible
  value-correction workflow is still required and retained below.

## 3. Single-P0 Order

Only one active P0 is worked at a time. Queued work retains an owner, exit criteria,
and ledger position until verified or explicitly superseded by the user.

Implementation order follows user cost of failure:

1. prevent data loss;
2. let the user import data;
3. make the guided journey coherent and recoverable;
4. make data readable;
5. make meaning and values reproducibly correctable;
6. re-audit the entire novice task.

## 4. Closure Ledger

| ID | Problem | Classification and state | Exit condition |
| --- | --- | --- | --- |
| U-01 | Word export can silently overwrite | **Verified closed / data loss prevented** | Existing target never changes without explicit replace consent; safe copy is available; DOCX is verified |
| U-02 | Excel cannot reach sheet selection after a bad default-sheet preview | **Verified closed / import blocker removed** | A parseable workbook retains its path and exposes sheet selection; corrupt input still fails closed |
| U-03 | `CASUAL MODE` misstates the contract | **Verified closed / guided contract named accurately** | Every user-facing selector says `GUIDED MODE`; internal `guided` remains compatible |
| U-04 | Experimental/no-auto warnings repeat | **Verified closed / warning fatigue removed** | One entry disclosure plus one quiet status; no duplicate warning in one decision context |
| U-05 | Abstention looks arbitrary | **Verified closed / reason and bounded recovery visible** | Typed reason is visible; causal abstention offers explicit non-causal reframe and direct analysis without changing intent silently |
| U-06 | Research OS failure hides cause and next action | **Active P0 / required functional recovery** | Sanitized reason, explanation, and state-valid recovery action are visible |
| U-07 | Long cells and headers cannot be read or resized | **Required inspectability fix** | Bounded auto-fit, manual resize, keyboard fit/reset, and full-text access work in both grids |
| U-08 | `데이터 넓게 보기` is vague; `데이터 원본 보기` would be false | **Required terminology fix** | Copy is `데이터 시트 열기` / `Open data sheet`; no immutable-raw claim |
| U-09 | Meaning Gate identifies missing metadata but cannot repair it | **Required gate completion** | User reaches the relevant variable setting, saves supported metadata, and receives a newly bound review |
| U-10 | Individual erroneous cells cannot be corrected | **Required follow-up; deferred, not abandoned** | Separate approved design supplies previewed, reversible, provenance-bound correction without raw mutation |
| U-11 | External Fable 5 participation validation is absent | **Separate submission owner; unverified, not abandoned** | Real external outcome is recorded; this branch never fabricates it |

Items may move forward when new evidence makes them blockers. They do not disappear
because a deadline passes.

### 4.1 U-01 closure evidence

Verified on code commit `b8b6839` in this branch. This is a branch claim, not a frozen
Build Week artifact claim.

- Focused gates: pipeline report `16 passed`; export service `14 passed`; controller
  replacement `6 passed`; QML/catalog/runtime `44 passed`.
- Non-gallery UI gate: `775 passed in 70.13s`, exit 0, with workspace-local
  `--basetemp`. `test_research_flow_visual_gallery.py` remains outside this claim; an
  earlier unrestricted run reached its fixture with a system-temp permission error.
- Ruff, compileall, and `git diff --check`: exit 0.
- Current-source smoke imported
  `C:\Users\V\.codex\worktrees\3998\TongTong\src\modori\__init__.py` and wrote
  `C:\Users\V\.codex\worktrees\3998\TongTong\.test-tmp\u01-smoke-current-b884d6eee9874d9b8b0879d0435c19ab\modori-output\report.docx`.
- Initial and post-cancel file: `76,374` bytes, SHA-256
  `dc65fe60301cefc959dd69dfffd7a803fdec98c8d36cbe9ec6f59571e385e588`.
- Approved replacement: valid DOCX ZIP, `76,375` bytes, SHA-256
  `7ce02ec1637c7d389f1edefc0b05717f5158ed8e6ffad8379d170a9c52178ba5`.
- Injected post-mutation failure restored the approved file to the same size and
  SHA-256; no `.backup` file remained.

The safe copy is the same-directory transactional backup used only during an approved
replacement. It is restored on export or disclosure failure and removed after a
successful replacement. No arbitrary Save As destination was added.

### 4.2 U-02 closure evidence

Verified on implementation commits `6456e25`, `0c8171d`, and `717ec9a`. The final gate
also includes Windows report-publication hardening commits `d6943dd` and `2f9cb73`,
which were required after the full suite exposed transient file locks.

- Table/XLSX focus: `16 passed`; import/QML focus: `57 passed`; combined import/QML
  runtime slice: `73 passed`.
- Final non-gallery UI gate: `785 passed in 95.59s`, exit 0, with workspace-local
  `--basetemp`.
- Ruff, compileall, and `git diff --check`: exit 0.
- Current-source smoke imported
  `C:\Users\V\.codex\worktrees\3998\TongTong\src\modori\__init__.py` and used
  `C:\Users\V\.codex\worktrees\3998\TongTong\.test-tmp\u02-smoke-current-3c4dcbd5fb814dfe9911515d4027154c\recoverable.xlsx`.
- The workbook had active `안내`, valid `응답자료`, and `코드북` sheets. Initial table
  preview remained false, recovery exposed all three names, and only an explicit
  `응답자료` preview enabled confirmation.
- Confirmed data was exactly two columns (`id`, `score`) and two rows; the committed
  import step recorded `table_layout.sheet_name=응답자료` and the schema-bound column
  selection.
- Source workbook before/after: `5,920` bytes, SHA-256
  `18d26768f53226e47e745e5a43d33c8b6eaad0f884567f4a88ce95a5bd18c54a`.
- Automated tests prove corrupt XLSX exposes no recovery state and a current pipeline,
  pipeline version, and dataset remain unchanged through recovery preview until
  explicit Confirm.

This evidence applies to the branch only. No frozen wheel, one-folder launcher,
default branch, or release artifact was replaced.

### 4.3 U-03 closure evidence

Verified on implementation commit `3e1c391` in this branch.

- TDD RED: the three changed naming contracts failed against the previous
  `CASUAL MODE` copy before implementation.
- Korean and English entry/workspace catalog values are exactly `GUIDED MODE`; a
  catalog regression rejects any remaining user-facing `CASUAL MODE` value.
- Internal QML/controller requests remain `chooseMode("guided")` and
  `chooseMode("standard")`; no controller, presenter, recommendation, or execution
  implementation changed.
- Mode, controller, presenter, recommendation, privacy, catalog, and QML runtime
  regression slice: `189 passed in 46.48s`, exit 0.
- Final non-gallery UI gate: `785 passed in 121.26s`, exit 0, with workspace-local
  `--basetemp`.
- Ruff, compileall, and `git diff --check`: exit 0.

That commit closed the misleading name only. Warning consolidation remained U-04 at
that checkpoint and is closed separately with the evidence in section 4.4.

### 4.4 U-04 closure evidence

Verified on implementation commit `891db7f` and independent-review correction commit
`9a10e6d` in this branch.

- Entry copy states the benefit first and the experimental/manual-review boundary
  once. The open guide retains one `실험적 가이드` / `Experimental guide` badge;
  candidate, preparation, confirmation, and the Research OS toggle no longer repeat
  the same global warning.
- Candidate stages now say `후보 준비됨`, `설정 준비 안 됨`, `설정 검토`, or
  `설정 확인됨` according to the actual state. The blocked state never presents a
  Prepare action or ready-state next step.
- A read-only independent review found two Important issues in `891db7f`: production
  blocked preparation still received ready copy, and the sole persistent status had
  no accessibility interface. Correction TDD reproduced ten failures, then passed the
  same ten contracts. `StateBadge` now exposes a static-text accessible name, and the
  open/close toggle description follows its state.
- Related presenter, QML runtime, catalog, accessibility, and panel slice:
  `147 passed in 22.90s`, exit 0. Ruff, compileall, and `git diff --check`: exit 0.
- Final clean-commit non-gallery UI gate on `9a10e6d` with workspace-local
  `--basetemp`: `790 passed in 65.48s`, exit 0.
- Final clean-commit visual-gallery gate: `12 passed in 38.90s`, exit 0. Its 30-item
  persistent Windows render manifest records source commit
  `9a10e6d2aba78aaa9f863cf1c8528ab0682a0f68`, `production-windows`, 387 available
  font families, and zero horizontal overflow, clipped headers, missing regions,
  property mismatches, or catalog misses. Manifest SHA-256:
  `88d7e4af1311a85e9d724dabdabd7c60bc2db5cd6019a3768c539735ba61dafd`.
- Current-source Windows entry captures showed the complete Korean and English Guided
  Mode descriptions without clipping. SHA-256 values are
  `1325b5bc1790f253fb79d9688bd319161a913d312c377cb883806cdd3c53074a`
  (Korean) and
  `a4cac1d3a6ac54ed9954b001d2c86f9d417ba6873cc652526e26160e28c588ce`
  (English).
- Current-source Windows work captures showed one persistent status. They also
  independently retained the queued U-07 English quick-candidate elision and U-08
  `Open wide data view` terminology findings; neither was hidden or reclassified as
  closed by U-04.
- Sealed preparations still retain `experimental=True` and
  `requires_explicit_configure_confirm_run=True`. Assisted provenance, report
  disclosure, commit-before-display, abstention, explicit confirmation, and separate
  Run boundaries remain unchanged.

This is branch evidence only. No wheel, one-folder launcher, frozen Build Week
artifact, push, merge, or default branch changed.

### 4.5 U-05 closure evidence

Verified on implementation commit `950a922`, first independent-review correction
`4ba879f`, atomic head-guard commit `6c370bf`, and final independent-review correction
`95060ee` in this branch.

- Guided and Pro views project the sealed passport's typed abstention reason. The
  exact causal tuple is `unsupported_causal_target` with recovery requirement
  `declare_noncausal_or_use_external_causal_workflow`; Pro diagnostics are bounded
  and Guided copy remains plain language.
- Only that exact causal abstention exposes `reframe_noncausal`. It starts a fresh
  task at non-causal intake without silently choosing a profile, candidate,
  preparation, confirmation, or run. The original causal task becomes read-only and
  its ledger remains byte-for-byte logically unchanged after the later non-causal
  commit.
- Independent review first found same-version dataset/head drift gaps and unbounded
  diagnostics; those were reproduced and corrected. The follow-up found a
  recover-to-replan race. The final design holds the task-index writer transaction,
  revalidates the exact recovered `LedgerHead`, and only then creates and installs
  the replacement. A mismatch leaves the original locator active and creates no new
  ledger.
- Final review follow-ups directly exercise mutation between the early verification
  and transactional guard, reject a guarded cross-identity shortcut before either
  task changes, and classify ordinary SQLite writer contention as conflict rather
  than corruption. Final read-only review reported no remaining Critical, Important,
  or Minor finding and approved U-05 closure.
- Clean-commit focused race and review regressions on `95060ee`: `6 passed in 4.36s`.
  Related task-index, task-session, and controller files: `94 passed in 13.26s`.
  Core Research OS suite under normal Windows: `314 passed in 28.30s`.
- Final clean-commit non-gallery UI gate with workspace-local `--basetemp`:
  `800 passed in 64.99s`, exit 0. Ruff, compileall, and `git diff --check`: exit 0.
- Final production-Windows visual-gallery gate: `13 passed in 41.80s`, exit 0.
  Its 31-item manifest records source commit
  `95060ee61eae380195b4efb18a1ae1b8cb9ee3aa`, `production-windows`, and zero
  horizontal overflow, missing regions, property mismatches, or catalog misses.
  State-render p95 was `249.755 ms` against the unchanged `250 ms` gate; interaction
  p95 was `31.611 ms`. Manifest SHA-256:
  `b14d60d9e6aca249f133fd36bb2adfbf52d23cc44e1052d9332ca46e0c4e26f6`.
- The actual runtime audit reached causal intent, committed causal abstention,
  explicit non-causal reframe, fresh Variable Meaning Gate, and a later ordinary
  non-causal commit. The original passport, events, artifacts, and head remained
  unchanged; no candidate or preparation appeared before that new commit.

This is branch evidence only. No wheel, one-folder launcher, frozen Build Week
artifact, push, merge, or default branch changed. U-06 is now the sole active P0;
U-07 through U-11 remain retained follow-ups, and U-10 remains deferred rather than
abandoned.

## 5. Guided Mode Contract

### 5.1 Naming and value proposition

User-facing names become `GUIDED MODE` and `PRO MODE`. Internal values remain `guided`
and `standard` to avoid unnecessary controller, presenter, persistence, and test risk.

`AUTO MODE` is rejected: the product does not automatically select, prepare, confirm,
or run an analysis.

Korean primary description:

> 연구 질문과 데이터 구조를 따라 분석 후보와 필요한 확인을 단계별로 안내합니다.

English primary description:

> Follow guided steps from your research question and data structure to a reviewable analysis candidate.

Compact secondary disclosure:

> 실험적 연구 가이드 · 설정과 실행은 직접 확인

> Experimental research guide · You review the setup and start the run

The benefit precedes the limitation. The disclosure applies to candidate guidance,
not to every manual calculation module.

### 5.2 Session disclosure

First Guided Mode entry in a process presents this complete contract inline, not in a
modal:

> 후보 안내는 실험적입니다. 계산 모듈은 별도 검증 범위를 가지며, 설정과 실행은 사용자가 확인합니다.

Entry is explicit and not persisted across restarts. Inspecting the mode never mutates
the pipeline or selects a candidate. After entry, the shell retains one quiet status:
`실험적 가이드` / `Experimental guide`. Candidate and preparation screens do not
repeat equivalent experimental/no-auto-run sentences.

### 5.3 Fixed evidence and execution boundary

- Guidance status never changes numerical parameters, cache identity, or engine claims.
- Assisted configuration retains `experimental_candidate_assisted` provenance.
- Manual configuration remains `manual` unless an assisted prefill is still in use.
- Assisted reports keep their provenance disclosure.
- Candidate display remains commit-before-display.
- No command combines recommendation application and execution.

## 6. Interruption Model

Every message has exactly one level.

### Mode information

Sets expectations once. It never blocks inspection, question entry, candidate browsing,
or direct analysis. Examples are the experimental-guidance and no-auto-run boundary.

### Review request

Appears inline only when information changes the defensible configuration. It blocks
only the dependent action and links directly to remediation. Examples are missing
meaning, required roles, and stale preparation.

### Hard block

Prevents data loss, integrity failure, unsupported claims, or unconfirmed execution.
It names the specific reason, affected action, and valid next actions. Examples are
existing Word targets, ledger corruption, causal claims outside scope, and an
unconfirmed assisted run.

Generic danger prose is not shown when a specific condition is known. Identical
warnings do not repeat within one visible decision context.

## 7. End-to-End Interaction

### 7.1 Excel import

1. Record the selected local path before tabular preview.
2. Enumerate workbook sheets independently of a successful default-sheet preview.
3. Open the ordinary inferred preview when the default sheet is usable.
4. If the workbook is parseable but the default sheet is empty/non-tabular, open the
   import dialog in recovery mode with the sheet selector and an explanation.
5. A chosen sheet must produce the ordinary schema-bound preview before confirmation.
6. Corrupt, unreadable, or unsupported-encryption input remains a terminal failure.

Recoverable preview failure preserves the pending path. Previous datasets and
pipelines remain untouched until import confirmation succeeds.

### 7.2 Data inspection

Embedded and detached grids share width behavior:

- deterministic bounded content-fit from header plus a sample;
- drag a header boundary to resize one column;
- keyboard-accessible fit/reset;
- full header/cell text access without requiring precise hover;
- widths remain view state and never mutate data or the pipeline.

The detached action becomes `데이터 시트 열기` / `Open data sheet`. It displays the
current model, including committed transformations, and is not called a raw-data view.

### 7.3 Variable meaning

The gate displays only recorded metadata and never invents definitions or units. A row
requiring repair links to its variable settings. Saving supported metadata invalidates
stale guidance and produces a new meaning review bound to the updated identity.

If the current metadata contract cannot persist concept/unit safely, the UI must say
`기록되지 않음` without requesting unsavable information. Persistence expansion needs
its own contract tests.

### 7.4 Task, clarification, recommendation, and abstention

Guided Mode presents one current next action and does not interleave repeated global
warnings. Questions stay deterministic and bounded; `잘 모르겠습니다` remains a valid
answer.

- **Recommend:** show the reviewable candidate and deterministic reason.
- **Clarify:** ask only a question capable of changing a supported decision.
- **Abstain:** show the typed reason and supported next actions.

For `unsupported_causal_target`, the primary recovery is an explicit choice such as
`인과 효과 대신 변수 간 관계 확인`. Choosing it records the non-causal boundary and
replans. Modori never rewrites intent silently. Direct analysis remains secondary. If
the user keeps causal intent, abstention stands.

Abstention counts are not reduced by weakening claims or fabricating candidates.

### 7.5 Prepare, confirm, and run

The five stages remain distinct: candidate display, Prepare, exact role/parameter
review, Confirm, separate Run. Only the current-stage instruction is prominent.
Dataset, metadata, role, candidate, or mode changes invalidate relevant confirmation.

### 7.6 Results and Word export

Numerical engine evidence remains separate from recommendation validity.

- New destination: write normally.
- Existing destination: require explicit replacement or a safe-copy path.
- Cancel: leave the existing file byte-for-byte unchanged.
- Assisted report: include required provenance before exposing completion.
- Write failure: do not expose a partial file as successful output.

### 7.7 Failure recovery

Research OS carries a sanitized presentation payload containing a stable reason code,
localized explanation, and valid recovery actions. Raw exceptions and cell contents
are never rendered. Integrity failure remains distinct from ordinary failure.

The primary button names the real action (`다시 시도`, `현재 데이터로 다시 계획`, or
`데이터 다시 열기`) rather than generic `기록에서 다시 확인` when the controller will
do something else.

## 8. Components and Data Flow

Expected copy/QML surfaces include:

- `src/modori/ui/strings.py` and `strings_en.py`;
- `EntryScreen.qml`, `ModeSegment.qml`, `GuideRail.qml`;
- `ResearchFlowPanel.qml`, `ResearchCandidateCard.qml`;
- `DataGridView.qml` and `Main.qml`.

`UiImportFlow` separates pending path, workbook discovery, successful table preview,
recoverable layout failure, and terminal read failure. QML opens `ImportDialog` for a
successful preview or recoverable workbook state; confirmation still requires a
successful schema-bound preview.

Research flow results gain a small typed, sanitized failure payload. Guided and
standard retain equivalent recovery authority; standard may expose a diagnostic ID,
never raw data.

Column widths are UI-only state keyed by column identity and reset with model/dataset
replacement. Sizing is bounded so an extreme cell cannot create an unusable width.

Report destination conflict is rejected at the service/controller boundary before
write, not merely warned about in QML, so alternate callers cannot bypass it.

## 9. Test and Audit Strategy

Implementation is test-first. Passing criteria are not weakened.

### Copy and boundary tests

- Korean and English use `GUIDED MODE` consistently.
- Internal modes and Guided/PRO decision equivalence remain unchanged.
- Disclosure appears only at approved mode-level locations.
- No combined recommendation-and-run command exists.
- Assisted provenance and report disclosure remain intact.

### Import tests

- empty first sheet plus populated second sheet;
- notice sheet plus multi-row-header data sheet;
- usable default sheet;
- corrupt/unreadable workbook;
- pending-path and previous-pipeline preservation;
- sheet change then schema-bound confirmation.

### Recovery tests

- causal abstention exposes exact reason and reframe;
- accepting the reframe records the boundary before replan;
- declining preserves abstention;
- ordinary, memory, and integrity failures remain distinct;
- each rendered recovery action maps to a valid controller command.

### Grid tests

- bounded widths for short and long content;
- single-column manual resize without data mutation;
- reset/fit and keyboard accessibility;
- full cell/header text access;
- embedded/detached parity and corrected naming.

### Report tests

- new destination succeeds;
- existing destination without consent fails before mutation;
- cancel preserves original SHA-256;
- explicit replacement produces a valid DOCX;
- safe copy preserves both documents;
- assisted disclosure and commit-before-display remain verified.

### Novice end-to-end audit

Exercise an actual Excel workbook through:

```text
open -> import -> meaning review -> task -> bounded questions ->
recommend/clarify/abstain -> exact roles/parameters -> Prepare -> Confirm ->
separate Run -> results/evidence -> Word export -> error recovery
```

Separate manual UI observations from automated assertions. Record generated paths,
sizes, hashes, and DOCX validity. Reachability does not prove universal recommendation
validity or numerical correctness beyond existing engine evidence.

## 10. Deadline and Release Boundary

The Build Week deadline is 2026-07-21. P0 evidence and artifacts were frozen in a
separate release worktree. This branch does not enter that build automatically.

Before any integration decision, report the user benefit, invalidated frozen evidence,
required rechecks, remaining unverified claims, and cost of deferral. This design does
not authorize push, merge, default changes, or release artifact replacement.

## 11. Non-goals and Retained Follow-ups

No generative model, SLM, cloud transfer, telemetry, broad method expansion, or
recommendation-validity promotion is added.

Unrestricted raw-cell editing is not enabled. U-10 remains a required follow-up for a
previewed, reversible, provenance-bound correction step. Deferral is not completion
and not abandonment.

External Fable 5 validation remains unverified until the separate submission owner
records real evidence.
