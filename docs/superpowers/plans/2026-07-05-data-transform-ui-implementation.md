# Data Transform UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Step-backed Data Transform UI: reverse coding, scale-score creation, strengthened variable metadata editing, reproducibility tests, and QML surfaces.

**Architecture:** Add a focused `DataTransformEditor` service in `src/modori/ui/data_transform.py` that validates UI requests and inserts/edits engine data-prep Steps through `PipelineOperations`. Bind it through `UiControllerServices` and thin QML wrapper methods on `UiController`. QML remains a form surface only: all validation, collision checks, and Step creation stay in Python.

**Tech Stack:** Python 3.11, PySide6/QML, pytest, existing Modori `Pipeline`, `RecodeReverseStep`, `ComposeScaleStep`, and `VariableMetadataPatchStep`.

---

## Files

- Create: `src/modori/ui/data_transform.py`
  - Owns reverse-code and scale-score request validation.
  - Builds `RecodeReverseStep` and `ComposeScaleStep`.
  - Uses `PipelineOperations` only; no direct dataframe work.
- Modify: `src/modori/ui/service_contracts.py`
  - Add the small protocol methods needed by `DataTransformEditor` if current protocols do not cover them.
- Modify: `src/modori/ui/pipeline_ops.py`
  - Add reusable transform insertion/edit helpers and output-key collision queries.
- Modify: `src/modori/ui/controller_services.py`
  - Construct and refresh `DataTransformEditor`.
- Modify: `src/modori/ui/controller.py`
  - Add `applyReverseCodeTransform`, `applyScaleScoreTransform`, and QML slot wrappers.
- Modify: `src/modori/ui/strings.py`
  - Add Korean UI labels for transform controls and statuses.
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
  - Add the third `변환` tab.
- Create: `src/modori/ui/qml/components/TransformPanel.qml`
  - Dense form surface for reverse coding and scale scoring.
- Modify: `src/modori/ui/qml/components/DataTable.qml`
  - Show a visible source-protection notice.
- Modify: `src/modori/ui/qml/components/VariableTable.qml`
  - Add label and missing-code editing controls around the existing measure workflow.
- Test: `tests/ui/test_data_transform_editor.py`
- Test: `tests/ui/test_data_transform_controller.py`
- Test: `tests/ui/test_data_transform_qml.py`
- Modify: `tests/test_pipeline_core.py`
  - Add trusted round-trip coverage for import + metadata + reverse + compose.

## Task 1: Data Transform Editor Service

**Files:**
- Create: `src/modori/ui/data_transform.py`
- Modify: `src/modori/ui/pipeline_ops.py`
- Test: `tests/ui/test_data_transform_editor.py`

- [ ] **Step 1: Write failing editor tests**

