# Build Week Release Checklist

Deadline: **2026-07-22 09:00 KST** (2026-07-21 17:00 PDT)

Release policy: GPL-3.0-only source submission. No prebuilt executable or installer is
published. GitHub Actions availability is not a release condition; auditable local
evidence is used instead.

## P0 repository closure

- [x] Start from clean integrated baseline
      `eaa0e802a0c64f6619297432f129be4d198a79ea` in an isolated release branch.
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
- [ ] Verify the demo path against the final live GUI and correct any screen wording.
- [ ] Create a fresh constrained Python 3.12 environment from the README commands.
- [ ] Build and inspect source metadata/archive contents.
- [ ] Run the judge engine smoke, public-data smoke, and Research OS test cohort.
- [ ] Run the full local quality gate once with explicit Rscript, local PyInstaller
      build, packaged smokes, and slow statistical checks.
- [ ] Record exact exit codes, test counts, durations, artifact size, and SHA-256 in
      `VERIFICATION.md`; retain warnings and skips.
- [ ] Run final documentation-link, prohibited-claim, whitespace, and Git-state audit.
- [ ] Commit the release artifacts and final verification record locally.

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

## Owner-only actions and safe timing

These are intentionally not delegated to the release agent.

| Owner action | Recommended completion | Hard boundary |
| --- | --- | --- |
| In the existing primary core-build task, run `/feedback`, choose to share that existing session, and copy the returned Session ID | by 2026-07-20 12:00 KST | before Devpost submission |
| Record the approved 2:52 English demo, add matching English subtitles, and upload it as **Public** YouTube | by 2026-07-21 12:00 KST | before 2026-07-22 09:00 KST |
| Send the Fable-edited story for repository fact-check | as soon as available, preferably by 2026-07-21 12:00 KST | before final paste |
| Review the signed-out repository/video links and final Devpost preview, then submit | target 2026-07-21 20:00 KST | 2026-07-22 09:00 KST; no edits afterward |

Do not close the existing long-running build task before capturing its `/feedback`
Session ID. This release-audit task is not the substitute Session ID.

## Final cross-surface audit

- [ ] README, Devpost story, pitch, captions, and narration describe the same six-task
      scope and source-only artifact.
- [ ] Codex/GPT-5.6 are described as meaningful build-time collaborators, not runtime
      analyzers.
- [ ] Every test count, commit, and hash has exactly one matching repository record.
- [ ] B4-R numbers remain bound to commit `989d5c5...` and the recorded kit SHA-256.
- [ ] B5 remains **pending** unless a separate measured protocol is later completed.
- [ ] Zero verified external routes, incomplete full bilingual support, unvalidated
      recommendations, unproven expert/SPSS parity, and incomplete accessibility remain
      explicit.
- [ ] No new feature work was introduced during release closure.

## Post-P0 lane

Run B5 on the low-cost HP laptop only after the submission-critical repository,
license, demo, evidence, and Devpost packet are closed. A B5 failure or incomplete run
must be reported as such and must not rewrite the already accepted B4-R evidence.
