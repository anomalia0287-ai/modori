from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.core import Dataset, Measure, Pipeline, Step, StepResult, Variable
from modori.steps import ImportStep, VariableMetadataPatchStep
from modori.ui.controller import UiController


class MeasureEchoStep(Step):
    step_type = "test.measure_echo"
    produces_analysis = True

    def compute(self, ctx):
        variable_key = str(self.params["variable_key"])
        return StepResult(analysis=ctx.dataset.variables[variable_key].measure.value)

    def reads(self) -> set[str]:
        return {str(self.params["variable_key"])}

    def writes(self) -> set[str]:
        return {str(self.params["result_key"])}


class FailingMetadataDependentStep(Step):
    step_type = "test.failing_metadata_dependent"
    produces_analysis = True

    def compute(self, ctx):
        raise RuntimeError("metadata-dependent recompute failed")

    def reads(self) -> set[str]:
        return {str(self.params["variable_key"])}

    def writes(self) -> set[str]:
        return {str(self.params["result_key"])}


def _write_csv(path: Path) -> None:
    pd.DataFrame({"group": [1, 2], "score": [3.5, 4.5]}).to_csv(path, index=False)


def test_variable_metadata_patch_step_updates_metadata_without_touching_values() -> None:
    dataset = Dataset(
        df=pd.DataFrame({"group": [1, 2]}),
        variables={
            "group": Variable(
                name="group",
                label="Group code",
                measure=Measure.ORDINAL,
                value_labels={},
                missing_values=[],
                dtype="int",
                origin_step_id=None,
            )
        },
    )
    step = VariableMetadataPatchStep(
        id="metadata:group",
        title="Edit group metadata",
        params={"variable_key": "group", "measure": "nominal", "label": "Treatment group"},
    )

    result = step.compute_context_free(dataset)

    assert result.new_columns == {}
    assert result.new_variables["group"].measure is Measure.NOMINAL
    assert result.new_variables["group"].label == "Treatment group"
    assert dataset.df["group"].tolist() == [1, 2]
    assert step.reads() == {"group"}
    assert step.writes() == set()
    assert step.metadata_writes() == {"group"}


def test_pipeline_recomputes_downstream_steps_after_metadata_patch_edit(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.insert_after(
        "import",
        VariableMetadataPatchStep(
            id="metadata:group",
            title="Edit group metadata",
            params={"variable_key": "group", "measure": "nominal"},
        ),
    )
    pipeline.add(
        MeasureEchoStep(
            id="analysis:measure_echo",
            title="Measure echo",
            params={"variable_key": "group", "result_key": "measure_echo"},
        )
    )

    pipeline.recompute(dirty_from=None)
    assert pipeline.analysis_objects["measure_echo"] == "nominal"

    pipeline.edit_params("metadata:group", {"variable_key": "group", "measure": "scale"})

    assert pipeline.current_dataset.variables["group"].measure is Measure.SCALE
    assert pipeline.analysis_objects["measure_echo"] == "scale"


def test_controller_changes_variable_measure_through_metadata_step(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    controller = UiController(pipeline=pipeline)

    ok = controller.changeVariableMeasure("group", "nominal")

    assert ok is True
    assert [step.id for step in pipeline.steps][:2] == ["import", "metadata:group"]
    assert pipeline.current_dataset.variables["group"].measure is Measure.NOMINAL
    assert controller.stale is True
    assert controller.pipeline_version == 1
    assert "Edit metadata: group" in controller.stepChainText


def test_controller_maps_missing_codes_to_engine_missing_values(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    controller = UiController(pipeline=pipeline)

    result = controller.updateVariableMetadata("group", {"missing_codes": [2]})

    assert result.ok is True
    assert pipeline.current_dataset.variables["group"].missing_values == [2.0]
    compute_frame = pipeline.current_dataset.frame_for_compute(["group"])
    assert compute_frame["group"].isna().tolist() == [False, True]


def test_controller_rejects_ambiguous_missing_code_aliases(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    controller = UiController(pipeline=pipeline)
    before_version = controller.pipeline_version

    result = controller.updateVariableMetadata(
        "group",
        {"missing_codes": [1], "missing_values": [2]},
    )

    assert result.ok is False
    assert result.error_code == "invalid_metadata_patch"
    assert pipeline.current_dataset.variables["group"].missing_values == []
    assert controller.pipeline_version == before_version


def test_controller_rejects_unsupported_display_type_metadata_patch(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    controller = UiController(pipeline=pipeline)
    before_version = controller.pipeline_version

    result = controller.updateVariableMetadata("group", {"display_type": "numeric"})

    assert result.ok is False
    assert result.error_code == "unsupported_metadata_patch"
    assert [step.id for step in pipeline.steps] == ["import"]
    assert controller.pipeline_version == before_version


def test_controller_reuses_existing_metadata_step_for_measure_changes(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    controller = UiController(pipeline=pipeline)

    assert controller.changeVariableMeasure("group", "nominal") is True
    assert controller.changeVariableMeasure("group", "scale") is True

    assert [step.id for step in pipeline.steps].count("metadata:group") == 1
    assert pipeline.current_dataset.variables["group"].measure is Measure.SCALE
    assert controller.pipeline_version == 2


def test_controller_rolls_back_inserted_metadata_step_when_recompute_fails(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    pipeline = Pipeline(Dataset.empty())
    pipeline.add(
        ImportStep(
            id="import",
            title="Import CSV",
            params={"path": str(data_path), "file_type": "csv"},
        )
    )
    pipeline.recompute(dirty_from=None)
    pipeline.add(
        FailingMetadataDependentStep(
            id="analysis:failing",
            title="Failing metadata-dependent analysis",
            params={"variable_key": "group", "result_key": "failing_result"},
        )
    )
    controller = UiController(pipeline=pipeline)
    before_steps = list(pipeline.steps)
    before_dataset = pipeline.current_dataset
    before_version = controller.pipeline_version

    result = controller.updateVariableMetadata("group", {"measure": "nominal"})

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert pipeline.steps == before_steps
    assert [step.id for step in pipeline.steps] == ["import", "analysis:failing"]
    assert pipeline.current_dataset is before_dataset
    assert pipeline.current_dataset.variables["group"].measure is not Measure.NOMINAL
    assert controller.pipeline_version == before_version


def test_variable_table_exposes_measure_editing_action() -> None:
    qml = Path("src/modori/ui/qml/components/VariableTable.qml").read_text(encoding="utf-8")

    assert "variable.measure_edit" in qml
    assert "uiController.changeVariableMeasure" in qml


def test_variable_table_selects_row_as_measure_edit_target() -> None:
    qml = Path("src/modori/ui/qml/components/VariableTable.qml").read_text(encoding="utf-8")

    assert "property string selectedVariableKey" in qml
    assert "function selectVariable(variableKey, measureValue)" in qml
    assert "model.variableKey" in qml
    assert "model.measureValue" in qml
    assert "onClicked: root.selectVariable(variableKey, measureValue)" in qml
    assert "readOnly: true" in qml
    assert "uiController.changeVariableMeasure(root.selectedVariableKey" in qml