Add `tests/ui/test_data_transform_editor.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.core import Dataset, Pipeline
from modori.steps import ImportStep
from modori.ui.data_transform import DataTransformEditor
from modori.ui.pipeline_ops import PipelineOperations


def _pipeline_with_data(tmp_path: Path) -> Pipeline:
    data_path = tmp_path / "survey.csv"
    pd.DataFrame(
        {
            "q1": [1, 2, 3],
            "q2": [2, 3, 4],
            "q3": [5, 4, 3],
            "group": [1, 1, 2],
        }
    ).to_csv(data_path, index=False)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    return pipeline


def test_reverse_code_transform_inserts_step_and_marks_outputs(tmp_path: Path) -> None:
    pipeline = _pipeline_with_data(tmp_path)
    editor = DataTransformEditor(PipelineOperations(pipeline))

    result = editor.reverse_code(
        {"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": "_R"},
        pipeline_version=7,
    )

    assert result.ok is True
    assert result.error_code is None
    assert result.changed_step_ids == ["transform:reverse"]
    assert result.pipeline_version == 7
    assert [step.id for step in pipeline.steps] == ["import", "transform:reverse"]
    assert pipeline.steps[-1].step_type == "data.recode_reverse"
    assert pipeline.steps[-1].params == {
        "columns": ["q3"],
        "scale_min": 1.0,
        "scale_max": 5.0,
        "suffix": "_R",
    }
    assert "q3_R" in pipeline.current_dataset.df.columns
    assert pipeline.current_dataset.df["q3"].tolist() == [5, 4, 3]
    assert pipeline.current_dataset.df["q3_R"].tolist() == [1.0, 2.0, 3.0]


def test_reverse_code_rejects_output_collision_without_mutating_pipeline(tmp_path: Path) -> None:
    pipeline = _pipeline_with_data(tmp_path)
    before_steps = list(pipeline.steps)
    editor = DataTransformEditor(PipelineOperations(pipeline))

    result = editor.reverse_code(
        {"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": ""},
        pipeline_version=2,
    )

    assert result.ok is False
    assert result.error_code == "output_name_conflict"
    assert pipeline.steps == before_steps
    assert pipeline.current_dataset.df.columns.tolist() == ["q1", "q2", "q3", "group"]


def test_scale_score_transform_inserts_compose_step(tmp_path: Path) -> None:
    pipeline = _pipeline_with_data(tmp_path)
    editor = DataTransformEditor(PipelineOperations(pipeline))

    result = editor.scale_score(
        {
            "items": ["q1", "q2", "q3"],
            "name": "score",
            "method": "mean",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        },
        pipeline_version=4,
    )

    assert result.ok is True
    assert result.changed_step_ids == ["transform:scale_score"]
    assert pipeline.steps[-1].step_type == "data.compose_scale"
    assert pipeline.steps[-1].params == {
        "items": ["q1", "q2", "q3"],
        "name": "score",
        "method": "mean",
        "missing_policy": {"preset": "survey", "min_valid": 0.8},
    }
    assert pipeline.current_dataset.df["score"].tolist() == [
        8 / 3,
        3.0,
        10 / 3,
    ]


def test_scale_score_rejects_invalid_custom_min_valid_without_mutating_pipeline(
    tmp_path: Path,
) -> None:
    pipeline = _pipeline_with_data(tmp_path)
    before_steps = list(pipeline.steps)
    editor = DataTransformEditor(PipelineOperations(pipeline))

    result = editor.scale_score(
        {
            "items": ["q1", "q2"],
            "name": "score",
            "method": "mean",
            "missing_policy": {"preset": "custom", "min_valid": 1.2},
        },
        pipeline_version=1,
    )

    assert result.ok is False
    assert result.error_code == "invalid_transform"
    assert pipeline.steps == before_steps
    assert "score" not in pipeline.current_dataset.df.columns
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_data_transform_editor.py -q -p no:cacheprovider
```

Expected: fail because `modori.ui.data_transform` does not exist.

- [ ] **Step 3: Implement minimal editor and pipeline helpers**

Create `src/modori/ui/data_transform.py` with:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from modori.steps import ComposeScaleStep, RecodeReverseStep
from modori.ui.contracts import CommandResult
from modori.ui.service_contracts import DataTransformPipelineOps


