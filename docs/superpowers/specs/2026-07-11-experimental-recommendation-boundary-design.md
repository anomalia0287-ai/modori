# Experimental Recommendation Boundary Design

**Status:** Owner-approved direction; written-spec review pending before implementation

**Date:** 2026-07-11

## 1. Decision

Modori V1 keeps the recommendation implementation, but exposes it only as an
experimental analysis-candidate aid. The validated calculation modules remain stable
and executable. Recommendation selection quality is not promoted, scored, or described
as validated until the approved human benchmark gates exist.

This design does not delete recommendation code, add the future semantic-profile
architecture, or weaken the calculation engine. It separates product claims that are
currently coupled in one `level` field.

## 2. Verified Current-State Problem

The current implementation couples four different concepts:

1. calculation-module execution status;
2. product-facing recommendation confidence;
3. heuristic candidate ordering and default selection;
4. the frozen benchmark baseline's `strong`/`candidate`/`caution` levels.

`RecommendationCandidate.level` currently contains Korean product claims such as
`강한 추천`. The same value orders candidates, selects a default, renders directly in
QML, and maps into the frozen benchmark baseline. `AnalysisModuleSpec` also uses
`RecommendationPolicy.STRONG` for three families.

The guided UI currently starts as the controller default. Opening data directly or from
recent files can therefore expose recommendation guidance without an explicit
experimental-mode choice. `GuideRail.qml` also calls
`runPreparedRecommendationNow()`, whose controller path applies the selected candidate
and immediately calls `rerun()`.

These behaviors conflict with the approved V1 product boundary.

## 3. Goals

- Keep every validated calculation module `EXECUTABLE` within its recorded scope.
- Make all currently generated recommendation candidates explicitly experimental.
- Remove `strong`, accuracy, expert-equivalence, or validated-selection wording from
  production UI and product documentation.
- Require an explicit user choice to enter the experimental guidance surface.
- Ensure selecting a candidate never mutates the pipeline or starts calculation.
- Require the user to inspect and confirm variable roles and design settings before an
  experimental candidate can influence an analysis configuration.
- Preserve direct manual analysis as a stable, non-experimental path.
- Preserve the frozen benchmark scorer, baseline artifact, and baseline prediction hash.
- Preserve the ability to promote individual recommendation families later, based on
  approved human evidence rather than code age or intuition.
- Ensure recommendation failure cannot block data access, manual configuration,
  calculation, report export, or application shutdown.

## 4. Non-Goals

- Claiming or estimating recommendation accuracy.
- Creating human gold labels or replacing qualified human reviewers with model output.
- Implementing semantic profiles, memory, SLM assistance, or the future question
  planner.
- Adding new analysis families.
- Changing numerical algorithms, result DTOs, statistical reports, or reference
  tolerances.
- Marking a manually selected calculation or its numeric output as experimental.
- Treating `requires_configuration` as a validated clarification-planning system.
- Publishing the locked benchmark corpus.

## 5. State Model

### 5.1 Calculation status

`AnalysisStatus.EXECUTABLE` continues to mean that the calculation module can run
inside its documented scope. This status says nothing about whether Modori can choose
that module from a research question.

No calculation module is demoted merely because the recommendation layer is
experimental.

### 5.2 Recommendation evidence status

Add a recommendation evidence status independent of calculation status:

```text
NOT_APPLICABLE
EXPERIMENTAL
VALIDATED
```

For V1 after this change:

- every module that can emit a recommendation candidate is `EXPERIMENTAL`;
- modules with `MANUAL_ONLY` or `NEVER` routing are `NOT_APPLICABLE`;
- no module is `VALIDATED`.

`VALIDATED` is reserved for a future family-specific promotion backed by the approved
human benchmark and release decision. It cannot be inferred from unit tests, reference
parity, an external code review, or elapsed time.

### 5.3 Heuristic routing tier

Replace product-confidence vocabulary in the live recommendation DTO with internal
routing vocabulary:

```text
PRIMARY
SECONDARY
HEIGHTENED_REVIEW
```

The routing tier only controls deterministic ordering and whether an initial candidate
may be selected for inspection. It is not a probability, confidence score, accuracy
claim, or evidence level.

The current ordering behavior remains stable:

- former `강한 추천` -> `PRIMARY`;
- former `가능한 후보` -> `SECONDARY`;
- former `주의 필요` -> `HEIGHTENED_REVIEW`.

The production UI must not render these enum names as trust claims. It may render
workflow requirements such as `설정 확인 필요` or `주의 깊은 검토 필요`.

### 5.4 Frozen benchmark level

The recommendation benchmark retains its versioned
`strong`/`candidate`/`caution`/`none` vocabulary because it measures the historical A
baseline and future promotion gates. The baseline adapter maps internal routing tiers
to those frozen benchmark values.

