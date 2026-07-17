# Test fixtures

## `recommendation_benchmark/`

Deterministic synthetic recommendation benchmark economics pilot.

Use in Modori:

- Exactly 20 study-card cases and 19 CSV files, including a same-data/different-question pair.
- Blank independent reviewer workbooks and a separate adjudication workbook.
- Current A predictions are captured with case, prediction, and source fingerprints.
- The pilot measures labeling time and agreement; it is not accuracy evidence.
- No checked-in case contains real PII or an expert gold label.
- Human procedure: `docs/qa/recommendation-benchmark-pilot-runbook.md`.
- Controlled vocabulary: `docs/qa/recommendation-benchmark-annotation-guide.md`.

## `psych_bfi.csv`

Source: Rdatasets mirror of the R `psych` package `bfi` dataset.

Original CSV URL:
`https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/psych/bfi.csv`

Documentation URL:
`https://vincentarelbundock.github.io/Rdatasets/doc/psych/bfi.html`

Use in Modori:

- Public self-report survey fixture for Slice #01 end-to-end validation.
- Agreeableness key used by the test: `-A1, A2, A3, A4, A5`.
- Reverse-code range: 1 to 6.
- Group variable: `gender`.

## `jamovi/*.csv`

Small manual GUI-validation fixtures for jamovi 2.7.x.

Use in Modori:

- Optional external-GUI evidence only; these fixtures do not replace automated
  NIST/R/Decimal/formula-oracle tests.
- The manual runbook is `docs/qa/jamovi-gui-validation-runbook.md`.
- Covered analyses: independent t, Mann-Whitney, Wilcoxon signed-rank,
  one-way ANOVA, Kruskal-Wallis, multiple regression, and Pearson correlation.
- Expected values are locked by `tests/test_jamovi_validation_fixtures.py`.
- Evidence from these files supports "jamovi GUI representative fixture
  agreement" only, not SPSS/JASP-equivalent breadth.

## `logistic_regression/*.csv`

Deterministic, synthetic, overlapping binary-logistic fixtures.

Use in Modori:

- `continuous.csv` has two ordinary-scale numeric predictors and repeated
  predictor patterns containing both outcomes; the test derives a fixed
  five-row complete-case-missingness variant from it.
- `categorical.csv` has one numeric predictor and three category levels in a
  deliberately nonalphabetic source order; R and Modori both pin `control` as
  the reference and use the declared order `control`, `treat`, `placebo`.
- Both fixtures have at least 20 observations in each outcome class and are
  anchored to R base `glm`; the continuous fixture is also checked with an
  independent 80-decimal-digit `mpmath` Newton oracle.
- `reference-metadata.json` pins fixture/reference-script hashes, runtime
  versions, achieved maximum differences, and the enforced tolerance ceilings.
- Large-offset behavior is tested separately through shift invariance and the
  scaled operational path. Direct large-offset R fitting is not treated as an
  accuracy oracle because its original-scale design is cancellation-sensitive.

## `factorial_anova/*.csv`

Deterministic synthetic complete-cell 2-by-3 factorial ANOVA fixtures.

Use in Modori:

- `balanced-2x3.csv` has six rows per cell and is checked against independent
  corrected two-way sums, base R, and statsmodels Sum-contrast Type III.
- `unbalanced-2x3.csv` fixes A-major/B-fast cell counts at
  `(5, 11, 7, 13, 4, 9)` and anchors the equal-cell-weight estimand.
- `moderate-offset-2x3.csv` is the same unbalanced data plus `100`; its
  location-to-pooled-SD ratio remains at or below the frozen comparator limit.
- Every outcome and residual is a multiple of `0.125`, so adding `1e12` does
  not change the float-delivered within-cell distinctions. The derived extreme
  fixture is compared only with an explicit-rational 80-digit mpmath oracle.
- R uses base `lm`, `contr.sum`, and coefficient-block Wald forms. It does not
  call a Type III convenience package.
- `reference-metadata.json` pins source hashes, runtime versions, achieved
  differences, tolerance ceilings, and the boundary that R/statsmodels are
  implementation comparators rather than extreme-offset truth sources.

## `nist/*.csv`

Source: NIST/ITL Statistical Reference Datasets, linear least-squares
regression datasets.

Dataset URLs:
`https://www.itl.nist.gov/div898/strd/lls/data/Longley.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/Wampler5.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/Wampler1.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/Filip.shtml`

Certified values URLs:
`https://www.itl.nist.gov/div898/strd/lls/data/LINKS/v-Longley.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/LINKS/v-Wampler5.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/LINKS/v-Wampler1.shtml`
`https://www.itl.nist.gov/div898/strd/lls/data/LINKS/v-Filip.shtml`

Use in Modori:

- Regression numerical-accuracy fixtures for high-condition-number OLS,
  polynomial regression, perfect-fit rejection, and numerically unsafe design
  rejection.
- Certified coefficient, standard-error, R-squared, and F-statistic values are
  stored beside each CSV in `nist/*-certified.json`.

NIST StRD univariate summary-statistics source:
`https://www.itl.nist.gov/div898/strd/univ/numacc4.html`

Certified values and construction rule:
`https://www.itl.nist.gov/div898/strd/univ/certvalues/numacc4.html`
`https://www.itl.nist.gov/div898/strd/univ/addinfo/numacc4.html`

Use in Modori:

- `NumAcc4` is generated inside `tests/test_nist_strd_fixtures.py` from the
  official construction rule: one `10000000.2`, followed by 500 pairings of
  `10000000.1` and `10000000.3`.
- This locks large-offset mean and sample standard-deviation accuracy for
  `descriptives_table1` without checking in a repetitive 1001-line data file.

NIST StRD one-way ANOVA sources:
`https://www.itl.nist.gov/div898/strd/anova/SmLs01.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs04.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs07.html`
`https://www.itl.nist.gov/div898/strd/anova/AtmWtAg.html`

Certified values and construction rules:
`https://www.itl.nist.gov/div898/strd/anova/SmLs01_cv.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs01_info.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs04_cv.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs04_info.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs07_cv.html`
`https://www.itl.nist.gov/div898/strd/anova/SmLs07_info.html`
`https://www.itl.nist.gov/div898/strd/anova/AtmWtAg_cv.html`
`https://www.itl.nist.gov/div898/strd/anova/AtmWtAg_info.html`

Use in Modori:

- `SmLs01`, `SmLs04`, and `SmLs07` are generated inside
  `tests/test_nist_strd_fixtures.py` from the official construction rule for
  one-way balanced ANOVA.
- `SmLs04` locks the 7-constant-leading-digit cancellation regime.
- `SmLs07` locks the 13-constant-leading-digit regime as achieved float64
  precision, not full 15-digit certified parity.
- `AtmWtAg` is committed as an in-test observed-data fixture for
  `compare_groups` Student t. The certified one-way ANOVA `F` is checked
  through the two-group identity `F = t^2`; this does not change
  `anova_oneway`'s current three-or-more-group product policy.
- The SmLs fixtures lock certified df, F statistic, and
  R-squared/effect-size behavior for `anova_oneway` without checking in
  repetitive generated data files. `AtmWtAg` locks the certified two-group
  identity through `compare_groups`.