class DataTransformEditor:
    def __init__(self, pipeline_ops: DataTransformPipelineOps) -> None:
        self._pipeline_ops = pipeline_ops

    def reverse_code(self, payload: Mapping[str, Any], *, pipeline_version: int) -> CommandResult:
        if not self._pipeline_ops.has_pipeline():
            return self._error("변환할 데이터가 없습니다.", "no_pipeline", pipeline_version)
        try:
            columns = self._string_list(payload, "columns", min_count=1)
            scale_min = float(payload["scale_min"])
            scale_max = float(payload["scale_max"])
            suffix = str(payload.get("suffix", "_R"))
        except (KeyError, TypeError, ValueError):
            return self._error("역코딩 설정을 확인해 주세요.", "invalid_transform", pipeline_version)
        if scale_min >= scale_max or len(set(columns)) != len(columns):
            return self._error("역코딩 설정을 확인해 주세요.", "invalid_transform", pipeline_version)
        missing = [key for key in columns if not self._pipeline_ops.has_variable(key)]
        if missing:
            return self._error("알 수 없는 변수입니다: " + ", ".join(missing), "unknown_variable", pipeline_version)
        outputs = [f"{column}{suffix}" for column in columns]
        if len(set(outputs)) != len(outputs) or self._pipeline_ops.any_output_exists(outputs):
            return self._error("새 변수명이 기존 변수와 충돌합니다.", "output_name_conflict", pipeline_version)
        step = RecodeReverseStep(
            id="transform:reverse",
            title="Reverse-code items",
            params={
                "columns": columns,
                "scale_min": scale_min,
                "scale_max": scale_max,
                "suffix": suffix,
            },
        )
        return self._insert_or_edit(step, pipeline_version)

    def scale_score(self, payload: Mapping[str, Any], *, pipeline_version: int) -> CommandResult:
        if not self._pipeline_ops.has_pipeline():
            return self._error("변환할 데이터가 없습니다.", "no_pipeline", pipeline_version)
        try:
            items = self._string_list(payload, "items", min_count=2)
            name = str(payload["name"]).strip()
            method = str(payload.get("method", "mean"))
            missing_policy = dict(payload.get("missing_policy", {"preset": "survey", "min_valid": 0.8}))
        except (KeyError, TypeError, ValueError):
            return self._error("척도 점수 설정을 확인해 주세요.", "invalid_transform", pipeline_version)
        if not name or method not in {"mean", "sum"} or len(set(items)) != len(items):
            return self._error("척도 점수 설정을 확인해 주세요.", "invalid_transform", pipeline_version)
        if missing_policy.get("preset") == "custom":
            try:
                min_valid = float(missing_policy["min_valid"])
            except (KeyError, TypeError, ValueError):
                return self._error("결측 처리 기준을 확인해 주세요.", "invalid_transform", pipeline_version)
            if not 0 < min_valid <= 1:
                return self._error("결측 처리 기준을 확인해 주세요.", "invalid_transform", pipeline_version)
            missing_policy["min_valid"] = min_valid
        missing = [key for key in items if not self._pipeline_ops.has_variable(key)]
        if missing:
            return self._error("알 수 없는 변수입니다: " + ", ".join(missing), "unknown_variable", pipeline_version)
        if self._pipeline_ops.any_output_exists([name]):
            return self._error("새 변수명이 기존 변수와 충돌합니다.", "output_name_conflict", pipeline_version)
        step = ComposeScaleStep(
            id="transform:scale_score",
            title="Compose scale score",
            params={
                "items": items,
                "name": name,
                "method": method,
                "missing_policy": missing_policy,
            },
        )
        return self._insert_or_edit(step, pipeline_version)

    def _insert_or_edit(self, step: object, pipeline_version: int) -> CommandResult:
        try:
            self._pipeline_ops.insert_or_replace_transform_step(step)
        except Exception:
            return self._error("변환 단계를 추가하지 못했습니다.", "engine_error", pipeline_version)
        return CommandResult(
            ok=True,
            message_ko="변환 단계가 추가되었습니다. 다시 실행하면 결과가 업데이트됩니다.",
            pipeline_version=pipeline_version,
            changed_step_ids=[str(getattr(step, "id"))],
        )

    @staticmethod
    def _string_list(payload: Mapping[str, Any], key: str, *, min_count: int) -> list[str]:
        value = payload[key]
        if not isinstance(value, list) or len(value) < min_count:
            raise ValueError(key)
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError(key)
        return list(value)

    @staticmethod
    def _error(message_ko: str, error_code: str, pipeline_version: int) -> CommandResult:
        return CommandResult(ok=False, message_ko=message_ko, error_code=error_code, pipeline_version=pipeline_version)