The committed pilot predictions, scorer fingerprint, implementation digest, and
prediction SHA-256 must remain unchanged. Benchmark vocabulary is research evidence;
it must not leak into product UI.

### 5.5 Recommendation state and preparation DTO

Rename the live-state concept `default_candidate` to `initial_review_candidate`. The
initial candidate may be selected for inspection, but it is not a product default or a
claim that the analysis is appropriate. The versioned benchmark adapter may continue
to call the corresponding historical concept a default when reconstructing baseline A.

Introduce a pure `RecommendationPreparation` DTO containing only:

```text
candidate_id
analysis_intent
prefill_fields
evidence_status
review_requirement
```

Creating this DTO cannot edit a step, increment the pipeline version, invalidate a
cache, submit a worker job, or calculate a result. The existing manual editor consumes
user-confirmed fields after preparation. The current `applySelectedRecommendation()`
pipeline-mutating shortcut is removed from the experimental path rather than renamed.

## 6. Catalog Contract

Replace confidence-shaped catalog routing names with behavior-shaped names:

```text
DEFAULT_ELIGIBLE
CANDIDATE_ONLY
HEIGHTENED_REVIEW
MANUAL_ONLY
NEVER
```

The first three require `recommendation_evidence_status=EXPERIMENTAL` in V1. Contract
tests reject a candidate-emitting module with missing or unknown evidence status.

The catalog must be able to answer two independent questions:

1. Can the calculation module execute?
2. What evidence permits the product to expose automatic candidate selection?

No caller may infer the second answer from the first.

## 7. Product Experience

### 7.1 Entry and mode boundary

- The controller default mode becomes `standard`.
- Opening data directly or from recent files stays in standard mode.
- `안내 모드` becomes `실험적 후보 안내` in Korean production text.
- Entering that mode is an explicit user action; it is never restored implicitly from
  a stale or malformed setting.
- The experimental surface displays a persistent, compact status label:
  `검증 중인 분석 후보 · 자동 실행 안 함`.
- Stable manual analysis remains available regardless of recommendation state.

No modal warning is required merely to inspect the experimental surface. Repeated
modal warnings would train users to dismiss them. Confirmation is placed at the point
where a candidate can affect configuration.

### 7.2 Candidate presentation

- `기본 추천` becomes `현재 검토 후보`.
- `다른 추천 보기` becomes `다른 실험적 후보 보기`.
- Every candidate displays `실험적 후보`; no candidate displays `강한 추천`.
- `수준` becomes `검토 상태`.
- The reason remains visible and must describe observed deterministic facts, not the
  candidate as statistically correct.
- Configuration-required and heightened-review candidates retain visible warnings.
- No percentage, star rating, probability, model confidence, or expert-equivalence
  language is displayed.

### 7.3 Selection, preparation, confirmation, and execution

Candidate interaction is split into explicit phases:

1. **Select:** changes only the selected candidate and visible preparation state.
2. **Prepare:** pre-fills the existing manual analysis form with candidate variables
   and design mode. It does not add or change a pipeline step.
3. **Confirm:** the user confirms that the research question, variable roles, and sample
   structure were checked. Confirmation is invalidated when the dataset, candidate,
   relevant fields, or mode changes.
4. **Apply and run:** the existing manual configuration path validates the fields,
   applies the step, and starts calculation only after the explicit final command.

The production UI and controller must not expose a convenience command that applies a
recommendation directly to the pipeline or that combines recommendation application
with `rerun()`. The current `applySelectedRecommendation()`,
`runPreparedRecommendationNow()`, and `runPreparedRecommendation()` path is removed
from production use. Candidate-to-form conversion goes through the pure preparation
DTO; only the existing manual configuration path may edit the pipeline.

Advanced candidates such as binary logistic regression and factorial ANOVA continue to
require explicit event/reference or factor-role configuration. The experimental layer
may pre-fill known fields but cannot invent missing values.

### 7.4 Selection provenance

The UI session records one of:

```text
manual
experimental_candidate_assisted
```

This provenance is local session metadata, not a numerical step parameter. It must not
change the computation or cache key. If a report is exported from an experimentally
assisted configuration, it includes a concise note that method selection used an
experimental candidate aid while the calculation module has its own bounded numerical
evidence. A fully manual configuration has no experimental note.

Switching to direct manual selection clears pending experimental confirmation and
provenance unless an experimental prefill remains in use.

## 8. Failure and Recovery Rules

- Missing, corrupt, or failing recommendation providers yield an unavailable
  experimental surface and leave manual analysis operational.
- Unknown recommendation evidence status fails closed as unavailable; it never falls
  back to validated or default-eligible.
- Dataset replacement, metadata edits, data transforms, or candidate changes invalidate
  pending confirmation.
- A candidate that no longer matches observed variables cannot be applied.
- `requires_configuration` remains a hard block until required fields are supplied.
- An empty candidate set displays that no safe experimental candidate was produced; it
  does not imply that no valid statistical analysis exists.
