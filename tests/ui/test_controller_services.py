from __future__ import annotations

from pathlib import Path

from modori.ui.controller_services import UiControllerServices
from modori.ui.contracts import ImportOptions


class FakePipeline:
    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.steps = []


def test_controller_services_builds_pipeline_bound_services() -> None:
    pipeline = FakePipeline("first")
    services = UiControllerServices.build(
        pipeline=pipeline,
        pipeline_factory=lambda path, options: FakePipeline("loaded"),
        mode_provider=lambda: "guided",
        library=None,
    )

    assert services.pipeline_ops.current_dataset() is None
    assert services.analysis_editor is not None
    assert services.metadata_editor is not None
    assert services.import_flow.preview_text == ""


def test_controller_services_replaces_pipeline_bound_editors() -> None:
    first = FakePipeline("first")
    second = FakePipeline("second")
    services = UiControllerServices.build(
        pipeline=first,
        pipeline_factory=lambda path, options: second,
        mode_provider=lambda: "guided",
        library=None,
    )
    old_ops = services.pipeline_ops
    old_analysis = services.analysis_editor
    old_metadata = services.metadata_editor

    services.replace_pipeline(second)

    assert services.pipeline_ops is not old_ops
    assert services.analysis_editor is not old_analysis
    assert services.metadata_editor is not old_metadata
    assert services.pipeline_ops.steps() == []


def test_controller_services_default_loader_uses_injected_factory(tmp_path) -> None:
    loaded = FakePipeline("loaded")
    calls = []

    def factory(path: Path, options: ImportOptions) -> object:
        calls.append((path, options))
        return loaded

    services = UiControllerServices.build(
        pipeline=None,
        pipeline_factory=factory,
        mode_provider=lambda: "guided",
        library=None,
    )

    result = services.data_session_loader.open(
        tmp_path / "data.csv",
        ImportOptions(confirm_new_session=True),
        pipeline_ops=services.pipeline_ops,
        pipeline_version=0,
    )

    assert result.pipeline is loaded
    assert calls[0][0] == tmp_path / "data.csv"
