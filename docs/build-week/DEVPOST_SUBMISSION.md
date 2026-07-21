# Modori — Devpost Submission Packet

Status: **local evidence complete; public repository branch, YouTube URL, Codex
Session ID, and final Devpost submit action require owner-controlled publication**

This file is the English paste master for the OpenAI Build Week submission. It is
bound to the verified real-data demo and source-under-test commit
`ca379fd9bb907eeff04c0be7c1412a2e0f73f11b`.

## Short fields

| Field | Paste value |
| --- | --- |
| Project name | Modori |
| Track | Education |
| Tagline | A local Research OS that asks before it calculates. |
| Repository | `https://github.com/anomalia0287-ai/modori/tree/codex/research-os-functional-usability` after that branch is published |
| Demo video | Replace with the final **Public YouTube** URL |
| Codex Session ID | Replace with the value returned by `/feedback` in the primary core-build Codex task |
| Platform | Windows 11 x64; verified with CPython 3.12.10 |
| License | GPL-3.0-only source; third-party components retain their own terms |

## One-sentence pitch

Modori turns a learner's research question and real dataset into a reviewable
statistical plan, an explicit Run, and a Word report—without sending the data away.

## Inspiration

Learning statistics should not begin with a wall of method names. For many
social-science students, the difficult part comes before calculation: translating a
research question into variable roles, assumptions, and a method that can be
explained later. I built Modori to make that decision path visible and reviewable.

## What it does

Modori is a Windows-first desktop statistics workspace with two complementary paths.
Guided Mode begins with the research task. It asks a bounded set of design questions,
shows the recorded meaning of each selected variable, and presents an inspectable
method configuration. Pro Mode keeps the broader manual analysis workspace for users
who already know the method they need.

In the demonstrated Guided Mode path, Modori:

- imports and reviews a real 649-record UCI Student Performance table;
- confirms the label, measurement level, value labels, missing codes, and storage
  type of the variables before a durable recommendation is created;
- records bounded answers about independence, clustering, and weights;
- produces a dataset-bound experimental Spearman candidate for an association-only
  question;
- exposes the exact variables, missing-data policy, and parameters before execution;
- keeps Prepare, confirmation, and Run as three distinct actions;
- displays a reviewable result and exports it to Word locally; and
- abstains when a second request asks for a causal claim outside the current scope.

The demonstrated calculation is Spearman `rho = 0.275`, `p < .001`, `n = 649`.
The result describes association in the released records, not causation.

## How I built it

The desktop application uses Python 3.12, PySide6/QML, pandas, SciPy, statsmodels,
SQLite, and python-docx. A local append-only decision ledger records task transitions
and AnalysisPassports bind a reviewed configuration to the current dataset and
metadata. The statistical runtime is deterministic and local.

Modori's statistical engine existed before Build Week. During Build Week, Codex with
GPT-5.6 became a high-leverage engineering collaborator for the new guided Research
OS: repository inspection, architecture and contract design, failing regression
tests, implementation, semantic integration, Windows UI diagnosis, and evidence
management.

Three contribution chains are visible in the demo and traceable in the repository:

1. Variable Meaning Gate → passport/ledger authority → Prepare/Confirm/separate Run.
2. Real UI audit → Excel sheet recovery, safe Word replacement, and actionable
   failure recovery → focused regressions and broader verification.
3. Seven Royal Blue UI commits → path-by-path semantic conflict ledger → integrated
   bilingual workflow without blanket conflict resolution.

The final submission source suite reports `3,393 passed, 5 skipped`; external NIST
StRD and R cross-engine anchors support the calculation layer. Recommendation
boundaries and numerical calculations are tested as separate claims.

## Challenges

- Preserving an existing statistical engine while integrating a substantially revised
  bilingual UI and a new durable Research OS state machine.
- Ensuring that attractive recommendation copy never became a substitute for actual
  passport and ledger authority.
