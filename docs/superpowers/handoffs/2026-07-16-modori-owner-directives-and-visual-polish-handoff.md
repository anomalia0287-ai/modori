# Modori Owner Directives And Visual Polish Handoff

Date: 2026-07-16

Workspace: `C:\Users\V\Desktop\TongTong`

Branch: `release/readiness-1-9`

Owner-provided starting anchor: `ab3b9b966f7880298235fa582e9370adbd9c1bb5`

HEAD at handoff: `53e358e7bee534396579a46ebb24b7b0dcbd773a`

Status: implementation intentionally paused; visual changes are uncommitted and still require owner review.

## 0. 한국어 인수인계 요약

이 문서는 이번 디자인 작업의 최종 기준 문서다. 구현은 사용자의 실제 화면
승인 전 상태에서 멈춰 있으며, 현재 변경분을 초기화하거나 임의로 커밋하면 안
된다. 앞선 지시와 뒤의 지시가 충돌할 때에는 이 문서의 `4. Superseded
Decisions`에 적힌 최종안을 따른다. 전체 지시 흐름은 `14. Owner Directive
Ledger`에 시간순으로 남겼다.

다음 작업자가 가장 먼저 해결할 사항은 다음과 같다.

1. 마지막 화면에서 누락된 직접 분석 선택지 전체를 같은 반복 목록 체계로
   정리한다. 한두 버튼만 고치는 작업이 아니다.
2. 데이터 가져오기 창의 네 개 세로 스크롤바 높이 결함을 수정하고 실제 손잡이
   이동을 런타임 테스트와 실화면으로 확인한다.
3. 모드 이름을 `CASUAL MODE`와 `PRO MODE`로 통일하고, 크기·글자 위계를
   동일하게 유지한 채 선택/호버/키보드 포커스를 하단 브론즈 선으로 표현한다.
4. 진입 화면 문구와 좌측 오로라 범위를 최종 지시대로 고친다.
5. 데이터 셀 호버 툴팁을 제거하고 미세한 배경 변화만 남긴다.
6. 헤더 간격, 하단 `실행` 글래스 버튼, `로딩 중`, 절제된 화면 전환을 한 번의
   일관된 패스로 완성한다.
7. 전체 유사 목록을 선제적으로 감사한 뒤 실제 소스 앱을 띄워 사용자가 직접
   확인할 수 있게 둔다.

이미지 생성 목업이나 오래된 패키지 실행 화면은 검수 증거가 아니다. 테스트가
통과해도 시각적 완료를 주장할 수 없으며, 실제 Modori 화면에 대한 사용자 승인이
완료 조건이다.

## 1. Authority And How To Use This Handoff

This is the canonical handoff for the 2026-07-15 through 2026-07-16 Modori
visual-polish session. It records the owner's directives, later overrides,
current implementation state, known failures, verified technical findings, and
the acceptance procedure for the next worker.

When this document conflicts with an earlier visual proposal, use the latest
owner decision recorded here. Do not silently revive an earlier direction.
Before changing code, also read:

- `docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md`
- `docs/superpowers/specs/2026-07-15-guided-surface-reconciliation.md`
- `docs/superpowers/specs/2026-07-16-aurora-glass-brand-header-design.md`
- `docs/superpowers/plans/2026-07-16-full-bleed-bronze-reconciliation-implementation.md`
- `docs/POLICY.md`

The owner reviews the real application after every visual pass. Automated tests
are necessary but do not constitute visual acceptance. Do not substitute an
image-generated mockup, a disconnected HTML approximation, or a packaged build
that does not contain the current source changes.

## 2. Trust Failure To Avoid Repeating

The latest pass applied a glass-row treatment to one recommendation repeater but
left the adjacent manual-analysis choices as loose, poorly separated controls.
The owner then had to identify the same class of defect again in a screenshot.
This was not merely a missed button; it showed that the implementation followed
one literal example without auditing equivalent surfaces.

The correction is a process requirement:

- whenever the owner says “other similar items,” inventory every component with
  the same semantic role;
- inspect default, hover, focus, selected, disabled, long-text, and scrolled
  states, not only the state shown in the example;
- inspect the complete screen at the real window size after a local change;
- do not make the owner enumerate every repeated defect.

The most recent omission is visible in
`C:\Users\V\AppData\Local\Temp\codex-clipboard-1375dea1-dbb9-4c7d-b95e-4027ce065b84.png`.
The manual-analysis list in `GuideRail.qml` is therefore an explicit P0 item.

## 3. Non-Negotiable Product And Design Principles

