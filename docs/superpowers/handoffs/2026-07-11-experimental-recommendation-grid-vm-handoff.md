# 2026-07-11 Experimental Recommendation And Grid VM Handoff

## Read This First

This handoff freezes the state after host-side closure of the experimental
recommendation boundary and the first clean-VM feedback pass. Do not restart the
design or implementation from memory. Resume from the evidence and open gates
listed here.

Active worktree:

`C:\Users\V\Desktop\TongTong\.worktrees\recommendation-benchmark-pilot`

Branch:

`codex/recommendation-benchmark-pilot`

Implementation/documentation HEAD before this handoff commit:

`2f4b2a8a6bbf25d8af993e0428ecc33a053382e6`

Worktree state at handoff:

- tracked and untracked status is clean;
- no push was performed in this closure pass;
- the handoff file itself is a documentation-only commit above the tested
  implementation and does not make the package stale.

## Product Claim Boundary

- The recommendation surface is an experimental candidate guide, not a
  validated automatic recommendation engine.
- It must not claim recommendation accuracy, expert equivalence, an 80 percent
  success rate, or validated statistical-method selection.
- Statistical calculation-module evidence and recommendation-selection
  validity are separate claims.
- Candidate selection cannot calculate directly. It requires configuration
  review, explicit confirmation, and the existing manual run path.
- Broad visual redesign remains intentionally deferred to a separate task.
  This pass closes functional defects only.

## Tested Package Identity

Package:

`C:\Users\V\Desktop\TongTong\.worktrees\recommendation-benchmark-pilot\dist\Modori\Modori.exe`

Package identity:

- size: `30,983,166` bytes;
- SHA-256:
  `A531C537423613DDFA3867569EF6F43EC2BB24917C91FCB0ED3C53620AD19098`;
- build write time UTC: `2026-07-11T06:52:34.8557653Z`.

Pilot identity remained frozen:

- cases: 20;
- manifest entries: 20;
- unique data files: 19;
- scorer fingerprint:
  `sha256:1d232ac88bc705b8c31735aa6e997d253a388a478c9337d146f6798d50f33aac`;
- scorer implementation digest:
  `sha256:127d7cd7c1f313a592ed6d491307e891fee138f59212ecbbe8e1da8a78765679`;
- frozen and regenerated baseline SHA-256:
  `FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650`;
- regenerated baseline versus frozen baseline: zero-byte diff.

## Payload Identity

Payload VHDX:

`C:\VM\ModoriPayload\ModoriPayloadV2.vhdx`

Rebuild log:

`C:\VM\ModoriPayload\attach-payload-v2.log`

The payload was rebuilt at `2026-07-11 16:00 KST` from the exact worktree above.
The log records:

- workspace root:
  `C:\Users\V\Desktop\TongTong\.worktrees\recommendation-benchmark-pilot`;
- payload contract: `experimental-recommendation-boundary-v1`;
- packaged EXE SHA-256:
  `A531C537423613DDFA3867569EF6F43EC2BB24917C91FCB0ED3C53620AD19098`;
- VM: `Modori-CleanWin-QA-Direct / Off`;
- `Validate new payload contents`;
- `Attach payload disk to VM`;
- `Done`.

Current payload file facts:

- size: `742,391,808` bytes;
- write time UTC: `2026-07-11T07:00:49.5068096Z`;
- payload source freshness check: current.

Inside the VM, `D:\PAYLOAD_IDENTITY.txt` must begin with:

```text
Contract=experimental-recommendation-boundary-v1
ModoriExeSHA256=A531C537423613DDFA3867569EF6F43EC2BB24917C91FCB0ED3C53620AD19098
```

The payload validation already recomputed the EXE and all three experimental
sample hashes before the VHDX was attached. Owner-visible identity inspection is
still required before running the app.

## Defects Found By The First VM Walkthrough

The owner reported four issues after the first package inspection:

1. Hovering a grid cell displayed a duplicate numeric tooltip, sometimes with
   the value from another cell.
2. Horizontal and vertical grid movement looked rough, and the grid could be
   pulled beyond its top or left boundary.
3. Experimental wording was repeated so heavily that it obscured the action.
4. The first payload rebuild came from the main workspace rather than this
   worktree, so the experimental samples were missing.

