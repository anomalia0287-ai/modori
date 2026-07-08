# Statistical Coverage Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement assigned tasks. This is the controlling program plan; each module batch still needs its own task checklist and focused tests.

**Goal:** Complete the discussed social-science quantitative analysis coverage on top of the Analysis Module Contract, then run host package QA and prepare one final clean-VM verification pass after the full feature set is integrated.

**Architecture:** Modori remains a replayable pipeline. Each analysis is a Python `Step` with versioned params, module-local result/reporting/recommendation code, registry-backed `AnalysisModuleSpec`, Korean-first report output, and focused verification before it reaches UI menus or recommended run.

**Tech Stack:** Python dataclasses, pandas/numpy/scipy/statsmodels/pingouin/factor_analyzer/sklearn where already allowed by engine scope, pytest, existing QML thin shell, existing Word/report pipeline.

## Global Constraints

- Preserve `C:\Users\V\Desktop\TongTong\prototypes\crystal-aurora-proof\index.html` as a design asset. Do not clean, rename, rewrite, or remove it.
- Do not disturb staged release evidence files unless the assigned task explicitly owns that file.
- Clean VM is not run after each feature. It is reserved for the integrated feature set after host package QA passes.
- QML remains a thin shell. No statistical computation, p-value/effect-size/CI calculation, data reduction, or method routing belongs in `src/modori/ui/**` or QML.
- Every reportable statistic must have a named verification path before it enters `table_for`, `prose_for`, chart data, Word export, UI display, or recommended run.
- Recommendation is stricter than manual execution. A module may be executable manually but hidden from automatic recommendation until its eligibility rules are safe.
- Unknown params are errors after module-owned schema migration. New modules require `schema_version`.
- New result DTOs, reporting helpers, and recommendation providers are module-local. Shared dispatch files may contain small registration or dispatch hooks only.
- Shared files are serialized by the integrating session: `analysis_catalog.py`, `recommendations.py`, `steps/reporting.py`, `ui/controller.py`, `ui/pipeline_ops.py`, QML menu surfaces, and report export options.

## Current State

Completed or already executable:

- `descriptives_table1`: first new-style Analysis Module Contract pilot. Contract harness, versioned params, module-local DTO/reporting/recommendation, help key, UI recommendation execution, and full quality gate are complete in the current working tree and clean branch `codex/descriptives-table1-contract-ready`.
- Reliability, independent comparison, paired comparison, and basic OLS regression are migrated into the `AnalysisModuleSpec` contract gate.
- Frequency/crosstab/chi-square and correlation are integrated with module-local engines, reporting helpers, recommendation providers, catalog specs, help keys, UI command bridge, result display, and report dispatch.
- One-way ANOVA, Kruskal-Wallis, and ANCOVA are integrated in the supervising worktree with module-local engines, reporting helpers, recommendation providers, catalog specs, help keys, UI command bridge, result display, and report dispatch.
- Factor/PCA is integrated with PCA/EFA execution, KMO, Bartlett, deterministic parallel analysis, module-local reporting, recommendation candidate logic, catalog/help coverage, UI command bridge, result display, and report dispatch.
- Basic OLS regression has the V1 completion layer integrated: categorical-predictor dummy coding with explicit reference levels, interaction safety, centered interaction terms, and supported simple-slopes output.
- Latest host package QA on 2026-07-08 passed:
  `.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch`
  reported `896 passed, 3 skipped`, `package-tool-ok`, `package-launch-smoke-ok`,
  `package-engine-smoke-ok`, and `package-public-data-smoke-ok`. The packaged
  engine smoke JSON includes 16 V1 statistical engine checks, all `ok: true`.
  After payload preparation updates, `scripts\quality_gate.py --with-package-check
  --with-packaged-launch` reported `897 passed, 3 skipped` against the same
  packaged executable.
- Clean VM payload preparation is current: Payload V2 was rebuilt from the
  latest `dist\Modori` while `Modori-CleanWin-QA-Direct` was `Off`. The attach
  log records payload rebuild, content validation, disk attach, and `Done` at
  `2026-07-08 05:47:48` local time. Current file evidence shows
  `C:\VM\ModoriPayload\ModoriPayloadV2.vhdx` was written at
  `2026-07-08 05:52:08`, after the host package build at `2026-07-08 01:49:09`.