- This is a design and convenience improvement of the real Modori desktop tool.
- Overall harmony outranks preserving the earlier porcelain treatment.
- Aurora glass is a brand surface, not a decorative effect to spread through
  every data and form surface.
- The desired atmosphere is restrained mother-of-pearl: cool glass, a few warm
  drops, smooth color mixing, and no obvious rainbow bands.
- Meaningful light is allowed only when it communicates state. If nacre and
  semantic glow compete, remove the glow or nacre rather than forcing both.
- The application must remain credible as a statistical desktop tool. Avoid
  marketing-page scale, oversized text, elderly-mode sizing, thick controls,
  cards inside cards, and persistent four-sided outlines.
- Every word and control label must be reviewed for usability, not only visual
  fit.
- Replace unnecessary binary checkboxes with toggles when the choice represents
  an ongoing mode or preference. A required confirmation may remain a checkbox.
- Checkbox corners are moderately rounded: “Galaxy-like,” not pill-like or
  iPhone-like. The current theme radius of `4` is the intended range.
- Retain a gear icon as a future Settings entry point on both entry and work
  surfaces.
- Preserve local-first behavior, source-data immutability, replayable
  transformations, and the Python/QML architecture. Visual work must not move
  statistics into QML or add cloud, telemetry, or remote-asset dependencies.
- Do not put GPT, Codex, or other model branding in the product UI. Contribution
  credit is a separate project-governance matter; it is not a visual-branding
  requirement for these screens.
- Network design research was encouraged, but references never override the
  owner's real-screen judgment or the local product constraints.

## 4. Superseded Decisions

The following later decisions replace earlier ones:

| Earlier direction | Final direction to implement |
| --- | --- |
| Porcelain as the visual base | Porcelain may be removed; harmony and toned white are primary. |
| Heavy cream | Use a near-white warm canvas; distinguish a slightly darker warm surface. |
| Pure-white scrollbar rail/thumb | Use visibly contrasting neutral/bronze-gray rail and thumb without a separate outline. |
| Parisienne bronze `Modori` wordmark | Black uppercase Gothic/sans-serif `MODORI`, expanded letter spacing. |
| Tiffany blue as a flat full header | Use smooth aurora glass. Tiffany is at most an isolated secondary bloom and may be removed if muddy. |
| Green/teal action language | Replace with bronze/warm-neutral interaction roles. Do not reintroduce green. |
| Korean `안내 분석` / `직접 분석` mode labels | Use `CASUAL MODE` / `PRO MODE` consistently where mode selection is shown. |
| Solid selected mode button | Both modes share the same pale-rose base and dimensions; selection and hover use a one-edge bronze underline. |
| White bottom-right run button | Use a stronger glass treatment that remains legible and belongs to the footer. |
| Tooltip on every hovered data cell | Remove it; use only a subtle hover background change. |

## 5. Final Visual Tokens And Material Rules

### 5.1 Palette

- Base canvas: `#FEFDFC`. This is intentionally a few drops warmer/darker than
  pure `#FFFFFF`.
- Common darker surface: `#FAF8F5`. This is the approved approximately
  30-percent stronger contrast step from the earlier near-identical surface.
- Selected/emphasis edge: `#B9856E`.
- Thin warm separator: `#D7B9AA`.
- Bronze action: `#8D5B48`.
- Bronze hover: `#7B4F3F`.
- Bronze deep/pressed: `#684437`.
- Wordmark: near-black/black, not bronze.

The darker surface and base canvas must be visibly distinguishable on the real
monitor without producing a beige or heavy-cream application. If separation is
still weak, adjust only the darker role first; do not darken every surface.

### 5.2 Aurora Glass

- Use a cool blue-gray foundation with overlapping ice-blue, pale-lilac,
  restrained rose, and optional Tiffany blooms.
- Gradients must overlap with long falloffs. Do not fade colored stops into
  transparent black; use hue-preserving transparent endpoints.
- There must be no visible vertical band boundary or abrupt seam.
- Keep the field static. No drifting aurora, shimmer, pulse, particles, or
  gratuitous glow.
- A restrained white veil and one quiet edge anchor are sufficient for glass.
- Reduced-effects mode must retain a readable static neutral gradient.
- Approved placement is the work header, the entry screen's left brand region,
  and the full-width bottom rail treatment. Keep aurora out of data cells,
  result content, settings forms, and import content.

### 5.3 Borders, Separators, And Radius

- Do not outline every container. Persistent four-side bronze frames made the
  UI look old and complex.
