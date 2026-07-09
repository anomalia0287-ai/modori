# Statistics Accuracy Ledger

Status: working accuracy record for `release/readiness-1-9`.

Last updated: 2026-07-09 KST.

This ledger separates three claims:

- Recommendation quality: whether Modori suggests a defensible analysis candidate.
- Calculation accuracy: whether a selected analysis computes the expected statistic, effect size, confidence interval, and validation behavior.
- Presentation accuracy: whether tables, Korean/English prose, and UI surfaces report the calculated result without changing meaning.

Numerical-analysis literature and implementation obligations are mapped in
`docs/qa/statistics-numerical-accuracy-literature.md`.
Closure criteria and remaining risk categories are tracked in
`docs/qa/statistics-accuracy-closure-matrix.md`.

Manual external-GUI evidence is tracked separately in
`docs/qa/jamovi-gui-validation-runbook.md`. jamovi fixture agreement is useful
for reviewer confidence, but it is not a substitute for the automated
calculation gates and does not support SPSS/JASP-equivalent claims.

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
proof. Modori now also has R `lm()` controlled-index bootstrap anchors for
simple mediation and moderated-mediation Model 7/14 percentile CIs; these are
cross-engine parity checks for the same resampled rows, not a blanket proof of
interval adequacy. Independent bootstrap adequacy still requires documented
simulation/coverage fixtures. Rendered text and rounded table values are
verified separately from raw result-object values.

## Current High-Risk Coverage

