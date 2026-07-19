# Royal Blue Bilingual Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompose Modori's entry screen to the approved 37/63 royal-blue and ivory structure and add non-persisted, session-wide Korean/English UI localization without changing routing, analysis, or storage contracts.

**Architecture:** `AppBootstrap` owns the process-local locale and exposes a reactive lookup used by every QML string binding. Static copy lives in equal-key Korean and English catalogs; structured UI presenters select or format the active language for results, recommendations, import review, variable metadata, and controller messages. The entry screen retains its existing signals and Main routing while receiving entry-only components and theme roles.

**Tech Stack:** Python 3.11+, PySide6/Qt Quick QML, pytest, ruff, native QQuickView/QQuickWindow capture.

## Global Constraints

- Structural source: `C:/Users/V/AppData/Local/Temp/codex-clipboard-ed3874a9-fc06-4177-8451-abf62b4c69c3.png`.
- Entry brand `#173B7A`, entry canvas `#F7F3EA`, entry card `#FFFDF8`, entry primary `#2F5DA8`, entry text `#17233A`.
- Left region is 37% of the 1366 x 768 acceptance viewport.
- Language is session-local, defaults to `ko`, and is never serialized.
- Korean and English catalogs have exactly equal keys.
- Casual guidance stays explicitly experimental and never auto-runs.
- Recent rows show only real controller labels; no invented row, column, or time metadata.
- Existing mode, settings, file, recent-file, analysis, project, report, and settings-storage contracts remain intact.

---

### Task 1: Session Locale And Equal-Key Catalogs

**Files:**
- Create: `src/modori/ui/strings_en.py`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/app.py`
- Modify: `tests/ui/test_app_bootstrap.py`
- Modify: `tests/ui/test_qml_string_catalog.py`
- Test: `tests/ui/test_session_localization.py`

**Interfaces:**
- Consumes: current `AppBootstrap.text(key)` and `UI_STRINGS_KO`.
- Produces: `AppBootstrap.language`, `AppBootstrap.setLanguage(language)`, overloaded `AppBootstrap.text(key, language)`, `AppBootstrap.localize(message, language)`, and equal-key `UI_STRINGS_EN`.

- [ ] **Step 1: Write failing locale and catalog tests**

```python
def test_bootstrap_language_is_session_local_and_validated() -> None:
    bootstrap = AppBootstrap()
    seen: list[str] = []
    bootstrap.languageChanged.connect(lambda: seen.append(bootstrap.language))

    assert bootstrap.language == "ko"
    assert bootstrap.setLanguage("en") is True
    assert bootstrap.language == "en"
    assert seen == ["en"]
    assert bootstrap.setLanguage("fr") is False
    assert bootstrap.language == "en"


def test_korean_and_english_catalogs_have_identical_nonempty_keys() -> None:
    assert set(UI_STRINGS_EN) == set(UI_STRINGS_KO)
    assert all(value.strip() for value in UI_STRINGS_EN.values())
    assert all(not re.search(r"[가-힣]", value) for value in UI_STRINGS_EN.values())
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_app_bootstrap.py tests/ui/test_qml_string_catalog.py tests/ui/test_session_localization.py -q`

Expected: FAIL because `UI_STRINGS_EN`, `language`, and `setLanguage` do not exist.

- [ ] **Step 3: Add the complete English catalog**

Add every current Korean key plus the approved entry keys to
`UI_STRINGS_EN`. Use final product copy, including:

```python
ENTRY_STRINGS_EN = {
    "entry.heading": "Get started",
    "entry.guided": "CASUAL MODE",
    "entry.guided_badge": "Experimental candidate",
    "entry.guided_description": (
        "Review experimental analysis candidates step by step. "
        "Nothing runs automatically."
    ),
    "entry.standard": "PRO MODE",
    "entry.standard_description": "Choose the analysis method and variable roles yourself.",
    "entry.open_data": "Open data file",
    "entry.recent": "Recent files",
    "entry.selected": "Selected",
    "entry.language": "Language",
    "language.ko": "한국어",
    "language.en": "English",
}
```

The Korean catalog receives the same keys with Korean values; mode names remain the
approved English labels in both languages.

- [ ] **Step 4: Add the process-local bootstrap API**

```python
class AppBootstrap(QObject):
    languageChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._language = "ko"

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._language

    @Slot(str, result=bool)
    def setLanguage(self, language: str) -> bool:
        normalized = str(language).lower()
        if normalized not in {"ko", "en"}:
            return False
        if normalized != self._language:
            self._language = normalized
            self.languageChanged.emit()
        return True

    @Slot(str, result=str)
    @Slot(str, str, result=str)
    def text(self, key: str, language: str = "") -> str:
        selected = language if language in {"ko", "en"} else self._language
        catalog = UI_STRINGS_EN if selected == "en" else UI_STRINGS_KO
        return catalog.get(key, key)
