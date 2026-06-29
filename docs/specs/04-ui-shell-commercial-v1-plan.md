# Modori UI Shell #04 Commercial v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use a gated implementation workflow.
> Complete one gate at a time. Do not start the next gate until the current gate has
> passed two full test runs and the gate-specific guard checks. Do not commit unless the
> owner explicitly requests it.

**Goal:** Complete the #04 UI Shell to a commercial-ready v1 level without weakening the
validated engine, reporting, or knowledge-library contracts.

**Architecture:** Build a PySide6 Qt Quick shell as a thin UI over the existing engine.
The UI creates/edits pipeline Steps, runs the engine through a serialized controller,
and renders display DTOs. The UI never computes statistics, never owns raw dataframe
state, and never calls network/model services.

**Tech Stack:** Python, PySide6/QML, Qt `QAbstractTableModel`, existing Modori engine
modules, pytest, AST/code guard tests, local-only packaged QML resources.

---

## Non-negotiable execution rules

- The final target is the whole commercial v1 UI shell, not isolated partial features.
- Work proceeds through the nine gates below in order.
- Each gate must end with:
  - Full test run 1 green.
  - Full test run 2 green.
  - Gate-specific guard checks green.
  - No known stale result, security, packaging, or spec-contract violation.
- If a failure, flaky result, unexplained warning, or spec contradiction appears, stop
  and report before continuing.
- Runtime network/model use is forbidden.
- UI code must not compute statistics or import statistical libraries.
- Existing engine/library behavior is preserved unless the owner explicitly approves an
  engine change required by the UI contract.
- The repository folder name `C:\Users\V\Desktop\TongTong` remains unchanged.

## Standard verification commands

Run these at every gate after the gate implementation is complete.

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Run these when the gate touches UI, packaging, imports, or privacy/security.

```powershell
rg -ni "tongtong" src tests pyproject.toml
rg -n "https?://|^\s*(from|import)\s+(requests|httpx|urllib|socket|webbrowser)(\.|\s|$)" src\modori\ui src\modori\app.py
.\.venv\Scripts\python.exe -c "import modori; from modori.knowledge import load_library; print(len(load_library().all_slugs()))"
```

Expected `tongtong` residue result: no matches.

Expected network scan result: no matches, except test fixtures that deliberately assert
the guard catches forbidden strings.

---

## Planned file structure

### Existing files to modify

- `src/modori/app.py`
  - Replace the legacy QWidget launcher with the QML launcher.
  - Keep `main() -> int`.
  - Load QML by package resource, not by current working directory.

- `pyproject.toml`
  - Include QML/package data.
  - Keep console script `modori = "modori.app:main"`.

- Existing tests under `tests/`
  - Update legacy app tests to QML/controller behavior.
  - Preserve all existing engine/library assertions.

### New Python package

- `src/modori/ui/__init__.py`
  - UI package marker. No runtime side effects.

- `src/modori/ui/contracts.py`
  - Dataclasses/enums for `CommandResult`, `ImportOptions`, `ReportExportOptions`,
    `DisplayResult`, `DisplayTable`, `DisplayColumn`, `DisplayNote`, patch schemas,
    `RunStatus`, `StepState`, and `ControllerMode`.

- `src/modori/ui/patches.py`
  - Strict patch parsing and validation.
  - Reject unknown fields and wrong primitive types.
  - Return structured validation errors without mutating the pipeline.

- `src/modori/ui/table_provider.py`
  - Narrow `TableProvider` protocol.
  - Engine-backed provider implementation.
  - Deterministic row id handling.

- `src/modori/ui/models.py`
  - Qt `QAbstractTableModel` wrappers for data, variable metadata, steps, and results.
  - Models depend on `TableProvider`/DTOs, not raw dataframes.

- `src/modori/ui/controller.py`
  - Main QML-facing controller.
  - Owns pipeline session state, worker queue, `run_id`, `pipeline_version`, stale/error
    handling, import/report commands, mode switching, and library explain calls.