- Use surface contrast and spacing for primary grouping.
- Use a single bottom edge for hover, focus, and selected emphasis where
  practical.
- Use `#D7B9AA` for quiet separators, including repeated-list rows, only when it
  improves recognition.
- Data-grid lines may remain warm during the next review. If readability is
  weak, move grid lines to neutral gray/charcoal; do not preserve the warm line
  merely because it was once specified.
- Modal and panel corner treatment must be consistent on all four corners.
- Avoid excessive pill shapes. Moderate radii are preferred.

### 5.4 Scrollbars

- Rails and handles need enough contrast to be found immediately.
- Do not draw a separate four-side outline around rail or handle.
- The thumb must look integrated, move smoothly, and never overlap adjacent
  panels or appear to float outside its viewport.
- Verify both vertical and horizontal bars at start, middle, and end positions.

## 6. Screen-By-Screen Acceptance Contract

### 6.1 Entry Screen

- Use the approved “option 1” full-bleed split. The viewport is the composition;
  do not place a separate large card in the middle of an otherwise empty page.
- The left brand region is full height and owns its own aurora field. Size the
  `AuroraGlassSurface` to the actual brand-region width rather than letting a
  right-side opaque layer mask most of a full-window gradient. The current
  masking leaves mostly the first blue segment visible and weakens the intended
  lilac/rose mix.
- The left main line must be exactly:

  ```text
  통계 작업을 위한 선택,
  모도리에 오신 것을 환영합니다.
  ```

- The line break occurs immediately after the comma.
- The old sentence `데이터를 이 컴퓨터 안에서 분석하고, 선택 근거를 함께
  확인합니다.` is removed.
- The bottom privacy and provenance lines may remain:
  `데이터는 이 컴퓨터를 떠나지 않습니다` and `무료 · 오픈소스 · 로컬`.
- `MODORI` is black, uppercase, Gothic/sans-serif, and letter-spaced.
- The right task region stays calm, near-white, and free of a nested bright card.
- Entry mode labels are `CASUAL MODE` and `PRO MODE`.
- Both mode actions have identical dimensions, type size, weight, and pale-rose
  base. Neither mode is visually declared more important.
- The current mode keeps a bronze underline. The other mode receives the same
  underline on hover. Keyboard focus remains unmistakable and should use the
  same one-edge language rather than a permanent box.
- Preserve plain-language descriptions and the experimental disclosure. The
  English mode name must not erase `검증 중인 분석 후보 · 자동 실행 안 함`
  semantics.
- Recent files are individual rows with a thin separator or restrained glass
  division. Long names remain middle-elided. A tooltip is acceptable only for a
  truncated file name, not as a general hover effect.
- Keep the Settings gear available.

### 6.2 Work Header

- Keep the currently approved aurora-glass character but remove any visible
  color seam. The owner described the header as beautiful; the task is
  refinement, not replacement with a flat color.
- `MODORI` stays black, uppercase, Gothic/sans-serif, and letter-spaced.
- Increase the wordmark-to-first-command gap from the current token value `28`
  to approximately `40`, then inspect at the real window width.
- Command-to-command spacing stays compact and even.
- Header controls must not regain four-side passive outlines.
- Mode controls read `CASUAL MODE` and `PRO MODE`, share equal visual hierarchy,
  and use underline interaction as described above.
- The gear remains at the far-right settings entry point.
- Do not use green/teal for current mode, primary command, focus, or selection.

### 6.3 Guide Rail And Analysis Choices

- Preserve the recommendation boundary and status language. A candidate is not
  automatically executed merely because it is visually prominent.
- The current reviewed candidate may remain a stronger summary surface, but the
  action must remain bronze, not teal.
- `다른 실험적 후보 보기`, its expanded candidates, and `직접 선택` must read
  as one coherent list system with clear row boundaries.
- Every repeated candidate row needs an obvious default/hover/focus/selected
  distinction using surface shift plus a thin divider or restrained glass row.
- Audit the manual-analysis choices as part of the same system. The following
  are explicitly in scope:

  - `기술통계 표`
  - `척도 신뢰도`
  - `빈도/교차표`
  - `상관관계`
  - `요인/PCA`
  - `두 집단 평균 차이`
  - `세 집단 이상 평균 차이`
  - `순위 기반 세 집단 비교`
  - `공변량 보정 집단 비교`
  - `여러 변수로 예측`

- Do not leave these as floating text buttons in a loose `Flow`. Do not solve
  the selected item with a large filled block while leaving other items
  borderless and ambiguous. Use equal row/chip geometry and a consistent
  one-edge or glass-row selection language.
