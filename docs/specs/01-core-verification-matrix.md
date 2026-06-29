# TongTong Slice #01 Core Verification Matrix

> Status: live audit artifact. This document is not a completion claim. A row is
> complete only when the evidence is current, reproducible, and covers the stated
> requirement without relying on intent or self-referential checks.

## Completion standard

The Slice #01 core is not considered complete while any row is `fail`,
`unverified`, or `blocked`. Passing tests are evidence only for the requirement
they explicitly cover.

## Current gates

| Area | Requirement | Current evidence | Status |
| --- | --- | --- | --- |
| Pipeline P1 | Source data is never mutated during compute. | `tests/test_pipeline_core.py::test_dataset_masks_declared_missing_values_without_mutating_source_data` | pass |
| Pipeline P1 | Dirty propagation recomputes exactly dependent downstream steps. | `tests/test_pipeline_core.py::test_editing_step_params_recomputes_exact_dependent_downstream_steps` | pass |
| Pipeline P1 | Each output key has a single Step owner; duplicate writes are rejected on add, rolled back on parameter edit, and rejected after dynamic import writes resolve at recompute. | `tests/test_pipeline_core.py::test_pipeline_rejects_duplicate_writes_when_adding_step`, `tests/test_pipeline_core.py::test_edit_params_rolls_back_when_changed_writes_collide_with_another_step`, `tests/test_data_prep_steps.py::test_pipeline_rejects_duplicate_dynamic_import_writes_at_recompute` | pass |
| Pipeline P1 | Step results cannot write columns or metadata outside the step's declared `writes()` contract, and every returned column must include metadata. | `tests/test_pipeline_core.py::test_pipeline_rejects_step_result_columns_not_declared_in_writes`, `tests/test_pipeline_core.py::test_pipeline_rejects_step_result_columns_without_metadata` | pass |
| Pipeline P1 | Step result columns must be pandas Series whose indexes match the current dataset, preventing silent pandas alignment or row drift. | `tests/test_pipeline_core.py::test_pipeline_rejects_step_result_series_with_misaligned_index` | pass |
| Pipeline P1 | Step results cannot return analysis objects without exactly one declared analysis write, and cannot declare analysis writes without returning analysis. | `tests/test_pipeline_core.py::test_pipeline_rejects_analysis_without_declared_analysis_write`, `tests/test_pipeline_core.py::test_pipeline_rejects_declared_analysis_write_without_analysis`, `tests/test_pipeline_core.py::test_pipeline_rejects_multiple_analysis_writes_for_single_analysis_object` | pass |
| Pipeline P1 | Dirty propagation uses previous writes when upstream writes shrink. | `tests/test_pipeline_core.py::test_dirty_propagation_uses_previous_writes_when_upstream_writes_shrink` | pass |
| Pipeline P1 | Failed parameter edits roll back params and computed state. | `tests/test_pipeline_core.py::test_edit_params_rolls_back_when_new_params_cannot_be_validated` | pass |
| Pipeline P1 | Failed source replacement rolls back source and computed state. | `tests/test_pipeline_core.py::test_replace_source_dataset_rolls_back_when_downstream_recompute_fails` | pass |
| Pipeline P1 | Failed step removal rolls back step list and computed state. | `tests/test_pipeline_core.py::test_remove_rolls_back_when_downstream_recompute_fails` | pass |
| Serialization P1 | Pipeline JSON round-trip preserves source, steps, and results after recompute. | `tests/test_pipeline_core.py::test_pipeline_json_round_trip_preserves_source_steps_and_results` | pass |
| Serialization P1 | JSON output is strict and does not emit native `NaN`. | `tests/test_pipeline_core.py::test_pipeline_json_round_trip_uses_strict_json_for_native_missing_values` | pass |
| Serialization P1 | Built-in step types load in a fresh process during `Pipeline.from_json`. | `tests/test_runtime_environment.py::test_pipeline_from_json_registers_builtin_steps_in_fresh_process` | pass |
| Serialization P1 | Malformed pipeline JSON, dataset payloads, variable payloads, step params, and step dependency lists are rejected with clear `ValueError`s instead of raw Python exceptions or silent coercion. | `tests/test_pipeline_core.py::test_pipeline_from_json_rejects_malformed_payloads_clearly` | pass |
| Import | CSV import maps data, metadata, notes, and inferred measures. | `tests/test_data_prep_steps.py::test_import_step_reads_csv_into_dataset_with_metadata_and_notes` | pass |
| Import | XLSX import reads tabular data. | `tests/test_data_prep_steps.py::test_import_step_reads_xlsx` | pass |
| Import | SAV import preserves labels, value labels, point missing codes, and measure. | `tests/test_data_prep_steps.py::test_import_step_reads_sav_metadata` | pass |
| Import | `ImportStep.writes()` is header/metadata-only for CSV/XLSX/SAV. | `tests/test_data_prep_steps.py::*writes_reads_only*` | pass |
| Import | Unsupported SPSS missing ranges are not silently discarded. | `tests/test_data_prep_steps.py::test_import_step_rejects_sav_missing_ranges_that_are_not_point_codes` | pass |
| Reverse-code | Original column is preserved and labels reverse correctly. | `tests/test_data_prep_steps.py::test_reverse_recode_preserves_original_and_reverses_value_labels` | pass |
| Reverse-code | Declared missing codes are masked before reverse-coding. | `tests/test_data_prep_steps.py::test_reverse_recode_treats_declared_missing_codes_as_nan` | pass |
| Reverse-code | Invalid scale range is rejected. | `tests/test_data_prep_steps.py::test_reverse_recode_rejects_invalid_scale_range` | pass |
| Reverse-code | Duplicate source columns are rejected to prevent output-key overwrite. | `tests/test_data_prep_steps.py::test_reverse_recode_rejects_duplicate_columns` | pass |
| Compose | Survey missing policy uses the configured valid-response ratio. | `tests/test_data_prep_steps.py::test_compose_scale_survey_policy_uses_available_items_at_minimum_valid_ratio` | pass |
| Compose | Conservative policy requires complete cases. | `tests/test_data_prep_steps.py::test_compose_scale_conservative_policy_drops_any_case_with_missing_item` | pass |
| Compose | Empty item lists, duplicate item lists, and invalid `min_valid` values are rejected. | `tests/test_data_prep_steps.py::test_compose_scale_rejects_empty_item_list`, `tests/test_data_prep_steps.py::test_compose_scale_rejects_duplicate_items`, `tests/test_data_prep_steps.py::test_compose_scale_rejects_min_valid_outside_valid_ratio_range` | pass |
| Reliability | Cronbach alpha, CI, corrected item-total correlations, and alpha-if-deleted match independent formulas/reference library checks to 3 decimals. | `tests/test_reliability_step.py::test_reliability_step_computes_golden_values_and_chart_contract` | pass |
| Reliability | Cronbach alpha and CI match Pingouin's documented `cronbach_alpha` packaged dataset example. | `tests/test_reliability_step.py::test_reliability_step_matches_pingouin_documented_cronbach_dataset` | pass |
| Reliability | McDonald's omega definition is documented exactly. | `tests/test_reliability_step.py::test_mcdonald_omega_documents_its_exact_definition` | pass |
| Reliability | McDonald's omega has reproducible in-repo triangulation against an independent estimator. | `tests/test_reliability_step.py::test_reliability_step_computes_golden_values_and_chart_contract` | pass for directive Option B; stronger published/R-script validation remains desirable |
| Reliability | McDonald's omega has a committed R `psych::omega` reproduction path with captured stdout and no hard-coded fabricated R number. | `tests/r/omega_reference.R`; `tests/r/omega_reference.stdout.txt`; `tests/test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available` using `TONGTONG_RSCRIPT=.tools\r-env\Scripts\Rscript.exe` | pass |
| Reliability | Two-item and one-item scales are rejected because alpha-if-deleted is undefined unless at least two items remain after deletion. | `tests/test_reliability_step.py::test_reliability_step_rejects_fewer_than_three_items`, `tests/test_reliability_step.py::test_reliability_step_rejects_two_items_because_alpha_if_deleted_is_undefined` | pass |
| Reliability | Duplicate reliability items are rejected before dataframe selection to prevent double weighting or duplicate-column shape drift. | `tests/test_reliability_step.py::test_reliability_step_rejects_duplicate_items` | pass |
| Reliability | Non-numeric reliability items are rejected before Pingouin/factor-analysis execution. | `tests/test_reliability_step.py::test_reliability_step_rejects_non_numeric_items` | pass |
| Reliability | Singular omega matrices and zero-variance items produce clear errors. | `tests/test_reliability_step.py::test_reliability_step_reports_singular_omega_matrix_clearly`, `tests/test_reliability_step.py::test_reliability_step_rejects_zero_variance_items` | pass |
| Compare groups | Student t route matches reference statistics and signed Cohen's d. | `tests/test_compare_groups_step.py::test_compare_groups_routes_to_student_t_when_assumptions_hold` | pass |
| Compare groups | Student t route matches Pingouin's packaged `mixed_anova` public/reference dataset for August Control vs Meditation. | `tests/test_compare_groups_step.py::test_compare_groups_matches_pingouin_mixed_anova_public_dataset` | pass |
| Compare groups | Welch route matches reference statistics and signed Cohen's d. | `tests/test_compare_groups_step.py::test_compare_groups_routes_to_welch_when_variance_is_unequal` | pass |
| Compare groups | Mann-Whitney route matches U, p, rank-biserial, and chart contract. | `tests/test_compare_groups_step.py::test_compare_groups_routes_to_mann_whitney_for_small_nonnormal_groups` | pass |
| Compare groups | Row order does not change t-family or Mann-Whitney results. | `tests/test_compare_groups_step.py::*stable_when_rows_are_shuffled` | pass |
| Compare groups | String group codes without value labels work. | `tests/test_compare_groups_step.py::test_compare_groups_accepts_string_group_codes_without_value_labels` | pass |
| Compare groups | Duplicate rendered group labels are rejected so result dictionaries and reports cannot collapse two distinct groups. | `tests/test_compare_groups_step.py::test_compare_groups_rejects_duplicate_group_labels` | pass |
| Compare groups | Dependent variable and group variable must be different columns. | `tests/test_compare_groups_step.py::test_compare_groups_rejects_same_dependent_and_group_variable` | pass |
| Compare groups | Non-numeric dependent variables are rejected before assumption and test execution. | `tests/test_compare_groups_step.py::test_compare_groups_rejects_non_numeric_dependent_variable` | pass |
| Compare groups | Too-small groups, zero-variance groups, and invalid routing policies are rejected. | `tests/test_compare_groups_step.py::test_compare_groups_rejects_groups_too_small_for_assumption_checks`, `tests/test_compare_groups_step.py::test_compare_groups_rejects_zero_variance_within_group`, `tests/test_compare_groups_step.py::test_compare_groups_rejects_invalid_routing_policy` | pass |
| Compare groups | Routing boundaries use strict thresholds for `p < .05`, Levene `p < .05`, and the n=29/30 nonparametric cutoff. | `tests/test_compare_groups_step.py::test_modern_routing_uses_nonparametric_cutoff_boundary`, `tests/test_compare_groups_step.py::test_modern_routing_uses_strict_p_value_boundaries` | pass |
| Report | Korean APA prose, tables, figures, and docx are generated and synchronized with `ReportResult`. | `tests/test_report_step.py::test_report_step_generates_korean_apa_prose_figures_and_docx` | pass |
| Report | Generated PNG figures are readable images with 300 DPI metadata, SVG parses as XML, EPS has a PostScript header, and the docx embeds every generated PNG as non-zero inline shapes. | `tests/test_report_step.py::test_report_step_generates_korean_apa_prose_figures_and_docx` | pass |
| Report | English secondary prose is generated. | `tests/test_report_step.py::test_report_step_supports_english_secondary_prose` | pass |
| Report | Output filename traversal and unsupported language are rejected. | `tests/test_report_step.py::test_report_step_rejects_output_filename_path_traversal`, `tests/test_report_step.py::test_report_step_rejects_unsupported_language` | pass |
| Report | Absolute/forward-slash filenames and file-valued output directories are rejected. | `tests/test_report_step.py::test_report_step_rejects_absolute_or_forward_slash_filenames`, `tests/test_report_step.py::test_report_step_rejects_output_dir_that_is_an_existing_file` | pass |
| Report | Missing upstream analysis keys fail clearly. | `tests/test_report_step.py::test_report_step_reports_missing_upstream_analysis_key_clearly` | pass |
| Report | Missing upstream analysis keys are prevalidated before rendering, so failed reports do not leave partial figure/docx artifacts. | `tests/test_report_step.py::test_report_step_does_not_write_partial_figures_when_include_key_is_missing` | pass |
| Report | If chart rendering or docx writing fails after figures are rendered, generated figures and partial docx output are cleaned up. | `tests/test_report_step.py::test_report_step_cleans_generated_artifacts_when_chart_render_fails`, `tests/test_report_step.py::test_report_step_cleans_generated_artifacts_when_docx_write_fails` | pass |
| Reference workflow | Pingouin packaged reference data can be written to CSV, imported, analyzed for reliability/comparison, and rendered to report with reference statistics preserved. | `tests/test_report_step.py::test_public_reference_data_runs_from_csv_import_to_report` | pass |
| Reference workflow | A single public/published survey fixture, R `psych`/Rdatasets `bfi`, runs through CSV import, reverse-code, compose, reliability, Welch routing, APA prose, and docx output with independent pandas/scipy reference checks. | `tests/fixtures/psych_bfi.csv`; `tests/test_report_step.py::test_psych_bfi_public_survey_runs_from_csv_import_to_report` | pass |
| Visual layout QA | A representative BFI report docx was exported through Microsoft Word to PDF, rendered to page PNGs, and visually inspected for clipping, overlap, broken tables, broken figures, and missing glyphs. | `docs/specs/01-visual-layout-review.md` | pass for representative Slice #01 report |
| Re-run anchor | Import data change updates downstream report prose. | `tests/test_report_step.py::test_report_step_recomputes_after_import_data_changes` | pass |
| Re-run anchor | Reverse-code parameter changes update compose, reliability, comparison, and report outputs. | `tests/test_modes_and_preferences.py::test_reference_slice_reverse_code_param_change_updates_downstream_report` | pass |
| Reference workflow | Guided and Standard modes build identical engine steps. | `tests/test_modes_and_preferences.py::test_guided_and_standard_modes_create_the_same_engine_steps` | pass |
| Reference workflow | Preferences are snapshotted at Step creation. | `tests/test_modes_and_preferences.py::test_step_params_snapshot_preferences_at_creation_time` | pass |
| Reference workflow | Full reference slice runs end-to-end in both Guided and Standard modes. | `tests/test_modes_and_preferences.py::test_reference_slice_runs_end_to_end_in_guided_and_standard_modes` | pass |
| Reference workflow | One-click re-run updates final report after source data changes. | `tests/test_modes_and_preferences.py::test_reference_slice_one_click_rerun_updates_final_report` | pass |
| Runtime | Installed package imports outside the project working directory. | `tests/test_runtime_environment.py::test_installed_package_imports_from_non_project_working_directory` | pass |
| Runtime | Cache directory resolution returns absolute directories and falls back when configured path is a file. | `tests/test_runtime_environment.py::test_cache_dir_returns_absolute_configured_directory`, `tests/test_runtime_environment.py::test_cache_dir_falls_back_when_configured_path_is_file` | pass |
| Static security | Bandit scan reports no issues in `src`. | `.venv\Scripts\python.exe -m bandit -r src -f txt` | pass as of latest run |
| Dependency security | `pip check` reports no broken requirements; `pip-audit --local` reports no known vulnerabilities except local package skip. | `.venv\Scripts\python.exe -m pip check`; `.venv\Scripts\pip-audit.exe --local --cache-dir .pip-audit-cache` | pass as of latest run |
| Manual security review | Local desktop threat model and code-path review covers project JSON, pipeline ownership, StepResult shape, import/data-prep boundaries, statistics input boundaries, report filesystem writes, and dependency/static scan limits. | `docs/specs/01-security-review.md` | pass for manual review; not a delegated Deep Security Scan |
| Formal delegated Deep Security Scan | Codex Security Deep Security Scan runs through preflight, six usable independent discovery workers, canonical no-candidate merge, deterministic report generation, and app completion. | scan id `0632e745-0675-473d-863c-e9722867a2f3`; report `C:\Users\V\AppData\Local\Temp\codex-security-scans-hhPXV4\TongTong\unversioned_20260625T173550Z_i7fqmzt0\report.md`; status `complete`; finding count `0` | pass |

## Remaining perfection gaps

No open validation blocker is currently recorded for Slice #01 core after the
formal delegated Deep Security Scan closure.

| Gap | Reason it matters | Required closure evidence |
| --- | --- | --- |
| None currently recorded | N/A | N/A |
