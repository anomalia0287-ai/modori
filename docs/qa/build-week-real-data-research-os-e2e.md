# Build Week Real-Data Research OS E2E Audit

Date: 2026-07-21 KST

## Outcome

The committed UCI Student Performance demo data completed the English Guided-mode Research OS path through both the production QML component and the exact freshly built Windows one-folder executable. The source-under-test commit is `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`. The audits proved full-file import, variable-meaning review, bounded clarification, a ledger-backed local recommendation, passport-bound preparation, confirmation without execution, a separate Run, numerical agreement with an independent SciPy calculation, readable English Word export, and recovery after invalid variable-role input.

This document separates automated actual-QML evidence from direct observation of the exact packaged executable. It does not infer provenance or successful transitions from visible recommendation copy.

## Audited path

The automated audit uses `examples/build-week-demo/student-study-and-grades.csv` and a fresh isolated `LOCALAPPDATA` directory. It performs the following observable sequence:

1. select English and Guided mode;
2. preview the CSV through the normal import service;
3. confirm import and verify that all 649 rows, not only the 30-row preview sample, are loaded;
4. label `final_grade` as scale and `weekly_study_time_band` as ordinal, including all four study-time value labels;
5. open Research OS, answer that the question is noncausal, and choose rank co-movement;
6. assign Final grade as outcome and Weekly study time as focal predictor through the actual QML role fields;
7. review the exact labels, measures, and value labels in the Variable Meaning Gate before a durable recommendation exists;
8. answer the three committed clarification IDs for clustering, dependence, and weight use;
9. review the Spearman rank-correlation candidate and its association-only claim boundary;
10. invoke Prepare and review the sealed method and variable pair;
11. confirm the preparation and verify that no analysis result exists yet;
12. invoke the separate Run action;
13. inspect the displayed result and export an English Word report;
14. change the study-time measure after the run, verify that the old confirmation cannot be reused, and invoke the explicit replan recovery path.

The separate exact-package audit repeated the user-visible path with Windows controls. It also submitted the invalid outcome key `not_a_variable`, observed the bounded `Research OS operation failed` surface, selected `Return to the last verified state`, corrected the key to `final_grade`, and reached the Variable Meaning Gate again. No automatic retry or calculation occurred during this recovery check.

## Provenance and transition evidence

The Variable Meaning Gate completed before the local recommendation was committed. Both role facts contain the exact `variable-meaning-review:v1:<digest>` provenance reference. The terminal durable record has action `RECOMMEND_LOCAL`; its passport digest equals the displayed decision identity digest.

After the packaged run closed, the audit opened its isolated SQLite ledger and called `DecisionLedgerStore.verify(full_integrity=True)`. The result was eight committed events, 20 artifacts, four `analysis_passport` artifacts, no derived-state rebuild, and head `473eeba90f365ce5471ed997025a5ea919bf83fb871f5b53337dfda964ec5e0a`. `PassportHistory.inspect` reconstructed the action sequence `clarify`, `clarify`, `clarify`, `recommend_local`.

The terminal durable passport grants only the `association` claim class, identifies the Spearman capability, is `experimental: true`, is `auto_selected: false`, and retains `requires_explicit_configure_confirm_run: true`. This evidence comes from the decoded committed artifact and verified event chain, not the recommendation wording.

The sealed preparation is experimental and requires configure-confirm-run. Its exact canonical parameters are:

```json
{
  "method": "spearman",
  "missing_policy": "pairwise",
  "p_adjust": "none",
  "pairs": [["final_grade", "weekly_study_time_band"]],
  "schema_version": 1
}
```

Confirmation leaves the result model empty. Export is blocked before Run. Only the subsequent explicit Run submits the calculation and produces one correlation result.

## Numerical agreement

The acceptance test independently reads the demo CSV and calls SciPy `spearmanr` outside the Modori pipeline before running the product flow. The raw engine result agrees with that reference to the fixed tolerances:

| Check | Product result | Independent reference |
| --- | ---: | ---: |
| Method | Spearman | SciPy `spearmanr` |
| Coefficient | `0.2747118483356099` | `0.2747118483356099` |
| Two-sided p-value | `1.060624038270125e-12` | `1.060624038270125e-12` |
| Complete pairs | 649 | 649 |
| Excluded rows | 0 | 0 |

The display rounds the coefficient to `0.275` and the p-value to `0.000`, while retaining the full numerical values in the engine result. The English table preserves the tied-rank caution rather than hiding it. The exact packaged run generated a `37,343`-byte Word file with SHA-256 `6343649e5fbf39adf1c212ac2495e8e59e8490494b57b35f562a3e5719651d31`. It contains Spearman, both English variable labels, the rounded coefficient, sample and exclusion counts, the tied-rank caution, and the recommendation-validity boundary; no Korean product prose is present.

The Word file was inspected structurally and opened in Microsoft Word. Its single section is landscape (`11.0 × 8.5` inches), with `0.45`-inch horizontal margins and `0.55`-inch vertical margins. The 10-column result table has fixed weighted widths, `autofit: false`, and 8-point table text. All headers, the coefficient, p-value, `n`, excluded-row count, and wrapped warning fit on one visible page.