- `src/modori/ui/worker.py`
  - Serialized engine job queue.
  - Applies results on the Qt main thread only.
  - Discards stale/out-of-order results.

- `src/modori/ui/resources.py`
  - Package-resource lookup for QML and local assets.
  - No current-working-directory dependency.

- `src/modori/ui/strings.py`
  - Korean-first UI chrome string catalog.
  - No duplicated engine/reporting prose.

- `src/modori/ui/help_keys.py`
  - UI-only help-key registry and `not_explainable` declarations.

- `src/modori/ui/security.py`
  - Guard helper constants for forbidden UI imports, calls, and remote URL patterns.

### New QML files

- `src/modori/ui/qml/Main.qml`
  - Root window and screen router.

- `src/modori/ui/qml/screens/EntryScreen.qml`
  - Entry screen with 안내/표준 choice, open data action, recent files area.

- `src/modori/ui/qml/screens/WorkScreen.qml`
  - Header, `SplitView`, guide rail, data/variable tabs, results panel, pipeline rail.

- `src/modori/ui/qml/screens/LoadingOverlay.qml`
  - Status/progress overlay and stale-result indicator.

- `src/modori/ui/qml/components/DataTable.qml`
  - Virtualized QML `TableView` bound to the data model.

- `src/modori/ui/qml/components/VariableTable.qml`
  - Virtualized variable metadata view.

- `src/modori/ui/qml/components/ResultsPanel.qml`
  - Renders display DTOs only.

- `src/modori/ui/qml/components/PipelineRail.qml`
  - Step chain and rerun anchor.

- `src/modori/ui/qml/components/GuideRail.qml`
  - Guided-mode draft flow.

- `src/modori/ui/qml/components/ExplainPopover.qml`
  - Knowledge-library explanation popover.

- `src/modori/ui/qml/dialogs/ImportDialog.qml`
  - Import options and preview.

- `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
  - Report options and export command.

- `src/modori/ui/qml/theme/Theme.qml`
  - Deep teal/gold/orange tokens, reduce-effects switching.

### New tests

- `tests/ui/test_thin_shell_guards.py`
- `tests/ui/test_patches.py`
- `tests/ui/test_controller.py`
- `tests/ui/test_worker.py`
- `tests/ui/test_table_provider.py`
- `tests/ui/test_models.py`
- `tests/ui/test_qml_resources.py`
- `tests/ui/test_help_keys.py`
- `tests/ui/test_security_privacy.py`
- `tests/ui/test_smoke_qml.py`

---

## Gate 1: 명세/계획 고정

**Purpose:** Freeze the implementation plan and make the stop rules explicit.

**Files:**
- Create: `docs/specs/04-ui-shell-commercial-v1-plan.md`

**Steps:**

- [ ] Write this implementation plan.
- [ ] Confirm the plan follows the nine approved gates.
- [ ] Confirm no code implementation is mixed into Gate 1.
- [ ] Run the standard verification commands twice.
- [ ] Stop if any existing test fails.

**Gate 1 pass criteria:**
- This file exists and contains concrete gates, files, commands, and stop rules.
- Full tests pass twice.
- No implementation files have been changed in this gate.

---

## Gate 2: UI architecture skeleton

**Purpose:** Create the QML-based UI package and launcher without implementing business
logic beyond safe startup.

**Files:**
- Modify: `src/modori/app.py`
- Modify: `pyproject.toml`
- Create: `src/modori/ui/__init__.py`
- Create: `src/modori/ui/resources.py`
- Create: `src/modori/ui/strings.py`
- Create: `src/modori/ui/qml/Main.qml`
- Create: `src/modori/ui/qml/screens/EntryScreen.qml`
- Create: `src/modori/ui/qml/screens/WorkScreen.qml`
- Create: `src/modori/ui/qml/theme/Theme.qml`
- Create: `tests/ui/test_qml_resources.py`
- Modify: legacy app tests that import `ModoriWindow`

**Required behavior:**
- `modori.app:main` launches `QGuiApplication` and `QQmlApplicationEngine`.
- QML root loads from package resources.
- `MODORI_REDUCE_EFFECTS=1` is available to QML as initial reduce-effects state.
- Legacy QWidget `ModoriWindow` is removed or replaced by a minimal compatibility test
  target that does not launch the old UI.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_qml_resources.py -q -p no:cacheprovider
rg -n "QMainWindow|QWidget|QApplication" src\modori\app.py src\modori\ui
```

