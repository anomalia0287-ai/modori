# Novice Analysis Guidance Design - 2026-07-03

## Decision Status

Approved direction: **C-C, revised to C-2**.

The product goal is not merely to expose statistical controls. Modori must let a
user who is not confident with statistics import data, understand plausible next
steps, and run an analysis without needing to infer the correct variable roles
from raw column names.

## Problem

Clean Windows VM QA found three separate facts:

- The packaged engine smoke path succeeds with `engine-smoke-reference.xlsx`.
- CSV/XLSX visible import can show preview, variable view, and table data.
- SAV visible import failed before showing the import confirmation dialog because
  SPSS metadata may report variable measure as `unknown`.

The visible import flow also exposed a product-level UX failure: after import,
the app can make a novice user unsure whether the next failure is their mistake
or the tool's mistake. A statistical product aimed at novice users must not
require the user to guess which variables are appropriate.

## Scope

This design fixes the release-blocking UX path without trying to solve every
general-purpose statistical recommendation problem.

In scope:

- Stop automatic analysis immediately after import.
- Show an analysis preparation panel after successful import.
- Fill one safe default recommendation when the data supports it.
- Allow users to choose from other plausible recommendation candidates.
- Allow direct manual variable selection.
- Explain why each recommendation exists.
- Use coarse recommendation levels instead of percentages.
- Prevent execution when required variables are missing or invalid.

Out of scope for the first implementation:

- Machine-learning based recommendation.
- Numeric confidence scores.
- Full natural-language statistical tutoring.
- Supporting every possible statistical design.
- Automatically claiming a recommendation is the user's research intent.

## UX Model

After data import succeeds, Modori enters an **analysis preparation** state:

```text
Data imported
Preview/table/variable views are available
No analysis has run yet
The right-side preparation panel shows a default recommendation
The user can run, choose another recommendation, or select variables manually
```

The app must not call `rerunNow()` automatically from the import confirmation
flow. Analysis starts only after the user selects or accepts a configuration and
clicks an explicit run action.

## Safety Invariants

These invariants are mandatory. If an invariant cannot be satisfied, the UI must
disable analysis execution and show a plain-language reason.

- Analysis never starts from import confirmation, preview loading, table loading,
  variable view loading, or recommendation generation.
- Analysis starts only from an explicit user run action.
- The run action re-validates the currently selected configuration immediately
  before calling the engine worker.
- The engine worker must not receive unknown columns, empty required roles, or
  invalid role combinations from the recommendation/manual-selection path.
- Recommendation candidates are derived from the current imported schema and are
  discarded when the dataset changes.
- Choosing another recommendation only updates the prepared configuration and
  reason text. It never triggers analysis.
- A `주의 필요` candidate is never selected as the default while any `강한 추천` or
  `가능한 후보` candidate exists.
- Import success, recommendation presence, user-requested run, validation
  failure, and engine failure are represented as separate states.

## Recommendation Display

The panel shows a single default recommendation first:

```text
기본 추천
신뢰도 분석: A1-A5
수준: 강한 추천
이유: 같은 접두사 묶음, 다섯 개의 숫자형 설문 문항, 유사한 값 범위

[분석 실행] [다른 추천 보기] [직접 선택]
```

The user can open other recommendations:

```text
다른 추천 후보
- 신뢰도 분석: C1-C5
- 신뢰도 분석: E1-E5
- 집단 비교: A 평균 by gender
- 집단 비교: C 평균 by gender
- 회귀: age -> A 평균
```

Selecting a candidate replaces the fields in the preparation panel and updates
the reason text. It does not run analysis until the user clicks run.

## Default Recommendation Selection

The default recommendation is the highest-ranked safe candidate, not the only
valid candidate.

Candidate ranking order:

1. Strong item-group reliability candidates.
2. Strong two-group comparison candidates using a clear grouping variable and a
   numeric outcome or computed item-scale summary.
3. `가능한 후보` level candidates with valid variables but weaker intent
   evidence.
4. `주의 필요` level candidates, which are never auto-filled as the default
   unless no stronger candidate exists and the UI visibly marks the choice as
   cautionary.

When multiple candidates have the same level, prefer the one with the clearest
column pattern and shortest explanation. Keep all peer candidates available in
the alternatives list.

## Recommendation Levels

