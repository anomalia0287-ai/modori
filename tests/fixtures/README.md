# Test fixtures

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