Expected `rg` result: no matches for QWidget launcher classes in production UI code.

**Stop conditions:**
- QML loads only from the working directory.
- Installed package cannot find `Main.qml`.
- Legacy QWidget remains the default launched UI.

---

## Gate 3: controller/DTO/worker/patch core

**Purpose:** Build the non-visual correctness core before binding rich UI screens.

**Files:**
- Create: `src/modori/ui/contracts.py`
- Create: `src/modori/ui/patches.py`
- Create: `src/modori/ui/worker.py`
- Create: `src/modori/ui/controller.py`
- Create: `src/modori/ui/security.py`
- Create: `tests/ui/test_patches.py`
- Create: `tests/ui/test_worker.py`
- Create: `tests/ui/test_controller.py`
- Create: `tests/ui/test_thin_shell_guards.py`

**Required behavior:**
- `CommandResult` includes `ok`, `message_ko`, `error_code`, `run_id`,
  `pipeline_version`, `changed_step_ids`, and `result_ids`.
- Controller exposes `mode`, `reduceEffects`, `status`, `stale`, `lastError`,
  `stepsModel`, `dataModel`, `variableModel`, and `resultsModel`.
- Worker queue is serialized.
- Older `run_id`/`pipeline_version` results cannot overwrite newer controller state.
- Patch parsing rejects unknown fields and wrong types.
- Invalid patch does not mutate pipeline.
- UI guard rejects forbidden statistical imports and reduction calls.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_patches.py tests\ui\test_worker.py tests\ui\test_controller.py tests\ui\test_thin_shell_guards.py -q -p no:cacheprovider
rg -n "^\s*(from|import)\s+(numpy|pandas|scipy|statsmodels|pingouin|factor_analyzer|sklearn|statistics|math)(\.|\s|$)" src\modori\ui
```

Expected `rg` result: no forbidden statistical imports in production UI code.

**Stop conditions:**
- Controller computes or formats statistics.
- Worker results can race and overwrite newer state.
- Step patch dicts silently ignore unknown fields.

---

## Gate 4: lazy table/import/variable binding

**Purpose:** Bind data and variable views through lazy models without exposing raw
dataframes to QML/UI.

**Files:**
- Create: `src/modori/ui/table_provider.py`
- Create: `src/modori/ui/models.py`
- Modify: `src/modori/ui/controller.py`
- Create: `tests/ui/test_table_provider.py`
- Create: `tests/ui/test_models.py`
- Extend: `tests/ui/test_controller.py`

**Required behavior:**
- Data model uses `TableProvider` only.
- Variable model exposes labels, measures, value labels, missing codes, and display type.
- Import creates a new session by default.
- Import failure leaves previous session untouched.
- Cancelled import confirmation leaves previous session untouched.
- Deterministic row ids are available for sources without stable ids.
- Direct cell edit remains disabled unless `DataCellPatch` is fully backed by a Step.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_table_provider.py tests\ui\test_models.py tests\ui\test_controller.py -q -p no:cacheprovider
rg -n "\.iloc\[|\.iloc\(|\.loc\[|\.loc\(|\.dtypes|\.isna\(|\.describe\(|\.groupby\(|\.agg\(|\.mean\(|\.std\(|\.var\(" src\modori\ui
```

