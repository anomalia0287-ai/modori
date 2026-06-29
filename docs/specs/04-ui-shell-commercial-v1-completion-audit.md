# Modori UI Shell #04 Commercial v1 Completion Audit

Status: **COMPLETE for the repository-local #04 commercial-ready v1 implementation gate**.

Claim boundary: this is not a signed release or installer certification. Clean Windows VM
installation, visible manual desktop walkthrough, low-GPU usability, and distribution
packaging remain release QA items. They are not represented as automated proof.

## Final verified evidence

- QML launcher loads the packaged QML root in offscreen reduce-effects mode:
  `qml-load-ok`.
- Compile check passed: `python -m compileall -q src tests`.
- Full pytest run 1 passed: `267 passed, 2 skipped`.
- Full pytest run 2 passed: `267 passed, 2 skipped`.
- `tongtong` residue scan over `src`, `tests`, and `pyproject.toml`: no matches.
- Legacy QWidget launcher scan over production UI/app code: no matches.
- UI network/remote asset scan: no matches.
- UI direct variable mutation scan: no matches.

## Post-gate internal quality hardening evidence

This section records structural hardening after the repository-local commercial-v1
gate. It does not expand the release claim boundary and does not replace release QA.

- Pipeline metadata-step insertion is now transactional: insert-and-recompute either
  commits topology, caches, dataset, analyses, and step results together or restores
  the previous state.
- Metadata-only writes are included in pipeline write ownership checks without
  conflating column writes and variable-metadata writes.
- UI metadata patch naming is reconciled at the boundary: `missing_codes` remains the
  UI-facing name and is mapped explicitly to engine `missing_values`; ambiguous alias
  input and unsupported `display_type` patches are rejected rather than ignored.
- Controller internals were split into focused collaborators for command validation,
  import preview, explanation formatting, and result binding while preserving the
  existing QML-facing API.
- UI tests no longer write controller private fields; worker substitution uses an
  explicit constructor seam.
- Settings-backed session state for reduce-effects and recent files is delegated to a
  focused `UiSessionState` collaborator while preserving controller properties and QML
  slots.
- Static user-visible QML strings are routed through the `UI_STRINGS_KO` catalog via
  `appBootstrap.text(...)`; raw `text`/`placeholderText`/`title`/`Accessible.name` and
  `qsTr(...)` literals are guarded against regression.
- Reliability/comparison/regression selection routing is delegated to
  `AnalysisSelectionCommandBuilder`; the controller now adapts QML calls to command
  execution rather than owning the full validation/routing logic.
- Additional controller hardening split the remaining UI-shell responsibilities into
  focused collaborators for pipeline operations, result state, import flow, report
  export, run tracking, metadata editing, analysis editing, pipeline state, explanation
  lookup, data-session loading, service composition, and explicit service contracts.
- Post-hardening verification:
  - Compile check passed: `python -m compileall -q src tests`.
  - Intermediate full pytest run 1 passed: `284 passed, 2 skipped`.
  - Intermediate full pytest run 2 passed: `284 passed, 2 skipped`.
  - Latest full pytest run 1 passed: `334 passed, 2 skipped`.
  - Latest full pytest run 2 passed: `334 passed, 2 skipped`.
  - `tongtong` residue scan over `src`, `tests`, and `pyproject.toml`: no matches.
  - Legacy QWidget launcher scan over production UI/app code: no matches.
  - UI network/remote asset scan: no matches.
  - UI private-test-coupling scan over `tests/ui`: no matches.
  - Raw QML user-visible string scan: no matches.
  - Controller dead command-helper scan: no matches.
  - Controller internal-responsibility residue scans: no matches for pipeline internals,
    individual service fields, scattered result state, import/run bookkeeping,
    metadata/analysis internals, pipeline state fields, library resolution, or
    data-session loading policy.
  - Explicit service-contract scan: no `pipeline_ops: object` seams remain in the
    pipeline-bound UI services.

Remaining internal-quality work is tracked separately from this completion audit:
release-environment QA is not claimed as complete here.

## Requirement audit

