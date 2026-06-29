# Release Manual QA Matrix

Status: release QA evidence for the `release/readiness-1-9` lane.

Date: 2026-06-29.

Environment:

- OS shell: Windows PowerShell.
- Workspace: `C:\Users\V\Desktop\TongTong`.
- App runtime: PySide6/QML through `.venv\Scripts\python.exe`.
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
| screenshot evidence | Blocked in this environment | QML offscreen `grabWindow` timed out or exited without an accepted image. Visible desktop capture through `System.Drawing.Graphics.CopyFromScreen` failed with a Windows invalid-handle error. No screenshot is accepted as release evidence from this run. |

## Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui -q -p no:cacheprovider
```

Result:

```text
161 passed in 5.77s
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

## Screenshot Capture Attempts

Attempt 1: QML offscreen `window.grabWindow()` with `QT_QPA_PLATFORM=offscreen`.

- Result: timed out before a screenshot was saved.

Attempt 2: QML offscreen `processEvents()` with `QT_QUICK_BACKEND=software`.

- Result: exited nonzero without an accepted screenshot.

Attempt 3: visible app launch plus Windows `CopyFromScreen`.

- Result: failed with `Exception calling "CopyFromScreen" with "3" argument(s): "핸들이 잘못되었습니다."`

## Release Interpretation

This document closes the repository-local QA matrix and records current evidence.
It does not certify visible desktop layout quality. A target-machine visual
walkthrough with accepted screenshots remains required before claiming a signed
Windows release is ready for end users.