- Keeping ambiguity honest: a bounded clarification or abstention had to remain a
  successful product outcome rather than being hidden behind a convenient method.
- Turning failures seen in the packaged Windows UI into small owning fixes with tests,
  including Excel sheet recovery and transactional Word replacement.
- Binding every submission claim to the exact data, source commit, package, report,
  and video used to demonstrate it.

## Accomplishments

- One complete real-data path now runs from import and variable meaning through a
  reviewed candidate, explicit Run, result, evidence trail, and English Word report.
- A second causal request ends in an explicit, reviewable abstention instead of a
  substituted analysis.
- Dataset or metadata drift invalidates stale authority and requires a visible replan.
- The final 2:55 demo uses 649 released observations, actual Modori interaction, an
  actual generated Word report, English audio, and a matching 12-cue subtitle file.
- The final media, package, dataset, report, and source-suite evidence are hash-bound
  and independently rechecked.

## What I learned

The most valuable AI-assisted engineering was not producing more code. It was turning
product questions into executable contracts and then challenging those contracts at
the real UI boundary. A trustworthy guided statistics tool needs more than correct
arithmetic: it needs visible meaning, explicit authority, recoverable transitions,
and the ability to say that the evidence is not enough.

## What's next

The next stage is human validation with social-science learners and instructors,
followed by accessibility and localization refinement, a recorded single-cell
correction workflow, and carefully validated expansion of the supported research-task
space. Each addition will retain the same local, reviewable, no-auto-run boundary.

## Testing instructions for judges

Use Windows 11 x64 and CPython 3.12.10:

```powershell
git clone --branch codex/research-os-functional-usability --single-branch `
  https://github.com/anomalia0287-ai/modori.git
cd modori
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install `
  -c constraints\build-week-windows-py312.txt `
  -e ".[dev,packaging]"
.\.venv\Scripts\python.exe -m modori.app
```

Choose `English` → `GUIDED MODE` → `Open data file`, then open:

```text
examples\build-week-demo\student-study-and-grades.csv
```

The top-level README gives the exact ten-step demonstrated path. Dataset provenance,
license, hashes, and regeneration instructions are in
`examples/build-week-demo/README.md`. No R installation is needed to launch and try
the demonstrated workflow.

## Recommended Devpost gallery order

Upload these exact verified 1,920 × 1,080 frames from the local evidence directory:

1. `verified-02-008s.png` — **A result you can review.** 649 public records reach an
   inspectable Spearman result and local Word export.
2. `verified-06-055s.png` — **Meaning before method.** The Variable Meaning Gate shows
   exactly what is recorded before a durable recommendation exists.
3. `verified-09-105s.png` — **Review before calculation.** Confirmation leaves the
   result empty; the separate Run button remains the execution boundary.
4. `verified-10-124s.png` — **Abstention is a product behavior.** A causal request
   outside the current method space receives an explicit decision basis.
5. `verified-11-130s.png` — **Built with Codex + GPT-5.6.** Product questions moved
   through specification, red tests, implementation, and Windows verification.

Use image 1 as the cover. These are direct frames from the final hashed MP4, not
separately staged mockups.

## Final publication checklist

- [ ] Publish the exact current branch without changing the default branch.
- [ ] Open the branch URL in a signed-out browser and confirm that this README, the
      GPL license, third-party notices, real demo data, and contribution evidence load.
- [ ] Watch the exact hashed MP4 once at normal speed with sound.
- [ ] Upload that MP4 to YouTube as **Public** and upload the canonical SRT as English
      captions.
- [ ] Verify the YouTube URL in a signed-out browser.
- [ ] Run `/feedback` from the primary core-build Codex task and copy its Session ID.
- [ ] Paste the English fields above into Devpost; add the five verified gallery frames.
- [ ] Preview every Devpost section and test every external URL.
- [ ] Submit before **2026-07-22 09:00 KST** and preserve the confirmation receipt.
