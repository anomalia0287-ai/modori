# Build Week Real-Data Submission Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a submission-grade Modori build whose current usability work, public P0 fixes, real social-science dataset, actual Research OS run, Word report, and three-minute demo claims all describe the same verified product.

**Architecture:** Keep `codex/research-os-functional-usability` as the only writable implementation lane. Reconcile the eight public-P0 descendant commits by semantic diff without merging, copying whole files, or replacing later usability behavior; then prove one real-data path at controller, actual-QML, packaged-executable, and human-visible Windows boundaries. Keep source changes, demo data provenance, package evidence, and marketing documents as separate commits so each gate can be reviewed or rejected independently.

**Tech Stack:** Python 3.12, PySide6/QML, pandas/SciPy-backed Modori steps, pytest, Ruff, PyInstaller one-folder packaging, python-docx, PowerShell, local Windows UI.

## Global Constraints

- Keep one active P0: real-data submission closure.
- Preserve local-only execution, no telemetry, no cloud or generative recommendation path, and no user-data transmission.
- Preserve recommend/clarify/abstain, `EXPERIMENTAL`, commit-before-display, explicit Prepare confirmation, and a separate Run action.
- Do not weaken tests, thresholds, statistical boundaries, or provenance to obtain a pass.
- Do not merge or push a public branch, change the default branch, or replace public release artifacts without an explicit release decision.
- Do not use blanket `ours`/`theirs`, whole-file copying, or deletion of current usability behavior.
- Use a real public social-science dataset with a traceable source, codebook, reuse terms, non-sensitive demo subset, and explicit observation unit.
- Treat calculation correctness, workflow integrity, recommendation validity, and demo appeal as distinct evidence layers.
- Do not call the submission ready until the exact packaged executable completes import through Word export without a hidden workaround.

---

### Task 1: Reconcile Public-P0 Functional Fixes Into the Usability Lane

**Files:**
- Create: `docs/qa/build-week-public-p0-functional-delta-ledger.md`
- Modify: `src/modori/ui/controller.py`
- Modify: `src/modori/ui/run_validation.py`
- Modify: `src/modori/ui/localization.py`
- Modify: `src/modori/correlation_reporting.py`
- Modify: `src/modori/ui/qml/components/ResultsPanel.qml`
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/strings_en.py`
- Test: `tests/ui/test_research_flow_controller.py`
- Test: `tests/ui/test_run_validation.py`
- Test: `tests/ui/test_importing_service.py`
- Test: `tests/ui/test_session_localization.py`
- Test: `tests/test_correlation_reporting.py`
- Test: `tests/ui/test_qml_runtime_load.py`

**Interfaces:**
- Consumes: release-only range `b368cdcf208d04509717826bc6b0ab7e7b72ba7e..c23164c2cf42857c24776c83ee3cfbd017e74b9e` and usability-only range `b368cdcf208d04509717826bc6b0ab7e7b72ba7e..976397a1cd715d31edbf0c106effd8b7b35f791a`.
- Produces: a current-pipeline preparation boundary, a correlation validator accepting either engine-supported `variables` or sealed `pairs`, complete English session messages, correct English correlation prose, and Cronbach help visible only for reliability results.

- [ ] **Step 1: Freeze the exact release-only functional inventory**

Record all 12 `src/` and `tests/` paths changed between the shared `b368cdcf` parent and `c23164c2`, the owning source commits (`6169552`, `b2235da`, `4253844`), their blob IDs at both tips, and whether current usability history already preserves, supersedes, or lacks each semantic change.

Run:

```powershell
git diff --name-status b368cdcf208d04509717826bc6b0ab7e7b72ba7e..c23164c2cf42857c24776c83ee3cfbd017e74b9e -- src tests
git diff --name-status b368cdcf208d04509717826bc6b0ab7e7b72ba7e..HEAD -- src tests
```

Expected: exactly 12 release-only paths; no unrecorded functional path may be omitted.

- [ ] **Step 2: Preserve the failing correlation regression test**

Keep this exact behavior in `tests/ui/test_run_validation.py`:

```python
def test_validator_accepts_pair_scoped_correlation_from_research_os() -> None:
    result = validate(
        [{
            "step_type": "stats.correlation",
            "params": {
                "schema_version": 1,
                "pairs": [["body_mass_g", "flipper_length_mm"]],
                "method": "pearson",
                "missing_policy": "pairwise",
                "p_adjust": "none",
            },
        }],
        {"body_mass_g", "flipper_length_mm"},
    )
    assert result.ok is True
