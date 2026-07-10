# Binary Logistic Regression Reference Evidence

Date: 2026-07-10 KST

Status: calculation and product-path closure candidate for the explicitly bounded
V1 scope. Independent review remains before integration or any broader public
claim.

## Claim Boundary

The supported estimator is unweighted, independent-row, main-effects binary
logistic maximum likelihood with explicit event coding and explicit references
for categorical predictors. The evidence below supports numerical and product
path correctness inside that boundary.

Same-sample classification, ROC AUC, Brier score, and grouped calibration are
descriptive outputs. They are not adequacy evidence, external validation, or a
validated-prediction claim. Causal, diagnostic, screening, treatment-selection,
Firth/penalized, weighted, clustered, survey, repeated-observation, interaction,
and separated-data estimation remain outside V1 scope.

## Pinned Environment

| Component | Version or path |
| --- | --- |
| Python | 3.12.10 |
| NumPy | 2.5.0 |
| SciPy | 1.18.0 |
| statsmodels | 0.14.6 |
| mpmath | 1.4.1 |
| R | R 4.5.3 (2026-03-11 ucrt) |
| R executable | `C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe` |

The anchored fixture hashes and measured differences are pinned in
`tests/fixtures/logistic_regression/reference-metadata.json`.

## Independent Numerical Evidence

| Evidence | Scope | Ceiling | Achieved maximum difference |
| --- | --- | --- | --- |
| R base `glm` continuous fixture | Coefficients, final-probability Fisher SEs, fitted probabilities, log likelihood, null log likelihood, deviance, AIC, LR statistic and p-value | `1e-10` for anchored parity | Coefficient absolute `3.43e-13`; SE absolute `3.34e-14`; probability absolute `1.09e-13` |
| R base `glm` complete-case fixture | Listwise deletion plus the same fit surfaces | `1e-10`; R summary-SE diagnostic ceiling `1e-6` | Coefficient absolute `1.39e-16`; final-Fisher SE absolute `1.11e-16` |
| R base `glm` declared-reference categorical fixture | Explicit level order, reference, coefficient and likelihood surfaces | `1e-10` | Coefficient absolute `4.48e-13`; SE absolute `4.95e-14`; probability absolute `1.13e-13` |
| Independent 80-digit mpmath Newton/Fisher oracle | Coefficients, SEs, probabilities, and log likelihood | `1e-11` | Coefficient absolute `3.42e-13`; SE absolute `3.34e-14`; probability absolute `1.09e-13` |

The product covariance is recomputed from final fitted probabilities through an
SVD path. R emits both `summary(glm)` SEs and an independent final-probability
Fisher reconstruction; anchored parity uses the latter. Direct original-scale R
`glm` is intentionally not used as the large-offset oracle because that fit did
not converge at the pinned strict control tolerance. Product large-offset
evidence instead uses preconditioned-path and shift-invariance fixtures.

## Numerical Safety Evidence

- Event coding is mandatory and checked against the two current complete-case
  outcome levels. The engine never infers the event by order, sorting, or truthy
  conversion.
- Categorical levels and references are declared and checked against observed
  data. Numeric categorical labels are normalized before design-matrix creation.
- A linear-programming existence gate rejects complete and quasi-complete
  separation before maximum-likelihood fitting. Ambiguous solver outcomes fail
  closed.
- Rank, class-count, score-residual, fitted-weight, and Fisher-information
  condition gates reject unsupported or numerically unsafe results.
- Covariance uses SVD-backed Fisher information. There is no direct normal-
  equation or matrix inverse in the logistic engine.
- statsmodels perfect-separation, convergence, and runtime warnings are promoted
  to errors; non-converged result objects are rejected independently.
- Likelihood-ratio tails use `stats.chi2.sf`; a source-policy test now includes
  the logistic engine and rejects CDF complements and direct `linalg.inv` use.
- Overflowing odds-ratio displays become explicit undefined values with warning
  codes; they are not silently emitted as finite numbers.

## Product-Path Evidence

- Event and categorical-reference choices are populated from the current
  `Dataset` through canonical typed tokens. Tokens preserve `bool`, `int`,
  finite `float`, and `str` identity and reject stale, forged, noncanonical, and
  nonfinite values.
- QML uses `ComboBox` selectors for event and every categorical reference. There
  is no free-text event or reference entry. Apply remains disabled until every
  required choice is explicit.
