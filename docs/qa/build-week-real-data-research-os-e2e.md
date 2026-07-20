# Build Week Real-Data Research OS E2E Audit

Date: 2026-07-21 KST

## Outcome

The committed UCI Student Performance demo data completed the English Guided-mode Research OS path through the production QML component and `UiController`. The test proved full-file import, variable-meaning review, bounded clarification, a ledger-backed local recommendation, passport-bound preparation, confirmation without execution, a separate Run, numerical agreement with an independent SciPy calculation, English Word export, and recovery after a meaning-changing metadata edit.

This is source-level actual-QML evidence. It does not replace the still-pending audit of the freshly packaged Windows executable.

## Audited path

The automated audit uses `examples/build-week-demo/student-study-and-grades.csv` and a fresh isolated `LOCALAPPDATA` directory. It performs the following observable sequence:

1. select English and Guided mode;
2. preview the CSV through the normal import service;
3. confirm import and verify that all 649 rows, not only the 30-row preview sample, are loaded;
4. label `final_grade` as scale and `weekly_study_time_band` as ordinal, including all four study-time value labels;
5. open Research OS, answer that the question is noncausal, and choose rank co-movement;
6. assign Final grade as outcome and Weekly study time as focal predictor through the actual QML role fields;
7. review the exact labels, measures, and value labels in the Variable Meaning Gate before a durable recommendation exists;
8. answer the three committed clarification IDs for dependence, weight use, and clustering;
9. review the Spearman rank-correlation candidate and its association-only claim boundary;
10. invoke Prepare and review the sealed method and variable pair;
11. confirm the preparation and verify that no analysis result exists yet;
12. invoke the separate Run action;
13. inspect the displayed result and export an English Word report;
14. change the study-time measure after the run, verify that the old confirmation cannot be reused, and invoke the explicit replan recovery path.

## Provenance and transition evidence

The Variable Meaning Gate completed before the local recommendation was committed. Both role facts contain the exact `variable-meaning-review:v1:<digest>` provenance reference. The terminal durable record has action `RECOMMEND_LOCAL`; its passport digest equals the displayed decision identity digest.

The audit opens the SQLite ledger read-only and observes eight committed ledger events and four `analysis_passport` artifacts. It does not infer provenance from visible recommendation wording.

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

The display rounds the coefficient to `0.275` and the p-value to `0.000`, while retaining the full numerical values in the engine result. The English table preserves the tied-rank caution rather than hiding it. The Word file contains Research OS, Spearman, both English variable labels, the rounded coefficient, and the recommendation-validity boundary; no Korean product prose is present.

## Defects exposed by the real-data path

### Preview-limit wording

The production importer intentionally reads only 30 rows for a preview but previously displayed `Previewed data: 30 rows`, which could be mistaken for the total size of a 649-row file. Four focused assertions failed before the change. The UI now says `Preview sample: 30 rows · 6 variables` and explicitly states that only the first 30 rows are previewed and the full data is loaded after confirmation. The E2E then verifies an imported dataset length of 649.

Focused result: `4 passed in 2.87s`.

### English result-table warning

The actual Spearman result exposed a Korean tied-rank warning inside an otherwise English result table and Word report. The reporting path had bilingual prose but only one table-row representation. Three focused tests failed before the change: the correlation reporter rejected a language argument, `DisplayTable` had no English-row contract, and UI reporting generated only one table.

The fix keeps the caution, derives its English form only when the structured method details prove SciPy Spearman with tied ranks and asymptotic p-values, stores optional English table rows, applies them during live language binding, and passes the selected language into Word reporting. Unknown warnings are not silently discarded.

Focused result: `11 passed in 3.71s`.

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

## Remaining boundary

Verified here: source code, production QML component, production controller/import/report paths, isolated local ledger, independent numerical reference, and generated Word content.

Not yet verified here: a fresh wheel, a fresh one-folder executable, package smokes, cold visible Windows interaction, screenshot fidelity, and the final recording sequence. Those remain mandatory before a submission-ready claim.
