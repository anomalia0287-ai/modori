class FakePipeline:
    def __init__(self) -> None:
        self.steps = [{"id": "reliability"}]
        self.edits: list[tuple[str, object]] = []
        self.variable_keys = {"q1", "q2", "score", "group"}

    def edit_params(self, step_id: str, patch: object) -> None:
        self.edits.append((step_id, patch))


class ImportablePipeline(FakePipeline):
    def __init__(self, step_ids: list[str]) -> None:
        super().__init__()
        self.steps = [{"id": step_id} for step_id in step_ids]


def test_mode_switch_does_not_change_steps_or_pipeline_version() -> None:
    from modori.ui.controller import UiController

    pipeline = FakePipeline()
    controller = UiController(pipeline=pipeline)
    before_steps = list(pipeline.steps)
    before_version = controller.pipeline_version

    result = controller.setMode("standard")

    assert result.ok is True
    assert controller.mode == "standard"
    assert pipeline.steps == before_steps
    assert controller.pipeline_version == before_version
    assert pipeline.edits == []


def test_invalid_patch_does_not_mutate_pipeline() -> None:
    from modori.ui.controller import UiController

    pipeline = FakePipeline()
    controller = UiController(pipeline=pipeline)

    result = controller.updateStep(
        "reliability",
        {"kind": "reliability", "item_keys": [], "language": "ko"},
    )

    assert result.ok is False
    assert result.error_code == "invalid_step_patch"
    assert pipeline.edits == []
    assert controller.pipeline_version == 0


def test_valid_patch_commits_and_marks_results_stale() -> None:
    from modori.ui.controller import UiController

    pipeline = FakePipeline()
    controller = UiController(pipeline=pipeline)

    result = controller.updateStep(
        "reliability",
        {"kind": "reliability", "item_keys": ["q1", "q2"], "language": "ko"},
    )

    assert result.ok is True
    assert result.changed_step_ids == ["reliability"]
    assert controller.pipeline_version == 1
    assert controller.stale is True
    assert len(pipeline.edits) == 1


def test_controller_discards_stale_worker_result() -> None:
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())

    applied = controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=1,
            ok=True,
            payload={"result": "old"},
        )
    )

    assert applied is False
    assert controller.resultsModel == []


def test_controller_applies_latest_worker_result() -> None:
    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())

    applied = controller.apply_worker_result(
        EngineJobResult(
            run_id=0,
            pipeline_version=0,
            ok=True,
            payload=["fresh"],
        )
    )

    assert applied is True
    assert controller.resultsModel == ["fresh"]
    assert controller.stale is False


def test_open_data_file_requires_confirmation_before_new_session(tmp_path) -> None:
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    previous = ImportablePipeline(["import", "reliability", "report"])
    controller = UiController(pipeline=previous, pipeline_factory=lambda path, options: ImportablePipeline(["import"]))

    result = controller.openDataFile(tmp_path / "data.csv", ImportOptions(confirm_new_session=False))

    assert result.ok is False
    assert result.error_code == "confirmation_required"
    assert controller.pipeline is previous
    assert controller.pipeline_version == 0


def test_open_data_file_new_session_replaces_pipeline_after_confirmation(tmp_path) -> None:
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    created: list[object] = []

    def factory(path, options):
        pipeline = ImportablePipeline(["import"])
        created.append((path, options, pipeline))
        return pipeline

    controller = UiController(
        pipeline=ImportablePipeline(["import", "reliability", "report"]),
        pipeline_factory=factory,
    )

    result = controller.openDataFile(tmp_path / "data.csv", ImportOptions(confirm_new_session=True))

    assert result.ok is True
    assert result.changed_step_ids == ["import"]
    assert controller.pipeline is created[0][2]
    assert controller.stepsModel == [{"id": "import"}]
    assert controller.pipeline_version == 1
    assert controller.stale is True


def test_open_data_file_failure_leaves_previous_pipeline_untouched(tmp_path) -> None:
    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    previous = ImportablePipeline(["import", "report"])

    def factory(path, options):
        raise ValueError("cannot parse")

    controller = UiController(pipeline=previous, pipeline_factory=factory)

    result = controller.openDataFile(tmp_path / "bad.csv", ImportOptions(confirm_new_session=True))

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert controller.pipeline is previous
    assert controller.pipeline_version == 0


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
