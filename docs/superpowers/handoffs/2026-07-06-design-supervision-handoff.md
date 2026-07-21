# 2026-07-06 Design Supervision Handoff

## Read This First

Current active workspace:

`C:\Users\V\Desktop\TongTong`

Current branch:

`release/readiness-1-9`

Current HEAD at handoff time:

`3ed70c2 docs: record chart VM release evidence`

Recent product anchor:

`53f8335 fix: show automatic analysis charts`

The worktree was clean immediately before this handoff was written. Generated
visual QA files live under `.visual-qa/` and are ignored by git.

## Operating Policy

Read `docs\POLICY.md` before making a design or implementation decision. The
critical rules for the next session are:

- quality and correctness outrank speed, token use, convenience, and agreement;
- anyone may object, including against the owner or another AI contributor, when
  evidence supports the objection;
- a statistics tool must not imply unsupported accuracy or scope;
- verification tools and manual QA instructions are part of the release system;
- do not claim release readiness without current evidence and exact artifact
  identity.

The owner explicitly confirmed this operating philosophy during the session:
quality is first, anyone may speak, and evidence-based disagreement is allowed.

## Current Product State

The release lane already contains:

- novice/guided recommendation flow;
- data transform UI foundation;
- automatic analysis chart display in the normal result panel;
- packaged Windows executable rebuilt and VM-smoked after the chart-display fix.

Latest release-lane package from the 2026-07-05 evidence:

`C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`

SHA256:

`A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888`

Latest release/VM evidence handoff:

`docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md`

Do not replace that release anchor unless a new product/package change lands and
the package/payload/VM flow is rerun.

## Design Direction Discussion So Far

The owner initially wanted Claude Design to participate in the visual/product
design pass, but Claude Design hit a usage limit before returning a design
review.

Current update as of 2026-07-06: the owner has withdrawn Claude-side design
ownership for now. Do not wait for Claude Design output before planning the
redesign pass.

Current role split while Claude Design is withdrawn:

- Codex: likely primary redesign owner, product/architecture supervisor,
  QML/Python boundary protection, reproducibility model protection,
  implementation feasibility, test/package/VM verification, and final
  acceptance/rejection of design suggestions.
- Claude Design: optional future external critique only if the owner
  reintroduces it.

Do not treat any future Claude output as authoritative. If Claude Design is
reintroduced, classify each proposal as:

- accept;
- accept with modification;
- hold for later;
- reject with reason.

The design pass may change a lot of the visual surface, but must not weaken
these load-bearing constraints:

- QML remains a thin shell;
- statistics and validation remain in Python services;
- source data stays read-only;
- transforms remain explicit replayable pipeline steps;
- chart skinning stays at the renderer/service boundary;
- QML consumes local image paths and should not own chart drawing logic;
- no web rewrite, cloud dependency, telemetry, or remote assets.

Product positioning agreed in discussion:

> Modori's strongest value is not simply "free + convenient." The stronger
> position is: a Korean, local-first statistics tool that helps non-experts move
> safely from import to recommended analysis, graph, and report without damaging
> data or losing reproducibility.

## Claude Design Packet

A limited design-review packet was prepared for Claude Design. It intentionally
does not include the full repository, Python engine code, VM scripts, security
scripts, tests, or data files.

Folder:

`C:\Users\V\Desktop\TongTong\.visual-qa\claude-design-packet-2026-07-05`

Zip:

`C:\Users\V\Desktop\TongTong\.visual-qa\claude-design-packet-2026-07-05.zip`

Included files:

- `CLAUDE_DESIGN_BRIEF.md`
- `SCREENSHOT_MANIFEST.md`
- `QML_EXCERPTS.md`
- `PROMPT_FOR_CLAUDE_DESIGN.md`
- `screenshots\01-entry.png`
- `screenshots\02-import-preview.png`
- `screenshots\03-work-data-view.png`
- `screenshots\04-results-chart.png`
- `screenshots\05-transform-tab.png`
- `screenshots\06-variable-view.png`
- `screenshots\07-recommendation-alternatives.png`
- `screenshots\08-standard-mode.png`

