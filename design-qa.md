# Royal Blue Bilingual Entry — Design QA

## Evidence

- Source visual truth: `C:\Users\V\AppData\Local\Temp\codex-clipboard-ed3874a9-fc06-4177-8451-abf62b4c69c3.png`
- Implementation captures: `docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`, `ko-pro.png`, `en-casual.png`, `en-pro.png`, `ko-focus.png`, `en-focus.png`
- Full-view comparison: `docs/design-audit/2026-07-19-royal-blue-entry/comparison-ko-casual.png`
- Focused right-column comparison: `docs/design-audit/2026-07-19-royal-blue-entry/comparison-right-column.png`
- Focused mode-card comparison: `docs/design-audit/2026-07-19-royal-blue-entry/comparison-mode-cards.png`
- Viewport: 1366 × 768 logical pixels; Windows 125% device output was normalized to 1366 × 768.
- States: Korean/English × Casual/Pro, plus Korean and English keyboard-focus states.
- Renderer: native Windows Qt Quick/D3D11 capture from the real `EntryScreen.qml`; the capture harness reported no QML errors.

The 1381 × 801 structural reference was normalized to the required 1366 × 768 viewport before focused comparison. Its green palette, illustrative circles, fabricated recent-file metrics/times, and orange `Edit` annotation are not implementation targets. The written royal-blue palette, truthful-data rule, preserved routing, and no-new-feature boundary control those intentional deviations.

## Findings

No actionable P0, P1, or P2 finding remains.

- Fonts and typography: Segoe UI renders cleanly in native Windows captures. The implementation retains Modori's uppercase, letter-spaced wordmark, uses a clear 22 px entry heading, and keeps Korean and English descriptions on one readable line without truncation.
- Spacing and layout rhythm: the left region is exactly 37% and full-height. The right content remains within a 650 px measure; mode cards have equal height, the primary action spans the same measure, and recent rows use a stable 54 px rhythm.
- Colors and tokens: the approved roles are exact (`#173B7A`, `#F7F3EA`, `#FFFDF8`, `#2F5DA8`, `#17233A`). Selected cards add blue border, tinted fill, and a check marker rather than relying on color alone.
- Image and icon fidelity: settings and selected-state markers use existing real SVG assets. No placeholder illustration, emoji, handcrafted SVG, or code-drawn decorative asset replaces a source asset. The source's decorative shapes are intentionally omitted under the solid royal-blue written specification.
- Copy and content: Casual remains explicitly experimental and states that nothing runs automatically. Recent rows display only real model labels from fixture files; no time, row count, column count, or other metadata is invented. Korean and English catalogs have identical keys.
- Interaction and accessibility: language choices and mode cards expose radio-button semantics and checked state; all primary controls accept tab focus. The focused unselected card is distinguishable from the selected card, and locale selection persists across the active session without changing saved settings.
- Runtime reach: live tests cover entry copy, work-screen copy, dialog titles, dynamic errors, recommendation titles/reasons, pipeline step names, result copy, and import/variable models in English.

## Comparison History

### Iteration 1 — blocked

- [P1] English recent rows disappeared after switching languages.
  - Evidence: the first `en-casual.png` and `en-pro.png` retained the recent-files surface but rendered no delegate rows.
  - Cause: ListView height depended on `contentHeight`; model reevaluation during the session language change briefly collapsed the viewport to zero and prevented delegate recreation.
  - Fix: derive the bounded viewport from the real model count (`Math.min(count, 3) * entryRecentRowHeight`) instead of transient rendered content height.

### Iteration 2 — passed

- Post-fix evidence: `comparison-en-casual.png`, `comparison-en-pro.png`, `comparison-right-column.png`, and `comparison-mode-cards.png`.
- All three real recent filenames remain visible after Korean-to-English switching.
- Casual/Pro selection, unselected keyboard focus, language state, settings entry, and truthful recent rows are legible at 1366 × 768.

## Primary Interactions Checked

- Korean ↔ English session switching updates the complete visible runtime catalog and controller-backed UI copy.
- Casual and Pro preserve their existing `guidedRequested` / `standardRequested` routing.
- Data open, recent-file open, and settings preserve the existing Main handlers.
- Selected and keyboard-focused states remain separately visible.
- No QML `ReferenceError`, `TypeError`, or component-load error was emitted during the six-state native capture.

## Follow-up Polish

- [P3] A future real, licensed right-chevron icon could strengthen the recent-row affordance. It is intentionally omitted now because the repository has no matching asset and the approved scope forbids inventing one.

final result: passed
