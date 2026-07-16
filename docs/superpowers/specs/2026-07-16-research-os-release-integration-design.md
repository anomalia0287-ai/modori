# Research OS Release Integration Design

**Date:** 2026-07-16

**Status:** P0 direction approved; written specification pending owner review

**Design branch:** `codex/research-os-contract-design`

**Audit baselines:**

- release lane: `release/readiness-1-9` at `53e358e7bee534396579a46ebb24b7b0dcbd773a`
- Research OS lane: `codex/research-os-contract-design` at
  `e086bc724f093c3a6d7bfc7f6c307dccf6e7f065`
- merge base: `4e1170c58af35edc20e172f616b51d3464a5a2ef`

The audit baselines describe the state inspected for this design. They are not the
execution pins. The execution pins are captured only after this specification and its
implementation plan are committed and both source lanes satisfy the freeze protocol.

## 1. Decision

Integrate the two histories by creating a third, dedicated worktree and a new branch
from a clean, pinned `release/readiness-1-9` commit, then perform one history-preserving,
semantic merge of the pinned Research OS branch into it.

The intended integration identity is:

- branch: `codex/research-os-release-integration`
- worktree: `C:\Users\V\Desktop\TongTong\.worktrees\research-os-release-integration`
- first parent: the frozen release commit
- second parent: the frozen Research OS commit

Neither source worktree is modified, switched, stashed, reset, cleaned, or used to
resolve conflicts. No direct merge is made into either source branch. The integration
branch remains local until all P0 gates pass.

P0 produces a single coherent source tree with both histories and both verified feature
sets. It does **not** connect the live UI to the new multi-round Research OS, publish a
release, make a pull request, or make a recommendation-validity claim. Live Research OS
UI wiring is the next separately tested slice.

## 2. Audited facts and risk assessment

The read-only audit found:

1. The release lane has 59 commits not in the Research OS lane; the Research OS lane has
   163 commits not in the release lane at the audit baselines.
2. Since the merge base, the release lane changes 139 paths and the Research OS lane
   changes 300 paths.
3. Only 38 paths are changed by both lanes: 2 documentation paths, `pyproject.toml`, 5
   scripts, 2 non-UI runtime paths, 8 UI runtime paths, 6 core tests, and 14 UI tests.
4. A three-way preview reports 36 `changed in both` conflicts and 2 `added in both`
   conflicts. There are no audited rename/delete conflicts.
5. The other 101 release-only paths and 262 Research-OS-only paths are disjoint at the
   path level. A whole-history merge therefore has substantially lower silent-omission
   risk than selecting and copying features.
6. The release worktree is currently dirty with 45 modified or untracked entries from an
   active visual-finish slice. Seven of those paths are also in the 38-path conflict set:
   `DataGridView.qml`, `GuideRail.qml`, `PipelineRail.qml`, and four corresponding UI
   tests. The current release commit is therefore not yet a safe execution pin.
7. The Research OS audit baseline is clean and its canonical local gate passed with
   Ruff, Bandit, compile, launch smoke, dependency check, and `2135 passed, 5 skipped`.
   This is source-lane evidence, not merged-tree evidence.

The merge is feasible, but it is not a mechanical “take ours” or “take theirs” job. The
high-risk overlap is concentrated in shared controllers, packaging gates, the guided
rail, and tests that encode both product generations.

## 3. Alternatives considered

### 3.1 Recommended: release-first semantic merge

Use the frozen release lane as the product shell and merge the complete Research OS
history into it. Preserve release UI, accessibility, installer, and packaging behaviour;
preserve Research OS, decision-ledger, quarantine, passport, planner, and statistical
coverage behaviour; reconcile shared files by their contracts rather than by branch.

Benefits:

- preserves both parent histories and makes omissions auditable;
- retains the release lane as the first-parent product history;
- keeps the current visual and packaging work as the outer product shell;
- imports 262 Research-OS-only paths without reconstructing them by hand; and
- confines risk to a known conflict ledger.