```

The pre-fix observation is already recorded as a failure with `상관분석 변수는 문자열 목록이어야 합니다.`.

- [ ] **Step 3: Add the replaced-import-pipeline regression before porting its boundary**

Port `test_ui_controller_confirms_against_replaced_import_pipeline` from `6169552` into the current test file while retaining all later usability tests. It must assert that the initial pipeline stays unchanged, the replacement pipeline receives exactly one correlation step, `canRerun` is true, and confirmation does not execute analysis.

Run:

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_research_flow_controller.py::test_ui_controller_confirms_against_replaced_import_pipeline -q
```

Expected before the controller port: FAIL because preparation still holds the initial pipeline operations object.

- [ ] **Step 4: Port the minimal current-pipeline and correlation-contract fixes**

Use the release-proven boundaries, adapted only where current usability signatures differ:

```python
class _CurrentPipelineOperations:
    def __init__(self, provider: Callable[[], PipelineOperations]) -> None:
        self._provider = provider

    def current_dataset(self) -> object | None:
        return self._provider().current_dataset()

    def replace_research_os_analysis_step(
        self,
        preparation: PassportBoundPreparation,
        *,
        commit_pipeline_change: Callable[[PassportBoundPreparation], int],
    ) -> tuple[str, int]:
        return self._provider().replace_research_os_analysis_step(
            preparation,
            commit_pipeline_change=commit_pipeline_change,
        )
```

```python
from modori.steps.correlation import CorrelationStep

try:
    clean = CorrelationStep.validate_params(
        CorrelationStep.migrate_params(dict(params))
    )
except (TypeError, ValueError):
    return self._invalid("상관분석 설정이 올바르지 않습니다.")
variables = [str(value) for value in clean["variables"]]
return self._require_known_variables(variables, variable_keys)
```

- [ ] **Step 5: Port release claim-fidelity fixes semantically**

Add the three missing English session mappings, English correlation prose beginning `This result summarizes`, and the `canExplainCronbachAlphaResult`-bound QML button. Preserve Guided-mode warning consolidation, actionable recovery, grid resizing, and current terminology.

- [ ] **Step 6: Run the complete release-delta cohort**