- Audit any other repeated keyword/option list with the same semantics across
  the product. Do not add dividers to unrelated form fields merely to satisfy a
  global search-and-replace.

### 6.4 Data Grid

- Remove the tiny value popup/`ToolTip` that repeats the cell contents on every
  hover.
- Hover changes only the cell background subtly.
- Current/selected state takes precedence over hover.
- Grid rows and columns must remain aligned while scrolling. No cell or panel
  may appear to rise above, overlap, or clip through neighboring surfaces.
- Keep the status line and scroll rails inside the data region.
- Inspect warm grid lines for readability; neutralize them if necessary.

### 6.5 Import Dialog

- The whole dialog must use consistent corner rounding. Do not leave square top
  corners and rounded bottom corners.
- Avoid decorative frames around every internal area.
- Column-selection checkboxes may remain checkboxes because each row is a
  discrete include/exclude selection. Their radius remains moderate.
- The vertical scrollbar must visibly track content position in every scroll
  area. This is a functional defect, not a color-only problem.
- Hovering a data preview does not open redundant value windows.
- Keep import actions bronze and ensure search, include-all, cancel, and import
  states remain readable.
- Reproduce with `tests/fixtures/psych_bfi.csv` and verify dragging, wheel
  scrolling, page movement, and start/middle/end thumb positions.

### 6.6 Results Panel

- Keep one visual plane. Do not place a near-white result card on top of a
  slightly darker result card unless the content requires a real nested region.
- Retain purposeful table/chart frames but remove decorative nesting.
- Empty, waiting, running, ready, stale, and error states remain clearly
  distinct.
- `Word로 저장` and result-detail actions use the bronze interaction language.

### 6.7 Bottom Rail And Run Action

- The bottom rail runs from the left edge to the right edge of the work screen;
  it must not look like an inset floating card.
- Use a stronger glass field or a quiet dark-neutral field. The current approved
  direction is stronger glass first.
- The bottom-right `실행` action must not be a plain white secondary button.
  Give it a compact, high-contrast glass treatment integrated with the rail.
- Preserve disabled and running states and keyboard focus.

### 6.8 Loading And Screen Changes

- Real delay or processing shows the exact text `로딩 중`.
- Add a restrained busy indicator only if it remains visually clean.
- Analysis can bind to `uiController.status === "running"`.
- Synchronous file preview/open/import paths may need a main-level busy wrapper
  scheduled one event-loop frame before blocking work so the overlay can paint.
  Do not add a fake long delay.
- Use a restrained opacity crossfade around 160 ms for entry/work changes.
  Avoid slide, bounce, pulse, scale, or cinematic transitions.
- Reduced-effects mode disables or minimizes the transition.

### 6.9 Splash / Initial Loading Screen

- Remove the old-version visual vibe and align it with the current identity.
- Reuse the black uppercase, letter-spaced `MODORI` wordmark.
- Keep it calm and brief; do not turn it into a marketing hero or animated
  aurora showcase.

## 7. Verified Import Scrollbar Root Cause

The broken import-dialog scrollbar was reproduced in the real Modori dialog
using `tests/fixtures/psych_bfi.csv`.

Observed behavior:

- content position changed and the list actually scrolled;
- the visible thumb remained near the top;
- the attached `AppScrollBar` geometry was approximately
  `(x=398, y=0, width=12, height=28)` inside a view roughly 300 px tall;
- the scrollbar kept its 28 px implicit minimum height instead of filling the
  viewport, so `size` and `visualPosition` had no usable vertical travel.

A probe that bound the attached instance to the parent height produced a 300 px
bar and a thumb that moved to approximately `y=272` at the end of the list.

Required correction:

- fix all four `ScrollBar.vertical: AppScrollBar {}` instances in
  `ImportDialog.qml`, not just the first screenshot location;
- bind the bar's vertical length to its parent/viewport height and keep it on
  the trailing edge;
- do not globally change the shared component in a way that breaks the
  `DataGridView` bars, because those are explicitly reparented to rail items and
  anchored to fill;
- add a runtime regression proving bar height matches the view height and the
  thumb/`visualPosition` changes when content position changes;
- verify actual dragging in the real dialog after the test passes.

This defect will not be fixed by recoloring the thumb.

## 8. Current Implementation Snapshot

The worktree contains a substantial uncommitted design pass. Preserve it. Do not
reset, clean, or overwrite unrelated files.

Already present in the current source, but still awaiting final visual approval:

- near-white canvas and the stronger `#FAF8F5` common surface;
- bronze shared-control roles and removal of most teal/green action use;
- `#B9856E` emphasis and `#D7B9AA` thin-separator roles;
- shared `AuroraGlassSurface.qml`;
- full-bleed entry split foundation;
- aurora work header;
- black uppercase letter-spaced `MODORI` wordmark;
- flattened result surface;
- full-width bottom rail foundation;
- glass-row treatment for one experimental-candidate repeater;
- moderate checkbox radius;
- revised scrollbar appearance;
- updated splash identity foundation.

Known incomplete or wrong items at handoff:

1. `GuideRail.qml` manual-analysis choices still use `primary`/`quiet` variants
   in a loose flow and were not included in the list-separation pass.
2. Mode labels and behavior have not been converted to the final
   `CASUAL MODE` / `PRO MODE` equal-underlined design.
3. The entry tagline is still the old text.
4. The entry aurora is masked by the right surface and does not show the full
   intended mix in the left region.
5. The wordmark-to-command gap remains `28`; target review value is about `40`.
6. `DataGridView.qml` still contains the redundant per-cell tooltip.
7. All four attached import scrollbars still lack full viewport height.
8. `LoadingOverlay.qml` still says `계산 중`, not `로딩 중`, and lacks the
   final busy treatment.
9. Entry/work screen changes are still immediate visibility changes.
10. `PipelineRail.qml` still gives the run action a plain `secondary` variant.
11. Similar repeated option/list surfaces have not yet been fully inventoried.

Historical verification checkpoint before these remaining changes:

- full UI suite: `419 passed in 35.49s`;
- `tests/test_launch_smoke_script.py`: `1 passed`;
- `scripts/launch_smoke.py`: `launch-smoke-ok`;
- Ruff on touched tests: `All checks passed`;
- `git diff --check`: clean.

These are historical checkpoints only. They are not evidence for future edits.

## 9. Git And Worktree Safety

At handoff, the branch is 61 commits ahead of its remote and the worktree is
dirty by design. The visual work has not been committed because the owner has
not accepted the final screen.

Recent committed visual anchors are:

- `4f7a87d style: establish ivory Tiffany palette`
- `b5aa7f4 style: add Parisienne Modori wordmark` — superseded by the current
  uncommitted black uppercase wordmark direction;
- `145ba6e style: apply Tiffany header and white scrollbars` — superseded in
  part by the current aurora header and visible neutral scrollbar direction;
- `691eb88 docs: define aurora glass brand surfaces`
- `53e358e docs: define full-bleed bronze reconciliation`

Tracked modified areas include the theme, shared controls, entry/work/splash
screens, import/results/settings dialogs, and UI tests. Important untracked
items include:

- `src/modori/ui/qml/components/AuroraGlassSurface.qml`
- `tests/ui/test_full_bleed_bronze_reconciliation.py`
- the 2026-07-16 design/implementation documents under
  `docs/superpowers/specs` and `docs/superpowers/plans`
- `docs/design-audit/2026-07-15-aurora-glass-readiness/`

Rules:

- do not use `git reset --hard`, `git checkout --`, or `git clean`;
- do not delete or rewrite the design-audit directory;
- inspect overlapping diffs before editing;
- do not commit the implementation until the owner inspects the real window;
- if a documentation-only commit is desired, isolate it explicitly rather than
  sweeping all dirty files into the commit.

Exact dirty-path inventory at handoff, before adding this document:

```text
M docs/superpowers/specs/2026-07-16-aurora-glass-brand-header-design.md
M src/modori/ui/qml/components/AppButton.qml
M src/modori/ui/qml/components/AppCheckBox.qml
M src/modori/ui/qml/components/AppComboBox.qml
M src/modori/ui/qml/components/AppGroupBox.qml
M src/modori/ui/qml/components/AppIconButton.qml
M src/modori/ui/qml/components/AppRadioButton.qml
M src/modori/ui/qml/components/AppScrollBar.qml
M src/modori/ui/qml/components/AppSpinBox.qml
M src/modori/ui/qml/components/AppTextField.qml
M src/modori/ui/qml/components/BrandWordmark.qml
M src/modori/ui/qml/components/DataGridView.qml
M src/modori/ui/qml/components/ExplainPopover.qml
M src/modori/ui/qml/components/GuideRail.qml
M src/modori/ui/qml/components/ModeSegment.qml
M src/modori/ui/qml/components/PearlSurface.qml
M src/modori/ui/qml/components/PipelineRail.qml
M src/modori/ui/qml/components/PreferenceSwitch.qml
M src/modori/ui/qml/components/ResultsPanel.qml
M src/modori/ui/qml/components/StateBadge.qml
M src/modori/ui/qml/dialogs/ImportDialog.qml
M src/modori/ui/qml/dialogs/ReportExportDialog.qml
M src/modori/ui/qml/dialogs/ResultDetailDialog.qml
M src/modori/ui/qml/dialogs/SettingsDialog.qml
M src/modori/ui/qml/screens/EntryScreen.qml
M src/modori/ui/qml/screens/SplashScreen.qml
M src/modori/ui/qml/screens/WorkScreen.qml
M src/modori/ui/qml/theme/Theme.qml
M tests/ui/test_compact_control_system.py
M tests/ui/test_cream_nacre_visual_system.py
M tests/ui/test_data_grid_qml.py
M tests/ui/test_import_dialog_flow.py
M tests/ui/test_ivory_tiffany_brand_system.py
M tests/ui/test_mode_action_surfaces.py
M tests/ui/test_qml_runtime_load.py
M tests/ui/test_qml_visual_contract.py
M tests/ui/test_result_surface_qml.py
?? docs/design-audit/2026-07-15-aurora-glass-readiness/
?? docs/superpowers/plans/2026-07-16-aurora-glass-brand-header-implementation.md
?? docs/superpowers/plans/2026-07-16-full-bleed-bronze-reconciliation-implementation.md
?? docs/superpowers/plans/2026-07-16-quiet-boundary-tiffany-header-implementation.md
?? docs/superpowers/specs/2026-07-16-quiet-boundary-tiffany-header-design.md
?? src/modori/ui/qml/components/AuroraGlassSurface.qml
?? tests/ui/test_full_bleed_bronze_reconciliation.py
```

## 10. Primary File Map

| Concern | Primary files |
| --- | --- |
| Palette, spacing, radii, motion | `src/modori/ui/qml/theme/Theme.qml` |
| Aurora material | `src/modori/ui/qml/components/AuroraGlassSurface.qml` |
| Wordmark | `src/modori/ui/qml/components/BrandWordmark.qml` |
| Shared button/list variants | `src/modori/ui/qml/components/AppButton.qml` |
| Mode selector | `src/modori/ui/qml/components/ModeSegment.qml` |
| Guide/manual-analysis lists | `src/modori/ui/qml/components/GuideRail.qml` |
| Grid hover and scroll | `src/modori/ui/qml/components/DataGridView.qml` |
| Scrollbar material/geometry | `src/modori/ui/qml/components/AppScrollBar.qml` |
| Bottom rail/run action | `src/modori/ui/qml/components/PipelineRail.qml` |
| Result plane | `src/modori/ui/qml/components/ResultsPanel.qml` |
| Loading overlay | `src/modori/ui/qml/components/LoadingOverlay.qml` |
| Import modal and four bars | `src/modori/ui/qml/dialogs/ImportDialog.qml` |
| Entry composition and recent files | `src/modori/ui/qml/screens/EntryScreen.qml` |
| Header and layout | `src/modori/ui/qml/screens/WorkScreen.qml` |
| Splash | `src/modori/ui/qml/screens/SplashScreen.qml` |
| Screen visibility/transitions | `src/modori/ui/qml/Main.qml` |
| Korean microcopy source | `src/modori/ui/strings.py` and QML literals |
| Static/runtime contracts | `tests/ui/` |

## 11. Required Execution Order

Do not start by tuning colors. Use this order so the owner sees one coherent
pass rather than another isolated patch:

1. Write or update focused regressions for the import scrollbar geometry,
   data-cell tooltip removal, mode labels/equal underline behavior, entry text,
   manual-analysis list separation, run-button material, and loading text.
2. Fix all four import-dialog scrollbars and verify the thumb in the real dialog.
3. Build one reusable repeated-row/choice language and apply it to every
   semantically equivalent list, including the manual-analysis options.
4. Implement `CASUAL MODE` / `PRO MODE` consistently on entry and work screens.
5. Correct the entry tagline and constrain the aurora field to the left region.
6. Remove data-cell tooltips and add subtle hover-only color shift.
7. Increase header wordmark gap and refine the footer run button.
8. Add `로딩 중` and the restrained reduced-effects-aware crossfade.
9. Audit every changed screen at the real viewport for edge alignment, text
   clipping, hover/focus/selected states, and unexpected green.
10. Run the full verification gate, launch the actual source application, and
    leave it open in the state most useful for owner review.

