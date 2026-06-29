# UI Shell Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the #04 UI shell internals from test-passing to structurally excellent by removing transaction hazards, naming drift, controller overreach, QML duplication, weak lifecycle seams, and private implementation coupling while preserving every public behavior and output value.

**Architecture:** Keep the public v1 behavior stable. First harden engine/controller correctness seams with regression tests and an explicit pipeline edit transaction boundary, then move application behavior out of the QML bridge into focused services, then simplify QML bindings behind a command facade so the UI remains declarative and thin. Refactoring is structural only: user-visible analysis results, report values, CLI/module names, QML property names, and existing compatibility contracts must remain stable unless a defect is explicitly fixed by test.

**Tech Stack:** Python, PySide6/QML, pytest, existing Modori engine/core/ui modules.

---

## Audit findings driving this plan

1. `UiController` is 941 lines and owns import preview, recent files, settings, metadata editing, analysis selection, worker state, report export, explanation formatting, result formatting, chart cleanup, and QML bridge slots. This is operationally functional but not excellent internal design.
2. `updateVariableMetadata()` inserts a metadata Step before recompute, but if recompute fails the inserted Step remains while `pipeline_version` does not increment. This creates a mutated pipeline with a failure result that claims no committed version change.
3. `VariableMetadataPatch` uses `missing_codes`, while `VariableMetadataPatchStep` consumes `missing_values`. This naming drift means a full metadata patch can silently fail to update missing codes.
4. `Pipeline.metadata_writes()` is validated at result time but not included in static unique-write ownership or cached result write sets. Multiple metadata-only writers for the same variable can be inserted through engine APIs.
5. QML contains 47 inline `text:`/`placeholderText:` literals, despite a string catalog. This is acceptable for a prototype, not for a polished shell.
6. QML calls many controller methods directly from multiple surfaces. That keeps QML thin computationally, but UI command routing is scattered rather than intention-revealing.
7. Several tests reach private controller fields (`_latest_run_id`, `_worker`, `_pipeline_version`). That makes tests brittle around implementation shape rather than public behavior.

## External references reviewed, with license-safe usage

These sources inform engineering principles only. Do not copy prose, examples, diagrams, or code into this repository.

1. Qt Quick Performance documentation: use the principle that QML should avoid needless bindings/object churn and keep heavyweight work outside rendering paths.
2. Qt Internationalization documentation: use the principle that user-visible strings need a translation-ready boundary.
3. Cosmic Python Repository/Unit-of-Work chapters: use the general architectural pattern of explicit transaction/application-service boundaries, not the book's text or sample code.
4. Hynek Schlawack, "Don't Mock What You Don't Own": use the testing principle that fakes/mocks belong at owned boundaries, not around implementation internals.
5. Google Testing Blog, "Change-Detector Tests Considered Harmful": use the principle that tests should assert behavior and stable contracts, not private implementation details.
6. "Test Behaviors, Not Methods" (arXiv, 2026): use the principle that refactor-safe tests must lock observable state transitions and product contracts.

## Design standards for this hardening pass

1. Transaction boundaries must be explicit. Any operation that mutates pipeline topology and recomputes derived state must either commit all related state or restore all related state.
2. QML-facing objects must be adapters, not application service containers. `UiController` keeps existing Qt properties/slots but delegates work to focused collaborators.
3. Commands crossing from QML into Python must express user intent, not implementation choreography. Centralize command routing before adding more direct QML calls.
4. Tests must prefer public state transitions and DTOs. Private field reads/writes are allowed only in narrow test helpers with documented rationale.
5. String centralization is product infrastructure, not translation polish. It must not alter statistical prose, report wording, APA output, or knowledge-library content.
6. Compatibility is an invariant. Existing imports, entry points, QML names, DTO fields, and output bytes remain stable unless a documented bugfix requires a change.

## Non-goals

- Do not change statistical results, APA prose, report numeric output, or knowledge-library content.
- Do not add new analyses.
- Do not weaken existing security/privacy/thin-shell guards.
- Do not run release packaging or clean VM validation in this plan.

---

## Progress log

- 2026-06-29: Task 1 complete. Added transactional metadata-step insertion, metadata
  write ownership, rollback regression tests, and two full-suite verification runs.
- 2026-06-29: Task 2 complete. Reconciled `missing_codes` to engine
  `missing_values`, rejected ambiguous aliases and unsupported `display_type`, and
  completed two full-suite verification runs.
