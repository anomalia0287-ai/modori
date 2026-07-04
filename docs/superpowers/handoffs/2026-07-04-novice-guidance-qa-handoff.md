# 2026-07-04 Novice Guidance QA Handoff

## Immediate Warning

Do not use the repository root build for novice-guidance QA.

The root worktree at `C:\Users\V\Desktop\TongTong` is on
`release/readiness-1-9` and currently contains only the narrow no-auto-rerun
QML fix. It does not contain the full novice recommendation UI. The correct
active implementation is:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`

Branch:

`codex/novice-analysis-guidance`

The prior VM confusion happened because Payload V2 was rebuilt from the root
workspace, which removed the visible recommendation UI from the VM build.

## Current Product State

The novice guidance branch contains:

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

## Important Environment Detail

The root `.venv` is usable from the novice worktree, but its editable install
can resolve `modori` from the root workspace unless `PYTHONPATH` is forced.

When running tests/builds from the novice worktree, use:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe ...
```

Without this, tests may silently exercise the wrong source tree.

## Verified Commands

Run from:

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

## Current Git State

Root worktree:

`C:\Users\V\Desktop\TongTong`

- Branch: `release/readiness-1-9`
- Dirty files:
  - `src/modori/ui/qml/Main.qml`
  - `tests/ui/test_human_operated_qml_flow.py`
  - `tests/ui/test_import_dialog_flow.py`
- These root changes are the narrow no-auto-run fix only. Do not package from
  root for novice guidance QA.

Novice worktree:

`C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance`

- Branch: `codex/novice-analysis-guidance`
- Dirty files include:
  - `src/modori/ui/controller.py`
  - `src/modori/ui/controller_services.py`
  - `src/modori/ui/qml/components/GuideRail.qml`
  - `src/modori/ui/strings.py`
  - `src/modori/recommendations.py` new location
  - `src/modori/ui/recommendation_controller.py` new mixin
  - deleted `src/modori/ui/recommendations.py`
  - updated UI tests for explicit recommendation run contract

## Code Changes Since Last Commit In Novice Worktree

The latest uncommitted work addressed full-gate failures:

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

1. Do not ask the user to rerun VM yet unless the explicit goal is release or
   clean-machine verification.
2. First inspect the packaged app locally or with a lightweight local launch
   check from the novice worktree.
3. If continuing development, commit or otherwise preserve the novice worktree
   changes before attempting merges.
4. Decide how to reconcile the root no-auto-run dirty change with the novice
   branch. The novice branch already contains the correct no-auto-run behavior.
5. Only after the branch is selected as a release candidate should Payload V2 be
   rebuilt from the novice worktree path.

## If VM Verification Becomes Necessary

Only use this when the user explicitly wants clean Windows/release validation.

Set:

```powershell
$workspace = "C:\Users\V\Desktop\TongTong\.worktrees\novice-analysis-guidance"
```

Never use:

```powershell
$workspace = "C:\Users\V\Desktop\TongTong"
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
