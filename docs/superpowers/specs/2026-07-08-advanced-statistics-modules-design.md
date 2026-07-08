# Advanced Statistics Modules Design - 2026-07-08

## Goal

Add four executable, contract-gated statistical modules to Modori:

- `repeated_measures_anova`
- `friedman`
- `mediation`
- `moderated_mediation`

The modules must satisfy the existing analysis-module contract before exposure:
versioned params, unknown-param rejection, executable registry specs, module-local
result DTOs, deterministic Korean-first reporting, UI/run-validation coverage,
package smoke coverage, and reference tests against trusted R/Python sources.

## Runtime Boundary

The shipped Modori engine remains Python-native. R 4.6.1 and the installed CRAN
packages are used as reference tooling for golden tests and development
verification, not as a required runtime dependency for packaged users.

Available R reference packages on the main PC:

- `psych 2.6.5`
- `sandwich 3.1.1`
- `lavaan 0.6.21`
- `mediation 4.5.1`
- `afex 1.5.1`
- `ez 4.5.0`
- `emmeans 2.0.3`
- `manymome 0.3.6`
- `RMediation 1.5.0`

## Shared Contract Rules

Every new Step uses `CURRENT_SCHEMA_VERSION = 1`.

Every new Step rejects params with:

- missing `schema_version`;
- boolean or non-integer `schema_version`;
- newer `schema_version`;
- unknown params;
- duplicated variable roles.

Every new result DTO lives in a module-local file. `src/modori/results.py` remains
for legacy/shared DTOs only.

Every new reporting function lives in a module-local reporting file. The central
`reporting.py` dispatch may import and call these functions, but the statistics
and tables stay module-local.

All report prose is Korean-first and deterministic. Cross-sectional mediation
and moderated mediation results must avoid causal language unless future design
metadata explicitly justifies causal wording. The first version does not include
causal-design metadata, so the prose uses association/process wording.

## Repeated-Measures ANOVA

Step type: `stats.repeated_measures_anova`.

Input format: wide format. One row is one participant/unit. Each repeated
condition or time point is a separate variable.

Params:

- `schema_version`: `1`
- `measures`: ordered list of three or more variable keys
- `within_factor`: non-empty display name, default filled by UI as `condition`
- `level_labels`: optional list of display labels with the same length as
  `measures`
- `correction`: `auto`, `none`, `greenhouse_geisser`, or `huynh_feldt`
- `sphericity_alpha`: finite float in `(0, 1)`, default `0.05`
- `language`: `ko` or `en`

Supported data:

- all repeated variables are `scale` or `ordinal`;
- repeated variables are numeric and finite after missing-code normalization;
- at least three complete subjects after listwise deletion;
- each repeated variable has non-zero variance;
- residual error degrees of freedom are positive.

Statistics:

- one-way repeated-measures ANOVA from sums of squares;
- Mauchly sphericity test through `pingouin.sphericity`;
- Greenhouse-Geisser epsilon through `pingouin.epsilon`;
- corrected degrees of freedom and corrected p-value when correction policy
  requires it;
- partial eta squared;
- level summaries with N, mean, SD, median.

Fail-closed cases:

- long-format data without an explicit reshape step;
- two-level paired design, which belongs to paired comparison;
- more than one within-subject factor;
- mixed within-between ANOVA;
- missing sphericity diagnostics for three or more levels;
- non-finite statistics.

Reference tests:

- compare F, df, p, epsilon, and sphericity values against `pingouin`;
- compare the same fixture against R `afex::aov_ez`/`ez::ezANOVA` where the R
  package output is stable for the chosen fixture.

## Friedman

Step type: `stats.friedman`.

Input format: wide format, identical row/level semantics to repeated-measures
ANOVA.

Params:

- `schema_version`: `1`
- `measures`: ordered list of three or more variable keys
- `within_factor`: non-empty display name
- `level_labels`: optional list of display labels with the same length as
  `measures`
- `posthoc_method`: `none` in the first version
- `p_adjust`: `none` in the first version
- `language`: `ko` or `en`

Supported data:

- all repeated variables are `scale` or `ordinal`;
- repeated variables are numeric and finite after missing-code normalization;
- at least three complete subjects;
- at least three repeated levels.

Statistics:

- Friedman chi-square statistic and p-value through `scipy.stats.friedmanchisquare`;
- Kendall's W as `chi_square / (n_subjects * (k_levels - 1))`;
- per-level median, mean rank, mean, SD, and N.

Fail-closed cases:

- verified post-hoc tests before their reference tests exist;
- automatic p adjustment before the adjustment policy is specified;
- fewer than three levels;
- no complete subject rows.

Reference tests:

- compare statistic and p-value against SciPy;
- compare statistic, p-value, and Kendall's W against `pingouin.friedman` and R
  `friedman.test` for the committed fixture.

## Mediation

Step type: `stats.mediation`.

Scope: simple observed-variable mediation equivalent to PROCESS Model 4 for one
predictor X, one mediator M, and one outcome Y.

Params:

- `schema_version`: `1`
- `x`: predictor key
- `mediator`: mediator key
- `y`: outcome key
- `covariates`: ordered list of covariate keys, default `[]`
- `bootstrap`: object with `iterations`, `seed`, and `ci`
- `standardize`: `false` in the first version
- `language`: `ko` or `en`

Supported data:

- X, M, Y, and covariates are scale variables;
- numeric finite data after listwise deletion;
- more complete rows than estimated parameters in both path models;
- non-zero variance for all model variables;
- full-rank design matrices.

Statistics:

- path `a`: OLS M on X and covariates;
- path `b` and direct effect `c_prime`: OLS Y on X, M, and covariates;
- total effect `c`: OLS Y on X and covariates;
- indirect effect `a*b`;
- bootstrap percentile confidence interval for `a*b`;
- model R-squared values and complete/excluded case counts.

Fail-closed cases:

- binary/ordinal outcomes;
- categorical X or M;
- multiple mediators;
- serial mediation;
- latent-variable mediation;
- moderated paths;
- causal wording in report prose.

Reference tests:

- compare path coefficients against independent statsmodels OLS;
- compare indirect effect and bootstrap CI against a deterministic committed
  reference generated with R `mediation` or `lavaan` for the chosen fixture.

## Moderated Mediation

Step type: `stats.moderated_mediation`.

Scope: observed-variable moderated mediation for PROCESS-style Model 7 and Model
14 only.

- Model 7: W moderates the `a` path, `M ~ X + W + X:W + covariates`.
- Model 14: W moderates the `b` path, `Y ~ X + M + W + M:W + covariates`.

Params:

- `schema_version`: `1`
- `model`: `7` or `14`
- `x`: predictor key
- `mediator`: mediator key
- `moderator`: moderator key
- `y`: outcome key
- `covariates`: ordered list of covariate keys, default `[]`
- `bootstrap`: object with `iterations`, `seed`, and `ci`
- `moderator_values`: `mean_sd` in the first version
- `center`: `mean`
- `language`: `ko` or `en`

Supported data:

- X, M, W, Y, and covariates are scale variables;
- numeric finite data after listwise deletion;
- complete rows exceed estimated parameters;
- all model variables have non-zero variance;
- model matrices are full rank.

Statistics:

- OLS path models for the selected PROCESS-style template;
- conditional indirect effects at W mean minus 1 SD, mean, and mean plus 1 SD;
- bootstrap percentile CIs for each conditional indirect effect;
- index of moderated mediation with bootstrap percentile CI;
- complete/excluded case counts and model R-squared values.

Fail-closed cases:

- unsupported PROCESS model numbers;
- categorical moderators;
- Johnson-Neyman regions;
- latent-variable models;
- more than one moderator;
- binary/ordinal outcomes;
- causal wording in report prose.

Reference tests:

- compare path coefficients against independent statsmodels OLS;
- compare conditional indirect effects and the index of moderated mediation
  against deterministic R `manymome`/`lavaan` reference output for the committed
  fixture.

## Recommendation Policy

Repeated-measures ANOVA and Friedman are `candidate` modules when the dataset has
three or more same-prefix numeric variables that look like repeated conditions.

Mediation and moderated mediation are `caution_only`. The recommendation service
may surface them as cautious candidates only when the variable pattern is
unambiguous. They must not become the default recommendation in the first
version.

## UI Exposure

The first UI exposure is through the existing analysis selection command and run
validation surfaces. The QML guide rail can expose simple text inputs, but the
engine contract must not depend on QML.

Required command builders:

- `repeated_measures_anova(measures_text)`
- `friedman(measures_text)`
- `mediation(x_key, mediator_key, y_key, covariate_keys_text)`
- `moderated_mediation(model, x_key, mediator_key, moderator_key, y_key, covariate_keys_text)`

## Release Evidence

The package engine smoke must include all four modules. The smoke evidence must
fail if any new module cannot compute a deterministic result from a synthetic
fixture.

The release-readiness checklist must include the new modules, their reference
test commands, and the R reference package versions used for validation.
