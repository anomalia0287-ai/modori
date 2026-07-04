# 2026-07-04 Novice Guidance QA Handoff

## Current Release-Lane Status

This handoff was originally written before the novice guidance work was merged
back into the release lane. As of the release-lane integration, the repository
root is again the correct local build and package path for release/readiness QA:

`C:\Users\V\Desktop\TongTong`

Branch:

`release/readiness-1-9`

The pre-merge implementation worktree remains useful as historical evidence, but
release packaging should no longer be built from it unless a future branch
explicitly moves development there again:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`

`codex/novice-analysis-guidance`

The prior VM confusion happened because Payload V2 was rebuilt from the root
workspace, which removed the visible recommendation UI from the VM build.
That specific warning is now superseded by the merge: root contains the novice
recommendation UI after integration.

## Current Product State

The release lane now contains:

- Import confirmation no longer auto-runs analysis.
- Recent-file open no longer auto-runs analysis.
- Guide rail shows recommendation state after import.
- Recommended analysis run is explicit via `추천 분석 실행`.
- Alternative candidates can be shown and selected without running.
- Manual selection mode still supports explicit run via `선택한 분석 실행`.
- Caution-level candidates remain selectable but are not default when stronger
  candidates exist.
- Recommendation rules were moved out of the UI package to keep UI thin-shell
  boundaries intact.

## User-Reported Manual QA State

Before the path correction, the user confirmed:

- CSV/XLSX/SAV import paths were OK.
- Import no longer caused immediate engine error after the narrow no-auto-run fix.
- However, recommendation analysis execution was not visible.

Root cause of the missing recommendation UI:

- The VM payload was rebuilt from `C:\Users\V\Desktop\TongTong` instead of
  `C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`.
- This was an operator/build-path error, not a VM-only product failure.

The user correctly challenged why VM was being used for this. VM should now be
reserved for release/clean-machine verification, not ordinary development
iteration.

## Historical Environment Detail

The root `.venv` is usable from the novice worktree, but its editable install
can resolve `modori` from the root workspace unless `PYTHONPATH` is forced.

When running tests/builds from the novice worktree, use:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe ...
```

Without this, tests may silently exercise the wrong source tree.

## Verified Commands

Historical pre-merge novice worktree verification ran from:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`

Targeted regression check:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_mode_action_surfaces.py tests\ui\test_smoke_qml.py tests\ui\test_guided_standard_variable_selection_flow.py::test_guide_rail_shows_recommendations_without_auto_running -q -p no:cacheprovider
```

Result:

`7 passed`

Full gate with packaging:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

Result:

- `470 passed, 2 skipped`
- `package-tool-ok`
- `package-launch-smoke-ok`
- `package-engine-smoke-ok`

Packaged executable:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance\dist\Modori\Modori.exe`

SHA256:

`28B30734D322B01D6CD2D515CCBF2D6E45FAFDA238D77B7BAAEA22A91711DD5E`

Packaged QML was checked and includes:

- `uiController.recommendationTitle`
- `guide.run_recommended`
- `guide.run_manual`
- `uiController.runPreparedRecommendationNow()`
- no `rerunNow()` call in `Main.qml` import confirmation path

Post-merge release-lane verification ran from:

`C:\Users\V\Desktop\TongTong`

Full gate with package rebuild:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-package-build --with-packaged-launch
```

Result:

- `507 passed, 2 skipped`
- `package-tool-ok`
- `package-launch-smoke-ok`
- `package-engine-smoke-ok`

Rebuilt packaged executable:

`C:\Users\V\Desktop\TongTong\dist\Modori\Modori.exe`

SHA256:

`C40FEBA237CE10BC7263DA958819973B8642B6FDBFC47C14BE334E24629C8385`

Post-merge visible local package QA confirmed:

- `psych_bfi.csv` opens from the rebuilt root package.
- Import shows `기본 추천`, `다른 추천 보기`, `직접 선택`, and `추천 분석 실행`.
- Import does not auto-run analysis.
- Clicking `추천 분석 실행` updates the result panel with reliability output.

## Current Git State

Root worktree:

`C:\Users\V\Desktop\TongTong`

- Branch: `release/readiness-1-9`
- Contains the merged novice recommendation UI and the release-lane survey v1
  analysis work.
- Use this root for release-lane package builds after this integration.

Novice worktree:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`

- Branch: `codex/novice-analysis-guidance`
- Historical implementation branch retained for reference.

## Code Changes Integrated From Novice Worktree

The integrated work addressed full-gate failures:

- Moved recommendation computation from `modori.ui.recommendations` to
  `modori.recommendations` because UI thin-shell guards forbid `numpy`,
  `pandas`, and reduction calls in `src/modori/ui`.
- Added `modori.ui.recommendation_controller.RecommendationControllerMixin`
  to move recommendation QML bridge properties and slots out of
  `UiController`.
- Reduced `UiController` back under the facade size budget.
- Updated stale tests that still assumed `rerunNow()` should work immediately
  after import. The correct path is now `runPreparedRecommendationNow()` or
  `runPreparedRecommendation()`.
- Changed guide button labeling:
  - recommended mode: `추천 분석 실행`
  - manual mode: `선택한 분석 실행`

## Recommended Next Steps

1. Commit the release-lane integration only after local verification evidence is
   current.
2. Do not move to VM unless the explicit goal is release or clean-machine
   verification.
3. Only after the release lane is selected as the release candidate should
   Payload V2 be rebuilt from the release root path.

## If VM Verification Becomes Necessary

Only use this when the user explicitly wants clean Windows/release validation.

Set:

```powershell
$workspace = "C:\Users\V\Desktop\TongTong"
```

Never use:

```powershell
$workspace = "C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance"
```

Expected VM visible QA:

- CSV/XLSX/SAV preview works.
- Import works.
- Table view works.
- Variable view works.
- Import does not auto-run analysis.
- No engine error appears immediately after import.
- Guide panel shows default recommendation and recommendation level.
- `추천 분석 실행` is visible for recommended mode.
- `다른 추천 보기` is visible/enabled when multiple candidates exist.
- Selecting another candidate does not run analysis.

## Communication Note

The user is non-developer and explicitly prefers direct, honest status. They
called out a prior accidental switch to informal Korean. Use respectful Korean
and do not hand them developer-only assumptions without explaining exactly what
they need to click or run.
