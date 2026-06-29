# Slice 02 Multiple Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Slice #02 multiple linear regression without lowering the Slice #01 quality bar.

**Architecture:** Keep the existing replayable Step/Pipeline architecture. Regression is a new analysis Step that writes `analysis:<step_id>`, returns a typed `RegressionResult`, and is consumed by the existing `ReportStep` via step-id addressing while preserving legacy analysis keys for Slice #01 compatibility.

**Tech Stack:** Python, pandas, numpy, scipy, statsmodels, matplotlib, python-docx, pytest, R reference scripts.

---

## File structure

- Modify `src/tongtong/results.py`: add `CoefficientRow` and `RegressionResult`.
- Modify `src/tongtong/core/pipeline.py`: map each analysis result by declared write key and by producing step id.
- Modify `src/tongtong/steps/statistics.py`: add `MultipleRegressionStep` with OLS, diagnostics, HC3 policy, finite-output guards.
- Modify `src/tongtong/steps/reporting.py`: anchored APA number helper, regression prose/table/chart rendering, step-id include resolution.
- Modify `src/tongtong/steps/__init__.py`: export/register the new step.
- Modify `src/tongtong/workflow.py`: add regression preferences and A/B regression workflow builder.
- Create `tests/test_regression_step.py`: core, diagnostics, policy, validation, rerun, external reference checks.
- Modify `tests/test_report_step.py`: regression prose/table/chart/docx and legacy include compatibility.
- Modify `tests/test_modes_and_preferences.py`: guided/standard regression workflow equivalence and predictor-edit rerun.
- Create `tests/r/regression_reference.R` and `tests/r/regression_reference.stdout.txt`: reproducible R classical and HC3 references.
- Create or update `docs/specs/02-core-verification-matrix.md`: evidence ledger for Slice #02.

## Task 1: Analysis addressing and APA number hardening

- [ ] Add tests proving `ReportStep` resolves `include=["step-id"]` to `analysis:<step-id>` and legacy keys still work.
- [ ] Add a test proving `_apa_number(10.50, omit_leading_zero=True)` stays `10.50` and `-0.50` becomes `-.50`.
- [ ] Update `Pipeline._apply_analysis_writes` to also expose `analyses[step.id]` for analysis results.
- [ ] Update `ReportStep.reads()` and `ReportStep.compute()` to accept step ids and legacy keys.
- [ ] Fix `_apa_number` with anchored leading-zero stripping.

## Task 2: Regression result model and core OLS

- [ ] Add `CoefficientRow` and `RegressionResult` dataclasses.
- [ ] Add tests for classical OLS coefficients, classical SE, R2, adjusted R2, F, p, CI, standardized beta, beta CI, coefficient order, and chart contract.
- [ ] Implement `MultipleRegressionStep.compute()` with matrix/DataFrame API only.
- [ ] Reject non-SCALE/non-numeric dv or predictors, duplicate predictors, no predictors, zero variance, insufficient df, exact rank deficiency, and non-finite output.
- [ ] Ensure row reordering gives identical results.

## Task 3: Diagnostics and policies

- [ ] Add tests for VIF with constant included, BP LM p-value, HC3 auto-switch, robust coefficient SE/t/p/CI, robust Wald F, Shapiro small-n warning, DW order gating, Cook's distance, missing fraction warning.
- [ ] Implement VIF, Breusch-Pagan, Shapiro, Durbin-Watson, Cook's distance, warning generation, and modern/classic/custom policy.
- [ ] Reject HC3 non-finite covariance/statistics.

## Task 4: Reproducible validation

- [ ] Add unconditional numpy triangulation tests for b, classical SE, and R2.
- [ ] Add R reference script and captured stdout for `mtcars` classical fit plus HC3 reference.
- [ ] Add conditional pytest that executes the R script when `TONGTONG_RSCRIPT` or `Rscript` is available and compares stdout exactly before comparing values.

## Task 5: Reporting and charts

- [ ] Add tests for Korean/English regression prose, model-level APA sentence, predictor sentences excluding intercept, educational warnings, coefficient table, and coefficient forest chart PNG/SVG/EPS/docx embedding.
- [ ] Implement `prose_for`, `table_for`, and `render_chart` support for `RegressionResult` and `coefficient_forest`.
- [ ] Preserve existing reliability/comparison report tests.

## Task 6: A/B workflow and rerun anchor

- [ ] Add workflow tests proving guided and standard regression modes produce the same engine steps.
- [ ] Add predictor-edit rerun test proving coefficient table, prose, forest plot, and report refresh without changing ReportStep include references.
- [ ] Add source-data rerun test for listwise n and model output refresh.
- [ ] Implement `build_regression_slice_pipeline()` and regression preference snapshotting.

## Task 7: Full verification and documentation

- [ ] Run targeted red/green tests after each task.
- [ ] Run full pytest with `TONGTONG_RSCRIPT`.
- [ ] Run compileall, Bandit, pip check, and pip-audit.
- [ ] Record evidence in `docs/specs/02-core-verification-matrix.md`.
- [ ] Stop and report any blocker or non-finite/unverified statistic instead of claiming completion.