Run:

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_run_validation.py tests/ui/test_research_flow_controller.py tests/ui/test_importing_service.py tests/ui/test_session_localization.py tests/test_correlation_reporting.py tests/ui/test_qml_runtime_load.py -q
```

Expected: all tests pass, with no skipped or xfailed regression substituted for a pass.

- [ ] **Step 7: Commit the functional reconciliation**

```powershell
git add docs/qa/build-week-public-p0-functional-delta-ledger.md src/modori tests
git commit -m "fix: preserve public P0 functionality in usability lane"
```

---

### Task 2: Select and Freeze a Real Social-Science Demo Dataset

**Files:**
- Create: `docs/qa/build-week-real-data-demo-audit.md`
- Create: `scripts/prepare_build_week_demo_data.py`
- Create: `tests/test_prepare_build_week_demo_data.py`
- Create: `examples/build-week-demo/source/uci-student-performance.zip`
- Create: `examples/build-week-demo/student-study-and-grades.csv`
- Create: `examples/build-week-demo/README.md`

**Interfaces:**
- Consumes: UCI Student Performance DOI `10.24432/C5TG7T`, the official nested source archive, its UCI codebook, and the explicit UCI CC BY 4.0 license.
- Produces: a deterministic non-identifying Portuguese-language-course subset with six learning/context variables; source hash, transform hash, row count, missingness, value range, and the preselected Spearman reference are recorded.

- [ ] **Step 1: Audit three candidate stories against fixed gates**

Compare: the BFI respondent-level personality items, UCI Student Performance, and a one-year World Development Indicators country cross-section. Reject any candidate with unclear reuse terms, an unaddressed weight/cluster/repeated-measure requirement, fewer than 100 complete pairs, more than 10% pairwise missingness, sensitive identifiers, or an absolute association outside `0.25 <= |r or rho| <= 0.85`.

The completed pre-screen rejects BFI for public-demo use because Rdatasets explicitly says the rights to the numeric data are not definitive. UCI Student Performance is the primary candidate because UCI identifies it as observed social-science data, gives a DOI and full codebook, and licenses it under CC BY 4.0. The Portuguese-course file has 649 complete rows; weekly study-time band versus final grade has Spearman `rho = 0.2747118483356099`, while past failures versus final grade has `rho = -0.4483603000808326`. World Development Indicators remains a fallback only if the UCI source archive or research-design audit fails a later fixed gate.

- [ ] **Step 2: Write the deterministic preparation test first**

The test must require the exact nested source-archive SHA-256, the Portuguese-course member, the six allowlisted output columns, no direct identifier or demographic column, integer values in their documented ranges, exactly 649 rows with no missing cells, and a recomputed weekly-study-time/final-grade Spearman coefficient equal to `0.2747118483356099` within `1e-12`.

Run:

```powershell
python -m pytest -p no:cacheprovider tests/test_prepare_build_week_demo_data.py -q
```

Expected before implementation: FAIL because the preparation module or output does not exist.

- [ ] **Step 3: Implement the smallest auditable transform**

`prepare_build_week_demo_data.py` must validate and read only the checked-in official UCI archive, open the nested `student.zip` and `student-por.csv`, copy only `studytime`, `failures`, `absences`, `famsup`, `higher`, and `G3`, rename them to user-facing snake-case keys, write UTF-8 CSV deterministically, and emit a deterministic JSON summary when invoked with `--summary`.

- [ ] **Step 4: Generate and independently recalculate the demo data**

Run the script twice into separate ignored directories and require byte-identical CSV and JSON outputs. Independently recompute row count, complete-pair count, missing counts, ranges, Pearson, and Spearman with a separate audit command.

- [ ] **Step 5: Record provenance and interpretation boundaries**

The example README must identify the UCI source, DOI, article, codebook, and CC BY 4.0 attribution; define each output column and its observation unit; state that the demo file removes demographic and direct-identifier fields; state that the demo summarizes association within two Portuguese schools rather than causation or population representativeness; and provide exact regeneration and hash commands.

- [ ] **Step 6: Commit the dataset evidence**

```powershell
git add docs/qa/build-week-real-data-demo-audit.md scripts/prepare_build_week_demo_data.py tests/test_prepare_build_week_demo_data.py examples/build-week-demo
git commit -m "test: add real social-science demo evidence"
```

---

### Task 3: Prove the Real Dataset Through the Actual Research OS Flow

**Files:**
- Create: `tests/ui/test_research_os_real_data_e2e.py`
- Create: `docs/qa/build-week-real-data-research-os-e2e.md`
- Modify only if a new failing test exposes a product defect: the smallest owning `src/modori/...` file and its focused test.

**Interfaces:**
- Consumes: `examples/build-week-demo/student-study-and-grades.csv` and Task 1's reconciled controller/run boundaries.
- Produces: an English actual-QML path asking whether weekly study time and final grade tend to move together, with rank co-movement, sealed variable-meaning review, exact committed clarification answers, a passport-bound Spearman preparation, explicit confirmation without execution, separate Run, displayed result, and English Word report.

- [ ] **Step 1: Write the actual-QML real-data acceptance test**

Follow the production QML component through `UiController`, not direct service calls. Assert import preview, metadata labels and ordinal measures, `VARIABLE_MEANING_REVIEW`, the committed clarification IDs and answers, `CANDIDATE_READY`, `PREPARE_REVIEW`, `CONFIRMED` with no results, then explicit `rerun()` and one correlation result.

- [ ] **Step 2: Require numerical and provenance agreement**

Assert the displayed Spearman coefficient, p-value, `n`, and excluded count against an independent SciPy calculation. Assert the durable record action is `RECOMMEND_LOCAL`, the preparation uses one exact `pairs` entry, and the report contains the English variable labels, method, result, Research OS boundary, and no Korean product prose.

- [ ] **Step 3: Run the test and diagnose any failure before editing production**

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_research_os_real_data_e2e.py -q
```

Expected: PASS after Tasks 1–2. Any failure starts a new red/green cycle; no workaround or expectation weakening is allowed.

- [ ] **Step 4: Run the adjacent Research OS cohort**

```powershell
python -m pytest -p no:cacheprovider tests/ui/test_research_os_novice_e2e.py tests/ui/test_research_os_real_data_e2e.py tests/ui/test_research_flow_controller.py tests/test_research_flow_handoff.py tests/test_research_flow_preflight.py -q
```

- [ ] **Step 5: Commit real-data E2E evidence**

