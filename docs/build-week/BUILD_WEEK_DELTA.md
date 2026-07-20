# OpenAI Build Week Delta

Status: release-lane source-history audit; public default update pending

This project existed before OpenAI Build Week. This document separates prior work
from work committed during the official submission period. It does not claim that
the entire Modori application was created during Build Week.

## Official time boundary

The official submission period began on July 13, 2026 at 9:00 a.m. Pacific Time.
For this repository audit, that instant is represented as:

```text
2026-07-13T09:00:00-07:00
2026-07-14T01:00:00+09:00
```

The second line is the same instant in Korea Standard Time.

Official rules: <https://openai.devpost.com/rules>

## Audited repository identities

| Item | Identity |
| --- | --- |
| Public repository | `https://github.com/anomalia0287-ai/modori` |
| Public default branch observed at audit | `release/readiness-1-9` |
| Public default HEAD observed at audit | `0413059b993ae5bb28190907badb7733d94f3f64` |
| Integrated source baseline for this release lane | `eaa0e802a0c64f6619297432f129be4d198a79ea` |
| Sealed source-submission baseline | `616955232d91aa322da66cb21a8865ec686ba87f` |
| Functional-usability candidate | `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` |
| Local two-parent functional integration | `4260ed862a74fee094b9a94c42ffe95fd7fe4c64` |
| Historical immutable P0 functional freeze | `b2235dabbe01258ae68be4f49bcbb974777a9578` |
| Direct documentation audit correction | `8e4e6f91cd05e51fcb5d0f3b0fbd4c0b3ff235bc` |
| Final claim-fidelity source | `42538443501b817cedd25f858224499f4a97322e` |
| Package-metadata README child | `35e5d706861a0a4a8d8333c97df5d21a95a52e38` |
| Last pre-cutoff commit selected by timestamp traversal | `cf068cad748b409737aded844b1e4afb442d181a` |
| Commit time of that pre-cutoff record | `2026-07-13T05:05:10+09:00` |
| Post-cutoff commits reachable from the integrated baseline | 127 |
| Integrated baseline distance from the audited public HEAD | 285 commits |

At the local functional integration `4260ed8`, the same commands report 141
post-cutoff commits and a 299-commit distance from the audited public HEAD. Later
submission-evidence commits are additional post-cutoff work; they do not reclassify
pre-existing foundations as eligible work.

The 127 count is the result at `eaa0e80`, before the Build Week submission-document
commits on the current release branch. Those later release-only commits are additional
post-cutoff work and do not alter the feature attribution below.

Commands used for the timestamp audit:

```powershell
git rev-list -1 --before="2026-07-13T09:00:00-07:00" HEAD
git rev-list --count --after="2026-07-13T09:00:00-07:00" HEAD
git log --after="2026-07-13T09:00:00-07:00" --format="%H|%cI|%s" --reverse
git rev-list --count 0413059b993ae5bb28190907badb7733d94f3f64..eaa0e802a0c64f6619297432f129be4d198a79ea
```

The history contains a two-parent integration merge. A pre-cutoff commit that becomes
reachable through that merge remains pre-existing work. For that reason,
`git diff cf068cad..HEAD` is not used as a claim that every changed line is eligible;
commit timestamps, parent histories, specifications, and evidence records are reviewed
together.

## Pre-existing work not claimed as Build Week output

The following foundations existed before the cutoff and are disclosed as prior work:

- the Python statistical engine and its broader analysis modules, including data
  import, transformations, descriptive statistics, reliability, correlation, group
  comparisons, ANOVA-family methods, regression, factor/PCA, mediation-family paths,
  reporting, and reference tests;
- the original desktop shell, import preview, result and report surfaces, and earlier
  recommendation heuristics;
- the experimental recommendation boundary introduced before the event, including
  explicit confirmation and no-auto-run behavior;
- the initial six-task Research OS method space, resolver, clarification registry,
  AnalysisPassport foundation, decision-evidence contracts, and local SQLite decision
  ledger created before the cutoff;
- portable office-benchmark foundations and the internal installer work started before
  the cutoff; and
- statistical reference evidence accumulated before the event.

In particular, the post-cutoff commit `ab3b9b9` records an existing local-installer
integration. It is documentation, not a claim that the installer itself was newly built
during the submission period. The internal installer is not the public judge artifact.

## Meaningful post-cutoff extension

