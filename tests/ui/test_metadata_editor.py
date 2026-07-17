from __future__ import annotations

from modori.ui.metadata_editor import VariableMetadataEditor


class FakePipelineOps:
    def __init__(self) -> None:
        self.pipeline_present = True
        self.variables = {"score"}
        self.steps = set()
        self.edits = []
        self.insertions = []

    def has_pipeline(self) -> bool:
        return self.pipeline_present

    def has_variable(self, variable_key: str) -> bool:
        return variable_key in self.variables

    def has_step(self, step_id: str) -> bool:
        return step_id in self.steps

    def edit_metadata_params(self, step_id: str, params: dict[str, object]) -> None:
        self.edits.append((step_id, params))

    def insert_metadata_step(self, variable_key: str, step: object) -> None:
        self.insertions.append((variable_key, step))


def test_metadata_editor_normalizes_and_inserts_metadata_step() -> None:
    ops = FakePipelineOps()

    result = VariableMetadataEditor(ops).update(
        "score",
        {"measure": "nominal", "missing_codes": [99]},
        pipeline_version=4,
    )

    assert result.ok is True
    assert result.changed_step_ids == ["metadata:score"]
    assert result.pipeline_version == 4
    assert ops.edits == []
    assert len(ops.insertions) == 1
    _, step = ops.insertions[0]
    assert step.id == "metadata:score"
    assert step.params == {
        "variable_key": "score",
        "measure": "nominal",
        "missing_values": [99],
    }


def test_metadata_editor_reuses_existing_metadata_step() -> None:
    ops = FakePipelineOps()
    ops.steps.add("metadata:score")

    result = VariableMetadataEditor(ops).update(
        "score",
        {"label": "Score"},
        pipeline_version=2,
    )

    assert result.ok is True
    assert ops.edits == [("metadata:score", {"variable_key": "score", "label": "Score"})]
    assert ops.insertions == []


def test_metadata_editor_returns_validation_error_without_mutating_pipeline() -> None:
    ops = FakePipelineOps()

    result = VariableMetadataEditor(ops).update(
        "score",
        {"missing_codes": [1], "missing_values": [2]},
        pipeline_version=9,
    )

    assert result.ok is False
    assert result.error_code == "invalid_metadata_patch"
    assert ops.edits == []
    assert ops.insertions == []


def test_metadata_editor_rejects_invalid_measure_without_mutating_pipeline() -> None:
    ops = FakePipelineOps()

    result = VariableMetadataEditor(ops).update(
        "score",
        {"measure": "nonsense"},
        pipeline_version=9,
    )

    assert result.ok is False
    assert result.error_code == "invalid_measure"
    assert ops.edits == []
    assert ops.insertions == []


def test_metadata_editor_translates_pipeline_exceptions_to_engine_error() -> None:
    class FailingOps(FakePipelineOps):
        def insert_metadata_step(self, variable_key: str, step: object) -> None:
            raise RuntimeError("boom")

    result = VariableMetadataEditor(FailingOps()).update(
        "score",
        {"measure": "nominal"},
        pipeline_version=1,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