Cost: the 38 shared paths require deliberate semantic reconciliation and focused tests.

### 3.2 Rejected: Research-OS-first merge

Starting from the Research OS branch and merging the release lane could produce an
equivalent final tree, but it makes the experimental backend history the first-parent
product lineage. It also makes it easier to accidentally regress current installer,
visual, settings, and accessibility behaviour while treating the release shell as an
add-on. There is no compensating technical advantage.

### 3.3 Rejected: feature transplant or long cherry-pick sequence

Copying `research_os/`, `research_memory/`, selected tests, and selected commits appears
to reduce visible conflicts. In reality it moves conflict resolution out of Git and into
human memory. The Research OS lane also changes reporting, validation, packaging,
quality gates, strings, and controllers. Selective transplant would make a missed
dependency or safety test hard to detect and fragment provenance across 163 commits.

### 3.4 Forbidden shortcut: wholesale branch preference

`git checkout --ours` or `--theirs` across a conflict cohort is not an integration
strategy. Examples already show why: the release controller contains current product
properties absent from the Research OS lane, while the Research OS controller contains
selection-origin and experimental-confirmation boundaries absent from the release lane.
Both behaviours must survive when they do not contradict one another.

## 4. Scope and non-goals

P0 includes:

- source freeze and immutable SHA capture;
- an isolated integration worktree and branch;
- one merge commit with both source pins as parents;
- a per-path conflict-resolution ledger;
- semantic reconciliation of all 38 conflicts, recalculated at the execution pins;
- source-feature and test-census checks;
- focused, full-suite, QML runtime, quality, and local packaging verification; and
- an integration evidence record.

P0 excludes:

- live multi-round clarification UI wiring;
- presenting legacy heuristic reasons as AnalysisPassport evidence;
- credits UI, licence selection, or public release wording changes;
- additional visual redesign beyond preserving the frozen release source;
- validity-pilot annotation or claims;
- new statistics modules, new dependencies, SLMs, cloud teachers, or model training;
- office-PC release qualification; and
- push, pull request, merge to the release branch, branch deletion, or cleanup of any
  existing worktree.

## 5. Source freeze protocol

Integration may start only when all of the following are true:

1. `release/readiness-1-9` has a clean worktree, including no untracked visual artifacts.
   The integration owner never commits, discards, stashes, or cleans another session's
   release changes.
2. The active visual-finish owner has either committed its intended slice or explicitly
   ended it. Silence is not permission to ignore the dirty tree.
3. The Research OS design and implementation-plan commits are complete and its assigned
   worktree is clean.
4. Fresh source SHAs, merge base, ahead/behind counts, changed-path counts, and conflict
   inventory are recorded.
5. Each pinned source passes its own baseline verification. A failing source baseline is
   repaired on its owning lane or explicitly removed from P0 by a revised design; it is
   not concealed inside the merge.
6. The branch references still point to the recorded SHAs immediately before the merge.

After capture, the merge uses the immutable SHAs, not moving branch names. Later commits
on either source lane require a separate follow-up merge after P0, not an in-flight change
of inputs.

## 6. Isolation and authority rules

The integration worktree is a third workspace. Existing release, Research OS, statistics,
recommendation-benchmark, data-transform, and visual worktrees remain untouched.

The integration branch may use the already verified local Python and R runtimes, but all
source writes, generated evidence, test caches, and merge state remain inside the new
worktree. No user dataset is used. Fixtures are public or synthetic. No cloud model,
network service, or GitHub Actions run is required for P0.

The merge must preserve these authority boundaries:

- Research OS outputs remain hypotheses until the deterministic resolver accepts them;
- legacy heuristic recommendation state is not relabelled as passport-backed evidence;
- imported evidence remains quarantined and authority-downgraded until local promotion;
- the SLM prohibition and local-only runtime boundary remain intact;
- calculation accuracy, recommendation validity, and persistence feasibility remain
  separate claims; and
