# Statistics Accuracy Ledger

Status: working accuracy record for `release/readiness-1-9`.

Last updated: 2026-07-08 KST.

This ledger separates three claims:

- Recommendation quality: whether Modori suggests a defensible analysis candidate.
- Calculation accuracy: whether a selected analysis computes the expected statistic, effect size, confidence interval, and validation behavior.
- Presentation accuracy: whether tables, Korean/English prose, and UI surfaces report the calculated result without changing meaning.

Numerical-analysis literature and implementation obligations are mapped in
`docs/qa/statistics-numerical-accuracy-literature.md`.

## Tolerance Policy

Default numeric tolerance for deterministic statistics is `abs <= 1e-10` unless a test documents a tighter or looser reason. Sphericity, p-values, sums of squares, coefficients, and effect sizes prefer `abs <= 1e-12` when the reference path is deterministic and library-compatible. Bootstrap percentile CI checks use fixed seeds and compare to independent resampling references with `abs <= 1e-10` where the test owns the resampling algorithm. Rendered text and rounded table values are verified separately from raw result-object values.

## Current High-Risk Coverage

| Module | Reference Basis | Edge Coverage | Known Limits | Next Accuracy Work |
| --- | --- | --- | --- | --- |
| `repeated_measures_anova` | Manual wide-format ANOVA decomposition, SciPy F survival function, Pingouin sphericity/epsilon references. | Schema migration, duplicate and missing variable rejection, measure-type validation, non-numeric rejection, zero-variance rejection, Greenhouse-Geisser corrected df/p-value, listwise-missing complete-case parity. | No central ChartSpec rendering hook yet; optional R parity is not required in the default gate. | Add Huynh-Feldt explicit policy parity and imbalanced missing-pattern fixtures. |
| `friedman` | SciPy `friedmanchisquare`, Pingouin Kendall W reference. | Schema migration, duplicate and missing variable rejection, posthoc/p-adjust rejection, measure-type validation, non-numeric rejection, listwise-missing complete-case parity. | Posthoc is intentionally `none` only; no central ChartSpec rendering hook yet. | Add tied-rank heavy fixtures and optional R `friedman.test` golden output. |
| `mediation` | Independent OLS coefficient calculation and deterministic percentile bootstrap reference. | Schema migration, duplicate role rejection, non-scale rejection, unsupported standardization rejection, singular model rejection. | Supports observed-variable simple mediation only; serial/latent mediation is outside current scope. | Add missing-row parity, no-covariate parity, and larger bootstrap stability fixtures. |
| `moderated_mediation` | Independent OLS point-effect references for PROCESS-style Model 7 and Model 14; independent percentile bootstrap CI parity for Model 7. | Schema migration, unsupported model rejection, duplicate role rejection, non-scale rejection, unsupported centering rejection. | Supports Model 7 and Model 14 only; Johnson-Neyman and latent models are outside current scope. | Add independent bootstrap CI parity for Model 14, missing-row parity, and singular interaction fixtures. |
| `ancova` | Module tests cover ANCOVA table, adjusted means, homogeneity checks, and validation behavior. | Group/covariate validation, covariate overlap rejection, model-shape validation. | Broader parity against R `car`/`emmeans` is not yet ledger-complete. | Add R-style golden fixtures for adjusted means and partial eta squared. |
| `regression_ols` | Module tests cover OLS coefficients, categorical interaction behavior, report output, and validation behavior. | Categorical interaction fixture, report fixture, singular predictor rejection paths. | Broader diagnostics parity is not yet ledger-complete. | Add multicollinearity, heteroskedasticity, and missing-row golden fixtures. |

## Release Evidence

- Host quality gate:
  `scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch`
  reported `947 passed, 3 skipped`, `package-tool-ok`,
  `package-launch-smoke-ok`, `package-engine-smoke-ok`, and
  `package-public-data-smoke-ok`.
- Clean VM engine smoke:
  `Run-Engine-Smoke-XLSX.bat` returned exit code `0`, `ok: true`,
  `status: ready`, and `v1_statistics_smoke.ok: true` across 20 checks.
- Focus command for high-risk module accuracy:
  `pytest -p no:cacheprovider tests/test_repeated_measures_anova_step.py tests/test_friedman_step.py tests/test_mediation_step.py tests/test_moderated_mediation_step.py -q`

## Known Limits

The recommendation layer is heuristic. It can identify candidate analyses from variable metadata, names, cardinality, repeated-measure column patterns, and safe data shape checks, but it does not prove research-design validity. Calculation correctness must remain deterministic and test-backed; SLM assistance must not compute statistics or bypass validators.
