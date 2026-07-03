# Novice Analysis Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make post-import analysis safe for novice users by showing explainable recommendation candidates, requiring explicit run action, blocking invalid configurations before the engine worker, and preserving result-display integrity.

**Architecture:** Keep recommendation generation pure and dataset-driven, separate it from pipeline mutation, and make execution fail-closed through a run validator immediately before worker submission. QML displays the controller's preparation state; selecting a recommendation updates prepared fields only, while result binding validates completed payloads without generating next-analysis recommendations.

**Tech Stack:** Python dataclasses, pandas, PySide6 `Property`/`Slot`, QML Controls, pytest, existing Modori pipeline/step contracts.

---

### Task 1: Keep SAV `unknown` Measure Import Safe

**Files:**
- Modify: `tests/test_data_prep_steps.py`
- Modify: `src/modori/steps/data_prep.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_data_prep_steps.py` near the existing metadata variable tests:

```python
def test_import_step_treats_unknown_sav_measure_as_inferred_measure() -> None:
    import pandas as pd

    from modori.core import Measure
    from modori.steps.data_prep import TabularMetadata, metadata_variables

    frame = pd.DataFrame({"score": [1, 2, 3], "group": ["a", "b", "a"]})
    metadata = TabularMetadata(variable_measure={"score": "unknown", "group": "unknown"})

    variables = metadata_variables(frame, origin_step_id="preview", metadata=metadata)

    assert variables["score"].measure is Measure.ORDINAL
    assert variables["group"].measure is Measure.NOMINAL
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_data_prep_steps.py::test_import_step_treats_unknown_sav_measure_as_inferred_measure -q -p no:cacheprovider
```

Expected: FAIL with `ValueError: 'unknown' is not a valid Measure`.

- [ ] **Step 3: Implement the fallback**

In `src/modori/steps/data_prep.py`, update the `metadata_variables` branch that reads `metadata.variable_measure` so only known `Measure` enum values override inferred measures. Unknown metadata values must leave the already inferred measure unchanged:

```python
        if metadata is not None and column in metadata.variable_measure:
            metadata_measure = str(metadata.variable_measure[column]).lower()
            valid_measure_values = {item.value for item in Measure}
            if metadata_measure in valid_measure_values:
                measure = Measure(metadata_measure)
```

- [ ] **Step 4: Run the focused import tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_data_prep_steps.py tests\ui\test_importing_service.py tests\test_table_io.py -q -p no:cacheprovider
```

Expected: PASS with all tests green.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/steps/data_prep.py tests/test_data_prep_steps.py
git commit -m "fix: infer unknown sav measure metadata"
```

### Task 2: Remove Automatic Analysis After Import

**Files:**
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `src/modori/ui/qml/Main.qml`

- [ ] **Step 1: Write the failing static QML test**

Add this test to `tests/ui/test_import_dialog_flow.py`:

```python
def _qml_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_import_and_recent_file_paths_do_not_start_analysis_automatically() -> None:
    main = qml_text("Main.qml")

    recent_block = _qml_block(main, "onRecentFileRequested:", "WorkScreen")
    import_block = _qml_block(main, "onImportAccepted:", "ReportExportDialog")

    assert "uiController.rerunNow()" not in recent_block
    assert "uiController.rerunNow()" not in import_block
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_import_dialog_flow.py::test_import_and_recent_file_paths_do_not_start_analysis_automatically -q -p no:cacheprovider
```

Expected: FAIL because `Main.qml` still calls `uiController.rerunNow()` after recent-file open and import confirmation.

- [ ] **Step 3: Remove the automatic runs**

In `src/modori/ui/qml/Main.qml`, change the recent-file and import-accepted handlers to:

```qml
        onRecentFileRequested: {
            if (uiController.openRecentFileAt(index)) {
                root.currentScreen = "work"
            }
        }
```

```qml
        onImportAccepted: {
            if (uiController.confirmPendingImport()) {
                root.currentScreen = "work"
                importDialog.close()
            }
        }
```

- [ ] **Step 4: Run the import dialog tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_import_dialog_flow.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/ui/qml/Main.qml tests/ui/test_import_dialog_flow.py
git commit -m "fix: stop auto analysis after import"
```

### Task 3: Add Dataset-Driven Recommendation Candidates

**Files:**
- Create: `src/modori/ui/recommendations.py`
- Create: `tests/ui/test_recommendations.py`

- [ ] **Step 1: Write recommendation service tests**

Create `tests/ui/test_recommendations.py` with:

```python
from __future__ import annotations

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.ui.recommendations import RecommendationService


def _variable(name: str, measure: Measure, dtype: str = "int64") -> Variable:
    return Variable(
        name=name,
        label=None,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype=dtype,
        origin_step_id="import",
    )


def _dataset(frame: pd.DataFrame) -> Dataset:
    variables = {}
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            measure = Measure.SCALE
            dtype = "float64"
        else:
            measure = Measure.NOMINAL
            dtype = "object"
        variables[column] = _variable(column, measure, dtype)
    return Dataset(df=frame, variables=variables)


