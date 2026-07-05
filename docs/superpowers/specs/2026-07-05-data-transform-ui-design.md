# Data Transform UI Design

## Purpose

Build a commercial-grade minimum data transformation surface for Modori without
weakening the replayable pipeline architecture. The first transform UI must let
users create common survey-analysis transformations while preserving the raw
imported data and recording every change as an explicit pipeline Step.

This design intentionally does not introduce direct data-cell editing. Direct
cell editing remains read-only until a deterministic row-identity and
DataPatchStep design is specified and tested.

## External References Used For The Design Review

- jamovi computed variables: computed columns are a first-class data workflow,
  including survey-style sum scores.
  <https://docs.jamovi.org/data/data_2_computed_variables.html>
- jamovi transformed variables: reusable transforms support recoding and reverse
  scoring patterns.
  <https://docs.jamovi.org/data/data_3_transformed_variables.html>
- Stata recode documentation: recoding workflows support generating new
  variables instead of overwriting source variables.
  <https://www.stata.com/manuals/drecode.pdf>
- WCAG labels and instructions: transform forms need visible labels and
  instructions, not only accessible names.
  <https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html>
- WCAG status messages: transform success, failure, stale results, and rerun
  states must be communicated as status.
  <https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html>
- He and Zhu, "A Fuzzy Sphere Journey in Critical Phenomena": useful design
  analogy for replacing a difficult raw problem with a constrained
  representation that preserves meaning.
  <https://arxiv.org/abs/2607.01310>
- Gour, "Quantum Noncommutativity Uniquely Determines Relative Entropy": useful
  design analogy for choosing defaults by stronger operational criteria, not by
  convention alone.
  <https://arxiv.org/abs/2607.01712>

## Product Position

The UI should feel like a professional analysis tool, not a spreadsheet clone.
The user edits a reproducible analysis recipe, not raw data. The interface should
make the common path fast, but it must always expose enough of the recipe to
explain and reproduce the result later.

Design principle:

> Make transformations easy to request, explicit to review, and impossible to
> confuse with in-place source-data mutation.

## Scope

### In Scope

1. Add a `변환` tab to the central data area.
2. Add a reverse-code panel backed by `RecodeReverseStep`.
3. Add a scale-score panel backed by `ComposeScaleStep`.
4. Strengthen the variable property editor in `변수 보기` so metadata edits feel
   like a complete variable-properties workflow, not only a measure dropdown.
5. Show pre-apply summaries before each transform is committed.
6. Validate output names and reject output-key collisions before mutating the
   live pipeline.
7. Mark prior results stale after a successful transform and route recompute
   through the existing rerun path.
8. Keep the UI thin-shell boundary: QML and `src/modori/ui/**` do not compute
   statistics or inspect dataframe internals.
9. Add tests proving transform Steps survive `Pipeline.to_json` /
   `Pipeline.from_json` and recompute to the same output.

### Out Of Scope

1. Direct cell editing.
2. Arbitrary expression formulas.
3. Bulk value-label table editing beyond a compact, typed metadata patch path.
4. Project save/open UI commands. Core pipeline JSON round-trip must be tested,
   but a user-facing `.modori` file menu is a separate feature.
5. New statistical analyses.

## Screen Structure

The central work area has three tabs:

1. `데이터 보기`
   - Read-only respondent-by-variable grid.
   - Shows a visible source-protection notice, not only a tooltip:
     `원본 데이터는 직접 수정하지 않습니다. 변환은 새 단계와 새 변수로 기록됩니다.`

2. `변수 보기`
   - Variable table remains virtualized.
   - The editing controls become a variable-properties panel:
     - selected variable key
     - label
     - measure
     - missing codes
     - value-label summary
   - The first implementation may keep value-label editing minimal, but the UI
     must show that value labels are metadata and not raw values.

