# Grid Scroll Containment and Splash Reconciliation Design

**Status:** Approved direction, pending implementation
**Date:** 2026-07-16
**Scope:** Data grid scrolling, grid scrollbars, and the startup splash screen only

## Context and evidence

The annotated user screenshot and the currently running Modori build show the same problem: horizontal scrolling can stop between columns, leaving partial cells visible at both edges. The attached platform scrollbars sit over the table content, and the separately synchronized header and body make direction changes feel less settled than the rest of the interface. The current splash still uses the earlier full-screen teal-to-orange gradient, a large title, and the platform-default progress bar.

This change must not alter data loading, selection semantics, keyboard navigation, analysis configuration, results behavior, or the guided/direct mode boundary.

## Selected approach

Use a contained, cell-aligned grid with dedicated scrollbar rails, while retaining Qt's virtualized `TableView` and header views. Reconcile the splash with the current toned-down white and subtle nacre system.

This approach is preferred over a skin-only patch because clipping alone would leave the unsettled stopping behavior. It is preferred over rebuilding the grid because a rewrite would introduce unnecessary risk to virtualization, selection, accessibility, and large-data performance.

## Grid containment

- The complete grid viewport, including horizontal and vertical headers, is clipped by one explicit containment surface.
- Header, row-header, body, scrollbar rails, and status row have fixed stacking order. Cell and header delegates must never render over the row-header, results panel, scrollbar rails, or status row.
- Scrolling stops at the content bounds without overshoot or elastic bounce.
- Moving content remains pixel-aligned so one-pixel borders do not shimmer during direction changes.
- When movement ends, the leading edge settles to the nearest row or column boundary with a short ease-out no longer than 120 ms. Reduced-effects mode settles immediately.
- The existing fixed cell dimensions and view virtualization remain intact.
- A quiet one-pixel boundary line separates the grid from adjacent panels; no shadow or raised edge is introduced.

## Scrollbar system

- Add a reusable Qt Quick Controls Basic scrollbar styled from existing theme tokens.
- Give vertical and horizontal scrollbars dedicated 12 px rails outside the cell viewport instead of overlaying cells.
- Use a low-contrast 3 px track and a 5 px thumb. Expand the thumb to 7 px while hovered or dragged, without changing the rail's layout width.
- Use muted neutral color at rest and the existing subdued teal only while active. Avoid dark platform-gray bars and strong glow.
- Keep a minimum thumb length of 28 px and preserve mouse dragging, wheel scrolling, touchpad scrolling, and keyboard navigation.
- Fill the rail intersection with the same quiet surface as the grid frame so it reads as part of the table rather than a detached control.
- Hide the thumb when its axis does not overflow, but retain the 12 px rail so the grid does not jump when overflow changes.

## Startup splash

- Replace the teal-to-orange full-screen gradient with the current toned-down white canvas and a very subtle nacre ambient tint.
- Reduce the `Modori` wordmark to a compact 30 px title. Keep the current Korean subtitle and local-data reassurance copy.
- Replace the platform-default progress bar with a Basic progress control: a 180 px by 4 px quiet track and a subdued teal moving segment.
- Use a soft, continuous ease for normal mode. Reduced-effects mode shows a completed static line with no looping animation.
- Keep the existing splash timing and transition behavior. Do not add illustration, glow, logo invention, or new navigation.

## Accessibility and interaction

- Preserve arrow, Home, End, Page Up, Page Down, and copy shortcuts.
- Preserve the current-cell focus treatment and accessible cell activation behavior.
- Scrollbars retain an adequate 12 px pointer hit rail even though the visible thumb is narrower.
- Motion is brief, non-elastic, and disabled when reduced effects are enabled.
- Contrast must remain at least as strong as the current grid borders and control states; the active scrollbar cannot be the only indication of keyboard focus.

## Failure handling and boundaries

- Snap targets are clamped to valid content extents before positioning.
- Empty or smaller-than-viewport models must not produce invalid scrollbar positions, movement, or visible inactive thumbs.
- Resizing the window while scrolled must keep the current visible cell in range and must not expose content outside the grid surface.
- No changes are made to imported data, model ordering, selected cell values, or result calculations.

## Verification

- Add failing UI contract tests for explicit grid containment, non-overlay scrollbar rails, bounded pixel-aligned movement, and the reconciled splash.
- Add or extend runtime QML tests to load the grid with the wide 108-column fixture and verify valid scrollbar and snap bounds.
- Run the full UI test suite.
- Capture the actual application at 1180 × 760 with the same wide-data state, before and after horizontal and vertical movement.
- Compare the user-provided reference and the new render together, checking both grid edges, scrollbar placement, header/body alignment, and the results-panel boundary.
- Capture and inspect the startup splash in both normal and reduced-effects states.

## Acceptance criteria

1. No body or header cell appears outside its grid viewport at rest or during edge scrolling.
2. After movement settles, the leading row and column begin on a clean cell boundary.
3. Reversing scroll direction produces no elastic bounce, border shimmer, or detached-cell appearance.
4. Scrollbars never cover table values or headers and remain draggable.
5. The startup splash visibly belongs to the toned-down white, subtle nacre Modori system.
6. Existing grid selection, keyboard navigation, loading, analysis, and results behavior continue to pass their tests.