def test_recommendation_service_produces_item_group_candidates_for_bfi_columns() -> None:
    frame = pd.read_csv("tests/fixtures/psych_bfi.csv").head(60)

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is not None
    assert state.default_candidate.kind == "reliability"
    assert state.default_candidate.level == "강한 추천"
    assert state.default_candidate.item_keys == ["A1", "A2", "A3", "A4", "A5"]
    assert "같은 접두사" in state.default_candidate.reason_ko
    assert ["C1", "C2", "C3", "C4", "C5"] in [
        candidate.item_keys for candidate in state.candidates if candidate.kind == "reliability"
    ]
    assert ["E1", "E2", "E3", "E4", "E5"] in [
        candidate.item_keys for candidate in state.candidates if candidate.kind == "reliability"
    ]


def test_recommendation_service_produces_two_group_comparison_candidate() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 2, 3, 4, 5],
            "A2": [1, 2, 3, 4, 2, 3, 4, 5],
            "A3": [1, 2, 3, 4, 2, 3, 4, 5],
            "gender": [1, 1, 1, 1, 2, 2, 2, 2],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    comparison = next(candidate for candidate in state.candidates if candidate.kind == "comparison")
    assert comparison.outcome_key == "A1"
    assert comparison.group_key == "gender"
    assert comparison.level in {"강한 추천", "가능한 후보"}
    assert "두 집단" in comparison.reason_ko


