# Release Manual QA Matrix

Status: release QA evidence for the `release/readiness-1-9` lane.

Date: 2026-06-29.

Latest supplemental evidence: 2026-07-05, recorded in
`docs\superpowers\handoffs\2026-07-05-release-lane-chart-vm-handoff.md`.

Environment:

- OS shell: Windows PowerShell.
- Workspace: `C:\Users\V\Desktop\TongTong`.
- App runtime: packaged `dist\Modori\Modori.exe` plus PySide6/QML source smoke.
- Product Design saved context: none configured for this workspace.
- Local evidence folder: `.visual-qa\release-manual-qa-2026-06-29`.

## Matrix

| Item | Status | Evidence |
| --- | --- | --- |
| Korean Windows path | Pass for controller/report flow | A reference CSV was created under `.visual-qa\release-manual-qa-2026-06-29\한글 경로 QA`; `UiController` opened it, ran analysis, and exported `modori-output\report.docx`. |
| long filename | Pass for controller/report flow | The same probe used a CSV named `설문_` plus repeated `긴파일명` text. Report export succeeded from that path. |
| high DPI | Pass for offscreen launch smoke only | `QT_SCALE_FACTOR=1.5`, `QT_QPA_PLATFORM=offscreen`, and `MODORI_REDUCE_EFFECTS=1` with `scripts\launch_smoke.py` returned `launch-smoke-ok`. Visible layout inspection is still separate. |
| low GPU / reduce-effects | Pass for automated contract | `tests\ui\test_security_privacy.py::test_controller_reduce_effects_toggle_persists_to_settings` and `test_work_screen_exposes_reduce_effects_toggle` passed. Launch smoke also passed with `MODORI_REDUCE_EFFECTS=1`. |
| broken input file | Pass for visible error contract | Opening a missing CSV path creates a session, then `rerunNow` fails through the worker path with `status=error`, `stale=True`, and Korean `lastError` text. |
| report export failure | Pass for visible error contract | A failing report exporter returned `error_code=engine_error` and set `lastError` to `보고서를 내보내지 못했습니다.` |
| accessibility smoke | Pass for source/static contract | `tests\ui\test_security_privacy.py::test_core_qml_buttons_have_accessible_names` passed. Existing QML controls include Korean `Accessible.name` bindings. |
| screenshot evidence | Pass for packaged visible walkthrough | Codex Computer Use Windows.Graphics.Capture captured packaged `dist\Modori\Modori.exe` entry, Excel import preview, and final work screen. Final screen showed `가져온 데이터: 20행 · 12열`, `분석 결과가 업데이트되었습니다.`, reliability/comparison result text, result tables, and enabled `Word 내보내기`. |

## Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui -q -p no:cacheprovider
```

Result:

```text
188 passed in 9.45s
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Result:

```text
418 passed, 2 skipped in 40.59s
```

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe scripts\launch_smoke.py
```

Result:

```text
launch-smoke-ok
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_launch_smoke_script.py tests\test_package_launch_smoke_script.py -q -p no:cacheprovider
```

Result:

```text
4 passed in 4.00s
```

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_SCALE_FACTOR='1.5'
$env:MODORI_REDUCE_EFFECTS='1'
.\.venv\Scripts\python.exe scripts\launch_smoke.py
```

Result:

```text
launch-smoke-ok
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_security_privacy.py::test_core_qml_buttons_have_accessible_names tests\ui\test_security_privacy.py::test_controller_reduce_effects_toggle_persists_to_settings tests\ui\test_security_privacy.py::test_work_screen_exposes_reduce_effects_toggle -q -p no:cacheprovider
```

Result:

```text
3 passed in 3.87s
```

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-build --with-packaged-launch
```

Result:

```text
compileall passed
ruff check src tests scripts passed
bandit -q -r src passed
launch-smoke-ok
418 passed, 2 skipped
pip check: No broken requirements found.
dist\Modori\Modori.exe
package-launch-smoke-ok
```

```powershell
dist\Modori\Modori.exe --engine-smoke .visual-qa\release-manual-qa-2026-06-29\visible-import-reference.xlsx .tmp\packaged-engine-smoke.json
```

Result:

```json
{
  "data_columns": 12,
  "data_rows": 20,
  "last_error": "",
  "ok": true,
  "opened": true,
  "rerun": true,
  "result_summary_present": true,
  "status": "ready",
  "waited": true
}
```

## Screenshot Capture Attempts

Attempt 1: QML offscreen `window.grabWindow()` with `QT_QPA_PLATFORM=offscreen`.

- Result: timed out before a screenshot was saved.

Attempt 2: QML offscreen `processEvents()` with `QT_QUICK_BACKEND=software`.

- Result: exited nonzero without an accepted screenshot.

Attempt 3: visible app launch plus Windows `CopyFromScreen`.

- Result: failed with `Exception calling "CopyFromScreen" with "3" argument(s): "핸들이 잘못되었습니다."`

Attempt 4: packaged `dist\Modori\Modori.exe` visible launch plus Python
`PIL.ImageGrab.grab(all_screens=True)`.

- Result: failed with `OSError: screen grab failed`.

Attempt 5: Codex Computer Use Windows.Graphics.Capture path against packaged
`dist\Modori\Modori.exe`.

- Result: blocked by Computer Use app approval timeout before a targetable
  Modori window capture could be accepted.

Attempt 6: Codex Computer Use Windows.Graphics.Capture path against rebuilt
packaged `dist\Modori\Modori.exe`.

- Result: accepted screenshots captured. Entry screen exposed guided/standard
  modes, data-open action, and recent items. Excel import preview for
  `visible-import-reference.xlsx` showed `20 cases previewed · 9 variables`,
  sheet `Responses`, and sample rows with fixed visible `취소` / `가져오기`
  actions. Final work screen showed imported data, result summary text, result
  tables, and enabled report export.

## Issue Closed During Visible QA

- Import preview dialog previously let long Excel previews push the confirm
  action out of clear view. It now uses a scrollable preview body and fixed
  Korean `취소` / `가져오기` actions.
- Work screen previously did not make imported content easy to identify before
  analysis completed. It now binds preview/full data models and shows a data
  notice such as `가져온 데이터 미리보기: 20행 · 9열` or `가져온 데이터: 20행 · 12열`.
- Packaged analysis previously failed at chart/report rendering because
  PyInstaller omitted Matplotlib SVG/PS backends. The package build now includes
  `matplotlib.backends.backend_agg`, `backend_svg`, and `backend_ps`; packaged
  engine smoke covers this path.

## 2026-07-05 Supplemental VM QA

| Item | Status | Evidence |
| --- | --- | --- |
| automatic analysis chart display | Pass for current release-lane package | Commit `53f8335` renders analysis `chart_spec` into managed cache PNG paths for the result panel. Local default gate reported `527 passed, 2 skipped`; packaged gate reported `package-tool-ok`, `package-launch-smoke-ok`, and `package-engine-smoke-ok`. |
| clean VM payload refresh | Pass for host attach evidence | `C:\VM\ModoriPayload\attach-payload-v2.log` recorded `VM: Modori-CleanWin-QA-Direct / Off`, payload rebuild, `Path: C:\VM\ModoriPayload\ModoriPayloadV2.vhdx`, and `Done` ending at `2026-07-05 17:04:42` local time. |
| clean VM visible UI | Pass for user-operated manual evidence | After the payload rebuild, the user reported the VM app flow works. This is manual UI evidence; the post-`53f8335` inside-VM JSON was not pasted into this document. |

Current package SHA256:

```text
A4FE941EF6170E735B107D75244A4A2562722E881F293224B576A517E0796888
```

## Release Interpretation

This document records an accepted target-machine visible walkthrough for the
packaged Windows app. It does not by itself certify installer signing,
distribution trust, or broader SPSS-equivalent feature completeness.
