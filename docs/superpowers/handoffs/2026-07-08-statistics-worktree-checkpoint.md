# Statistics Worktree Checkpoint - 2026-07-08

Branch: `release/readiness-1-9`

Purpose: separate the current statistics feature output from pre-existing staged
changes and other working-tree changes before any cleanup, staging, commit, or VM
QA step.

Do not use `git add -A` from this state. Several files are mixed by topic, and
two files are mixed by index state (`MM`).

## Existing Staged Set To Preserve

These files are already staged and should not be unstaged, removed, or folded
into the statistics checkpoint without an explicit decision:

- `docs/qa/public-data-format-coverage.md`
- `docs/specs/release-manual-qa.md`
- `docs/specs/release-readiness-checklist.md`
- `docs/superpowers/handoffs/2026-07-03-clean-win-vm-verification-handoff.md`
- `docs/superpowers/handoffs/2026-07-06-public-data-smoke-vm-handoff.md`
- `docs/superpowers/plans/2026-07-07-import-curation.md`
- `docs/superpowers/plans/2026-07-07-visible-data-grid-qa.md`
- `prototypes/crystal-aurora-proof/index.html`

Special note:

- `prototypes/crystal-aurora-proof/index.html` is a protected design asset. It
  is staged as a new file and currently has no unstaged diff.
- `docs/specs/release-manual-qa.md` and
  `docs/specs/release-readiness-checklist.md` are `MM`: they have both staged
  and unstaged changes. Split them with `git diff --cached -- <file>` and
  `git diff -- <file>` before committing.

## Current Advanced Statistics Feature Output

This is the four-function feature set completed in the current checkpoint:

- repeated-measures ANOVA
- Friedman test
- mediation
- moderated mediation

Advanced-only plan/spec artifacts:

- `docs/superpowers/specs/2026-07-08-advanced-statistics-modules-design.md`
- `docs/superpowers/plans/2026-07-08-advanced-statistics-modules.md`

Advanced-only new module files:

- `src/modori/repeated_measures_anova_results.py`
- `src/modori/repeated_measures_anova_reporting.py`
- `src/modori/repeated_measures_anova_recommendation.py`
- `src/modori/steps/repeated_measures_anova.py`
- `src/modori/friedman_results.py`
- `src/modori/friedman_reporting.py`
- `src/modori/friedman_recommendation.py`
- `src/modori/steps/friedman.py`
- `src/modori/mediation_results.py`
- `src/modori/mediation_reporting.py`
- `src/modori/mediation_recommendation.py`
- `src/modori/steps/mediation.py`
- `src/modori/moderated_mediation_results.py`
- `src/modori/moderated_mediation_reporting.py`
- `src/modori/moderated_mediation_recommendation.py`
- `src/modori/steps/moderated_mediation.py`

Advanced-only help/library entries:

- `library/entries/repeated-measures-anova.yaml`
- `library/entries/mauchly-sphericity.yaml`
- `library/entries/greenhouse-geisser.yaml`
- `library/entries/huynh-feldt.yaml`
- `library/entries/friedman-test.yaml`
- `library/entries/kendalls-w.yaml`
- `library/entries/mediation-analysis.yaml`
- `library/entries/indirect-effect.yaml`
- `library/entries/bootstrap-ci.yaml`
- `library/entries/moderated-mediation.yaml`
- `library/entries/conditional-indirect-effect.yaml`
- `library/entries/index-of-moderated-mediation.yaml`

Advanced-only tests:

- `tests/test_repeated_measures_anova_step.py`
- `tests/test_repeated_measures_anova_reporting.py`
- `tests/test_friedman_step.py`
- `tests/test_friedman_reporting.py`
- `tests/test_mediation_step.py`
- `tests/test_mediation_reporting.py`
- `tests/test_moderated_mediation_step.py`
- `tests/test_moderated_mediation_reporting.py`

Advanced hunks inside shared files:

- `src/modori/analysis_catalog.py`: status/spec entries for
  `repeated_measures_anova`, `friedman`, `mediation`, and
  `moderated_mediation`.
- `src/modori/knowledge/registry.py`: help-key aliases for those four modules
  and their statistics.
- `src/modori/recommendations.py`: recommendation kinds/providers/rank for the
  four modules.
- `src/modori/steps/__init__.py`: imports and `__all__` for the four step
  classes.
- `src/modori/steps/reporting.py`: table/prose dispatch for the four result
  DTOs.
- `src/modori/ui/commands.py`: command builders for the four analyses.
- `src/modori/ui/run_validation.py`: run-time validation for the four step
  types.
- `src/modori/ui/pipeline_ops.py`: step instantiation, result-kind mapping, and
  report include routing for the four modules.
- `src/modori/ui/contracts.py`, `src/modori/ui/results.py`, and
  `src/modori/ui/result_validation.py`: display/result kind registration.
- `tests/test_analysis_catalog.py`, `tests/ui/test_commands.py`,
  `tests/ui/test_run_validation.py`, `tests/ui/test_pipeline_ops.py`, and
  `tests/ui/test_recommendations.py`: integration expectations for the four
  modules.
- `tests/test_app_engine_smoke.py` and `tests/test_v1_statistics_smoke.py`:
  smoke expectations for the four modules.

These shared files must be staged by hunk if the advanced feature needs a
separate commit.

## Broader V1 Statistics Output

The working tree also contains a broader V1 statistics expansion that is not
limited to the current four advanced modules. Treat this as a separate product
checkpoint unless the release decision is to ship the whole statistics bundle at
once.

Examples:

- `descriptives_table1`
- `frequency_crosstab`
- `correlation`
- `anova_oneway`
- `kruskal_wallis`
- `ancova`
- `factor_pca`
- recommendation providers for reliability, regression OLS, compare-groups,
  and other V1 modules
