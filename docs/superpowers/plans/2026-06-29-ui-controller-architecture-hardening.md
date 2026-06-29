# UI Controller Architecture Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Modori UI controller a thin Qt-facing coordinator instead of a mixed pipeline, report, result, and state object.

**Architecture:** Extract pipeline-specific operations into `modori.ui.pipeline_ops.PipelineOperations`. Keep `UiController` responsible for Qt properties, slots, state mutation, and service orchestration. Guard the boundary with tests so private pipeline probing and controller bloat do not silently return.

**Tech Stack:** Python 3, PySide6, pytest, existing Modori pipeline/result/reporting modules.

---

### Task 1: Lock the boundary with RED tests

**Files:**
- Modify: `tests/ui/test_architecture_guards.py`
- Create: `tests/ui/test_pipeline_ops.py`

- [ ] **Step 1: Write the controller-boundary guard**

```python
def test_ui_controller_does_not_keep_pipeline_internals() -> None:
    import ast
    from pathlib import Path

    path = Path("src/modori/ui/controller.py")
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    controller = next(
        node for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UiController"
    )
    forbidden = {
        "_variable_keys",
        "_has_downstream_steps",
        "_has_pipeline_step",
        "_metadata_insert_after_step_id",
        "_run_current_pipeline",
        "_display_results_from_pipeline",
        "_kind_for_result",
        "_default_report_exporter",
        "_format_step_chain",
    }
    actual = {node.name for node in controller.body if isinstance(node, ast.FunctionDef)}
    assert sorted(actual & forbidden) == []
```

- [ ] **Step 2: Write the pipeline-ops behavior tests**

```python
from modori.ui.pipeline_ops import PipelineOperations


class FakeVariable:
    origin_step_id = "import"


class FakeDataset:
    variables = {"score": FakeVariable()}


class FakeStep:
    def __init__(self, step_id: str, step_type: str = "import.table") -> None:
        self.id = step_id
        self.step_type = step_type
        self.title = step_id


class FakePipeline:
    def __init__(self) -> None:
        self.steps = [FakeStep("import"), FakeStep("analysis:reliability", "stats.reliability")]
        self.current_dataset = FakeDataset()
        self.variable_keys = {"score"}
        self.analysis_objects = {}
        self.edits = []
        self.insertions = []
        self.recomputed = False

    def edit_params(self, step_id, params):
        self.edits.append((step_id, params))

    def insert_after_and_recompute(self, after_step_id, step, *, dirty_from):
        self.insertions.append((after_step_id, step, dirty_from))

    def recompute(self, dirty_from):
        self.recomputed = True


def test_pipeline_operations_exposes_ui_safe_pipeline_queries() -> None:
    pipeline = FakePipeline()
    ops = PipelineOperations(pipeline)

    assert ops.variable_keys() == {"score"}
    assert ops.has_downstream_steps() is True
    assert ops.has_step("import") is True
    assert ops.metadata_insert_after_step_id("score") == "import"
    assert ops.step_chain_text() == "import -> analysis:reliability"
```

- [ ] **Step 3: Run RED tests**

Run: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\ui\test_architecture_guards.py tests\ui\test_pipeline_ops.py`

Expected: FAIL because `pipeline_ops.py` does not exist and `UiController` still owns the forbidden internals.

### Task 2: Extract `PipelineOperations`

**Files:**
- Create: `src/modori/ui/pipeline_ops.py`
- Modify: `src/modori/ui/controller.py`

- [ ] **Step 1: Create `PipelineOperations`**

The class owns pipeline introspection, step-chain formatting, display-result extraction, recomputation, and default report export.

- [ ] **Step 2: Wire `UiController` through `PipelineOperations`**

Replace controller direct helper calls with `self._pipeline_ops`. When replacing the pipeline after import, rebuild `self._pipeline_ops` from the new pipeline.

- [ ] **Step 3: Remove controller internal helpers**

Delete the forbidden helper methods from `UiController`; do not leave wrappers that merely delegate.

- [ ] **Step 4: Run GREEN tests**

Run: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\ui\test_architecture_guards.py tests\ui\test_pipeline_ops.py tests\ui\test_controller.py tests\ui\test_variable_metadata_editing.py tests\ui\test_smoke_qml.py`

Expected: PASS.

### Task 3: Full verification gate

**Files:**
- No code changes expected.

- [ ] **Step 1: Compile**

Run: `.\.venv\Scripts\python.exe -m compileall -q src tests`

Expected: exit 0.

- [ ] **Step 2: Full test suite, first pass**

Run: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`

Expected: all tests pass.

- [ ] **Step 3: Full test suite, second pass**

Run: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`

Expected: all tests pass.

- [ ] **Step 4: Residue scans**

Run: `rg -n "_variable_keys|_has_downstream_steps|_has_pipeline_step|_metadata_insert_after_step_id|_run_current_pipeline|_display_results_from_pipeline|_kind_for_result|_default_report_exporter|_format_step_chain" src/modori/ui/controller.py`

Expected: no output.