def test_recommendation_service_returns_no_default_without_safe_candidate() -> None:
    frame = pd.DataFrame(
        {
            "id": [1001, 1002, 1003, 1004],
            "constant": [1, 1, 1, 1],
            "mostly_missing": [None, None, None, 3],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is None
    assert state.candidates == []
    assert state.message_ko == "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."


def test_caution_candidates_are_not_default_when_stronger_candidates_exist() -> None:
    frame = pd.DataFrame(
        {
            "A1": [1, 2, 3, 4, 5, 6],
            "A2": [1, 2, 3, 4, 5, 6],
            "A3": [1, 2, 3, 4, 5, 6],
            "age": [18, 20, 22, 24, 26, 28],
        }
    )

    state = RecommendationService().recommend(_dataset(frame))

    assert state.default_candidate is not None
    assert state.default_candidate.level != "주의 필요"
    assert any(candidate.level == "주의 필요" for candidate in state.candidates)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_recommendations.py -q -p no:cacheprovider
```

Expected: FAIL with `ModuleNotFoundError: No module named 'modori.ui.recommendations'`.

- [ ] **Step 3: Implement recommendation contracts and service**

Create `src/modori/ui/recommendations.py` with these public contracts and deterministic heuristics:

```python
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

import pandas as pd


RecommendationKind = Literal["reliability", "comparison", "regression"]
RecommendationLevel = Literal["강한 추천", "가능한 후보", "주의 필요"]


@dataclass(frozen=True)
class RecommendationCandidate:
    candidate_id: str
    kind: RecommendationKind
    title_ko: str
    level: RecommendationLevel
    reason_ko: str
    item_keys: list[str] = field(default_factory=list)
    outcome_key: str = ""
    group_key: str = ""
    predictor_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecommendationState:
    candidates: list[RecommendationCandidate]
    default_candidate: RecommendationCandidate | None
    selected_candidate: RecommendationCandidate | None
    message_ko: str = ""


class RecommendationService:
    def recommend(self, dataset: object | None) -> RecommendationState:
        frame = getattr(dataset, "df", None)
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return self._empty_state()
        frame = frame.copy()
        usable = [column for column in frame.columns if self._is_usable_column(frame[column], str(column))]
        numeric = [column for column in usable if pd.api.types.is_numeric_dtype(frame[column])]
        item_groups = self._item_groups(frame, numeric)
        candidates: list[RecommendationCandidate] = []
        candidates.extend(self._reliability_candidates(frame, item_groups))
        candidates.extend(self._comparison_candidates(frame, numeric, usable))
        candidates.extend(self._caution_candidates(frame, numeric, item_groups))
        candidates = self._rank(candidates)
        default = self._default_candidate(candidates)
        message = "" if candidates else "안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요."
        return RecommendationState(
            candidates=candidates,
            default_candidate=default,
            selected_candidate=default,
            message_ko=message,
        )

    @staticmethod
    def _empty_state() -> RecommendationState:
        return RecommendationState(
            candidates=[],
            default_candidate=None,
            selected_candidate=None,
            message_ko="안전하게 추천할 분석을 찾지 못했습니다. 직접 변수를 선택해 주세요.",
        )

    @staticmethod
    def _is_usable_column(series: pd.Series, column: str) -> bool:
        lower = column.lower()
        if lower in {"id", "rowid", "row_id", "rownames", "index"}:
            return False
        non_missing = series.dropna()
        if len(series) == 0 or len(non_missing) / len(series) < 0.5:
            return False
        return non_missing.nunique(dropna=True) > 1

    @staticmethod
    def _is_survey_numeric(series: pd.Series) -> bool:
        non_missing = pd.to_numeric(series, errors="coerce").dropna()
        if non_missing.empty:
            return False
        if non_missing.nunique() > 11:
            return False
        return float(non_missing.min()) >= 0 and float(non_missing.max()) <= 10

    def _item_groups(self, frame: pd.DataFrame, numeric: list[str]) -> list[tuple[str, list[str]]]:
        grouped: dict[str, list[tuple[int, str]]] = {}
        for column in numeric:
            match = re.match(r"^([A-Za-z가-힣_]+)(\d+)$", str(column))
            if match is None or not self._is_survey_numeric(frame[column]):
                continue
            grouped.setdefault(match.group(1), []).append((int(match.group(2)), str(column)))
        result: list[tuple[str, list[str]]] = []
        for prefix, numbered_columns in grouped.items():
            ordered = [column for _, column in sorted(numbered_columns)]
            if len(ordered) >= 3:
                result.append((prefix, ordered))
        return sorted(result, key=lambda item: (item[0], len(item[1])))

    def _reliability_candidates(
        self,
        frame: pd.DataFrame,
        item_groups: list[tuple[str, list[str]]],
    ) -> list[RecommendationCandidate]:
        candidates: list[RecommendationCandidate] = []
        for prefix, item_keys in item_groups:
            level: RecommendationLevel = "강한 추천" if len(item_keys) >= 5 else "가능한 후보"
            reason = f"같은 접두사 {prefix}, {len(item_keys)}개의 숫자형 설문 문항, 유사한 값 범위"
            candidates.append(
                RecommendationCandidate(
                    candidate_id=f"reliability:{prefix}",
                    kind="reliability",
                    title_ko=f"신뢰도 분석: {item_keys[0]}-{item_keys[-1]}",
                    level=level,
                    reason_ko=reason,
                    item_keys=item_keys,
                )
            )
        return candidates

    def _comparison_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
        usable: list[str],
    ) -> list[RecommendationCandidate]:
        groups = [column for column in usable if self._is_two_group_column(frame[column])]
        outcomes = [column for column in numeric if column not in groups and self._is_survey_numeric(frame[column])]
        if not groups or not outcomes:
            return []
        group = self._preferred_group(groups)
        outcome = outcomes[0]
        return [
            RecommendationCandidate(
                candidate_id=f"comparison:{outcome}:{group}",
                kind="comparison",
                title_ko=f"집단 비교: {outcome} by {group}",
                level="강한 추천",
                reason_ko=f"{group}는 두 집단 변수이고 {outcome}는 숫자형 결과 변수입니다.",
                outcome_key=str(outcome),
                group_key=str(group),
            )
        ]

    @staticmethod
    def _is_two_group_column(series: pd.Series) -> bool:
        return series.dropna().nunique(dropna=True) == 2

    @staticmethod
    def _preferred_group(groups: list[str]) -> str:
        return "gender" if "gender" in groups else groups[0]

    def _caution_candidates(
        self,
        frame: pd.DataFrame,
        numeric: list[str],
        item_groups: list[tuple[str, list[str]]],
    ) -> list[RecommendationCandidate]:
        grouped_columns = {column for _, columns in item_groups for column in columns}
        candidates: list[RecommendationCandidate] = []
        for column in numeric:
            lower = str(column).lower()
            if lower in {"age", "education"} and column not in grouped_columns:
                outcome = next(
                    (
                        str(candidate)
                        for candidate in numeric
                        if candidate != column and candidate not in grouped_columns and self._is_survey_numeric(frame[candidate])
                    ),
                    "",
                )
                if not outcome:
                    continue
                candidates.append(
                    RecommendationCandidate(
                        candidate_id=f"regression-caution:{column}",
                        kind="regression",
                        title_ko=f"회귀 후보: {column} -> {outcome}",
                        level="주의 필요",
                        reason_ko=f"{column}는 예측 변수로 가능하지만 연구 의도가 명확하지 않습니다.",
                        outcome_key=outcome,
                        predictor_keys=[str(column)],
                    )
                )
        return candidates

    @staticmethod
    def _rank(candidates: list[RecommendationCandidate]) -> list[RecommendationCandidate]:
        level_rank = {"강한 추천": 0, "가능한 후보": 1, "주의 필요": 2}
        kind_rank = {"reliability": 0, "comparison": 1, "regression": 2}
        return sorted(
            candidates,
            key=lambda candidate: (
                level_rank[candidate.level],
                kind_rank[candidate.kind],
                len(candidate.reason_ko),
                candidate.candidate_id,
            ),
        )

    @staticmethod
    def _default_candidate(
        candidates: list[RecommendationCandidate],
    ) -> RecommendationCandidate | None:
        if not candidates:
            return None
        for candidate in candidates:
            if candidate.level != "주의 필요":
                return candidate
        return candidates[0]
```

- [ ] **Step 4: Run recommendation tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_recommendations.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- src/modori/ui/recommendations.py tests/ui/test_recommendations.py
git commit -m "feat: add novice recommendation candidates"
```

### Task 4: Expose Preparation State Through the Controller

**Files:**
- Modify: `src/modori/ui/controller_services.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `tests/ui/test_controller.py`

- [ ] **Step 1: Write controller tests for recommendation state**

Add these tests to `tests/ui/test_controller.py`:

```python
def test_open_data_file_populates_recommendation_without_running_worker(tmp_path) -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    class FakeWorker:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            self.calls.append((run_id, pipeline_version, job))
            raise AssertionError("worker must not run during import")

    class PipelineWithDataset:
        def __init__(self) -> None:
            frame = pd.DataFrame(
                {
                    "A1": [1, 2, 3, 4, 5],
                    "A2": [1, 2, 3, 4, 5],
                    "A3": [1, 2, 3, 4, 5],
                }
            )
            self.current_dataset = Dataset(
                df=frame,
                variables={
                    column: Variable(
                        name=column,
                        label=None,
                        measure=Measure.SCALE,
                        value_labels={},
                        missing_values=[],
                        dtype="int64",
                        origin_step_id="import",
                    )
                    for column in frame.columns
                },
            )
            self.steps = []
            self.variable_keys = set(frame.columns)

    worker = FakeWorker()
    controller = UiController(
        pipeline_factory=lambda path, options: PipelineWithDataset(),
        worker=worker,
    )

    result = controller.openDataFile(tmp_path / "survey.csv", ImportOptions(confirm_new_session=True))

    assert result.ok is True
    assert controller.recommendationTitle.startswith("신뢰도 분석")
    assert controller.recommendationLevel in {"강한 추천", "가능한 후보"}
    assert "접두사" in controller.recommendationReason
    assert controller.recommendationAlternativesText
    assert worker.calls == []


def test_select_recommendation_updates_prepared_fields_without_running(tmp_path) -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    class PipelineWithDataset:
        def __init__(self) -> None:
            frame = pd.DataFrame(
                {
                    "A1": [1, 2, 3, 4, 5],
                    "A2": [1, 2, 3, 4, 5],
                    "A3": [1, 2, 3, 4, 5],
                    "C1": [1, 2, 3, 4, 5],
                    "C2": [1, 2, 3, 4, 5],
                    "C3": [1, 2, 3, 4, 5],
                }
            )
            self.current_dataset = Dataset(
                df=frame,
                variables={
                    column: Variable(
                        name=column,
                        label=None,
                        measure=Measure.SCALE,
                        value_labels={},
                        missing_values=[],
                        dtype="int64",
                        origin_step_id="import",
                    )
                    for column in frame.columns
                },
            )
            self.steps = []
            self.variable_keys = set(frame.columns)

    controller = UiController(pipeline_factory=lambda path, options: PipelineWithDataset())
    controller.openDataFile(tmp_path / "survey.csv", ImportOptions(confirm_new_session=True))
    before_version = controller.pipeline_version

    assert controller.selectRecommendationAt(1) is True

    assert controller.recommendationTitle.startswith("신뢰도 분석")
    assert controller.preparedReliabilityItems in {"A1, A2, A3", "C1, C2, C3"}
    assert controller.pipeline_version == before_version
    assert controller.status == "ready"


def test_run_prepared_recommendation_applies_selection_before_worker_submit(tmp_path) -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    class Step:
        id = "reliability"
        step_type = "stats.reliability"
        title = "Reliability"
        params = {"items": ["old1", "old2", "old3"], "scale_name": "selected_scale"}

    class PipelineWithReliability:
        def __init__(self) -> None:
            frame = pd.DataFrame(
                {
                    "A1": [1, 2, 3, 4, 5],
                    "A2": [1, 2, 3, 4, 5],
                    "A3": [1, 2, 3, 4, 5],
                }
            )
            self.current_dataset = Dataset(
                df=frame,
                variables={
                    column: Variable(
                        name=column,
                        label=None,
                        measure=Measure.SCALE,
                        value_labels={},
                        missing_values=[],
                        dtype="int64",
                        origin_step_id="import",
                    )
                    for column in frame.columns
                },
            )
            self.steps = [Step()]
            self.variable_keys = set(frame.columns)
            self.analysis_objects = {}

        def edit_params(self, step_id, params):
            self.steps[0].params = dict(params)

        def recompute(self, dirty_from):
            self.analysis_objects = {}

    class FakeFuture:
        def add_done_callback(self, callback):
            self.callback = callback

    class FakeWorker:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            self.calls.append((run_id, pipeline_version, job))
            return FakeFuture()

    worker = FakeWorker()
    controller = UiController(
        pipeline_factory=lambda path, options: PipelineWithReliability(),
        worker=worker,
    )
    controller.openDataFile(tmp_path / "survey.csv", ImportOptions(confirm_new_session=True))

    result = controller.runPreparedRecommendation()

    assert result.ok is True
    assert controller.pipeline.steps[0].params["items"] == ["A1", "A2", "A3"]
    assert len(worker.calls) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py::test_open_data_file_populates_recommendation_without_running_worker tests\ui\test_controller.py::test_select_recommendation_updates_prepared_fields_without_running -q -p no:cacheprovider
```

Expected: FAIL because the controller does not expose recommendation properties or prepared recommendation execution yet.

- [ ] **Step 3: Add recommendation service to controller services**

In `src/modori/ui/controller_services.py`, import and add the service:

```python
from modori.ui.recommendations import RecommendationService
```

Add a field to `UiControllerServices`:

```python
    recommendation_service: RecommendationService
```

Add it in `build`:

```python
            recommendation_service=RecommendationService(),
```

- [ ] **Step 4: Add controller preparation properties and selection slot**

In `src/modori/ui/controller.py`, import the state:

```python
from modori.ui.recommendations import RecommendationCandidate, RecommendationState
```

Add instance fields in `__init__`:

```python
        self._recommendation_state = RecommendationState(
            candidates=[],
            default_candidate=None,
            selected_candidate=None,
            message_ko="",
        )
```

Add these properties and helpers:

```python
    @Property(str, notify=stateChanged)
    def recommendationTitle(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.title_ko

    @Property(str, notify=stateChanged)
    def recommendationLevel(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.level

    @Property(str, notify=stateChanged)
    def recommendationReason(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return self._recommendation_state.message_ko
        return candidate.reason_ko

    @Property(str, notify=stateChanged)
    def recommendationAlternativesText(self) -> str:
        return "\n".join(
            f"{index}. {candidate.title_ko} | {candidate.level}"
            for index, candidate in enumerate(self._recommendation_state.candidates)
        )

    @Property(int, notify=stateChanged)
    def recommendationCount(self) -> int:
        return len(self._recommendation_state.candidates)

    @Property(str, notify=stateChanged)
    def preparedReliabilityItems(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None or candidate.kind != "reliability":
            return ""
        return ", ".join(candidate.item_keys)

    @Property(str, notify=stateChanged)
    def preparedOutcomeKey(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.outcome_key

    @Property(str, notify=stateChanged)
    def preparedGroupKey(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        return "" if candidate is None else candidate.group_key

    @Property(str, notify=stateChanged)
    def preparedPredictorKeys(self) -> str:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return ""
        return ", ".join(candidate.predictor_keys)

    @Slot(int, result=bool)
    def selectRecommendationAt(self, index: int) -> bool:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            self._last_error = "추천 후보를 찾을 수 없습니다."
            self._last_message = ""
            self.stateChanged.emit()
            return False
        selected = self._recommendation_state.candidates[index]
        self._recommendation_state = RecommendationState(
            candidates=self._recommendation_state.candidates,
            default_candidate=self._recommendation_state.default_candidate,
            selected_candidate=selected,
            message_ko=self._recommendation_state.message_ko,
        )
        self._last_error = ""
        self._last_message = "추천 후보를 선택했습니다."
        self.stateChanged.emit()
        return True

    @Slot(int, result=str)
    def recommendationCandidateTitleAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].title_ko

    @Slot(int, result=str)
    def recommendationCandidateLevelAt(self, index: int) -> str:
        if index < 0 or index >= len(self._recommendation_state.candidates):
            return ""
        return self._recommendation_state.candidates[index].level

    def applySelectedRecommendation(self) -> CommandResult:
        candidate = self._recommendation_state.selected_candidate
        if candidate is None:
            return self._command_error("실행할 추천 분석이 없습니다.", "no_recommendation")
        if candidate.kind == "reliability":
            return self.configureReliabilitySelection(", ".join(candidate.item_keys))
        if candidate.kind == "comparison":
            return self.configureComparisonSelection(candidate.outcome_key, candidate.group_key)
        if candidate.kind == "regression":
            return self.configureRegressionSelection(
                candidate.outcome_key,
                ", ".join(candidate.predictor_keys),
            )
        return self._command_error("지원하지 않는 추천 분석입니다.", "invalid_recommendation")

    @Slot(result=bool)
    def runPreparedRecommendationNow(self) -> bool:
        return self.runPreparedRecommendation().ok

    def runPreparedRecommendation(self) -> CommandResult:
        applied = self.applySelectedRecommendation()
        if not applied.ok:
            return applied
        return self.rerun()

    def _refresh_recommendations(self) -> None:
        self._recommendation_state = self._services.recommendation_service.recommend(
            self._services.pipeline_ops.current_dataset()
        )

    def _clear_recommendations(self) -> None:
        self._recommendation_state = RecommendationState(
            candidates=[],
            default_candidate=None,
            selected_candidate=None,
            message_ko="",
        )
```

Call `_refresh_recommendations()` in `openDataFile` after `_services.replace_pipeline(load_result.pipeline)` and before `stateChanged.emit()`. Call `_clear_recommendations()` when import fails and when no pending import exists.

- [ ] **Step 5: Run controller tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/modori/ui/controller.py src/modori/ui/controller_services.py tests/ui/test_controller.py
git commit -m "feat: expose analysis preparation state"
```

### Task 5: Render the Preparation Panel and Keep Selection Non-Executing

**Files:**
- Modify: `src/modori/ui/strings.py`
- Modify: `src/modori/ui/qml/components/GuideRail.qml`
- Modify: `src/modori/ui/qml/components/PipelineRail.qml`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_qml_string_catalog.py`

- [ ] **Step 1: Write QML behavior tests**

Add this test to `tests/ui/test_guided_standard_variable_selection_flow.py`:

```python
def test_guide_rail_shows_recommendations_without_auto_running() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(encoding="utf-8")

    assert "uiController.recommendationTitle" in guide
    assert "uiController.recommendationLevel" in guide
    assert "uiController.recommendationReason" in guide
    assert "uiController.recommendationAlternativesText" in guide
    assert "uiController.recommendationCount" in guide
    assert "uiController.recommendationCandidateTitleAt(index)" in guide
    assert "uiController.recommendationCandidateLevelAt(index)" in guide
    assert "uiController.selectRecommendationAt" in guide
    assert "guide.other_recommendations" in guide
    assert "guide.manual_selection" in guide

    run_button_start = guide.index('text: appBootstrap.text("guide.run_selected")')
    run_button = guide[run_button_start : guide.index("TextField", run_button_start)]
    assert "uiController.runPreparedRecommendationNow()" in run_button

    selection_block_start = guide.index("uiController.selectRecommendationAt")
    selection_block = guide[selection_block_start : guide.index('text: appBootstrap.text("guide.run_selected")')]
    assert "uiController.rerunNow()" not in selection_block
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_guided_standard_variable_selection_flow.py::test_guide_rail_shows_recommendations_without_auto_running -q -p no:cacheprovider
```

Expected: FAIL because the current `GuideRail.qml` does not show recommendation state and still has a combined configure-and-run button.

- [ ] **Step 3: Add string catalog entries**

Add these keys to `UI_STRINGS_KO` in `src/modori/ui/strings.py`:

```python
    "guide.default_recommendation": "기본 추천",
    "guide.level": "수준",
    "guide.reason": "이유",
    "guide.run_selected": "분석 실행",
    "guide.other_recommendations": "다른 추천 보기",
    "guide.manual_selection": "직접 선택",
    "guide.no_recommendation": "추천 없음",
```

- [ ] **Step 4: Replace the combined guided run button**

In `src/modori/ui/qml/components/GuideRail.qml`, replace the current `guide.run_recommended` button with this sequence:

```qml
        Label {
            text: appBootstrap.text("guide.default_recommendation")
            font.bold: true
            color: "#0B4A43"
            visible: uiController.recommendationTitle.length > 0
            Layout.fillWidth: true
        }

        Label {
            text: uiController.recommendationTitle.length > 0
                ? uiController.recommendationTitle
                : appBootstrap.text("guide.no_recommendation")
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("guide.level") + ": " + uiController.recommendationLevel
            visible: uiController.recommendationLevel.length > 0
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            text: appBootstrap.text("guide.reason") + ": " + uiController.recommendationReason
            visible: uiController.recommendationReason.length > 0
            color: "#26352F"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Button {
            text: appBootstrap.text("guide.other_recommendations")
            Accessible.name: appBootstrap.text("guide.other_recommendations")
            enabled: uiController.recommendationAlternativesText.length > 0
            Layout.fillWidth: true
            onClicked: alternativesList.visible = !alternativesList.visible
        }

        ColumnLayout {
            id: alternativesList
            visible: false
            Layout.fillWidth: true

            Repeater {
                model: uiController.recommendationCount

                Button {
                    text: uiController.recommendationCandidateTitleAt(index) + " · " + uiController.recommendationCandidateLevelAt(index)
                    Accessible.name: text
                    Layout.fillWidth: true
                    onClicked: uiController.selectRecommendationAt(index)
                }
            }
        }

        Button {
            text: appBootstrap.text("guide.manual_selection")
            Accessible.name: appBootstrap.text("guide.manual_selection")
            enabled: root.canEditSelection
            Layout.fillWidth: true
            onClicked: {
                root.selectedIntent = "reliability"
            }
        }

        Button {
            text: appBootstrap.text("guide.run_selected")
            Accessible.name: appBootstrap.text("guide.run_selected")
            enabled: root.canCommitSelection || uiController.recommendationTitle.length > 0
            Layout.fillWidth: true
            onClicked: {
                if (root.canCommitSelection) {
                    if (root.commitSelectedIntent()) {
                        uiController.rerunNow()
                    }
                } else {
                    uiController.runPreparedRecommendationNow()
                }
            }
        }
```

Keep the existing manual `TextField` controls and the existing `guide.apply_selection` button so direct variable selection remains possible.

- [ ] **Step 5: Keep standard mode explicit**

In `src/modori/ui/qml/components/PipelineRail.qml`, leave the existing `pipeline.rerun` button as the only standard-mode execution path. Do not add recommendation selection to `PipelineRail.qml` in this task.

- [ ] **Step 6: Run QML string and guided-flow tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_qml_string_catalog.py tests\ui\test_guided_standard_variable_selection_flow.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- src/modori/ui/strings.py src/modori/ui/qml/components/GuideRail.qml src/modori/ui/qml/components/PipelineRail.qml tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_qml_string_catalog.py
git commit -m "feat: render novice preparation panel"
```

### Task 6: Validate Runs Immediately Before Worker Submission

**Files:**
- Create: `src/modori/ui/run_validation.py`
- Modify: `src/modori/ui/controller_services.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `tests/ui/test_controller.py`

- [ ] **Step 1: Write tests that worker submission is blocked**

Add this test to `tests/ui/test_controller.py`:

```python
def test_rerun_blocks_unknown_columns_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class BadStep:
        id = "reliability"
        step_type = "stats.reliability"
        title = "Reliability"
        params = {"items": ["q1", "q2", "missing"]}

    class BadPipeline:
        steps = [BadStep()]
        variable_keys = {"q1", "q2"}
        current_dataset = None

        def recompute(self, dirty_from):
            raise AssertionError("recompute must not run")

    class FakeWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted")

    controller = UiController(pipeline=BadPipeline(), worker=FakeWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "알 수 없는 변수" in controller.lastError
    assert controller.status == "ready"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py::test_rerun_blocks_unknown_columns_before_worker_submit -q -p no:cacheprovider
```

Expected: FAIL because `rerun()` currently submits the worker directly.

- [ ] **Step 3: Implement run validation service**

Create `src/modori/ui/run_validation.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunValidationResult:
    ok: bool
    message_ko: str = ""
    error_code: str | None = None


class RunConfigurationValidator:
    def validate(self, pipeline_ops: object) -> RunValidationResult:
        variable_keys = pipeline_ops.variable_keys()
        if variable_keys is None:
            return RunValidationResult(ok=True)
        for step in pipeline_ops.steps():
            step_type = self._step_type(step)
            params = self._step_params(step)
            if step_type == "stats.reliability":
                result = self._validate_reliability(params, variable_keys)
            elif step_type == "stats.compare_groups":
                result = self._validate_comparison(params, variable_keys)
            elif step_type == "stats.regression_ols":
                result = self._validate_regression(params, variable_keys)
            else:
                result = RunValidationResult(ok=True)
            if not result.ok:
                return result
        return RunValidationResult(ok=True)

    @staticmethod
    def _validate_reliability(
        params: Mapping[str, Any],
        variable_keys: set[str],
    ) -> RunValidationResult:
        items = params.get("items")
        if not isinstance(items, list) or any(not isinstance(item, str) or not item for item in items):
            return RunValidationResult(False, "신뢰도 분석에는 문항 변수가 필요합니다.", "invalid_run_configuration")
        if len(items) < 3:
            return RunValidationResult(False, "신뢰도 분석에는 세 개 이상의 문항 변수가 필요합니다.", "invalid_run_configuration")
        return _require_known(items, variable_keys)

    @staticmethod
    def _validate_comparison(
        params: Mapping[str, Any],
        variable_keys: set[str],
    ) -> RunValidationResult:
        outcome = params.get("dv")
        group = params.get("group")
        if not isinstance(outcome, str) or not outcome or not isinstance(group, str) or not group:
            return RunValidationResult(False, "집단 비교에는 결과 변수와 집단 변수가 필요합니다.", "invalid_run_configuration")
        if outcome == group:
            return RunValidationResult(False, "결과 변수와 집단 변수는 달라야 합니다.", "invalid_run_configuration")
        return _require_known([outcome, group], variable_keys)

    @staticmethod
    def _validate_regression(
        params: Mapping[str, Any],
        variable_keys: set[str],
    ) -> RunValidationResult:
        outcome = params.get("dv")
        predictors = params.get("predictors")
        if not isinstance(outcome, str) or not outcome:
            return RunValidationResult(False, "회귀분석에는 종속 변수가 필요합니다.", "invalid_run_configuration")
        if not isinstance(predictors, list) or any(not isinstance(item, str) or not item for item in predictors):
            return RunValidationResult(False, "회귀분석에는 예측 변수가 필요합니다.", "invalid_run_configuration")
        if outcome in predictors:
            return RunValidationResult(False, "종속 변수는 예측 변수에 포함될 수 없습니다.", "invalid_run_configuration")
        return _require_known([outcome, *predictors], variable_keys)

    @staticmethod
    def _step_type(step: object) -> str:
        if isinstance(step, Mapping):
            return str(step.get("step_type", ""))
        return str(getattr(step, "step_type", ""))

    @staticmethod
    def _step_params(step: object) -> Mapping[str, Any]:
        params = step.get("params", {}) if isinstance(step, Mapping) else getattr(step, "params", {})
        return params if isinstance(params, Mapping) else {}


def _require_known(values: list[str], variable_keys: set[str]) -> RunValidationResult:
    missing = sorted(set(values) - variable_keys)
    if missing:
        return RunValidationResult(
            ok=False,
            message_ko=f"알 수 없는 변수입니다: {', '.join(missing)}",
            error_code="invalid_run_configuration",
        )
    return RunValidationResult(ok=True)
```

- [ ] **Step 4: Wire validation into services and `rerun()`**

In `src/modori/ui/controller_services.py`, import and add:

```python
from modori.ui.run_validation import RunConfigurationValidator
```

Add a field:

```python
    run_validator: RunConfigurationValidator
```

Add it in `build`:

```python
            run_validator=RunConfigurationValidator(),
```

In `src/modori/ui/controller.py`, add this check at the start of `rerun()` after the `self.pipeline is None` guard and before `_run_tracker.submit`:

```python
        validation = self._services.run_validator.validate(self._services.pipeline_ops)
        if not validation.ok:
            return self._command_error(
                validation.message_ko,
                validation.error_code or "invalid_run_configuration",
            )
```

- [ ] **Step 5: Run controller and worker tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py tests\ui\test_worker.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add -- src/modori/ui/run_validation.py src/modori/ui/controller_services.py src/modori/ui/controller.py tests/ui/test_controller.py
git commit -m "feat: validate runs before engine worker"
```

### Task 7: Validate Result Payloads Without Next-Analysis Recommendations

**Files:**
- Create: `src/modori/ui/result_validation.py`
- Modify: `src/modori/ui/controller_services.py`
- Modify: `src/modori/ui/controller.py`
- Modify: `tests/ui/test_controller.py`

- [ ] **Step 1: Update the existing successful payload test**

In `tests/ui/test_controller.py`, update `test_controller_applies_latest_worker_result` so the successful payload is a valid display result:

```python
def test_controller_applies_latest_worker_result() -> None:
    from modori.ui.contracts import DisplayResult
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())
    display = DisplayResult(
        result_id="reliability:scale",
        kind="reliability",
        title_ko="신뢰도",
        title_en="Reliability",
        prose_ko="결과 문장",
        prose_en="Result sentence",
    )

    applied = controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[display],
        )
    )

    assert applied is True
    assert controller.resultsModel == [display]
    assert controller.stale is False
```

- [ ] **Step 2: Write result-display validation tests**

Add this test to `tests/ui/test_controller.py`:

```python
def test_worker_success_with_empty_payload_becomes_result_display_error() -> None:
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())

    applied = controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=[],
        )
    )

    assert applied is True
    assert controller.status == "error"
    assert controller.lastError == "결과를 표시하지 못했습니다."
    assert controller.resultsModel == []
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py::test_worker_success_with_empty_payload_becomes_result_display_error -q -p no:cacheprovider
```

Expected: FAIL because empty successful payload currently becomes an empty result display.

- [ ] **Step 4: Implement result payload validator**

Create `src/modori/ui/result_validation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultPayloadValidation:
    ok: bool
    message_ko: str = ""
    error_code: str | None = None


class ResultPayloadValidator:
    def validate(self, payload: Any) -> ResultPayloadValidation:
        if not isinstance(payload, list) or not payload:
            return ResultPayloadValidation(
                ok=False,
                message_ko="결과를 표시하지 못했습니다.",
                error_code="result_display_error",
            )
        for result in payload:
            if not getattr(result, "result_id", ""):
                return ResultPayloadValidation(
                    ok=False,
                    message_ko="결과를 표시하지 못했습니다.",
                    error_code="result_display_error",
                )
            if not getattr(result, "title_ko", "") and not getattr(result, "prose_ko", ""):
                return ResultPayloadValidation(
                    ok=False,
                    message_ko="결과를 표시하지 못했습니다.",
                    error_code="result_display_error",
                )
        return ResultPayloadValidation(ok=True)
```

- [ ] **Step 5: Wire result validation into services and worker result application**

In `src/modori/ui/controller_services.py`, import and add:

```python
from modori.ui.result_validation import ResultPayloadValidator
```

Add a field:

```python
    result_payload_validator: ResultPayloadValidator
```

Add it in `build`:

```python
            result_payload_validator=ResultPayloadValidator(),
```

In `src/modori/ui/controller.py`, add this block in `apply_worker_result` after the `if not result.ok` block and before `_refresh_dataset_models()`:

```python
        validation = self._services.result_payload_validator.validate(result.payload)
        if not validation.ok:
            self._pipeline_state.mark_error()
            self._last_error = validation.message_ko
            self._last_message = ""
            self.stateChanged.emit()
            return True
```

- [ ] **Step 6: Run result-state tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_controller.py tests\ui\test_result_state.py tests\ui\test_result_binding.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add -- src/modori/ui/result_validation.py src/modori/ui/controller_services.py src/modori/ui/controller.py tests/ui/test_controller.py
git commit -m "feat: validate result display payloads"
```

### Task 8: End-to-End Guard Tests and Clean VM Criteria

**Files:**
- Modify: `tests/ui/test_import_dialog_flow.py`
- Modify: `tests/ui/test_guided_standard_variable_selection_flow.py`
- Modify: `tests/ui/test_smoke_qml.py`

- [ ] **Step 1: Add static safety tests for no hidden auto-run**

Add this test to `tests/ui/test_smoke_qml.py`:

```python
def test_no_hidden_rerun_calls_in_import_or_recommendation_selection() -> None:
    main = qml_text("Main.qml")
    guide = qml_text("components/GuideRail.qml")

    import_section = main[main.index("ImportDialog") : main.index("ReportExportDialog")]
    recommendation_selection = guide[
        guide.index("uiController.selectRecommendationAt") : guide.index('text: appBootstrap.text("guide.run_selected")')
    ]

    assert "uiController.rerunNow()" not in import_section
    assert "uiController.rerunNow()" not in recommendation_selection
```

- [ ] **Step 2: Run the focused UI safety suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ui\test_import_dialog_flow.py tests\ui\test_guided_standard_variable_selection_flow.py tests\ui\test_smoke_qml.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 3: Run the full focused regression suite for this feature**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_data_prep_steps.py tests\ui\test_importing_service.py tests\test_table_io.py tests\ui\test_recommendations.py tests\ui\test_controller.py tests\ui\test_guided_standard_variable_selection_flow.py tests\ui\test_import_dialog_flow.py tests\ui\test_qml_string_catalog.py tests\ui\test_smoke_qml.py tests\ui\test_result_binding.py tests\ui\test_result_state.py tests\ui\test_worker.py -q -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 4: Package and clean-VM verification**

Run the established packaging and VM recovery commands from the release verification handoff:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_package_windows_script.py tests\test_package_engine_smoke_script.py tests\test_clean_vm_payload_script.py -q -p no:cacheprovider
```

Expected: PASS.

Then rebuild the package, create or attach the next explicitly named payload, and verify in `Modori-CleanWin-QA-Direct`:

```text
Run-Engine-Smoke-XLSX.bat: exit code 0 and JSON ok true
Run-Modori.bat: app opens
CSV/XLSX/SAV visible import: preview dialog appears
After import confirmation: no automatic analysis starts
Preparation panel: one default recommendation appears when safe
Alternative recommendation selection: fields and reason update without analysis
Manual selection: still possible
Explicit analysis run: starts only after clicking 분석 실행
Invalid selection: blocked before engine worker with Korean validation text
Completed calculation: result displays or result-display error appears without next-analysis recommendation
```

- [ ] **Step 5: Commit final guard tests**

```powershell
git add -- tests/ui/test_import_dialog_flow.py tests/ui/test_guided_standard_variable_selection_flow.py tests/ui/test_smoke_qml.py
git commit -m "test: lock novice analysis safety flow"
```