Expected `rg` result: no raw dataframe or reduction use in production UI code.

**Stop conditions:**
- UI model materializes a full cell matrix for large data.
- QML/UI receives raw dataframe objects.
- Import silently preserves incompatible downstream Steps.

---

## Gate 5: QML work screen

**Purpose:** Implement the main work shell and visible rerun anchor.

**Files:**
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Create: `src/modori/ui/qml/components/DataTable.qml`
- Create: `src/modori/ui/qml/components/VariableTable.qml`
- Create: `src/modori/ui/qml/components/PipelineRail.qml`
- Create: `src/modori/ui/qml/components/GuideRail.qml`
- Create: `src/modori/ui/qml/components/LoadingOverlay.qml`
- Modify: `src/modori/ui/controller.py`
- Create: `tests/ui/test_smoke_qml.py`

**Required behavior:**
- Header shows Modori, 데이터/분석/보고서 menus, 안내/표준 segmented control, 설명
  mode toggle, and reduce-effects state.
- `SplitView` contains guide rail, data/variable tabs, and results placeholder panel.
- Pipeline rail shows Step chain and `다시 실행`.
- Switching 안내/표준 changes exposure only and does not modify Steps.
- `rerun()` goes through the controller and worker queue.
- Running state shows `계산 중`; stale previous results are visually marked.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_smoke_qml.py tests\ui\test_controller.py -q -p no:cacheprovider
```

**Stop conditions:**
- QML calls engine modules directly.
- Mode switching changes pipeline Steps.
- Recompute runs synchronously on the UI thread.

---

## Gate 6: results/report binding

**Purpose:** Render engine output without reformatting and export reports through
`ReportStep`.

**Files:**
- Create: `src/modori/ui/qml/components/ResultsPanel.qml`
- Create: `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- Create: `src/modori/ui/results.py`
- Modify: `src/modori/ui/contracts.py`
- Modify: `src/modori/ui/controller.py`
- Extend: `tests/ui/test_controller.py`
- Create: `tests/ui/test_results_report_binding.py`

**Required behavior:**
- Result DTOs use `table_for`, `prose_for`, and engine-rendered chart paths.
- QML renders DTO strings as-is.
- Missing chart file shows `그림 파일을 찾을 수 없습니다`.
- Report export calls `ReportStep` and reports success only after output path exists.
- UI does not write `.docx` itself.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_results_report_binding.py tests\ui\test_controller.py -q -p no:cacheprovider
rg -n "Document\\(|docx|add_paragraph|add_table|save\\(" src\modori\ui
```

Expected `rg` result: no UI-owned `.docx` writing.

**Stop conditions:**
- UI reconstructs APA strings or p-value formatting.
- Report export bypasses engine `ReportStep`.
- Chart lifecycle can delete user-selected export files.

---

## Gate 7: 설명 모드/library binding

**Purpose:** Connect explainable UI terms to the local knowledge library.

**Files:**
- Create: `src/modori/ui/help_keys.py`
- Create: `src/modori/ui/qml/components/ExplainPopover.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/controller.py`
- Create: `tests/ui/test_help_keys.py`

**Required behavior:**
- Every explainable result label has an `entity_key`.
- UI-only explainable labels are registered in `UI_HELP_KEYS`.
- Non-explainable chrome labels are explicitly marked `not_explainable`.
- `explain(entityKey, language)` uses `resolve_help_key` and `library.explain`.
- Missing library resolution returns `library_missing` and does not fabricate text.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_help_keys.py tests\test_knowledge_library.py -q -p no:cacheprovider
rg -n "OpenAI|LLM|chat|completion|ResponsesAPI|CompletionsAPI" src\modori\ui
```

Expected `rg` result: no AI/model path in explanation UI.

**Stop conditions:**
- UI invents explanation text outside the library.
- Explainable label has no resolvable help key.
- Library missing state is hidden.

---

## Gate 8: 보안/프라이버시/성능/accessibility guard

