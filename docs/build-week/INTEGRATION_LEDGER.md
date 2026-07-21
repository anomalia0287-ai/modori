# Build Week P0 Integration Ledger

Date opened: 2026-07-20 KST

Worktree: local linked release worktree (personal path intentionally omitted)

Release branch: `codex/modori-build-week-release-p0`

## Identities

| Role | Commit | Relationship |
| --- | --- | --- |
| Dirty release baseline | `eaa0e802a0c64f6619297432f129be4d198a79ea` | current HEAD before sealing |
| Functional-usability candidate | `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` | 12 commits ahead of the same baseline |
| Merge base | `eaa0e802a0c64f6619297432f129be4d198a79ea` | verified with `git merge-base` |
| Sealed release-side baseline | `616955232d91aa322da66cb21a8865ec686ba87f` | preserved the original release-side work before integration |
| Two-parent functional integration | `4260ed862a74fee094b9a94c42ffe95fd7fe4c64` | parents `6169552` and `b368cdc` |
| Historical immutable functional freeze | `b2235dabbe01258ae68be4f49bcbb974777a9578` | direct child of the integration commit |
| Documentation audit correction | `8e4e6f91cd05e51fcb5d0f3b0fbd4c0b3ff235bc` | direct `b223` child; source/tests unchanged |
| Final claim-fidelity source | `42538443501b817cedd25f858224499f4a97322e` | Cronbach result-help gating; no generic selection rationale |
| Package-metadata README child | `35e5d706861a0a4a8d8333c97df5d21a95a52e38` | README only; source/tests identical to `4253844` |

The release checkout is a linked Git worktree whose Git directory and common directory
were both resolved successfully. Their personal filesystem paths are intentionally not
published. No nested worktree is required.

## Original dirty inventory

These SHA-256 values were recorded before creating this ledger or changing any
application/release file.

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `pyproject.toml` | 1,888 | `a8869870f5b977fbb4fd049f40fdf5df238c62cda01c9ce8bee46f91c9c5cf45` |
| `src/modori/ui/controller.py` | 27,150 | `bc5d3e5868be13b2f4513850b70b5575ea5270946bc9996dbc34acc5de5cf426` |
| `src/modori/ui/run_validation.py` | 24,963 | `7d700636a4885afffcb0bce254ba88d747521ae7e81df5ba1362b468a5b5395a` |
| `tests/ui/test_research_flow_controller.py` | 48,333 | `dd9246e41ca26e799d5ed83f6212c6a1b0fc114a259dd2da04a33e1e198efe29` |
| `README.md` | 12,542 | `8f7a761dbb51818c75a85bb2992002d9d5abcc2144799d1b06345c634888befd` |
| `LICENSE` | 34,494 | `e938f77583facb40cc631cae80c9307b5d438be273c9f5ddb950b7c700308e2c` |
| `THIRD_PARTY_NOTICES.md` | 6,998 | `795990098ea5f85017457b4aedd14a8526d7c08399c4bcf7a4736ad541bdb0d2` |
| `constraints/build-week-windows-py312.txt` | 1,815 | `614ed297c9c9a865f1ff79b289d56beef695c2ce8a0ea78c39cc04289bc71068` |
| `docs/build-week/BUILD_WEEK_DELTA.md` | 10,428 | `dba3d166705e769eae6afd32e027d709e4c432a3816a0c44bfad7c390dd0fb8e` |
| `docs/build-week/CLAIM_MATRIX.md` | 5,084 | `0de19775341d9e55b8d46a3527751479e97951e79ebde420625858dcc44bc7ca` |
| `docs/build-week/DEMO_SCRIPT.md` | 7,119 | `32ed2fbd59a2e63ddd96c98b1ff9f66706c388216374435f94911d8a52d5131e` |
| `docs/build-week/DEVPOST_SUBMISSION.md` | 13,470 | `59e3ec1f3ee461851a0040bb247a0808985f45bb85d40fb755b1ac82f1081c84` |
| `docs/build-week/RELEASE_CHECKLIST.md` | 4,763 | `895ff85f0c2ca2d8053ab2201412cbb2662e688b84e749ddfeb83836f397ea58` |
| `docs/build-week/VERIFICATION.md` | 8,532 | `7a5a54fb09e9a80d4d8982d86e636665cc74dcac54e717f8738efd7d71288aea` |
| `docs/build-week/assets/demo-closing-card.svg` | 1,011 | `0173272ea58b99c78fbbac763732cd24d0ef3d2cf88e2289884edfeac3eb8c2f` |
| `docs/build-week/assets/demo-evidence-card.svg` | 2,685 | `e43d49543de045adab728ac5153b0a00e756056e2357cad7187be94fc7fafa71` |
| `docs/build-week/assets/modori-build-week-demo.en.srt` | 2,100 | `c1c64e6de81309df3c1ac644c1ac8acd8bcadf609c6ef2eb3dbc8f0a3fe59e805` |

## Path and semantic overlap

