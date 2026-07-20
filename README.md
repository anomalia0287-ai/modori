# Modori

**Turn a research question and a real dataset into a reviewable statistical plan,
an explicit Run, and a Word report—locally.**

Modori is a Windows-first desktop statistics workspace for learners and researchers
who want more guidance than a blank analysis dialog. Its Guided Mode asks a bounded
set of research-design questions, shows what each selected variable means, proposes
an inspectable method configuration, and waits for the user to run it.

The current Build Week demonstration follows 649 released student records from
import to a Spearman rank-correlation result and an English Word report. The table
stays on the computer; the runtime uses deterministic local code rather than a
hosted model.

## Why it is useful

- **Question before command.** Start from the research task and variable roles,
  then review the exact method and parameters that will be used.
- **Meaning before recommendation.** The Variable Meaning Gate shows labels,
  measurement levels, value labels, missing codes, and storage types before the
  first durable Research OS decision.
- **Review before calculation.** `Prepare` creates an experimental, dataset-bound
  configuration. Confirmation does not calculate; `Run` remains a separate action.
- **Evidence after calculation.** Results expose the method, coefficient, p-value,
  sample size, exclusions, interpretation boundary, and a Word export path.
- **Recoverable decisions.** Metadata or pipeline changes invalidate stale authority
  and lead back to an explicit replan rather than silently reusing an old result.
- **Local by design.** Statistical calculations, recommendation rules, project
  ledgers, and report generation run on the local machine.

## Guided Mode and Pro Mode

**Guided Mode** supports a closed Research OS task set:

1. a numeric distribution;
2. category counts and proportions;
3. Pearson linear co-movement;
4. Spearman rank co-movement;
5. a mean difference between two independent groups; and
6. mean change between two measurements from the same unit.

The system can recommend, ask a bounded clarification, or abstain. Candidate order
is not an accuracy ranking, every candidate is labelled experimental, and no
analysis is selected or run automatically.

**Pro Mode** exposes the broader verified manual analysis workspace for users who
already know the method they want. Both modes use the same deterministic calculation
engine and report path.

## Real-data Build Week walkthrough

The committed demo view comes from the UCI Student Performance Portuguese-course
table: 649 student records with six non-identifying learning/context fields. The
demo question is:

> Do weekly study-time bands and final grades tend to move together in these
> records?

The reviewed method is Spearman rank correlation because weekly study time is an
ordered four-level variable. The independently reproduced result is:

```text
rho = 0.2747118483356099
two-sided p = 1.060624038270125e-12
n = 649
excluded = 0
```

The product display rounds the coefficient to `0.275` and the p-value to `0.000`.
This is an association within the released records, not a causal or population-wide
claim.

Use:

```text
examples\build-week-demo\student-study-and-grades.csv
```

Source, license, codebook, hashes, transformation rules, and regeneration commands
are documented in
[`examples/build-week-demo/README.md`](examples/build-week-demo/README.md).

## Run from source on Windows

The verified environment is Windows 11 x64 with CPython 3.12.10.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install `
  -c constraints\build-week-windows-py312.txt `
  -e ".[dev,packaging]"
.\.venv\Scripts\python.exe -m modori.app
```

Choose `English` or `한국어`, open **GUIDED MODE**, and select **Open data file**.
CSV, XLSX, legacy XLS, and SPSS SAV imports are supported. The preview labels its
30-row limit as a sample; confirming the import loads the complete table.

## Reproduce the demonstrated path

1. Open `student-study-and-grades.csv` and confirm the import.
2. Set `weekly_study_time_band` to ordinal and review its four value labels.
3. Set `final_grade` to scale.
4. Open Research OS and choose a noncausal rank co-movement task.
5. Assign Final grade as outcome and Weekly study time as focal predictor.
6. Confirm the Variable Meaning Gate and answer the bounded design questions.
7. Review the Spearman candidate and its association-only claim boundary.
8. Choose `Prepare`, inspect the exact pair/missingness configuration, and confirm.
9. Choose the separately enabled `Run` action.
10. Review the result and export the English Word report.

The actual-QML acceptance test additionally proves that early export is blocked,
the durable decision is passport/ledger-backed, and changing the study-time measure
forces a replan.

## Verified evidence

The current real-data closure includes:

- a deterministic source archive and derived CSV with frozen SHA-256 values;
- independent SciPy agreement for coefficient, p-value, complete pairs, and
  exclusions;
- an actual-QML import-to-Word-to-replan test;
- an adjacent Research OS/import/report cohort with 179 passing tests; and
- a full non-gallery source run with `3387 passed, 5 skipped` under the pinned
  R 4.5.3 reference boundary.

The failed first full-run observation and its four individually repaired audit/copy
contracts are retained alongside the clean rerun. Exact commands, commit identities,
package hashes, and visual evidence belong in
[`docs/build-week/VERIFICATION.md`](docs/build-week/VERIFICATION.md).

## Build Week contribution

Modori existed before OpenAI Build Week. The eligible work turns its statistical
engine into a guided, reviewable research workflow: the deterministic multi-round
Research OS, local decision memory and passports, explicit recommendation boundaries,
Variable Meaning Gate, prepare/confirm/separate-run lifecycle, Royal Blue bilingual
workspace integration, recovery paths, real-data acceptance evidence, and release
hardening.

Codex with GPT-5.6 served as a high-leverage engineering collaborator throughout the
eligible period. It helped inspect a large existing repository, design adversarial
tests, implement and integrate the workflow, trace authority and provenance across
layers, diagnose failures in the real Windows UI and packaged path, and keep product
copy aligned with executable behavior. The result demonstrates AI-assisted software
development applied to a difficult, evidence-heavy desktop product—not an AI model
inserted where deterministic statistics are the better runtime tool.

See [`docs/build-week/BUILD_WEEK_DELTA.md`](docs/build-week/BUILD_WEEK_DELTA.md) for
the pre-existing/eligible boundary and
[`docs/build-week/DEVPOST_SUBMISSION.md`](docs/build-week/DEVPOST_SUBMISSION.md) for
the submission copy.

## Local data and current boundaries

Modori has no configured runtime network client, telemetry route, cloud analysis
route, or generative-model call. It may store settings, recent-file paths, caches, a
research-task index, and per-project SQLite ledgers beneath `%LOCALAPPDATA%\Modori`.
Reports are written to a `modori-output` directory next to the imported file, so an
externally synchronized source folder may also synchronize its report.

Imported source cells are read-only in the current build. Variable metadata and
reproducible transformation steps can be edited inside Modori; changing raw source
values requires editing the source file and importing it again. Direct cell editing
remains a follow-up usability item, not a hidden feature claim.

The six Guided Mode tasks do not establish universal method coverage, recommendation
validity, causal validity, expert equivalence, or complete accessibility/localization
conformance. Those are separate evaluation targets from the calculation and workflow
evidence above.

## License and attribution

Modori-authored source is licensed `GPL-3.0-only`; see [`LICENSE`](LICENSE).
Dependencies, fonts, icons, and datasets retain their own terms; see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The UCI demo view is derived from
CC BY 4.0 source data and retains its attribution.

No prebuilt or code-signed public executable is included in this source submission.
