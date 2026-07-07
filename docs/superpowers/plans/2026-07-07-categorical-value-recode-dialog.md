# Categorical Value Recode Dialog — Design & Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This document is design-first.** The Decision Table below is the primary
> artifact. Do not start implementation until the table's V1/reject/defer
> boundaries are accepted, and do not widen any "rejected" cell during
> implementation — widening is a new plan, not a code change.

**Goal:** Let the user correct categorical values by typing — the missing
"직접 수정" path identified in release QA — while every correction is recorded
as a replayable pipeline step. The user experience is "edit a value table";
the artifact is a `recode.map_values` step, so reproducibility is preserved
and the correction is visible, editable, and revertible in the pipeline rail.

**Why design-first:** Extending value unification casually would create
quality debt in exactly four areas: missing values, numeric types, value
labels, and variable metadata. The prior slice (`UnifyValuesStep`) writes
`value_labels={}, missing_values=[]` into its output — safe for
formatting-variant unification, silently destructive if reused for general
recoding. This plan prevents that by gating scope fail-closed and re-checking
the gate at compute time.

**Relationship to existing work:**

- `recode.unify_values` (shipped): suggestion-driven, formatting variants
  only. Stays as-is.
- This plan: user-driven old→new mapping over a column's value inventory.
  Same engine family, separate step type so pipeline provenance reads
  differently ("표기 통일" vs "값 수정").
- `data.variable_metadata_patch` (shipped): the existing mechanism for
  declaring numeric missing codes and value labels. This plan does not touch
  it and must not duplicate it.

---

## Architectural Facts The Design Relies On

Verified in the current codebase; if any of these change, revisit the table.

1. `Variable.missing_values` is coerced to `list[float]` and
   `Variable.value_labels` to `dict[float, str]`
   (`VariableMetadataPatchStep._coerce_value_labels`, import path). Therefore
   **string-typed columns cannot carry declared missing codes or value labels
   in the current model.** Gating V1 to string columns structurally excludes
   the missing-code and label-remap traps rather than merely avoiding them.
2. Missing codes act at compute time by masking
   (`Dataset.frame_for_compute`), i.e. declared-missing is a metadata
   mechanism, distinct from stored NaN.
3. The pipeline enforces unique writes across steps, so recoding writes a new
   suffixed column; the source column is never mutated.
4. `RecodeReverseStep` remaps numeric value labels arithmetically — the
   existing precedent that label remapping is possible but is real work, not
   a default behavior.

## Decision Table (primary artifact)

