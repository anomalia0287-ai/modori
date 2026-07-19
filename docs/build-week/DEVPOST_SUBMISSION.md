# Devpost Submission Packet

Status: **technical draft; final story edit, URLs, Session ID, and owner review pending**

This packet is written in English so it can be pasted into Devpost without
translation. Repository evidence and `CLAIM_MATRIX.md` remain authoritative. The
official rules and FAQ are:

- <https://openai.devpost.com/rules>
- <https://openai.devpost.com/details/faqs>

## Short fields

| Field | Prepared value |
| --- | --- |
| Project name | Modori |
| Track | Education |
| Tagline | A local, auditable path from research intent to a reviewed statistical run. |
| Repository | `https://github.com/anomalia0287-ai/modori` after the final release commit becomes the public default entry point |
| Demo video | `[OWNER: paste the final Public YouTube URL]` |
| Codex Session ID | `[OWNER: run /feedback in the primary build thread and paste the returned Session ID]` |
| Tested platform | Windows 11 x64 with CPython 3.12.10 |
| Public artifact | GPL-3.0-only source; no prebuilt executable |
| Technologies | Python, PySide6/QML, pandas, SciPy, statsmodels, scikit-learn, Pingouin, factor_analyzer, SQLite, PyInstaller, pytest, Ruff, Bandit |

## One-sentence pitch

Modori helps a learner or researcher make a bounded statistical decision visible,
reviewable, and replayable before a local calculation starts.

## Inspiration and problem

A blank statistics dialog asks users to translate a research question into variables,
assumptions, and a method all at once. That translation is easy to lose after the
result appears. Modori treats the decision path as part of the research artifact: it
captures intent and roles over multiple rounds, records what was decided, binds the
prepared method to the current data, and leaves calculation behind a separate user
action.

This is an education-oriented workflow aid, not an automated expert. Its current
Research OS scope is intentionally limited to six research tasks, and its candidates
are labelled experimental.

## What it does

Modori is a Windows-first desktop application. A user can import CSV, XLSX, XLS, or
SPSS SAV data, review the detected table, and use either direct deterministic analysis
paths or the bounded Research OS P1 flow.

For exactly six tasks—Pearson correlation, Spearman correlation, paired mean change,
Welch two-group mean difference, descriptive summary, and frequency distribution—the
Research OS flow can:

- collect research intent and variable roles over multiple local rounds;
- record clarification decisions and their rationale;
- produce an AnalysisPassport bound to the current dataset and decision state;
- show an experimental method candidate, roles, and interpretation boundary; and
- prepare the existing deterministic calculation path without starting it.

A calculation starts only after a separate user action. There is no runtime GPT-5.6,
LLM, SLM, hosted analysis, telemetry, or verified external route in the current code.
Application state, recent-file settings, task indexes, and decision ledgers are local.

## What existed before Build Week

Modori was not created from scratch during the event. Before the official cutoff it
already had a broader Python statistical engine, the original desktop and import
surfaces, report generation, earlier experimental recommendation boundaries, the
initial six-task method-space and passport foundations, local ledger contracts, and
statistical reference evidence.

The repository's `docs/build-week/BUILD_WEEK_DELTA.md` identifies the cutoff, commit
history, integration-merge caveat, and pre-existing foundations. Judges should score
the meaningful post-cutoff extension rather than the whole historical product.

## What was meaningfully extended during Build Week

After July 13, 2026 at 9:00 a.m. Pacific Time, the project was extended with:

1. a substantially revised and repeatedly reviewed Windows research surface;
2. bounded deterministic minimax clarification, refusal/replanning behavior, and an
   evidence-backed explanation of why one question ranked ahead of another;
3. AnalysisPassport v2 authority binding and one-active-passport semantics;
4. an end-to-end durable local multi-round workflow, exact dataset identity, recovery,
   asynchronous UI projection, and live QML interaction; and
