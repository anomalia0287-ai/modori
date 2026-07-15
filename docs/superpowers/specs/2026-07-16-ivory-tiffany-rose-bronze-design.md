# Ivory, Tiffany, and Rose-Bronze Visual Reconciliation

**Status:** Approved by the owner on 2026-07-16
**Scope:** Global palette roles, Modori wordmark, structural boundaries,
scrollbar colors, and matching startup treatment

## Context

The first cream-nacre implementation is visually heavier and warmer than the
new reference direction. The owner has selected a much lighter foundation: a
white-adjacent ivory canvas, a separately readable warm secondary surface, a
Tiffany-blue top command header, and restrained rose-bronze structure. Pure
white is reserved for the scrollbar rail and thumb so those controls remain
visibly distinct from both application surfaces.

This document supersedes only the palette and wordmark portions of
`2026-07-15-cream-nacre-qml-redesign-design.md` and the color treatment in the
scrollbar and splash portions of
`2026-07-16-grid-scroll-and-splash-design.md`. Their interaction, containment,
motion, accessibility, and statistical-integrity requirements remain in
force.

## Selected Approach

Apply the change through semantic theme tokens and one reusable wordmark
component. Do not paint individual screens with unrelated literal colors and
do not simulate metal with a gradient or shader.

This keeps dialogs, tables, panels, the work shell, and the startup screen in
one system while preserving the existing QML component architecture.

## Fixed Palette

The approved fixed values are:

| Role | Value | Use |
| --- | --- | --- |
| Primary canvas and quiet content | `#FEFDFC` | White-adjacent ivory used for the overall application foundation |
| Secondary warm surface | `#FBF9F7` | Areas that previously used the stronger cream, including grouped forms and supporting panels |
| Top command header | `#81D8D0` | Tiffany-blue work-shell header; not a general-purpose card color |
| Modori wordmark | `#B9856E` | Parisienne logotype on entry, work, and splash surfaces |
| Strong or emphasized boundary | `#B9856E` | Selected, focused, or structurally important edges |
| Thin divider | `#D7B9AA` | Quiet grid, tab, rail, and panel separation |
| Scrollbar rail and resting thumb | `#FFFFFF` | The only deliberate pure-white surface role |

The deep green-charcoal text and established action teal remain semantic text
and action colors. Tiffany blue is not substituted for every action: it is
reserved for the top command header and the active scrollbar state so the
palette does not become decorative or noisy.

Literal instances of these values remain centralized in `Theme.qml`. QML
screens and controls consume named roles only.

## Surface Hierarchy

- The outer canvas and principal reading surfaces use `#FEFDFC`.
- Grouped forms, supporting panes, quiet button fills, and the areas that were
  previously dark cream use `#FBF9F7`.
- Adjacent primary and secondary surfaces are separated with a one-pixel
  `#D7B9AA` divider instead of elevation or shadow.
- `#B9856E` is reserved for meaningful emphasis: strong frame edges, selected
  or focused structure, and the brand wordmark.
- The top work-shell command band uses `#81D8D0`. Child controls remain calm
  and readable rather than inheriting saturated fills.
- Cards do not appear to float. Long-lived panes use flush alignment and thin
  boundaries; shadow is retained only where an overlay must be distinguished
  from its parent.

## Nacre and Semantic Light

The aurora treatment becomes a near-white nacre reflection rather than a
visible colored wash:

- ambient mint, shell-pink, and lilac stops are lifted close to white and kept
  at very low opacity;
- a parent surface supplies the reflection while child panels remain quiet;
- no large colored bloom, rainbow band, or continuous decorative glow is
  introduced;
- light appears only for focus, an actionable ready state, current selection,
  running, stale, or error state;
- reduced-effects mode preserves borders and labels while removing pulse,
  bloom, and nonessential motion.

Exact ambient opacity may be reduced after running-app comparison, but it may
not be increased until the nacre becomes an obvious color field.

## Modori Wordmark

- Use the Parisienne typeface for the word `Modori` in the entry screen, work
  header, and startup splash.
- Bundle the regular font file and its license with the application. Do not
  rely on a system-installed font or runtime network access.
