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