## 12. Verification And Real-Screen Review

Set the source path explicitly from the workspace:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
```

Minimum focused tests should include the changed contracts under `tests/ui`,
especially:

- `test_mode_action_surfaces.py`
- `test_import_dialog_flow.py`
- `test_data_grid_qml.py`
- `test_ivory_tiffany_brand_system.py`
- `test_qml_runtime_load.py`
- `test_qml_visual_contract.py`
- `test_full_bleed_bronze_reconciliation.py`

Then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q tests\test_launch_smoke_script.py -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\launch_smoke.py
.\.venv\Scripts\python.exe -m ruff check tests\ui
git diff --check
```

Launch the actual current source, not a stale package:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
.\.venv\Scripts\python.exe -m modori.app
```

`C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe` is the packaged location,
but it does not contain uncommitted QML changes unless the package is rebuilt.
Do not use it to claim the current source design was shown.

Real-screen acceptance states:

- entry screen at the normal full window size;
- entry mode hover, selected, and keyboard-focus states;
- recent files with short and long names;
- work header in both modes;
- collapsed and expanded recommendation alternatives;
- every manual-analysis option, including selected and hovered long labels;
- data grid scrolled vertically and horizontally;
- import dialog with `psych_bfi.csv`, bar at start/middle/end, and a dragged thumb;
- bottom rail with run enabled, disabled, and loading;
- result panel empty, running, ready, and error/stale where practical;
- reduced-effects mode.

The owner performs final visual acceptance. Leave Modori open after verification.

## 13. Definition Of Done

This pass is not done until all of the following are true:

- no semantically equivalent repeated-list surface is left in the older loose
  style;
- manual-analysis choices are clearly separated and consistent;
- `CASUAL MODE` and `PRO MODE` are equal-size pale-rose actions with correct
  selected/hover/focus underline behavior;
- entry copy and aurora composition match the final direction;
- import scroll thumb visibly moves and is covered by a runtime regression;
- data cells no longer open redundant tooltips;
- header spacing, footer run action, and loading treatment are visually coherent;
- no green/teal action accent has returned;
- automated tests and launch smoke pass from the current tree;
- the actual source application has been inspected at the target size;
- the owner has reviewed the real screen and accepted the pass.

## 14. Owner Directive Ledger

This ledger preserves the evolution of the request so a future worker does not
lose intent by reading only the last screenshot.

1. Begin a design/convenience pass on `release/readiness-1-9`; use the real tool
   or local launch for inspection. Apply aurora glass, replace unnecessary
   checkboxes with toggles, and scrutinize even single words for usability.
2. Porcelain is optional; overall harmony matters more.
3. Move to a cream/toned-white family and reduce obvious aurora saturation;
   imagine subtle mother-of-pearl.
4. Stop producing disconnected image mocks. Every visual shown must be a real,
   connectable implementation in Modori.
5. Participation and contribution may be credited like human work, but the
   product UI is not a place for GPT/Codex branding.
6. Meaningful glow is acceptable. Design references may be researched online.
7. Reserve a gear-icon entry point for future Settings. Consult the July 11
   experimental-boundary and July 15 guided-surface documents.
8. Make the actual execution location clear and allow the owner to inspect the
   app directly.
9. Replace the oversized click-choice treatment between guided and direct modes
   with a genuine compact mode control. Avoid thick text and oversized controls.
10. Keep checkbox rounding moderate, closer to Galaxy than iPhone.
11. If cream becomes difficult, lower it substantially or use toned white.
12. Fix grid/panel overlap and the sense that content lifts or protrudes while
    scrolling. Modernize the scrollbar and update the initial loading screen.
13. A non-overlapping position is not sufficient if motion still looks stiff or
    unnatural; scrolling must feel visually smooth.
14. Establish a near-white main field, a distinguishable darker warm surface,
    Tiffany/aurora header direction, and rose-bronze separators. Initial
    Parisienne-logo direction was later superseded.
15. Fix `#B9856E` for logo/emphasis boundaries and `#D7B9AA` for thin
    separators; the later wordmark decision moved the logo itself to black.
16. Remove nacre or semantic light if their coexistence is forced. Warm data-grid
    lines are provisional and may become neutral for readability.
17. Reduce border proliferation. Use simple selected edges instead of outlining
    four sides. Make scrollbars visible without outlines. Keep modal corner
    rounding consistent. Refine header spacing and type toward a Tiffany & Co.
    level of restraint.