| Module | Reference Basis | Edge Coverage | Known Limits | Next Accuracy Work |
| --- | --- | --- | --- | --- |
| `repeated_measures_anova` | Manual wide-format ANOVA decomposition, SciPy F survival function, Pingouin sphericity/epsilon references. | Schema migration, duplicate and missing variable rejection, measure-type validation, non-numeric rejection, zero-variance rejection, Greenhouse-Geisser corrected df/p-value, listwise-missing complete-case parity, centered SS decomposition, large additive-offset audit. | No central ChartSpec rendering hook yet; optional R parity is not required in the default gate. | Add Huynh-Feldt explicit policy parity and imbalanced missing-pattern fixtures. |
| `friedman` | SciPy `friedmanchisquare`, Pingouin Kendall W reference, and R `friedman.test` anchor on a tied-rank fixture. | Schema migration, duplicate and missing variable rejection, posthoc/p-adjust rejection, measure-type validation, non-numeric rejection, listwise-missing complete-case parity, tied-rank policy disclosure, chi-square approximation warning limited to small repeated designs (`n <= 13` and `k <= 4`), R-base statistic/df/p parity. | Posthoc is intentionally `none` only; no central ChartSpec rendering hook yet. | Add posthoc design before enabling pairwise comparisons. |
| `mediation` | Independent OLS coefficient calculation, deterministic bootstrap reproduction for the current percentile method, R `lm()` controlled-index percentile-CI parity, and slow known-effect coverage smoke. | Schema migration, duplicate role rejection, non-scale rejection, unsupported standardization rejection, singular model rejection, OLS condition-number rejection, SVD-backed OLS covariance without normal-equation inverse, complete-case missing-row parity, no-covariate parity, user-facing bootstrap default `5000`, warning below `1000`, R controlled-index CI anchor, slow `1000`-resample known-effect coverage smoke behind `scripts/slow_stats_gate.py`. | Supports observed-variable simple mediation only; serial/latent mediation is outside current scope. The slow coverage smoke is adequacy evidence for gross regression detection, not exhaustive interval proof. | Add broader coverage designs only if the product scope expands. |
| `moderated_mediation` | Independent OLS point-effect references for PROCESS-style Model 7 and Model 14; deterministic bootstrap reproduction for Model 7 and Model 14; R `lm()` controlled-index percentile-CI parity for both models; slow known-effect coverage smoke for the Model 7 and Model 14 indexes. | Schema migration, unsupported model rejection, duplicate role rejection, non-scale rejection, unsupported centering rejection, OLS interaction condition-number rejection, shared SVD-backed OLS covariance helper, complete-case Model 7 parity, no-covariate Model 14 parity, user-facing bootstrap default `5000`, warning below `1000`, R controlled-index CI anchors, slow Model 7/14 index coverage smoke behind `scripts/slow_stats_gate.py`. | Supports Model 7 and Model 14 only; Johnson-Neyman and latent models are outside current scope. | Add broader coverage designs only if the product scope expands. |
| `ancova` | Module tests cover ANCOVA table, adjusted means, homogeneity checks, and validation behavior. | Group/covariate validation, covariate overlap rejection, model-shape validation, full-rank near-collinearity rejection through the shared OLS condition-number gate, centered-y OLS fitting with adjusted-mean offset restoration, large outcome-offset audit. | Broader parity against R `car`/`emmeans` is not yet ledger-complete. | Add R-style golden fixtures for adjusted means and partial eta squared. |
| `regression_ols` | Module tests cover OLS coefficients, categorical interaction behavior, report output, validation behavior, and NIST StRD Longley/Wampler5 certified values. | Categorical interaction fixture, report fixture, complete-case missing-row parity, HC3 statsmodels robust-covariance parity, singular predictor rejection paths, condition-number diagnostics, ill-conditioned design rejection, centered-y OLS fit with intercept restoration, large outcome-offset audit, Wampler1 perfect-fit fail-closed, Filip numerically unsafe polynomial fail-closed. | Broader cross-engine diagnostics parity is not yet ledger-complete. | Add broader regression diagnostics only if product scope expands. |
| `compare_groups_t` | Module tests cover Welch and Student t paths; NIST StRD `AtmWtAg` anchors the two-group Student path through certified `F = t^2`. | Welch-first routing, custom/classic Student routing, common-offset centered t-family computation, Welch large-offset formula-oracle fixture, signed Cohen's d, case-count reporting, row-order stability, and NIST `AtmWtAg` certified F parity. | `anova_oneway` still intentionally rejects two-treatment ANOVA; `AtmWtAg` is imported only through the compare-groups t-test identity. | Add broader two-group fixtures only if product scope expands. |
| `descriptives_table1` | NIST StRD NumAcc4 generated fixture and module tests. | Large-offset mean and sample standard deviation use one shared Decimal-backed conversion and match certified NumAcc4 values. Boolean SCALE values are explicitly rejected. | Median/min/max remain float64 summaries; NumAcc1-3 and autocorrelation are not product-surfaced fixtures yet. | Add NumAcc1-3 where they expose distinct product risk; only add autocorrelation if Modori surfaces it. |
| `factor_pca` | Current tests cover PCA/EFA behavior, eigenvalue/loadings surfaces, validation paths, and R `psych`/base-R anchors for KMO, Bartlett, PCA eigenvalues, and PCA loadings. | Correlation-matrix validation, singular correlation rejection, condition-number rejection for near-singular correlation matrices, KMO/Bartlett diagnostic handling, invalid Heywood-like EFA estimate rejection, deterministic parallel-analysis seed, user-facing parallel-analysis default `1000`, warning below `1000`, external R anchor on the public BFI Likert fixture. | EFA loadings remain factor-analyzer parity plus fail-closed policy, not hard R `psych::fa` parity. | Add EFA cross-engine anchors only if EFA claim scope expands. |
| `reliability_omega` | Current tests include R-gated omega parity and R `psych::omega` parity on a public BFI Likert fixture. | Cronbach alpha paths, corrected item-total correlations, omega singular-correlation rejection, omega condition-number rejection for near-singular item matrices, FactorAnalyzer runtime/user warning fail-closed, invalid Heywood-like omega estimate rejection, R `psych` omega anchors for simple and real Likert fixtures. | McDonald's omega uses maximum-likelihood factor extraction and remains method-sensitive across engines; tolerances are intentionally looser than deterministic algebraic statistics. | Add broader omega fixtures only if new item-matrix shapes are added to product claims. |
| `anova_oneway` | SciPy `f_oneway` parity tests, NIST StRD SmLs01/SmLs04/SmLs07 fixtures, a large-offset unbalanced Decimal oracle, and posthoc coverage via statsmodels/Pingouin paths. | Group validation, Levene assumption summaries, omnibus ANOVA, certified df/F/R-squared parity, centered effect-size SS path, large-offset eta/omega stability, unbalanced group-size 50-digit Decimal oracle, posthoc result surfaces, Tukey/Games-Howell p-value source disclosure, studentized-range survival-function policy lock, direct extreme-tail Tukey/Games-Howell fixtures. | `SmLs07` is recorded as achieved float64 precision rather than full 15-digit certified parity. `AtmWtAg` is covered through `compare_groups_t`, but `anova_oneway` still routes/validates one-way ANOVA as three-or-more groups. | Decide whether two-treatment ANOVA should be accepted in `anova_oneway`; add broader posthoc edge fixtures only if product scope expands. |
| `rank_based_nonparametric_tests` | Current coverage spans Mann-Whitney, Wilcoxon, Kruskal-Wallis, Friedman, and Spearman through module tests, plus R base anchors for tied Mann-Whitney, Wilcoxon p-value, Kruskal-Wallis, and Friedman fixtures. | Mann-Whitney records tie policy and exact-vs-asymptotic selection; untied Mann-Whitney exact is used through `min(n) <= 25`; untied `26-49` is an intentional policy difference from R's wider exact default; Wilcoxon records zero-difference, tie, correction, and method policy; Kruskal-Wallis, Friedman, and Spearman now record tied-rank/method policy details on Likert-shaped fixtures; Kruskal-Wallis warns on small group sizes where chi-square approximation is weak; R-base statistic/df/p parity is locked where statistic conventions align. | SPSS/JASP anchors are not included; Kruskal-Wallis and Friedman posthoc remain intentionally unsupported. Public claims must be phrased as R/NIST/formula anchored, not SPSS-equivalent. | Add SPSS/JASP anchors only if external review requires those engines. |