```

Add `DataTransformPipelineOps` to `src/modori/ui/service_contracts.py`:

```python
class DataTransformPipelineOps(Protocol):
    def has_pipeline(self) -> bool: ...
    def has_variable(self, variable_key: str) -> bool: ...
    def any_output_exists(self, output_keys: list[str]) -> bool: ...
    def insert_or_replace_transform_step(self, step: object) -> None: ...
```

Add helpers to `PipelineOperations`:

```python
    def any_output_exists(self, output_keys: list[str]) -> bool:
        variable_keys = self.variable_keys()
        if variable_keys is None:
            return False
        return any(output_key in variable_keys for output_key in output_keys)

    def insert_or_replace_transform_step(self, step: object) -> None:
        if self._pipeline is None:
            raise RuntimeError("Pipeline does not support transform insertion")
        if self.has_step(str(getattr(step, "id"))):
            self._pipeline.edit_params(str(getattr(step, "id")), dict(getattr(step, "params")))
            return
        after_step_id = self._last_data_prep_step_id()
        if hasattr(self._pipeline, "insert_after_and_recompute") and after_step_id is not None:
            self._pipeline.insert_after_and_recompute(after_step_id, step, dirty_from=str(getattr(step, "id")))
            return
        if hasattr(self._pipeline, "add"):
            self._pipeline.add(step)
            self._pipeline.recompute(dirty_from=str(getattr(step, "id")))
            return
        raise RuntimeError("Pipeline does not support transform insertion")

    def _last_data_prep_step_id(self) -> str | None:
        data_step_types = {"import.table", "data.variable_metadata_patch", "data.recode_reverse", "data.compose_scale"}
        candidate = None
        for step in self.steps():
            if self._step_type(step) in data_step_types:
                candidate = self._step_id(step)
        return candidate
```

- [ ] **Step 4: Run editor tests to verify GREEN**

Run the same command from Step 2. Expected: all tests in `tests/ui/test_data_transform_editor.py` pass.

- [ ] **Step 5: Commit Task 1**

```powershell
git add src\modori\ui\data_transform.py src\modori\ui\pipeline_ops.py src\modori\ui\service_contracts.py tests\ui\test_data_transform_editor.py
git commit -m "feat: add data transform editor"
```

## Task 2: Controller Binding

**Files:**
- Modify: `src/modori/ui/controller_services.py`
- Modify: `src/modori/ui/controller.py`
- Test: `tests/ui/test_data_transform_controller.py`

- [ ] **Step 1: Write failing controller tests**

Add `tests/ui/test_data_transform_controller.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController


def _write_csv(path: Path) -> None:
    pd.DataFrame({"q1": [1, 2], "q2": [2, 3], "q3": [5, 4], "group": [1, 2]}).to_csv(path, index=False)


def test_controller_applies_reverse_code_transform_and_marks_results_stale(tmp_path: Path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    assert controller.openDataFile(data_path, ImportOptions(confirm_new_session=True)).ok is True
    before_version = controller.pipeline_version

    result = controller.applyReverseCodeTransform(
        {"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": "_R"}
    )

    assert result.ok is True
    assert result.changed_step_ids == ["transform:reverse"]
    assert controller.pipeline_version == before_version + 1
    assert controller.stale is True
    assert "Reverse-code items" in controller.stepChainText
    assert "q3_R" in controller.pipeline.current_dataset.df.columns


def test_controller_applies_scale_score_transform(tmp_path: Path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))

    result = controller.applyScaleScoreTransform(
        {
            "items": ["q1", "q2", "q3"],
            "name": "score",
            "method": "mean",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        }
    )

    assert result.ok is True
    assert "Compose scale score" in controller.stepChainText
    assert "score" in controller.pipeline.current_dataset.df.columns


