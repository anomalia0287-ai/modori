# Royal Blue Workspace Reconciliation Design

Date: 2026-07-19

Status: owner-approved on 2026-07-19.

## Objective

Extend the approved Royal Blue bilingual entry palette into Modori's work surface
without redesigning the workspace. Preserve the existing three-column structure,
panel order, routing, analysis behavior, controller contracts, dialogs, and storage
formats. Replace only presentation roles that conflict with the entry screen and fix
English wrapping or clipping visible at the 1366 x 768 acceptance viewport.

## Visual Source And Precedence

The approved entry implementation is the palette source of truth:

`docs/design-audit/2026-07-19-royal-blue-entry/ko-casual.png`

The current work implementation is the structural source of truth:

`docs/design-audit/2026-07-17-aurora-glass-final/work-manual-top.png`

The entry palette controls color and interaction hierarchy. The work screenshot
controls the three-column composition, header command order, guide rail, data tabs,
results rail, and bottom pipeline placement. Written requirements override legacy
peach/bronze interaction colors and the pastel header/footer aurora gradient.

## Chosen Approach

Add workspace semantic roles to `Theme.qml` and route shared work components through
those roles. Entry-specific `entry*` roles remain unchanged. Warning and danger roles
remain unchanged. This avoids a global literal color replacement, which could alter
the already-approved entry screen or weaken semantic states, and avoids per-component
color literals that would recreate palette drift.

The implementation remains a token and layout-density reconciliation. It adds no new
screen, route, panel, command, recommendation behavior, or asset.

## Workspace Palette

The workspace uses the same five approved source colors as the entry screen:

- workspace canvas: `#F7F3EA`;
- workspace card and panel: `#FFFDF8`;
- workspace primary, active, selected, and focus: `#2F5DA8`;
- workspace text: `#17233A`;
- workspace brand: `#173B7A`.

Derived roles use only alpha variations of these colors. The selected surface is a
low-opacity `#2F5DA8` tint over ivory. Hover is a lighter blue tint than selected.
Dividers are a low-opacity `#17233A`, not peach. Disabled controls use the existing
neutral text and opacity behavior.

Existing warning (`warning`, `warningSurface`) and error (`danger`,
`dangerSurface`) roles are not remapped. The work palette must not turn warnings or
errors blue.

## Header And Command Surface

The header remains in its current position and keeps the exact wordmark, command,
mode-segment, settings order, and signal handlers. Its pastel Aurora Glass background
is replaced by an ivory command surface. A subtle neutral divider separates the header
from the workspace. The wordmark uses Royal Blue brand color. Quiet commands stay
visually quiet; hover and keyboard focus use a pale blue surface and Royal Blue focus
outline. Disabled commands retain their existing disabled behavior.

Casual and Pro controls remain equal in hierarchy. The selected mode uses a pale blue
surface plus Royal Blue text and a bottom indicator; hover uses only the lighter blue
tint. Selection and focus remain distinguishable without relying on color alone.

## Three-Column Workspace

The existing `SplitView` order is unchanged:

1. Casual guide rail, visible only in Casual mode;
2. data, variable, and transform center surface;
3. results panel.

The canvas behind these columns is ivory. Each rail or center surface uses the card
role, with quiet neutral dividers and the existing corner vocabulary. No panel is
moved, nested differently, or converted to a new navigation pattern.

Active data tabs use all of the following:

- Royal Blue text;
- a pale blue selected background;
- a two-pixel Royal Blue bottom indicator.

Keyboard focus uses a two-pixel Royal Blue outline or indicator independent of the
selected state. Unselected tabs remain ivory with muted body text.

Primary actions across the work surface use Royal Blue fill, ivory text, a darker
Royal Blue pressed treatment, and a visible Royal Blue focus ring. Checkboxes,
radio buttons, switches, text selection, active scrollbar surfaces, selected rows,
and selected candidates use the same interaction family. Secondary and quiet actions
remain ivory or transparent and use blue only for hover, selection, or focus.

## Guide Rail And English Density