- experimental recommendation candidates never become automatic execution.

## 7. Merge and conflict-resolution architecture

The integration branch starts at the frozen release SHA. The frozen Research OS SHA is
merged with `--no-ff --no-commit`. Before editing, the preview conflict inventory is
compared with the audited inventory and written into the conflict ledger.

Conflicts are handled in six cohorts:

1. documentation and dependency metadata;
2. packaging, smoke, and quality-gate scripts;
3. application bootstrap and statistical reporting;
4. Python UI contracts, controllers, validation, and strings;
5. QML shared surfaces; and
6. core and UI tests.

Each conflict-ledger row records:

- path and conflict kind;
- behaviour added by the release lane;
- behaviour added by the Research OS lane;
- chosen semantic union or explicit supersession;
- invariants that must remain absent as well as present;
- focused verification command and result; and
- any intentionally superseded test or text, with a reason.

### 7.1 Resolution ownership matrix

| Surface | Required resolution |
|---|---|
| Release-only UI, theme, settings, accessibility, installer paths | Preserve the frozen release version. Research OS code may not restyle them during P0. |
| Research-OS-only `research_os/`, `research_memory/`, planner, passport, ledger, quarantine, benchmark, factorial-ANOVA, and logistic-regression paths | Preserve the frozen Research OS version and its tests. |
| `pyproject.toml` | Form a dependency and tool-configuration union. No dependency is removed merely because one lane did not know it. No new dependency beyond the two pins is introduced. |
| Packaging and quality scripts | Preserve the superset of package contents, fail-closed checks, security scans, statistical smoke cases, and Research OS smoke cases. A green result produced by dropping a check is a failure. |
| `app.py` and `steps/reporting.py` | Retain release bootstrap/engine behaviour and Research OS statistical/reporting additions. Dispatch remains explicit; unknown analysis families fail closed. |
| UI contracts, controller, recommendation controller, validation, and strings | Reconcile API and state semantics. Current release properties and current Research OS authority/selection properties both survive unless a written conflict row proves they are mutually exclusive. Closed copy is not freely rewritten. |
| `DataGridView.qml`, `GuideRail.qml`, and `PipelineRail.qml` | Preserve the frozen release visual/accessibility structure and the Research OS experimental/provenance boundaries. Do not create live Research OS visibility during P0 and do not route the new rationale presenter from legacy heuristic state. |
| Conflicting tests | Preserve the behavioural union. Renaming or consolidating a test is allowed only when the ledger maps both original assertions to the replacement. Deleting or weakening an assertion to obtain green is forbidden. |
| Added-in-both design document | Reconcile the stronger boundary clauses and retain a single internally consistent specification; do not select a version solely by length or recency. |

## 8. Verification and evidence

### 8.1 Pre-merge baselines

For both frozen source pins, record:

- `git status`, exact SHA, branch, and merge base;
- Python, SQLite, Qt, R, and critical statistics dependency versions;
- compile, Ruff, Bandit, dependency, launch-smoke, and full pytest output;
- QML runtime-load result; and
- source-specific package smoke where applicable.

The source branches need not have identical test counts. Each must be independently
green before their evidence can diagnose a merged regression.

### 8.2 Merge census

Before conflict resolution, generate three manifests from the frozen pins:

1. release-only changed paths;
2. Research-OS-only changed paths; and
3. shared changed paths.

After resolution:

- every branch-only path must exist with its pinned content unless the conflict ledger
  records an intentional generated-artifact exclusion;
- every shared path must have a ledger disposition;
- both source SHAs must be ancestors of the final merge commit;
- test module and test-function inventories from both parents must be represented in the
  merged tree or mapped to explicit replacements; and
- no conflict marker, merge backup, worktree path, or generated user/environment identity
  may remain.

### 8.3 Focused gates