def test_controller_rejects_invalid_transform_without_version_bump(tmp_path: Path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
    before_version = controller.pipeline_version

    result = controller.applyScaleScoreTransform(
        {"items": ["q1"], "name": "", "method": "mean", "missing_policy": {"preset": "survey"}}
    )

    assert result.ok is False
    assert result.error_code == "invalid_transform"
    assert controller.pipeline_version == before_version
    assert "score" not in controller.pipeline.current_dataset.df.columns
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_data_transform_controller.py -q -p no:cacheprovider
```

Expected: fail because controller methods do not exist.

- [ ] **Step 3: Bind service and controller**

In `UiControllerServices`, add field and construction:

```python
from modori.ui.data_transform import DataTransformEditor

data_transform_editor: DataTransformEditor

data_transform_editor=DataTransformEditor(pipeline_ops),
```

In `replace_pipeline`, rebuild it:

```python
self.data_transform_editor = DataTransformEditor(self.pipeline_ops)
```

In `UiController`, add:

```python
    def applyReverseCodeTransform(self, payload: Mapping[str, Any]) -> CommandResult:
        result = self._services.data_transform_editor.reverse_code(
            payload,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result)

    def applyScaleScoreTransform(self, payload: Mapping[str, Any]) -> CommandResult:
        result = self._services.data_transform_editor.scale_score(
            payload,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_transform_result(result)

    def _apply_transform_result(self, result: CommandResult) -> CommandResult:
        if not result.ok:
            self._last_error = result.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._pipeline_state.mark_step_changed(self._services.pipeline_ops, fallback=self.stepsModel)
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self._refresh_recommendations()
        self._last_error = ""
        self._last_message = result.message_ko
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )
```

- [ ] **Step 4: Add QML slot wrappers**

Add minimal string wrappers:

```python
    @Slot(str, str, float, float, result=bool)
    def reverseCodeFromText(self, columns_text: str, suffix: str, scale_min: float, scale_max: float) -> bool:
        columns = [item.strip() for item in columns_text.split(",") if item.strip()]
        return self.applyReverseCodeTransform(
            {"columns": columns, "scale_min": scale_min, "scale_max": scale_max, "suffix": suffix or "_R"}
        ).ok

    @Slot(str, str, str, str, float, result=bool)
    def scaleScoreFromText(self, items_text: str, name: str, method_label: str, policy_label: str, min_valid: float) -> bool:
        items = [item.strip() for item in items_text.split(",") if item.strip()]
        method = "sum" if method_label == "sum" else "mean"
        if policy_label == "conservative":
            policy = {"preset": "conservative"}
        elif policy_label == "custom":
            policy = {"preset": "custom", "min_valid": float(min_valid)}
        else:
            policy = {"preset": "survey", "min_valid": 0.8}
        return self.applyScaleScoreTransform(
            {"items": items, "name": name.strip(), "method": method, "missing_policy": policy}
        ).ok
```

- [ ] **Step 5: Run controller tests to verify GREEN**

Run the same command from Step 2. Expected: pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add src\modori\ui\controller.py src\modori\ui\controller_services.py tests\ui\test_data_transform_controller.py
git commit -m "feat: bind data transforms to controller"
```

## Task 3: QML Transform Surface And Variable Properties

**Files:**
- Create: `src/modori/ui/qml/components/TransformPanel.qml`
- Modify: `src/modori/ui/qml/screens/WorkScreen.qml`
- Modify: `src/modori/ui/qml/components/DataTable.qml`
- Modify: `src/modori/ui/qml/components/VariableTable.qml`
- Modify: `src/modori/ui/strings.py`
- Test: `tests/ui/test_data_transform_qml.py`

- [ ] **Step 1: Write failing QML tests**

Add `tests/ui/test_data_transform_qml.py`:

```python
from pathlib import Path


def qml_text(relative: str) -> str:
    return Path("src/modori/ui/qml").joinpath(relative).read_text(encoding="utf-8")


def test_work_screen_exposes_transform_tab() -> None:
    work_screen = qml_text("screens/WorkScreen.qml")

    assert "work.transform_view" in work_screen
    assert "TransformPanel" in work_screen


def test_transform_panel_calls_controller_transform_methods() -> None:
    transform_panel = qml_text("components/TransformPanel.qml")

    assert "transform.reverse_title" in transform_panel
    assert "transform.scale_title" in transform_panel
    assert "uiController.reverseCodeFromText" in transform_panel
    assert "uiController.scaleScoreFromText" in transform_panel
    assert "transform.source_protected" in transform_panel


def test_data_table_shows_source_protection_notice() -> None:
    data_table = qml_text("components/DataTable.qml")

    assert "transform.source_protected" in data_table


def test_variable_table_exposes_label_and_missing_code_controls() -> None:
    variable_table = qml_text("components/VariableTable.qml")

    assert "variable.label_placeholder" in variable_table
    assert "variable.missing_codes_placeholder" in variable_table
    assert "uiController.updateVariableMetadataFromText" in variable_table
```

- [ ] **Step 2: Run QML tests to verify RED**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_data_transform_qml.py -q -p no:cacheprovider
```

Expected: fail because the transform panel and strings are missing.

- [ ] **Step 3: Add strings**

Add these keys to `UI_STRINGS_KO`:

```python
"transform.view": "변환",
"work.transform_view": "변환",
"transform.source_protected": "원본 데이터는 직접 수정하지 않습니다. 변환은 새 단계와 새 변수로 기록됩니다.",
"transform.reverse_title": "역코딩",
"transform.reverse_columns": "역코딩할 변수",
"transform.reverse_suffix": "새 변수 접미사",
"transform.scale_min": "최솟값",
"transform.scale_max": "최댓값",
"transform.apply_reverse": "역코딩 적용",
"transform.scale_title": "척도 점수 만들기",
"transform.scale_items": "문항 변수",
"transform.scale_name": "새 변수 이름",
"transform.scale_method": "계산 방법",
"transform.scale_policy": "결측 처리",
"transform.min_valid": "유효 응답 비율",
"transform.apply_scale": "척도 점수 적용",
"variable.label_placeholder": "변수 레이블",
"variable.missing_codes_placeholder": "결측 코드: 9, 99",
"variable.metadata_apply": "속성 변경",
```

- [ ] **Step 4: Add controller metadata text slot**

Add to `UiController`:

```python
    @Slot(str, str, str, result=bool)
    def updateVariableMetadataFromText(self, variable_key: str, label: str, missing_codes_text: str) -> bool:
        patch: dict[str, object] = {}
        if label.strip():
            patch["label"] = label.strip()
        if missing_codes_text.strip():
            try:
                patch["missing_codes"] = [
                    float(item.strip()) for item in missing_codes_text.split(",") if item.strip()
                ]
            except ValueError:
                self._command_error("결측 코드는 숫자 목록이어야 합니다.", "invalid_metadata_patch")
                return False
        if not patch:
            self._command_error("변경할 속성이 없습니다.", "invalid_metadata_patch")
            return False
        return self.updateVariableMetadata(variable_key, patch).ok
```

- [ ] **Step 5: Create TransformPanel.qml**

Create a dense `ColumnLayout` with:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Label { text: appBootstrap.text("transform.source_protected"); wrapMode: Text.WordWrap; Layout.fillWidth: true }

        GroupBox {
            title: appBootstrap.text("transform.reverse_title")
            Layout.fillWidth: true
            GridLayout {
                columns: 2
                anchors.fill: parent
                Label { text: appBootstrap.text("transform.reverse_columns") }
                TextField { id: reverseColumns; placeholderText: "q3, q7"; Layout.fillWidth: true; Accessible.name: appBootstrap.text("transform.reverse_columns") }
                Label { text: appBootstrap.text("transform.scale_min") }
                SpinBox { id: reverseMin; from: -999; to: 999; value: 1; Accessible.name: appBootstrap.text("transform.scale_min") }
                Label { text: appBootstrap.text("transform.scale_max") }
                SpinBox { id: reverseMax; from: -999; to: 999; value: 5; Accessible.name: appBootstrap.text("transform.scale_max") }
                Label { text: appBootstrap.text("transform.reverse_suffix") }
                TextField { id: reverseSuffix; text: "_R"; Layout.fillWidth: true; Accessible.name: appBootstrap.text("transform.reverse_suffix") }
                Item {}
                Button {
                    text: appBootstrap.text("transform.apply_reverse")
                    enabled: uiController.status !== "running"
                    onClicked: uiController.reverseCodeFromText(reverseColumns.text, reverseSuffix.text, reverseMin.value, reverseMax.value)
                }
            }
        }

        GroupBox {
            title: appBootstrap.text("transform.scale_title")
            Layout.fillWidth: true
            GridLayout {
                columns: 2
                anchors.fill: parent
                Label { text: appBootstrap.text("transform.scale_items") }
                TextField { id: scaleItems; placeholderText: "q1, q2, q3"; Layout.fillWidth: true; Accessible.name: appBootstrap.text("transform.scale_items") }
                Label { text: appBootstrap.text("transform.scale_name") }
                TextField { id: scaleName; placeholderText: "job_sat"; Layout.fillWidth: true; Accessible.name: appBootstrap.text("transform.scale_name") }
                Label { text: appBootstrap.text("transform.scale_method") }
                ComboBox { id: scaleMethod; model: ["mean", "sum"]; Accessible.name: appBootstrap.text("transform.scale_method") }
                Label { text: appBootstrap.text("transform.scale_policy") }
                ComboBox { id: scalePolicy; model: ["survey", "conservative", "custom"]; Accessible.name: appBootstrap.text("transform.scale_policy") }
                Label { text: appBootstrap.text("transform.min_valid") }
                SpinBox { id: minValid; from: 1; to: 100; value: 80; Accessible.name: appBootstrap.text("transform.min_valid") }
                Item {}
                Button {
                    text: appBootstrap.text("transform.apply_scale")
                    enabled: uiController.status !== "running"
                    onClicked: uiController.scaleScoreFromText(scaleItems.text, scaleName.text, scaleMethod.currentText, scalePolicy.currentText, minValid.value / 100)
                }
            }
        }
    }
}
```

- [ ] **Step 6: Wire WorkScreen tab**

In `WorkScreen.qml`, add a third `TabButton`:

```qml
TabButton { text: appBootstrap.text("work.transform_view") }
```

and add `TransformPanel {}` as the third `StackLayout` child.

- [ ] **Step 7: Strengthen DataTable and VariableTable**

In `DataTable.qml`, add a visible `Label` for `transform.source_protected` above the existing notice.

In `VariableTable.qml`, add `TextField` controls for label and missing codes plus a button calling:

```qml
uiController.updateVariableMetadataFromText(root.selectedVariableKey, labelField.text, missingCodesField.text)
```

- [ ] **Step 8: Run QML tests to verify GREEN**

Run the same command from Step 2. Expected: pass.

- [ ] **Step 9: Commit Task 3**

```powershell
git add src\modori\ui\qml\components\TransformPanel.qml src\modori\ui\qml\screens\WorkScreen.qml src\modori\ui\qml\components\DataTable.qml src\modori\ui\qml\components\VariableTable.qml src\modori\ui\strings.py src\modori\ui\controller.py tests\ui\test_data_transform_qml.py
git commit -m "feat: add data transform ui surface"
```

## Task 4: Reproducibility And Guard Verification

**Files:**
- Modify: `tests/test_pipeline_core.py`
- Modify as needed: focused tests from earlier tasks

- [ ] **Step 1: Write failing pipeline round-trip test**

Add to `tests/test_pipeline_core.py`:

```python
def test_pipeline_json_round_trip_preserves_data_transform_steps(tmp_path) -> None:
    import pandas as pd

    from modori.steps import ComposeScaleStep, ImportStep, RecodeReverseStep, VariableMetadataPatchStep

    data_path = tmp_path / "survey.csv"
    pd.DataFrame({"q1": [1, 2], "q2": [2, 3], "q3": [5, 4]}).to_csv(data_path, index=False)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(ImportStep(id="import", title="Import CSV", params={"path": str(data_path), "file_type": "csv"}))
    pipeline.insert_after(
        "import",
        VariableMetadataPatchStep(
            id="metadata:q3",
            title="Edit metadata: q3",
            params={"variable_key": "q3", "measure": "ordinal", "missing_values": []},
        ),
    )
    pipeline.add(
        RecodeReverseStep(
            id="transform:reverse",
            title="Reverse-code items",
            params={"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": "_R"},
        )
    )
    pipeline.add(
        ComposeScaleStep(
            id="transform:scale_score",
            title="Compose scale score",
            params={
                "items": ["q1", "q2", "q3_R"],
                "name": "score",
                "method": "mean",
                "missing_policy": {"preset": "survey", "min_valid": 0.8},
            },
        )
    )
    pipeline.recompute(dirty_from=None)

    restored = Pipeline.from_json(pipeline.to_json(), trusted_project_json=True)

    assert [step.id for step in restored.steps] == [
        "import",
        "metadata:q3",
        "transform:reverse",
        "transform:scale_score",
    ]
    pd.testing.assert_frame_equal(restored.current_dataset.df, pipeline.current_dataset.df)
    assert restored.current_dataset.df["q3"].tolist() == [5, 4]
    assert restored.current_dataset.df["q3_R"].tolist() == [1.0, 2.0]
    assert restored.current_dataset.df["score"].tolist() == [4 / 3, 7 / 3]
```

- [ ] **Step 2: Run round-trip test to verify RED or PASS**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\test_pipeline_core.py::test_pipeline_json_round_trip_preserves_data_transform_steps -q -p no:cacheprovider
```

Expected: It may pass if engine serialization already supports these Steps. If it fails because `RecodeReverseStep` does not serialize `suffix`, update `RecodeReverseStep.compute`, `writes`, and `provenance` to use `params.get("suffix", "_R")`.

- [ ] **Step 3: Run focused suite**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_data_transform_editor.py tests\ui\test_data_transform_controller.py tests\ui\test_data_transform_qml.py tests\ui\test_variable_metadata_editing.py tests\ui\test_patches.py tests\test_data_prep_steps.py tests\test_pipeline_core.py::test_pipeline_json_round_trip_preserves_data_transform_steps -q -p no:cacheprovider
```

Expected: all selected tests pass.

- [ ] **Step 4: Run UI guard tests**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe -m pytest tests\ui\test_architecture_guards.py tests\ui\test_thin_shell_guards.py tests\ui\test_smoke_qml.py -q -p no:cacheprovider
```

Expected: all selected tests pass.

- [ ] **Step 5: Run release gate without package rebuild**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
C:\Users\V\Desktop\TongTong\.venv\Scripts\python.exe scripts\quality_gate.py --with-package-check --with-packaged-launch
```

Expected: compileall, ruff, bandit, launch smoke, pytest, pip check, package check, packaged launch smoke, and package engine smoke all pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add tests\test_pipeline_core.py src\modori\steps\data_prep.py
git commit -m "test: cover transform pipeline reproducibility"
```

Commit only files that changed in this task.

## Self-Review

Spec coverage:

- Reverse-code UI and service: Task 1, Task 2, Task 3.
- Scale-score UI and service: Task 1, Task 2, Task 3.
- Variable metadata strengthening: Task 3 plus existing metadata tests.
- Source data protection notice: Task 3.
- Output collision validation: Task 1.
- Reproducibility through pipeline JSON: Task 4.
- Thin-shell guard and release verification: Task 4.

No direct cell editing is included. Project save/open UI is intentionally out of scope; Task 4 covers core pipeline JSON reproducibility only.