## Release Evidence

- Local calculation-reliability gate:
  `.\.venv\Scripts\python.exe scripts\quality_gate.py --with-slow-stats`
  passed on 2026-07-09 KST with `compileall`, `ruff`, `bandit`,
  `launch-smoke-ok`, full pytest `1015 passed, 4 skipped`, `pip check`, and
  slow statistics pytest `3 passed, 1016 deselected`.
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
  `pytest -p no:cacheprovider tests/test_descriptives_table1_step.py tests/test_regression_step.py tests/test_regression_categorical_interaction.py tests/test_ancova_step.py tests/test_mediation_step.py tests/test_moderated_mediation_step.py tests/test_compare_groups_step.py tests/test_paired_comparison_step.py tests/test_friedman_step.py tests/test_kruskal_wallis_step.py tests/test_anova_oneway_step.py tests/test_factor_pca_step.py tests/test_reliability_step.py tests/test_statistics_numerics.py tests/test_nist_strd_fixtures.py tests/test_tail_probability_policy.py -q`
- Slow bootstrap adequacy smoke:
  `scripts\slow_stats_gate.py` reported `3 passed, 1016 deselected` for
  simple mediation percentile CI and moderated-mediation Model 7/14 index
  known-effect coverage checks.
- R cross-engine reference gate:
  `pytest -q -rs -p no:cacheprovider tests/test_r_cross_engine_references.py tests/test_reliability_step.py::test_mcdonald_omega_matches_r_psych_when_r_is_available tests/test_regression_step.py::test_regression_matches_committed_r_reference_when_r_is_available`
  reported `8 passed` with the workspace-local R runtime.
- jamovi GUI fixture pack:
  `tests/test_jamovi_validation_fixtures.py` locks the expected values used by
  `docs/qa/jamovi-gui-validation-runbook.md`. Manual jamovi screenshots or
  exports are optional external-GUI evidence and should be stored outside git.
- Presentation/report drift check:
  reporting, prose-contract, report-step, UI report binding/export, result
  state, and pipeline result-binding tests passed with `68 passed` after this
  R cross-engine calculation-reliability closure pass.

## Known Limits

The recommendation layer is heuristic. It can identify candidate analyses from variable metadata, names, cardinality, repeated-measure column patterns, and safe data shape checks, but it does not prove research-design validity. Calculation correctness must remain deterministic and test-backed; SLM assistance must not compute statistics or bypass validators.

Public calculation-accuracy claims are limited to the evidence actually present:
NIST StRD, R/base-R or R `psych`/`lm()` anchors, SciPy/statsmodels/Pingouin
library parity, and explicit formula/Decimal oracles. The current release must
not be described as SPSS-equivalent or JASP-equivalent.

The deterministic bootstrap tests prove repeatable implementation plumbing.
The R controlled-index tests prove cross-engine parity for identical resampled
rows. The slow bootstrap coverage smoke adds initial interval-performance
evidence for simple mediation and Model 7/14 index CIs, but it is not exhaustive
proof of every sample size, effect size, or distributional shape.
