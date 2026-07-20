# Research Flow Failure Recovery Implementation Plan

**Date:** 2026-07-20
**Active P0:** U-06 only
**Baseline:** `4ed738d` on `codex/research-os-functional-usability`
**Release boundary:** branch-only; no push, merge, default change, or frozen artifact replacement

## Goal

Replace the generic Research OS failure dead end with a closed, sanitized explanation
and a recovery action that the controller can actually perform. Preserve the existing
error taxonomy, local-only processing, commit-before-display, abstention, explicit
Prepare/Confirm/Run, and fail-closed integrity behavior.

## Confirmed audit

- `ResearchFlowRuntime._typed_error()` maps exceptions to four visible states but
  discards the reason before presentation.
- `PreflightResult` retains closed issue codes, while the failure presenter drops
  them and always offers `RESUME`; deterministic invalid or unsupported preparation
  therefore loops through the same result.
- an unexpected worker result and preparation-review exception both become the same
  detail-free `FAILURE` view.
- `ResearchFlowPanel.qml` has an evidence surface for abstention but no equivalent
  failure/recovery surface.
- the transient corruption presenter emits `BACK`, but
  `ResearchFlowController.back()` rejects `CORRUPTION`; the visible action is dead.
- exception text can contain internal identifiers or paths, so raw exception strings
  cannot become UI copy.

The exact exception behind the user's captured failure screen is unverified because
the production-safe worker intentionally does not retain raw exceptions unless local
debug logging was enabled.

## External usability evidence

- Nielsen Norman Group's error-recovery heuristic requires plain language, a precise
  problem statement, and a constructive solution:
  <https://media.nngroup.com/media/articles/attachments/Heuristic_Summary_Letter_compressed.pdf>
- a workflow-analysis usability study found that raw Python-style errors and unclear
  error-versus-warning presentation forced facilitator intervention:
  <https://f1000research.com/articles/11-192/v1>
- JASP maintains a consistent reviewed error catalog so users can transfer recovery
  knowledge across analyses:
  <https://github.com/jasp-stats/jasp-desktop/wiki/List-of-Error-Messages>

These sources support a small closed catalog. They do not justify exposing arbitrary
engine exception text or adding a model-generated explanation layer.

## Closed design

### Sanitized reason contract

Add a presentation-only `ResearchFailureReason` enum. Production paths map only from
known exception classes, preflight issue codes, and controller stages. No raw message,
path, traceback, variable value, or source filename enters the state model.

Required reason families:

1. current data/import context unavailable;
2. dataset fingerprint unavailable within the local deadline;
3. local record unavailable;
4. local record changed or writer conflict;
5. local record integrity failure;
6. request verification failure;
7. unsupported, invalid, or failed execution preflight;
8. preparation review failure;
9. unexpected serialized-worker failure.

Guided Mode shows localized reason and next step. Pro Mode adds one stable bounded
reason ID. Both modes retain identical state and command authority.

### State-valid recovery matrix

| Reason | State | Command | Meaning |
| --- | --- | --- | --- |
| current data/import context | `failure` | `resume` | reread the current data and last verified record |
| fingerprint deadline | `memory_unavailable` | `resume` | retry the local identity check |
| local record unavailable | `memory_unavailable` | `resume` | reopen the local record |
| changed record or writer conflict | `replan_required` | `replan` | start a fresh explicit task from current data |
| integrity failure | `corruption` | `back` | leave the unsafe record for the safe start surface |
| request verification | `failure` | `resume` | return to the last verified durable state |
| preflight unsupported/invalid/failure | `failure` | `replan` | do not loop the same sealed preparation |
| preparation review | `failure` | `resume` | reload the last verified candidate |
| unexpected worker failure | `failure` | `resume` | reload rather than pretending the operation committed |

`replan` from `failure` is accepted only when the displayed primary action is the
closed `REPLAN` command. `back` from corruption performs no ledger or pipeline write.

### Visual surface

Add one compact accessible `researchFailureRecovery` surface for `failure`,
`memory_unavailable`, `corruption`, and `replan_required` when reason rows exist. It
shows `What happened` and `Next step`; Pro additionally shows `Reason ID`. Reuse the
Royal Blue/Aurora component system and `Text.Wrap`. Do not redesign the panel.

## TDD tasks

### Task 1: Presenter contract

Files:

- `src/modori/ui/research_flow_presenter.py`
- `src/modori/ui/strings.py`
- `src/modori/ui/strings_en.py`
- `tests/ui/test_research_flow_presenter.py`
- `tests/ui/test_qml_string_catalog.py`

Write failing tests for every reason/state/action mapping, Guided versus Pro evidence,
invalid reason/state combinations, bounded identifiers, and deterministic preflight
replan. Implement the smallest closed mapping.

### Task 2: Runtime and controller provenance

Files:

- `src/modori/ui/research_flow_controller.py`
- `tests/ui/test_research_flow_controller.py`

Write failing tests proving known exception classes map to the intended reason without
including exception text, worker/preparation failures retain a sanitized stage, a
preflight failure offers a working replan, and corruption's visible Back action is
accepted without mutating pipeline or ledger state.

### Task 3: QML and visual fixture

Files:

- `src/modori/ui/qml/components/ResearchFlowPanel.qml`
- `tests/ui/test_research_flow_qml.py`
- `tests/ui/test_qml_visual_contract.py`
- `tests/fixtures/research_flow_visual_states.json`
- `tests/ui/test_research_flow_visual_gallery.py`

Write failing runtime and source-contract tests for the accessible failure surface,
wrapped copy, real action dispatch, and minimum-width/1.5x readability. Update the
existing failure fixture; do not add unrelated visual directions.

### Task 4: Verification and independent review

Run focused RED-to-GREEN tests, affected full files, core Research OS tests, Ruff,
compileall, `git diff --check`, the complete non-gallery UI suite, and the clean-commit
production-Windows gallery. Inspect the actual failure images. Request a read-only
independent review of privacy, taxonomy, recovery reachability, and authority
preservation.

Close U-06 only when every production failure path shows a sanitized reason, the
displayed action succeeds from that state, deterministic preflight failures no longer
loop through Resume, and no raw diagnostic or false corruption claim reaches QML.