Run focused tests after each resolved cohort where the unresolved merge state permits
them. At minimum, verify:

- package-environment, Windows-package, engine-smoke, public-data-smoke, and quality-gate
  tests;
- app engine smoke and report rendering, including factorial and logistic outputs;
- controller, recommendation, run-validation, pipeline, strings, and security/privacy
  tests;
- QML runtime load, data-grid, guided/standard flow, result-surface, mode, focus, and
  accessibility contracts;
- Research OS resolver, counterfactual planner, passport, transition, decision-ledger,
  evidence-bundle, quarantine, promotion, and rationale suites; and
- a negative provenance test proving that legacy `recommendationReason` cannot populate
  a passport-backed rationale surface.

### 8.4 Final gates

P0 is accepted only after fresh merged-tree evidence shows:

1. compile and import smoke pass;
2. Ruff and Bandit pass without suppressing a new finding merely for integration;
3. dependency consistency passes;
4. all focused tests pass;
5. the full pytest suite passes with no unexplained new skip or deselection;
6. QML loads in both Guided and Standard modes at the supported baseline;
7. local packaging succeeds and its engine/public-data smoke exercises both the release
   statistics bundle and the integrated Research OS boundary;
8. the merge census and ancestry assertions pass;
9. the worktree is clean; and
10. the evidence record contains commands, versions, counts, source pins, merge commit,
    and conflict dispositions.

The final office-PC performance rerun remains a later release gate. P0 local packaging
evidence does not establish low-end-PC latency, recommendation validity, numerical
accuracy, SPSS superiority, or release readiness.

## 9. Stop conditions and recovery

Stop before creating the integration worktree if the release source remains dirty or
either source reference moves during pin capture.

Abort the merge in the dedicated integration worktree, leaving both sources unchanged,
if any of these occurs:

- the fresh conflict inventory introduces rename/delete ambiguity in authority-bearing
  Research OS, ledger, quarantine, or package-verifier paths;
- a source baseline fails and the failure cannot be separated from the intended source
  change;
- preserving one lane requires weakening the other lane's privacy, authority, integrity,
  numerical, or fail-closed contract;
- the only route to green is deleting tests, lowering thresholds, adding exclusions, or
  relabelling a legacy heuristic as Research OS evidence;
- packaging requires an unreviewed dependency or network access; or
- focused remediation repeatedly fails and the remaining change is no longer bounded
  enough to review path by path.

For an ordinary textual or API conflict, first attempt a semantic union and write a
regression test. If that is unreasonable or repeatedly fails, stop the integration and
revise the contract explicitly. Do not silently choose a side.

The fallback is not selective copying. The fallback is to keep both proven source lanes
intact, document the unresolved boundary, and design a narrower adapter or schema change
before another integration attempt.

## 10. Acceptance result and handoff

The P0 handoff consists of:

- the clean integration branch and two-parent merge commit;
- the frozen-source manifest;
- the 38-path-or-updated conflict ledger;
- the feature/test census;
- the merged verification evidence; and
- an explicit list of deferred P1 live-UI work.

Only after that handoff is reviewed may the next slice connect the live, current
AnalysisPassport V2 and clarification state to the UI. P0 success means “the two proven
code histories coexist without a detected regression.” It does not mean “the Research OS
is already visible or scientifically validated in the product.”

## 11. Non-developer analogy and its limit

The release lane is a renovated vehicle body with controls, seats, safety indicators,
and an installer. The Research OS lane is a separately tested engine, black box, and
navigation logic. P0 does not bolt the engine onto whichever wires happen to fit. It
builds a third prototype, records every shared connector, and proves that neither the
brakes nor the navigation was discarded during the transplant.

**Analogy loss point:** software connectors carry state, authority, provenance, and
failure semantics that are invisible from the outside. A screen that opens and an engine
that runs are insufficient. The merged contracts, negative tests, ancestry, packaging,
and complete suite are the evidence that the integration did not merely look successful.