5. history-preserving integration plus stronger package, mutation, legacy-path, and
   deterministic benchmark-kit evidence.

The final source-submission audit also used a real packaged application walkthrough.
It exposed and closed two interoperability blockers between imported pipelines,
Research OS preparation, correlation validation, and Run enablement. Regression
coverage now exercises that exact boundary without expanding the six-task method
space.

These are workflow, authority, explanation-fidelity, and release-evidence extensions.
They do not establish recommendation accuracy or research validity.

## How Codex and GPT-5.6 were used

Codex with GPT-5.6 acted as a build-time engineering collaborator. It accelerated
repository-wide contract searches, design alternatives for bounded deterministic
clarification, adversarial and mutation-oriented test construction, implementation,
history-preserving integration analysis, QML review, and the final licensing,
reproducibility, and claim audit.

The most useful collaboration was not one-shot code generation. Codex repeatedly
compared intended behavior with executable contracts, found authority and recovery
edge cases, and converted them into tests or narrower wording. The owner made the key
product and release decisions: keep the runtime local and deterministic; close the P1
method space at six tasks; require explicit review and a separate Run action; retain
the experimental label; use a GPL-3.0-only source release; publish no prebuilt binary;
and leave the unmeasured B5 laptop claim pending.

Git timestamps document when changes entered the repository but do not prove model
identity. The Devpost `/feedback` Session ID from the primary build thread provides
the required model-bound session evidence.

## Challenges

- Separating eligible work from a large pre-existing repository required auditing
  timestamps and both parents of an integration merge instead of treating one broad
  diff as new work.
- A useful clarification flow had to remain finite, deterministic, reviewable, and
  unable to acquire execution authority by itself.
- Dataset identity, recoverable local state, and one-active-passport rules had to stay
  consistent across services, SQLite ledgers, presenters, and QML.
- Release evidence had to stay bound to exact commits and hashes. A development-PC
  benchmark result could not be relabelled as an unmeasured low-cost-laptop pass.
- Dependency licensing favored a source-only GPL-3.0-only release over a rushed
  statistical-engine rewrite or an under-audited public binary.

## Accomplishments

- A live, recoverable, local multi-round flow now reaches an exact dataset-bound
  AnalysisPassport, an explicitly reviewed calculation preparation, and a separately
  started result on the public synthetic fixture.
- The candidate boundary remains visible: experimental, no accuracy rank, no automatic
  selection, and no automatic execution.
- The repository records the Build Week delta, license and third-party notices,
  Windows dependency constraints, synthetic sample, judge smoke path, demo script,
  claim matrix, and verification evidence in one public audit trail.
- The sealed B4-R development-PC kit remains bound to commit
  `989d5c5829e3d3de69ebda0f4fc88e6f76d16112` and SHA-256
  `6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43`.
  Its recorded result is `3233 passed, 13 skipped`, 300 rejected sealed mutations, and
  three byte-identical independent kit builds. This does not establish the pending B5
  laptop measurement or a byte-identical general application build.

## What we learned

For a high-consequence workflow, the most valuable AI-assisted engineering work was
making authority and uncertainty inspectable. Determinism alone was not enough: the
system also needed exact dataset binding, finite questions, refusal handling, durable
records, no-auto-run enforcement, and wording that does not outrun the evidence.

We also learned that submission quality is a technical artifact. Licensing, sample
provenance, setup commands, historical attribution, demo narration, and public claims
must be tested against the same repository contracts as the application.

## What's next

The immediate next work is evidence, not scope expansion: complete the separate B5
low-cost HP measurement, conduct human and domain-expert validation of the bounded
recommendation workflow, and improve accessibility and Korean/English coverage. Any
future task or external route should enter only with its own authority boundary,
validation plan, and disclosure. No result in this submission predicts those future
outcomes.

## Testing instructions for judges

1. Use Windows 11 x64 with CPython 3.12.10.
2. Follow the three setup commands in the top-level `README.md`.
3. Launch `python -m modori.app` and import the repository's deterministic synthetic
   `pilot-007-correlation.csv` fixture.
