# Aurora Glass design QA

## Comparison target

- Source visual truth:
  - `C:\Users\V\AppData\Local\Temp\codex-clipboard-71c07cee-f829-4ee3-aa87-0700ba657126.png` — owner-marked entry-screen card treatment to replace with a full-bleed composition.
  - `C:\Users\V\AppData\Local\Temp\codex-clipboard-1375dea1-dbb9-4c7d-b95e-4027ce065b84.png` — owner-marked manual-analysis list whose two-column treatment and missing separation were rejected.
  - `C:\Users\V\AppData\Local\Temp\codex-clipboard-fb2ec486-be5b-4721-a417-ba950b998b7e.png` — owner-marked import dialog and scrollbar state.
  - `docs/superpowers/handoffs/2026-07-16-modori-owner-directives-and-visual-polish-handoff.md` — consolidated owner directives, exact copy, semantic-state, spacing, color, and interaction requirements.
  - `docs/superpowers/specs/2026-07-16-aurora-glass-brand-header-design.md` — approved Aurora Glass design contract.
- Rendered implementation:
  - `docs/design-audit/2026-07-17-aurora-glass-final/entry.png`
  - `docs/design-audit/2026-07-17-aurora-glass-final/work-manual-top.png`
  - `docs/design-audit/2026-07-17-aurora-glass-final/import-dialog.png`
  - `docs/design-audit/2026-07-17-aurora-glass-final/import-dialog-scrolled.png`
  - `docs/design-audit/2026-07-17-aurora-glass-final/loading.png`
- Viewport: 1180 × 760 logical pixels on Windows at 125% device scaling; native captures are 1475 × 950 physical pixels.
- State: entry; guided work screen with imported `psych_bfi.csv`; manual analysis selection expanded; import preview at top and scrolled; transient loading overlay.

The owner screenshots are iterative issue references rather than one exact pixel mock. The comparison therefore treats the approved written design contract as authoritative and uses the screenshots to verify that each rejected treatment is absent. Physical screenshot dimensions vary slightly, so the boards normalize each image without claiming pixel-for-pixel equivalence.

## Full-view comparison evidence

- `docs/design-audit/2026-07-17-aurora-glass-final/comparison-entry.png`
  - The former centered card is replaced by a true edge-to-edge two-region entry screen.
  - The left brand region carries the restrained aurora surface; the right remains a toned white work surface.
  - `MODORI` is black, uppercase, Gothic, and tracked; the approved two-line welcome copy replaces the former data-locality headline.
  - `CASUAL MODE` and `PRO MODE` have equal scale and pale rose surfaces, with selection expressed by a bottom bronze line rather than a filled dominant button.
- `docs/design-audit/2026-07-17-aurora-glass-final/comparison-import-dialog.png`
  - The dialog uses one consistent radius on every corner.
  - Scroll rails have no separate outline; darker neutral thumbs remain visible against a near-white rail.
  - Controls, checkboxes, and the primary action use the bronze family rather than the retired green state color.

## Focused region comparison evidence

- `docs/design-audit/2026-07-17-aurora-glass-final/comparison-manual-list.png`
  - The former two-column text cloud is replaced by a single scan path.
  - Each analysis option occupies its own quiet-glass row and is separated by a thin bronze divider.
  - All ten labels are exposed in the QML accessibility tree; the focused capture shows the first five, and runtime scrolling exposes the remaining five.
- `docs/design-audit/2026-07-17-aurora-glass-final/import-dialog-scrolled.png`
  - The import-column scrollbar moved from visual position `0.0000` to `0.6588` and exposes the final variables (`gender`, `education`, `age`).
- `docs/design-audit/2026-07-17-aurora-glass-final/loading.png`
  - The blocking state is clearly legible as `로딩 중` over a restrained dim layer, with no decorative animation required when reduced effects are enabled.

## Required fidelity surfaces

- Fonts and typography: `Segoe UI` is retained for Korean and interface copy. The brand wordmark uses uppercase capitalization, demi-bold weight, and 2.4px tracking. Hierarchy is compact; no oversized navigation text or clipped manual-analysis label remains in the accessible contract.
- Spacing and layout rhythm: the work wordmark-to-command gap is 40px; header actions remain compact; mode actions have equal minimum width; the entry screen is full bleed; guide, grid, result, and pipeline regions align without floating nested cards.
- Colors and visual tokens: the final system uses toned white/ivory surfaces, `#B9856E` for logo-adjacent emphasis and selected boundaries, and `#D7B9AA` for quiet dividers. Green interaction emphasis is removed. The aurora is constrained to header, entry brand region, and footer glass rather than spread across every panel.
- Image quality and asset fidelity: no photographic, generated, or placeholder image asset is part of the approved interface. Aurora and glass are native QML surfaces, not substitutes for a missing source image. The existing gear icon remains crisp and aligned.
- Copy and content: entry copy is exactly `통계 작업을 위한 선택,\n모도리에 오신 것을 환영합니다.` Mode labels are `CASUAL MODE` and `PRO MODE`. The experimental-candidate boundary language is retained. Loading copy is exactly `로딩 중`.

## States, behavior, and accessibility

- Verified entry-to-work navigation, mode switching, manual-list expansion, manual-list scrolling, data-grid selection surface, import preview, import-list scrolling, and loading overlay.
- Data-grid hover is a subtle surface shift; repeated value tooltips are removed.
- Mode controls expose radio-button semantics, names, and checked state. Manual analysis rows expose full accessible names. Existing mandatory review confirmation remains a checkbox.
- Focus/selected states use the bronze lower indicator. Reduced-effects mode removes optional motion while keeping loading feedback visible.
- Import scrollbar runtime evidence: rail height tracks its scroll view and `visualPosition` changes with content position.

## Findings

- No actionable P0, P1, or P2 mismatch remains.
- P3 follow-up: the aurora balance can still be tuned after owner inspection without changing hierarchy, interaction semantics, or component geometry.

## Comparison history

1. Earlier owner evidence showed a floating entry card, green emphasis, dense four-sided borders, an unseparated two-column manual list, old scrollbar rails, repeated data-cell hover content, and no unified loading state.
2. The implementation replaced those treatments with full-bleed entry composition, bronze semantic emphasis, one-direction dividers, single-column glass rows, borderless scrollbar rails, subtle data-cell hover, and a localized loading overlay.
3. Native Windows QML captures at the target logical viewport were placed beside the owner references in the three comparison boards above. No new P0/P1/P2 issue was found.
4. The import scrollbar was then moved programmatically through its real attached QML object; the revised capture confirmed the thumb and content moved together from top to lower content.

## Implementation checklist

- [x] Full-bleed entry screen and restrained aurora brand region.
- [x] Aurora header, black tracked `MODORI`, 40px command separation, settings entry point.
- [x] Equal `CASUAL MODE` / `PRO MODE` controls with bronze lower-line state.
- [x] Bronze semantic states and toned-white/ivory hierarchy; no green interaction emphasis.
- [x] Ten manual-analysis rows with glass separation and working rail scroll.
- [x] Import dialog radii, borderless rails, visible thumb, and verified movement.
- [x] Data-grid hover without repeated value tooltip.
- [x] Strong-glass footer execution action.
- [x] Localized loading overlay and reduced-motion behavior.

final result: passed
