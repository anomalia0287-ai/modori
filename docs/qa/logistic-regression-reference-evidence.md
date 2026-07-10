# Binary Logistic Regression Reference Evidence

Date: 2026-07-10 KST

Status: post-review calculation and product-path closure candidate for the
explicitly bounded V1 scope. Both actionable external-review findings were
reproduced before correction. Native packaged visual inspection remains a
separate non-calculation gate; no broader prediction or causal claim follows.

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
- Outcome values must remain distinguishable to a user, not only to typed tokens.
  Engine and selector reject blank or colliding labels after NFKC, control,
  whitespace, and case normalization. Integral float labels use the same display
  convention as other categorical levels.
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
- If a finite coefficient or log-odds CI cannot be exponentiated, coefficient,
  SE, z, p, likelihood, and fitted probabilities remain available. The OR and
  OR-CI become explicit undefined values, the term is named in a warning, and
  only that term is omitted from the OR forest. Scale-grid tests cover both
  coefficient directions at `1e-9`, `1e-6`, `1`, and `1e6`.

## Product-Path Evidence

- Event and categorical-reference choices are populated from the current
  `Dataset` through canonical typed tokens. Tokens preserve `bool`, `int`,
  finite `float`, and `str` identity and reject stale, forged, noncanonical, and
  nonfinite values.
- The event selector and engine share the same user-visible collision boundary;
  mixed typed levels such as string `"1"` and integer `1` cannot produce two
  indistinguishable choices or two identical report labels.
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

1. Post-review focused logistic/R/product gate:

   ```text
   Exact 16-file command recorded in
   `docs/qa/logistic-regression-external-review-brief.md`.
   197 passed in 13.94s
   ```

   R tests executed; there were no logistic-specific skips.

2. Final complete quality, package, and slow-statistics gate:

   ```text
   python scripts/quality_gate.py --with-package-check --with-packaged-launch --with-slow-stats
   compileall: pass
   ruff: pass
   bandit: pass
   launch-smoke-ok
   1242 passed, 4 skipped in 79.63s
   pip check: no broken requirements
   package-tool-ok
   package-launch-smoke-ok
   package-engine-smoke-ok
   package-public-data-smoke-ok
   3 passed, 1243 deselected in 23.87s
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

   The rebuild was deliberately launched from a parent environment whose PATH
   began with the workspace R runtime. The package environment removed that
   reference runtime before PyInstaller analysis; `Analysis-00.toc` contained
   zero R-runtime entries. This prevents R's ICU/UCRT/OpenSSL DLLs from being
   collected beside PySide6.

   Packaged executable:
   `dist/Modori/Modori.exe`, 30,899,420 bytes, SHA-256
   `23315F94BB82EAC76E7F575E1B7DB2D3B4C9602A275C48DCAB4A46D48B59BFCA`.

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
| Ambiguous outcome display | Exact, case-only, whitespace, full-width Unicode, and blank-label fixtures fail closed in both engine and UI. Typed identity cannot override an indistinguishable display. |
| Free-text event/reference entry | No matching QML `TextField`; event and references are model-backed `ComboBox` controls and canonical tokens are revalidated at commit and rerun. |
| Hosmer-Lemeshow | No implementation or claim. It is intentionally absent rather than presenting an unstable grouped calibration p-value as model validation. |
| Unsupported public claims | Report, catalog, knowledge, ledger, and matrix searches found only explicit prohibitions or limitation wording for causal, screening, diagnostic, and validated-prediction claims. |
| PyInstaller warnings | Build warned about an absent optional Qt asset-downloader plugin and SciPy `_cdflib` hidden import. Packaged launch smoke, all 21 engine checks including logistic `chi2.sf`, and public-data smoke all executed successfully, so neither warning affected an exercised V1 path. |
| Package DLL provenance | A verification build exposed that the global R-reference PATH could make PyInstaller collect R ICU/UCRT/OpenSSL DLLs and break packaged QtCore loading. R paths are now scoped to pytest/slow reference commands and defensively stripped by package build/run environments. A contaminated-parent rebuild collected zero R DLLs and passed both executable command smokes. |
| Stale smoke evidence | Engine and public-data smoke scripts delete only their owned previous `result.json` before launch and reject a zero-exit process that does not produce a fresh result. |

## External Review Disposition

The external reviewer reproduced the broad numerical evidence and reported two
actionable findings. F1 showed that string `"1"` and integer `1` could be
computationally distinct but visually identical; it was a V1 blocker and now
fails closed across engine and UI. F2 showed that a harmless predictor unit
change could make a one-unit OR unrepresentable and discard otherwise valid
inference; the product now preserves finite log-odds inference and discloses the
unavailable OR instead of narrowing the invariance claim incorrectly.

The review's remaining approximate-separation risk is retained honestly: the LP,
score, convergence, weight, and Fisher-condition gates provide executable
defense, but they are not an analytic proof that every finite-MLE boundary case
has a prescribed number of accurate digits. Native packaged visual walkthrough
also remains open. Neither residual item permits a wider prediction, diagnosis,
screening, causal, separated-data, or SPSS-equivalence claim.