Korean keeps the compact guide-rail width. English receives a larger preferred guide
width within the existing `SplitView` minimum and maximum bounds so sentences remain
legible without changing the three-column structure. At 1366 x 768, the English
preferred width is 300 logical pixels and the Korean preferred width is 260 logical
pixels. The center data surface remains usable and the results rail keeps its existing
preferred width.

Guide body labels use word wrapping and width-constrained layouts rather than clipping
or eliding meaning. The long English action copy changes from
`View other experimental candidates` to `Other experimental candidates`. This keeps
the experimental-boundary meaning and the same action while fitting the accepted
viewport. Recommendation status and reason copy may wrap to multiple lines; the
containing rail remains vertically scrollable.

No Korean or English copy may imply automatic execution, validation, confidence, or
expert equivalence. The existing experimental-candidate and no-auto-run wording stays
intact.

## Results And Bottom Pipeline

The results rail uses the workspace card role directly. The unnecessary appearance of
a white card floating on a differently colored inner panel is removed by using one
ivory hierarchy with quiet spacing and neutral dividers. Result status badges continue
to use their semantic states.

The bottom pipeline keeps its current location, height logic, controls, and rerun
signal. The pastel multi-hue gradient is replaced by an ivory surface with a Royal
Blue top divider and blue primary or focus treatments. It remains visually distinct
from the canvas without becoming a second brand banner.

## Dialog And Shared-Control Consistency

Dialogs opened from the work surface retain their structure and behavior. Shared
buttons, fields, selectors, checks, radios, and focus rings inherit the workspace
interaction roles, so an import or settings dialog does not reintroduce peach controls
after the user leaves the entry screen. Dialog backgrounds use the same ivory/card
hierarchy. File paths, values, report content, and semantic alerts are not recolored or
rewritten.

## Accessibility

Selected states continue to use more than color: tabs use a tinted background and
bottom indicator; checkboxes and radios use a border and checked marker; switches use
both track and thumb position; selected candidate actions use a tinted background and
border. All keyboard-focusable controls retain visible focus at 1366 x 768, with Royal
Blue focus at two logical pixels. Text contrast is evaluated against both workspace
canvas and card surfaces. Warning and danger contrast remains independent of the brand
palette.

English labels, descriptions, tooltips, and accessible names remain session-reactive.
The palette work must not remove existing `Accessible.name`, role, checked state, Tab
focus, or focus order contracts.

## Verification Contract

Test-first automated coverage must prove:

- exact workspace palette source values and derived-role usage;
- entry palette values remain unchanged;
- warning and danger roles remain unchanged;
- the work header no longer enables pastel Aurora layers;
- active tabs, primary buttons, selection, and focus use workspace Royal Blue roles;
- the bottom pipeline no longer uses the pastel Aurora footer treatment;
- the three-column `SplitView`, panel order, visibility conditions, signals, and Main
  routing remain unchanged;
- English guide width is 300 logical pixels and Korean guide width is 260 logical
  pixels at the preferred-size level;
- the shortened English candidate action remains catalog-key equivalent with Korean;
- no literal Hangul enters QML and Korean/English catalog key parity remains exact;
- QML loads without warnings or errors in Korean and English, Casual and Pro modes.

Native Windows Qt Quick captures at 1366 x 768 must include:

1. Korean / Casual;
2. Korean / Pro;
3. English / Casual;
4. English / Pro;
5. Korean keyboard focus;
6. English keyboard focus.

Each state is compared with the current work structure and the approved Royal Blue
entry palette in combined evidence. Focused comparisons cover the header and mode
controls, the left guide rail and English action copy, active tabs, primary actions,
and the bottom pipeline. `design-qa.md` must end with exactly
`final result: passed` before handoff.

## Scope Boundaries

Do not change the analysis engine, statistical methods, pipeline schema, import or
report format, settings format, recent-file format, controller command contracts,
panel order, route names, or screen transitions. Do not introduce a new theme mode,
new dependency, network request, generated image, icon, animation, or hidden auto-run
path. Do not redesign the entry screen.