These were treated as product defects, not dismissed as cosmetic observations.

## Implemented Corrections

### Grid tooltip ownership

- Removed the shared attached tooltip from the cell hover `MouseArea`.
- Added a delegate-local tooltip bound to the current delegate's exact text.
- The tooltip appears only when the rendered label is actually truncated.
- Runtime QML tests force row and column delegate reuse before asserting the
  tooltip text, covering the stale-cell failure mechanism.

Commit:

`d485f18 fix: bind grid tooltips to truncated cells`

### Grid boundary behavior

- Body, horizontal header, and vertical header now use
  `Flickable.StopAtBounds` for both `boundsBehavior` and `boundsMovement`.
- Tests cover origin drag, navigation to the right and bottom, and header/body
  synchronization.

Commit:

`e7cdbbf fix: stop data grid overscroll at bounds`

### Candidate-guide wording

The persistent product surface now uses:

- `분석 후보 안내`;
- `실험적 · 자동 실행 안 함`;
- `분석 후보 목록`.

The explicit report provenance disclosure remains unchanged. The product does
not use `분석 자동 추천`, because that phrase would overstate the current
behavior.

Commit:

`7596509 fix: simplify experimental candidate wording`

### Payload source-lane identity

- Wrapper passes an explicit worktree root.
- Attach/check scripts print the resolved workspace root and EXE hash.
- Payload includes `PAYLOAD_IDENTITY.txt`.
- Rebuild fails if payload hashes differ from source hashes.

Commit:

`7367eee fix: bind VM payload to explicit source identity`

## Fresh Host Evidence

The final integrated command was run with explicit R:

```powershell
$env:MODORI_RSCRIPT='C:\Users\V\Desktop\TongTong\.tools\r-env\Scripts\Rscript.exe'
python scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch --with-slow-stats
```

Fresh result:

- `compileall`: pass;
- Ruff: pass;
- Bandit: pass;
- launch smoke: pass;
- full suite: `1542 passed, 5 skipped, 0 failed`;
- `pip check`: no broken requirements;
- package tool check and build: pass;
- packaged launch smoke: pass;
- packaged engine smoke: pass;
- packaged public-data smoke: pass;
- slow statistics: `4 passed, 1543 deselected`;
- command exit code: `0`.

The five regular-suite skips were audited:

- one intentional recommendation-ineligibility contract for
  `paired_comparison`;
- three bootstrap slow-statistics tests;
- one factorial-ANOVA performance slow-statistics test.

The four slow tests executed and passed through the slow gate. R reference tests
executed and are not among the skipped tests.

Focused evidence after the fixes:

- complete UI suite: `429 passed`;
- grid/wording/boundary/payload bundle: `46 passed`;
- complete data-grid QML suite: `17 passed`;
- clean-VM payload contract tests: `20 passed`;
- product wording scanner: `6 passed`;
- both PowerShell payload scripts: zero parser errors;
- `git diff --check`: pass.

Windows-QPA captures retained locally:

`C:\Users\V\Desktop\TongTong\.worktrees\recommendation-benchmark-pilot\.tmp\grid-hardening-visual-windows`

The captures prove the host rendering state only. They do not replace owner VM
acceptance.

## Open Gate: Owner Clean-VM Recheck

Do not modify more code before receiving the owner's result unless the owner
changes direction.

The exact procedure is:

`docs\qa\experimental-recommendation-vm-runbook.md`

The immediate first-pass checks are:

1. Open `D:\PAYLOAD_IDENTITY.txt` and verify the two pinned lines above.
2. Verify `D:\Samples\experimental_recommendation` contains all three CSV files.
3. Run `D:\Run-Modori.bat`.
4. Import `D:\Samples\visible-grid-overflow.csv`.
5. Hover `r1c1` and two or three adjacent short cells. No duplicate popup may
   appear.
6. Scroll to the middle and far right/bottom. Headers must stay aligned and no
   blank overshoot area may appear.
7. Return to top-left and try to pull beyond the origin. The first row and column
   must remain bounded.
8. Open `experimental-candidate.csv`, enter `분석 후보`, and verify
   `분석 후보 안내` plus `실험적 · 자동 실행 안 함`.

