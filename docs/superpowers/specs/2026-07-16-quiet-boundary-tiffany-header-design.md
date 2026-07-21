# Quiet Boundary and Tiffany Header Reconciliation

**Status:** Owner-approved on 2026-07-16
**Scope:** Persistent surface boundaries, work tabs and command header, import-dialog shape, and scrollbars

## Decision

Modori will stop outlining every long-lived region. Structure is expressed first by
surface tone, spacing, alignment, and a small number of one-direction dividers.
Rose-bronze emphasis appears only for selection or meaningful focus, not as a
permanent frame around every control.

## Surface hierarchy

- `PearlSurface` is borderless by default.
- Modal overlays may request one subtle outer outline; nested panes do not inherit it.
- The work shell's guide, data, results, and pipeline regions separate through their
  approved background roles and layout gaps instead of four-sided frames.
- Form fields and independent selection controls retain an affordance boundary, but
  passive cards and quiet buttons do not.

## Selection and focus

- Work tabs have no permanent four-sided border.
- The selected tab uses a two-pixel `#B9856E` bottom line.
- Keyboard focus remains visible as a bottom line without turning pointer-selected
  tabs into a green frame.
- Current data-grid cells retain a non-color-only selected fill plus one emphasized
  edge treatment.

## Scrollbars

- Scroll rails use a visible warm neutral fill and thumbs use a darker neutral fill.
- Rails and thumbs have no independent outline or center-line decoration.
- Hovered or dragged thumbs use a darker Tiffany-family color so the active state
  remains visible without adding an outline.
- The import preview, review list, column list, and expanded settings all use the
  shared contained `AppScrollBar` rather than platform-default scrollbars.

## Import dialog

- The dialog keeps one consistent radius on all four corners.
- The header is transparent over the rounded dialog surface, so it cannot square off
  the top corners.
- The right settings pane separates by background tone, not an additional outline.

## Work header

- The Tiffany band remains the dominant material.
- Header commands use compact typography, transparent resting backgrounds, and no
  permanent border.
- The wordmark is slightly reduced, command gaps are tightened, and the mode switch
  uses a quiet neutral track with rose-bronze state rather than a green bordered pill.
- The settings gear remains a plain icon entry point, showing an outline only for
  keyboard focus.

## Verification

- Contract tests cover borderless default surfaces, selected-tab bottom emphasis,
  borderless scrollbar geometry, import scrollbar reuse, rounded dialog header, and
  compact header controls.
- QML runtime loading and the full UI suite must pass.
- The real application is launched for owner visual review; acceptance remains based
  on the running interface, not a generated mockup.
