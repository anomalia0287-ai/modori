# Research OS Release Integration Evidence

- Plan date: 2026-07-16
- Evidence capture date: 2026-07-17
- Status: P0 local integration evidence
- Integration branch: `codex/research-os-release-integration`
- Worktree notation: `%USERPROFILE%\Desktop\TongTong\.worktrees\research-os-release-integration`

## Decision

P0 is accepted locally at the recorded merge commit. The frozen release product shell
and frozen Research OS feature set coexist in one history-preserving tree, every shared
path has a verified disposition, every permitted parent-only adaptation is hash-bound,
the parent test-identifier union is preserved, and the complete local package gate
passes. No push, pull request, release-branch merge, or public-release claim is part of
this evidence.

## Immutable identities

| Item | Identity |
|---|---|
| Release parent | `ca40471297da5f69e90c4519a28ecf0864fd1c08` |
| Research OS parent | `247f8f5d80c8045080510cdffa12fe88f1271cbb` |
| Merge base | `4e1170c58af35edc20e172f616b51d3464a5a2ef` |
| Two-parent merge | `c67b81af432a14aeb9a29d6dddc79eb90510a82b` |
| Ordered parents | release parent first, Research OS parent second |
| Source manifest | `docs/qa/research-os-release-integration-source-manifest.json` |
| Conflict ledger | `docs/qa/research-os-release-integration-conflict-ledger.json` |
| Machine report | `docs/qa/research-os-release-integration-verification.json` |

The release and Research OS source worktrees were rechecked at these exact commits and
both remained clean immediately before the merge commit. A later attempt to rerun the
release suite in its frozen worktree was rejected because tests may create temporary
files there; that refusal was not bypassed. The exact source results below come from
the already completed pre-merge gates in the task record.

## Runtime

| Component | Verified version |
|---|---|
| Python | 3.12.10 |
| SQLite | 3.49.1 |
| PySide6 | 6.11.1 |
| Qt | 6.11.1 |
| R / Rscript | 4.5.3 (2026-03-11) |
| PyInstaller | 6.21.0 |
| Host platform recorded by package build | Windows 11, 64-bit |

No Windows account name, hostname, or absolute user path is part of the committed
evidence.

## Frozen source baselines

| Source | Exact recorded result | Exit |
|---|---|---:|
| Release parent | `1325 passed, 4 skipped`; slow statistics `3 passed`; compile, Ruff, Bandit, dependency check, package build, and launch/engine/public-data smokes passed | 0 |
| Research OS parent | `2148 passed, 5 skipped`; slow statistics `4 passed`; compile, Ruff, Bandit, dependency check, package build, and launch/engine/public-data smokes passed | 0 |

The Research OS gate was rerun after the bounded data-preparation correction and
returned the same `2148 passed, 5 skipped` result with top-level exit 0 before the
Research OS SHA was frozen.

## Conflict and provenance census

| Check | Result |
|---|---:|
| Shared changed paths | 38 |
| Changed in both | 36 |
| Added in both | 2 |
| Release-only changed paths | 127 |
| Research-OS-only changed paths | 268 |
| Verified shared ledger entries | 38 |
| Hash-bound branch-only adjustments | 10 |
| Unresolved paths | 0 |
| Conflict-marker or merge-residue paths | 0 |
| Required parent test IDs | 1,881 |
| Test IDs present in merge | 1,896 |
| Missing parent test IDs | 0 |
| Unledgered branch-only mismatches | 0 |

The ten adjustments are the exact paths listed in the machine report. The verifier
rejects unrecorded, duplicate, unknown, forged, incomplete, or unnecessary adjustment
records.

## Integration verification

### Focused and structural gates

- Final combined integration suite: `473 passed in 95.54s`, exit 0.
- Report-export/QML regression cohort after responsibility extraction:
  `116 passed in 33.57s`, exit 0.
