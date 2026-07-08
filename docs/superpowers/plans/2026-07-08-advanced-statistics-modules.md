# Advanced Statistics Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add executable repeated-measures ANOVA, Friedman, mediation, and moderated-mediation modules with full Modori contract, reporting, UI validation, and smoke coverage.

**Architecture:** Each module is a vertical bundle: Step, module-local result DTO, module-local reporting, optional recommendation provider, catalog spec, knowledge entries, UI command/run validation, and package smoke. Runtime statistics are Python-native; R is used for reference verification and fixture generation.

**Tech Stack:** Python 3.11+, pandas, numpy, scipy, statsmodels, pingouin, pytest, optional local R 4.6.1 reference packages.

## Global Constraints

- Do not modify or clean `C:\Users\V\Desktop\TongTong\prototypes\crystal-aurora-proof\index.html`.
- Use `.venv\Scripts\python.exe -m pytest` for Python verification.
- Set `MPLCONFIGDIR=C:\Users\V\Desktop\TongTong\matplotlib-cache` for commands that import plotting-related dependencies.
- All new Step params require `schema_version: 1`.
- Unknown current-schema params are errors.
- New module DTOs must be module-local files, not additions to `src/modori/results.py`.
- Report prose must be deterministic and Korean-first.
- Mediation and moderated mediation prose must not use causal claims.
- R packages are reference tools, not package runtime dependencies.

---

## Task 1: Repeated-Measures Result, Step, Reporting, and Tests

**Files:**
- Create: `src/modori/repeated_measures_anova_results.py`
- Create: `src/modori/repeated_measures_anova_reporting.py`
- Create: `src/modori/steps/repeated_measures_anova.py`
- Modify: `src/modori/steps/__init__.py`
- Modify: `src/modori/steps/reporting.py`
- Test: `tests/test_repeated_measures_anova_step.py`
- Test: `tests/test_repeated_measures_anova_reporting.py`

**Interfaces:**
- Produces `RepeatedMeasuresAnovaResult` with fields used by reporting and UI display.
- Registers `RepeatedMeasuresAnovaStep.step_type == "stats.repeated_measures_anova"`.

- [ ] Write failing step tests for schema gates, wide-format repeated measures, Mauchly/epsilon diagnostics, corrected p-value, partial eta squared, and invalid inputs.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests\test_repeated_measures_anova_step.py -q` and confirm failures caused by missing module.
- [ ] Implement DTO, Step, registration, and reporting dispatch.
- [ ] Run the repeated-measures step/reporting tests and confirm pass.

## Task 2: Friedman Result, Step, Reporting, and Tests

**Files:**
- Create: `src/modori/friedman_results.py`
- Create: `src/modori/friedman_reporting.py`
- Create: `src/modori/steps/friedman.py`
- Modify: `src/modori/steps/__init__.py`
- Modify: `src/modori/steps/reporting.py`
- Test: `tests/test_friedman_step.py`
- Test: `tests/test_friedman_reporting.py`

**Interfaces:**
- Produces `FriedmanResult`.
- Registers `FriedmanStep.step_type == "stats.friedman"`.

- [ ] Write failing tests for schema gates, SciPy/pingouin parity, Kendall's W, stable level ordering, posthoc fail-closed behavior, and invalid inputs.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests\test_friedman_step.py -q` and confirm failures caused by missing module.
- [ ] Implement DTO, Step, registration, and reporting dispatch.
- [ ] Run the Friedman step/reporting tests and confirm pass.

## Task 3: Mediation Result, Step, Reporting, and Tests

**Files:**
- Create: `src/modori/mediation_results.py`
- Create: `src/modori/mediation_reporting.py`
- Create: `src/modori/steps/mediation.py`
- Modify: `src/modori/steps/__init__.py`
- Modify: `src/modori/steps/reporting.py`
- Test: `tests/test_mediation_step.py`
- Test: `tests/test_mediation_reporting.py`

**Interfaces:**
- Produces `MediationResult`.
- Registers `MediationStep.step_type == "stats.mediation"`.

- [ ] Write failing tests for schema gates, OLS path coefficient parity, deterministic bootstrap CI, listwise deletion counts, singular model rejection, non-scale rejection, and non-causal prose.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests\test_mediation_step.py -q` and confirm failures caused by missing module.
- [ ] Implement OLS helpers, bootstrap sampling with fixed seed, DTO, Step, registration, and reporting dispatch.
- [ ] Run mediation tests and confirm pass.

## Task 4: Moderated-Mediation Result, Step, Reporting, and Tests

**Files:**
- Create: `src/modori/moderated_mediation_results.py`
- Create: `src/modori/moderated_mediation_reporting.py`
- Create: `src/modori/steps/moderated_mediation.py`
- Modify: `src/modori/steps/__init__.py`
- Modify: `src/modori/steps/reporting.py`
- Test: `tests/test_moderated_mediation_step.py`
- Test: `tests/test_moderated_mediation_reporting.py`

**Interfaces:**
- Produces `ModeratedMediationResult`.
- Registers `ModeratedMediationStep.step_type == "stats.moderated_mediation"`.

- [ ] Write failing tests for Model 7, Model 14, conditional indirect effects at W mean +/- 1 SD, index of moderated mediation, deterministic bootstrap CIs, unsupported model rejection, and non-causal prose.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest tests\test_moderated_mediation_step.py -q` and confirm failures caused by missing module.
- [ ] Implement centered interaction path models, conditional indirect-effect bootstrap, DTO, Step, registration, and reporting dispatch.
- [ ] Run moderated-mediation tests and confirm pass.

