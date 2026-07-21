# Full-Bleed Bronze Reconciliation Design

## Goal

Refine Modori's approved aurora-glass direction so the entry screen reads as a complete application canvas rather than a floating card, the work shell uses one coherent bronze interaction language, and adjacent surfaces remain visibly distinct without returning to heavy outlines.

## Approved Direction

Use the unified aurora-glass approach selected by the user:

- make the entry screen a full-window split canvas;
- keep the work header aurora, but remove visible color bands;
- replace green control and state accents with the existing rose-bronze family;
- flatten the results panel from two nested light surfaces to one surface;
- place each alternate analysis candidate in a restrained glass row;
- make the pipeline rail a full-width, stronger neutral aurora-glass footer;
- increase the contrast of the commonly used darker neutral surface by approximately 30 percent.

## Color System

### Neutral surfaces

The reference canvas remains `#FEFDFC`.

The current darker neutral is `#FBF9F7`. Increase its RGB-channel distance from the canvas by 1.3 times:

- current deltas from the canvas: 3 red, 4 green, 5 blue;
- 1.3-times deltas, rounded: 4 red, 5 green, 7 blue;
- new darker neutral: `#FAF8F5`.

Use `#FAF8F5` for the shared raised and quiet surface roles so the change is consistent across the application. Keep the base canvas and paper surfaces lighter so the two levels remain distinguishable.

### Bronze interaction family

Keep `#B9856E` as the visible rose-bronze brand accent and selected-edge color. Add darker bronze derivatives for solid interactive fills, hover/pressed states, focus, and active scroll thumbs. Solid buttons must use a bronze dark enough for white text to remain readable; do not use `#B9856E` with small white text as the primary filled state.

Replace the green/teal interaction roles across buttons, checkboxes, radio buttons, text selections, switches, focus rings, status badges, and active scrollbars. Replace green-tinted text roles with warm neutral charcoal roles. Warning and danger semantics remain distinct.

The cyan/ice/lilac/rose colors inside the approved aurora glass remain; they are environmental color, not an interaction-state language.

## Entry Screen

Remove the centered fixed-size rounded start card and its outer viewport gutter. The window itself becomes the composition:

- the aurora brand region fills the full height at the left;
- the warm neutral task region fills the remaining width at the right;
- neither region has an enclosing outer radius or floating-card outline;
- the existing brand copy, privacy copy, mode choices, data opening action, recent files, and settings entry point retain their behavior;
- internal content keeps generous padding so full bleed does not become edge-to-edge text.

The split is structural rather than card-like. The right task region may cover the aurora layer, but it must not introduce a rounded nested panel.

## Aurora Blending

The current header blends colored stops toward a shared transparent black value, which creates dull transition bands. Replace those fades with transparent variants of the same hue. Spread the ice, lilac, and rose transitions across overlapping layers with wider falloff ranges.

Requirements:

- no hard seam between cyan, ice, lilac, and rose;
- no animation;
- no persistent full perimeter border;
- keep the one-edge rose-bronze anchor only where selection or structural grounding is useful;
- reduced-effects mode continues to use a static neutral fallback;
- Tiffany can remain in the glass because the user approved the color, but it must not remain as a control accent.

## Work Shell

### Header

Keep the current thin aurora header, black uppercase wordmark, and spacious wordmark-to-command gap. Only smooth the gradient and migrate interactive controls from green to bronze.

### Guide rail and candidate list

Retain the recommended-candidate summary surface. Render each alternate candidate as a low-profile glass row with moderate Galaxy-like corner rounding, a quiet light fill, and a single subtle lower separator. Do not restore full four-sided outlines. Preserve keyboard focus and the existing click behavior.

### Results panel

Remove the near-white preview surface nested inside a darker results panel. The results panel should be a single light plane with its content padding applied directly. Tables and figures may retain their own purposeful frames because they are embedded artifacts, not duplicate panel chrome.

### Footer / pipeline rail

Place the pipeline rail outside the inset work-content margins so it spans from the left edge to the right edge below the main workspace. Use a stronger neutral aurora-glass surface with no outer corner radius. Do not use the dark-charcoal alternative in this pass because standard mode places multiple light form controls inside the footer; a dark footer would require a second inverted control theme and would make the dense form visually heavier.

The footer's content and behavior stay unchanged.

## Component Boundaries

- `Theme.qml` owns neutral, bronze, aurora-fade, list-row, and footer tokens.
- `AuroraGlassSurface.qml` owns smooth hue-preserving blending and supports the stronger neutral footer treatment.
- `EntryScreen.qml` owns the full-window split layout.
- `WorkScreen.qml` owns the full-width footer placement and the inset main workspace.
- `ResultsPanel.qml` owns the single-plane results layout.
- `GuideRail.qml` selects the glass-row appearance for alternate candidates.
- Shared control components consume bronze semantic tokens and do not define literal colors.

## Accessibility And Interaction

- Keep all current accessible names, keyboard focus policies, toggle behavior, and click handlers.
- Solid primary buttons use white text only on a sufficiently dark bronze fill.
- Focus remains visible without a persistent outline at rest.
- Candidate rows must remain identifiable at rest, on hover, on focus, and while pressed.
- Reduced-effects mode remains static and readable.

## Acceptance Criteria

1. The entry screen has no centered floating start card or outer gutter.
2. The header has no visible gray or abrupt color bands.
3. No shared interactive control uses the former teal/green theme roles.
4. The shared darker neutral is `#FAF8F5`.
5. The results panel has one panel plane rather than a panel inside a panel.
6. Alternate analysis candidates appear as distinct glass rows without four-sided outlines.
7. The pipeline rail spans the complete work-window width and uses the stronger neutral glass treatment.
8. Existing analysis, mode-selection, file-opening, report, and settings behavior remains unchanged.
9. Static QML contracts, QML runtime-load tests, the complete UI suite, and launch smoke all pass.
10. The real Modori entry and work screens are captured and compared with the user's screenshots before handoff.

## Out Of Scope

- New workflows or analysis behavior.
- A dark mode or inverted dark-control system.
- Motion in the aurora glass.
- Changes to the experimental recommendation boundary or analysis semantics.
