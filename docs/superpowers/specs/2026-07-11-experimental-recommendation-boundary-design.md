# Experimental Recommendation Boundary Design

**Status:** Owner-approved; external-review amendments incorporated; implementation
plan pending

**Date:** 2026-07-11

## 1. Decision

Modori V1 keeps the recommendation implementation, but exposes it only as an
experimental analysis-candidate aid. The validated calculation modules remain stable
and executable. Recommendation selection quality is not promoted, scored, or described
as validated until the approved human benchmark gates exist.

This design does not delete recommendation code, add the future semantic-profile
architecture, or weaken the calculation engine. It separates product claims that are
currently coupled in one `level` field.

This document is the product-exposure authority for recommendation vocabulary. The
future semantic design in
`docs/superpowers/specs/2026-07-10-semantic-profiling-recommendation-memory-design.md`
must use this document's `evidence_status` and routing-tier split for live product
behavior. Historical benchmark terms remain versioned evidence vocabulary only.

## 2. Source-Lane Prerequisite

The canonical benchmark artifacts are not present on the current
`release/readiness-1-9` tip (`4e1170c58af35edc20e172f616b51d3464a5a2ef`). They are
owned by `codex/recommendation-benchmark-pilot`, which descends from that release tip.

Implementation therefore continues on this worktree or another descendant containing
both:

- baseline artifact commit `145a4485d4dd29f68573b318ce1f4f301c464bde`;
- benchmark hardening commit `ec092d55046d3348000bb6e05dfed744963e85cb`.

The canonical baseline path and identities are:

```text
tests/fixtures/recommendation_benchmark/public/pilot/baseline-a-predictions.jsonl
SHA-256 FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650
scorer fingerprint sha256:1d232ac88bc705b8c31735aa6e997d253a388a478c9337d146f6798d50f33aac
scorer implementation digest sha256:127d7cd7c1f313a592ed6d491307e891fee138f59212ecbbe8e1da8a78765679
```

The full recommendation-benchmark branch is integrated into the release lane before
or together with this implementation. Cherry-picking UI commits onto a release tip
that lacks the canonical pack is forbidden because artifact-preservation tests would
have no reference object.

## 3. Verified Current-State Problem

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

## 4. Goals

- Keep every validated calculation module `EXECUTABLE` within its recorded scope.
- Make all currently generated recommendation candidates explicitly experimental.
- Remove `strong`, accuracy, expert-equivalence, or validated-selection wording from
  production UI and product documentation.
- Require an explicit user choice to enter the experimental guidance surface.
- Present no automatically selected candidate when experimental guidance opens.
- Ensure selecting a candidate never mutates the pipeline or starts calculation.
- Require the user to inspect and confirm variable roles and design settings before an
  experimental candidate can influence an analysis configuration.
- Preserve direct manual analysis as a stable, non-experimental path.
- Preserve the frozen benchmark scorer, baseline artifact, and baseline prediction hash.
- Preserve the ability to promote individual recommendation families later, based on
  approved human evidence rather than code age or intuition.
- Ensure recommendation failure cannot block data access, manual configuration,
  calculation, report export, or application shutdown.

## 5. Non-Goals

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

## 6. State Model

### 6.1 Calculation status

`AnalysisStatus.EXECUTABLE` continues to mean that the calculation module can run
inside its documented scope. This status says nothing about whether Modori can choose
that module from a research question.

No calculation module is demoted merely because the recommendation layer is
experimental.

### 6.2 Recommendation evidence status

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

### 6.3 Heuristic routing tier

Replace product-confidence vocabulary in the live recommendation DTO with internal
routing vocabulary:

```text
PRIMARY
SECONDARY
HEIGHTENED_REVIEW
```

The routing tier only controls deterministic ordering and historical-baseline adapter
behavior. It is not a probability, confidence score, accuracy claim, evidence level,
or validated priority. Live product state starts with no selected candidate; the user
must choose one from the list.

The current ordering behavior remains stable:

- former `강한 추천` -> `PRIMARY`;
- former `가능한 후보` -> `SECONDARY`;
- former `주의 필요` -> `HEIGHTENED_REVIEW`.

The production UI must not render these enum names as trust claims. It may render
workflow requirements such as `설정 확인 필요` or `주의 깊은 검토 필요`.

The experimental surface displays this caption beside the list:

`후보 순서는 검증된 정확도나 우선순위가 아니라 현재의 결정론적 정렬 규칙입니다.`

### 6.4 Frozen benchmark level

