# Research OS Variable Meaning Gate Implementation Plan

Status: completed in `ed8bcae6f7452d2713865afc3ebfa98508d3b65b`; final verification
evidence is recorded in `docs/qa/research-os-royal-blue-novice-flow-audit.md`.

> Execute with test-driven development. Do not weaken ledger, passport, preflight, or
> manual-run boundaries to make tests pass.

**Goal:** Insert an explicit, dataset-bound variable-meaning confirmation before the
first durable Research OS request.

**Architecture:** A pure `research_flow` review contract/builder seals current metadata
and roles. The runtime prepares and revalidates it on the worker. The controller exposes
two new transient states and commits only from the explicit confirm command. QML renders
the immutable review with existing Royal Blue components.

## Task 1: Contract and builder RED/GREEN

- Add tests for canonical digest coverage, all six role shapes, metadata projection,
  duplicate/out-of-dataset rejection, and drift-sensitive equality.
- Implement `VariableMeaningRow`, `VariableMeaningReview`, and the pure builder.

## Task 2: Controller/runtime authority RED/GREEN

- Prove role submit creates no task/ledger and returns `variable_meaning_review`.
- Prove Back adds no authority.
- Prove stale or altered review cannot commit.
- Prove explicit confirm commits and role Fact provenance names the real ledger event and
  review digest.
- Implement the new states, runtime review/revalidation, pending-state lifecycle, and
  `confirmVariableMeanings` command.

## Task 3: QML and localization RED/GREEN

- Require the real panel to render `researchVariableMeaningReview` in Korean and English.
- Require exact metadata/role rows, primary Confirm, quiet Back, and no submit-to-commit
  shortcut.
- Add catalog parity and runtime-warning coverage.

## Task 4: Permanent novice E2E

- Drive actual QML from preview through the new gate, bounded clarifications, durable
  candidate, Prepare, configuration Confirm, separate Run, Word export, drift block, and
  explicit replan.
- Inspect SQLite read-only and assert request/passport provenance bindings.

## Task 5: Regression and evidence

- Update the Royal Blue integration ledger blob identities for every tracked path changed.
- Run contract, live flow, UI/QML, report, full suite, lint/compile, launch smoke, and
  visual-state checks freshly.
- Record exact commands, counts, hashes, and remaining unverified claims.
