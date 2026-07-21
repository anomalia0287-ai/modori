# 2026-07-05 Release Lane Chart/VM QA Handoff

## Current Status

Use the repository root for the current release lane:

`C:\Users\V\Desktop\TongTong`

Branch:

`release/readiness-1-9`

Latest product commit at the time of this handoff:

`53f8335 fix: show automatic analysis charts`

The worktree was clean immediately after that commit. Packaging artifacts under
`dist/` are generated and ignored by git.

## What Changed

The data transform UI work was already merged into the release lane. During VM
QA, the user asked whether graph generation existed. Investigation found two
separate facts:

- The original analysis specs required automatic figures through `ChartSpec`.
- A standalone user-driven graph builder was not part of v1; native/interactive
  charts were explicitly out of scope for the UI shell v1.

The product defect was narrower: automatic analysis figures existed in the
engine/report path, but normal result-panel display did not render `chart_spec`
into `DisplayResult.chart_paths`.

Commit `53f8335` fixes that result-panel connection:

- `src/modori/ui/chart_assets.py` renders a result `ChartSpec` to a managed
  cache PNG for UI display.
- `src/modori/ui/pipeline_ops.py` attaches rendered chart paths to
  `DisplayResult`.
- Renderer construction is centralized through `UiControllerServices`, so a
  future chart skin/theme renderer can replace the current matplotlib-backed
  renderer without changing QML.
- If chart rendering fails, text/table results still display and a Korean figure
  note is surfaced instead of failing the whole run.

## Current Package

Rebuilt package:

`C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`

SHA256:

`A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888`

File details observed after rebuild:

- Size: `29655872` bytes
- LastWriteTime: `2026-07-05 16:16:27` local time

## Verification Evidence

Commands were run from:

`C:\Users\V\Desktop\TongTong`

Use the release-root source path explicitly when running Python commands:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe ...
```

Focused chart/UI verification:

```text
tests\ui\test_chart_assets.py
tests\ui\test_pipeline_ops.py
tests\ui\test_controller_services.py
tests\ui\test_result_surface_qml.py
tests\ui\test_chart_report_options.py
tests\ui\test_results_report_lifecycle_hardening.py
```

Result:

```text
29 passed
```

UI structure/result guards:

```text
40 passed
```

Engine/report chart tests:

```text
85 passed, 1 skipped
```

Default release gate:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py
```

Result:

```text
527 passed, 2 skipped
pip check: No broken requirements found.
```

Packaged release gate:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

Result:

```text
527 passed, 2 skipped
package-tool-ok
package-launch-smoke-ok
package-engine-smoke-ok
```

## Clean VM Evidence

Correct VM:

`Modori-CleanWin-QA-Direct`

Correct payload label:

`MODORIQA2`

Host attach log:

`C:\VM\ModoriPayload\attach-payload-v2.log`

Observed attach-log evidence:

```text
Start time: 20260705170429
VM: Modori-CleanWin-QA-Direct / Off
Backing up existing payload VHDX to:
C:\VM\ModoriPayload\ModoriPayloadV2.before-rebuild-20260705-170431.vhdx
Path: C:\VM\ModoriPayload\ModoriPayloadV2.vhdx
Done
End time: 20260705170442
```

Current payload VHDX observed on host:

```text
C:\VM\ModoriPayload\ModoriPayloadV2.vhdx
Length: 809500672
LastWriteTime: 2026-07-05 17:10:53 local time
```

Inside-VM manual evidence:

- The user ran the post-payload VM check flow after commit `53f8335`.
- The user reported: `작동한다.`
- Interpretation: the packaged app launched and the user-visible automatic chart
  path was working in the clean VM flow.

Evidence boundary:

- The host attach log and payload timestamp are machine-observed.
- The final inside-VM UI confirmation is user-operated manual evidence. The
  post-`53f8335` inside-VM engine-smoke JSON was not pasted into this handoff.

## UI/Design Follow-Up

Automatic analysis chart display is now a functional release-lane fix. Do not
fold that back into a design-polish task.

The following should be handled with the broader design/UI improvement pass:

- chart skin/theme choices;
- chart surface spacing and visual polish;
- richer chart interactions;
- a standalone graph builder where users choose variables and chart types.

The skinning seam should remain at the renderer/service level, not in QML. QML
should continue to consume local image paths from the controller.

## Next Recommended Steps

1. If another product change lands, rebuild the package and rerun the payload/VM
   evidence. Do not reuse this package hash for a different commit.
2. Treat `53f8335` + SHA256
   `A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888` as the
   current release-lane verification anchor.
3. Continue with design/UI improvements as a separate scoped task. The automatic
   chart display blocker is closed.