- general analysis-module contract tests and library entries

Representative new files:

- `src/modori/descriptives_table1_*.py`
- `src/modori/frequency_crosstab_*.py`
- `src/modori/correlation_*.py`
- `src/modori/anova_oneway_*.py`
- `src/modori/kruskal_wallis_*.py`
- `src/modori/ancova_*.py`
- `src/modori/factor_pca_*.py`
- `src/modori/steps/descriptives_table1.py`
- `src/modori/steps/frequency_crosstab.py`
- `src/modori/steps/correlation.py`
- `src/modori/steps/anova_oneway.py`
- `src/modori/steps/kruskal_wallis.py`
- `src/modori/steps/ancova.py`
- `src/modori/steps/factor_pca.py`
- matching `tests/test_*_step.py`, `tests/test_*_reporting.py`, and
  `tests/test_*_recommendation.py`

Mixed shared files for this broader set include:

- `src/modori/analysis_catalog.py`
- `src/modori/knowledge/registry.py`
- `src/modori/recommendations.py`
- `src/modori/steps/__init__.py`
- `src/modori/steps/reporting.py`
- `src/modori/ui/commands.py`
- `src/modori/ui/pipeline_ops.py`
- `src/modori/ui/run_validation.py`
- `src/modori/ui/results.py`
- `src/modori/ui/contracts.py`
- `src/modori/ui/result_validation.py`

## VM, Payload, Package, And Release-Ops Changes

Keep these separate from the statistics feature unless the release checkpoint is
explicitly "statistics plus VM package readiness":

- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`
- `scripts/attach_modori_payload_disk.ps1`
- `scripts/check_modori_payload_v2.ps1`
- `scripts/package_engine_smoke.py`
- `tests/test_clean_vm_payload_script.py`
- `tests/test_package_engine_smoke_script.py`

`scripts/package_engine_smoke.py` now fails closed when
`v1_statistics_smoke.ok` is absent or false. That supports the statistics
release gate, but it is a package-smoke hardening change rather than a single
analysis module.

## UI/QML And Guidance Changes

These appear to be product-surface work and should be reviewed separately from
engine statistics correctness:

- `src/modori/ui/qml/components/GuideRail.qml`
- `src/modori/ui/qml/components/PipelineRail.qml`
- `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- `src/modori/ui/qml/theme/Theme.qml`
- `src/modori/ui/analysis_editor.py`
- `src/modori/ui/controller.py`
- `src/modori/ui/patches.py`
- `src/modori/ui/recommendation_controller.py`
- `src/modori/ui/strings.py`
- matching UI tests under `tests/ui/`

Some UI test files are mixed because they include both statistics-command
coverage and product-surface behavior.

## Known Worktree Warnings

- `git status` reports permission warnings for `pytest-cache-files-*`
  directories. These are working-tree scan noise, not test failures.
- Git reports CRLF normalization warnings for
  `tests/test_clean_vm_payload_script.py` and `tests/test_regression_report.py`.
- Local `main` does not exist. The apparent base branch is `master`.

## Suggested Next Checkpoint Sequence

1. Preserve the existing staged set as-is until its owner/scope is confirmed.
2. Do not stage the protected design asset together with generated statistics
   code.
3. If committing in slices, commit the broader V1 statistics base before the
   advanced four-module feature, or consciously ship the full statistics bundle
   as one product checkpoint.
4. For an advanced-only commit, use hunk staging in the shared files listed
   above.
5. Keep VM/payload/package changes separate unless the commit is explicitly a
   release-readiness commit.
6. Run the full quality gate after any hunk split; hunk staging can accidentally
   separate code from registration or tests.

## Verification Evidence Before This Checkpoint

Functional verification completed before this checkpoint document was written:

- Advanced contract/UI/recommendation focused tests: `182 passed, 1 skipped`
- Advanced module step/reporting tests: `18 passed`
- Smoke tests for app/package helpers: `5 passed`
- Full pytest: `946 passed, 3 skipped`
- `scripts/quality_gate.py --with-package-check --with-packaged-launch`: passed

This document itself is a classification/checkpoint artifact and does not modify
runtime code.

## Separation Executed

Statistics bundle worktree:

- Path: `C:/Users/V/Desktop/TongTong/.worktrees/statistics-bundle-checkpoint`
- Branch: `codex/statistics-bundle-checkpoint`
- Base commit: `6603bab`

The original checkout remains on `release/readiness-1-9`; its existing staged
set was preserved. The protected prototype
`prototypes/crystal-aurora-proof/index.html` still has no unstaged diff in the
original checkout.

The separated worktree intentionally includes the statistics bundle, statistics
UI surface, smoke/package gate integration, and the statistics checkpoint docs.
It intentionally excludes:

- `RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd`
- `RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd`
- `scripts/attach_modori_payload_disk.ps1`
- `scripts/check_modori_payload_v2.ps1`
- `tests/test_clean_vm_payload_script.py`
- `prototypes/crystal-aurora-proof/index.html`
- pre-existing staged release/handoff/import-curation documents

Verification run inside the separated worktree with
`PYTHONPATH` pinned to the worktree `src`:

- Focused statistics/integration tests: `150 passed, 1 skipped`
- Full pytest: `945 passed, 3 skipped`
- `scripts/quality_gate.py --with-package-check --with-packaged-launch`: passed

Package note:

- The first package-gate attempt in the separated worktree failed because
  `dist/Modori/Modori.exe` did not exist in that new worktree.
- Running `scripts/package_windows.py` in the separated worktree created the
  package.
- The subsequent package-inclusive quality gate passed.