| Area | Status | Evidence / scope boundary |
| --- | --- | --- |
| Thin-shell no-statistics boundary | Satisfied | UI AST guards reject forbidden statistics imports/reduction calls; UI renders engine DTO strings rather than computing numbers. |
| QML launcher / package resources | Satisfied | `modori.app:main` launches `QGuiApplication`/`QQmlApplicationEngine`; QML root resolves by package resource path. |
| Worker queue, `run_id`, stale discard | Satisfied | Serialized worker and stale-result discard tests are green. |
| Data table virtualization | Satisfied for v1 | `TableView` + `QAbstractTableModel` + lazy `TableProvider`; no full cell matrix materialization. |
| Raw dataframe boundary | Satisfied | QML/model layer uses `TableProvider`; UI has no pandas/statistics imports. |
| Import dialog and preview | Satisfied for v1 | Controller preview lists cases, variables, inferred measures, labels/missing indicators; QML never parses files. |
| `.sav` metadata preservation | Satisfied through engine binding | Engine `ImportStep` preserves pyreadstat labels/value labels/user-missing codes; UI preview surfaces metadata summaries. |
| Recent files | Satisfied for v1 | Settings-backed local recent files with opt-out and clearing; no dataset contents stored. |
| Data-cell editing policy | Satisfied by explicit v1 read-only scope | UI discloses read-only direct cell editing until a reproducible DataCellStep exists; no out-of-pipeline mutation. |
| Variable view display | Satisfied | Variable model exposes key, label, measure, value labels, missing codes, and type. |
| Variable metadata edit rule | Satisfied for measure edits | `VariableMetadataPatchStep` performs metadata-only Step-backed edits; UI/controller do not mutate dataset variables directly. |
| Metadata edit transactionality | Satisfied after post-gate hardening | New regression tests prove failed inserted metadata edits restore pipeline topology and version state; duplicate metadata writers are rejected. |
| Metadata patch naming boundary | Satisfied after post-gate hardening | `missing_codes` maps to engine `missing_values`; ambiguous aliases and unsupported display-type edits fail explicitly. |
| Step parameter editing | Satisfied for v1 analysis selections | Reliability/comparison/regression selection APIs edit existing engine Steps with validated variable keys and preserve existing policies. |
| Pipeline rail | Satisfied for v1 | Step chain, rerun anchor, reliability/comparison standard controls, and controller-backed edits are wired. |
| Guided mode | Satisfied for supported v1 analyses | Guided intent flow commits reliability/comparison selections through controller Step edits; regression is explicit and fails clearly if the current pipeline has no regression Step. |
| Standard mode | Satisfied for supported v1 analyses | Standard rail controls use the same controller Step-edit APIs as guided mode. |
| Mode switching exposure-only | Satisfied | Mode switching tests prove Steps are unchanged. |
| Results panel prose/table | Satisfied | Display DTOs use `table_for` and `prose_for`; QML renders strings as-is. |
| Chart display and lifecycle | Satisfied for v1 | Existing chart files are rendered via local `file:` URL; missing files surface notes; obsolete generated chart files are cleaned only under the app cache. |
| Report export | Satisfied | Export delegates to engine/report path, verifies output existence, surfaces failures, and exposes language/include/figure options. |
| 설명 mode / knowledge library | Satisfied | Controller resolves local library keys only; rich popover includes layered fields and reference verification status. |
| UI-rendered vocabulary coverage | Satisfied for current surfaces | UI help-key tests resolve registered explainable labels through the seed-complete knowledge library. |
| Reduce-effects mode | Satisfied for v1 | Environment-forced startup, controller toggle, settings persistence, and QML binding are covered. |
| Accessibility minimum | Satisfied for core controls | Core buttons/fields have Korean accessible names; full assistive-technology certification remains release QA. |
| Privacy/network | Satisfied for repo-local runtime | No production UI network imports, remote QML URLs, telemetry, or remote assets were found. |
| End-to-end smoke | Satisfied for repository-local automation | Import, confirmation, rerun, data/variable models, results, explanation, report export, stale/error, and QML load are covered. |
| UI internal responsibility split | Satisfied after post-gate hardening | Command validation, import preview, report export, run tracking, metadata editing, analysis selection, pipeline state, data-session loading, library resolution, result binding, and service composition are delegated to focused modules; the public QML API remains stable. |
| UI session/settings boundary | Improved after post-gate hardening | Reduce-effects and recent-file state are delegated to `UiSessionState`; controller properties/slots remain stable. |
| QML string catalog boundary | Satisfied after post-gate hardening | Static QML chrome strings are catalog-backed and guarded against raw literal regression. |
| Analysis command routing boundary | Satisfied after post-gate hardening | Reliability/comparison/regression selection routing and Step edit application are delegated to focused command/editor collaborators; controller keeps QML adapter responsibility. |
| UI test contract focus | Improved after post-gate hardening | `tests/ui` no longer writes controller private fields; tests assert observable state transitions and DTO-backed outputs. |

## Remaining release QA items, not implementation blockers

1. Visible manual desktop walkthrough on the target Windows machine.
2. Clean Windows VM install and launch from outside the repository checkout.
3. Installer/signing/packaging validation.
4. Manual low-GPU/old-PC usability check.
5. Future direct data-cell editing only after a reproducible DataCellStep is specified and implemented.

## Final verdict

The repository-local #04 UI Shell implementation now meets the commercial-ready v1
contract for the approved v1 scope: thin shell, local-only runtime, Step-backed edits,
lazy data/variable views, guided/standard analysis selection, engine-bound results and
reports, local knowledge-library explanations, reduce-effects support, stale/error
handling, and privacy/security guards. The remaining items are release QA rather than
known implementation gaps in this repository.