- A configuration-required recommendation opens the manual logistic form and
  does not mutate or run the pipeline before event confirmation.
- The real pipeline integration test computes the 60-row fixture, binds the
  `LogisticRegressionResult`, renders coefficient/ROC/calibration charts, and
  writes the Word report.
- Pipeline JSON round-trip, stale-token rejection, transaction rollback, rerun
  validation, report inclusion, and numeric-category missing-code upcast are
  covered by executable tests.
- The engine-smoke top-level `ok` flag now requires the analysis rerun command
  itself to succeed; a rejected rerun can no longer be masked by a later ready
  status or successful standalone statistic checks.

## Executed Gates

All commands ran from the isolated
`codex/recommendation-benchmark-pilot` worktree with `PYTHONPATH=src`, offscreen
Qt, and the explicit workspace-local R executable.

1. Focused logistic/R/product closure:

   ```text
   pytest ... logistic engine, references, reporting, recommendation,
   R cross-engine, V1/app/package smoke, and UI product-flow tests
   112 passed in 12.67s
   ```

   R tests executed; there were no logistic-specific skips.

2. Complete local quality gate:

   ```text
   python scripts/quality_gate.py --with-slow-stats
   compileall: pass
   ruff: pass
   bandit: pass
   launch-smoke-ok
   1201 passed, 4 skipped in 92.45s
   pip check: no broken requirements
   3 passed, 1202 deselected in 28.92s
   ```

   The four full-suite skips are optional environment cases outside the focused
   logistic gate; the explicit logistic/R closure command had zero skips.

3. Windows package rebuilt from this worktree with PyInstaller 6.21.0:

   ```text
   package-launch-smoke-ok
   package-engine-smoke-ok
   package-public-data-smoke-ok
   ```

   Packaged engine JSON reported `opened: true`, `rerun: true`, `waited: true`,
   `status: ready`, and 21 successful V1 statistical checks. The added check is
   `logistic_regression` with analysis type `LogisticRegressionResult`.

   Packaged executable:
   `dist/Modori/Modori.exe`, 30,897,933 bytes, SHA-256
   `B9DAFA2F51933A2569770BAAD8B3A4CF35AF8D9C72C9A9785EEF094E216A8876`.

   Native visual inspection is not counted as evidence in this pass. The Windows
   automation launch approval timed out and no Modori window was created. QML
   runtime tests and packaged launch smoke passed, but they do not replace a
   human-visible packaged walkthrough.

## Source Audit

| Search target | Result and disposition |
| --- | --- |
| Lower-tail/CDF-complement p-values | No product logistic CDF-complement match. LR p-value uses `stats.chi2.sf`; `tests/test_tail_probability_policy.py` locks it. |
| Direct matrix inverse | No `linalg.inv` match in `src/modori`. The logistic covariance and condition calculations use SVD-backed helpers. |
| Uncaught statsmodels warnings | Logistic fitting wraps perfect-separation, convergence, and runtime warnings as errors; dedicated monkeypatch tests exercise each failure path. |
| Implicit event mapping | No order-based event selection. `event_value` is required, type-normalized, matched to observed levels, and disclosed with the non-event in reports. |
| Free-text event/reference entry | No matching QML `TextField`; event and references are model-backed `ComboBox` controls and canonical tokens are revalidated at commit and rerun. |
| Hosmer-Lemeshow | No implementation or claim. It is intentionally absent rather than presenting an unstable grouped calibration p-value as model validation. |
| Unsupported public claims | Report, catalog, knowledge, ledger, and matrix searches found only explicit prohibitions or limitation wording for causal, screening, diagnostic, and validated-prediction claims. |
| PyInstaller warnings | Build warned about an absent optional Qt asset-downloader plugin and SciPy `_cdflib` hidden import. Packaged launch smoke, all 21 engine checks including logistic `chi2.sf`, and public-data smoke all executed successfully, so neither warning affected an exercised V1 path. |

## Remaining Decision

The calculation and product-path evidence is sufficient to present this module
for adversarial review inside its bounded V1 scope. Independent review remains:
separation detection, preconditioning/covariance restoration, event/reference
coding, pseudo-R2 formulas, calibration wording, reference tolerances, and
catalog/UI promotion gates must be attacked before integration. Any finding is
reproduced with a failing test before correction. No wider prediction or causal
claim follows from this closure candidate.