3. `변환`
   - Contains two transform groups:
     - `역코딩`
     - `척도 점수 만들기`
   - Uses dense form rows, visible labels, stable widths, and clear status text.
   - Does not use decorative cards inside cards.

## Reverse-Code Workflow

User flow:

1. Select one or more variables.
2. Set source scale minimum and maximum.
3. Choose an output naming rule:
   - default suffix: `_R`
   - optional custom suffix field
4. Review generated output names.
5. Apply.

Validation:

- At least one variable is required.
- Scale minimum and maximum must be numeric.
- Minimum must be lower than maximum.
- Variable keys must exist in the current dataset.
- Output keys must not collide with existing variables or other planned outputs.
- Duplicate source variables are rejected.

Step behavior:

- Creates or edits one managed `RecodeReverseStep`.
- Source columns are never overwritten.
- Generated columns use the chosen suffix.
- The Step id should be stable and readable, such as `transform:reverse`.
- The Step title should be user-facing, such as `Reverse-code items`.

Pre-apply summary example:

```text
q3, q5를 1-5 척도로 역코딩합니다.
새 변수: q3_R, q5_R
원본 변수는 변경하지 않습니다.
```

## Scale-Score Workflow

User flow:

1. Select two or more item variables.
2. Enter output variable name.
3. Choose method:
   - `평균`
   - `합계`
4. Choose missing policy:
   - `설문 기본`: at least 80% valid responses, default
   - `완전응답`: all selected items must be valid
   - `사용자 지정`: explicit valid-response ratio
5. Review summary.
6. Apply.

Validation:

- At least two item variables are required for the UI workflow.
- Output variable name is required.
- Output name must not collide with existing variables or planned transform
  outputs.
- Duplicate item variables are rejected.
- Method must be `mean` or `sum`.
- Custom `min_valid` must satisfy `0 < min_valid <= 1`.

Step behavior:

- Creates or edits one managed `ComposeScaleStep`.
- The default policy is survey-oriented: `{"preset": "survey", "min_valid": 0.8}`.
- The UI copy explains the default:
  `설문 기본은 선택한 문항의 80% 이상이 유효할 때 평균을 계산합니다.`
- Source columns are never overwritten.

Pre-apply summary example:

```text
q1, q2, q3, q4, q5의 평균으로 job_sat을 만듭니다.
결측 처리: 설문 기본, 80% 이상 응답 필요
원본 변수는 변경하지 않습니다.
```

## Variable Properties Workflow

The existing measure-only edit is not enough for a commercial-grade variable
view. The first strengthened version should expose:

- variable key, read-only
- label
- measure: nominal, ordinal, scale
- missing codes
- value-label summary

Validation:

- Unknown variables are rejected.
- Unsupported measure values are rejected.
- Missing codes must be a list of scalar values that the engine can coerce.
- `display_type` remains unsupported and must return the existing
  `unsupported_metadata_patch` error.
- If both `missing_codes` and `missing_values` are sent, reject the patch as
  ambiguous.

Step behavior:

- Uses `VariableMetadataPatchStep`.
- Raw observed values are never changed.
- Existing `metadata:<variable_key>` Step is reused when possible.

## Controller And Service Boundary

Add a focused transform service under `src/modori/ui/` instead of putting transform
logic directly in `UiController`.

Expected responsibilities:

- Parse user-facing transform requests into engine Step params.
- Validate variable existence and output-key collisions.
- Insert or edit managed transform Steps.
- Return `CommandResult` with stable error codes.
- Leave recompute to the existing pipeline/rerun flow unless an existing local
  pattern already recomputes metadata immediately.

Recommended command surface:

- `applyReverseCodeTransform(payload: Mapping[str, Any]) -> CommandResult`
- `applyScaleScoreTransform(payload: Mapping[str, Any]) -> CommandResult`
- `updateVariableMetadata(variable_key, patch)` remains the metadata command.

QML-facing slots may be convenience wrappers over these commands, but validation
must live in Python.

