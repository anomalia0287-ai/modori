# Cream Nacre QML Redesign Design

## Status

Approved by the owner on 2026-07-15. This document supersedes the visual
direction in `2026-07-06-porcelain-glass-ui-redesign-design.md` while keeping
its architectural, privacy, and statistical-integrity constraints.

The design is expected to be calibrated against the running application. The
semantic roles, interaction model, and accessibility requirements are fixed;
individual color, spacing, and opacity values may be adjusted after screenshot
comparison when the implementation proves visually heavier or weaker than the
design intent.

## Objective

Redesign Modori as a coherent cream-toned desktop statistics tool with a subtle
mother-of-pearl material language. The result must be implemented in the real
PySide6/QML application, preserve the current controller bindings, and improve
the novice workflow rather than merely reskinning it.

The redesign must:

- feel calm, trustworthy, and recognizably Modori;
- keep data tables and statistical prose easier to read than the decoration;
- use light or glow only when it communicates state or action;
- replace persistent binary checkboxes with switches;
- reduce the amount of standard-mode configuration visible in guided mode;
- describe transforms as replayable additions, never as in-place source edits;
- produce review evidence from the running application, not generated images.

## Product And Technical Constraints

- QML remains a thin shell over the existing Python services.
- No statistical computation, inference, or result interpretation moves into
  QML.
- Source data remains read-only and transforms remain replayable pipeline steps.
- Existing controller calls and result bindings remain the source of truth.
- The application remains local-first with no telemetry, remote font, CDN, or
  runtime network dependency.
- The design must work at the current 1180 x 760 window and improve gracefully
  with additional width.
- `reduceEffects` remains a real fallback, not merely a different theme label.
- User-visible Korean strings stay in `src/modori/ui/strings.py`.
- Existing accessibility names, keyboard operation, status wording, and error
  visibility must not regress.

## Reference Findings

The implementation borrows principles, not branding or visual assets, from the
following current references:

- [Microsoft Mica guidance](https://learn.microsoft.com/en-us/windows/apps/design/style/mica)
  treats a subtle, mostly opaque material as the long-lived application base.
- [Microsoft Acrylic guidance](https://learn.microsoft.com/en-us/windows/apps/design/style/acrylic)
  reserves stronger translucency for transient or supporting surfaces, warns
  against adjacent acrylic layers, and requires legibility over material.
- [Apple material guidance](https://developer.apple.com/design/human-interface-guidelines/materials)
  uses material to communicate structure and recommends thicker, more opaque
  surfaces for fine text.
- [Qt MultiEffect guidance](https://doc.qt.io/qt-6/qml-qtquick-effects-multieffect.html)
  identifies blur and shadow as the heaviest effects and recommends enabling
  only effects that are needed on optimally sized items.
- [Qt Switch guidance](https://doc.qt.io/qt-6/qml-qtquick-controls-switch.html)
  defines a switch as a two-state control that takes effect immediately, which
  matches explanation and reduced-effects preferences.
- [WCAG 2.2 contrast requirements](https://www.w3.org/TR/WCAG22/)
  require at least 4.5:1 for normal text and 3:1 for large text.
- [jamovi](https://www.jamovi.org/) validates the adjacent spreadsheet and
  results model for an approachable statistics tool.
- [RStudio pane guidance](https://docs.posit.co/ide/user/ide/guide/ui/ui-panes.html)
  validates resizable task panes, while its accessibility guidance supports
  reducing UI complexity and motion for users who need it.

## Considered Approaches

### Approach A: Theme Token Replacement Only

Change `Theme.qml` colors and leave the existing screen composition and default
controls intact.

This is the lowest-risk change, but it would preserve the weak hierarchy, the
large guided-mode pipeline form, and the default Qt appearance. It cannot meet
the usability goal and is rejected.

### Approach B: QML Component And Shell Recomposition

Keep Python contracts and the major screen boundaries, introduce a small set of
reusable QML visual primitives, and recompose the entry, dialogs, work shell,
guide, results, transform, and pipeline surfaces.

This is the chosen approach. It makes the design real and testable while
limiting behavioral risk.

### Approach C: New UI View Models And Full Custom Control System

Add new Python view models for every visual surface and build a complete custom
Qt Quick Controls style.

This could provide the most control, but it expands the regression surface and
is unnecessary for the 1.9 redesign. It is rejected unless implementation
uncovers a specific contract gap that cannot be solved honestly in QML.

## Material Language

### Base Palette

The foundation is warm cream rather than white or grey:

- canvas: warm cream near `#F3EEE5`;
- primary content: near-opaque ivory near `#FBF8F1`;
- raised support surface: muted oat near `#EDE5D9`;
- strong text: deep green-charcoal near `#24332F`;
- body text: muted green-grey near `#485A54`;
- primary action: restrained deep teal near `#196B60`;
- pearl reflections: low-chroma mint, shell pink, and lilac;
- warning: warm amber; error: muted coral red.

Pure white and pure black are avoided. Pearl reflection colors must remain
subordinate to text and data.

### Mother-Of-Pearl Treatment

Mother-of-pearl is a material behavior, not an illustration:

- long-lived surfaces use opaque or near-opaque cream fills;
- a low-opacity, multi-stop reflection appears along one edge or corner;
- mint, shell-pink, and lilac shifts stay within a narrow luminance range;
- large rainbow bands, neon color, animated blobs, and decorative bloom are
  prohibited;
- adjacent panels do not each carry competing reflections;
- one parent surface supplies the ambient reflection and child content panels
  stay quieter.

The first implementation uses QML gradients, borders, and small shadows. It
does not require full-window blur. `MultiEffect` may be used only on a small,
bounded semantic target after measurement proves the simpler treatment
insufficient.

### Semantic Light

Glow is allowed only when it conveys meaning:

- selected navigation or mode: a thin teal edge and restrained inner light;
- primary action ready to run: a focused action halo;
- latest result: a small teal status light or badge edge;
- running: a gentle pulse when effects are enabled, static progress otherwise;
- stale: amber edge and explicit text;
- error: coral edge and explicit text;
- keyboard focus: a high-contrast focus ring.

Neutral cards, body copy, table cells, inactive controls, and decorative
backgrounds do not glow. Reduced-effects mode removes pulse, blur, and bloom
while preserving borders, labels, and contrast.

## Reusable QML Primitives

Introduce only the primitives needed to make the touched screens coherent:

- `PearlSurface`: cream surface, border, optional ambient reflection, and
  reduced-effects fallback;
- `AppButton`: primary, secondary, and quiet variants with shared sizing,
  focus, hover, pressed, disabled, and semantic-light behavior;
- `PreferenceSwitch`: accessible immediate two-state setting control;
- `ModeSegment`: mutually exclusive guided/direct mode selector;
- `StateBadge`: latest, running, stale, error, and neutral result states.

The primitives wrap Qt Quick Controls instead of replacing input semantics with
`MouseArea`-only drawings. Text fields, combo boxes, multi-select checkboxes,
scroll views, and tables retain native keyboard behavior and receive only
targeted visual styling.

## Screen Design

### Entry Screen

- Use a quiet cream shell with one restrained pearl reflection across the
  background.
- Divide the central surface into product context and start actions without
  creating two unrelated card styles.
- Make guided analysis the clear primary start; keep direct analysis secondary.
- Keep `데이터 열기` visible without requiring a mode choice first.
- Render recent files as compact rows using the existing filename-oriented
  model labels, with truncation rather than raw path expansion.
- Replace the duplicate subtitle `모도리` with a useful product sentence.
- Keep the local-first privacy promise visible near the start actions.

### Import Dialog

- Center the dialog as a cream pearl sheet over a quiet scrim.
- Lead with filename and dataset dimensions.
- Keep the table preview visually dominant.
- Group row/header/column corrections under a clearly labeled import-settings
  section, initially compact when the inferred layout is usable.
- Retain checkboxes for independent import choices and column multi-selection.
- Pair disabled settings with a short explanation instead of unexplained grey
  controls.

### Work Shell

- Replace the dark banner with a cream command surface that shares the parent
  pearl reflection.
- Group file actions, result/report actions, and preferences by purpose.
- Use `ModeSegment` for `안내 분석` and `직접 분석`.
- Replace `설명 모드` and `가벼운 모드` checkboxes with
  `PreferenceSwitch` controls labeled `설명` and `시각 효과 줄이기`.
- Retain the current guide / data / results relationship, but use consistent
  spacing, rounded surfaces, and resizable boundaries.
- Keep the data surface visually quiet and more opaque than supporting panes.

### Guided Analysis

- Present one recommendation card with title, level, reason, and primary run
  action.
- Move alternative recommendations and manual selection behind deliberate
  secondary actions.
- Show only fields required by the selected manual analysis.
- Hide the full standard analysis form in guided mode.
- Keep a compact replay strip with the current step chain and `다시 실행`.

### Direct Analysis

- Preserve every supported analysis configuration.
- Replace the always-expanded flow of unrelated fields with analysis selection
  followed by only the fields required for that analysis.
- Keep the step chain visible and make stale recovery explicit.
- Do not auto-run merely because a selection changed.

### Data, Variables, And Transform Tabs

- Use short tab labels: `데이터`, `변수`, `변환`.
- Keep the grid background near-opaque with clear row and column headers.
- Preserve direct visual distinction between source columns and derived data.
- Rename transform actions to describe their safe outcome:
  - `값 정리 단계 추가`;
  - `역코딩 변수 만들기`;
  - `척도 점수 변수 만들기`;
  - `표기 통일 단계 추가`.
- Keep the source-protection statement visible but concise.
- Collapse unsupported or currently unusable transform sections with an
  explanation rather than leaving large disabled forms exposed.

### Results

- Increase the preferred result width while preserving a usable data grid at
  1180 x 760.
- Use a report hierarchy: state and export, summary, result table or figure,
  notes, then file details.
- Keep the current result strings and chart paths as authoritative bindings.
- Give raw text tables horizontal navigation and a wider-detail affordance
  rather than clipping columns inside a narrow fixed frame.
- Rename `왜 이 검정?` to `이 분석을 선택한 이유`.
- Use semantic light only on the status badge and actionable export/rerun
  states.

### Pipeline And Replayability

- Guided mode shows a compact step chain and rerun action only.
- Direct mode shows the selected analysis configuration and its required
  fields, not every analysis form simultaneously.
- Stale state explains that inputs changed and names `다시 실행` as recovery.
- Transform steps and analysis steps remain visibly replayable and do not imply
  source mutation.

### Report Export Dialog

- Use a centered pearl sheet with clear language and section grouping.
- Retain checkboxes for independently includable report sections.
- Use a segmented language choice for Korean and English.
- Disable unavailable result sections with an explanation.
- Keep Word export as the single primary completion action.

## Copy Decisions

The following wording changes are part of the design:

- `안내 모드` -> `안내 분석`;
- `표준 모드` -> `직접 분석`;
- `설명 모드` -> `설명`;
- `가벼운 모드` -> `시각 효과 줄이기`;
- `데이터 창` -> `데이터 넓게 보기`;
- `Word 내보내기` -> `Word로 저장`;
- `왜 이 검정?` -> `이 분석을 선택한 이유`;
- transform labels change as specified in the transform section.

Action labels describe the result of the action. Nouns are used for places;
verbs are used for commands. Statistical certainty is not implied where the
engine supplies only a recommendation.

## State And Data Flow

No new statistical data flow is introduced:

1. Python services expose controller state and models.
2. QML surfaces render those bindings through the new visual primitives.
3. Existing controller slots handle mode, preferences, import, recommendation,
   configuration, rerun, transform, and export actions.
4. Result state selects the corresponding `StateBadge` treatment.
5. `reduceEffects` disables nonessential material effects without changing the
   workflow or information hierarchy.

If a visual requirement needs data that the controller does not expose, the
implementation must either use an honest existing representation or document a
small view-contract addition with a focused test. QML must not parse or infer
statistical meaning.

## Accessibility

- Normal text meets WCAG AA contrast of at least 4.5:1; large text and visual
  component boundaries meet at least 3:1.
- Status is always communicated with text in addition to color or light.
- Controls preserve keyboard focus, activation, and accessible names.
- Persistent preferences use switches; independent multi-selection retains
  checkboxes.
- Touch/click targets aim for at least 40 logical pixels in the primary flow.
- Korean labels are tested at the default window size and with longer dynamic
  content.
- Reduced-effects mode is available from the work shell and remains persisted.

## Verification And Iteration

### Automated

- Add focused tests before each behavior or visual-contract change.
- Run QML string-catalog, visual-token, resource, runtime-load, guided/direct,
  result-state, transform, import, and report-export tests.
- Run the complete `tests/ui` suite after the screen slices pass.
- Run the repository quality gate if Python contracts or packaging resources
  change.

### Running Application

Capture the real application at the default window size for:

1. entry;
2. import preview;
3. guided work before results;
4. guided work with latest results;
5. stale state;
6. direct analysis configuration;
7. transform tab;
8. report export;
9. reduced-effects mode.

Each slice is compared with the previous running-app capture for hierarchy,
Korean fit, clipping, contrast, focus visibility, and material restraint. The
first pass is not assumed to be final. Theme values and layout ratios are tuned
after evidence, while semantic roles and behavior remain stable.

Generated UI images are not design evidence and are not used for owner review.

## Expected Implementation Scope

Primary files:

- `src/modori/ui/qml/theme/Theme.qml`;
- new reusable components under `src/modori/ui/qml/components/`;
- `src/modori/ui/qml/screens/EntryScreen.qml`;
- `src/modori/ui/qml/dialogs/ImportDialog.qml`;
- `src/modori/ui/qml/screens/WorkScreen.qml`;
- `src/modori/ui/qml/components/GuideRail.qml`;
- `src/modori/ui/qml/components/ResultsPanel.qml`;
- `src/modori/ui/qml/components/TransformPanel.qml`;
- `src/modori/ui/qml/components/PipelineRail.qml`;
- `src/modori/ui/qml/dialogs/ReportExportDialog.qml`;
- `src/modori/ui/strings.py`;
- focused tests under `tests/ui/`.

Python UI contracts are changed only when a verified QML contract gap blocks an
approved behavior. Statistical engine modules, report calculations, release
package evidence, and remote dependencies are outside this redesign.

## Completion Criteria

The design slice is complete when:

- the real application exhibits one coherent cream-nacre material language;
- no generated mockup is presented as implementation evidence;
- guided mode no longer exposes the complete direct-analysis form;
- persistent preferences are switches and multi-select choices remain
  checkboxes;
- result tables can be inspected without silent clipping;
- transform labels state their safe outcome;
- semantic light is limited to meaningful state and action;
- reduced-effects mode provides a visually coherent static fallback;
- focused and full UI tests pass;
- the owner has reviewed running-app captures and requested no remaining
  blocking visual correction.
