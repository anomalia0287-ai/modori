# Porcelain Glass UI Redesign Design

## Status

Approved design brief from the owner on 2026-07-06. This document defines the
P0 UI redesign scope before implementation planning.

## Product Context

Modori is a Korean, local-first desktop statistical analysis app for
non-experts. The redesign must make the app feel more credible and commercial
without weakening the current architecture:

- QML remains a thin shell.
- Statistical computation, validation, result formatting, and chart rendering
  remain in Python services.
- Source data remains read-only.
- Data transforms remain explicit replayable pipeline steps.
- QML consumes local image paths for charts and must not own chart drawing.
- No web rewrite, cloud dependency, telemetry, CDN font, or remote asset.

## Visual Sources

Primary reference folder:

`C:\Users\V\Desktop\폴더 검토 및 UI 개선`

Relevant files:

- `Modori Redesign.dc.html`
- `Modori Redesign-print-1y3tng6.dc.html`
- `.thumbnail`
- `uploads\claude-design-packet-2026-07-05\...`

The HTML contains three routes:

- `2a` / Crystal Aurora: expressive glass and aurora visual direction.
- `1a` / Mist Glass: immersive glass surface on a soft aqua background.
- `1b` / Porcelain Glass: restrained white work surface, data-centered layout,
  and report-like result panel.

## Chosen Direction

Use `1b` Porcelain Glass as the implementation baseline and selectively borrow
the entry/import atmosphere from `2a` and `1a`.

The product should not become an aurora-themed decorative app. It should read as
a professional statistics tool with a polished first impression:

- Entry/import can carry stronger glass and aurora atmosphere.
- Work screens should use restrained porcelain surfaces.
- Results should feel like a report preview, not raw console output.
- Transform workflows should visibly preserve source data and append replayable
  steps.

## Considered Approaches

### Approach A: Full Crystal Aurora

Apply the expressive `2a` treatment across the whole product.

Rejected for P0. It has the strongest visual identity, but the always-present
aurora/glass treatment competes with tables, statistical output, and chart
reading. It also increases QML rendering risk if implemented with heavy blur or
animation.

### Approach B: Pure Porcelain Glass

Apply the restrained `1b` treatment everywhere.

Viable but slightly too conservative for the entry flow. It improves credibility
and density, but misses the stronger first impression the owner prefers.

### Approach C: Porcelain Glass With Limited Aurora

Use `1b` for the application shell and analytical surfaces, then apply controlled
aurora/glass atmosphere to the entry screen and import dialog.

Chosen. This balances brand presence, statistical credibility, QML feasibility,
and readability.

## P0 Scope

P0 includes:

1. Entry screen redesign.
2. Import dialog redesign.
3. Work screen shell polish.
4. Guide rail polish.
5. Results panel redesign into a report-preview surface.
6. Transform panel polish focused on source preservation and step creation.
7. Pipeline rail polish focused on replayability and stale-state clarity.
8. Theme token expansion for color, spacing, radius, border, and typography
   constants used by the touched QML surfaces.

P0 excludes:

- Standalone chart builder.
- Interactive native chart drawing in QML.
- New statistical behavior.
- New transform semantics.
- Report export format changes.
- VM release-package replacement.
- Remote fonts or external visual assets.

## Screen Design

### Entry Screen

The entry screen should use the strongest visual treatment in P0:

- Soft teal/aqua background with static aurora-like gradient layers.
- A two-zone card or panel: product promise on one side, start actions on the
  other.
- Guided mode remains the default visible choice.
- Standard mode remains available but secondary.
- Recent files become structured rows instead of raw button text.
- Local-first privacy text remains visible.

Effects must be static and low-cost. Avoid animated blobs, large runtime blur,
or dependencies on remote fonts.

### Import Dialog

The import dialog should feel like a deliberate confirmation step:

- Header with filename and dataset dimensions.
- Preview content structured as a variable summary/table where possible within
  the existing `uiController.importPreviewText` contract.
- Preserve-metadata checkbox remains visible and disabled when the controller
  requires it.
- Confirm/cancel actions stay clear and keyboard-accessible.
- The dialog can use stronger glass styling than the work screen, but must
  remain readable over any overlay.

If the current controller only exposes plain preview text, P0 should improve the
container and typography without inventing parsed data in QML.

### Work Screen Shell

The work screen should move from a dark banner plus raw split panes to a
restrained desktop tool shell:

- Light porcelain background.
- Compact top toolbar with app title, current dataset context, mode segmented
  control, explain/reduce controls, and settings/report actions.
- Guided mode keeps the left rail.
- Standard mode removes the guide rail and allocates width to the central work
  surface.