- Use the approved flat `#B9856E` color. Do not use a metallic gradient,
  texture, glow, or faux embossed effect.
- Keep each existing brand slot compact; the font change must not introduce a
  larger hero block or change command-header height.
- The work-header rendering is checked in the real application because the
  approved wordmark and Tiffany colors intentionally have restrained
  contrast. If recognition is weak, adjust the immediate supporting surface or
  size while preserving both approved colors.
- Preserve the accessible product name independently of the decorative font.

## Scrollbar Treatment

The existing contained, non-overlay scrollbar geometry and cell-aligned
settling behavior remain unchanged.

- Rail fill: `#FFFFFF`.
- Resting thumb fill: `#FFFFFF`.
- Quiet rail separation: one-pixel `#D7B9AA`.
- Thumb and emphasized edge: one-pixel `#B9856E`.
- Hovered or dragged thumb: `#81D8D0`, with geometry expanding inside the
  existing 12 px hit rail rather than changing layout.
- No platform-grey fill, shadow, glow, overshoot, or overlay on grid content.

Pure white is allowed only for these scrollbar roles. It must not leak into
the application canvas, cards, tables, dialogs, or startup background.

## Startup Treatment

The splash uses the same `#FEFDFC` foundation and restrained near-white nacre
reflection as the application. It uses the Parisienne `#B9856E` wordmark and
the custom progress geometry already defined by the grid-and-splash design.
The progress accent may use the established action teal; the splash does not
receive a large Tiffany panel or decorative glow.

## Accessibility and Interaction

- Normal functional text retains at least 4.5:1 contrast; component boundaries
  and focus indicators retain at least 3:1 where required.
- The Parisienne brand name is a logotype, not the sole functional label for a
  control or destination.
- Focus, selection, running, stale, and error states continue to use text or
  shape in addition to color.
- The new palette must not change keyboard navigation, pointer hit targets,
  screen-reader names, or reduced-effects behavior.
- Existing checkboxes remain only for independent multi-selection. Persistent
  immediate binary preferences remain switches.

## Implementation Scope

Expected touched areas are:

- `src/modori/ui/qml/theme/Theme.qml`;
- a reusable wordmark component under `src/modori/ui/qml/components/`;
- `src/modori/ui/qml/screens/EntryScreen.qml`;
- `src/modori/ui/qml/screens/WorkScreen.qml`;
- `src/modori/ui/qml/screens/SplashScreen.qml`;
- `src/modori/ui/qml/components/AppScrollBar.qml`;
- the local font and license resources;
- `pyproject.toml` package-data declarations;
- focused UI visual-contract, resource, and runtime-load tests.

Other screens should change through semantic token consumption, not through a
screen-by-screen literal-color rewrite.

## Verification

1. Add failing contract tests for the exact palette roles, pure-white
   restriction, wordmark component usage, and bundled font resources.
2. Add or extend runtime QML tests for font loading and scrollbar states.
3. Run focused tests, then the complete `tests/ui` suite.
4. Launch the real application and capture the entry screen, work shell with a
   wide dataset, a scrolled grid, and the startup splash at the established
   viewport.
5. Compare the implementation with the supplied color references and current
   running-app captures, checking surface separation, header balance,
   wordmark recognition, scrollbar containment, and unwanted floating cards.
6. Tune only non-fixed opacity or spacing values when the running evidence is
   visually heavier or weaker than intended.

## Acceptance Criteria

1. The application canvas is visibly softer than pure white but remains
   lighter and distinct from the `#FBF9F7` secondary surface.
2. The top work header reads as Tiffany blue without spreading that color
   across unrelated cards or actions.
3. Every visible Modori wordmark uses bundled Parisienne and `#B9856E`.
4. Strong boundaries use `#B9856E`; thin dividers use `#D7B9AA`.
5. Pure white appears only in the scrollbar rail and resting thumb.
6. Scrollbars remain contained, draggable, non-overlaying, and visibly active
   in Tiffany blue.
7. The splash, entry screen, work shell, dialogs, and data grid read as one
   restrained ivory-and-nacre system.
8. Existing UI tests and runtime loading pass, and the owner reviews the real
   running application rather than a generated mockup.
