# Data Grid Interaction Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate misleading cell hover values and grid overshoot, then reduce experimental-wording repetition without weakening the recommendation evidence boundary.

**Architecture:** Keep `DataGridView.qml` as the single grid primitive used by data and variable tables. Replace the shared attached tooltip with delegate-local disclosure that activates only for truncated text, constrain all synchronized flickables at their bounds, and change only string-catalog vocabulary for the recommendation surface.

**Tech Stack:** Python 3.12, PySide6 6, Qt Quick Controls, QML `TableView`, pytest/QTest offscreen runtime tests, PyInstaller, Windows Hyper-V.

## Global Constraints

- Short values that fit inside a cell receive no tooltip.
- A truncated-value tooltip is owned by and bound to the hovered delegate.
- Grid body and synchronized headers use `Flickable.StopAtBounds` and remain clipped.
- Right/down scrolling, keyboard navigation, fixed dimensions, and header synchronization remain functional.
- Product entry/title vocabulary is `분석 후보 안내`.
- The panel keeps one persistent status: `실험적 · 자동 실행 안 함`.
- Do not use `분석 자동 추천`.
- Do not change data models, statistics, recommendation candidates/order/evidence/routing, execution boundaries, or report provenance.
- Work inline in `codex/recommendation-benchmark-pilot`; do not dispatch subagents.

---

## File Structure

- `src/modori/ui/qml/components/DataGridView.qml`: tooltip ownership and bounds behavior.
- `tests/ui/test_data_grid_qml.py`: source and real-QML hover, reuse, drag, navigation, and header-sync regressions.
- `src/modori/ui/strings.py`: recommendation-surface Korean vocabulary only.
- `tests/ui/test_security_privacy.py`, `tests/ui/test_experimental_recommendation_flow.py`, `tests/ui/test_guided_standard_variable_selection_flow.py`, `tests/ui/test_qml_string_catalog.py`: exact wording and interaction contracts.
- `docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md`: superseded wording amendment.
- `docs/qa/experimental-recommendation-vm-runbook.md`: corrected human-visible checkpoints.
- `docs/qa/experimental-recommendation-release-evidence.md`: fresh gate, package, and VM evidence.

### Task 1: Delegate-Local Truncated-Value Tooltip

**Files:**
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `src/modori/ui/qml/components/DataGridView.qml`

**Interfaces:**
- Consumes: model `display`, `variableKey`, and `measureValue` roles.
- Produces: `gridCellTooltip` with visibility tied to `cellHover.containsMouse && cellLabel.truncated` and text tied to `cellDelegate.cellText`.

- [ ] **Step 1: Write RED tests**

Allow `_GridFixtureModel` to receive explicit rows while preserving its current default. Add helpers `_render_grid`, `_visible_grid_delegate`, `_hover_delegate`, and `_close_grid` so tests use real QML objects.

```python
def test_data_grid_does_not_use_shared_attached_tooltip_for_cells() -> None:
    qml = qml_text("components/DataGridView.qml")
    assert "ToolTip.visible: containsMouse" not in qml
    assert "visible: cellHover.containsMouse && cellLabel.truncated" in qml
    assert "text: cellDelegate.cellText" in qml


def test_short_cell_hover_has_no_duplicate_tooltip() -> None:
    view, root, body = _render_grid(_GridFixtureModel(), width=480, height=240)
    cell = _visible_grid_delegate(body, row=0, column=0)
    _hover_delegate(view, cell)
    tooltip = cell.findChild(QObject, "gridCellTooltip")
    assert tooltip is not None
    assert tooltip.property("visible") is False
    _close_grid(view)


def test_truncated_cell_tooltip_matches_hovered_delegate_after_reuse() -> None:
    rows = tuple(
        (f"v{row}", "scale", (f"row-{row}-" + "x" * 80, f"other-{row}-" + "y" * 80))
        for row in range(60)
    )
    view, root, body = _render_grid(_GridFixtureModel(rows), width=340, height=180)
    body.setProperty("contentY", 40 * root.property("cellHeight"))
    _process_events()
    cell = _visible_grid_delegate(body, row=40, column=1)
    _hover_delegate(view, cell)
    tooltip = cell.findChild(QObject, "gridCellTooltip")
    assert tooltip.property("visible") is True
    assert tooltip.property("text") == "other-40-" + "y" * 80
    _close_grid(view)
```