| Release-side path/change | Candidate path overlap | Meaning decision |
| --- | --- | --- |
| `pyproject.toml`: README, `GPL-3.0-only`, setuptools 77 metadata | no candidate commit changes this path | retain release change unchanged |
| `src/modori/ui/run_validation.py`: delegate correlation migration/validation to `CorrelationStep` | no candidate commit changes this path | retain release change unchanged |
| `src/modori/ui/controller.py`: `_CurrentPipelineOperations` forwarding adapter | direct overlap | preserve in the seal commit, but final tree uses candidate's more direct `pipeline_ops_provider=lambda: owner._services.pipeline_ops`; do not retain duplicate adapter |
| `tests/ui/test_research_flow_controller.py`: replaced-import confirmation regression | direct overlap | preserve in the seal commit, but final tree retains candidate's broader `test_imported_pipeline_can_confirm_research_preparation_without_running` and removes the narrower duplicate |
| top-level README, license, notices, constraints, `docs/build-week/**` | no candidate path overlap | retain, then update claims against integrated behavior and fresh evidence |

## Pre-integration verification

Command:

```powershell
py -3.12 -m pytest -q -p no:cacheprovider tests\ui\test_run_validation.py tests\ui\test_research_flow_controller.py
```

Observed on the original dirty tree: `54 passed in 17.67s`, exit code `0`.

## Candidate evidence boundary

The candidate branch records `3289 passed, 5 skipped` for its final non-gallery suite,
plus Ruff, compile, and launch-smoke passes. Those observations remain bound to
`b368cdcf208d04509717826bc6b0ab7e7b72ba7e`. The separate final merged-source result
is recorded in `VERIFICATION.md`; neither count is silently transferred between trees.

Cold-render observations are mixed: earlier runs failed the 250 ms gate at
approximately 292–303 ms, while independent repeats observed approximately 200–217
ms. This is not stable performance characterization and must not be presented as a
pass. No threshold will be changed for submission.

## Merge policy

1. Seal the entire original dirty inventory in its own commit.
2. Merge the exact candidate commit with `--no-ff --no-commit` so both histories remain
   visible.
3. Resolve every reported conflict by reading both meanings; do not use blanket
   ours/theirs selection.
4. Require the live pipeline provider and the real import-to-Word-export E2E in the
   final tree.
5. Run targeted tests before completing the merge, then update this ledger with the
   merge identity and result.
6. Do not push or change the public default branch until the final local candidate and
   exact external execution plan have been reported.

## Execution record

- Seal commit: `616955232d91aa322da66cb21a8865ec686ba87f`.
- Seal-stage whitespace check: clean.
- Seal baseline: `54 passed in 17.67s` for the two affected test modules.
- Local merge source: `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` with
  `--no-ff --no-commit`.
- Actual conflict set: exactly `src/modori/ui/controller.py` and
  `tests/ui/test_research_flow_controller.py`; no unexpected path conflict occurred.
- Controller resolution: removed `_CurrentPipelineOperations` and retained
  `pipeline_ops_provider=lambda: owner._services.pipeline_ops`.
- Test resolution: removed the narrower replaced-pipeline regression and retained
  `test_imported_pipeline_can_confirm_research_preparation_without_running`.
- Post-resolution comparison: both resolved files are identical to the corresponding
  files at `b368cdcf208d04509717826bc6b0ab7e7b72ba7e`.
- Pre-commit integration cohort: `57 passed in 11.31s` for
  `test_run_validation.py`, `test_research_flow_controller.py`, and
  `test_research_os_novice_e2e.py`.
- Historical `b223` non-gallery suite after the bounded English demo-path fixes:
  `3290 passed, 5 skipped in 425.65s`, exit code `0`, with R 4.5.3 and isolated
  application state under normal Windows permissions.

The resulting two-parent merge commit is
`4260ed862a74fee094b9a94c42ffe95fd7fe4c64`, with parents
`616955232d91aa322da66cb21a8865ec686ba87f` and
`b368cdcf208d04509717826bc6b0ab7e7b72ba7e`. Before commit, three trailing-
whitespace warnings in two candidate Markdown evidence files were converted to blank
line separation without changing their wording or product evidence.

## Post-freeze claim-fidelity closure

The later source correction did not modify the integration sequence, shared-path
count, conflict count, or functional merge decision above. It narrowed a result-help
claim that had outgrown its implementation:

- `src/modori/ui/controller.py` now exposes a typed gate that is true only when an
  actual reliability `DisplayResult` exists;
- empty, correlation, and unsupported result states fail closed;
- `ResultsPanel.qml` uses that gate for its Cronbach's alpha help button;
- Korean and English strings describe Cronbach's alpha rather than why an arbitrary
  analysis was selected; and
- no passport, ledger, result-summary parsing, candidate guess, or generic selection
  rationale was introduced.

The shared-path working-tree binding ledger was updated for the changed controller
and strings blobs while retaining its seven-commit integration sequence and recorded
conflict set. The first exact non-gallery observation before that rebinding reported
`2 failed, 3290 passed, 5 skipped in 390.26s`: the stale binding was expected, while a
Word publish exception appeared only in that full-suite process. The actual-QML
novice E2E then completed in ten separate processes (`10/10` exit code `0`), and the
Word exception did not recur in the fresh full run. No impossible-to-recur or
load-cause claim is made.

The final source at `4253844` completed the exact non-gallery suite with pinned
R 4.5.3, fresh isolated state, and normal Windows permissions:
`3292 passed, 5 skipped in 367.62s`, exit code `0`. Compileall, Ruff, Bandit, source
launch, and pip check returned exit code `0`. One representative gallery contract
reported `1 passed in 39.19s`; the mixed historical 292–303 ms failures remain the
controlling reason not to claim stable cold-render performance.

The README-only child `35e5d70` retains the `4253844` source and tests trees. Its
ignored local package candidate and fresh English packaged-GUI audit are recorded in
`VERIFICATION.md`; neither artifact is a public binary.