```

Keep `copyText` unchanged. Do not read or write language through `UiSettingsStore`.

- [ ] **Step 5: Verify GREEN and commit**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_app_bootstrap.py tests/ui/test_qml_string_catalog.py tests/ui/test_session_localization.py -q`

Expected: PASS.

Commit: `git commit -am "feat: add session-wide bilingual UI catalog"` after staging the new files.

### Task 2: Dynamic Session-Wide Presentation

**Files:**
- Create: `src/modori/ui/localization.py`
- Modify: `src/modori/ui/result_binding.py`
- Modify: `src/modori/ui/result_state.py`
- Modify: `src/modori/ui/importing.py`
- Modify: `src/modori/ui/import_flow.py`
- Modify: `src/modori/ui/models.py`
- Modify: `src/modori/ui/preview_models.py`
- Modify: `src/modori/ui/recommendation_controller.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/app.py`
- Test: `tests/ui/test_session_localization.py`
- Test: `tests/ui/test_result_binding.py`
- Test: `tests/ui/test_importing_service.py`
- Test: `tests/ui/test_models.py`

**Interfaces:**
- Consumes: `DisplayResult.title_ko/title_en`, `prose_ko/prose_en`, `DisplayTable.caption_ko/caption_en`, structured import previews, recommendation kind/variable fields, and existing Korean `CommandResult.message_ko`.
- Produces: `UiController.uiLanguage`, `UiController.setUiLanguage(language)`, language-aware presenters, and a UI-only `localize_message` fallback.

- [ ] **Step 1: Write failing dynamic-presentation tests**

```python
def test_result_binding_selects_english_fields() -> None:
    state = presenter.bind([display_result], language="en")
    assert state.summary_text == "English title\nEnglish prose"
    assert state.table_text.startswith("Result table\n")


def test_ui_language_reformats_existing_results_without_rerun(controller) -> None:
    controller.apply_worker_result(successful_display_result)
    controller.setUiLanguage("en")
    assert "English prose" in controller.resultSummary
    assert controller.pipelineVersion == original_pipeline_version
```

Add companion tests that English import previews use `File:`, `Previewed data:`,
`Inference:`, `Header`, `Data`, `Scale`, and `(missing)`; English variable models use
`Name`, `Label`, `Measure`, `Value labels`, `Missing`, and `Type`; and English
recommendation presentation contains no Hangul.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_session_localization.py tests/ui/test_result_binding.py tests/ui/test_importing_service.py tests/ui/test_models.py -q`

Expected: FAIL because presenters are Korean-only and the controller has no UI locale.

- [ ] **Step 3: Implement language-aware result binding**

```python
def bind(self, results: list[Any], *, language: str = "ko") -> ResultBindingState:
    selected = "en" if language == "en" else "ko"
    return ResultBindingState(
        summary_text=self._summarize(results, selected),
        table_text=self._format_tables(results, selected),
        notes_text=self._format_notes(results, selected),
        chart_paths_text=chart_paths_text,
        chart_source_text=self._format_chart_source(chart_paths),
        chart_paths=chart_paths,
    )
```

Select `title_en/prose_en/caption_en` for English and the existing Korean fields for
Korean. Translate only UI-authored note labels; preserve variable names and values.

- [ ] **Step 4: Implement structured import and model formatting**

Give `ImportPreviewService.preview` and its formatting helpers a validated `language`
argument. Store the active language in `UiImportFlow`, and reformat an existing
`table_preview` when `set_language` is called. Give `VariableTableModel` localized
column and measure-label maps, and rebuild preview/current models after a language
change without touching dataset content.

- [ ] **Step 5: Implement recommendation and controller localization**

Add UI-only recommendation methods that take `language` and derive English titles and
deterministic reasons from candidate kind and existing variable fields. Add
`UiController.setUiLanguage` to rebind result state, import preview, and current models,
then emit existing state signals. Connect `AppBootstrap.languageChanged` to this slot in
`main()`:

```python
bootstrap.languageChanged.connect(lambda: controller.setUiLanguage(bootstrap.language))
```

Use stable message/error mappings in `localization.py` for controller-authored
success/error copy. Unknown raw user data and exception details remain unchanged; no
error is suppressed.

- [ ] **Step 6: Verify GREEN and commit**

Run the focused command from Step 2 and expect PASS.

Commit: `git commit -am "feat: localize dynamic UI presentation"` after staging
`localization.py`.

### Task 3: Reactive QML Localization

**Files:**
- Modify: every `src/modori/ui/qml/**/*.qml` file that calls `appBootstrap.text`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/qml/components/DataTable.qml`
- Modify: `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Modify: `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- Modify: `src/modori/ui/qml/dialogs/ResultDetailDialog.qml`
- Test: `tests/ui/test_qml_string_catalog.py`
- Test: `tests/ui/test_qml_runtime_load.py`
- Test: `tests/ui/test_session_localization.py`