## Defects exposed by the real-data path

### Preview-limit wording

The production importer intentionally reads only 30 rows for a preview but previously displayed `Previewed data: 30 rows`, which could be mistaken for the total size of a 649-row file. Four focused assertions failed before the change. The UI now says `Preview sample: 30 rows · 6 variables` and explicitly states that only the first 30 rows are previewed and the full data is loaded after confirmation. The E2E then verifies an imported dataset length of 649.

Focused result: `4 passed in 2.87s`.

### English result-table warning

The actual Spearman result exposed a Korean tied-rank warning inside an otherwise English result table and Word report. The reporting path had bilingual prose but only one table-row representation. Three focused tests failed before the change: the correlation reporter rejected a language argument, `DisplayTable` had no English-row contract, and UI reporting generated only one table.

The fix keeps the caution, derives its English form only when the structured method details prove SciPy Spearman with tied ranks and asymptotic p-values, stores optional English table rows, applies them during live language binding, and passes the selected language into Word reporting. Unknown warnings are not silently discarded.

Focused result: `11 passed in 3.71s`.

### Wide Word result table

The real correlation row has 10 columns. The previous portrait Word export compressed those columns into an unreadable table even though the values were technically present. The reporting tests were first extended to require landscape orientation, bounded margins, fixed weighted widths, top-aligned cells, 8-point text, and extra room for the warning column. The implementation then satisfied those contracts without changing the analysis result or warning content.

Focused report result: `52 passed`.

The final package-generated report was then opened in Microsoft Word and visually checked at 100% zoom. The table remained on one page and its full numerical row and wrapped caution were readable.

## Test evidence

```text
python -m pytest -p no:cacheprovider tests/ui/test_research_os_real_data_e2e.py -q
1 passed in 5.05s
exit 0
```

The adjacent cohort included both synthetic-fixture and real-data novice flows, the Research Flow controller, handoff and preflight contracts, import service, correlation reporting, bilingual result binding, and report binding:

```text
$env:PYTHONPATH=(Resolve-Path src).Path
python -m pytest -p no:cacheprovider `
  tests/ui/test_research_os_novice_e2e.py `
  tests/ui/test_research_os_real_data_e2e.py `
  tests/ui/test_research_flow_controller.py `
  tests/test_research_flow_handoff.py `
  tests/test_research_flow_preflight.py `
  tests/ui/test_importing_service.py `
  tests/test_correlation_reporting.py `
  tests/ui/test_result_binding.py `
  tests/ui/test_results_report_binding.py -q
179 passed in 17.01s
exit 0
```

The explicit `PYTHONPATH` is required only for a preflight test that launches a clean child interpreter from this uninstalled `src`-layout worktree. Reproducing that child process without the source path fails before importing Modori; with the source path it prints the required `False False False`, proving that base Research Flow import does not eagerly load the inference stack.

The final full non-gallery source suite for `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b` completed with:

```text
3393 passed, 5 skipped in 526.41s
exit 0
```

Ruff, compileall, Bandit, source launch, and `pip check` also exited zero. The fresh wheel is `663,415` bytes with SHA-256 `30f17c2ea96128f12786b4593c9d48ea0b103059cc45f72f549784b8862b43fb`; its metadata is version 2.4 with `GPL-3.0-only` and it contains 227 files.

The final one-folder contains 4,491 files totaling `625,478,586` bytes. Its launcher is `31,494,275` bytes with SHA-256 `f539c9ae698fcc2f7b6cc5a0bc634aa9607a415993ccb4e83d5e8a507770c8d5`. The packaged launch, engine, and public-data smokes all exited zero in `7.258 s`, `23.43 s`, and `3.174 s` respectively.

The exact launcher then completed two isolated visible sessions:

1. the successful 649-row import → metadata → Variable Meaning Gate → three clarifications → candidate → exact configuration → confirm → separate Run → result → English Word path; and
2. the invalid-role failure → last-verified-state recovery → corrected role → Variable Meaning Gate path.

Accepted screenshots are stored under `.visual-qa/build-week-real-data-candidate-2026-07-21/screenshots/final-package-ca379fd/`. They are supporting visual evidence; the numerical, document, and ledger claims above are independently checked from the generated artifacts and verified SQLite records.

## Remaining boundary

Verified here: source code, production QML component, production controller/import/report paths, isolated local ledger, decoded passport provenance, independent numerical reference, fresh wheel, fresh one-folder executable, package smokes, direct Windows interaction, error recovery, generated Word structure, and the visible Microsoft Word page.

Not verified here: the final edited 2:55 recording, its exact subtitle synchronization, YouTube upload visibility, or the external submission form. Those are submission operations, not product-function claims, and must be checked against the canonical recording script before publication.

Post-submission formatting backlog: display finite p-values below `.001` as
`p < .001` instead of the rounded `0.000`, while preserving the raw numeric p-value
in result metadata and exports. The submission video must continue to show the
actual current UI and narrate the value as below `.001`.