The recommendation benchmark retains its versioned
`strong`/`candidate`/`caution`/`none` vocabulary because it measures the historical A
baseline and future promotion gates. The baseline adapter maps internal routing tiers
to those frozen benchmark values.

The committed pilot predictions, scorer fingerprint, implementation digest, and
prediction SHA-256 must remain unchanged. Benchmark vocabulary is research evidence;
it must not leak into product UI.

### 6.5 Recommendation state and preparation DTO

Remove `default_candidate` from live product state. `RecommendationState` contains the
ordered candidates, an initially null `selected_candidate`, and a status message. The
versioned benchmark adapter owns a separate `historical_baseline_default()` function
that reproduces baseline A without changing live product selection behavior.

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

## 7. Catalog Contract

Replace confidence-shaped catalog routing names with behavior-shaped names:

```text
PRIMARY_REVIEW
SECONDARY_REVIEW
HEIGHTENED_REVIEW
MANUAL_ONLY
NEVER
```

The first three require `recommendation_evidence_status=EXPERIMENTAL` in V1. Contract
tests reject a candidate-emitting module with missing or unknown evidence status.

The catalog must be able to answer two independent questions:

1. Can the calculation module execute?
2. What evidence permits the product to expose a candidate for user review?

No caller may infer the second answer from the first.

## 8. Product Experience

The exact surface wording in Sections 8.1 and 8.2 is amended by
`docs/superpowers/specs/2026-07-11-data-grid-interaction-hardening-design.md`.
The experimental evidence boundary remains persistent, but repeated experimental
labels are consolidated into one compact panel-level status.

### 8.1 Entry and mode boundary

- The controller default mode becomes `standard`.
- Opening data directly or from recent files stays in standard mode.
- `안내 모드` becomes `분석 후보 안내` in Korean production text.
- Every process starts in standard mode. Mode is not persisted in V1. Entering
  experimental guidance is an explicit action once per running application session;
  no valid, stale, or malformed prior setting can restore it on the next launch.
- The experimental surface displays a persistent, compact status label:
  `실험적 · 자동 실행 안 함`.
- Stable manual analysis remains available regardless of recommendation state.

No modal warning is required merely to inspect the experimental surface. Repeated
modal warnings would train users to dismiss them. Confirmation is placed at the point
where a candidate can affect configuration.

### 8.2 Candidate presentation

- No candidate is selected when the surface opens.
- The ordered experimental candidate list is visible without a hidden default card.
- A user selection creates `현재 검토 후보`; before selection that surface is empty.
- `다른 추천 보기` becomes `분석 후보 목록`.
- Candidate labels use `분석 후보`; no candidate displays `강한 추천`.
- `수준` becomes `검토 상태`.
- The reason remains visible and must describe observed deterministic facts, not the
  candidate as statistically correct.
- Configuration-required and heightened-review candidates retain visible warnings.
- No percentage, star rating, probability, model confidence, or expert-equivalence
  language is displayed.
- The candidate-order caption from Section 6.3 is always visible with the list.

### 8.3 Selection, preparation, confirmation, and execution

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

The shortcut removal must not make an existing candidate family unreachable. Before
the shortcut is deleted, all emitted candidate kinds must have an explicit manual-form
path. Repeated-measures ANOVA and Friedman use a reviewed measures list; mediation and
moderated mediation use separately named X, mediator, moderator, Y, model, and
covariate fields. Mediation roles must never be inferred later from positional list
indexes. An exhaustive contract test locks the candidate-kind-to-form mapping so a new
provider cannot silently create an unreviewable candidate.

### 8.4 Selection provenance

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

## 9. Failure and Recovery Rules

- Missing, corrupt, or failing recommendation providers yield an unavailable
  experimental surface and leave manual analysis operational.
- Unknown recommendation evidence status fails closed as unavailable; it never falls
  back to validated or primary-review routing.
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

## 10. Compatibility and Migration

- Existing calculation step schemas do not change.
- Existing analysis result DTOs do not change.
- Existing benchmark JSONL schemas and scorer fingerprint do not change.
- Existing user settings without an experimental mode field load into standard mode.
- No previous setting may silently opt a user into experimental guidance.
- The current committed A-baseline prediction file remains byte-for-byte identical.
- `default_candidate` is removed from live product callers; only the frozen baseline
  adapter owns historical-default compatibility.
- Public API callers of the old recommendation `level` field receive an explicit
  migration failure or a versioned compatibility adapter; silent semantic reuse is
  forbidden.

## 11. Testing Contract

### 11.1 Unit and catalog tests

- Calculation status and recommendation evidence status are independent.
- Every candidate-emitting module is experimental.
- No current module is validated.
- Routing tiers preserve frozen candidate order while live product state starts with no
  selection.