**Purpose:** Harden the shell against privacy leaks, performance regressions, and basic
accessibility failures.

**Files:**
- Modify: `src/modori/ui/security.py`
- Modify: `src/modori/ui/strings.py`
- Modify: QML files under `src/modori/ui/qml/`
- Create: `tests/ui/test_security_privacy.py`
- Extend: `tests/ui/test_thin_shell_guards.py`
- Extend: `tests/ui/test_smoke_qml.py`

**Required behavior:**
- No telemetry, remote assets, network calls, or remote QML URLs.
- `MODORI_REDUCE_EFFECTS=1` disables blur/shader/animation before QML loads.
- UI chrome strings come from the string catalog.
- Core controls have Korean accessible names.
- Keyboard rules for Esc/Enter and table navigation are implemented for core flows.
- Large synthetic table model remains lazy.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_security_privacy.py tests\ui\test_thin_shell_guards.py tests\ui\test_smoke_qml.py tests\ui\test_models.py -q -p no:cacheprovider
rg -n "http://|https://|WebEngine|XmlHttpRequest|fetch\\(|^\s*(from|import)\s+(requests|httpx|urllib|socket|webbrowser)(\.|\s|$)" src\modori\ui src\modori\app.py
```

Expected `rg` result: no production network/remote asset paths.

**Stop conditions:**
- Any runtime network path appears.
- Reduce-effects mode still requires shader/blur.
- Accessibility labels are absent from core controls.

---

## Gate 9: end-to-end smoke/QA hardening

**Purpose:** Prove the commercial v1 flow works locally and identify remaining
environment-only risks honestly.

**Files:**
- Extend: `tests/ui/test_smoke_qml.py`
- Create: `tests/ui/test_end_to_end_ui_flow.py`
- Create: `docs/specs/04-ui-shell-commercial-v1-qa.md`

**Required behavior:**
- App launches to entry.
- Entry opens a data file through the controller.
- Work screen shows data/variable/result surfaces.
- Rerun refreshes results.
- Report export returns an output path.
- 안내 and 표준 modes produce the same Steps for the same committed action.
- Failure states are visible and recoverable.
- QA document records automated evidence, manual smoke evidence, and unresolved
  environment risks.

**Gate-specific checks:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m compileall -q src tests
rg -ni "tongtong" src tests pyproject.toml
rg -n "QMainWindow|QWidget|QApplication" src\modori\app.py src\modori\ui
rg -n "http://|https://|WebEngine|XmlHttpRequest|fetch\\(|^\s*(from|import)\s+(requests|httpx|urllib|socket|webbrowser)(\.|\s|$)" src\modori\ui src\modori\app.py
```

Expected:
- Full suite green twice.
- `tongtong` residue: no matches.
- Legacy QWidget launcher: no matches in production UI.
- Network/remote asset scan: no production matches.

**Stop conditions:**
- Any v1 core flow requires developer intervention.
- Any result number/prose/table differs from engine/reporting output.
- Any privacy promise is unverifiable.
- Any failure state hides stale or invalid results.

---

## Commercial v1 completion criteria

The project can be called commercial-ready v1 only when all are true:

- Gates 1 through 9 are complete in order.
- Every gate has two consecutive full green test runs.
- `modori.app:main` launches the QML shell by default.
- The UI thin-shell guard is active and green.
- The controller worker discards stale/out-of-order results.
- Data and variable views are lazy and do not expose raw dataframe APIs to UI/QML.
- All Step edits are typed, validated, and pipeline-backed.
- Results/report UI renders engine DTO output without reformatting numbers.
- 설명 모드 resolves all explainable terms through the local knowledge library.
- No runtime network/model/telemetry/remote asset path exists.
- Reduce-effects mode launches and remains functional.
- End-to-end local smoke covers entry, import, work screen, rerun, results, explanation,
  and report export.
- Remaining environment risks, if any, are documented rather than hidden.
