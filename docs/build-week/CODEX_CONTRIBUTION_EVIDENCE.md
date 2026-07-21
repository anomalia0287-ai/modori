# Codex Contribution Evidence

This note records concrete OpenAI Build Week engineering contributions at the
source-under-test commit `ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`. It is a
claim ledger for the demo, README, and submission copy: each claim is tied to a
design decision, production code, a regression test, and recorded verification.

Codex with GPT-5.6 was used as a high-leverage engineering collaborator across a
large existing Windows/Python/QML codebase. The strongest evidence is not a line
count. It is the set of difficult boundaries and real UI defects that were designed,
implemented, challenged, and closed with reproducible tests.

## 1. Meaning, authority, and execution are separate boundaries

### Design problem

A recommendation card is not proof that the displayed decision is authorized by the
reviewed data and metadata. Likewise, confirming a configuration must not silently
start a calculation.

### Engineering contribution

Codex helped design and test a closed transition system with three explicit gates:

1. **Variable meaning before the first durable decision.** The Variable Meaning Gate
   presents the recorded label, measurement level, value labels, missing codes, and
   storage type. Confirmation creates a
   `variable-meaning-review:v1:<digest>` provenance reference; role selection alone
   creates no task ledger or passport authority.
2. **Passport/ledger-backed authority.** An immutable event ledger commits the active
   `AnalysisPassport`, binds it to the exact dataset fingerprint and request, and
   reconstructs the durable action history. Visible recommendation prose is never
   treated as evidence of this authority.
3. **Prepare, Confirm, then a separate Run.** `Prepare` exposes the exact method,
   variables, missingness, and other parameters. Confirmation seals one step but
   leaves the result model empty. Only the separately enabled `Run` command submits
   the calculation. Metadata drift invalidates the old authority and requires an
   explicit replan.

### Code and test evidence

- Meaning model and digest: `src/modori/research_flow/variable_meaning.py`
- Durable ledger and reconstruction:
  `src/modori/research_memory/ledger_store.py`,
  `src/modori/research_memory/passport_state.py`
- Passport contract and exact handoff:
  `src/modori/research_os/passport.py`,
  `src/modori/research_flow/handoff.py`
- Review/confirmation boundary:
  `src/modori/ui/research_preparation_editor.py`,
  `src/modori/ui/research_flow_controller.py`
- Focused regressions:
  `tests/test_research_flow_variable_meaning.py`,
  `tests/test_research_memory_ledger_store.py`,
  `tests/test_research_memory_passport_state.py`,
  `tests/test_research_flow_handoff.py`,
  `tests/ui/test_research_preparation_editor.py`, and
  `tests/ui/test_research_flow_qml.py::test_prepare_confirm_and_run_remain_three_distinct_actions`
- Actual-QML real-data proof:
  `tests/ui/test_research_os_real_data_e2e.py`

The real-data audit verified the gate before recommendation, matching provenance
digests, an eight-event/20-artifact/four-passport integrity-checked ledger, exact
Spearman parameters, an empty result after confirmation, blocked early export, a
separate Run, and explicit replan after metadata drift. The implementation landmarks
include `ed8bcae` (Variable Meaning Gate), `b3f337b` (passport-bound analysis steps),
and `ddfa6f2` (passport-bound preparation confirmation).

## 2. Real Windows UI audits became tested product fixes

These changes began with observed user failures, not hypothetical feature requests.
Codex traced each symptom across QML, controller, service, file-operation, and test
layers, wrote a failing regression, implemented the smallest owning fix, and reran
the affected and broader gates.

### Excel sheet recovery

**Observed failure:** a valid workbook could report that no table data existed when
its default sheet was an empty or informational sheet, even though another sheet held
the data.

**Closed behavior:** the pending workbook path and sheet list survive a recoverable
preview failure; the user can select another sheet and review a schema-bound preview.
Corrupt workbooks still fail closed, and the current dataset/pipeline remains
unchanged until explicit import confirmation.

- Production path: `src/modori/table_io.py`, `src/modori/ui/importing.py`,
  `src/modori/ui/import_flow.py`, and
  `src/modori/ui/qml/dialogs/ImportDialog.qml`
- Regressions: `tests/test_table_io.py`, `tests/ui/test_importing_service.py`,
  `tests/ui/test_import_preview_recent_files.py`, and
  `tests/ui/test_import_dialog_flow.py`
- Commits: `6456e25`, `0c8171d`, `717ec9a`
- Recorded closure: 73 import/QML runtime tests and a 785-test non-gallery UI gate;
  the source XLSX hash was unchanged before and after recovery.