- 2026-06-29: Task 3 partial complete. Extracted command validation, import preview,
  explanation formatting, and result binding collaborators while preserving the QML
  API. Deeper session/application-service split remains open.
- 2026-06-29: Task 5 complete. Removed UI-test writes to controller private fields and
  added an explicit worker injection seam. Two full-suite verification runs completed.
- 2026-06-29: Task 3 session-boundary follow-up complete. Extracted settings-backed
  reduce-effects/recent-files state into `UiSessionState` while preserving controller
  properties and QML slots. Two full-suite verification runs completed.
- 2026-06-29: Task 4 complete. Moved static user-visible QML strings into the
  `UI_STRINGS_KO` catalog, replaced raw QML literals with `appBootstrap.text(...)`,
  and added a guard for raw `text`/`placeholderText`/`title`/`Accessible.name`/`qsTr`
  strings. Two full-suite verification runs completed.
- 2026-06-29: Application-service command routing follow-up complete. Extracted
  reliability/comparison/regression selection routing into `AnalysisSelectionCommandBuilder`
  and removed the old controller-only helper path. Two full-suite verification runs
  completed.
- Remaining: final documentation closeout and completion audit.

---

## Task 1: Make metadata Step insertion transactional and version-honest

**Files:**
- Modify: `src/modori/core/pipeline.py`
- Modify: `src/modori/ui/controller.py`
- Test: `tests/ui/test_variable_metadata_editing.py`
- Test: `tests/test_pipeline_core.py`

- [ ] Add a failing controller test where a newly inserted metadata patch fails during compute, then assert the pipeline Step list and `pipeline_version` remain unchanged.
- [ ] Add a failing core pipeline test for duplicate metadata writers to the same variable.
- [ ] Add an explicit pipeline edit transaction API, preferably `PipelineEditTransaction` or `Pipeline.try_insert_after(...)`, that snapshots `steps`, caches, dataset, analyses, and step results before insertion.
- [ ] Make the transaction API the only path used by controller metadata insertion when recomputation is required; raw `insert_after()` remains a low-level primitive and must not be used for recompute-coupled edits.
- [ ] Include `metadata_writes()` in static ownership checks and preflight/write-cache logic.
- [ ] Update `UiController.updateVariableMetadata()` to use the transactional helper and return a visible `engine_error` without partial mutation.
- [ ] Add assertions that failed insertion restores step order, result cache, dataset object identity or value equivalence, analysis outputs, and pipeline version.
- [ ] Run targeted tests for pipeline and metadata editing.

## Task 2: Reconcile metadata patch schema naming