- [ ] **Step 2: Run RED tests**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests\ui\test_data_grid_qml.py -k "tooltip or short_cell or truncated_cell"
```

Expected: failure because the shared attached tooltip remains and no delegate-local tooltip exists.

- [ ] **Step 3: Implement the minimal QML correction**

```qml
delegate: Rectangle {
    id: cellDelegate
    required property int row
    required property int column
    property string variableKey: model.variableKey ?? ""
    property string measureValue: model.measureValue ?? ""
    property string cellText: String(model.display ?? "")

    MouseArea {
        id: cellHover
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {
            body.forceActiveFocus()
            root.currentRow = cellDelegate.row
            root.currentColumn = cellDelegate.column
            root.cellActivated(cellDelegate.row, cellDelegate.column, cellDelegate.variableKey, cellDelegate.measureValue)
        }
    }

    Text {
        id: cellLabel
        anchors.centerIn: parent
        width: parent.width - theme.spaceSm
        text: cellDelegate.cellText
        color: theme.textTable
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
    }

    ToolTip {
        id: cellToolTip
        objectName: "gridCellTooltip"
        visible: cellHover.containsMouse && cellLabel.truncated
        text: cellDelegate.cellText
    }
}
```

- [ ] **Step 4: Run the complete data-grid test file**

Expected: all tests pass with no QML warnings.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/ui/qml/components/DataGridView.qml tests/ui/test_data_grid_qml.py
git commit -m "fix: bind grid tooltips to truncated cells"
```

### Task 2: Hard Grid Bounds And Synchronized Navigation

**Files:**
- Modify: `tests/ui/test_data_grid_qml.py`
- Modify: `src/modori/ui/qml/components/DataGridView.qml`

**Interfaces:**
- Consumes: existing `syncView: body` headers.
- Produces: no top/left overshoot while preserving right/down navigation.

- [ ] **Step 1: Write RED source and pointer tests**

Add `_large_grid_model(*, rows: int, columns: int)`, `_grid_headers(root)`, and
`_point(scene_point)` helpers. `_large_grid_model` returns `_GridFixtureModel` with
unique values for every row and column; `_grid_headers` selects the real
`QQuickHorizontalHeaderView` and `QQuickVerticalHeaderView`; `_point` rounds a
`QPointF` to a `QPoint` for QTest pointer input.

```python
def test_grid_and_headers_stop_at_content_bounds() -> None:
    qml = qml_text("components/DataGridView.qml")
    assert qml.count("boundsBehavior: Flickable.StopAtBounds") == 3
    assert qml.count("boundsMovement: Flickable.StopAtBounds") == 3


def test_pointer_drag_at_origin_cannot_pull_grid_above_or_left() -> None:
    model = _large_grid_model(rows=80, columns=20)
    view, root, body = _render_grid(model, width=360, height=190)
    start = body.mapToScene(QPointF(body.width() / 2, body.height() / 2))
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, _point(start))
    QTest.mouseMove(view, QPoint(round(start.x() + 100), round(start.y() + 100)), 30)
    _process_events()
    assert float(body.property("contentX")) >= 0.0
    assert float(body.property("contentY")) >= 0.0
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, _point(start))
    _close_grid(view)


def test_right_and_down_navigation_remain_scrollable_and_header_synced() -> None:
    model = _large_grid_model(rows=80, columns=20)
    view, root, body = _render_grid(model, width=360, height=190)
    QTest.keyClick(view, Qt.Key_End)
    for _ in range(4):
        QTest.keyClick(view, Qt.Key_PageDown)
    _process_events()
    horizontal, vertical = _grid_headers(root)
    assert float(body.property("contentX")) > 0.0
    assert float(body.property("contentY")) > 0.0
    assert abs(float(horizontal.property("contentX")) - float(body.property("contentX"))) < 1.0
    assert abs(float(vertical.property("contentY")) - float(body.property("contentY"))) < 1.0
    _close_grid(view)
```

- [ ] **Step 2: Run RED tests**

Expected: source contract fails because no `StopAtBounds` declarations exist.

- [ ] **Step 3: Add these properties to both headers and the body**

```qml
boundsBehavior: Flickable.StopAtBounds
boundsMovement: Flickable.StopAtBounds
```

Keep clipping, synchronization, fixed providers, and scrollbar policies unchanged.

- [ ] **Step 4: Run the complete data-grid test file**