## Pipeline Placement

Transform Steps should be inserted after the import Step and after relevant
metadata Steps where needed. The ordering must preserve dependency semantics:

1. import
2. variable metadata patches
3. reverse-code transforms
4. scale-score transforms
5. analyses
6. report

If an analysis already exists, adding or editing a transform marks results stale
and requires rerun. It must not silently replace or retarget an analysis Step.

## Status And Error Handling

Success message:

```text
변환 단계가 추가되었습니다. 다시 실행하면 결과가 업데이트됩니다.
```

Common errors:

- `no_pipeline`: no imported dataset exists.
- `unknown_variable`: selected variable does not exist.
- `invalid_transform`: malformed transform request.
- `output_name_conflict`: output variable already exists.
- `engine_error`: engine rejected the Step despite UI validation.

The UI must show status text near the transform panel and update the global
controller status fields consistently. Prior results become stale after a
successful transform.

## Accessibility And Visual Requirements

- Every input has a visible label and `Accessible.name`.
- Status text is visible near the form and exposed through existing state text.
- Buttons are disabled while `uiController.status === "running"`.
- Keyboard tab order follows: transform kind, variable fields, numeric fields,
  naming fields, method/policy controls, apply button, status.
- The transform panel uses stable dimensions so validation messages do not shift
  tables or results unexpectedly.
- Data and result tables remain flat and high contrast. Glass/blur effects are
  not used behind transform forms, tables, or numeric results.

## Test Plan

### Unit And Service Tests

- Reverse-code command inserts `RecodeReverseStep` with selected variables,
  scale bounds, suffix, and generated outputs.
- Reverse-code command rejects output collisions without changing the pipeline.
- Scale-score command inserts `ComposeScaleStep` with item variables, output
  name, method, and missing policy.
- Scale-score command rejects duplicate items, empty output names, and invalid
  custom `min_valid` without changing the pipeline.
- Metadata command still reuses existing `metadata:<variable_key>` Steps.

### Reproducibility Tests

- A pipeline with import, metadata patch, reverse-code, and scale-score Steps
  round-trips through `Pipeline.to_json` and `Pipeline.from_json` with trusted
  project JSON enabled and recomputes the same output columns.
- Strict JSON still does not emit native `NaN`.
- Untrusted project JSON still rejects file-I/O Steps by default.

### UI/QML Tests

- Work screen contains `데이터 보기`, `변수 보기`, and `변환` tabs.
- Transform panel exposes reverse-code controls and scale-score controls.
- Transform controls call controller methods rather than computing in QML.
- Data view shows the visible source-protection notice.
- Variable view exposes label, measure, missing-code, and value-label metadata
  surfaces.

### Guard Tests

- Existing UI thin-shell import and reduction guards remain green.
- UI network/privacy guards remain green.
- No new UI module imports pandas, numpy, scipy, statsmodels, pingouin,
  factor_analyzer, sklearn, statistics, or math.

## Completion Criteria

The feature is complete only when:

1. Users can apply reverse-code and scale-score transforms from the UI.
2. Users can strengthen basic variable metadata from the UI without touching raw
   values.
3. Every transform is represented by a Step in the pipeline rail.
4. Raw imported columns are never overwritten.
5. Invalid transform requests leave the live pipeline unchanged.
6. Transform output survives pipeline JSON round-trip and recompute.
7. Prior results are visibly stale after transforms until rerun.
8. Focused tests and the full repository gate pass with `PYTHONPATH` forced to
   the release worktree `src`.

## Implementation Order

1. Add focused service tests for reverse-code and scale-score commands.
2. Implement the transform service with collision checks and Step insertion.
3. Add controller methods and QML-callable wrappers.
4. Add reproducibility round-trip tests for transform Steps.
5. Add the `변환` tab and transform panel QML.
6. Strengthen the variable properties panel.
7. Run focused UI tests, transform tests, thin-shell guards, and the release gate.