| Risk area | V1 does | V1 explicitly rejects (with user-visible reason) | Deferred slice |
|---|---|---|---|
| **결측 missing** | Recode-to-missing as an explicit per-value choice; implemented as real NaN in the output column. Count reported in step notes and dialog preview. | Recoding columns that have declared missing codes (impossible for string columns by fact #1; guard still enforced). Mixing the metadata missing-code mechanism into this dialog. | Numeric recode-to-declared-missing-code interplay (needs the numeric slice first). |
| **숫자 numeric** | Nothing — V1 is string-dtype columns only, so typed input compares as exact string with no coercion ambiguity. | Numeric columns: listed in the dialog but disabled with "숫자 변수는 아직 값 수정을 지원하지 않습니다". Any type-changing target (no coercion paths exist at all in V1). | `recode.map_values` V2: numeric mapping with typed parsing (input parsed against source dtype, type-changing targets rejected), measure re-check. |
| **라벨 labels** | Nothing — impossible on eligible columns by fact #1. | Columns with `value_labels`: disabled with "값 라벨이 있는 변수는 아직 값 수정을 지원하지 않습니다". No silent label drop path exists because such columns cannot enter the dialog. | Label remap slice: unambiguous remap plus collision-resolution UI, following the `RecodeReverseStep` precedent. |
| **메타데이터 metadata** | Output `Variable`: `measure` copied from source, `dtype` from the resulting series, `label` = source label + `" (recoded)"` (English suffix precedent), `origin_step_id` = step id, `value_labels={}`, `missing_values=[]` — **correct, not debt**, because the gate guarantees the source had neither. | Copying labels/missing codes "best effort". Inferring a new measure silently. | Measure re-inference prompt when category count changes materially. |

### Gate definition (both dialog-side and compute-time)

Eligible column := `measure` ∈ {NOMINAL, ORDINAL} AND string dtype
(object/string) AND `value_labels == {}` AND `missing_values == []` AND
unique non-blank values ≤ 200.

- The dialog lists ineligible columns **disabled with the reason**, never
  hidden — refusal must be visible, not mysterious.
- `MapValuesStep.compute` re-verifies the gate and raises on violation
  (defense in depth: a pipeline edited or replayed later must fail loudly,
  not silently degrade).

## Step Semantics — `recode.map_values`

Params:

```json
{
  "column": "지역",
  "mapping": {"남 자": "남자", "여 자": "여자"},
  "to_missing": ["무응답"],
  "suffix": "_수정"
}
```

- Output column `{column}{suffix}`, default suffix `_수정`.
- **Simultaneous one-pass application** on source values: `a→b, b→c` maps
  every `a` to `b` and every `b` to `c`; chains are NOT followed. This is the
  only deterministic reading and must be documented in the dialog help text
  and pinned by a test.
- `mapping` keys and `to_missing` entries must be disjoint; both must be
  non-empty strings; targets must be non-empty strings (recode-to-empty-string
  is rejected — "empty new value" in the dialog means *no change*, and this
  rule prevents accidental blanking).
- Values not mentioned pass through unchanged.
- Merging into an existing category (target equals a value already present)
  is **allowed** — that is legitimate category merging — but the dialog
  preview must say so explicitly: "'남 자' 3건이 기존 '남자' 12건과
  합쳐집니다".
- Step notes: replaced count per rule summary + missing-conversion count,
  e.g. `Recoded 5 values in 지역 (2 rules); 1 value set to missing.`
- Step id `transform:map:{column}`; re-applying replaces the whole mapping
  (insert-or-replace, same as other transforms). The dialog always opens from
  the source column's current value inventory, prefilled from the existing
  step's params when the step exists.

## UI Flow

1. Entry point: "값 수정" action next to eligible variables (variable
   table / transform panel).
2. Dialog: value inventory table from the engine (thin shell: plain dicts) —
   each row = current value, count, editable "새 값" field, "결측으로"
   toggle. Sorted by count desc. Rows the user leaves untouched produce no
   mapping entry.
3. Live preview line per edited row (counts are already known) + total
   summary before apply.
4. Apply → editor validates against the gate and step semantics → step
   inserted → pipeline reruns → rail shows "값 수정: 지역 (2건 규칙)".

## Tests Per Trap (fail-first, one per decision-table row)

- [ ] SAV-imported numeric column with declared missing codes and value
      labels → dialog payload marks it ineligible with the label reason;
      `MapValuesStep.compute` on it raises.
- [ ] Numeric (int/float) column → ineligible with the numeric reason; no
      coercion path reachable.
- [ ] `to_missing` produces real NaN; note counts; downstream descriptives
      treat it as missing.
- [ ] Simultaneous one-pass semantics pinned (`a→b, b→c`).
- [ ] Merge-into-existing-category allowed and counted.
- [ ] Empty-string target rejected; untouched rows produce no rule.
- [ ] Output metadata: measure copied, empty labels/missing, `(recoded)`
      label suffix, dtype preserved.
- [ ] Replay determinism: same params + same source → identical output.
- [ ] Unique-writes conflict on `{column}_수정` surfaced as the standard
      output-name-conflict error.

## Implementation Tasks

- [ ] Task 1 — Engine: value inventory + eligibility payload
      (`modori/value_clustering.py` sibling or new `modori/value_inventory.py`),
      returning eligible/ineligible columns with reasons and per-value counts.
- [ ] Task 2 — Step: `MapValuesStep` in `src/modori/steps/data_prep.py` with
      compute-time gate, registered type, notes discipline.
- [ ] Task 3 — Editor + controller: `DataTransformEditor.map_values` with the
      validation rules above; controller property for the inventory payload +
      apply slot; facade budget respected.
- [ ] Task 4 — QML dialog + strings; string catalog / visual contract /
      dialog-flow guards green.
- [ ] Task 5 — Full default gate; update
      `docs/qa/public-data-format-coverage.md` follow-ups.

## Explicit Non-Goals (V1)

- Numeric recoding (V2 slice, needs typed-parsing design).
- Value-label remapping (own slice, `RecodeReverseStep` precedent).
- Cell-level, row-targeted edits (separate design: stable row identity is an
  unsolved question under row-dropping import options).
- In-place mutation of the source column (architecturally excluded).
- Free-form formulas or conditional recodes.
