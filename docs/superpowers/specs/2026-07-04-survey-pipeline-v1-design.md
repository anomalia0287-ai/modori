# Survey Pipeline V1 Design - 2026-07-04

## Decision Status

Approved direction: **FB revision accepted**.

V1 is not an AI product and not an SPSS menu clone. V1 is a deterministic,
replayable survey-analysis pipeline that takes a messy social-science survey
file to submission-ready, re-runnable results.

The product sentence for this slice is:

> Deterministic survey analysis pipeline: from messy survey files to
> re-runnable, submission-ready results.

This replaces the looser "SPSS-grade features plus easier workflow" framing.
SPSS parity may remain a long-term internal coverage checklist, but it is not
the V1 promise or market position.

## Background

The previous planning direction correctly centered survey-based quantitative
social-science research, but it overreached in two ways:

- It placed optional local AI too close to the product center, conflicting with
  the established project rule: **SLM deferred, deterministic only**.
- It treated mediation/moderation as a late workflow step without separating
  safe regression interactions from PROCESS-grade indirect-effect analysis.

This design restores the earlier non-negotiables from the existing specs:

- All guidance, routing, assumption checks, and report text are deterministic.
- Runtime AI/SLM is not part of V1.
- Any future SLM is an optional component behind the deterministic knowledge
  library, not a source of statistical truth.
- The replayable pipeline is the product's core technical asset.

## Product Positioning

Modori V1 competes by removing rework and statistical uncertainty in a common
survey-analysis workflow, not by exposing the largest analysis menu.

The differentiator is the integrated path:

```text
Import messy survey file
Normalize metadata and missingness
Prepare variables and scales
Run guarded analyses
Generate Korean-first APA-style outputs
Re-run the full pipeline after data or parameter changes
```

The app must remain useful with all guidance features enabled or disabled. Guided
mode and standard mode create the same engine Steps; they only differ in how
parameters are filled.

## V1 Scope

V1 is a vertical slice for scale-based survey research. It must be deep enough
that a user can complete a common survey paper/report segment without exporting
to SPSS for routine cleanup, assumption routing, or APA reporting.

In scope:

- Import `.csv`, `.xlsx`, and `.sav`.
- Preserve and normalize variable labels, value labels, measure types, and user
  missing codes where available.
- Let users correct inferred metadata in the variable view.
- Record every preparation and analysis operation as replayable pipeline Steps.
- Reverse-code Likert items without destroying source columns.
- Detect likely missed reverse-coded items through negative item-total
  relationships and show a warning before scale/report use.
- Compose scale scores with explicit missing policies and visible case counts.
- Compute technical/descriptive summaries suitable for Table 1.
- Compute reliability statistics with item diagnostics.
- Run factor/PCA checks with KMO, Bartlett, and parallel-analysis based factor
  count guidance.
- Run frequency, crosstab, chi-square, and exact-test routing.
- Run correlation analyses, including Spearman routing where appropriate.
- Run Welch-first two-group comparisons and two-time paired comparisons.
- Run ANOVA/ANCOVA with assumption checks and post-hoc routing.
- Provide nonparametric alternatives for common assumption failures.
- Run basic OLS regression with categorical-predictor encoding, VIF diagnostics,
  and safe interaction handling.
- Detect interaction terms and support minimal moderation safety: centering
  guidance, interaction interpretation warnings, and simple-slopes output for
  supported cases.
- Generate Korean-first APA-style report text with effect sizes, confidence
  intervals, sample sizes, exclusion counts, and non-causal wording unless the
  design justifies causal language.

## Explicit V1 Exclusions

The following are not V1 execution features:

- Mediation analysis that produces indirect effects.
- Bootstrap confidence intervals for indirect effects.
- Conditional indirect effects.
- Johnson-Neyman regions.
- PROCESS-compatible model coverage.
- Repeated-measures ANOVA or Friedman tests for three or more within-subject
  levels.
- Mixed models and MANOVA.
- Any generated interpretation from an LLM or SLM.
- External API calls for statistical guidance, routing, or result explanation.

When users request mediation in V1, the app must not fabricate a partial result.
It should explain that the requested model is not supported in V1, list the
missing statistical requirements, and point to external verification paths such
as PROCESS, R/lavaan, or jamovi/jAMM. The tone must be practical rather than
scolding: the product should not trap the user inside Modori.

## V1.x Priority

Mediation is a V1.x priority, not a vague future idea. The V1.x module must be
planned as a separate, heavily verified advanced-process module with:

- Bootstrap confidence intervals.
- Indirect-effect significance reporting.
- Model templates and path diagrams.
- Conditional-effect handling where supported.
- Johnson-Neyman support if moderation coverage requires it.
- Golden tests against trusted PROCESS/R/lavaan outputs.
- Clear limits for cross-sectional causal interpretation.

Repeated-measures coverage beyond two-time paired comparisons is also V1.x. It
requires its own gates before exposure:

- Sphericity evaluation for repeated-measures ANOVA.
- Greenhouse-Geisser correction when sphericity is violated.
- Friedman routing for nonparametric repeated-measures cases.
- Golden tests against trusted R/SPSS outputs.

## Deterministic Guidance Boundary

V1 guidance must be implemented through deterministic rules and the knowledge
library.

Allowed:

- Rule-based method suggestions generated from variable metadata and engine
  diagnostics.
- Deterministic explanations resolved from curated library entries.
- Korean-first report prose generated from engine-owned result DTOs and fixed
  templates.
- Future SLM rewriting of already-grounded text, if a later spec approves it.

Forbidden in V1:

- Model-generated statistical recommendations.
- Model-generated variable-role selection.
- Model-generated interpretation that can contradict numeric results.
- Any hidden network call.
- Any AI output treated as a source of statistical truth.

