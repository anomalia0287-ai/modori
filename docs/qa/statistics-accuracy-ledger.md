# Statistics Accuracy Ledger

Status: working accuracy record for `release/readiness-1-9`.

Last updated: 2026-07-08 KST.

This ledger separates three claims:

- Recommendation quality: whether Modori suggests a defensible analysis candidate.
- Calculation accuracy: whether a selected analysis computes the expected statistic, effect size, confidence interval, and validation behavior.
- Presentation accuracy: whether tables, Korean/English prose, and UI surfaces report the calculated result without changing meaning.

Numerical-analysis literature and implementation obligations are mapped in
`docs/qa/statistics-numerical-accuracy-literature.md`.
Closure criteria and remaining risk categories are tracked in
`docs/qa/statistics-accuracy-closure-matrix.md`.

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

`descriptives_table1` computes scale means and sample standard deviations from
Decimal values built from the original non-missing cell representations, while
median/min/max still follow the float64 summary path. Public DTO values remain
plain floats. Boolean values in SCALE columns fail closed instead of being
silently treated as `1`/`0`.

Bootstrap percentile CI checks with the same seed and resampling algorithm are
recorded as deterministic bootstrap reproduction, not independent accuracy
proof. Independent bootstrap adequacy requires either cross-engine resampling
with controlled indices or a documented simulation/coverage fixture. Rendered
text and rounded table values are verified separately from raw result-object
values.

## Current High-Risk Coverage