- Integration verifier unit suite was included in the focused gate.
- `UiController` frozen limits remain 560 lines, 60 methods, and 45 lines per method.
  The accepted tree measures 531 lines, 53 methods, and a 44-line longest method.
- Scoped staged whitespace check: zero findings.

The first complete gate was intentionally stopped by the unchanged facade limit after
`2472 passed, 5 skipped`: the semantic union had produced a 576-line `UiController`.
The limit was not raised. A failing-first ownership test preceded extraction of only
the stateless QML report-export adapters into an integration-authored mixin.

### Final complete gate

Command contract:

```text
scripts/quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
```

Fresh result at the merge tree:

- compileall: pass;
- Ruff: `All checks passed!`;
- Bandit recursive source scan: pass;
- launch smoke: `launch-smoke-ok`;
- full pytest: `2474 passed, 5 skipped in 255.56s`, exit 0;
- dependency check: `No broken requirements found.`;
- Windows package check: `package-tool-ok`;
- Windows package build: pass, producing `dist\Modori\Modori.exe`;
- packaged launch: `package-launch-smoke-ok`;
- packaged engine: `package-engine-smoke-ok`;
- packaged public data: `package-public-data-smoke-ok`;
- slow statistics: `4 passed, 2475 deselected in 32.22s`, exit 0;
- top-level quality gate: exit 0.

The five understood skips were:

1. one `paired_comparison` case that does not require recommendation eligibility;
2. three bootstrap-adequacy cases delegated to the separately executed slow gate; and
3. one factorial-ANOVA performance case delegated to the separately executed slow gate.

PyInstaller reported two non-fatal warnings: an absent optional Qt Labs asset-downloader
plugin binary and an unavailable hidden import `scipy.special._cdflib`. They are not
silently classified as harmless in isolation; acceptance rests on the successful
package launch, engine, public-data, explanation-library, and slow-statistics probes.

### Machine verifier

`scripts/verify_release_integration.py verify` returned `ok: true` for the exact merge
commit. It confirmed the ordered parents, 38 shared paths, 10 accepted adjustments,
zero branch-only blob mismatches, zero missing parent test IDs, and zero merge residue.

## Human-operated package evidence

The rebuilt Windows application was opened directly from the packaged executable with
the public `psych_bfi.csv` fixture. The operator selected Casual mode, explicitly chose
the A1-A5 reliability candidate, opened its rationale and review surface, confirmed the
configuration, and ran it. The review retained `A1, A2, A3, A4, A5`; the result surface
reported approximately Cronbach alpha 0.43 and omega 0.59. This proves the packaged
selection/review/run path and explanation resource are reachable. It does not prove
that those statistics are substantively suitable for a real study.

## Preserved boundaries

- No legacy heuristic recommendation reason was relabelled as AnalysisPassport or
  passport-rationale evidence.
- No live multi-round Research OS UI was added in P0.
- Experimental candidates remain non-automatic and require explicit selection,
  configuration review, confirmation, and a separate run action.
- The deterministic resolver remains authoritative; SLM output is not connected.
- No network service, cloud model, telemetry, or real user data was used.
- Imported authority remains downgraded and cannot promote itself.
- Evidence bundles remain quarantined and local promotion remains explicit.
- Neither source worktree was modified.
- The package explanation library is bundled and probed; explanation failure is
  bounded and cannot erase a prepared recommendation.

## Non-claims and remaining boundary

P0 does not establish recommendation validity, numerical correctness of every method,
human or professor equivalence, superiority over SPSS, full social-science coverage,
complete accessibility conformance, office-PC performance, or public release
readiness. Model agreement and self-grading are not human gold. The earlier HP office
benchmark is evidence about the ledger/import-memory path only, not these broader
claims.

The next authorized phase is P1: live, local, deterministic multi-round Research OS UI
wiring over the already implemented StudySpec, Method Space, resolver, AnalysisPassport,
and question-rationale contracts. P1 must preserve the same explicit authority and
non-automatic execution boundaries and must be verified independently before any later
phase begins.
