# TongTong — Vertical Slice Spec #02
## Multiple linear regression (OLS) — coefficients, diagnostics, APA report, re-run

> **Purpose.** Clone the validated slice #01 pattern for multiple linear regression,
> the workhorse of survey research. This slice proves the pattern generalizes to a
> richer result object (multi-predictor coefficient table) and to **diagnostic-driven
> warnings** (vs. slice #01's test rerouting).
>
> **Reuse, do not re-specify.** This slice inherits everything from
> `specs/01-reference-slice-likert-to-report.md` and `docs/POLICY.md`:
> the non-negotiable principles P1–P5 (replayable pipeline, numerical
> trustworthiness, A/B = one engine, deterministic intelligence, educational layer),
> the `Variable`/`Dataset`/`Step`/`Pipeline` model, the `StepResult`/`PipelineContext`
> contract, the settings-snapshot reproducibility rule (§5.5), and the
> `AnalysisResult` contract (every result carries `chart_spec` + `apa_template_id`).
> Only the **new** pieces are specified below.
>
> Language: English (engineering record, POLICY §1). Product-facing output
> (UI strings, generated APA prose) is Korean-first.

---

## PART 0 — Inherited principles (pointer only)
All of slice #01 PART 0 applies unchanged. One reminder elevated by the round-1
review of slice #01:

> **Validation honesty (POLICY §2/§3).** Golden numbers must be checked against a
> GENUINELY REPRODUCIBLE reference. Never attribute a number to an external tool
> that is not actually executed and committed. See PART 7.

---

## PART 1 — New Step: MultipleRegressionStep

**Step type:** `stats.regression_ols`

```
params = {
    "dv": "job_sat",                       # outcome, SCALE
    "predictors": ["autonomy", "workload", "support"],  # numeric predictors
    "regression_policy": {"preset": "modern"},          # see PART 3; snapshotted
}
```

Scope of predictors for this slice: **numeric SCALE predictors**, plus the intercept
(always included). Numeric ordinal or nominal codes are not accepted as predictors
in this slice unless a prior Step has explicitly produced a SCALE/indicator column.
Categorical predictors are handled by a future `DummyCodeStep` that produces numeric
indicator columns (PART 8) — out of scope here.

`compute`:
- Build the design matrix from `predictors` + constant; drop rows with any NaN in
  `dv`/`predictors` (listwise), via `frame_for_compute`.
- Use statsmodels' matrix/DataFrame API, not formula/Patsy strings. Variable names
  are untrusted and may contain `+`, `:`, spaces, or other formula syntax.
- Fit OLS with `statsmodels`. Standard errors per the regression policy (PART 3:
  classical OLS SE, or HC3 robust when heteroscedasticity is auto-detected).
- Produce a `RegressionResult` (PART 2): model fit, per-predictor coefficient table
  (unstandardized b, SE, standardized β, t, p, 95% CI, VIF), diagnostics, the
  canonical chart spec, and `apa_template_id`.
- `notes`: model fit one-liner + any diagnostic warnings (educational layer, P5).

`reads()` = `{dv} ∪ set(predictors)`.
`writes()` = `{f"analysis:{self.id}"}`.

The display label may be `regression:{dv}:<predictor labels>`, but it is never the
analysis addressing handle and never participates in dirty-propagation identity.

> Standardized β: compute by fitting on z-scored variables, OR
> `beta_i = b_i * (sd(x_i) / sd(y))`. Document which; cross-check the two agree.
> The β 95% CI used by the forest plot is the b CI scaled the same way:
> `beta_ci_i = (ci_lo_i, ci_hi_i) * (sd(x_i) / sd(y))`.

---

## PART 1.5 — Input validation, missing data, determinism (parallels slice #01 hardening)

> Slice #01's reliability step was praised for rejecting degenerate input with clear
> errors. Regression needs the analogous guardrails — it must never emit NaN/inf.

### Input validation (raise clear `ValueError`, not NaN/inf)
- `dv` measure must be SCALE; every predictor must be SCALE and numeric. Reject
  otherwise with a message naming the offending variable.
- At least 1 predictor; predictors must be unique.
- No constant (zero-variance) predictor or dv.
- `n_obs` must be ≥ `len(predictors) + 2` (enough residual df).
- Multicollinearity has two distinct responses (do not conflate):
  - **ERROR only on exact rank deficiency** — `XᵀX` singular / design matrix not
    full rank (a unique OLS solution does not exist). Raise a clear error naming the
    collinear set ("predictors are perfectly collinear: …"). Do NOT return unstable
    coefficients.
  - **WARN (never error) on severe-but-invertible collinearity** — the VIF path in
    §3.1 (VIF > 10). A full-rank model with high VIF still fits; the researcher may
    legitimately want it with the warning. Rejecting it would be over-eager.
- Degenerate but full-rank fits must still produce finite statistics. Reject with a
  clear `ValueError` when the model has zero residual variance/perfect fit, non-finite
  classical or robust standard errors, non-finite t/p/CI/F statistics, or a non-finite
  standardized beta/CI. Do not emit NaN/inf into `RegressionResult`, prose, tables, or
  charts.
- For HC3, reject models where leverage/hat values make robust covariance undefined
  or non-finite. A warning is not enough because downstream APA and diagnostics would
  otherwise contain invalid numbers.

### Missing data (listwise, but reported — survey reality)
- v1 behavior is listwise deletion across `dv` + `predictors`. Imputation is out of
  scope (see PART 8).
- Report `n_obs`, `n_total`, and `n_dropped` in the result and `notes`.
- Educational warning (P5) when the dropped fraction exceeds a threshold
  (default 0.10, configurable in `regression_policy`): e.g. "전체의 {pct}% 사례가
  결측으로 제외되었습니다 — 결과 편향 가능성을 검토하세요."

### Determinism
- Coefficient table order is fixed: `(Intercept)` first, then predictors in the
  user-specified order. Results must be identical under row reordering of the input.

---

## PART 1.6 — Analysis identity & downstream addressing (ANCHOR-CRITICAL; amends the shared contract)

> This fixes a real contradiction: §7.2 requires that editing predictors re-runs the
> report, but a content-derived analysis key would change when predictors change,
> silently breaking the ReportStep reference. The most common regression edit (adding
> or dropping a predictor) is exactly the re-run scenario — so identity must be stable.

- **Downstream steps address upstream analyses by the producing Step's `id`, not by a
  content-derived key.** ReportStep `include` references step ids (e.g. `"reg_main"`),
  and the pipeline maps step id → its `AnalysisResult`. Editing `predictors` on that
  step changes its output but NOT its id, so the report reference survives and
  re-runs correctly.
- The canonical analysis write key is `analysis:<step_id>`. ReportStep may store step
  ids in `include` and resolve them to `analysis:<step_id>` during compute. The
  human-readable key (`regression:{dv}:…`) may remain as a *display label* only,
  never as the addressing handle.
- **Variable names are untrusted** (a `.sav` column may contain `:`, `+`, spaces).
  Never build an addressing handle by string-joining variable names. Step id is a
  UUID and is safe.
- This is a small amendment to the slice #01 analysis-addressing contract; apply it
  consistently (slice #01's ReportStep should also accept step-id references). Keep
  backward behavior working: ReportStep may accept either a step id or, for #01's
  existing tests, the legacy key — but step id is the canonical, anchor-safe path.

---

## PART 2 — RegressionResult data structure

```python
@dataclass
class CoefficientRow:
    name: str            # predictor name ("(Intercept)" for the constant)
    b: float             # unstandardized coefficient
    se: float
    beta: float | None   # standardized; None for intercept
    beta_ci: tuple[float, float] | None   # 95% CI for beta (forest plot); None for intercept
    t: float
    p_value: float
    ci: tuple[float, float]   # 95% CI for b
    vif: float | None         # None for intercept; also None when <2 predictors

@dataclass
class RegressionResult:
    dv: str
    predictors: list[str]
    n_obs: int                 # cases actually used (after listwise deletion)
    n_total: int               # rows before deletion
    n_dropped: int             # cases dropped for missingness
    se_type: str               # "classical" | "HC3"
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    df_model: int
    df_resid: int
    f_p_value: float
    coefficients: list[CoefficientRow]
    diagnostics: dict          # see PART 3 (bp_p, dw, shapiro_resid_p, max_cooks, max_vif, ...)
    warnings: list[str]        # human-readable diagnostic warnings
    apa_template_id: str       # "regression.v1"
    chart_spec: "ChartSpec"
```

Follows the `AnalysisResult` contract from slice #01 (carries `chart_spec` +
`apa_template_id`).

---

## PART 3 — Diagnostics & policy (the new deterministic-intelligence surface)

Unlike slice #01 (which *reroutes* to a nonparametric test), regression diagnostics
mostly **warn and advise**; one diagnostic drives an automatic SE change.

### 3.1 Diagnostics (computed every time; exact rules)
```
- Multicollinearity:  VIF per predictor. FOOTGUN: statsmodels
    variance_inflation_factor regresses each column on the OTHERS, so the design
    matrix MUST INCLUDE the constant column or every VIF is wrong/inflated. Compute
    VIF on [const, predictors], then report VIF for predictors only (drop the
    constant's VIF). Only when len(predictors) >= 2 (else vif = None).
    warn if any VIF > 5 ("moderate"); strong warning if > 10 ("severe").
- Heteroscedasticity: Breusch–Pagan (statsmodels het_breuschpagan, which returns
    (lm, lm_pvalue, fvalue, f_pvalue)). Use the LM p-value: bp_p = lm_pvalue.
    bp_p < .05 → flag.
- Residual normality: Shapiro–Wilk on residuals. shapiro_resid_p < .05 AND
    n_obs < 30 → warn (CLT note for large n, mirroring slice #01 rationale).
    Edge: scipy Shapiro is unreliable / capped for very large n — if n_obs is beyond
    its supported range, skip with a note rather than error.
- Independence:       Durbin–Watson — REPORTED, but DW assumes a MEANINGFUL ROW
    ORDER (time/sequence). Cross-sectional survey data is unordered, so a DW warning
    would be spurious and confusing for our target users. Therefore: compute and
    store dw, but only EMIT the dw<1.5/>2.5 warning when the data has a declared
    order via `regression_policy["order_var"]` or
    `regression_policy["ordered_data"] == true`. If `order_var` is provided it must
    name an existing variable and rows are evaluated in that order for DW. Default:
    no DW warning, with an educational note that independence matters for ordered
    data.
- Influential points: Cook's distance. flag (count) points with cook > 4 / n_obs;
    report the max and the count — never auto-remove cases.
```
Each triggered diagnostic appends a plain-language entry to `warnings` and, where
relevant, auto-surfaces the matching diagnostic plot (PART 5, educational tie-in).

### 3.2 RegressionPolicy (snapshotted into params per slice #01 §5.5)
| Preset | Standard errors |
|--------|-----------------|
| `"modern"` (default) | classical OLS SE; **auto-switch to HC3 robust SE when Breusch–Pagan p < .05** (deterministic, analogous to slice #01's t→Welch reroute) |
| `"classic"` | always classical OLS SE (report the heteroscedasticity warning, no auto-switch) |
| `"custom"` | user sets: SE type (classical/HC3), Breusch–Pagan threshold, VIF warn cutoff, missing-data warning threshold, and optional DW order fields (`order_var` or `ordered_data`) |

A mode exposes `modern` (beginner protection); policy changes live in B / settings.
Record `se_type` actually used in the result and APA prose.

**HC3 and the model F-test.** When `se_type == "HC3"`, the per-coefficient t/p/CI use
the robust covariance, and the **model significance test must be the robust Wald F**
(statsmodels `f_test` against the HC3 covariance) — not the classical F. R² and
adj. R² are unchanged (not SE-dependent). Record which F was used; the APA model
sentence already discloses the HC3 switch.

---

## PART 4 — APA prose templates (`regression.v1`) — KO primary / EN secondary

Number formatting per APA, as in slice #01 PART 4 (p to 3 decimals; statistics to 2;
β and R² with leading zero omitted).

> **Fix the leading-zero helper first (hardens #01 too).** Slice #01's `_apa_number`
> strips the leading zero with an unanchored `replace("0.", ".")`, which corrupts any
> value with magnitude ≥ 1 (e.g. "10.50" → "1.50"). Standardized β can exceed ±1
> (suppression/multicollinearity), so the strip MUST be anchored to the leading zero
> only — e.g. regex `^(-?)0\.` → `\1.`. #01 never hit this (p/r/α are all < 1), but the
> helper is now shared with β, so fix it and add a regression test for |value| ≥ 1.

**Model sentence (significant model):**
- KO: `"{se_label_ko}를 사용한 회귀모형은 통계적으로 유의하였다, F({df_model}, {df_resid}) = {F}, {p}, R² = {R2}, adjusted R² = {adjR2}."`
- EN: `"Using {se_label_en}, the regression model was statistically significant, F({df_model}, {df_resid}) = {F}, {p}, with R² = {R2}, adjusted R² = {adjR2}."`
- Non-significant model: replace "통계적으로 유의하였다 / was statistically significant" with the negative form; still report R² and adjusted R².
- If `se_type == "HC3"`, `se_label_ko = "이분산-강건(HC3) 표준오차"` and `se_label_en = "HC3 robust standard errors"`. Classical fits use the corresponding classical-SE label.

**Per-predictor sentences** — iterate **predictors only; the intercept is NEVER given
a predictor sentence** (it stays in the table). Order deterministically in the
user-specified predictor order.
- KO (significant): `"{predictor}는 유의하게 예측하였다(b = {b}, SE = {se}, t({df_resid}) = {t}, {p}, β = {beta})."`
- KO (non-significant): `"{predictor}는 유의하지 않았다(b = {b}, SE = {se}, t({df_resid}) = {t}, {p}, β = {beta})."`
- EN (significant): `"{predictor} significantly predicted {dv} (b = {b}, SE = {se}, t({df_resid}) = {t}, {p}, beta = {beta})."`
- EN (non-significant): `"{predictor} was not significant (b = {b}, SE = {se}, t({df_resid}) = {t}, {p}, beta = {beta})."`
- Edge case to handle gracefully: a significant overall model with no individual
  significant predictor (common under multicollinearity) — the prose must still read
  sensibly, and the educational layer (§4.1) should name this pattern.

Warnings (VIF/heteroscedasticity/etc.) are surfaced in the educational layer, not
forced into the APA paragraph (keep the manuscript prose clean; warnings advise the
researcher separately).

### 4.1 Educational interpretation (P5 (b)) — the core differentiator
Beyond the APA prose, every regression result carries plain-language interpretation
for the statistics-anxious user (this is TongTong's reason to exist, not optional):
- R²: e.g. "이 모형은 {dv} 점수 변동의 약 {R2_pct}%를 설명합니다."
- Each significant predictor, with direction: e.g. "{predictor}이(가) 1 표준편차
  높을수록 {dv}은(는) 약 {beta} 표준편차 {증가/감소}하는 경향이 있습니다."
- A one-line meaning for each triggered diagnostic warning (what it is, what to do).
These appear in the educational panel, not the manuscript paragraph.

---

## PART 5 — Automatic visualization

- **Canonical chart (default, one only):** coefficient **forest plot** of standardized
  β with 95% CI (intercept excluded), zero line marked. `chart_spec.type =
  "coefficient_forest"`.
- **Diagnostic plots (secondary, "show more"; auto-surfaced when a diagnostic is
  flagged — educational tie-in, slice #01 §5.4):**
  - residual-vs-fitted (linearity/heteroscedasticity),
  - Q–Q plot of residuals (normality),
  - Cook's distance plot (influence).
- All publication defaults from slice #01 §5.3 (grayscale-safe, labeled, PNG 300dpi
  + SVG + EPS). No chart spam.

---

## PART 6 — A/B mode entry

- **A (Guided):** "어떤 점수를 *설명/예측*하고 싶으세요?" → `dv` (SCALE only). "그것을
  설명한다고 보는 변수들을 고르세요." → `predictors` (numeric). Diagnostics, SE policy,
  warnings are automatic; not asked.
- **B (Standard):** `Analyze ▸ Regression ▸ Linear` dialog (outcome + predictors,
  optional policy). Same engine, same automatic diagnostics (P3).

---

## PART 7 — Validation & Definition of Done (validation honesty enforced)

### 7.1 Numerical correctness — independent + reproducible (no fabrication)
- **Unconditional in-repo triangulation (must run in normal CI):** cross-check
  against an INDEPENDENT `numpy` computation — not just the coefficients. At minimum
  triangulate: **b** (`numpy.linalg.lstsq` / normal equations), **classical SE**
  (σ̂²·diag((XᵀX)⁻¹), σ̂² = SSres/df_resid), and **R²** (1 − SSres/SStot). Assert
  agreement to a stated tolerance. Point estimates alone are not enough — SEs drive
  every p-value. This guarantees correctness even where R is unavailable (the lesson
  from slice #01 FIX 2).
- **External reference (reproducible):** validate coefficients, classical SE, R², F,
  and VIF against EITHER
    (A) a documented dataset with published/citable regression results, e.g.
        R car::Duncan `lm(prestige ~ income + education)` or `mtcars`
        `lm(mpg ~ wt + hp + cyl)` — cite the source and the exact model, OR
    (B) R `lm()` + `car::vif()` via a committed, runnable script
        (tests/r/regression_reference.R) with its captured stdout
        (tests/r/regression_reference.stdout.txt), gated on R availability —
        exactly the pattern established in slice #01 (tests/r/omega_reference.*).
  The external reference VALUE MUST DIFFER from our own engine's output only within
  the documented tolerance, and must be genuinely reproducible. **Never paste our
  own output and label it as an external tool's result** (POLICY §3; this was a
  caught defect in slice #01 round 1).
- **HC3 robust SE is its own numeric path → its own golden check (do NOT skip).** The
  HC3 standard errors must be validated against an external reference —
  R `sandwich::vcovHC(model, type = "HC3")` + `lmtest::coeftest` (committed script +
  stdout, like (B) above) or a published value. An unvalidated robust-SE path is
  exactly the kind of hard-to-verify statistic that produced the slice #01 ω defect.

### 7.2 Anchor (re-run) test
- Add/remove a predictor (edit step params) or add cases (Import) → one user action
  → coefficient table, diagnostics, APA prose, forest plot, and .docx all refresh
  consistently (no staleness). Reuse slice #01's ReportStep.

### 7.3 Pipeline integrity
- `reads()/writes()` correctness; dirty propagation touches exactly the dependent
  steps; serialization round-trip identical.

### 7.4 Definition of Done
- 7.1–7.3 pass; the scenario runs end-to-end (to .docx) in both A and B modes;
  all slice #01 tests remain green; no changes outside this slice's scope except the
  explicitly required shared-contract hardening in PART 1.6 (step-id analysis
  addressing) and PART 4 (`_apa_number` leading-zero fix).

---

## PART 8 — Explicitly out of scope (scope discipline)
- Categorical-predictor dummy coding (future `DummyCodeStep`), interaction terms,
  polynomial terms.
- Hierarchical / stepwise / model-comparison regression (a later slice).
- Logistic / other GLMs (different slice — different result + link).
- C-mode (multilevel, SEM), network visualization (v1.5).
- Design / theming / packaging.

---

## PART 9 — Codex build order & handoff
0. **Step-id addressing (PART 1.6) FIRST** — make ReportStep reference upstream
   analyses by producing-step id; keep slice #01 tests green. Without this the re-run
   anchor is broken for predictor edits, so it precedes regression work.
1. `RegressionResult` + `CoefficientRow` (results module) following the AnalysisResult contract.
2. Input validation + missing reporting (PART 1.5); `MultipleRegressionStep.compute`
   (statsmodels OLS) + reads/writes (content key is a display label only); headless unit tests.
3. Diagnostics (VIF *with constant in design matrix*, Breusch–Pagan LM p, Durbin–Watson
   gated, residual Shapiro, Cook's) + warnings.
4. `RegressionPolicy` (modern/classic/custom) with HC3 auto-switch (+ robust Wald F) + snapshot rule.
5. Validation: unconditional numpy triangulation of b/SE/R² FIRST; then external
   references for classical fit AND for HC3 SE (both reproducible, no fabrication).
6. Fix `_apa_number` leading-zero helper (anchored); APA template `regression.v1`
   (KO/EN, intercept excluded from prose) in reporting.py; extend `prose_for`/`table_for`.
7. `ChartSpec` types: `coefficient_forest` (β ± beta_ci) + diagnostic plots in the renderer.
8. Re-run acceptance test (7.2) — must include a **predictor-edit** case (proves the
   step-id addressing from item 0), via existing ReportStep.
9. A/B mode exposure.

**Reviewer (planning) gate:** review first when items 2 and 5 are done — if the OLS
fit is correct (numpy-triangulated, incl. SE and R²) and BOTH external references
(classical + HC3) are genuine and reproducible, the rest is pattern cloning. The
reviewer will independently re-run every external reference (as in slice #01) and
will specifically test the predictor-edit re-run.

---

### Appendix A — Library mapping (Codex starting point)
| Function | Library |
|----------|---------|
| OLS fit, robust SE (HC3), F, R² | `statsmodels` |
| VIF | `statsmodels.stats.outliers_influence.variance_inflation_factor` (design matrix MUST include the constant) |
| Breusch–Pagan, Durbin–Watson | `statsmodels.stats` (use BP LM p-value) |
| independent check of b / SE / R² | `numpy.linalg.lstsq` + normal equations (triangulation) |
| residual normality | `scipy.stats.shapiro` |
| external reference (classical) | R `lm` + `car::vif` via committed script (reproducible) |
| external reference (HC3 SE) | R `sandwich::vcovHC(type="HC3")` + `lmtest::coeftest` via committed script |
| viz, docx | `matplotlib`, `python-docx` (as slice #01) |