The following groups are the eligible Build Week extension. Commit IDs are
representative anchors, not an attempt to hide intermediate commits or review fixes.

### 1. Usable Windows research surface

The existing shell was materially redesigned and then reconciled through multiple
actual-QML review passes. The work includes the cream/nacre and Aurora Glass passes,
followed by the integrated Royal Blue entry and workspace, contained grid scrolling,
visible settings, improved import/work/result and transform surfaces, session-level
Korean/English controls across the reviewed workflow, and clearer experimental
guidance.

Representative commits:

- `043cf8d` — cream nacre QML foundation;
- `0645d02` — entry and work-shell recomposition;
- `73d684d` — result and transform surface improvement;
- `55fbd50` and `92deb5f` — contained data-grid scrolling;
- `b5aa7f4` and `145ba6e` — wordmark and header treatment; and
- `ca40471` — Aurora Glass interface pass;
- `70dadf9` — bilingual Royal Blue entry;
- `e5db816` — Royal Blue workspace reconciliation; and
- `05b1ede` — entry-mode and variable-editor layout refinement.

### 2. Bounded deterministic clarification and AnalysisPassport v2

The pre-existing six-task resolver was extended with a finite counterfactual
clarification planner, bounded minimax question ordering, refusal/replanning tests,
strict plan decoding, AnalysisPassport v2 authority binding, one-active-passport
semantics, and a verified explanation of why a question ranked ahead of its runner-up.

Representative commits:

- `f8d5e75` — bounded minimax clarification search;
- `f0c0230` and `a42aca4` — refusal and policy-oracle tests;
- `8ad5bc5` — AnalysisPassport v2 contract;
- `6fe2018` — one active v2 passport;
- `4492cab` — minimum-rank selection enforcement; and
- `a5e91e1` — verified question-rationale projection.

This is deterministic policy and explanation-fidelity work. It is not recommendation
accuracy, human gold, or proof of research correctness.

### 3. History-preserving release integration

The independently developed release shell and Research OS history were integrated with
an explicit conflict ledger, source manifest, test-identifier union check, package gate,
and no-auto-run boundary preservation.

Representative commits:

- `c67b81a` — two-parent integration merge; and
- `fc00d82` — integration evidence.

The integration evidence is in
`docs/qa/research-os-release-integration-evidence.md`. It records local evidence only;
it did not claim a public release.

### 4. Durable local multi-round Research OS flow

The contract foundation was extended into an end-to-end local workflow with exact
dataset identity, bounded task indexing, intake, recoverable sessions, durable
multi-round state transitions, passport-bound analysis preparation, asynchronous UI
projection, and a live QML flow.

Representative commits:

- `9f917aa` — live flow contracts;
- `451afca` — full dataset-identity binding;
- `7166317` — bounded intake;
- `1f9aea5` — recoverable task sessions;
- `cdcb15a` — durable multi-round flow;
- `b3f337b` — passport binding to exact analysis steps;
- `e9719ee` — asynchronous flow exposure; and
- `a0edd30` — live Research OS QML flow.

The runtime method space remains exactly six local tasks. It has no verified external
route, no runtime SLM/LLM, and no automatic calculation execution.

The final functional-usability pass adds a dataset-bound Variable Meaning Gate before
the first durable request commit. It displays recorded metadata and explicitly reports
an unavailable conceptual definition or unit rather than inferring either. An
automated actual-QML Korean novice E2E verifies import, metadata review, the meaning
gate, durable clarification, configuration confirmation without calculation, a
separate Run, Word export, and fail-closed replanning after metadata drift. That one
automated path does not
establish equivalent end-to-end coverage for every task or language.

Representative commits:

- `ed8bcae` — Variable Meaning Gate and authority binding;
- `17815ef` — duplicate integration-residue cleanup; and
- `b368cdc` — functional-usability audit and bounded evidence record.

### 5. Release and constrained-hardware evidence hardening

The live Research OS path received visual population tests, response gates, file-
operation audits, a complete development-PC office protocol, a sealed portable kit,
legacy Win32 path-bound recovery, mutation rejection, and deterministic kit build
hardening.

Representative commits:

- `df462e4`, `f4d35cd`, and `6b81883` — visual and response gates;
- `d59a07f` — file-operation audit;
- `bb8ab1e` — live office-benchmark contract;
- `4551122` — sealed live Research OS office kit;
- `91065b4` and `c484931` — legacy path boundary recovery; and
- `989d5c5` — deterministic source-date-epoch pin.

