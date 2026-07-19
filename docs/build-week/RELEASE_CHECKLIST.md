# Build Week Release Checklist

Owner's internal hard deadline: **2026-07-21 KST**

Official no-edit deadline: **2026-07-22 09:00 KST** (2026-07-21 17:00 PDT)

Release policy: GPL-3.0-only source submission. No prebuilt executable or installer is
published. GitHub Actions availability is not a release condition; auditable local
evidence is used instead.

## Immediate owner-only blockers

These three actions cannot be completed by the release agent and must finish within
the owner's 2026-07-21 KST internal deadline.

| Owner action | Target | Hard boundary |
| --- | --- | --- |
| In the existing primary core-build task, run `/feedback`, choose to share that existing session, and copy the returned Session ID | immediately | before final Devpost submission |
| Record the approved 2:55 English demo with matching subtitles and upload it as **Public** YouTube | by 2026-07-21 12:00 KST | before the internal submission review |
| Check the repository and video signed out, review the final Devpost preview, and submit | target 2026-07-21 20:00 KST | internal hard deadline 2026-07-21 KST; official deadline 2026-07-22 09:00 KST |

Do not close the existing long-running build task before capturing its `/feedback`
Session ID. This release-audit task is not a substitute Session ID. Send the
Fable-edited story to this lane as soon as it is available; repository evidence and
`CLAIM_MATRIX.md` decide every technical fact.

## P0 repository closure

- [x] Start from clean integrated baseline
      `eaa0e802a0c64f6619297432f129be4d198a79ea` in an isolated release branch.
- [x] Seal the original dirty source-release work at
      `616955232d91aa322da66cb21a8865ec686ba87f` with its SHA-256 inventory.
- [x] Integrate `b368cdcf208d04509717826bc6b0ab7e7b72ba7e` through the two-parent
      merge `4260ed862a74fee094b9a94c42ffe95fd7fe4c64`, resolving only the two
      recorded overlaps by meaning; the integration cohort reported `57 passed`.
- [x] Audit top-level entry point, dependency and asset licenses, workflow triggers,
      packaging instructions, public-repository distance, and claim boundaries.
- [x] Obtain owner approval for the GPL-3.0-only, source-only path.
- [x] Add top-level English README and full GPL-3.0-only license text.
- [x] Add third-party dependency, font, icon, NIST, synthetic-fixture, and uncertain
      Rdatasets/psych fixture notices.
- [x] Separate pre-existing foundations from post-cutoff Build Week work.
- [x] Add exact Windows/Python dependency constraints and a bounded judge smoke path.
- [x] Draft a sub-three-minute English demo, subtitles, screenshot plan, and Devpost
      technical fields.
- [x] Retarget the written demo to the Royal Blue workflow, Variable Meaning Gate,
      source read-only boundary, separate Run, and post-Run Word export.
- [x] Audit the final integrated demo path in the live Windows GUI and record the
      exact direct-observation boundary separately from the test-only fresh Research
      OS path and Word-file creation evidence.
- [x] Create a fresh constrained Python 3.12 environment from the README commands.
- [x] Build and inspect final local wheel metadata and license contents; do not publish
      the wheel as a submission artifact.
- [x] Run the isolated judge engine smoke, public-data smoke, and four-file Research OS
      cohort; copy the engine input below `.tmp` so generated reports do not touch the
      fixture tree.
- [x] Let one merged-tree all-tests observation finish and retain its failed result;
      separate the wrong-R, sandbox-TEMP, timeout, and real localization outcomes
      without relaxing any threshold.
- [x] Run the corrected final non-gallery suite with explicit R 4.5.3, the local
      PyInstaller build, and all three packaged smokes on the source-under-test later
      frozen as `b2235dabbe01258ae68be4f49bcbb974777a9578`.
- [x] Reattribute `4 passed, 3301 deselected in 28.05s` to the pre-final tree and
      record the independent exact-`b223` slow-statistics result:
      `4 passed, 3302 deselected in 43.91s`, exit code `0`.
- [x] Document the exact non-gallery pytest command separately from
      `scripts/quality_gate.py`, whose full pytest invocation includes the gallery.
- [x] Record exact exit codes, test counts, durations, artifact size, SHA-256,
      warnings, skips, and the non-stable visual boundary in `VERIFICATION.md`.
- [x] Run final documentation-link, prohibited-claim, whitespace, and Git-state audit.
- [x] Preserve `b223` as the immutable functional freeze and commit this minimal
      documentation-only audit correction as its direct child.

## Public repository plan

- [ ] Report the exact local release branch, commit sequence, verification result, and
      proposed GitHub commands to the owner before changing public state.
- [ ] After approval, push only `codex/modori-build-week-release-p0` first.
- [ ] Confirm the pushed branch and commit in a signed-out GitHub view.
- [ ] Merge or fast-forward into the public default path only under the separately
      reported plan; do not silently change the default branch or rewrite history.
- [ ] Confirm that `https://github.com/anomalia0287-ai/modori` opens directly to the
      final README, license, notices, sample, tests, and Build Week evidence.
- [ ] Confirm no `dist`, installer, private evidence, account path, or secret entered
      the commit.
- [ ] Record the final public default branch and HEAD in `VERIFICATION.md` and Devpost.

## Final cross-surface audit

- [x] README, repository Devpost story, pitch, captions, and narration describe the same six-task
      scope and source-only artifact.
- [x] Codex/GPT-5.6 are described as meaningful build-time collaborators, not runtime
      analyzers.
- [x] Every test count, commit, and hash has a matching repository evidence record.
- [x] B4-R numbers remain bound to commit `989d5c5...` and the recorded kit SHA-256.
- [x] B5 remains **pending** unless a separate measured protocol is later completed.
- [x] Zero verified external routes, incomplete full bilingual support, unvalidated
      recommendations, unproven expert/SPSS parity, and incomplete accessibility remain
      explicit.
- [x] Imported source cells remain documented as read-only; transformations are new
      steps/variables and changed source values require re-import and review.
- [x] Mixed cold-render observations remain explicitly uncharacterized; neither the
      roughly 200–217 ms passes nor the roughly 292–303 ms failures are hidden, and the
      250 ms gate is unchanged.
- [x] No new feature work was introduced during release closure.

## Post-P0 lane

Run B5 on the low-cost HP laptop only after the submission-critical repository,
license, demo, evidence, and Devpost packet are closed. A B5 failure or incomplete run
must be reported as such and must not rewrite the already accepted B4-R evidence.