Expected: all tests pass, origin remains bounded, and later rows/columns remain reachable.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/ui/qml/components/DataGridView.qml tests/ui/test_data_grid_qml.py
git commit -m "fix: stop data grid overscroll at bounds"
```

### Task 3: Reduce Experimental Wording Repetition

**Files:**
- Modify: `src/modori/ui/strings.py`
- Modify: `tests/ui/test_security_privacy.py`
- Modify: `tests/ui/test_experimental_recommendation_flow.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_qml_string_catalog.py`
- Modify: `docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md`
- Modify: `docs/qa/experimental-recommendation-vm-runbook.md`

**Interfaces:**
- Consumes: existing string keys and QML controls.
- Produces: `분석 후보 안내` vocabulary with one persistent `실험적 · 자동 실행 안 함` status.

- [ ] **Step 1: Change exact tests first and verify RED**

```python
assert bootstrap.text("entry.guided") == "분석 후보 안내"
assert UI_STRINGS_KO["work.guided"] == "분석 후보"
assert UI_STRINGS_KO["guide.title"] == "분석 후보 안내"
assert UI_STRINGS_KO["guide.experimental_status"] == "실험적 · 자동 실행 안 함"
assert UI_STRINGS_KO["guide.candidate_list"] == "분석 후보 목록"
assert UI_STRINGS_KO["guide.candidate_label"] == "분석 후보"
assert UI_STRINGS_KO["guide.no_recommendation"] == "현재 규칙으로 표시할 분석 후보가 없습니다. 수동 분석을 사용할 수 있습니다."
assert "분석 자동 추천" not in UI_STRINGS_KO.values()
```

Retain source assertions that the persistent status and order disclaimer are visible.

- [ ] **Step 2: Update only catalog values**

```python
"entry.guided": "분석 후보 안내",
"work.guided": "분석 후보",
"guide.title": "분석 후보 안내",
"guide.experimental_status": "실험적 · 자동 실행 안 함",
"guide.candidate_list": "분석 후보 목록",
"guide.candidate_label": "분석 후보",
"guide.no_recommendation": "현재 규칙으로 표시할 분석 후보가 없습니다. 수동 분석을 사용할 수 있습니다.",
```

- [ ] **Step 3: Reconcile the earlier spec and VM runbook**

Add a dated amendment link to the new grid design, replace superseded exact wording, and keep the order disclaimer plus no-preselection checks.

- [ ] **Step 4: Run focused UI and product-wording gates**

```powershell
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests\ui\test_security_privacy.py tests\ui\test_experimental_recommendation_flow.py tests\ui\test_guided_standard_variable_selection_flow.py tests\ui\test_qml_string_catalog.py tests\test_product_recommendation_wording.py
& 'C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe' scripts\check_product_wording.py
```

Expected: all tests pass and the scanner exits 0.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/ui/strings.py tests/ui/test_security_privacy.py tests/ui/test_experimental_recommendation_flow.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_qml_string_catalog.py docs/superpowers/specs/2026-07-11-experimental-recommendation-boundary-design.md docs/qa/experimental-recommendation-vm-runbook.md
git commit -m "fix: simplify experimental candidate wording"
```

### Task 4: Host Visual, Full Gate, Package, And VM Evidence

**Files:**
- Modify: `docs/qa/experimental-recommendation-release-evidence.md`

**Interfaces:**
- Consumes: Tasks 1-3 and frozen benchmark/payload fixtures.
- Produces: fresh test counts, executable hash, visual evidence, payload, and owner VM status.

- [ ] **Step 1: Run complete data-grid, recommendation, QML-runtime, and UI suites**

Any QML warning, new skip, or failure blocks completion.

- [ ] **Step 2: Capture host visual evidence**

Render real QML with compact and normal viewports, short and overflow models, at origin and scrolled positions. Verify no duplicate short tooltip, no blank overshoot, synchronized headers, and no overlap.

- [ ] **Step 3: Re-run benchmark identity and integrated gate**

Require frozen baseline SHA-256 `FC5D3E9032D086225B0C7C62F4E3145217BA44F8FDDF73CB10E4F5EADD485650`. Run the full gate with explicit R, package check/build/launch, and slow stats.

- [ ] **Step 4: Update evidence and commit**

Record exact counts, skip reasons, package hash, source audit, visual evidence paths, and remaining VM status. Require evidence tests and `git diff --check` to pass.

- [ ] **Step 5: Rebuild payload from the exact worktree**

Require the transcript command line to include `.worktrees\recommendation-benchmark-pilot\scripts\attach_modori_payload_disk.ps1` and matching `-WorkspaceRoot` before VM start.

- [ ] **Step 6: Owner clean-VM regression**

Verify the three corrected behaviors first, then resume selection, configuration, report disclosure, no-candidate recovery, and normal shutdown checks.
