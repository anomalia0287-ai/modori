# Directive — Slice #03 FIX 2: real coverage of user-facing terms (+ un-xfail)

Context: the seed is COMPLETE — 29 entries in `library/entries/`, link-integrity passes
(`test_seed_is_link_complete` currently XPASSES), all entries `needs_review`. Finish
FIX 2: make the coverage guarantee target USER-FACING terms and make the guard real.
Keep all tests green; keep honest gating; no fabrication; **do NOT author library
content** (planner's role — see the STOP rule).

## 1. Redefine the coverage vocabulary = user-facing identifiers
Coverage purpose (spec §3.1): every term the USER sees/clicks must be explainable.
Derive the coverage set from what the UI shows, NOT from engine internals:
- Source it from `table_for(result)` column keys + the surfaced result-object fields the
  UI renders + `test_name` + `effect_name`, across ReliabilityResult / ComparisonResult
  / RegressionResult.
- Normalize keys (lowercase, snake_case; e.g. "95% CI" → confidence_interval, "VIF"/"vif"
  → vif) and collapse duplicate aliases to ONE concept:
  - bp_p / breusch_pagan_p → breusch-pagan
  - dw / durbin_watson → durbin-watson
  - shapiro_p / shapiro_resid_p / shapiro_g1_p / shapiro_g2_p → shapiro-wilk
- EXCLUDE internal-only identifiers from the must-cover set: apa_template_ids
  (reliability.v1, ttest.v1, mwu.v1, regression.v1, report.apa.v1), step_types (stats.*),
  internal selectors (model_test, classical_f / robust_wald_f, raw se_type values).
  Reconcile the per-step vocabulary constants / ENGINE_VOCABULARY accordingly (the prior
  set mixed these in).

## 2. HELP_KEYS — extend with these user-facing mappings (normalized term → slug)
Keep the existing alpha/cronbach/welch variants. Map the engine's actual emitted column
keys / values to these normalized terms (you own `table_for`, so wire the exact strings):

    student_t            -> student-t-test
    welch_t              -> welch-t-test
    mann_whitney         -> mann-whitney-u
    cohen_d              -> cohens-d
    rank_biserial        -> rank-biserial
    cronbach_alpha       -> cronbach-alpha
    mcdonald_omega       -> mcdonald-omega
    corrected_item_total_correlation -> corrected-item-total-correlation
    p_value              -> p-value
    confidence_interval  -> confidence-interval
    standardized_beta    -> standardized-beta   (regression "beta" column)
    r_squared            -> r-squared
    adjusted_r_squared   -> adjusted-r-squared
    f_statistic          -> f-test
    vif                  -> vif
    breusch_pagan        -> breusch-pagan
    durbin_watson        -> durbin-watson
    shapiro_wilk         -> shapiro-wilk
    cooks_distance       -> cooks-distance
    levene               -> levene-test
    normality            -> normality
    homoscedasticity     -> homoscedasticity
    homogeneity_of_variance -> homogeneity-of-variance
    independence_of_errors  -> independence-of-errors
    multicollinearity    -> multicollinearity
    linearity            -> linearity
    listwise_deletion    -> listwise-deletion
    statistical_significance -> statistical-significance

## 3. Replace the tautological guard with a real one
- The current `test_engine_vocabulary_is_engine_declared_and_reconciled` asserts
  `ENGINE_VOCABULARY == its own defining union` (a tautology). Replace it.
- New guard: build each result type from a fixture (reuse existing ones), collect the
  ACTUAL user-facing identifiers it emits (table_for columns + surfaced fields +
  test_name/effect_name), normalize them, and assert each resolves via HELP_KEYS to an
  existing library entry. This catches real drift (a newly emitted term with no entry
  fails the test). Keep concise reconciliation presence/absence checks if useful.

## 4. Un-xfail
- `test_seed_is_link_complete` → remove the xfail mark; it passes now and must be required.
- `test_engine_vocabulary_fully_covered` → make it required ONCE coverage passes (after
  the planner adds any entries surfaced by the STOP rule below).

## 5. STOP-and-report rule (do NOT invent content, do NOT drop terms)
If the real guard surfaces user-facing terms with NO library entry: do NOT create
library entries (content is the planner's role) and do NOT drop them from the coverage
set to force a pass. List the uncovered terms and stop. **Expected gaps to report:**
regression table columns `b` (unstandardized coefficient), `SE` (standard error),
`t` (t-statistic), and `df` (degrees of freedom) — these have no entry yet. The planner
will author those few entries, then coverage flips to required and must pass.

## Done when
- Coverage vocabulary is user-facing + derived from actual outputs; internal-only ids
  excluded; HELP_KEYS extended; tautological guard replaced by a real drift guard;
  `test_seed_is_link_complete` un-xfailed and passing; any uncovered user-facing terms
  reported (not invented, not dropped); all other tests green.

────────────────────────────────────────────────────────
# PLANNER RESOLUTION (2026-06-28) — gaps filled; RESUME FIX 2

Codex correctly hit the STOP rule and reported the uncovered user-facing terms. The
planner has now authored the missing **statistical-concept** entries. Seed is now 34
entries; link-integrity still passes. Codex may resume.

## New entries authored (now exist in library/entries/)
- `unstandardized-coefficient` (b), `standard-error` (SE), `test-statistic` (t and the
  comparison "statistic" column, generic t/U/F), `degrees-of-freedom` (df),
  `alpha-if-deleted` (alpha_if_deleted).

## HELP_KEYS — add these (in addition to §2 above)
    b                 -> unstandardized-coefficient
    se                -> standard-error
    t                 -> test-statistic
    statistic         -> test-statistic
    df                -> degrees-of-freedom
    alpha_if_deleted  -> alpha-if-deleted

## EXCLUDE from the must-cover set (structural / identifier / data columns — NOT concepts)
These table columns are variable names, group/data labels, or meta-labels, not
statistical concepts to explain, so they are NOT required to have library entries.
Add them to the guard's explicit exclude list:
    predictor, dv, group, group_1, group_2, item, test, effect, effect_value
Rationale: the actual test/effect NAMES are already covered via `test_name`/`effect_name`
→ their method/effect entries; these columns merely hold which-variable / which-name /
the raw value.

## Resume steps for Codex
1. Wire HELP_KEYS (§2 map + the 6 additions above).
2. Apply the exclude list when deriving the must-cover set from table_for()/results.
3. Replace the tautological guard with the real drift guard (§3).
4. Un-xfail `test_seed_is_link_complete` (passing) and `test_engine_vocabulary_fully_covered`;
   both must now pass against the 34-entry seed.
5. Keep all other tests green. If any further user-facing term is still uncovered,
   STOP and report it (do not invent entries).