Explicitly deferred in the current catalog:

- `repeated_measures_anova`
- `friedman`
- `mediation`
- `moderated_mediation`

The deferment is correct until their dedicated golden-reference gates exist.

## Product Completion Definition

For this goal, "all discussed statistical features" means the committed V1/V1.x scope already recorded in the repository, not every method in SPSS.

V1 product-ready coverage requires:

- Descriptives and Table 1 summaries.
- Reliability with item-total diagnostics.
- Frequency, crosstab, chi-square, and exact-test routing.
- Correlation, including Pearson/Spearman routing.
- Independent Welch t-test.
- Paired t-test.
- Mann-Whitney U.
- Wilcoxon signed-rank.
- Kruskal-Wallis.
- ANOVA with post-hoc tests.
- ANCOVA with slope-homogeneity check.
- Factor analysis/PCA with KMO, Bartlett, and parallel analysis.
- Basic OLS regression with dummy coding, VIF, interaction safety, and supported simple-slopes output.
- Korean-first APA-style report text for each exposed result, including N, excluded N, effect sizes or practical statistics, confidence intervals where supported, and non-causal wording unless design metadata explicitly permits causal language.
- UI menu/guide exposure and report export controls for the expanded result set.

V1.x coverage follows after V1 gates pass:

- Mediation and moderated mediation as a separate advanced-process module with bootstrap CI, indirect-effect reporting, model templates, path diagrams, conditional effects where supported, and golden tests against PROCESS/R/lavaan or jamovi/jAMM.
- Repeated-measures ANOVA and Friedman routing with sphericity evaluation, Greenhouse-Geisser/Huynh-Feldt handling where justified, nonparametric routing, and golden tests against trusted R/SPSS outputs.
- Logistic, ordinal, and multinomial regression only if a narrow verified slice can be delivered without delaying V1; otherwise they remain V1.x.

Out of scope for this completion pass unless a later spec changes the boundary:

- Mixed models.
- MANOVA.
- Complex survey weights.
- Multiple imputation.
- LLM/SLM-generated statistical interpretation.
- External API calls for routing, guidance, or explanation.

## Implementation Order

### Phase 0: Stabilize The Contract Surface

Purpose: prevent the next modules from colliding in shared files.

Deliverables:

- Migrate existing executable analyses to new-style specs or a registry-backed equivalent:
  - `stats.reliability`
  - `stats.compare_groups`
  - `stats.paired_comparison`
  - `stats.regression_ols`
- Add or document schema-version compatibility for legacy params. Legacy project JSON without `schema_version` may be accepted only through explicit module-owned migration.
- Ensure the contract harness covers existing executable modules, not only `descriptives_table1`.
- Introduce a low-conflict registration pattern before new module workers start:
  - module-local `MODULE_SPEC`;
  - module-local reporting handler;
  - module-local recommendation provider;
  - small central loader/dispatch list owned by the integration session.
- Preserve current behavior and focused tests for existing reliability/comparison/paired/regression features.

Stop condition:

- Existing executable modules pass the contract harness, or the plan records a precise reason why a legacy module remains temporarily lightweight and hidden from expanded module work.

### Phase 1: Low-Risk Breadth Modules

Purpose: add common social-science coverage with limited modeling ambiguity.

Modules:

- `frequency_crosstab_chisquare`
  - Frequencies for nominal/ordinal variables.
  - Crosstabs.
  - Chi-square with expected-cell diagnostics.
  - Exact-test routing where supported and clearly verified.
  - Cramer's V or an appropriate association effect size.
- `correlation`
  - Pearson for scale-scale pairs when assumptions are acceptable.
  - Spearman routing for ordinal/non-normal/rank-safe cases.
  - Pairwise/listwise deletion must be visible.
  - Multiple-comparison guidance for correlation matrices.

Recommendation policy:

- Frequencies may be `strong` after import for categorical variables.
- Crosstab/chi-square and correlation are `candidate` unless explicit user intent identifies variables.

### Phase 2: Group Comparison Expansion

Purpose: complete the common inferential comparison set.

Modules:

- `one_way_anova`
  - One-way ANOVA.
  - Assumption diagnostics.
  - Tukey post-hoc for ordinary equal-variance cases.
  - Games-Howell for unequal-variance cases.
  - Eta-squared or omega-squared where verified.
- `kruskal_wallis`
  - Kruskal-Wallis.
  - Post-hoc routing with correction guidance.
  - Effect size with visible limits.
- `ancova`
  - ANCOVA.
  - Homogeneity of regression slopes check before interpretation.
  - Clear fail-closed behavior when slopes are not homogeneous.

Recommendation policy:

- Manual or candidate only. Automatic strong recommendation is not allowed without explicit research intent and variable-role confirmation.

### Phase 3: Factor/PCA

Purpose: support scale construction and construct validity workflows without relying on weak heuristics.

Modules:

- `factor_pca`
  - KMO.
  - Bartlett test.
  - Parallel-analysis based factor-count guidance.
  - PCA and EFA output boundaries explicitly separated.
  - Rotation behavior fixed in params.
  - Loading table, communalities, explained variance, and warnings.

Recommendation policy:

- Manual or candidate only. No strong recommendation, because factor/PCA depends on construct intent and item-set selection.

### Phase 4: Regression Completion

Purpose: make the regression slice publishable for routine social-science use.

Modules or extensions:

- Categorical-predictor encoding with explicit reference levels.
- Interaction-term safety:
  - centering guidance;
  - product-term construction as a replayable step or explicit regression param;
  - no causal wording from cross-sectional data.
- Supported simple-slopes output.
- Regression report export across the expanded result set.

Recommendation policy:

- Caution only unless a clear guided intent is present. Multiple defensible models must not auto-run.

### Phase 5: UI Menus, Guide, Report Export, And Host QA

Purpose: expose the completed engine set without turning QML into the statistics layer.

Deliverables:

- Analysis menu/dialog entries for all executable V1 modules.
- Guide rail intent mapping for safe cases only.
- Result DTO conversion for every new result kind.
- Report export include options that do not silently drop new result kinds.
- Explain-mode help-key coverage for every new user-facing term.
- Main PC package rebuild:
  - `.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-build --with-packaged-launch`
- Host packaged launch from:
  - `C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`
- Manual host QA through import, run, results, report export, and screenshot review.

### Phase 6: Clean VM Verification

Purpose: validate install/runtime only after the full feature set is integrated.

Deliverables:

- Shut down the VM fully before rebuilding Payload V2.
- Rebuild/attach payload only while Hyper-V reports the VM as `Off`.
- Run clean VM smoke against the integrated package and fixtures.
- Record release evidence in the existing release QA docs.

## Parallel Session Rules

Use a separate worktree session only when it reduces risk or time without requiring simultaneous edits to the same shared file.

Safe parallel work:

- Numeric engine and result DTO for one module.
- Module-local reporting helper.
- Module-local recommendation provider.
- Module-local tests and golden fixtures.
- Module-specific help entries if the knowledge registry supports independent entry files.

Serialized integration work:

- Global analysis catalog or module loader changes.
- Shared reporting dispatch.
- Shared recommendation orchestration.
- UI controller and QML menu wiring.
- Report export include options.
- Full quality gate and package build.

Required worker output:

- Exact files changed.
- Focused tests run and results.
- Known unsupported cases.
- Whether shared-file edits were made.
- Any generated cache/build outputs left behind.

## First Work Orders

Active delegated sessions:

| Work order | Thread id | Worktree | Scope boundary | Status at dispatch |
| --- | --- | --- | --- | --- |
| A: Existing module contract migration | `019f3d12-6675-7da1-a220-88af4b509208` | `C:\Users\V\.codex\worktrees\f92f\TongTong` | May edit narrow shared contract/harness files; no new statistical features | Integrated into supervising worktree; focused suite and quality gate passed |
| B: Frequency/crosstab/chi-square local slice | `019f3d14-f6ef-7bd2-b062-1c623e55153b` | `C:\Users\V\.codex\worktrees\ed9d\TongTong` | Module-local engine, DTO, reporting helper, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge |
| C: Correlation local slice | `019f3d15-40c5-7250-8b79-f3ca62a67d8e` | `C:\Users\V\.codex\worktrees\6d64\TongTong` | Module-local engine, DTO, reporting helper, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge |
| D: One-way ANOVA local slice | `019f3d2e-b1c5-7ac2-9267-4894b79aca9e` | `C:\Users\V\.codex\worktrees\83b2\TongTong` | Module-local engine, DTO, reporting helper, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge |
| E: Kruskal-Wallis local slice | `019f3d2f-03a2-7c61-ac76-ef60a2f2a032` | `C:\Users\V\.codex\worktrees\c83d\TongTong` | Module-local engine, DTO, reporting helper, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge |
| F: ANCOVA local slice | `019f3d2f-6746-7052-aabd-d17a0a07dd86` | `C:\Users\V\.codex\worktrees\26f6\TongTong` | Module-local engine, DTO, reporting helper, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge |
| G: Factor/PCA local slice | `019f3d4b-d9e3-78c0-8e9e-7b761c80abd7` | `C:\Users\V\.codex\worktrees\9982\TongTong` | Module-local engine, DTO, reporting helper, recommendation provider, focused tests only | Integrated into supervising worktree with catalog, recommendation, report/display bridge, UI command bridge, and help entries |
| H: Regression completion engine slice | `019f3d4c-39fd-72e3-85bd-29d19ee26b48` | `C:\Users\V\.codex\worktrees\83e2\TongTong` | Regression engine/results and focused regression tests only; no central UI/catalog/reporting dispatch | Integrated into supervising worktree with regression DTO/reporting compatibility and focused regression tests |

Supervising session obligations before accepting any delegated result:

- Read the worker's final report and exact test output.
- Inspect `git status --short` in the worker worktree.
- Inspect `git diff --stat` and shared-file edits directly.
- Reject or revise any result that touches forbidden files, weakens schema migration, adds UI statistics, skips focused tests, or claims release readiness.
- Integrate one worker at a time into the release lane and rerun the relevant focused tests from the integration worktree.

### Work Order A: Existing Module Contract Migration

Base: `codex/descriptives-table1-contract-ready`.

Scope:

- Migrate reliability, independent comparison, paired comparison, and OLS regression to `AnalysisModuleSpec` or the accepted registry-backed equivalent.
- Add schema migration/validation coverage for legacy params without breaking existing saved-project behavior.
- Extend the contract harness so these modules are gated.
- Do not add new statistical features.

Focused tests:

- `tests/test_analysis_module_contract.py`
- `tests/test_analysis_catalog.py`
- `tests/test_reliability_step.py`
- `tests/test_compare_groups_step.py`
- `tests/test_paired_comparison_step.py`
- `tests/test_regression_step.py`
- relevant reporting/UI tests touched by the migration.

### Work Order B: Frequency/Crosstab/Chi-Square Module Design And Engine

Base: after Work Order A, or from the same base only if the worker avoids shared integration files.

Scope:

- Define module-local result DTO, step, reporting helper, recommendation provider, and tests.
- Include frequencies, crosstabs, chi-square diagnostics, exact-test routing only where verified, and association effect size.
- Keep UI wiring out unless Work Order A has landed.

Focused tests:

- New module step tests.
- New reporting tests.
- Contract harness tests.
- Golden/reference parity tests against scipy/statsmodels or a committed R/SPSS fixture.

### Work Order C: Correlation Module Design And Engine

Base: after Work Order A, or from the same base only if the worker avoids shared integration files.

Scope:

- Define module-local result DTO, step, reporting helper, recommendation provider, and tests.
- Include Pearson/Spearman routing, visible N/excluded N, CI/effect reporting where verified, and multiple-comparison guidance.
- Keep UI wiring out unless Work Order A has landed.

Focused tests:

- New module step tests.
- New reporting tests.
- Contract harness tests.
- Golden/reference parity tests.

## Acceptance Gates

The goal is not complete until:

- Every V1 module listed above is executable, contract-gated, reportable, and UI-reachable where intended.
- Deferred V1.x modules are still visibly fail-closed until their advanced gates are implemented.
- Full quality gate passes.
- Host package build and packaged launch pass.
- Main PC visual/manual QA confirms the screens.
- Clean VM verification is run only after the integrated package is ready and produces release evidence.
