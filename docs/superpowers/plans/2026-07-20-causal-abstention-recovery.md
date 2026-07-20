# Causal Abstention Recovery Implementation Plan

**Date:** 2026-07-20
**Active P0:** U-05 only
**Branch:** `codex/research-os-functional-usability`
**Release boundary:** no push, merge, default change, or frozen artifact replacement

## Goal

Turn the currently generic causal abstention into a reasoned, recoverable decision.
The UI must project the typed reason from the committed passport and offer an explicit
non-causal reframe without silently changing research intent, inventing a candidate,
or weakening the causal-support boundary.

## Current evidence

- A committed abstention passport already contains `reason_codes` and
  `recovery_requirement_ids`.
- The observed causal path is sealed as `unsupported_causal_target` with
  `declare_noncausal_or_use_external_causal_workflow`.
- `present_durable_record` currently discards both fields and renders one generic
  abstention title/body.
- Every abstention currently receives only the generic `replan` primary action.
- `replan` correctly starts a fresh task and returns to causal-intent intake, but it
  does not offer the direct, explicit non-causal recovery the user needs.
- The existing manual-analysis surface stays separate from Research OS and never runs
  automatically.

## Fixed interaction contract

### Typed reason

The causal abstention title and body state that a causal-effect interpretation is
outside the current Research OS scope. A dedicated reason surface is derived only
from the committed `AbstainPayload`.

- Guided Mode shows a localized reason label.
- Pro Mode may additionally show the stable reason code and recovery requirement ID.
- Unknown or non-causal abstention reasons remain fail-closed and use a sanitized
  generic category. They never inherit the causal reframe action.

### Explicit recovery choices

For an exact committed `unsupported_causal_target` abstention:

- primary: `인과 효과 대신 변수 간 관계 확인` /
  `Explore a relationship instead of a causal effect`;
- secondary: the existing fresh replan action, which lets the user reconsider the
  causal-intent question;
- direct/manual analysis remains available as the separate secondary product path.

Choosing the primary action starts a fresh replan task and moves to the six supported
non-causal task profiles. It does not mutate or retract the prior causal abstention.
The explicit click is the user's non-causal declaration; the eventual new passport
records `causal_intent=noncausal` when the selected profile and roles are committed.
No candidate appears before that separate commit.

If the user keeps causal intent, the abstention remains valid. Modori does not relabel
the request or issue a non-causal candidate automatically.

## Non-negotiable preservation assertions

1. The causal abstention remains committed and immutable in its original task.
2. The reframe command is available only when the current durable passport contains
   exactly the supported causal abstention reason and recovery requirement.
3. A spoofed QML command, generic abstention, integrity abstention, stale record, or
   busy controller cannot enter the non-causal profile flow.
4. Fresh replan keeps dataset/pipeline identity checks and session-store recovery.
5. Candidate display remains commit-before-display.
6. Reframing never prepares, confirms, or runs an analysis.
7. Guided and Pro views retain identical recovery authority; Pro exposes only more
   diagnostic detail.
8. No generative model, network path, telemetry, or external causal workflow is added.

## Task 1: Freeze presenter and copy contracts (RED)

Modify:

- `tests/ui/test_research_flow_presenter.py`
- `tests/ui/test_qml_string_catalog.py`

Assertions:

- the causal abstention copy names the causal-support reason;
- the primary command is a new closed `reframe_noncausal` command;
- fresh replan remains secondary;
- the reason rows are bound to the committed passport payload;
- Guided and Pro actions are identical while Pro may expose stable IDs;
- a non-causal or unmapped abstention receives no reframe command.

Run the focused tests and retain the expected failures before implementation.

## Task 2: Project the committed abstention payload

Modify:

- `src/modori/ui/research_flow_presenter.py`
- `src/modori/ui/strings.py`
- `src/modori/ui/strings_en.py`

Actions:

- add `ResearchUiCommand.REFRAME_NONCAUSAL` and its bilingual action copy;
- validate and project `AbstainPayload` reason/recovery values;
- use causal-specific title/body/badge only for the exact causal reason;
- produce localized reason rows for Guided Mode and bounded stable-ID detail for Pro;
- retain sanitized generic abstention copy and ordinary replan for every other reason.

## Task 3: Implement a provenance-preserving reframe transition

Modify:

- `src/modori/ui/research_flow_controller.py`
- `tests/ui/test_research_flow_controller.py`

Actions:

- add a closed runtime `reframe_noncausal` operation;
- revalidate the current durable passport before any session mutation;
- reuse the existing fresh fingerprint, pipeline-current, and `start_replan`
  boundaries;
- make the prior task read-only and return `INTAKE_PROFILE`, not a candidate;
- expose a controller slot only from causal `ABSTAIN_READY` with the presenter-issued
  command;
- preserve existing typed error and cancellation behavior.

The runtime does not commit a replacement intent on its own. The later ordinary P1
profile commit creates the new non-causal passport, keeping the lineage explicit.

## Task 4: Render the reason and route the action

Modify:

- `src/modori/ui/qml/components/ResearchFlowPanel.qml`
- `tests/ui/test_research_flow_qml.py`
- `tests/fixtures/research_flow_visual_states.json`
- `tests/ui/test_research_flow_visual_gallery.py`

Actions:

- render a compact, accessible abstention-reason surface from `evidenceRows`;
- route `reframe_noncausal` only to the new controller slot;
- keep the generic action renderer and separate manual-analysis surface;
- update the synthetic causal-abstention fixture and its expected regions;
- reject overflow, missing copy, or misleading generic-only recovery in the visual
  contract.

## Task 5: Verify U-05 and transition the ledger

Run:

1. focused presenter/controller/QML RED-to-GREEN tests;
2. Research OS service, passport, transition, task-session, controller, presenter,
   QML, end-to-end, preparation, and provenance regressions;
3. Ruff, compileall, and `git diff --check`;
4. the complete non-gallery UI suite with workspace-local `--basetemp`;
5. the complete production-Windows visual gallery on a clean commit;
6. an actual causal-intent to abstention to non-causal-profile transition audit.

Close U-05 only if the displayed reason is passport-backed, the reframe action cannot
be spoofed onto another abstention, the prior record remains immutable, no candidate
appears before a new commit, and the Windows render is readable. Otherwise leave U-05
active and record the exact missing evidence.