Use three levels in the first release:

- `강한 추천`
- `가능한 후보`
- `주의 필요`

Do not use percentages. Percentages imply precision the product does not have
and create a second interpretation problem for novice users.

Five levels may be added later only if user testing shows the three-level model
is too coarse.

## Recommendation Rules

The first implementation uses deterministic, explainable heuristics.

Exclude columns that look like:

- row names or IDs;
- mostly missing values;
- near-constant values;
- too many categories for a grouping variable.

Detect candidate roles:

- Item candidates: numeric columns with narrow survey-like value ranges.
- Item groups: repeated prefix/name patterns such as `A1-A5`, `C1-C5`.
- Group candidates: categorical or low-cardinality columns, especially two-level
  columns such as `gender`.
- Outcome candidates: numeric variables or computed item-scale summaries.
- Caution candidates: variables such as `age` or `education` where intent is
  plausible but not guaranteed.

Analysis validation:

- Reliability needs at least three compatible item variables.
- Group comparison needs a numeric outcome and a valid grouping variable.
- Regression needs a numeric outcome, compatible predictors, and enough rows.
- If no safe candidate exists, show an empty preparation state with instructions
  instead of a forced recommendation.

## Error Handling

Invalid configurations known from imported metadata must be blocked before
engine execution. If validity cannot be determined confidently, the UI must mark
the candidate as `주의 필요` and require an explicit user run action after showing
the reason.

Examples:

- Missing required columns: show which variable is missing and which choice needs
  it.
- No valid group variable: explain the grouping requirement.
- SAV metadata reports `unknown` measure: infer from data instead of failing the
  preview/import path.
- Recommendation exists but is uncertain: mark it as `주의 필요` and require
  explicit run.

Engine exceptions may still occur, but ordinary invalid variable choices should
not surface as only `Engine execution error`.

## Acceptance Criteria

- Importing CSV/XLSX/SAV visible fixtures opens the preview/confirmation flow.
- After confirmation, table and variable views are available.
- No automatic analysis runs immediately after import.
- The preparation panel shows one default recommendation when safe.
- Alternative recommendations can be selected and update the prepared fields.
- Manual selection remains possible.
- Recommendation levels use the three-level label model.
- Each recommendation shows a short reason.
- Running an invalid recommendation is blocked before the engine worker when the
  invalidity is knowable from imported metadata.
- The run action re-validates the selected configuration immediately before
  engine execution.
- Dataset changes discard stale recommendation candidates.
- Choosing another recommendation never starts analysis.
- `주의 필요` candidates are not used as the default when stronger candidates
  exist.
- Clean VM QA can distinguish:
  - import success;
  - recommendation presence;
  - user-confirmed analysis run;
  - analysis failure.

## Test Strategy

Add focused tests for:

- SAV `unknown` variable measure falls back to inferred measure.
- Import confirmation does not automatically call `rerunNow()`.
- Recommendation service produces item-group candidates for BFI-style columns.
- Recommendation service produces a two-group comparison candidate when a valid
  group variable exists.
- Recommendation service returns no forced default when no safe candidate exists.
- Selecting an alternative recommendation updates the prepared fields and reason
  text without running analysis.
- Run action validation blocks unknown columns, missing required roles, and
  invalid role combinations before the engine worker is called.
- Dataset replacement clears stale recommendations.
- `주의 필요` candidates are excluded from default selection when `강한 추천` or
  `가능한 후보` candidates exist.
- QML exposes the preparation panel actions: run selected recommendation, show
  other recommendations, choose manually.

Clean VM rerun requirements:

- Rebuild package after fixes.
- Regenerate Payload V2 or create the next explicitly named payload only if the
  recovery runbook is updated.
- Rerun engine smoke.
- Rerun visible import QA for CSV/XLSX/SAV.
- Confirm SAV preview dialog appears in the VM.
- Confirm automatic analysis does not run immediately after import.

## Risks

- Overconfident recommendations can mislead users.
- Too many alternatives can overwhelm novice users.
- Hard-coded fixture-specific recommendations would pass QA while failing real
  user data.

Mitigations:

- Keep the default recommendation conservative.
- Collapse alternatives behind a secondary action.
- Require a plain-language reason for each recommendation.
- Build recommendation rules around general column patterns, not fixture names.