If an SLM is added later, it must be optional, disabled by default on unsupported
hardware, grounded in the library, and unable to inspect raw data, choose
variables, calculate statistics, or invent result claims. If it rewrites approved
report text, numeric fields must be passed through as immutable placeholders from
deterministic result DTOs.

## Data Management Requirements

V1 must not stop at "import and inspect." Data management is part of the
competitive wedge because survey users often lose time before analysis begins.

Required V1 data operations:

- Import with metadata preservation.
- Missing-code normalization at compute time without destructive source edits.
- Recode values into new columns.
- Reverse-code selected items into new columns.
- Compose scale scores from selected items.
- Choose and display missing policies for scale composition and analyses.
- Show analysis-specific N and excluded N.
- Support categorical predictor encoding for regression.
- Persist all operations as replayable Steps.

The first implementation does not need a full reshape/merge studio. However, the
data model must not block later merge, reshape, and automatic recode features.

## Statistical Safety Gates

These gates are release-critical. A feature that cannot satisfy its gates should
remain disabled or hidden.

- Golden/reference tests are required for every statistic that enters a report.
- t-test defaults to Welch unless a specific paired or one-sample design is
  selected.
- Chi-square expected-cell violations produce warnings and exact-test routing
  where supported.
- ANOVA includes post-hoc routing. Tukey is acceptable for ordinary equal-variance
  cases; Games-Howell is required for unequal-variance routing.
- Every inferential report includes effect size and confidence interval where a
  standard effect-size CI is supported.
- p-values must not be reported alone.
- Multiple comparisons against the same outcome must trigger correction guidance
  such as Holm or Bonferroni.
- Factor/PCA guidance must not rely on eigenvalue-greater-than-one alone;
  parallel analysis is the default factor-count guide.
- KMO and Bartlett checks are reported before factor/PCA interpretation.
- Listwise or pairwise deletion must never silently shrink N; used N and excluded
  N are always visible.
- Normality routing must not rely on Shapiro-Wilk p-values alone in large samples.
- ANCOVA checks homogeneity of regression slopes before interpretation.
- Regression reports include VIF diagnostics.
- Categorical predictors in regression require explicit encoding.
- Automatic report prose uses non-causal wording for cross-sectional correlation
  or regression unless the design metadata explicitly supports causal language.
- Stale results are visibly marked and never presented as current.

## Analysis Coverage

V1 must support this practical set before the product can claim the survey
pipeline is release-ready:

- Descriptives and Table 1 summaries.
- Reliability with item-total diagnostics.
- Frequency, crosstab, chi-square, and exact-test routing.
- Correlation, including Pearson/Spearman routing.
- Independent Welch t-test.
- Paired t-test.
- Mann-Whitney U.
- Wilcoxon signed-rank.
- Kruskal-Wallis.
- ANOVA with post-hoc tests.
- ANCOVA with slope-homogeneity check.
- Factor analysis/PCA with KMO, Bartlett, and parallel analysis.
- Basic OLS regression with dummy coding, VIF, and interaction safety.

Logistic, ordinal, and multinomial regression remain important, but they are V1.x
unless the implementation plan finds a narrow, fully verified slice that does not
delay the V1 survey pipeline.

## Report Output Requirements

Generated report text is a product feature, but it is also a statistical risk
surface.

V1 report output must:

- Be Korean-first.
- Include method name, sample size, excluded cases, statistic, df where
  applicable, p-value, effect size, and confidence interval where supported.
- Mention assumption reroutes and why they occurred.
- Avoid causal verbs for cross-sectional association models.
- Keep warnings near the affected result.
- Link each explanation to deterministic knowledge-library entries.
- Be regenerated from current pipeline results, never edited as free text inside
  the analysis result.

## Architecture

The design uses the existing project architecture:

- `Pipeline` and `Step` remain the source of truth.
- Data-preparation operations are Steps.
- Analysis operations are Steps.
- Result DTOs carry all numeric values and display-ready report fields.
- The UI remains a thin shell over engine Steps and result DTOs.
- The knowledge library supplies deterministic explanations and method guidance.

No UI component may compute statistics or decide routing from raw numbers. UI
actions collect intent and create/edit Steps.

## Testing And QA

Verification must cover both numeric correctness and decision correctness.

Required test classes:

- Golden numeric tests against trusted references for each statistic.
- Routing tests for assumption failures and supported alternatives.
- Report-text tests that assert required fields and forbidden causal wording.
- Pipeline replay tests for import, recode, scale composition, analysis, and
  re-run after data changes.
- UI boundary tests proving the UI does not import statistical libraries or call
  reduction APIs.
- Clean Windows packaged smoke tests for import and at least one complete
  pipeline.
- Fixture parity tests across CSV/XLSX/SAV where file contents are intended to be
  equivalent.

Any unsupported advanced model must fail closed with an actionable explanation,
not a partial result.

## Risk Register

Primary risks:

- A single incorrect reported statistic can destroy product trust.
- A wrong guidance branch can invalidate an otherwise correct calculation.
- Thin data-management coverage would make Modori a weaker version of existing
  free tools.
- Scope creep from "SPSS-grade" language can prevent V1 from shipping.
- Mediation absence may push thesis users back to SPSS/PROCESS unless V1.x is
  explicitly prioritized.

Mitigations:

- Keep V1 as a vertical pipeline, not a menu-completion project.
- Require golden tests before exposing reportable statistics.
- Keep unsupported advanced analyses visibly unsupported.
- Treat data-preparation depth and report reproducibility as first-class scope.
- Track mediation as the first advanced-process module after V1.
