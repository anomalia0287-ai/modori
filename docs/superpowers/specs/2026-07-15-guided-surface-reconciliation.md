# Guided-Surface Reconciliation Appendix

Date: 2026-07-15

Status: owner-confirmed on 2026-07-15. It amends the two referenced designs
where they conflict; it changes nothing else in either document.

Referenced documents:

- `2026-07-11-experimental-recommendation-boundary-design.md` (interaction and
  claims contract; restored to the repository on 2026-07-15 after existing only
  in session transcripts, per the same-session commit rule).
- `2026-07-15-cream-nacre-qml-redesign-design.md` (visual and material
  contract).

## Why This Appendix Exists

Both documents are owner-approved and both recompose the same surfaces
(`GuideRail.qml`, `WorkScreen.qml`, `strings.py`, entry screen). They disagree
on four guided-surface decisions. Implementing either one as written would
silently overwrite the other. This appendix fixes precedence before any
implementation session starts.

## Precedence Rule

1. **Interaction model, claims vocabulary, and product-boundary wording**:
   the experimental recommendation boundary design wins.
2. **Visual language, material treatment, layout, spacing, and component
   styling**: the cream nacre redesign wins.
3. Where a single string carries both a visual label and a claim, the claim
   constraint wins and the label is restyled, not reworded, by the redesign.

## Conflict Resolutions

| # | Topic | Cream nacre text | Boundary text | Resolution |
| --- | --- | --- | --- | --- |
| 1 | Guided mode name | `안내 모드` -> `안내 분석` | `안내 모드` -> `실험적 후보 안내` | ModeSegment label is `안내 분석(실험적)`. The full boundary phrase appears once on the entry action description, and the persistent in-surface status label `검증 중인 분석 후보 · 자동 실행 안 함` is retained exactly as the boundary design requires. |
| 2 | Default mode and entry prominence | guided is "the clear primary start" | controller default is `standard`; explicit entry action required | Both hold. The controller default is `standard`; direct data opens and recent-file opens stay in standard mode. The entry screen may still present the guided start action as visually primary, because clicking it is the explicit user action the boundary design requires. Visual prominence is a layout decision; the default mode is a state decision. |
| 3 | Candidate card fields | "title, level, reason, and primary run action" | `수준` -> `검토 상태`; every candidate labeled `실험적 후보`; no trust vocabulary | The card shows title, `검토 상태`, the `실험적 후보` badge, and the deterministic reason. The word `수준` and any level/trust vocabulary do not appear. |
| 4 | Card primary action | "primary run action" | select/prepare/confirm phases; apply-and-run removed | The card's primary action is **Prepare** (`구성 검토로 이동`). It pre-fills the manual form and never mutates the pipeline. The run command exists only inside the manual configuration path after Confirm, exactly as boundary section 7.3 defines. The redesign's "primary run action" is reinterpreted as that post-confirmation manual run button. `applySelectedRecommendation()`, `runPreparedRecommendationNow()`, and `runPreparedRecommendation()` are removed from production use before or during the GuideRail recomposition, never after it. |

## Unified Copy Table

The two documents' copy tables merge as follows; entries not listed here are
unchanged from their source document.

- `안내 모드` -> `안내 분석(실험적)` (segment label; boundary phrasing retained
  in the entry description and persistent status label);
- `표준 모드` -> `직접 분석`;
- `기본 추천` -> `현재 검토 후보`;
- `다른 추천 보기` -> `다른 실험적 후보 보기`;
- `수준` -> `검토 상태`;
- `설명 모드` -> `설명`;
- `가벼운 모드` -> `시각 효과 줄이기`;
- `데이터 창` -> `데이터 넓게 보기`;
- `Word 내보내기` -> `Word로 저장`;
- `왜 이 검정?` -> `이 분석을 선택한 이유`;
- transform labels as specified in the cream nacre transform section.

## Implementation Sequencing

- `GuideRail.qml` and the work-shell command surface are recomposed **once**,
  in a single slice that implements the boundary interaction contract with the
  cream nacre visual language. Two sequential rewrites of the same file would
  spend a full review cycle re-reviewing churn (the installer lane already paid
  this cost once with premature evidence promotion).
- The acceptance spine for that slice is boundary testing contract 10.2-10.4
  plus the cream nacre capture slices for the guided surfaces.
- All other cream nacre surfaces (entry, import dialog, results, transform,
  pipeline, report export) proceed independently of the boundary work, except
  that the entry screen implements resolution #2 above.
- The boundary design's own prerequisite is unchanged: the frozen benchmark
  baseline artifacts must be adopted onto the release lane and their identity
  locked before the vocabulary migration starts.

## Test Reconciliation

- The forbidden-wording scan uses the boundary design's list (`강한 추천`,
  `기본 추천`, `추천 분석 실행`, accuracy percentages, expert-equivalence) and
  extends beyond production QML to report templates, help/library entries, and
  exported Word text.
- Cream nacre running-app capture slices add the boundary VM walkthrough items
  1-3 (standard default, explicit experimental entry, visible experimental
  labeling without auto-run) so one capture set serves both documents.
- Boundary test 10.3's invariant — experimentally assisted and fully manual
  configurations with identical parameters produce identical step params and
  numerical results — is the non-negotiable regression floor for the combined
  GuideRail slice.

## Process Note

The boundary design text existed only in session transcripts until this
appendix was written. It is now committed alongside this appendix. Any future
owner-approved design must be committed in the session that approves it; a
design that is not in the repository cannot participate in conflict detection.