```powershell
git add tests/ui/test_research_os_real_data_e2e.py docs/qa/build-week-real-data-research-os-e2e.md
git commit -m "test: prove real-data Research OS path"
```

---

### Task 4: Verify and Build the Exact Submission Candidate

**Files:**
- Create under ignored evidence root: `.visual-qa/build-week-real-data-candidate-2026-07-21/`
- Modify tracked files only if a failing gate exposes a separately tested defect.

**Interfaces:**
- Consumes: Tasks 1–3 commits and the pinned Windows/Python constraints already used by the public P0.
- Produces: focused/full test logs, Ruff/compile/launch results, wheel and one-folder hashes, package smokes, and an actual executable real-data path.

- [ ] **Step 1: Run source quality and focused gates**

Run compileall, Ruff, the complete Task 1–3 cohort, source launch smoke, and `pip check`. Every command must exit zero without ignored failures.

- [ ] **Step 2: Run the full non-gallery suite**

Use isolated `LOCALAPPDATA`, temp, cache, and the pinned R 4.5.3 boundary. Record the exact command, count, duration, and exit code. Do not relabel environment failures as product passes without a clean rerun under the documented environment.

- [ ] **Step 3: Build fresh wheel and one-folder outputs outside existing `dist`**

Use new ignored output directories and absolute PyInstaller data paths. Do not overwrite the public P0 wheel, launcher, or one-folder tree. Record source commit, file counts, byte sizes, and SHA-256 values.

- [ ] **Step 4: Run package launch, engine, and public-data smokes**

Each smoke must target the newly built executable, use isolated state, and exit zero. Preserve stdout/stderr logs in the evidence root.

- [ ] **Step 5: Use approved Windows control for the real-data executable audit**

Open the new executable with fresh isolated application state and English language. Complete the exact Task 3 path through visible UI, verify the result table and English Word file, recover once from a reversible metadata mistake, and capture screenshots of result-first, meaning gate, preparation, result, and export states.

- [ ] **Step 6: Commit no generated package artifact**

Require `git status --short` to show only intentional tracked documentation changes. Generated wheels, executables, reports, screenshots, ledgers, and local state remain ignored evidence until a separate release decision.

---

### Task 5: Align the Three-Minute Demo and Submission Evidence

**Files:**
- Modify after release-owner handoff or on its designated docs lane: `docs/build-week/DEMO_SCRIPT.md`
- Modify after release-owner handoff or on its designated docs lane: `docs/build-week/assets/modori-build-week-demo.en.srt`
- Modify after release-owner handoff or on its designated docs lane: `docs/build-week/DEVPOST_SUBMISSION.md`
- Modify after release-owner handoff or on its designated docs lane: `docs/build-week/VERIFICATION.md`

**Interfaces:**
- Consumes: Task 4's exact executable hash, screenshots, measured result, Word file, and source commit.
- Produces: a 2:55 result-first English demo, matching subtitles, positive AI-collaboration framing, and claim-bounded submission copy.

- [ ] **Step 1: Replace the synthetic demo story with the verified real-data result**

Keep the approved timeline: result/Word teaser, value proposition, Codex/GPT-5.6 contribution, import, preview, task/roles, Variable Meaning Gate, clarifications, candidate/configuration, separate Run, result, Word, closing.

- [ ] **Step 2: Enforce marketing and truth constraints**

Use positive product language, describe Codex/GPT-5.6 as a valuable engineering collaborator, lead with local guided analysis and reviewable method configuration, and keep limitation language concise. Do not claim causality, population representativeness, expert equivalence, SPSS superiority, or recommendation validity.

- [ ] **Step 3: Validate timing and text parity**

Require 11 SRT cues, final cue ending at or before `00:02:55,000`, no overlap, no placeholder text, no synthetic-data narration, and exact agreement between spoken numbers, visible result, Word report, and verification document.

- [ ] **Step 4: Prepare the user recording checklist**

Provide exact window size, fresh-state directory, data file, click sequence, expected state after each click, prohibited personal-path exposure, silent-screen-recording method, English voiceover/subtitle workflow, export destination, and one clean fallback take.

- [ ] **Step 5: Stop before public mutation**

Report the candidate commit, test counts, package hashes, video-ready files, remaining manual recording/upload steps, and any unresolved risk. Obtain the separate release decision before push, default-branch change, public artifact replacement, or Devpost submission mutation.