**Interfaces:**
- Consumes: `appBootstrap.language`, overloaded `text`, `localize`, and controller language-aware methods.
- Produces: live session-wide QML updates with no screen reload and no stale accessibility labels.

- [ ] **Step 1: Write a failing live QML transition test**

Load `EntryScreen.qml` with a real `AppBootstrap` and controller, locate named Korean
labels, call `bootstrap.setLanguage("en")`, process events, and assert those same QML
objects now expose English `text` and `Accessible.name` values.

- [ ] **Step 2: Run the runtime test and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_session_localization.py::test_live_qml_language_change_updates_visible_and_accessible_copy -q`

Expected: FAIL because current bindings do not observe the language property.

- [ ] **Step 3: Make every catalog lookup reactive**

Mechanically change:

```qml
appBootstrap.text("settings.title")
```

to:

```qml
appBootstrap.text("settings.title", appBootstrap.language)
```

Update the catalog scanner regex to accept and require the second argument. Route
controller error/success strings through `appBootstrap.localize(value,
appBootstrap.language)`. Pass `appBootstrap.language` to result, recommendation,
explanation, and import language-aware methods. Initialize report-export language from
the session language without removing the dialog's explicit language choice.

- [ ] **Step 4: Verify GREEN and commit**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_qml_string_catalog.py tests/ui/test_qml_runtime_load.py tests/ui/test_session_localization.py -q`

Expected: PASS with no QML warnings.

Commit: `git commit -am "feat: reactively localize all QML surfaces"`.

### Task 4: Royal Blue Entry Composition

**Files:**
- Create: `src/modori/ui/qml/components/EntryModeCard.qml`
- Create: `src/modori/ui/qml/components/LanguageChoiceButton.qml`
- Modify: `src/modori/ui/qml/theme/Theme.qml`
- Modify: `src/modori/ui/qml/screens/EntryScreen.qml`
- Modify: `pyproject.toml`
- Test: `tests/ui/test_royal_blue_entry_screen.py`
- Modify: `tests/ui/test_ivory_tiffany_brand_system.py`
- Modify: `tests/ui/test_cream_nacre_visual_system.py`
- Modify: `tests/ui/test_mode_action_surfaces.py`

**Interfaces:**
- Consumes: existing entry signals, controller mode/recent model, settings icon asset, check icon asset, and language API.
- Produces: the approved 37/63 entry layout with stacked, equally weighted mode cards and truthful recent rows.

- [ ] **Step 1: Write failing visual-contract tests**

```python
def test_entry_palette_and_split_are_exact() -> None:
    colors = theme_literal_colors()
    entry = qml_text("screens/EntryScreen.qml")
    assert colors["entryBrand"] == "#173B7A"
    assert colors["entryCanvas"] == "#F7F3EA"
    assert colors["entryCard"] == "#FFFDF8"
    assert colors["entryPrimary"] == "#2F5DA8"
    assert colors["entryText"] == "#17233A"
    assert "width: Math.round(parent.width * theme.entryBrandRatio)" in entry
    assert "readonly property real entryBrandRatio: 0.37" in theme_source
```

Add tests for exactly one `openDataRequested()` action, preserved signals, two
`EntryModeCard` instances, the real recent model, no row/column/time labels, and mode
card border/background/check/accessible checked cues.