- Main center surface remains tabbed: data, variables, transforms.
- Right side remains results/report preview.

The shell must preserve existing controller calls and QML component boundaries.

### Guide Rail

The guide rail should read as a recommendation workflow, not a loose list of
buttons:

- A recommendation card with level badge, title, reason, and primary action.
- Secondary controls for other recommendations and manual selection.
- Manual inputs remain visible only when needed.
- Recommendation confidence wording must not imply unsupported statistical
  certainty.

### Results Panel

The results panel is the most important P0 surface.

Target shape:

- Header: `보고서 미리보기`-style title, state badge (`latest`, `stale`,
  `running`, or `error`), and export action.
- Summary: readable Korean prose with restrained line height.
- Table: report-like framed area, still backed by `uiController.resultTableText`
  in P0.
- Chart: local image rendered by Python service, framed and sized as a figure.
- Notes/path information: visible but visually secondary.
- Explain button remains available when explain mode is enabled.

Do not move chart rendering, table parsing, or result interpretation into QML.

### Transform Panel

The transform panel should make safety visible:

- Top note: source data is protected; transforms create new variables and are
  recorded as pipeline steps.
- Reverse coding and scale scoring become clear form sections.
- Primary actions should say they add a step, not that they edit data in place.
- When transforms make results stale, the surrounding shell and pipeline rail
  should make rerun flow obvious.

### Pipeline Rail

The pipeline rail should become a replayability strip:

- Show the current step chain as chips or compact step labels.
- Preserve direct standard-mode controls for reliability, comparison, and
  regression configuration.
- Make `rerun` the visible recovery action when state is stale.
- Avoid implying that transforms edit the original dataset.

## Theme Tokens

Expand `Theme.qml` enough to avoid hardcoding the new visual system across many
files.

Minimum token groups:

- Brand colors: deep teal, action teal, aqua, porcelain, paper, border, muted
  text, warning, danger, transform accent.
- Radius values: small, medium, large.
- Spacing values: xs, sm, md, lg.
- Font sizes for title, section, body, caption.

Tokens should remain simple QML properties. Do not introduce a custom theming
engine.

## Interaction And State Requirements

All existing controls must keep their current behavior:

- Entry mode selection and file open.
- Recent-file open flow.
- Import preview and confirmation.
- Guided recommendation execution.
- Manual analysis selection.
- Standard pipeline configuration.
- Transform commands.
- Rerun.
- Explain popover.
- Word export dialog.

Visible states:

- Empty/imported.
- Ready/latest.
- Running.
- Stale after changes.
- Error.

State styling must support Korean text fit and must not hide errors, stale
warnings, or unsupported-scope messaging.

## Accessibility And Localization

- Keep existing `Accessible.name` coverage for buttons and important inputs.
- Keep user-facing strings in the string catalog where practical.
- Korean text must fit within buttons, tabs, and badges at the current desktop
  size.
- Avoid color-only status indicators; pair badges or labels with color.
- Preserve `reduceEffects` as a real escape hatch for stronger entry/import
  visual effects.

## Verification Plan

Minimum verification for P0 QML visual changes:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
```

If controller bindings, transform behavior, chart paths, or report export are
touched, run the focused tests for those paths and the default quality gate.

Manual visual verification:

- Capture screenshots after each meaningful slice:
  - entry screen;
  - import dialog;
  - guided work/results screen;
  - transform tab;
  - standard mode if touched.
- Compare against the existing screenshot packet and the owner-provided
  reference routes.
- Show the owner screen captures at slice boundaries.

Do not claim release readiness or replace the current package evidence unless a
new package/VM flow is explicitly run.

## Implementation Boundaries

Expected touched areas:

- `src/modori/ui/qml/theme/Theme.qml`
- `src/modori/ui/qml/screens/EntryScreen.qml`
- `src/modori/ui/qml/dialogs/ImportDialog.qml`
- `src/modori/ui/qml/screens/WorkScreen.qml`
- `src/modori/ui/qml/components/GuideRail.qml`
- `src/modori/ui/qml/components/ResultsPanel.qml`
- `src/modori/ui/qml/components/TransformPanel.qml`
- `src/modori/ui/qml/components/PipelineRail.qml`
- string catalog entries only where new user-facing labels are necessary
- focused QML/UI tests where current guards need to recognize the new surfaces

Implementation should not touch Python statistical services unless a QML
contract gap is found and explicitly justified.

## Owner Review Plan

Before implementation, the owner should review this spec and confirm:

- the hybrid Porcelain Glass plus limited Aurora direction;
- the P0 screen scope;
- the plan to show screenshots after each screen-level slice;
- the decision not to alter release-package evidence during normal design
  iteration.
