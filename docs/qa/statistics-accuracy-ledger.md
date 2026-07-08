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

Default numeric tolerance for bounded deterministic statistics is `abs <=
1e-10` unless a test documents a tighter or looser reason. P-values,
correlations, standardized effects, proportions, and sphericity diagnostics
prefer `abs <= 1e-12` when the reference path is deterministic and
library-compatible.

Scale-dependent statistics use mixed tolerance. Large sums of squares,
regression coefficients, covariance estimates, and NIST StRD large-offset
fixtures must declare both an absolute floor and a relative tolerance, usually
`rel <= 1e-12` for certified deterministic values unless the reference source
requires otherwise.

Bootstrap percentile CI checks with the same seed and resampling algorithm are
recorded as deterministic bootstrap reproduction, not independent accuracy
proof. Independent bootstrap adequacy requires either cross-engine resampling
with controlled indices or a documented simulation/coverage fixture. Rendered
text and rounded table values are verified separately from raw result-object
values.

## Current High-Risk Coverage

| Module | Reference Basis | Edge Coverage | Known Limits | Next Accuracy Work |
| --- | --- | --- | --- | --- |
| `repeated_measures_anova` | Manual wide-format ANOVA decomposition, SciPy F survival function, Pingouin sphericity/epsilon references. | Schema migration, duplicate and missing variable rejection, measure-type validation, non-numeric rejection, zero-variance rejection, Greenhouse-Geisser corrected df/p-value, listwise-missing complete-case parity. | No central ChartSpec rendering hook yet; optional R parity is not required in the default gate. | Add Huynh-Feldt explicit policy parity and imbalanced missing-pattern fixtures. |
| `friedman` | SciPy `friedmanchisquare`, Pingouin Kendall W reference. | Schema migration, duplicate and missing variable rejection, posthoc/p-adjust rejection, measure-type validation, non-numeric rejection, listwise-missing complete-case parity. | Posthoc is intentionally `none` only; no central ChartSpec rendering hook yet. | Add tied-rank heavy fixtures and optional R `friedman.test` golden output. |
| `mediation` | Independent OLS coefficient calculation and deterministic bootstrap reproduction for the current percentile method. | Schema migration, duplicate role rejection, non-scale rejection, unsupported standardization rejection, singular model rejection. | Supports observed-variable simple mediation only; serial/latent mediation is outside current scope. The owned OLS helper currently needs an explicit condition-number policy before covariance estimates can be called robust under near-collinearity. | Add condition-number rejection/reporting, missing-row parity, no-covariate parity, user-facing bootstrap default/floor policy, and independent interval adequacy checks. |
| `moderated_mediation` | Independent OLS point-effect references for PROCESS-style Model 7 and Model 14; deterministic bootstrap reproduction for Model 7. | Schema migration, unsupported model rejection, duplicate role rejection, non-scale rejection, unsupported centering rejection. | Supports Model 7 and Model 14 only; Johnson-Neyman and latent models are outside current scope. `x` and moderator are mean-centered before interaction terms; Model 14 still needs explicit policy tests around the mediator-by-centered-moderator term and covariance conditioning. | Add Model 14 deterministic CI reproduction, missing-row parity, condition-number rejection/reporting, singular interaction fixtures, and independent interval adequacy checks. |
| `ancova` | Module tests cover ANCOVA table, adjusted means, homogeneity checks, and validation behavior. | Group/covariate validation, covariate overlap rejection, model-shape validation. | Broader parity against R `car`/`emmeans` is not yet ledger-complete. | Add R-style golden fixtures for adjusted means and partial eta squared. |
| `regression_ols` | Module tests cover OLS coefficients, categorical interaction behavior, report output, and validation behavior. | Categorical interaction fixture, report fixture, singular predictor rejection paths. | Broader diagnostics parity is not yet ledger-complete. | Add multicollinearity, heteroskedasticity, and missing-row golden fixtures. |
| `factor_pca` | Current tests cover PCA/EFA behavior, eigenvalue/loadings surfaces, and validation paths. | Correlation-matrix validation, singular correlation rejection, KMO/Bartlett diagnostic handling, deterministic parallel-analysis seed. | Near-singular correlation matrices, KMO inverse sensitivity, ML factor extraction convergence, and parallel-analysis iteration adequacy are not ledger-complete. | Add near-singular correlation fixtures, KMO failure fixtures, high-iteration parallel-analysis policy, and cross-engine PCA/EFA references. |
| `reliability_omega` | Current tests include R-gated omega parity when the R environment is available. | Cronbach alpha paths, corrected item-total correlations, omega singular-correlation rejection. | McDonald's omega uses maximum-likelihood factor extraction; Heywood cases, convergence failures, and near-singular item matrices are not ledger-complete. | Add omega convergence/Heywood fixtures and an explicit R `psych` golden suite for difficult item matrices. |
| `anova_oneway` | SciPy `f_oneway` parity tests and posthoc coverage via statsmodels/SciPy paths. | Group validation, Levene assumption summaries, omnibus ANOVA, posthoc result surfaces. | Studentized-range tail behavior for Tukey/Tukey-Kramer/Games-Howell is not ledger-complete. | Add NIST StRD ANOVA fixtures and studentized-range posthoc tail fixtures. |
| `rank_based_nonparametric_tests` | Current coverage spans Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, and Spearman through module tests. | Rank methods already appear in comparison, paired comparison, Kruskal-Wallis, Friedman, and correlation modules. | Likert-heavy ties, Wilcoxon zero-difference policy, exact-vs-asymptotic selection, continuity correction, and cross-engine disagreements are not ledger-complete. | Add tied-rank fixtures, zero-difference policy fixtures, small-sample exact/asymptotic fixtures, and R/SPSS/JASP anchors. |

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

The current deterministic bootstrap tests prove repeatable implementation
plumbing. They do not prove percentile interval adequacy or coverage.