Screenshots were captured from the main PC packaged app, not from the VM. The
owner stated that VM screenshots are not available; if screenshots are needed,
capture them on the main PC.

Use `PROMPT_FOR_CLAUDE_DESIGN.md` as the prompt only if Claude Design is
reintroduced.

## Owner-Provided Redesign Reference

The owner provided an additional external reference folder:

`C:\Users\V\Desktop\폴더 검토 및 UI 개선`

Observed files:

- `.thumbnail`: WebP preview of the redesigned import dialog.
- `Modori Redesign.dc.html`: design-canvas HTML containing three visual routes.
- `Modori Redesign-print-1y3tng6.dc.html`: print-oriented copy of the same
  routes with extra print helper code.
- `support.js`: generated design-canvas runtime, not a product implementation
  reference.
- `uploads\claude-design-packet-2026-07-05\...`: copy of the existing screenshot
  packet.

The HTML contains these routes, each covering entry, import, guided work/results,
and transform screens:

- `2a` / Crystal Aurora: most expressive; colorful glass/aurora background.
- `1a` / Mist Glass: immersive glass surface over a soft aqua background.
- `1b` / Porcelain Glass: restrained white work surface, data-centered layout,
  and report-like result panel.

Implementation guidance: use `1b` as the strongest baseline for QML redesign
because it best matches a professional statistical desktop tool and the current
thin-shell architecture. Borrow selectively from `2a`/`1a` for the entry/import
atmosphere only. Do not directly port remote font dependencies, heavy animated
aurora backgrounds, large blur/backdrop effects, or design-canvas runtime
assumptions into the product.

## What To Do If Claude Design Is Reintroduced

1. Save or paste the Claude Design output into the current thread.
2. Review it against the constraints above and `docs\POLICY.md`.
3. Produce a short acceptance matrix:
   - proposal;
   - decision: accept / modify / hold / reject;
   - reason;
   - affected QML/component files;
   - risk and test coverage needed.
4. Only then start implementation for accepted or modified proposals.

If the owner asks to implement the design pass, prefer a separate branch or
worktree from `release/readiness-1-9`, for example:

`codex/ui-design-polish`

Do not directly disturb release evidence unless the owner explicitly decides the
design pass is part of the release lane.

## Likely Implementation Scope

Likely high-value design work, in order:

1. Results/chart panel: make the output feel credible and publication-oriented.
2. Work screen density: improve the balance among guide rail, data grid, results
   panel, and pipeline rail.
3. Transform tab: make reverse-code and scale-score workflows feel safer, more
   complete, and less raw.
4. Guided vs standard mode: clarify the behavioral and visual difference.
5. Tables/forms: improve typography, row height, borders, selected states, empty
   states, stale/error/running states, and Korean text fit.
6. Theme tokens: centralize palette, spacing, radius, and typography enough that
   future skin swaps are possible without a full rewrite.

Avoid:

- decorative SaaS/landing-page styling;
- cards inside cards;
- pure single-hue palette;
- hidden state;
- oversized marketing-style hero layouts;
- moving analysis/chart logic into QML;
- making transforms look like in-place spreadsheet edits.

## Verification Rules For Any UI Change

For local Python/test commands from this root, force the source path:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe ...
```

Minimum likely verification after QML-only visual changes:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest -q tests\ui -p no:cacheprovider
```

If controller bindings, chart paths, transform behavior, or report export are
touched, run focused tests for those paths plus the default quality gate.

Before claiming a release package is current, rerun the package gate and, if the
owner chooses release/clean-machine validation, rebuild Payload V2 and rerun the
VM smoke/UI flow. Do not use the VM for normal design iteration.

## Current User Preference

The owner is comfortable with direct, evidence-based pushback. Keep responses
concise and practical. The owner offered that informal speech is acceptable if
useful; it was decided to keep using respectful Korean, but with shorter
engineering-focused phrasing.

## Immediate Next Step

If the owner asks Codex to proceed with the redesign, create a design-polish
plan from the existing screenshot packet and implement screen-by-screen with
verification after each meaningful slice. Do not block on Claude Design output.