### Safe Word export and replacement

**Observed failure:** exporting again to the same report path could silently replace
an existing document, and report work could occur before the user's explicit export.

**Closed behavior:** Modori predicts the destination without mutation, rejects an
existing target before the exporter runs, asks for explicit replacement authority,
uses a same-directory transactional backup, restores the original on post-mutation
failure, validates the new DOCX, and removes the backup only after success. Report
files are deferred until explicit export.

- Production path: `src/modori/ui/report_export.py`,
  `src/modori/ui/report_export_controller.py`, `src/modori/ui/controller.py`,
  `src/modori/ui/pipeline_ops.py`, and
  `src/modori/ui/qml/dialogs/ReportExportDialog.qml`
- Regressions: `tests/ui/test_report_export_service.py`,
  `tests/ui/test_pipeline_ops.py`, `tests/ui/test_controller.py`, and
  `tests/ui/test_human_operated_qml_flow.py`
- Commits: `d444955`, `b0d6e24`, `9a599ec`, `b29ae1a`, `706e56d`, `b8b6839`
- Recorded closure: the cancel and injected-failure cases preserved the original
  SHA-256; the focused gates passed 16 + 14 + 6 + 44 tests, followed by a 775-test
  non-gallery UI gate.

### Actionable Research OS failure recovery

**Observed failure:** an ordinary Research OS error showed a generic failure card
whose button label did not reliably describe the controller action.

**Closed behavior:** a closed reason catalog maps known failure classes to sanitized,
localized explanations and state-valid actions. Raw exceptions, paths, and cell
values never enter the QML model. Recovery distinguishes replan, local-record reload,
safe return, and the one true pending-transition resume path.

- Production path: `src/modori/ui/research_flow_presenter.py`,
  `src/modori/ui/research_flow_controller.py`, and
  `src/modori/ui/qml/components/ResearchFlowPanel.qml`
- Regressions: `tests/ui/test_research_flow_presenter.py`,
  `tests/ui/test_research_flow_controller.py`, and
  `tests/ui/test_research_flow_qml.py`
- Commits: `7c7b7dd`, `9b1a3e9`
- Recorded closure: 824 non-gallery UI tests and 789 Research OS/flow/memory tests.
  The packaged audit also entered an invalid role, returned to the last verified
  state, corrected the role, and reached the Variable Meaning Gate again without an
  automatic retry or calculation.

## 3. Semantic integration across a large existing codebase

The completed Royal Blue interface arrived as seven ordered commits on top of an
already functional Research OS. Codex helped build a machine-readable integration
ledger before code resolution: both sides changed 25 paths, 12 had predicted textual
conflicts, and the remaining 13 still required semantic review.

The resolution rule preserved Research OS safety, provenance, abstention, and manual
execution authority while adding the bilingual Royal Blue experience. Shared tests
were resolved as assertion unions. Blanket `ours`/`theirs`, whole-file copying, and
deleting existing behavior to satisfy UI code were prohibited. The closed ledger and
its validator are:

- `docs/qa/research-os-royal-blue-functional-integration-ledger.json`
- `tests/test_research_os_royal_blue_integration_ledger.py`

A later public-P0 reconciliation repeated the same method for 12 changed source/test
paths. Each path received a specific disposition; a 155-test release-delta cohort
proved the result without reintroducing superseded controller architecture. See
`docs/qa/build-week-public-p0-functional-delta-ledger.md`.

The final source-under-test was then checked by the actual-QML real-data acceptance
test, a 179-test adjacent Research OS/import/report cohort, and the complete
non-gallery source suite:

```text
3,393 passed, 5 skipped in 526.41s
exit 0
```

Ruff, Bandit, compileall, source launch, `pip check`, wheel inspection, and packaged
launch/engine/public-data smokes also exited zero. Exact hashes and the separation
between automated and manually observed evidence are recorded in
`docs/qa/build-week-real-data-research-os-e2e.md` and
`docs/build-week/DEMO_SCRIPT.md`. The final local video codec, frame-count, subtitle,
hash, motion, and privacy checks are recorded in
`docs/build-week/VIDEO_VERIFICATION.md`.

## Product framing

This is AI-assisted engineering applied to a difficult desktop product: repository
inspection, architecture design, adversarial testing, semantic integration, Windows
UI diagnosis, and evidence management. Modori's shipped statistical workflow remains
deterministic and local, so the product can pair fast AI-assisted development with
inspectable calculations, durable provenance, and reproducible release claims.