The sealed kit source/build identity is
`989d5c5829e3d3de69ebda0f4fc88e6f76d16112`, and its recorded ZIP SHA-256 is
`6f567b327ad53c68eff5f27623e494c1273f9a424e11896e99c5d9f5a0bb8d43`.
The development-PC B4-R evidence records `3233 passed, 13 skipped`, 300 rejected
sealed mutations, and three byte-identical independent kit builds. The B5 low-cost HP
laptop measurement is still pending and is not described as passed.

### 6. Source-submission closure and live-path repair

The source-only submission lane added the GPL-3.0-only entry point, third-party
notices, exact Windows constraints, judge instructions, claim controls, and demo
packet. A real packaged-app walkthrough then exposed two release-path contract
mismatches that narrower component tests had not caught:

- the Research OS preparation editor retained the initial pipeline-operations object
  after an import replaced the active pipeline; and
- the run validator accepted only the manual correlation parameter form even though
  the sealed Research OS path emits an engine-supported pair form.

The sealed release baseline first resolved the import mismatch through a forwarding
adapter. The later functional integration supersedes that adapter with the more direct
`pipeline_ops_provider=lambda: owner._services.pipeline_ops` boundary and retains the
broader real import-to-Word-export E2E. Correlation migration and validation continue
to delegate to the correlation step's canonical contract. The superseded adapter and
narrower regression remain recoverable in `6169552`; they are not duplicated in the
final tree. These are submission-blocking interoperability repairs, not a new
statistical method or an expansion beyond the six-task scope.

The merge decision and original dirty-file SHA-256 inventory are recorded in
`docs/build-week/INTEGRATION_LEDGER.md`. The local merge commit `4260ed8` has parents
`6169552` and `b368cdc`.

After the immutable `b223` functional freeze and its direct documentation-audit child
`8e4e6f91`, a final claim-fidelity review found one misleading result affordance. The
underlying Cronbach's alpha explanation was valid, but its label and visibility could
be read as a generic explanation of why an analysis had been selected. Commit
`4253844` added a typed reliability-result gate, hid the affordance for empty,
correlation, and unsupported results, and relabelled it as Cronbach's alpha help. It
did not create a passport- or ledger-backed selection rationale, infer provenance, or
expand the six-task method space.

The first exact non-gallery observation on that working tree retained two failures:
one expected stale integration-ledger blob binding and one full-suite-only Word publish
exception. After rebinding the ledger, the actual-QML novice E2E completed in ten
separate processes, and a fresh exact non-gallery run reported
`3292 passed, 5 skipped in 367.62s` with pinned R 4.5.3. The Word exception did not
recur, but is not declared impossible or attributed to load. The README-only child
`35e5d70` preserves the `4253844` source and tests trees and supplies the metadata for
the final ignored local package candidate.

A fresh packaged English correlation walkthrough then directly exercised import,
the Variable Meaning Gate, all three clarifications, configuration confirmation with
no calculation, a separate Run, the exact result, and actual English Word creation.
The existing Korean numeric-distribution E2E remains the evidence for metadata-drift
recovery. These are separate bounded paths, not all-method or full-bilingual evidence.

## Codex and GPT-5.6 evidence boundary

The owner reports that the eligible extension was developed through Codex sessions
using GPT-5.6. Within those sessions, Codex was used for repository-grounded design,
implementation, adversarial review, test construction, integration analysis, live
Windows release-path verification, and release auditing. The owner retained authority over product scope, claim boundaries,
licensing, hardware operation, and release decisions.

Git commit authorship and timestamps establish repository history but do not establish
model identity. The required model-bound evidence is the `/feedback` Session ID from
the primary thread where most core functionality was built. That ID is intentionally
not invented in this repository and remains pending owner capture for the Devpost form.

The release README and demo must describe GPT-5.6 as a build-time collaborator. Modori
does not contain a runtime GPT-5.6, LLM, or SLM integration.

## Claims this delta does not support

This history does not establish:

- validated recommendation accuracy;
- equivalence or superiority to a professor, qualified researcher, SPSS, JASP, jamovi,
  or another statistics package;
- broad or complete social-science-method coverage;
- complete numerical correctness for arbitrary data;
- complete accessibility or complete Korean/English UI coverage;
- any verified external route;
- a B5 HP laptop pass; or
- public prebuilt-binary readiness.
