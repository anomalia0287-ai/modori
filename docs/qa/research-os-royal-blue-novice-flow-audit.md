# Research OS Royal Blue Novice Flow Audit

Date: 2026-07-19

Branch: `codex/research-os-functional-usability`

Integrated baseline: `217730e`, functional commit
`ed8bcae6f7452d2713865afc3ebfa98508d3b65b`, and cleanup commit
`17815ef617c480486d398abe81e6f0024ec719d8`

## Outcome

One real Korean beginner flow now reaches import, an explicit variable-meaning review,
a durable Research OS decision, explicit configuration confirmation, a separate
calculation run, Word export, and explicit recovery after metadata drift. The authority
gap reproduced in the first pass is closed: role submission is transient, creates no
task handle or ledger, and only the separate meaning-confirm action may start the first
durable commit.

## Scenario and measured path

The audit used the real `UiController`, default local `ResearchFlowRuntime`, task-local
SQLite storage, the real `ResearchFlowPanel.qml`, and a controllable serialized worker.
The fixture was a one-column CSV (`score`, values 1 through 10).

| Stage | Measured result |
| --- | --- |
| Preview | One column row and four import-review rows were visible; `variableModel` was intentionally absent until import confirmation. |
| Import | `score` was inferred as `ordinal`; pipeline version became 1. |
| Metadata review | A reproducible `data.variable_metadata_patch` changed label to `인지 점수` and measure to `scale`; pipeline version became 2. |
| Research task | QML selected noncausal → numeric distribution → outcome `score`. |
| Meaning gate after fix | Role submit entered `meaning_reviewing`, then `variable_meaning_review`; the panel displayed key, label, measure, value labels, missing codes, dtype, and explicit `not_recorded` definition/unit status. No task handle or request existed yet. |
| Bounded clarification | Exactly three committed questions: `confirm_cluster_use`, `confirm_dependence`, and `confirm_weight_use`. |
| Decision | `recommend_local`, ledger sequence 8, `stats.descriptives_table1`, variables `[score]`, no group, missing counts enabled, Korean output. |
| Provenance after gate | The outcome role Fact was `user_confirmed` only after explicit confirmation and had exactly two refs: the real initial ledger event ID and `variable-meaning-review:v1:<review digest>`. |
| Durable storage | Read-only SQLite inspection matched head sequence 8 and event count 8; four `analysis_passport` artifacts existed across the clarification chain. |
| Legacy separation | The shape-based candidate `기술통계 표 1` had no `passport_digest`; it was not treated as Research-OS-backed. |
| Prepare | Reached `prepare_review`; one worker operation; no analysis Step added yet. |
| Confirm | Reached `confirmed`; one exact analysis Step was added; result count remained zero; no new worker operation. |
| Early Word export | Failed closed before the separate Run and did not submit calculation. |
| Separate Run | One additional worker submission produced `descriptives_table1`. |
| Word | A 37,188-byte DOCX was generated with Research OS disclosure and the statement that recommendation validity is not guaranteed. The sealed pipeline Step chain was restored unchanged after export. |
| Recovery | Changing the label after the run produced `replan_required`, required selection reconfirmation, blocked Run with `experimental_confirmation_required`, and returned to `intake_causal` only after explicit replan. |

## Integration defects and missing gate fixed with TDD

1. **Imported-pipeline confirmation binding.** `ResearchPreparationEditor` retained the
   `PipelineOperations(None)` created before import while `UiControllerServices`
   replaced its live operations object. Prepare succeeded, but Confirm failed closed.
   The editor now resolves the current operations object from a provider at confirmation
   time.
2. **Research OS Word export.** Confirmation intentionally adds one exact analysis Step
   and no Report Step, so the existing export path could not produce Word. Export now
   requires a completed explicit Run, temporarily appends a Report Step, computes only
   that report from cached results, and restores the exact pipeline snapshot.
3. **Variable Meaning Gate.** Role submission previously promoted typed keys directly
   into durable `user_confirmed` facts. A pure dataset-bound review contract now seals
   exact metadata and roles, the worker prepares it without storage allocation, the UI
   renders it as a separate state, and commit recomputes the review before accepting it.
4. **Visual evidence catalog binding.** The gallery subprocess could import an older
   installed Modori catalog instead of the current repository source, exposing raw
   localization keys in screenshots. The capture harness now prepends the repository
   `src` root, implements the current bilingual bootstrap contract, records catalog
   misses, and fails the gallery contract unless the miss set is empty.
5. **Duplicate integration residue.** Static analysis found one duplicated localized
   recommendation-title slot and one duplicated catalog-reactivity test. The duplicate
   definitions were byte-equivalent and were removed; the surviving slot and test keep
   the same behavior and coverage.

These changes preserve no-auto-run behavior. Focused regression evidence:

- imported-pipeline RED: Confirm returned `False`;
- imported-pipeline GREEN: `1 passed`;
- preparation/services/architecture: `66 passed`;
- pipeline/report/preparation/flow: `113 passed`;
- meaning contract/controller/QML provenance bundle: `188 passed`;
- permanent focused regression bundle: `283 passed`;
- real Korean QML beginner E2E: `1 passed`;
- post-experiment QML/runtime regression bundles: `45 passed` and `83 passed`;
- final non-gallery repository suite: `3289 passed, 5 skipped in 485.87s`;
- final focused launch/QML/catalog/ledger bundle: `28 passed`;
- `ruff check .`, `compileall -q src scripts`, and `launch_smoke.py`: passed;
- Windows-native visual matrix: `30 states`, zero catalog misses, zero horizontal
  overflow sources, zero clipped header titles.

The visual matrix passed all structural, localization, privacy, interaction-response,
and image-digest checks. Its cold Windows `state_render_ms` threshold is load-sensitive
on this machine and is not presented as a stable pass: the same four shell fixtures
ranged from 209.77 ms to 306.15 ms across immediate repetitions, while the untouched
`eaa0e802` baseline measured 285.765 ms against the same 250 ms limit. One integrated
30-state run passed the frozen threshold (`1 passed in 37.31s`), and later full-matrix
runs failed only that assertion with p95 values including 276.433, 300.069, 278.908,
303.232, and 292.365 ms. The last value came from the final full repository run. That
run finished with `2 failed, 3298 passed, 5 skipped`; the other failure was the expected
stale integration-ledger blob identity corrected after the run. The threshold and
measurement code were not relaxed. After correcting the ledger and removing the
duplicate integration residue, the final complete non-gallery suite passed with
`3289 passed, 5 skipped in 485.87s`.

A loader-based inactive-editor experiment was also tested and rejected. It produced
seven QML/runtime regressions and did not make the render timing stable, so all three
experimental QML edits were fully reverted. The original Royal Blue components then
passed the two focused regression bundles (`45` and `83` tests). No unverified
performance optimization remains in the final tree.

## Closed minimum gate

The audit selected the Variable Meaning Gate only after reproducing the full flow. It is
placed between role entry and the first durable request commit. Existing structural
preflight remains later and independent: the gate confirms what the selected variables
mean in the current dataset, while preflight checks whether the sealed method can be
configured. Neither substitutes for the other.

The commit boundary now fails closed when the reviewed dataset fingerprint, pipeline
version, profile, role rows, or any displayed metadata differs. Back, Cancel, language
change, and role submission cannot append ledger authority. Prepare still does not add
an analysis Step, configuration Confirm still does not run calculation, and Word export
still requires a completed separate Run.

## Current-run visual evidence

Windows-native production-component captures were accepted for the bounded question,
candidate, variable-meaning review, Prepare review, and replan-required states. The new
meaning review fits the 360-pixel panel, keeps the primary confirmation after both role
cards, renders Back as a quiet secondary action, and shows the missing definition/unit
boundary in warning color. Automated geometry metadata found no horizontal overflow or
title clipping. Screenshot inspection cannot establish keyboard traversal, screen-reader
announcement order, or complete WCAG conformance; those remain separate interaction and
assistive-technology checks.

Accepted screenshot SHA-256 identities:

| State file | SHA-256 |
| --- | --- |
| `03-question-guided-ko.png` | `3054daded005c7c4e1d4b63ce0a80690107510e849b7a32e2d5c77d9ba9ca80d` |
| `13-candidate-guided-ko.png` | `364b5599612333429a357601240ccebf19e1dd1b8efe66be544a8c6a45e679ab` |
| `21-variable-meaning-review-ko.png` | `77835a05ec00018f6d8e20671f0db3a6fda67670d650db23b40b5ed4a87a6221` |
| `22-prepare-review-ko.png` | `d8fc5f087c08f7b48f4b7dc11abb81a74048788268d81a957a63f7ade0b30bf2` |
| `18-stale-replan-en.png` | `0aa7968bb80ab3c3853ba38aa9b54bc80b88bcb64172691cab8b355a94b3f2a1` |

## Inference and limits

- The current dataset fingerprint already binds variable key, label, measurement level,
  value labels, missing codes, dtype, and cell values. A confirmation digest can bind a
  displayed meaning review to this identity without a new remote or generative system.
- The core variable model has no conceptual-definition or unit field. The minimum gate
  must report those fields as unavailable and must not infer them. Adding a broad new
  metadata authoring schema is outside this pass.
- The real end-to-end audit covers one Korean numeric-distribution slice. Pure contract
  tests cover all six P1 role shapes, and the English gate is a QML/catalog acceptance
  test, but the other five profiles were not each driven through a complete live ledger,
  Run, and Word export in this audit.
