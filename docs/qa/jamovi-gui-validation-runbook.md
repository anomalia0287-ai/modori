# jamovi GUI Validation Runbook

Status: optional external-GUI evidence pack for calculation reliability.

Date: 2026-07-09 KST.

Installed local version observed on this workstation:

```text
C:\Program Files\jamovi 2.7.37.0\bin\jamovi.exe
```

## Scope

This runbook is a manual GUI cross-check. It does not replace the automated
NIST, R, Decimal, formula-oracle, or dependency-parity gates. It supports only
the narrower claim that representative Modori fixtures agree with jamovi's
visible GUI output to ordinary displayed precision.

Do not use this evidence to claim SPSS-equivalent or JASP-equivalent breadth.

## Evidence Folder

Create a folder such as:

```text
C:\Users\V\Desktop\Modori-jamovi-evidence-2026-07-09
```

For each fixture below, save either a screenshot or exported jamovi output using
the suggested filename. A screenshot is enough if it clearly shows the test
name, statistic, df when present, and p-value.

## Fixtures And Expected Values

| Fixture | jamovi Analysis | Expected Values |
| --- | --- | --- |
| `tests\fixtures\jamovi\independent_t.csv` | Independent Samples T-Test, `score` by `group`, Welch/Student equal here | `t = -4.714`, `df = 18.000`, `p = 0.000173` |
| `tests\fixtures\jamovi\mann_whitney_tied.csv` | Independent Samples T-Test with Mann-Whitney option | `U = 11.000`, asymptotic continuity-corrected `p = 0.285844` in Modori/R/SciPy policy. If jamovi reports a different p-value, record the exact jamovi option label because exact/asymptotic defaults can differ. |
| `tests\fixtures\jamovi\paired_wilcoxon.csv` | Paired Samples T-Test with Wilcoxon option, `post` paired with `pre` | Modori/R/SciPy policy: smaller signed-rank statistic `W = 0.000`, continuity-corrected asymptotic `p = 0.057907`. R displays the positive-rank statistic as `V = 15`; both are the same ranking convention with opposite statistic label. |
| `tests\fixtures\jamovi\anova_balanced.csv` | One-Way ANOVA, `score` by `arm` | `F = 27.000`, `df1 = 2`, `df2 = 6`, `p = 0.001000` |
| `tests\fixtures\jamovi\kruskal_tied.csv` | One-Way ANOVA or Nonparametric test with Kruskal-Wallis option | `H = 9.640`, `df = 2`, `p = 0.008067` |
| `tests\fixtures\jamovi\regression_correlation.csv` | Linear Regression, `y` dependent, `x` and `z` covariates | Intercept `b = 5.257`, `x b = 0.888`, `z b = -0.726`, `R^2 = 0.983`, model `F = 200.074`, model `p = 0.000000666` |
| `tests\fixtures\jamovi\regression_correlation.csv` | Correlation Matrix, `x` and `y` Pearson | `r = 0.959075`, `p = 0.0000117` |

## Manual Steps

1. Open jamovi.
2. Use `File` -> `Open` -> `This PC` -> `Browse`.
3. Select the fixture CSV path from the table above.
4. If jamovi asks about import options, keep the default comma-separated CSV
   import.
5. For grouping columns such as `group` or `arm`, confirm they are treated as
   nominal/text variables. For numeric columns such as `score`, `pre`, `post`,
   `x`, `z`, and `y`, confirm they are continuous.
6. Run the analysis named in the table.
7. Compare the displayed statistic and p-value to the expected values.
8. Save a screenshot or exported output in the evidence folder.
9. If a p-value differs only because jamovi uses an exact test where Modori uses
   an asymptotic continuity-corrected policy, record it as a policy difference,
   not as a calculation defect.

## Suggested Evidence Filenames

```text
01-independent-t.png
02-mann-whitney-tied.png
03-paired-wilcoxon.png
04-anova-balanced.png
05-kruskal-tied.png
06-regression.png
07-correlation.png
```

## Interpretation Rule

- Matching to displayed precision strengthens external GUI confidence.
- A mismatch in exact/asymptotic nonparametric p-values is expected unless the
  jamovi option label matches Modori's documented policy.
- Any mismatch in ANOVA F, Kruskal-Wallis H, Pearson r, regression coefficients,
  or model R-squared should be treated as a real investigation item.