The owner was asked to report each item as `정상` or `이상`. If any item fails,
preserve the screen and record the immediately preceding input before closing or
retrying.

## What The Next Session Must Do

### If every immediate VM check passes

1. Continue the remaining runbook interaction checks.
2. Record owner acceptance in
   `docs\qa\experimental-recommendation-release-evidence.md`.
3. Keep recommendation-accuracy claims explicitly open.
4. Commit VM evidence as documentation only.
5. Do not push unless the owner explicitly orders a push.
6. Close this functional-hardening track before opening the separate visual
   redesign task.

### If any VM check fails

1. Do not widen scope immediately.
2. Preserve screenshot, exact sample, cell, scroll position, and input sequence.
3. Reproduce on the host Windows QPA where possible.
4. Add a failing regression test before implementation.
5. Fix the smallest correct ownership or boundary issue.
6. Run the focused suite, complete UI suite, and the full integrated gate when
   packaged behavior changes.
7. Rebuild Payload V2 from this worktree and repeat the same VM check.

## Host Versus VM Verification Policy

Do not run the VM after every feature or every commit. That would add cost without
improving the strongest evidence for many changes. Use layered verification.

### Host verification is mandatory and primary for

- pure statistical formulas, tolerances, fail-closed rules, and DTO contracts;
- deterministic recommendation routing and non-mutation contracts;
- unit, integration, reference-parity, R-anchor, and slow simulation tests;
- QML object contracts and reproducible interaction tests;
- wording scanners, report text, and script contract tests;
- package build and packaged command-line smoke tests.

For calculation correctness, certified/reference fixtures and independent
oracles are stronger evidence than manually clicking the same calculation in a
VM.

### Clean-VM verification is mandatory for

- a release candidate or a newly rebuilt packaged artifact;
- PyInstaller dependency/runtime behavior on a clean Windows installation;
- actual mouse, keyboard, focus, tooltip, scrolling, DPI, font, and layout
  behavior that host automation cannot fully establish;
- native file dialogs, drive letters, path handling, permissions, and payload
  discovery;
- imports or exports dependent on OS codecs, Office/Word availability, shell
  integration, or clean-machine state;
- a defect first observed only in the clean VM;
- any change to payload construction or VM launch/check tooling.

### Practical cadence

- Pure engine change: host reference and full statistical gates; one packaged
  representative smoke, not a manual VM run per fixture.
- UI interaction change: host QML regression plus Windows rendering; VM at the
  feature checkpoint and release candidate.
- Import/export or OS-integration change: host tests plus clean VM before closure.
- Documentation/test-only change: no VM rebuild unless the document changes the
  payload or the owner procedure.
- Final release candidate: full host gate, immutable artifact identity, payload
  rebuild, then clean-VM acceptance.

## Deliberate Non-Goals

- Do not start the broad visual redesign in the VM-recheck session.
- Do not promote recommendation families to `VALIDATED`.
- Do not claim the 20-case pilot proves recommendation accuracy.
- Do not add an SLM or cloud transmission path.
- Do not change statistical algorithms in response to a visual defect.
- Do not push this branch without an explicit owner instruction.

## Relevant Documents

- Release evidence:
  `docs\qa\experimental-recommendation-release-evidence.md`
- VM runbook:
  `docs\qa\experimental-recommendation-vm-runbook.md`
- Grid hardening design:
  `docs\superpowers\specs\2026-07-11-data-grid-interaction-hardening-design.md`
- Grid hardening plan:
  `docs\superpowers\plans\2026-07-11-data-grid-interaction-hardening.md`
- Experimental-boundary design:
  `docs\superpowers\specs\2026-07-11-experimental-recommendation-boundary-design.md`

## Codex App Interruption Note

At approximately `16:02 KST`, the Codex desktop UI displayed its usage panel and
the task appeared to pause. The panel showed 83 percent of the five-hour allowance
and 97 percent of the weekly allowance remaining. Local logs contained no
`rate_limit`, quota, or HTTP 429 error; they showed an app-server configuration
reload and thread resume. No repository, package, commit, or payload work was
lost. Do not consume a banked reset solely because that panel appears again with
substantial allowance remaining.
