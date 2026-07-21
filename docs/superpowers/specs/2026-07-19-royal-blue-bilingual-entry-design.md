# Royal Blue Bilingual Entry Design

Date: 2026-07-19

Status: owner-approved with the session-wide localization condition on 2026-07-19.

## Objective

Recompose Modori's existing entry screen around the supplied structural reference while
preserving the current mode, file-open, recent-file, settings, and routing contracts.
The change is a presentation and session-local localization slice. It does not change
analysis algorithms, step schemas, project files, report files, or persisted settings.

## Source Of Truth And Precedence

The structural source is:

`C:/Users/V/AppData/Local/Temp/codex-clipboard-ed3874a9-fc06-4177-8451-abf62b4c69c3.png`

The reference controls the two-column composition, information order, density, stacked
mode cards, primary file action, and recent-file grouping. The owner's written
constraints override the reference's green palette and fabricated file metadata.
Decorative circles, the floating edit control, and any sample row/column/time metadata
are not part of the implementation target.

## Chosen Approach

Use the existing QML shell, controller signals, theme object, button vocabulary, and
settings dialog. Recompose only `EntryScreen.qml` and the entry-specific mode-card
presentation. Introduce a session-local language property in `AppBootstrap`; the entry
screen owns the only language control, while the selected language is observed by all
QML text bindings and UI presenters for the remainder of the process lifetime.

Two rejected alternatives are recorded for clarity:

1. Persisting the language in `ui-settings.json` was rejected because the settings
   storage format must remain unchanged.
2. Translating only the entry screen was rejected because work screens, dialogs,
   errors, result presentation, and accessibility copy must follow the same session
   language.

## Visual System

All new colors are named theme roles rather than component literals:

- entry brand field: `#173B7A`;
- entry canvas: `#F7F3EA`;
- entry card: `#FFFDF8`;
- entry primary and selected state: `#2F5DA8`;
- entry body text: `#17233A`.

The left region occupies 37% of the available width at the 1366 x 768 acceptance
viewport. It is full-height and contains the Modori wordmark, concise product promise,
local-data statement, and existing open-source/local footer. The right region is
full-height ivory. Its content column is width-bounded and vertically centered enough
to retain the reference's calm whitespace without turning the content into a floating
card.

The right-side order is:

1. session language control and existing settings action;
2. localized start heading;
3. Casual mode card;
4. Pro mode card;
5. one full-width data-file action;
6. recent-file heading and list when real recent files exist.

Recent rows display only the controller's existing labels, which contain a real file
name and only add a real compact parent hint when duplicate names require
disambiguation. The UI does not infer or invent dimensions, timestamps, or file
contents.

## Mode And Recommendation Boundary

The existing routing remains unchanged:

- Casual invokes `guidedRequested()` and enters the guided work surface only after the
  explicit user action;
- Pro invokes `standardRequested()` and enters the manual work surface;
- data open invokes `openDataRequested()`;
- a recent item invokes `recentFileRequested(index)`;
- settings invokes `settingsRequested()`.

Casual remains an experimental candidate aid. Its Korean and English descriptions both
state that candidates are experimental and that nothing runs automatically. No text
claims recommendation accuracy, validation, confidence, or expert equivalence.

Mode cards are equal in size and hierarchy. Selection is communicated through all of:

- a two-pixel primary border;
- a selected background token distinct from the unselected card;
- a real check icon and localized selected-state accessible description.

Hover and keyboard focus add a visible focus treatment without changing the card's
size. Color alone is never the sole selected-state cue.

## Session-Local Localization Contract

`AppBootstrap` owns a non-persisted `language` property with allowed values `ko` and
`en`, a `languageChanged` signal, and a validated `setLanguage(language)` slot. The
default is Korean on each launch. The existing one-argument `text(key)` API remains
available. QML uses a language-observing lookup so bindings are reevaluated immediately
when the property changes.

`UI_STRINGS_KO` and `UI_STRINGS_EN` must have exactly equal keys. The English catalog
must cover every static QML label, placeholder, dialog title, tooltip, and accessibility
name currently covered by the Korean catalog.

Session language also reaches dynamic UI presentation:

- controller success and error messages are localized by stable UI message keys or
  existing error codes without altering `CommandResult` storage contracts;
- result summaries and tables select the existing bilingual `DisplayResult` and
  `DisplayTable` fields;
- recommendation titles and deterministic reasons receive UI-only English
  presentation derived from the existing candidate kind and observed variable fields;
- import preview headings, inferred-role labels, measure labels, and missing-value
  labels are formatted in the selected language;
- variable-table headers and measure labels follow the selected language;
- user data, variable names, file names, file paths, cell values, and generated
  numerical values remain untouched.

The language state is never written to `UiSettingsStore` and adds no field to
`DEFAULT_SETTINGS` or saved JSON.

## Accessibility And Keyboard Contract

The language choices and mode cards use semantic radio-button roles with checked state.
The settings action retains its button role. The primary file action and every recent
row remain reachable by Tab. Focus order follows visible reading order. Every focused
control has a visible two-pixel outline with adequate contrast against its surface.
Accessible names and state descriptions use the active session language.

The layout must remain usable when English strings wrap at 1366 x 768 and at the
project's existing minimum supported window size. Reduced-effects mode keeps the same
information and state cues.

## Verification Contract

Automated tests must cover:

- exact palette tokens and 37/63 entry split;
- preserved entry signals and Main routing;
- one file-open action and real recent-file labels only;
- selected mode border, background, check marker, and accessible checked state;
- `ko` default, validated `ko`/`en` transitions, and rejection of unknown values;
- Korean/English key equality and full QML catalog use;
- reactive QML updates after a live language change;
- work-screen, dialog, error, result-presenter, recommendation, import-preview,
  variable-table, and accessibility localization;
- no language field in settings defaults or serialized settings.

Native QML captures at 1366 x 768 must include:

1. Korean / Casual selected;
2. Korean / Pro selected;
3. English / Casual selected;
4. English / Pro selected;
5. Korean keyboard focus;
6. English keyboard focus.

Each capture is compared with the structural reference in one combined comparison
image. The written palette and truthful-data constraints are intentional deviations.
The project-root `design-qa.md` is updated through the comparison loop and must end with
exactly `final result: passed` before handoff.

## Scope Boundaries

No analysis engine, statistical algorithm, step schema, cache key, project format,
report format, recent-file storage format, or settings storage format changes are
allowed. No new route, recommendation behavior, auto-run path, network dependency,
image asset, or fabricated recent-file metadata is added.
