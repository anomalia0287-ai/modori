# Descriptives Table 1 Contract Evidence

Date: 2026-07-07

## Scope

- Scale summaries: N, missing N, mean, sample SD, median, min, max.
- Nominal/ordinal summaries: N, missing N, category count, category percent.
- Optional nominal/ordinal grouping variable.
- Korean-first report prose and table output.
- Module-owned recommendation eligibility for imported datasets with usable variables.

## Explicitly Unsupported

- Weights
- Complex samples
- Multiple imputation
- Standardized mean differences
- Baseline imbalance claims
- Causal, treatment, or control-group interpretation

## Verification

- `tests/test_analysis_catalog_module_specs.py`
- `tests/test_analysis_module_contract.py`
- `tests/test_descriptives_table1_step.py`
- `tests/test_descriptives_table1_reporting.py`
- `tests/test_descriptives_table1_recommendation.py`
- `tests/test_knowledge_library.py`
- `tests/ui/test_recommendations.py`
- `tests/ui/test_controller.py`
- `tests/ui/test_end_to_end_ui_flow.py`
- `tests/ui/test_result_surface_qml.py`

## Determinism

- Variable order follows `params["variables"]`.
- Group order follows metadata value labels, then normalized lexical order.
- Category order follows metadata value labels, then normalized lexical order.
- The recommendation provider limits default variables to the first 20 usable variables in dataset order.

## Replay

- Params require `schema_version: 1`.
- Newer schema versions are rejected.
- Missing schema versions are rejected for this new module.
- Unknown params are rejected after migration.

## Help Key

- `analysis.descriptives_table1` resolves to `descriptives-table1`.
- The knowledge entry states descriptive-only scope, missing-denominator rules, and V1 exclusions.

## Latest Gate

- `.\.venv\Scripts\python.exe scripts\quality_gate.py`
- Result on 2026-07-07: `713 passed, 2 skipped`; compileall, ruff, bandit, launch smoke, pytest, and pip check passed.