| Module | Reference Basis | Edge Coverage | Known Limits | Next Accuracy Work |
| --- | --- | --- | --- | --- |
| `repeated_measures_anova` | Manual wide-format ANOVA decomposition, SciPy F survival function, Pingouin sphericity/epsilon references. | Schema migration, duplicate and missing variable rejection, measure-type validation, non-numeric rejection, zero-variance rejection, Greenhouse-Geisser corrected df/p-value, listwise-missing complete-case parity, centered SS decomposition, large additive-offset audit. | No central ChartSpec rendering hook yet; optional R parity is not required in the default gate. | Add Huynh-Feldt explicit policy parity and imbalanced missing-pattern fixtures. |
| `friedman` | SciPy `friedmanchisquare`, Pingouin Kendall W reference. | Schema migration, duplicate and missing variable rejection, posthoc/p-adjust rejection, measure-type validation, non-numeric rejection, listwise-missing complete-case parity, tied-rank policy disclosure, chi-square approximation warning limited to small repeated designs (`n <= 13` and `k <= 4`). | Posthoc is intentionally `none` only; no central ChartSpec rendering hook yet. R `friedman.test` anchor is not yet ledger-complete. | Add optional R `friedman.test` golden output and posthoc design before enabling pairwise comparisons. |
| `mediation` | Independent OLS coefficient calculation and deterministic bootstrap reproduction for the current percentile method. | Schema migration, duplicate role rejection, non-scale rejection, unsupported standardization rejection, singular model rejection, OLS condition-number rejection, SVD-backed OLS covariance without normal-equation inverse, user-facing bootstrap default `5000`, warning below `1000`. | Supports observed-variable simple mediation only; serial/latent mediation is outside current scope. Deterministic bootstrap reproduction is not interval adequacy proof. | Add missing-row parity, no-covariate parity, independent interval adequacy checks, and cross-engine mediation references. |
| `moderated_mediation` | Independent OLS point-effect references for PROCESS-style Model 7 and Model 14; deterministic bootstrap reproduction for Model 7. | Schema migration, unsupported model rejection, duplicate role rejection, non-scale rejection, unsupported centering rejection, OLS interaction condition-number rejection, shared SVD-backed OLS covariance helper, user-facing bootstrap default `5000`, warning below `1000`. | Supports Model 7 and Model 14 only; Johnson-Neyman and latent models are outside current scope. Model 14 still needs deterministic CI reproduction. Deterministic bootstrap reproduction is not interval adequacy proof. | Add Model 14 deterministic CI reproduction, missing-row parity, independent interval adequacy checks, and cross-engine moderated-mediation references. |
| `ancova` | Module tests cover ANCOVA table, adjusted means, homogeneity checks, and validation behavior. | Group/covariate validation, covariate overlap rejection, model-shape validation, full-rank near-collinearity rejection through the shared OLS condition-number gate, centered-y OLS fitting with adjusted-mean offset restoration, large outcome-offset audit. | Broader parity against R `car`/`emmeans` is not yet ledger-complete. | Add R-style golden fixtures for adjusted means and partial eta squared. |
| `regression_ols` | Module tests cover OLS coefficients, categorical interaction behavior, report output, validation behavior, and NIST StRD Longley/Wampler5 certified values. | Categorical interaction fixture, report fixture, singular predictor rejection paths, condition-number diagnostics, ill-conditioned design rejection, centered-y OLS fit with intercept restoration, large outcome-offset audit, Wampler1 perfect-fit fail-closed, Filip numerically unsafe polynomial fail-closed. | Broader diagnostics parity is not yet ledger-complete. | Add heteroskedasticity fixtures and missing-row golden fixtures. |
| `descriptives_table1` | NIST StRD NumAcc4 generated fixture and module tests. | Large-offset mean and sample standard deviation use one shared Decimal-backed conversion and match certified NumAcc4 values. Boolean SCALE values are explicitly rejected. | Median/min/max remain float64 summaries; NumAcc1-3 and autocorrelation are not product-surfaced fixtures yet. | Add NumAcc1-3 where they expose distinct product risk; only add autocorrelation if Modori surfaces it. |
| `factor_pca` | Current tests cover PCA/EFA behavior, eigenvalue/loadings surfaces, and validation paths. | Correlation-matrix validation, singular correlation rejection, condition-number rejection for near-singular correlation matrices, KMO/Bartlett diagnostic handling, deterministic parallel-analysis seed. | KMO inverse sensitivity is now fail-closed for tested near-singular inputs, but high-iteration parallel-analysis policy and cross-engine PCA/EFA references are not ledger-complete. | Add high-iteration parallel-analysis policy and cross-engine PCA/EFA references. |
| `reliability_omega` | Current tests include R-gated omega parity when the R environment is available. | Cronbach alpha paths, corrected item-total correlations, omega singular-correlation rejection, omega condition-number rejection for near-singular item matrices, FactorAnalyzer runtime/user warning fail-closed. | McDonald's omega uses maximum-likelihood factor extraction; Heywood cases and explicit R `psych` golden fixtures for difficult item matrices are not ledger-complete. | Add omega convergence/Heywood fixtures and an explicit R `psych` golden suite for difficult item matrices. |
| `anova_oneway` | SciPy `f_oneway` parity tests, NIST StRD SmLs01/SmLs04/SmLs07 fixtures, and posthoc coverage via statsmodels/Pingouin paths. | Group validation, Levene assumption summaries, omnibus ANOVA, certified df/F/R-squared parity, centered effect-size SS path, large-offset eta/omega stability, posthoc result surfaces, Tukey/Games-Howell p-value source disclosure, studentized-range survival-function policy lock. | `SmLs07` is recorded as achieved float64 precision rather than full 15-digit certified parity. `AtmWtAg` is not imported yet because it is a two-treatment ANOVA fixture and Modori currently routes/validates one-way ANOVA as three-or-more groups. Independent studentized-range edge fixtures are not ledger-complete. | Decide whether two-treatment ANOVA should be accepted before importing `AtmWtAg`; add extreme-tail posthoc fixtures for Tukey/Games-Howell. |
| `rank_based_nonparametric_tests` | Current coverage spans Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, and Spearman through module tests. | Mann-Whitney records tie policy and exact-vs-asymptotic selection; Wilcoxon records zero-difference, tie, correction, and method policy; Kruskal-Wallis, Friedman, and Spearman now record tied-rank/method policy details on Likert-shaped fixtures; Kruskal-Wallis warns on small group sizes where chi-square approximation is weak. | Cross-engine disagreements against R/SPSS/JASP are not ledger-complete. Kruskal-Wallis and Friedman posthoc remain intentionally unsupported. | Add R/SPSS/JASP anchors and explicit small-sample/exact-policy documentation for each rank family. |

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
- Current numerical-policy focus command:
  `pytest -p no:cacheprovider tests/test_descriptives_table1_step.py tests/test_regression_step.py tests/test_regression_categorical_interaction.py tests/test_ancova_step.py tests/test_mediation_step.py tests/test_moderated_mediation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py tests/test_friedman_step.py tests/test_kruskal_wallis_step.py tests/test_anova_oneway_step.py tests/test_factor_pca_step.py tests/test_reliability_step.py tests/test_nist_strd_fixtures.py tests/test_tail_probability_policy.py -q`

## Known Limits

The recommendation layer is heuristic. It can identify candidate analyses from variable metadata, names, cardinality, repeated-measure column patterns, and safe data shape checks, but it does not prove research-design validity. Calculation correctness must remain deterministic and test-backed; SLM assistance must not compute statistics or bypass validators.

The current deterministic bootstrap tests prove repeatable implementation
plumbing. They do not prove percentile interval adequacy or coverage.
