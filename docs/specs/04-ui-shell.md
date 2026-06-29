# Modori — UI Shell Spec #04 (desktop app)
## Draft for owner review before handoff to Codex

> **Purpose.** Define the desktop UI shell that sits on top of the validated headless
> engine (slices #01–#02) and the knowledge library (#03). The UI is a **thin shell**:
> it creates/edits pipeline Steps, triggers re-run, and renders engine outputs + library
> explanations. It does **no statistics itself** (P2/P4).
>
> **Status:** IMPLEMENTATION-HARDENING DRAFT. Mockups are agreed (entry, loading,
> work, variable view, report export, .sav import). This spec is now an
> implementation contract draft: it must be concrete enough that an agent can build
> the shell without inventing state, statistics, or coverage rules.
>
> Language: spec/code English (POLICY §1). All UI strings Korean-first (product content).
> Brand name: **Modori (모도리)**.

---

## PART 0 — Non-negotiable UI principles
- **U1. The UI never computes statistics.** Every analysis/number comes from the engine
  (Steps → AnalysisResult). The UI builds Step params, calls the pipeline, and renders
  results. No stats math in the UI layer (upholds P2/P4).
- **U2. Everything is a pipeline edit (P1).** User actions (import, recode, choose a
  test, edit predictors) create or edit Steps; the visible "다시 실행 (re-run)" maps to
  `pipeline.recompute`. The UI reflects the recompute graph; it does not hold a parallel
  source of truth.
- **U3. A/B are one engine, exposure-only (P3).** 안내(guided) and 표준(standard) produce
  the SAME Steps; they differ only in how params get filled (guided rail vs menu/dialog).
- **U4. Glass on chrome, flat on data.** Glassmorphism (blur/translucency/gradient) is
  for chrome only — splash, entry, header tint, guide card, dialogs, 설명-mode popovers.
  Data-dense surfaces (data view, variable view, results tables) are flat and
  high-contrast for legibility.
- **U5. Degrade gracefully on weak hardware.** A "가벼운 모드 (reduce effects)" toggle +
  automatic weak-hardware detection disables blur and animation and uses a static
  gradient. The app must be fully usable with all effects off. (Target: old social-
  science lab PCs.)
- **U6. Explanations are deterministic (no AI).** 설명 모드 and educational notes pull
  from the knowledge library (#03) via `resolve_help_key` / `explain`. No model.

### 0.1 Thin-shell boundary (testable)
For this slice, the UI/controller layer means `src/modori/ui/**`, QML files, and the
QML launcher path in `src/modori/app.py`. The boundary is deliberately narrow:

- Allowed responsibilities: collect user intent, create/edit pipeline Steps, call the
  engine, expose Qt models, render engine/report DTOs, route library explanations.
- Forbidden responsibilities: any statistical computation, descriptive reduction,
  p-value/effect-size/CI calculation, test selection based on numeric outcomes, or
  numeric formatting beyond displaying engine-provided strings.
- Forbidden imports in `src/modori/ui/**`: `numpy`, `pandas`, `scipy`, `statsmodels`,
  `pingouin`, `factor_analyzer`, `sklearn`, `statistics`, and `math`. A UI model may
  hold engine-owned tabular objects but must not import these libraries or call their
  statistical/reduction APIs.
- Forbidden calls in `src/modori/ui/**`: `.mean(`, `.median(`, `.std(`, `.var(`,
  `.corr(`, `.cov(`, `.sem(`, `.quantile(`, `.describe(`, `.groupby(`, `.agg(`,
  `.sum(` for numeric summaries, and any direct p-value/effect-size formula.
- Required guard: an AST/code-check test fails if the UI layer imports forbidden
  modules or uses forbidden reduction calls. If a display-only exception is ever
  needed, it must be justified in this spec before code is changed.

### 0.2 Source of truth
There is exactly one source of truth: `Pipeline` + engine `StepResult`s.

- QML state is view state only: selected tab, selected step, panel sizes, toggles,
  popover visibility, and transient command status.
- Controller state mirrors engine state but must not fork it. After any Step edit,
  data edit, import option change, or variable metadata change, downstream results are
  invalidated through the pipeline and re-pulled after recompute.
- Stale display rule: while recompute is running, prior results may remain visible only
  with a visible `계산 중` overlay; once recompute fails, stale results must be visually
  marked `이전 결과` and the error shown. Silent stale results are not allowed.

### 0.3 Privacy and runtime network boundary
The UI repeats the promise `데이터는 이 컴퓨터를 떠나지 않습니다`; the runtime contract
must make that true.

- No telemetry, analytics beacon, remote logging, remote font loading, remote icon
  loading, CDN asset loading, or model/network call is allowed in this slice.
- QML must load only packaged local assets or Qt built-in primitives.
- Help/explanation content must come only from the local knowledge library.
- External links, if later added to citations, must open only through explicit user
  action and are out of scope for this slice.
- A code check must fail if `src/modori/ui/**` imports or calls obvious network clients
  such as `requests`, `urllib`, `httpx`, `socket`, `webbrowser`, or QML remote URLs.

---

## PART 1 — Technology
- **PySide6**, UI authored in **Qt Quick (QML)** for the shell (enables the glass,
  gradient, animation, and resizable `SplitView` cleanly; QWidgets cannot do glass well).
- **Data grid:** a virtualized QML `TableView` backed by a Python `QAbstractTableModel`
  (data view) and a second model for variable view. Virtualization is required for large
  survey datasets — never instantiate a delegate per cell for the whole table.
- **Backend binding:** a Python controller object exposed to QML (context property /
  `QmlElement`) that wraps the engine: holds the `Pipeline`, exposes models, and
  forwards user intents to Steps. QML calls the controller; the controller calls the
  engine. One-way: QML → controller → engine → results → models → QML.
- **Premium gradient (splash/entry):** QML `ShaderEffect` (GLSL) animated mesh/aurora,
  deep-teal + gold/orange — **deferred polish**, gated behind U5 with a static gradient
  fallback. Ship a tasteful static/simple-animated gradient first; shader later.
- **Charts:** the engine already renders matplotlib figures to files (PNG/SVG/EPS). v1:
  the UI displays the engine-produced figure image in the results panel. (A future
  native interactive chart layer is out of scope.)

### 1.1 Package and launch contract
- The existing console entry point remains `modori = "modori.app:main"`.
- `src/modori/app.py` becomes the thin launcher: create `QGuiApplication` /
  `QQmlApplicationEngine`, register/expose the controller, load the root QML, and exit
  with the Qt return code.
- New UI code lives under `src/modori/ui/`. QML assets live under
  `src/modori/ui/qml/`.
- The legacy QWidget window may exist only as a temporary compatibility shim during the
  first implementation task. The reviewer gate for this slice requires the QML work
  skeleton to be the launched default.
- Existing engine modules (`core`, `steps`, `workflow`, `results`, `knowledge`) are not
  moved into the UI package.

### 1.2 QML packaging contract
- QML and UI assets under `src/modori/ui/qml/` must be included in editable installs and
  built wheels through package-data configuration.
- The launcher resolves QML by package resource path, not by the current working
  directory. Launching from `C:\WINDOWS\System32` must work after editable install.
- Tests must verify that the root QML resource exists through the same lookup path used
  by `modori.app:main`.
- No generated UI cache, screenshots, or user data is packaged.

---

## PART 2 — Brand & visual system
- **Name/wordmark:** "Modori" (Latin) with "모도리" available as subtitle.
- **Brand color:** deep teal (base, e.g. ~#0F6E56 / #0B4A43) warmed by gold + orange in
  gradients. Header = solid deep teal, white text. Secondary chrome = teal-tinted glass.
- **Type/spacing/icons:** follow a clean flat system (sentence case Korean, two weights,
  hairline borders, generous whitespace). Tabler-style outline icons.
- **Dark mode:** support; the brand teal header stays constant; surfaces adapt.
- Final color tokens to be locked with the owner; deep teal + gold/orange is the agreed
  direction.

---

## PART 3 — Screens & states

### 3.1 Loading (splash)
Teal+gold/orange glass gradient; Modori wordmark + tagline; progress + status
("통계 엔진을 준비하고 있어요"); privacy line ("데이터는 이 컴퓨터를 떠나지 않습니다").
Static fallback under 가벼운 모드.

### 3.2 Entry (start)
Same glass gradient. Two starting paths — **안내 모드** (featured) / **표준 모드**
(sets the initial A/B exposure). 데이터 열기 (.sav · .csv · .xlsx) → §3.6 import dialog.
최근 항목 list. Footer: 무료 · 오픈소스 · 로컬.

### 3.2.1 Recent files policy
- Recent files are local-only convenience state, never part of the pipeline.
- The list stores absolute paths plus display names in the app settings file. It stores
  no dataset contents, variable values, or analysis results.
- Missing files remain visible with `파일을 찾을 수 없음` and can be removed by the user.
- A setting disables recent-file persistence; when disabled, the list is cleared.
- Recent-file paths are never included in exported reports.

### 3.3 Work screen (the main window)
- **Header (solid deep teal, white text):** Modori · 데이터/분석/보고서 menus ·
  [안내 | 표준] segmented · 설명 모드 toggle.
- **Resizable panels (QML SplitView, draggable handles):**
  - **Guide rail (left):** present in 안내 mode (collapsible; hidden by default in 표준).
    Hosts the guided flow (§4).
  - **Data panel (center):** tabs 데이터 보기 / 변수 보기 (§3.4, §3.5).
  - **Results panel (right):** APA table + auto sentence + figure + "왜 이 검정?" note.
- **Pipeline rail (bottom):** the Step chain (가져오기 → 역코딩 → 합산 → 신뢰도 →
  집단비교 → 보고서) + **다시 실행**. Selecting a step shows/edits its params; editing
  triggers recompute of downstream steps (P1) and refreshes results.

### 3.3.1 Controller state and command contract
The controller is the only object QML calls for engine work. It exposes Qt properties
and invokable commands with stable result shapes.

Required read-only properties:
- `mode`: `"guided"` or `"standard"`.
- `reduceEffects`: boolean.
- `status`: `"empty"`, `"ready"`, `"running"`, or `"error"`.
- `stale`: boolean; true only when visible results do not match the current pipeline.
- `lastError`: localized Korean error text, empty when there is no active error.
- `stepsModel`: Step chain model for the bottom rail.
- `dataModel`: virtualized respondent-by-variable table model.
- `variableModel`: virtualized variable metadata table model.
- `resultsModel`: result cards/tables/prose/figures as display DTOs.

Required commands:
- `setMode(mode: str) -> CommandResult`: changes exposure only; must not modify Steps.
- `setReduceEffects(enabled: bool) -> CommandResult`: changes chrome effects only.
- `openDataFile(path: str, options: ImportOptions) -> CommandResult`: creates or
  replaces the import Step and recomputes.
- `updateStep(stepId: str, patch: object) -> CommandResult`: edits one Step, invalidates
  downstream results, recomputes, and refreshes models.
- `rerun() -> CommandResult`: recomputes the current pipeline without changing Steps.
- `exportReport(options: ReportExportOptions) -> CommandResult`: delegates to
  `ReportStep`; the UI does not write `.docx` itself.
- `explain(entityKey: str, language: "ko" | "en") -> ExplainResult`: resolves through
  the knowledge library only.

`CommandResult` shape:
- `ok: bool`.
- `message_ko: str`.
- `error_code: str | null`; stable machine-readable code such as
  `"invalid_file"`, `"invalid_step_patch"`, `"engine_error"`, `"library_missing"`.
- `run_id: int | null`; set when the command starts or completes engine execution.
- `pipeline_version: int`; monotonically increasing controller-side version.
- `changed_step_ids: list[str]`.
- `result_ids: list[str]`.

Commands must catch expected user errors and return `CommandResult`. Unexpected
exceptions may still fail tests, but production UI must display them as `engine_error`
with no traceback in the visible UI.

### 3.3.2 Controller execution model
Import, recompute, and report export can be slow. They must not block the QML/UI
thread.

- The controller runs engine work in a serialized worker queue. Only one engine job is
  active at a time.
- Every engine job receives a monotonically increasing `run_id`.
- Every committed pipeline edit increments `pipeline_version`.
- Worker jobs may emit progress/status, but model mutation and Qt signals happen on the
  Qt main thread.
- Out-of-order protection: when a worker result returns, the controller applies it only
  if its `run_id` and `pipeline_version` match the latest expected values. Older worker
  results are discarded and may only update debug logs.
- Cancellation policy for v1: starting a newer recompute marks older queued work
  obsolete. If an active engine call cannot be interrupted safely, let it finish and
  discard its result by `run_id`.
- The UI displays `계산 중` while status is `"running"` and disables conflicting commands
  that would produce ambiguous pipeline edits.

### 3.3.3 Pipeline edit transaction model
The controller must choose correctness over optimistic UI mutation.

- Step patches are parsed and schema-validated before they touch the live pipeline.
- If patch validation fails, the live pipeline and `pipeline_version` do not change.
- For valid patches, v1 uses commit-then-recompute: commit the Step edit, increment
  `pipeline_version`, mark downstream results stale, enqueue recompute.
- If recompute fails, keep the edited pipeline visible, mark affected results `이전 결과`,
  set `status = "error"`, and expose the Step with `invalid_or_failed` state. Do not
  silently roll back the user's explicit edit.
- A future copy-on-write recompute may be added, but it must preserve the same visible
  semantics unless this spec changes.

### 3.3.4 Patch schemas
`updateStep(stepId, patch: object)` accepts only typed patch objects. Unknown fields are
load errors, not ignored.

Required patch kinds:
- `ReliabilityPatch`: `item_keys: list[str]`, `language: "ko" | "en"`.
- `ComparisonPatch`: `outcome_key: str`, `group_key: str`, `group_a: str | number`,
  `group_b: str | number`, `language: "ko" | "en"`.
- `RegressionPatch`: `outcome_key: str`, `predictor_keys: list[str]`,
  `include_intercept: bool`, `language: "ko" | "en"`.
- `ReportPatch`: `language: "ko" | "en"`, `include_reliability: bool`,
  `include_comparison: bool`, `include_regression: bool`, `include_figures: bool`.
- `VariableMetadataPatch`: `variable_key: str`, optional `label: str`,
  optional `measure: "scale" | "ordinal" | "nominal"`, optional `value_labels`,
  optional `missing_codes`, optional `display_type`.
- `DataCellPatch`: `row_id: str`, `variable_key: str`, `new_value`.

Patch validation rules:
- Empty `item_keys` or `predictor_keys` are invalid.
- A variable key must exist in the current imported dataset.
- A grouping patch must identify two distinct groups.
- Unknown fields, missing required fields, and wrong primitive types return
  `invalid_step_patch`.
- Patch parsing lives in Python controller code, not QML.

### 3.4 Data view
Virtualized spreadsheet (respondents × variables), SPSS-familiar. Flat,
high-contrast.

Data boundary:
- QML and UI table models must not receive raw `pandas.DataFrame` objects.
- The controller exposes a narrow `TableProvider` protocol: `row_count`,
  `column_count`, `cell(row_index, column_index)`, `column_header(column_index)`,
  `row_id(row_index)`, and `variable_key(column_index)`.
- `TableProvider` may be backed by the engine dataset internally, but the UI model
  cannot call dataframe APIs such as `.iloc`, `.columns`, `.dtypes`, `.isna`, or
  reductions.
- Import assigns deterministic internal `row_id` values when the source file lacks a
  stable row identifier. Row ids must be stable for a given imported file and import
  options.

Editing rule:
- Cell editing is allowed only when backed by a reproducible pipeline Step.
- If a `CellEditStep`/`DataPatchStep` is not implemented yet, the data grid is read-only
  and shows a Korean tooltip: `셀 직접 수정은 재현 가능한 편집 단계가 준비된 뒤 활성화됩니다.`
- When enabled, a cell edit records row identity, variable key, previous display value,
  new value, timestamp-free deterministic patch content, and the target import Step id.
  It must not mutate the source table in place outside the pipeline.
- Every edit triggers downstream invalidation and recompute through the controller.

### 3.5 Variable view
One row per variable: 이름 · 레이블 · 측정수준 (척도/순서/명목) · 값 레이블 · 결측 · 유형.
Editing measurement level can change which analyses are recommended (guided flow).
Missing codes here feed the engine's compute-time masking.

Variable metadata edit rule:
- Variable edits are Step-backed metadata patches, not direct mutations of the current
  dataset object.
- A metadata patch may change label, measure, value labels, user-missing codes, and
  display type. It must not change raw observed values.
- Measurement-level changes affect recommendations only before a test Step is created,
  or by explicitly editing the existing test Step. The UI must not silently replace an
  analysis Step because a variable measure changed.
- If a metadata edit makes an existing downstream Step incompatible, the controller marks
  that Step `invalid_step` and shows the specific missing/incompatible variable. It must
  not silently rewrite the Step to a different analysis.

### 3.6 Import dialog (.sav / .csv / .xlsx)
Shows the file, detected variable/case counts, "값 레이블·결측 코드 그대로 가져오기"
(for .sav, via pyreadstat metadata), and a preview of detected variables + inferred
measurement levels. [취소] / [가져오기]. (.csv has no metadata → measures inferred,
correctable in variable view.)

Import contract:
- QML never parses data files. It passes the path/options to the controller.
- `.sav`: preserve pyreadstat variable labels, value labels, user-missing codes/ranges
  when the user leaves `값 레이블·결측 코드 그대로 가져오기` enabled.
- `.csv`/`.xlsx`: infer variable names and simple measures through the engine/import
  path, then allow correction in variable view through metadata patches.
- Import preview rows are display-only and come from the controller model. The preview
  must not create a second parser in QML.

Import/session policy:
- `openDataFile` starts a new analysis session by default: it creates a new import Step
  and clears downstream analysis/report Steps after explicit confirmation if unsaved
  pipeline edits exist.
- A future `replace import and preserve compatible steps` mode is out of scope for v1.
- If the user cancels confirmation, no pipeline state changes.
- Import failure leaves the previous session untouched and returns `invalid_file` or
  `engine_error`.

### 3.7 Report export
Options (언어 ko/en, 포함 항목: 신뢰도/집단비교/그림) → **Word(.docx) 내보내기** (engine
ReportStep) + document preview (auto sentence, APA table, figure). Note: figures saved
as PNG 300dpi · SVG · EPS for journal submission.

Preview contract:
- The preview uses the same display DTOs that the results panel uses: engine/reporting
  `table_for`, `prose_for`, and engine-rendered chart paths.
- The UI must not reformat p-values, confidence intervals, coefficients, degrees of
  freedom, or APA punctuation for preview.
- Export success is reported only after `ReportStep` returns the output path.

---

## PART 4 — A/B modes & the guided flow
- **안내 (guided):** the guide rail walks the decision tree (slice #01 A-mode): plain-
  language intent ("무엇을 알고 싶으세요?") → narrow by variable types (inferred, not
  asked) → recommend a test (with "왜 이 검정?" from the library) → run. Educational
  notes shown proactively (push).
- **표준 (standard):** guide rail collapsed; analyses chosen from the 분석 menu/dialogs.
  Same Steps produced; educational notes available on demand (pull).
- Switching modes never changes results — only exposure (U3). Surfacing posture per the
  recorded surfacing principle (A push / B pull / C off; default depth; density).

### 4.1 Guided recommendation contract
Guided mode recommends analyses from declared metadata and explicit user intent, not
from computed outcomes.

Minimum v1 decision table:
- Intent `두 집단 평균 차이`: one numeric/scale outcome + one two-level grouping
  variable → independent-samples t-test family. If equal-variance assumption is not
  satisfied by the engine result, the displayed result may be Welch; the guide must not
  pre-compute the assumption itself.
- Intent `척도 신뢰도`: two or more scale items → reliability Step.
- Intent `여러 변수로 예측`: one numeric/scale outcome + one or more predictors →
  multiple regression Step.
- Unsupported combinations produce a clear `아직 지원하지 않는 조합입니다` message and
  create no partial analysis Step.

The first implementation may include only the analyses already supported by the
validated engine. Adding new analyses is out of scope for this slice.

Guide draft state:
- Guided-mode wizard selections are draft UI state until the user clicks an explicit
  run/apply action.
- Switching 안내 ↔ 표준 discards uncommitted guide draft state after confirmation, or
  preserves it only as view draft; it must not create partial Steps.
- Only committed guide actions create/edit Steps. Draft state never affects engine
  results or report export.

---

## PART 5 — 설명 모드 (explain mode) — wires to the knowledge library (#03)
- A toggle in the header. When ON, explainable terms (table headers, result fields,
  test names, diagnostics) are interactive; right-click / click opens a **glass popover**.
- The popover content = `library.explain(slug, language)` resolved via
  `resolve_help_key(entity_key)`. Shows: title, plain-first summary, "더 자세히" (deeper
  layers: interpretation/when_to_use/pitfalls), and the source citation.
- **Layered surfacing:** popover opens at `summary` (plainest) for 안내/beginners; B/C may
  open deeper. The library guarantees every engine-emitted term resolves (coverage tests
  in #03), so the UI can always explain what it shows.
- 설명 모드 ≠ 안내 모드: 안내 *leads the analysis*; 설명 *defines the terms*. (Naming was
  changed from "질문 모드" to remove this confusion.)

### 5.1 UI-rendered vocabulary contract
#03 guarantees coverage for engine-emitted terms. The UI must additionally prove that
every help key it renders resolves.

- Every result table header, diagnostic label, chart label, test name, effect name, and
  guide recommendation label that is interactive in 설명 모드 carries an `entity_key`.
- UI-only labels must be registered in `UI_HELP_KEYS` or explicitly marked
  `not_explainable`.
- A test builds representative result DTOs for reliability, comparison, regression,
  import preview, variable view, and report preview; it asserts every explainable
  `entity_key` resolves through `resolve_help_key` and `library.explain`.
- The UI may display a non-interactive label without a help key only when the label is
  purely navigational chrome, e.g. `파일`, `보고서`, `다시 실행`.

---

## PART 6 — Performance & accessibility (U5)
- **가벼운 모드 (reduce effects):** a setting (and auto-enabled on detected weak hardware)
  that turns off backdrop blur and gradient animation, using a static gradient/solid
  surfaces. All functionality remains.
- Table virtualization mandatory; lazy-load large files; keep the data path off the GPU.
- Contrast: data/results text meets legibility on flat surfaces; glass never sits behind
  body numbers.
- Keyboard navigation and screen-reader labels for core flows (at least: menus, dialog
  fields, table navigation).

### 6.1 Concrete performance rules
- Table models must implement `rowCount`, `columnCount`, `data`, `headerData`, and
  edit methods without converting the full dataset to nested Python lists or prebuilt
  string matrices.
- `data(index)` must fetch only the requested cell and return display-ready text or a
  simple scalar for Qt display roles.
- The data view must remain usable for at least 10,000 rows × 200 variables on a normal
  desktop without pre-instantiating all delegates.
- CI tests cover the Python model contract with synthetic large dimensions; manual UI
  smoke covers QML scrolling because exact GPU timing is hardware-dependent.

### 6.1.1 Accessibility minimums
- Every menu action, dialog field, mode toggle, explain toggle, import button, rerun
  button, and export button has an accessible name in Korean.
- Keyboard order follows header → guide rail → data/variable tabs → results panel →
  pipeline rail.
- `Esc` closes dialogs/popovers without changing pipeline state.
- `Enter` activates the focused primary action only when validation passes.
- Data table keyboard navigation supports arrow keys, Home/End, PageUp/PageDown, and
  copy of selected display cells.
- Body text and table text must meet WCAG AA contrast on flat surfaces; glass surfaces
  may not sit behind numeric table values.

### 6.2 Reduce-effects contract
- `MODORI_REDUCE_EFFECTS=1` forces 가벼운 모드 before QML loads.
- The in-app setting persists and can be toggled without restarting.
- Automatic weak-hardware detection is advisory for v1: enable reduce effects when Qt
  reports a software renderer or when animated effects fail to initialize. The app must
  not refuse to launch because detection is unavailable.
- With reduce effects on, all blur, shader, and gradient animation are disabled; layout,
  data grid, explanations, and report export remain identical.

### 6.3 UI string ownership
- UI chrome strings live in one Python/QML-accessible string catalog for v1.
- Engine prose, APA tables, and report text are not duplicated in the UI string catalog.
- QML may contain object ids and layout labels, but user-visible Korean/English copy
  should come from the catalog unless it is engine/reporting output.
- Tests may assert important fixed strings from the catalog; they must not assert
  duplicated engine prose in QML.

---

## PART 7 — Engine/library binding (the thin-shell contract)
- Controller exposes: open/import (→ ImportStep), data/variable models, the Step list +
  per-step param editors, `run()` (→ recompute), current results (ReliabilityResult /
  ComparisonResult / RegressionResult), report export (→ ReportStep), and library lookup
  (`resolve_help_key`, `explain`).
- Rendering: results panel renders `table_for(result)` (tables), the auto prose
  (`prose_for`), the engine figure image (from `chart_spec` render), and educational
  notes. The UI must not reformat numbers itself beyond display — values come formatted
  from the engine/reporting layer.
- Re-run: any Step edit or data change calls the engine recompute; the UI re-pulls
  results. No stale views (the engine's dirty-graph guarantees correctness).

### 7.1 Display DTO contract
The controller converts engine results into display DTOs so QML does not inspect
statistical internals.

`DisplayResult` fields:
- `result_id: str`.
- `kind: "reliability" | "comparison" | "regression" | "report"`.
- `title_ko: str`, `title_en: str`.
- `prose_ko: str`, `prose_en: str`; from `prose_for`.
- `tables: list[DisplayTable]`; from `table_for`.
- `chart_paths: list[str]`; engine-rendered files only.
- `notes: list[DisplayNote]`; library-backed educational notes.

`DisplayTable` fields:
- `caption_ko: str`, `caption_en: str`.
- `columns: list[DisplayColumn]`, where each column has `label`, `entity_key`, and
  `not_explainable`.
- `rows: list[list[str]]`; already formatted for display by the reporting layer.

QML may choose layout, truncation, wrapping, and popover position. It must not parse the
strings to derive new numbers or reformat values.

### 7.2 Chart lifecycle contract
- Chart files are produced only by engine/reporting render functions.
- Each `DisplayResult` contains chart paths for the current `run_id` only.
- When recompute starts, existing chart DTOs are marked stale together with their parent
  result.
- If a chart path is missing at render time, the UI shows `그림 파일을 찾을 수 없습니다`
  and the result remains otherwise usable.
- The controller owns cleanup of obsolete generated chart files under the app cache
  directory. It must not delete user-selected export destinations.

---

## PART 8 — Out of scope (this slice)
- C (expert) mode; network-psychometrics visualization (v1.5).
- Native interactive charts (use engine-rendered figures for now).
- The premium QML shader gradient is *deferred polish* (ship static/simple first).
- New analyses (correlation, ANOVA, EFA, …) — separate engine slices.

---

## PART 9 — Validation & Definition of Done
UI is hard to unit-test fully; require:
- **Thin-shell guard (key test):** assert the UI/controller layer computes no statistics
  — e.g., results shown equal the engine's outputs for a fixture pipeline; the controller
  delegates to the engine (no numeric logic in UI code). A code check / review confirms
  no stats libs imported in the UI layer except for display.
- **Binding tests:** controller round-trips — import → models populate; edit a Step →
  recompute → results update (the re-run anchor, through the UI controller).
- **설명-mode coverage:** every term the results panel renders resolves via
  `resolve_help_key` to a library entry (reuse #03 coverage).
- **가벼운 모드:** app launches and is usable with effects off; no crash without GPU
  acceleration.
- Smoke: app launches to entry; entry → import → work → results → report export runs
  end-to-end in both 안내 and 표준 modes.
- All existing engine/library tests stay green.

Concrete test gates:
- `test_ui_thin_shell_import_guard`: AST scan of `src/modori/ui/**` rejects forbidden
  imports and reduction calls from §0.1.
- `test_controller_delegates_to_engine`: fixture pipeline result displayed by the
  controller is byte-identical to `table_for`/`prose_for` output.
- `test_mode_switch_does_not_change_steps`: switching 안내 ↔ 표준 changes only `mode`.
- `test_step_edit_recomputes_downstream`: editing a Step patch invalidates downstream
  results, calls recompute, and refreshes DTOs.
- `test_ui_help_keys_resolve`: representative UI DTOs expose only resolvable help keys.
- `test_reduce_effects_env_launch`: `MODORI_REDUCE_EFFECTS=1` launches the app without
  blur/shader requirements.
- `test_table_model_is_lazy`: synthetic large model initialization does not materialize
  a full cell matrix and answers sampled cell requests correctly.
- `test_controller_discards_stale_run`: an older worker result cannot overwrite a newer
  `run_id`/`pipeline_version`.
- `test_invalid_patch_does_not_mutate_pipeline`: malformed patch returns
  `invalid_step_patch` and leaves Steps unchanged.
- `test_open_data_file_new_session_policy`: a successful import clears downstream Steps
  only after confirmation; cancel leaves the previous pipeline untouched.
- `test_ui_table_model_uses_table_provider_only`: UI model depends on `TableProvider`
  and not raw dataframe APIs.
- `test_qml_resource_packaged`: root QML loads through package-resource lookup after
  editable install.
- `test_ui_network_guard`: UI layer has no network imports, remote QML URLs, telemetry,
  or remote asset references.

---

## PART 10 — Build order (proposed)
0. Lock controller/display DTO contracts and tests for the thin-shell guard.
1. Controller + model bindings over the existing engine (headless-testable).
2. Work screen skeleton in QML: header, SplitView panels, data view (virtualized table),
   pipeline rail + 다시 실행 — wired to the controller (the re-run anchor visible).
3. Variable view; import dialog (.sav/.csv/.xlsx).
4. Results panel (table + prose + figure + note).
5. 안내-mode guide rail (decision-tree flow) + 표준-mode menu.
6. 설명 모드 popover wired to the library.
7. Entry + loading screens (glass gradient, static first); 가벼운 모드 + weak-HW detect.
8. Report export screen.
9. Premium shader gradient (deferred polish) with fallback.

**Reviewer gate:** review after step 2 (controller + work skeleton + re-run through the
UI) — if the thin-shell contract, DTO boundary, lazy table model, and re-run anchor hold
through the UI, the rest is assembly. Then review 설명-mode wiring (step 6) against the
library.