**Files:**
- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/patches.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/steps/data_prep.py`
- Test: `tests/ui/test_patches.py`
- Test: `tests/ui/test_variable_metadata_editing.py`

- [ ] Add a failing test proving `missing_codes` from the UI patch updates `Variable.missing_values` in the engine dataset.
- [ ] Choose one public UI name: keep `missing_codes` in UI DTOs and map it explicitly to engine `missing_values` at the boundary.
- [ ] Reject simultaneous `missing_codes` and `missing_values` in UI-facing calls.
- [ ] Ensure `display_type` is either supported explicitly or rejected with a stable message; do not accept and ignore it.
- [ ] Run targeted metadata patch tests.

## Task 3: Split `UiController` into focused collaborators without changing QML API

**Files:**
- Create: `src/modori/ui/session.py`
- Create: `src/modori/ui/importing.py`
- Create: `src/modori/ui/commands.py`
- Create: `src/modori/ui/explanations.py`
- Create: `src/modori/ui/result_binding.py`
- Modify: `src/modori/ui/controller.py`
- Test: existing `tests/ui/test_controller.py`, `tests/ui/test_import_preview_recent_files.py`, `tests/ui/test_results_report_lifecycle_hardening.py`

- [ ] Extract import preview/recent-file logic into `importing.py` with a small public service API.
- [ ] Add `commands.py` as an intention-revealing command facade for QML-originated actions such as configure analysis, run analysis, update metadata, open import preview, save report, and request explanation.
- [ ] Extract result summary/table/note/chart-source formatting and cache cleanup into `result_binding.py`.
- [ ] Extract library explain formatting into `explanations.py`.
- [ ] Keep QML-facing properties/slots in `UiController`; delegate internals to collaborators and route newly touched QML actions through the command facade.
- [ ] Maintain backward-compatible public controller API.
- [ ] Add or update tests around public command outcomes rather than collaborator internals.
- [ ] Run targeted UI controller/result/import tests.

## Task 4: Centralize QML user-visible strings

**Files:**
- Modify: `src/modori/ui/strings.py`
- Modify: QML under `src/modori/ui/qml/`
- Test: `tests/ui/test_security_privacy.py`
- Test: `tests/ui/test_smoke_qml.py`

- [ ] Add string catalog keys for fixed QML chrome labels and placeholders.
- [ ] Replace hard-coded QML `text:` and `placeholderText:` where feasible with `appBootstrap.text(...)` or `qsTr(...)` when Qt extraction is the better long-term fit.
- [ ] Keep engine/reporting prose out of the catalog.
- [ ] Add a guard test that counts remaining literal strings and allows only documented exceptions.
- [ ] Run targeted QML source tests.

## Task 5: Reduce private-field coupling in UI tests

**Files:**
- Modify: `src/modori/ui/controller.py` only if small public test hooks are justified.
- Create: `tests/ui/helpers.py` only if shared public-behavior helpers reduce private coupling without weakening assertions.
- Modify: tests under `tests/ui/`

- [ ] Replace direct writes to `_latest_run_id` with public worker/submit helpers where possible.
- [ ] Replace direct assertions against `_pipeline_version`, `_worker`, and private caches with observable status, stale state, result DTO, chart source, report path, and command return assertions where possible.
- [ ] Add a small explicit test helper only if it wraps public behavior and does not leak into product UI behavior.
- [ ] Keep tests focused on public state transitions: status, stale, result DTOs, error messages, chart source, and report path.
- [ ] Run targeted UI tests.

## Task 6: Final cleanup and documentation update

**Files:**
- Modify: `docs/specs/04-ui-shell-commercial-v1-completion-audit.md`
- Modify: `docs/specs/04-ui-shell-commercial-v1-qa.md`

- [ ] Update the audit to distinguish “quality-hardened” from merely “gate-passing”.
- [ ] Record final verification evidence.
- [ ] Confirm no new release-scope claims are introduced.

---

## Plan self-review pass 1: coverage

- Metadata transaction hazard: covered by Task 1.
- Schema drift: covered by Task 2.
- Controller bloat: covered by Task 3.
- QML string duplication: covered by Task 4.
- Test brittleness: covered by Task 5.
- Documentation honesty: covered by Task 6.
- Explicit transaction/application-service architecture: covered by Task 1 and Task 3.
- License-safe external learning: covered by the reference section and the no-copy rule.
- No statistical behavior changes are required.

## Plan self-review pass 2: risk ordering

- Correctness hazards precede refactoring. Task 1 and Task 2 must complete before Task 3.
- Transaction hardening precedes controller extraction because the controller split must not preserve a broken mutation boundary.
- Refactoring preserves QML API to reduce blast radius.
- Command facade work is incremental and starts only on actions already touched by this pass.
- QML string cleanup is isolated after controller/service split.
- Test cleanup comes after stable public surfaces exist.

## Plan self-review pass 3: stop rules

- Stop if any Task 1/2 test exposes statistical result drift.
- Stop if controller split requires changing QML public method names.
- Stop if a QML string catalog change affects engine/reporting prose.
- Stop if compatibility would require renaming public DTO fields, module names, QML properties, or existing CLI entry points.
- Stop if external reference material would need to be copied rather than independently implemented.
- Stop if verification cannot be run. Execution requires explicit permission to run targeted and full tests.

## Execution verification required

After each task during execution:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Also repeat residue/security scans:

```powershell
rg -ni "tongtong" src tests pyproject.toml
rg -n "QMainWindow|QWidget|QApplication" src\modori\app.py src\modori\ui
rg -n "http://|https://|WebEngine|XmlHttpRequest|fetch\(|^\s*(from|import)\s+(requests|httpx|urllib|socket|webbrowser)(\.|\s|$)" src\modori\ui src\modori\app.py
```

## Execution permission note

This plan requires TDD red/green runs and two full-suite verification runs per completed task. If test execution is not explicitly authorized for an execution turn, implementation must stop before changing production code or must limit itself to documentation/plan work.
