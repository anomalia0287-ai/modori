# Aurora Glass Brand Header Design

## Context

The current work header is a flat Tiffany surface. Its light tone lowers text contrast, while the script wordmark and tight command spacing make the header feel visually crowded. The entry screen has the same brand wordmark but no distinct brand field, so the identity is not carried consistently from entry to work.

The approved direction is a stronger, static aurora glass treatment grounded in the supplied cool-blue-to-rose reference. Tiffany blue may remain only as one aurora layer. If that layer muddies the surface or weakens legibility in the real application, it must be removable without redesigning the component.

## Goals

- Improve header legibility without returning to persistent outlines.
- Replace the script logo with a consistent black, uppercase Gothic-style `MODORI` wordmark.
- Give the wordmark generous separation from work commands.
- Reuse one aurora glass component in the work header and the entry screen's left brand region.
- Preserve a calm hierarchy by keeping aurora glass out of data, result, settings, and import surfaces.
- Keep the treatment static and compatible with the existing reduced-effects preference.

## Approved Visual Direction

### Aurora glass

The surface uses a cool neutral glass base with layered vertical and horizontal color fields:

- a cool blue-gray foundation provides the dominant contrast;
- Tiffany blue appears only as a secondary bloom, not the full background;
- ice blue, pale lilac, and restrained rose create the stronger aurora requested by the owner;
- a translucent white veil and a narrow top sheen create the glass impression;
- a single quiet bottom separator anchors the work header without outlining it on four sides.

The effect is static. There is no drifting gradient, shimmer animation, or pulse. Reduced-effects mode removes secondary blooms and keeps a readable cool-neutral glass gradient.

The Tiffany bloom is an isolated theme role and an explicit component property. It can be disabled after real-screen review without changing layout, typography, or the remaining aurora layers.

### Wordmark

All `BrandWordmark` instances display `MODORI` in uppercase using the Windows Gothic/sans-serif system family. The wordmark uses near-black rather than rose bronze, medium-to-semi-bold weight, and visible letter spacing. Accessibility text remains the localized application title.

On the work header, the wordmark receives a dedicated trailing margin substantially larger than the normal command gap. Command-to-command spacing stays compact.

### Placement

The aurora glass component is used in exactly two layout regions:

1. the full-width work header;
2. the left brand region inside the entry start surface.

The entry brand region owns the wordmark, product promise, privacy statement, and local/open-source footer. Its glass field is clipped by the existing outer entry surface so the left top and bottom corners remain consistent. The old vertical divider is removed because the change in surface tone provides the boundary.

The splash screen adopts the new black uppercase wordmark for identity consistency, but it does not gain a new aurora panel in this pass.

## Component Design

### `AuroraGlassSurface.qml`

The new shared component owns all glass layers and exposes only layout-safe controls:

- `reduceEffects`: selects the simplified neutral fallback;
- `tiffanyBloomEnabled`: includes or removes the Tiffany layer;
- `radius`: matches the containing surface where needed.

All colors, opacities, dimensions, and separator values come from `Theme.qml`. Non-theme QML contains no literal colors or visual metric literals.

### Existing screens

- `WorkScreen.qml` replaces the flat header `PearlSurface` with `AuroraGlassSurface` and adds a dedicated wordmark-to-command margin.
- `EntryScreen.qml` changes the start sheet to a clipped two-region layout. The left region is `AuroraGlassSurface`; the right task region remains the quiet off-white surface.
- `BrandWordmark.qml` drops the Parisienne font loader and owns uppercase capitalization, Gothic system font, near-black color, weight, and letter spacing.
- `SplashScreen.qml` continues reusing `BrandWordmark` with no additional decorative surface.

## Readability Rules

- All work-header labels and icons use the existing strong or control text roles; disabled labels retain their disabled role.
- The aurora field must not sit above controls or intercept input.
- The wordmark remains readable at the compact work size and the larger entry size.
- The work header retains a single bottom anchor line only; no persistent button frames or full header outline are introduced.
- If the first real-screen capture looks muddy, the first correction is to disable the Tiffany bloom, not to add borders or darken every control.

## Testing And Review

Automated checks will establish the following contracts before implementation:

- the shared aurora component exists and is used only in the approved two regions;
- the Tiffany layer can be disabled independently;
- the wordmark is uppercase, near-black, Gothic/sans-serif, and letter-spaced without loading Parisienne;
- the work wordmark has a dedicated trailing gap;
- no animation is introduced in the aurora component;
- QML runtime loading and existing UI suites remain green.

After automated verification, the real Modori entry and work screens will be captured at the same window size used in the current review. The owner will review contrast, aurora strength, wordmark spacing, and whether the Tiffany bloom remains clean. If it does not, the isolated Tiffany layer will be disabled and the neutral aurora version will be shown instead.

## Out Of Scope

- Aurora panels in results, data grids, transforms, settings, reports, or import dialogs.
- Animated aurora, shimmer, particle, glow, or semantic status effects.
- Reintroducing outlined header buttons.
- Changing the established off-white content palette or rose-bronze selection language.