- [ ] **Step 2: Run focused entry tests and verify RED**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_royal_blue_entry_screen.py tests/ui/test_ivory_tiffany_brand_system.py tests/ui/test_cream_nacre_visual_system.py tests/ui/test_mode_action_surfaces.py -q`

Expected: FAIL on missing entry tokens, components, and structure.

- [ ] **Step 3: Add entry theme roles and components**

Add only the five approved literal colors plus derived alpha roles. Implement
`EntryModeCard` as a `Button` with `Accessible.RadioButton`, `Accessible.checked`, a
two-pixel selected border, selected background, and the existing real `check.svg`.
Implement `LanguageChoiceButton` as a compact radio-style text control with the same
focus contract.

- [ ] **Step 4: Recompose EntryScreen without changing signals**

Build a full-height 37% brand field and 63% ivory task field. Place language and
settings at the upper right; then heading, stacked mode cards, one primary file action,
and the recent list in a bounded column. Keep recent `model.display`, middle elision,
tooltip, index, and click signal. Keep error display localized and visible.

- [ ] **Step 5: Verify focused tests and commit**

Run the command from Step 2 and expect PASS.

Commit: `git commit -am "style: recompose royal blue entry screen"` after staging the
new QML files.

### Task 5: Native Runtime Captures And Blocking Design QA

**Files:**
- Create: `scripts/capture_entry_states.py`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/ko-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/en-casual.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/en-pro.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/ko-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/en-focus.png`
- Create: `docs/design-audit/2026-07-19-royal-blue-entry/comparison-*.png`
- Modify: `design-qa.md`
- Test: `tests/ui/test_royal_blue_entry_screen.py`

**Interfaces:**
- Consumes: real QML app, source screenshot, fixed 1366 x 768 viewport, real controller mode, language property, and keyboard focus.
- Produces: six state captures, combined source/implementation comparisons, and a passing QA report.

- [ ] **Step 1: Add and test a deterministic native capture harness**

The harness sets `QT_QPA_PLATFORM=offscreen`, instantiates real `AppBootstrap` and
`UiController`, loads `EntryScreen.qml` into `QQuickView`, sets 1366 x 768 geometry,
sets locale/mode/focus for each named state, processes events, and saves
`grabWindow()` output. It must not mutate settings or recent-file storage.

- [ ] **Step 2: Capture all six required states**

Run: `& .venv/Scripts/python.exe scripts/capture_entry_states.py --output docs/design-audit/2026-07-19-royal-blue-entry`

Expected: six nonempty 1366 x 768 PNG files and no QML errors.

- [ ] **Step 3: Build combined comparison images and inspect them**

Put the structural reference and each implementation capture into a single labeled
comparison canvas. Inspect the full view plus focused right-column and mode-card crops.
Written palette and truthful-data deviations are accepted; layout, density, typography,
control hierarchy, focus, and selected-state mismatches are not.

- [ ] **Step 4: Iterate until `design-qa.md` passes**

Record each P0/P1/P2 issue, fix it, recapture the same state, and compare again. The
final report includes source path, capture paths, viewport, states, full/focused
evidence, interaction checks, iteration history, and the exact final line:

```text
final result: passed
```

- [ ] **Step 5: Commit visual evidence**

Commit: `git commit -am "test: verify bilingual entry screen visually"` after staging
the capture script, audit directory, and `design-qa.md`.

### Task 6: Full Regression And Clean Handoff

**Files:**
- Verify all modified and created files from Tasks 1-5.

**Interfaces:**
- Consumes: complete implementation and evidence.
- Produces: fresh local gate evidence and a clean branch commit.

- [ ] **Step 1: Run focused localization and entry suites**

Run: `& .venv/Scripts/python.exe -m pytest tests/ui/test_app_bootstrap.py tests/ui/test_qml_string_catalog.py tests/ui/test_session_localization.py tests/ui/test_result_binding.py tests/ui/test_importing_service.py tests/ui/test_models.py tests/ui/test_royal_blue_entry_screen.py tests/ui/test_qml_runtime_load.py -q`

Expected: all pass with zero failures.

- [ ] **Step 2: Run the full local quality gate**

Run: `& .venv/Scripts/python.exe scripts/quality_gate.py`

Expected: compileall, ruff, bandit, launch smoke, pytest, and pip check all exit 0; only
the repository's four established skips remain unless the test inventory legitimately
changes.

- [ ] **Step 3: Verify the storage and routing boundaries**

Run static and runtime tests proving `DEFAULT_SETTINGS` and saved JSON contain no
language key; EntryScreen retains all five signals; Main retains the same handlers;
recommendation selection still does not auto-run; and recent rows still use only the
real model label.

- [ ] **Step 4: Inspect diff, commit, and prove status**

Run: `git diff --check`, inspect `git diff --stat` and `git diff`, then commit any final
verified changes with `git commit -m "feat: add bilingual royal blue entry"`.

Run: `git status --porcelain=v1 --untracked-files=all` and report the exact output.
