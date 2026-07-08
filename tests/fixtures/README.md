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