18. Change the wordmark to black uppercase Gothic/sans-serif with wide tracking;
    give it generous space from commands. Strengthen the aurora glass over the
    earlier flat Tiffany header.
19. If Tiffany mixes poorly, drop it and prioritize the aurora-glass result.
20. Place the shared aurora treatment in the work header and the entry left brand
    region; inspect the real result rather than approving from prose.
21. Use a full-bleed entry composition, smooth gradient blending, bronze instead
    of green, a flat result plane, stronger contrast for common darker surfaces,
    clearer repeated-list rows, and a full-width bottom treatment.
22. Confirm “option 1” for the full-bleed entry. Increase the darker common
    surface contrast by about 30 percent.
23. Add separators between recent-file/keyword rows and every similar list.
24. Rename modes to `CASUAL MODE` and `PRO MODE`, equalize their size and
    hierarchy, use a pale-rose base, and show selection/hover with a lower bar.
25. Replace the entry message with
    `통계 작업을 위한 선택,\n모도리에 오신 것을 환영합니다.` and give the left
    side an aurora strength comparable to the header.
26. Fix the import scrollbar that appears not to move.
27. Replace data-cell hover popups with a subtle background shift.
28. Increase wordmark/option spacing, give the bottom-right run action stronger
    glass, show `로딩 중` during real waits, and use only restrained screen-change
    motion.
29. The final screenshot showed that manual-analysis choices and similar
    surfaces were still not audited. The next worker must fix the whole semantic
    family, not wait for another owner annotation.
30. Preserve all directions in documentation and leave a complete handoff before
    any change of implementer.

## 15. Screenshot Reference Registry

These owner-provided files are temporary local references. They may disappear
after a system cleanup, so this document also describes every required outcome
in text.

### Initial layout, control, and scroll criticism

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-ffc4675c-bdde-4593-939f-a24e73e50607.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-0ecd21a9-5456-4ba1-b7a6-5a69453b9e76.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-2c5e067a-e94f-40f3-8c2c-3697a3f77216.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-c56b091c-6d4c-4cad-8e7e-b6e828729762.png`

### Palette references

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-6c110a86-ef87-4894-be64-4176ccb0759d.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-dac55890-0250-457e-86a2-261e3818fe2b.png`

### Border, modal, scrollbar, and header criticism

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-6e4401ff-08b8-4f97-a6ca-ebe91c705198.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-79f9261e-cb84-469b-aa9e-59a3ea2323da.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-9474bf4b-6ebe-4313-a25e-ec624c7e9d8c.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-4d9aa872-245b-4272-ab6d-6571405e8524.png`

### Aurora and wordmark direction

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-37e10d37-b7d0-41b6-913c-d4a2d8d9494e.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-8c91d43f-b6ad-47a5-a65d-322162903d93.png`

### Full-bleed, bronze, results, list, and footer direction

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-71c07cee-f829-4ee3-aa87-0700ba657126.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-644c0b31-3aa6-4b01-ab58-b52738cebd3b.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-443ce470-f001-424f-98c2-d436843e9921.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-da50a664-c6c2-490b-90bc-0a1d8953e19b.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-aa3d8d15-7608-4c5a-be78-4db171e9576f.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-6d96e490-a61c-44fb-ac99-3dbf5a23b27a.png`

### Final requested pass

- `C:\Users\V\AppData\Local\Temp\codex-clipboard-787d72b0-cefc-4641-9c90-d9b75d0af1ce.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-63d28d5c-cb28-4496-9fd7-c0889e9ccc36.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-36b65b43-5c20-4c6d-acee-f12cb5595ebd.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-f1117ee0-5a2b-4453-a188-41f5a3eaa7a0.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-4ad4a6ac-c310-4a28-b1fd-fc1d458ee372.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-fb2ec486-be5b-4721-a417-ba950b998b7e.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-570c9a80-1330-4b8a-a23a-cbafc193829f.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-04877ba4-c6fc-4a14-abc8-805cd7510f9b.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-673e74df-7a6a-482d-ba9f-3381c79a8da3.png`
- `C:\Users\V\AppData\Local\Temp\codex-clipboard-1375dea1-dbb9-4c7d-b95e-4027ce065b84.png`

## 16. Immediate Handoff Starting Point

The next implementation session starts with `GuideRail.qml` and
`ImportDialog.qml`, not with another palette experiment. First establish the
repeated-choice contract across every matching list and fix the verified
scrollbar geometry. Then complete the mode, entry-copy, grid-hover, footer-run,
and loading changes as one coherent pass. Finish by launching the current source
and leaving the actual Modori window open for owner inspection.