- The historical baseline adapter alone preserves old default-selection behavior.
- Unknown evidence and routing values fail closed.

### 11.2 Benchmark preservation tests

- Rebuild the current A baseline into a fresh temporary output.
- Assert byte equality and SHA-256 equality with the committed prediction file.
- Assert the scorer fingerprint and implementation digest are unchanged.
- Run the complete recommendation benchmark and workbook contract suite.

### 11.3 Controller and pipeline tests

- Selecting a candidate does not alter steps, pipeline version, cache, results, or
  worker submissions.
- Opening experimental mode does not select a candidate.
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

### 11.4 UI and product-wording tests

- Standard mode is the default for direct and recent-file opens.
- Experimental mode has a persistent status label and explicit entry action.
- Production UI, QML-accessible names, report templates, Word export text,
  knowledge/help library entries, and product-facing documentation contain no
  `강한 추천`, `기본 추천`, `추천 분석 실행`, accuracy percentage, or
  expert-equivalence claim.
- Frozen benchmark fixtures, scorer diagnostics, historical evidence ledgers, and
  migration tests may retain versioned historical terms only through an explicit
  path allowlist.
- Product-wording tests fail if a new production-text path is added without being
  classified as scanned or historical-evidence-only.
- The unvalidated deterministic-order caption is visible and accessible.
- Candidate buttons are stable in width and do not overflow at the supported minimum
  window size.
- Keyboard and screen-reader names disclose experimental status and confirmation.
- QML runtime tests cover select, prepare, confirm, apply, run, cancel, and switch-to-
  manual paths.

### 11.5 Regression and package gates

- All focused recommendation, UI, benchmark, report, and analysis-contract tests pass.
- The full quality gate and slow statistical gate pass with no new unexplained skips.
- A fresh Windows package passes launch, engine, and public-data smokes.
- The 22 V1 calculation smoke checks remain unchanged.

## 12. VM Acceptance Scope

After automated gates and a fresh payload rebuild, the owner performs a bounded visual
walkthrough in `Modori-CleanWin-QA-Direct`:

1. direct data open stays in standard mode;
2. experimental guidance requires an explicit mode choice;
3. no candidate is preselected and the ordering disclaimer is visible;
4. a regular candidate is visibly experimental and does not auto-run;
5. a configuration-required candidate opens fields without inventing missing choices;
6. a no-candidate dataset preserves manual analysis;
7. confirmation is required before the candidate-assisted configuration runs;
8. the same analysis can run manually and produces the same result;
9. report export discloses experimental selection provenance only when applicable;
10. normal application and Windows shutdown succeed.

This walkthrough proves interaction and disclosure behavior. It does not prove
recommendation accuracy.

The future semantic question planner is not present in this scope, so this VM pass does
not claim a true clarification-question flow. `설정 확인 필요` is tested only as a
configuration boundary.

## 13. Promotion Rule

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

## 14. Implementation Order

1. Verify that the implementation worktree contains the canonical benchmark commits
   and artifact hashes from Section 2.
2. Add state separation and benchmark-preserving adapters.
3. Migrate providers and catalog routing vocabulary.
4. Lock benchmark artifact identity before UI changes.
5. Remove live default selection and combined apply-and-run recommendation commands.
6. Make standard mode the per-process default and add experimental product wording.
7. Add select/prepare/confirm/manual-run flow and provenance.
8. Add report disclosure without changing numerical step schemas.
9. Run focused, full, slow, package, and payload gates.
10. Run the owner-operated VM acceptance walkthrough.

## 15. External Review Disposition

1. **Benchmark source lane:** accepted. Section 2 pins the prerequisite commits,
   artifact path, file hash, scorer fingerprint, and integration order.
2. **Mode persistence:** accepted. V1 starts every process in standard mode and never
   persists experimental-mode entry.
3. **Default-shaped routing name:** accepted. Routing uses `PRIMARY_REVIEW` and
   `SECONDARY_REVIEW`; no `DEFAULT_ELIGIBLE` name remains.
4. **Ordering anchor:** strengthened beyond the requested disclosure. Live product
   state has no preselected candidate, and the still-deterministic order is publicly
   described as unvalidated.
5. **Forbidden wording scan:** accepted. The scan covers UI, accessibility, help,
   reports, Word export, and product documents with an explicit historical-evidence
   allowlist.
6. **Semantic-spec vocabulary:** accepted. Both specifications cross-reference the
   evidence-status and routing-tier model; frozen benchmark terminology remains
   isolated as historical evaluation vocabulary.
