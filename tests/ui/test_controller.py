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


def valid_display_result():
    from modori.ui.contracts import DisplayResult

    return DisplayResult(
        result_id="fresh",
        kind="reliability",
        title_ko="신뢰도 분석",
        title_en="Reliability analysis",
        prose_ko="결과 요약",
        prose_en="Result summary",
    )


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
    display = valid_display_result()

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


def test_worker_success_with_malformed_table_payload_becomes_result_display_error() -> None:
    from dataclasses import replace

    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())
    display = replace(
        valid_display_result(),
        tables=[object()],  # type: ignore[list-item]
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
    assert controller.status == "error"
    assert controller.lastError == "결과를 표시하지 못했습니다."
    assert controller.resultsModel == []


def test_worker_success_with_malformed_notes_payload_becomes_result_display_error() -> None:
    from dataclasses import replace

    from modori.ui.controller import UiController
    from modori.ui.worker import EngineJobResult

    controller = UiController(pipeline=FakePipeline())
    display = replace(
        valid_display_result(),
        notes=[object()],  # type: ignore[list-item]
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
    assert controller.status == "error"
    assert controller.lastError == "결과를 표시하지 못했습니다."
    assert controller.resultsModel == []


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
    assert controller.recommendationTitle == ""
    assert controller.recommendationReason == ""
    assert controller.recommendationCount > 0
    assert controller.recommendationCandidateTitleAt(0)
    assert not hasattr(controller, "recommendationLevel")
    assert not hasattr(controller, "recommendationAlternativesText")
    assert worker.calls == []


def test_default_open_data_file_imports_fixture_for_recommendations_without_worker() -> None:
    from pathlib import Path

    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    class RaisingWorker:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            self.calls.append((run_id, pipeline_version, job))
            raise AssertionError("worker must not run during import")

    worker = RaisingWorker()
    controller = UiController(worker=worker)

    result = controller.openDataFile(
        Path("tests/fixtures/psych_bfi.csv"),
        ImportOptions(confirm_new_session=True),
    )

    assert result.ok is True
    assert controller.pipeline.current_dataset.df.shape[0] > 0
    assert controller.pipeline.current_dataset.df.shape[1] > 0
    assert controller.recommendationCount > 0
    assert controller.recommendationTitle == ""
    assert worker.calls == []


def test_export_report_with_selections_passes_expanded_family_options(tmp_path) -> None:
    from modori.ui.contracts import ReportExportOptions
    from modori.ui.controller import UiController

    seen: list[ReportExportOptions] = []
    output_path = tmp_path / "report.docx"
    output_path.write_bytes(b"docx")

    def exporter(pipeline, options):
        seen.append(options)
        return output_path

    controller = UiController(
        pipeline=ImportablePipeline(["import", "report"]),
        report_exporter=exporter,
    )

    assert (
        controller.exportReportWithSelections(
            "en",
            False,
            True,
            False,
            True,
            False,
            True,
            True,
            False,
        )
        is True
    )

    assert seen == [
        ReportExportOptions(
            language="en",
            include_descriptives=False,
            include_reliability=True,
            include_comparison=False,
            include_association=True,
            include_group_models=False,
            include_dimension_reduction=True,
            include_regression=True,
            include_figures=False,
        )
    ]


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
    assert controller.prepareSelectedRecommendationNow() is True

    assert controller.recommendationTitle.startswith("신뢰도 분석")
    assert ", ".join(controller.preparedRecommendationField("item_keys")) in {
        "A1, A2, A3",
        "C1, C2, C3",
    }
    assert controller.pipeline_version == before_version
    assert controller.status == "ready"


def test_confirmed_manual_configuration_applies_before_worker_submit(tmp_path) -> None:
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
        def __init__(self, pipelines) -> None:
            self.pipelines = pipelines
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            pipeline = self.pipelines[0]
            assert pipeline.steps[0].params["items"] == ["A1", "A2", "A3"]
            self.calls.append((run_id, pipeline_version, job))
            return FakeFuture()

    pipelines = []

    def factory(path, options):
        pipeline = PipelineWithReliability()
        pipelines.append(pipeline)
        return pipeline

    worker = FakeWorker(pipelines)
    controller = UiController(
        pipeline_factory=factory,
        worker=worker,
    )
    controller.openDataFile(tmp_path / "survey.csv", ImportOptions(confirm_new_session=True))
    reliability_index = next(
        index
        for index, candidate in enumerate(controller._recommendation_state.candidates)
        if candidate.kind == "reliability"
    )
    assert controller.selectRecommendationAt(reliability_index) is True
    assert controller.prepareSelectedRecommendationNow() is True
    items = ", ".join(controller.preparedRecommendationField("item_keys"))
    configured = controller.configureReliabilitySelection(items)
    assert configured.ok is True

    result = controller.rerun()

    assert result.ok is True
    assert controller.pipeline.steps[0].params["items"] == ["A1", "A2", "A3"]
    assert len(worker.calls) == 1


def test_advanced_recommendation_candidates_apply_to_pipeline_steps() -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.controller import UiController

    class PipelineWithDataset:
        def __init__(self, frame: pd.DataFrame) -> None:
            self.current_dataset = Dataset(
                df=frame,
                variables={
                    column: Variable(
                        name=column,
                        label=None,
                        measure=Measure.SCALE,
                        value_labels={},
                        missing_values=[],
                        dtype=str(frame[column].dtype),
                        origin_step_id="import",
                    )
                    for column in frame.columns
                },
            )
            self.steps = []
            self.variable_keys = set(frame.columns)
            self.edits: list[tuple[str, dict[str, object]]] = []

        def edit_params(self, step_id, params):
            self.edits.append((step_id, dict(params)))

    cases = [
        (
            "repeated_measures_anova",
            pd.DataFrame(
                {
                    "time1": [1, 2, 3, 4, 5, 6],
                    "time2": [2, 3, 4, 5, 6, 7],
                    "time3": [3, 4, 5, 6, 7, 8],
                    "score": [4, 5, 6, 7, 8, 9],
                }
            ),
            "repeated_measures_anova",
            {"measures": ["time1", "time2", "time3"]},
        ),
        (
            "friedman",
            pd.DataFrame(
                {
                    "time1": [1, 2, 3, 4, 5, 6],
                    "time2": [2, 3, 4, 5, 6, 7],
                    "time3": [3, 4, 5, 6, 7, 8],
                    "score": [4, 5, 6, 7, 8, 9],
                }
            ),
            "friedman",
            {"measures": ["time1", "time2", "time3"]},
        ),
        (
            "mediation",
            pd.DataFrame(
                {
                    "x": [1, 2, 3, 4, 5, 6, 7, 8],
                    "m": [2, 3, 4, 4, 5, 6, 7, 8],
                    "y": [3, 4, 5, 6, 7, 8, 9, 10],
                }
            ),
            "mediation",
            {"x": "x", "mediator": "m", "y": "y"},
        ),
        (
            "moderated_mediation",
            pd.DataFrame(
                {
                    "x": [1, 2, 3, 4, 5, 6, 7, 8],
                    "m": [2, 3, 4, 4, 5, 6, 7, 8],
                    "w": [1, 1, 2, 2, 3, 3, 4, 4],
                    "y": [3, 4, 5, 6, 7, 8, 9, 10],
                }
            ),
            "moderated_mediation",
            {"model": 7, "x": "x", "mediator": "m", "moderator": "w", "y": "y"},
        ),
    ]

    for kind, frame, expected_step_id, expected_params in cases:
        pipeline = PipelineWithDataset(frame)
        controller = UiController(pipeline=pipeline)
        controller._refresh_recommendations()
        index = next(
            index
            for index, candidate in enumerate(controller._recommendation_state.candidates)
            if candidate.kind == kind
        )

        assert controller.selectRecommendationAt(index) is True
        assert controller.prepareSelectedRecommendationNow() is True
        if kind == "repeated_measures_anova":
            result = controller.configureRepeatedMeasuresAnovaSelection(
                ", ".join(controller.preparedRecommendationField("variable_keys"))
            )
        elif kind == "friedman":
            result = controller.configureFriedmanSelection(
                ", ".join(controller.preparedRecommendationField("variable_keys"))
            )
        elif kind == "mediation":
            result = controller.configureMediationSelection(
                controller.preparedRecommendationField("x_key"),
                controller.preparedRecommendationField("mediator_key"),
                controller.preparedRecommendationField("y_key"),
            )
        else:
            result = controller.configureModeratedMediationSelection(
                controller.preparedRecommendationField("model"),
                controller.preparedRecommendationField("x_key"),
                controller.preparedRecommendationField("mediator_key"),
                controller.preparedRecommendationField("moderator_key"),
                controller.preparedRecommendationField("y_key"),
            )

        assert result.ok is True
        assert result.changed_step_ids == [expected_step_id]
        assert pipeline.edits
        edited_step_id, params = pipeline.edits[-1]
        assert edited_step_id == expected_step_id
        for key, value in expected_params.items():
            assert params[key] == value


def test_unselected_recommendation_cannot_prepare_or_submit_work() -> None:
    from pathlib import Path

    from modori.ui.contracts import ImportOptions
    from modori.ui.controller import UiController

    class InspectingWorker:
        def __init__(self) -> None:
            self.calls = []

        def submit(self, *, run_id, pipeline_version, job):
            self.calls.append((run_id, pipeline_version, job))
            raise AssertionError("an unselected candidate must not submit work")

    controller = UiController()
    worker = InspectingWorker()
    controller._worker = worker
    opened = controller.openDataFile(
        Path("tests/fixtures/psych_bfi.csv"),
        ImportOptions(confirm_new_session=True),
    )
    assert opened.ok is True
    before_step_ids = [step.id for step in controller.pipeline.steps]

    prepared = controller.prepareSelectedRecommendationNow()

    assert prepared is False
    assert [step.id for step in controller.pipeline.steps] == before_step_ids
    assert worker.calls == []


def test_rerun_blocks_unknown_columns_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "reliability"
        step_type = "stats.reliability"
        params = {"items": ["q1", "q2", "missing"], "scale_name": "bad_scale"}

    class PipelineWithBadReliability:
        steps = [Step()]
        variable_keys = {"q1", "q2"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted for invalid run configuration")

    controller = UiController(pipeline=PipelineWithBadReliability(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "알 수 없는 변수" in controller.lastError
    assert controller.status == "ready"


def test_rerun_blocks_blank_reliability_item_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "reliability"
        step_type = "stats.reliability"
        params = {"items": ["q1", "q2", "q3", ""], "scale_name": "bad_scale"}

    class PipelineWithBlankReliabilityItem:
        steps = [Step()]
        variable_keys = {"q1", "q2", "q3"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted for invalid run configuration")

    controller = UiController(pipeline=PipelineWithBlankReliabilityItem(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "문자열" in controller.lastError
    assert controller.status == "ready"


def test_rerun_blocks_duplicate_reliability_items_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "reliability"
        step_type = "stats.reliability"
        params = {"items": ["q1", "q1", "q2"], "scale_name": "bad_scale"}

    class PipelineWithDuplicateReliabilityItem:
        steps = [Step()]
        variable_keys = {"q1", "q2"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted for invalid run configuration")

    controller = UiController(pipeline=PipelineWithDuplicateReliabilityItem(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "중복" in controller.lastError
    assert controller.status == "ready"


def test_rerun_blocks_blank_regression_predictor_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "regression"
        step_type = "stats.regression_ols"
        params = {"dv": "score", "predictors": ["q1", ""], "regression_policy": {"preset": "modern"}}

    class PipelineWithBlankRegressionPredictor:
        steps = [Step()]
        variable_keys = {"score", "q1"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted for invalid run configuration")

    controller = UiController(pipeline=PipelineWithBlankRegressionPredictor(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "문자열" in controller.lastError
    assert controller.status == "ready"


def test_rerun_blocks_import_only_pipeline_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "import"
        step_type = "import.table"
        params = {"path": "survey.csv"}

    class ImportOnlyPipeline:
        steps = [Step()]
        variable_keys = {"q1", "q2", "q3"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted without an analysis step")

    controller = UiController(pipeline=ImportOnlyPipeline(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "실행할 분석" in controller.lastError
    assert controller.status == "ready"


def test_rerun_blocks_duplicate_regression_predictors_before_worker_submit() -> None:
    from modori.ui.controller import UiController

    class Step:
        id = "regression"
        step_type = "stats.regression_ols"
        params = {
            "dv": "score",
            "predictors": ["q1", "q1"],
            "regression_policy": {"preset": "modern"},
        }

    class PipelineWithDuplicateRegressionPredictor:
        steps = [Step()]
        variable_keys = {"score", "q1"}

    class RaisingWorker:
        def submit(self, *, run_id, pipeline_version, job):
            raise AssertionError("worker must not be submitted for invalid run configuration")

    controller = UiController(pipeline=PipelineWithDuplicateRegressionPredictor(), worker=RaisingWorker())

    result = controller.rerun()

    assert result.ok is False
    assert result.error_code == "invalid_run_configuration"
    assert "중복" in controller.lastError
    assert controller.status == "ready"