- Recommendation errors must not mutate the pipeline version, step list, result cache,
  or current dataset.
- Report provenance failure does not block calculation, but it fails report export
  closed rather than emitting a report that silently omits experimental selection
  provenance.

## 9. Compatibility and Migration

- Existing calculation step schemas do not change.
- Existing analysis result DTOs do not change.
- Existing benchmark JSONL schemas and scorer fingerprint do not change.
- Existing user settings without an experimental mode field load into standard mode.
- No previous setting may silently opt a user into experimental guidance.
- The current committed A-baseline prediction file remains byte-for-byte identical.
- `default_candidate` callers migrate to `initial_review_candidate`; the frozen
  baseline adapter owns any historical-default compatibility.
- Public API callers of the old recommendation `level` field receive an explicit
  migration failure or a versioned compatibility adapter; silent semantic reuse is
  forbidden.

## 10. Testing Contract

### 10.1 Unit and catalog tests

- Calculation status and recommendation evidence status are independent.
- Every candidate-emitting module is experimental.
- No current module is validated.
- Routing tiers preserve the frozen candidate order and default-selection behavior.
- Unknown evidence and routing values fail closed.

### 10.2 Benchmark preservation tests

- Rebuild the current A baseline into a fresh temporary output.
- Assert byte equality and SHA-256 equality with the committed prediction file.
- Assert the scorer fingerprint and implementation digest are unchanged.
- Run the complete recommendation benchmark and workbook contract suite.

### 10.3 Controller and pipeline tests

- Selecting a candidate does not alter steps, pipeline version, cache, results, or
  worker submissions.
- Preparing a candidate only changes UI preparation state.
- Applying without current confirmation fails.
- Confirmation resets on dataset, candidate, mode, transform, metadata, or role-field
  changes.
- Direct manual selection never requires experimental confirmation.
- Experimentally assisted and fully manual configurations with identical parameters
  produce identical step params and numerical results.
- Recommendation-provider failure leaves manual calculation usable.
- No combined recommendation-apply-and-rerun controller method remains callable from
  production QML.

### 10.4 UI and wording tests

- Standard mode is the default for direct and recent-file opens.
- Experimental mode has a persistent status label and explicit entry action.
- Production UI contains no `강한 추천`, `기본 추천`, `추천 분석 실행`, accuracy
  percentage, or expert-equivalence claim.
- Candidate buttons are stable in width and do not overflow at the supported minimum
  window size.
- Keyboard and screen-reader names disclose experimental status and confirmation.
- QML runtime tests cover select, prepare, confirm, apply, run, cancel, and switch-to-
  manual paths.

### 10.5 Regression and package gates

- All focused recommendation, UI, benchmark, report, and analysis-contract tests pass.
- The full quality gate and slow statistical gate pass with no new unexplained skips.
- A fresh Windows package passes launch, engine, and public-data smokes.
- The 22 V1 calculation smoke checks remain unchanged.

## 11. VM Acceptance Scope

After automated gates and a fresh payload rebuild, the owner performs a bounded visual
walkthrough in `Modori-CleanWin-QA-Direct`:

1. direct data open stays in standard mode;
2. experimental guidance requires an explicit mode choice;
3. a regular candidate is visibly experimental and does not auto-run;
4. a configuration-required candidate opens fields without inventing missing choices;
5. a no-candidate dataset preserves manual analysis;
6. confirmation is required before the candidate-assisted configuration runs;
7. the same analysis can run manually and produces the same result;
8. report export discloses experimental selection provenance only when applicable;
9. normal application and Windows shutdown succeed.

This walkthrough proves interaction and disclosure behavior. It does not prove
recommendation accuracy.

The future semantic question planner is not present in this scope, so this VM pass does
not claim a true clarification-question flow. `설정 확인 필요` is tested only as a
configuration boundary.

## 12. Promotion Rule

Recommendation families are promoted individually, never as a package. A future
promotion from `EXPERIMENTAL` to `VALIDATED` requires all of the following:

- the applicable human-labeled corpus tier;
- frozen scorer and split evidence;
- predeclared family-specific thresholds;
- independent review and documented disagreement resolution;
- no unresolved E4/E5 safety failures;
- an explicit owner release decision.

Calculation parity, open-source popularity, downloads, contributor count, or a model
upgrade cannot substitute for this rule.

## 13. Implementation Order

1. Add state separation and benchmark-preserving adapters.
2. Migrate providers and catalog routing vocabulary.
3. Lock benchmark artifact identity before UI changes.
4. Remove combined apply-and-run recommendation commands.
5. Make standard mode the default and add experimental product wording.
6. Add select/prepare/confirm/manual-run flow and provenance.
7. Add report disclosure without changing numerical step schemas.
8. Run focused, full, slow, package, and payload gates.
9. Run the owner-operated VM acceptance walkthrough.