4. Run the two JSON-producing smoke commands and the three-file Research OS pytest
   cohort under **Judge smoke path** in the README.
5. Confirm exit code `0` and top-level `"ok": true` in both JSON files.

No R installation is needed for this bounded judge path. The separate full release
gate and its R-backed reference checks are documented in
`docs/build-week/VERIFICATION.md`. The repository intentionally provides no prebuilt
or code-signed executable.

## Screenshot plan and captions

Use 16:9 PNG or high-quality JPEG images, crop out Windows account names and private
paths, and keep application text readable. Use the same synthetic fixture as the
video.

| Order | Capture | Approved English caption | Acceptance check |
| --- | --- | --- | --- |
| 1 | Entry screen with mode choices and local-processing message | **Start locally.** Modori is a Windows-first research workflow; the current runtime has no configured hosted analysis or telemetry route. | No recent-file names or private path visible |
| 2 | Import preview with `stress` and `sleep_hours` | **Review before import.** The demo uses a 16-row deterministic synthetic fixture with no real respondent records. | Filename and both columns legible |
| 3 | Research OS intake after the noncausal boundary, with linear co-movement and both variable roles | **Bind intent to data.** Research OS P1 supports exactly six bounded local tasks and records roles over multiple rounds. | Boundary, selected task, and two roles visible |
| 4 | Clarification/rationale or passport state | **Make the decision auditable.** Deterministic clarification and the AnalysisPassport preserve rationale and exact dataset authority. | Do not imply correctness or expert validation |
| 5 | Candidate/preparation card with experimental and no-auto-run wording | **Review before calculation.** The Pearson candidate is experimental, is not an accuracy rank, and cannot run automatically. | Badge, roles, and boundary legible |
| 6 | Result/report after the separate Run action | **Run separately, interpret narrowly.** The result summarizes association; it does not establish causality or recommendation validity. | Result visible; no real data or superiority claim |

Optional seventh image: a plain repository evidence collage showing the top-level
README, `BUILD_WEEK_DELTA.md`, and `VERIFICATION.md`. Do not use a test-terminal image
unless the command, commit, count, and exit status are all visible and correspond to
the final release evidence.

## Fable story fact-check

When the edited story arrives, accept tone and structure changes only after checking
every technical statement against `CLAIM_MATRIX.md`. Reject or narrow any added claim
of:

- a project built entirely during Build Week;
- runtime GPT-5.6, a runtime LLM/SLM, or a verified external route;
- validated recommendation accuracy, expert equivalence, or SPSS superiority;
- broad social-science coverage or complete numerical correctness;
- complete bilingual or accessibility support;
- a passed B5 low-cost HP measurement; or
- a public executable or binary-distribution audit.

## Final paste checklist

- [ ] Track is **Education**.
- [ ] All prose and testing instructions are in English.
- [ ] The public repository's default entry point shows the final commit, README,
      GPL-3.0-only license, third-party notices, sample, and verification record.
- [ ] Repository URL works in a signed-out browser.
- [ ] Public YouTube video is 3:00 or shorter, includes clear audio, and demonstrates
      the working product plus specific Codex/GPT-5.6 collaboration.
- [ ] YouTube URL works in a signed-out browser and resolves as **Public**.
- [ ] `/feedback` Session ID is from the primary core-build thread, not this release
      audit or a side thread.
- [ ] Fable-edited story passed the fact-check above.
- [ ] Screenshot captions match the claim matrix and contain no private information.
- [ ] Final testing instructions point to the exact README commands.
- [ ] No prebuilt binary, HP pass, full-bilingual, recommendation-accuracy,
      expert-equivalence, SPSS-superiority, complete-accessibility, broad-scope, or
      verified-external-route claim is present.
- [ ] Owner performs the final Devpost preview and submit action before the deadline.