## Task 5: Catalog, Knowledge, Recommendations, UI Commands, and Run Validation

**Files:**
- Modify: `src/modori/analysis_catalog.py`
- Modify: `src/modori/knowledge/registry.py`
- Modify: `src/modori/recommendations.py`
- Create: `src/modori/repeated_measures_anova_recommendation.py`
- Create: `src/modori/friedman_recommendation.py`
- Create: `src/modori/mediation_recommendation.py`
- Create: `src/modori/moderated_mediation_recommendation.py`
- Modify: `src/modori/ui/commands.py`
- Modify: `src/modori/ui/run_validation.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/ui/results.py`
- Modify: `src/modori/ui/result_validation.py`
- Modify: `src/modori/ui/strings.py`
- Create: `library/entries/repeated-measures-anova.yaml`
- Create: `library/entries/mauchly-sphericity.yaml`
- Create: `library/entries/greenhouse-geisser.yaml`
- Create: `library/entries/friedman-test.yaml`
- Create: `library/entries/kendalls-w.yaml`
- Create: `library/entries/mediation-analysis.yaml`
- Create: `library/entries/indirect-effect.yaml`
- Create: `library/entries/bootstrap-ci.yaml`
- Create: `library/entries/moderated-mediation.yaml`
- Create: `library/entries/conditional-indirect-effect.yaml`
- Test: `tests/test_analysis_catalog.py`
- Test: `tests/test_analysis_module_contract.py`
- Test: `tests/test_knowledge_library.py`
- Test: `tests/ui/test_commands.py`
- Test: `tests/ui/test_run_validation.py`
- Test: `tests/ui/test_pipeline_ops.py`
- Test: `tests/ui/test_recommendations.py`

**Interfaces:**
- New specs appear in `module_specs()`.
- New commands produce executable pipeline step commands.
- New result kinds render in the UI result adapter.

- [ ] Write failing catalog/contract tests that prove the former deferred modules are executable specs.
- [ ] Write failing UI command/run-validation tests for all four step types.
- [ ] Implement specs, help aliases, knowledge entries, recommendation providers, command builders, run validation, pipeline ops, and result-kind mappings.
- [ ] Run the catalog, knowledge, and UI tests and confirm pass.

## Task 6: Smoke, Documentation, and Release Verification

**Files:**
- Modify: `src/modori/v1_statistics_smoke.py`
- Modify: `tests/test_v1_statistics_smoke.py`
- Modify: `tests/test_app_engine_smoke.py`
- Modify: `tests/test_package_engine_smoke_script.py`
- Modify: `docs/specs/release-readiness-checklist.md`
- Modify: `docs/specs/release-manual-qa.md`
- Modify: `scripts/package_engine_smoke.py` if result keys are asserted explicitly.

**Interfaces:**
- `v1_statistics_smoke_payload()` includes all four new modules.
- Package engine smoke fails if any new module fails.

- [ ] Write failing smoke tests that expect the four new checks.
- [ ] Add deterministic fixtures and assertions to `v1_statistics_smoke.py`.
- [ ] Run focused smoke tests.
- [ ] Run full quality gate with package check when code-level verification is green.

## Verification Commands

Run after Task 4:

```powershell
$env:MPLCONFIGDIR='C:\Users\V\Desktop\TongTong\matplotlib-cache'
.\.venv\Scripts\python.exe -m pytest tests\test_repeated_measures_anova_step.py tests\test_friedman_step.py tests\test_mediation_step.py tests\test_moderated_mediation_step.py -q
```

Run after Task 5:

```powershell
$env:MPLCONFIGDIR='C:\Users\V\Desktop\TongTong\matplotlib-cache'
.\.venv\Scripts\python.exe -m pytest tests\test_analysis_catalog.py tests\test_analysis_module_contract.py tests\test_knowledge_library.py tests\ui\test_commands.py tests\ui\test_run_validation.py tests\ui\test_pipeline_ops.py tests\ui\test_recommendations.py -q
```

Run after Task 6:

```powershell
$env:MPLCONFIGDIR='C:\Users\V\Desktop\TongTong\matplotlib-cache'
.\.venv\Scripts\python.exe -m pytest tests\test_v1_statistics_smoke.py tests\test_app_engine_smoke.py tests\test_package_engine_smoke_script.py -q
```

Final verification:

```powershell
$env:MPLCONFIGDIR='C:\Users\V\Desktop\TongTong\matplotlib-cache'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

## Self-Review

- The plan covers all four modules from Step through package smoke.
- The plan avoids central DTO expansion for new modules.
- The plan keeps R as reference tooling only.
- The plan includes fail-closed behavior for unsupported advanced cases.
- The plan does not require edits to the protected design asset.
