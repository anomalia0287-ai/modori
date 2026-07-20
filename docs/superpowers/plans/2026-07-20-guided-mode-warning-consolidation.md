# Guided Mode Warning Consolidation Implementation Plan

**Date:** 2026-07-20
**Active P0:** U-04 only
**Branch:** `codex/research-os-functional-usability`
**Release boundary:** no push, merge, default change, or frozen artifact replacement

## Goal

Present the experimental guidance contract once at entry and retain one quiet status in
the open research rail. Replace repeated candidate/preparation warnings with
stage-specific instructions without changing provenance, confirmation, or execution
authority.

## Current evidence

- Entry currently combines an `실험적 후보` badge with a second sentence saying that
  nothing runs automatically.
- `GuideRail.qml` contains an experimental status header, but that header is currently
  hidden.
- The legacy candidate section repeats another experimental/no-auto sentence.
- A ready Research OS candidate repeats the experimental badge in the panel header and
  candidate card, then renders another no-auto sentence.
- Preparation repeats an experimental badge and no-auto sentence while its settings
  rows also expose `experimental=true` and `automatic_run=false` as though they were
  engine parameters.
- Work-shell and action accessibility descriptions reuse the warning sentence.
- Assisted report provenance is a separate evidence boundary and must remain unchanged.

## Fixed copy and interaction contract

### Entry disclosure

The Guided Mode description is benefit first, followed by one compact disclosure:

```text
연구 질문과 데이터 구조를 따라 분석 후보와 필요한 확인을 단계별로 안내합니다.
실험적 연구 가이드 · 설정과 실행은 직접 확인
```

```text
Follow guided steps from your research question and data structure to a reviewable analysis candidate.
Experimental research guide · You review the setup and start the run
```

The separate entry badge is removed. Selecting the card still changes only the mode;
opening data remains a separate action.

### Persistent status

The open research rail shows exactly one quiet status above its scrollable contents:
`실험적 가이드` / `Experimental guide`. It is present in Guided Mode and when the
same Research OS rail is explicitly opened from Pro Mode. It does not obscure or
replace state badges such as clarification, failure, or abstention.

### Candidate and preparation

- Candidate state badge: `후보 준비됨` / `Candidate ready`.
- Candidate instruction: `다음 단계에서 변수 역할과 설정을 검토합니다.` /
  `Next, review variable roles and settings.`
- Preparation state badge: `설정 검토` / `Setup review`.
- Confirmed state badge: `설정 확인됨` / `Setup confirmed`.
- Confirmation accessibility description: `표시된 설정만 확인합니다.` /
  `Confirms only the displayed setup.`
- The existing post-confirmation instruction that Run is separate remains visible.
- `experimental` and `automatic_run` remain immutable preparation properties and test
  assertions, but are not presented as engine setting rows.

## Non-negotiable preservation assertions

1. Internal mode values remain `guided` and `standard`.
2. Candidate display remains commit-before-display.
3. Selecting, viewing, or preparing a candidate does not run an analysis.
4. Exact configuration confirmation and Run remain separate commands.
5. Assisted selection provenance remains `experimental_candidate_assisted`.
6. Word reports retain the localized assisted-selection disclosure.
7. Guided and standard views retain equivalent state and decision authority.

## Task 1: Freeze warning-placement and copy tests (RED)

Modify:

- `tests/ui/test_qml_string_catalog.py`
- `tests/ui/test_mode_action_surfaces.py`
- `tests/ui/test_royal_blue_entry_screen.py`
- `tests/ui/test_research_flow_presenter.py`
- `tests/ui/test_research_flow_qml.py`
- `tests/ui/test_research_preparation_editor.py`
- `tests/ui/test_qml_runtime_load.py`

Assertions:

- exact Korean and English entry/status/stage copy;
- one `guide.experimental_status` binding in `GuideRail.qml`;
- no entry badge binding and no legacy experimental-status binding;
- no experimental/no-auto binding inside candidate or preparation cards;
- the offscreen runtime finds one visible `guidedExperimentalStatus` object;
- review rows contain exact engine/role settings but not the two guidance-control flags;
- the sealed preparation still has `experimental is True` and
  `requires_explicit_configure_confirm_run is True`;
- report/provenance and separate-Run tests remain unchanged.

Run the focused tests and record the expected failures before implementation.

## Task 2: Implement the copy catalog and presenter projection

Modify:

- `src/modori/ui/strings.py`
- `src/modori/ui/strings_en.py`
- `src/modori/ui/research_flow_presenter.py`

Actions:

- apply the fixed entry and persistent-status copy;
- replace candidate experimental-warning keys with ready-state and next-step keys;
- add preparation review/confirmed state labels and action-specific accessibility copy;
- remove catalog keys that no longer have a QML consumer;
- leave report-export disclosure constants untouched.

## Task 3: Consolidate the visible QML surfaces

Modify:

- `src/modori/ui/qml/screens/EntryScreen.qml`
- `src/modori/ui/qml/screens/WorkScreen.qml`
- `src/modori/ui/qml/components/GuideRail.qml`
- `src/modori/ui/qml/components/ResearchFlowPanel.qml`
- `src/modori/ui/qml/components/ResearchCandidateCard.qml`

Actions:

- remove the entry badge binding;
- expose one quiet `guidedExperimentalStatus` above the guide scroll and anchor the
  scroll below it;
- remove the legacy warning label;
- keep only the panel state badge, removing the candidate-card duplicate;
- remove the preparation warning row and derive preparation/confirmed state labels in
  the panel header;
- use action-specific accessibility descriptions instead of the global warning.

## Task 4: Keep guidance controls out of engine-setting rows

Modify:

- `src/modori/ui/research_preparation_editor.py`
- `tests/ui/test_research_preparation_editor.py`

Return only canonical step/role parameters from `_settings_rows`. Do not alter the
sealed `PassportBoundPreparation` flags, digest validation, preflight validation,
commit transaction, or separate-run behavior.

## Task 5: Verify U-04 and transition the ledger

Run:

1. the focused warning/copy/runtime/preparation tests;
2. guided/standard authority, recommendation, preparation, pipeline, report-export,
   and end-to-end UI regression files;
3. Ruff, compileall, `git diff --check`, and a source scan for the retired repeated
   warning bindings;
4. the complete non-gallery UI suite with a workspace-local `--basetemp`;
5. an actual current-source render inspection at entry, candidate, preparation review,
   and confirmed states.

Close U-04 only if the runtime shows one persistent status, the repeated warning
surfaces are absent, all preservation assertions pass, and the render remains readable.
Otherwise leave U-04 active and record the exact missing evidence.
