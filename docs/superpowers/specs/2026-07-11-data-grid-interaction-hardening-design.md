# Data Grid Interaction Hardening Design

Date: 2026-07-11 KST

Status: approved in owner discussion; written-spec review pending.

## 1. Purpose

The clean-VM walkthrough exposed three product-surface problems:

1. hovering a data cell duplicates its visible value and can display a value from a
   different cell;
2. the virtualized grid can be pulled beyond its top and left bounds, producing a
   rough, detached scrolling effect; and
3. the experimental recommendation boundary repeats the word `experimental` more
   often than needed.

The first problem is a release blocker because it misrepresents user data. The second
is a bounded interaction defect. The third is a wording refinement that must preserve
the unvalidated-recommendation disclosure.

## 2. Scope And Invariants

This pass may change only grid interaction, recommendation-surface wording, tests,
and QA documentation. It must not change:

- imported data or display-role values;
- statistical formulas, result DTOs, tolerances, or report numbers;
- recommendation candidates, ordering rules, evidence status, or routing policy;
- the explicit select, prepare, confirm, and manual-run boundary;
- report selection provenance or its disclosure.

The standard mode remains the process default. Recommendation selection remains
experimental and never runs an analysis automatically.

## 3. Cell Hover Contract

Short values that fit inside a cell receive no tooltip. Repeating an already visible
number adds no information and creates visual noise.

A tooltip may appear only when the rendered cell label is truncated. It must be an
instance owned by that delegate rather than the shared attached `ToolTip` mechanism.
Its text binds to the same delegate-local display value used by the visible label.
Virtualized delegate pooling or reuse must not allow another row or column to supply
the tooltip text.

Tests must cover:

- no tooltip for a short value;
- the exact full value for a truncated cell;
- movement between cells with distinct values;
- delegate reuse after scrolling, with tooltip text still matching the hovered cell.

## 4. Scrolling Contract

The grid body and synchronized horizontal and vertical headers stop at their content
bounds. Dragging or flicking at the origin must not move content above the first row or
left of the first column. The table remains clipped to its viewport.

Normal rightward and downward scrolling, scrollbars, keyboard navigation, fixed cell
dimensions, and header synchronization remain unchanged. No inertial-tuning claim is
made beyond removing overshoot and detached content movement.

Tests must inspect the real QML objects and exercise pointer drag at the origin. They
must also verify that a larger model can still reach later rows and columns.

## 5. Recommendation Wording Contract

Use `분석 후보 안내` as the entry, mode, and panel title vocabulary. Do not use
`분석 자동 추천`: the product neither chooses and runs an analysis automatically nor
has evidence for validated recommendation quality.

The panel keeps one compact persistent status:

```text
실험적 · 자동 실행 안 함
```

The deterministic-order disclaimer remains visible. Candidate-list headings and
individual candidate labels do not repeat `실험적` when the persistent status already
provides that context. Accessibility names must preserve the same experimental status
without repeating it on every unrelated control.

A one-time-only warning is rejected because later screenshots, re-entry, and partial
views would lose the evidence boundary.

## 6. Verification

Implementation follows test-first order:

1. add runtime regressions and observe the current tooltip and bounds behavior fail;
2. replace shared tooltip ownership and restrict display to truncated values;
3. stop overshoot on body and synchronized headers;
4. update wording and contract tests;
5. run focused QML tests, the complete UI suite, product-wording scan, and the full
   quality/package/slow-statistics gate;
6. rebuild the payload from the exact worktree and repeat the clean-VM walkthrough.

Host visual evidence must include a compact grid, an overflow grid at its origin and
scrolled position, and the recommendation panel header. The owner VM walkthrough is
the final interaction gate.

## 7. Acceptance Criteria

- Hovering an ordinary numeric cell shows no duplicate value.
- A tooltip for a genuinely truncated value always matches that cell.
- Top and left overshoot cannot expose detached or blank grid space.
- Right and bottom navigation remain functional and synchronized with headers.
- The primary product label is `분석 후보 안내`.
- Exactly one persistent panel-level experimental status remains visible.
- No automatic recommendation execution or recommendation-quality claim is added.
- Full host gates pass and the corrected behavior is confirmed on the clean VM.
