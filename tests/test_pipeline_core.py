import json
from dataclasses import dataclass

import pandas as pd
import pytest

from modori.core import (
    Dataset,
    DatasetShapeLimits,
    Measure,
    Pipeline,
    PipelineContext,
    Step,
    StepResult,
    Variable,
)


def variable(name: str, *, missing_values: list[float] | None = None) -> Variable:
    return Variable(
        name=name,
        label=name.upper(),
        measure=Measure.SCALE,
        value_labels={},
        missing_values=missing_values or [],
        dtype="float",
        origin_step_id=None,
    )


def source_dataset() -> Dataset:
    return Dataset(
        df=pd.DataFrame({"raw": [1.0, 2.0, 3.0]}),
        variables={"raw": variable("raw")},
    )


@dataclass
class MultiplyStep(Step):
    compute_calls: int = 0

    step_type = "test.multiply"

    def compute(self, ctx: PipelineContext) -> StepResult:
        self.compute_calls += 1
        source = self.params["source"]
        output = self.params["output"]
        factor = self.params["factor"]
        return StepResult(
            new_columns={output: ctx.dataset.df[source] * factor},
            new_variables={
                output: Variable(
                    name=output,
                    label=output,
                    measure=Measure.SCALE,
                    value_labels={},
                    missing_values=[],
                    dtype="float",
                    origin_step_id=self.id,
                )
            },
            analysis=None,
            notes=[],
        )

    def reads(self) -> set[str]:
        return {self.params["source"]}

    def writes(self) -> set[str]:
        return {self.params["output"]}

    def provenance(self) -> str:
        return f"multiply {self.params['source']} by {self.params['factor']}"


Step.register_type(MultiplyStep.step_type, MultiplyStep)


def multiply_step(step_id: str, source: str, output: str, factor: float) -> MultiplyStep:
    return MultiplyStep(
        id=step_id,
        title=f"Multiply {source}",
        params={"source": source, "output": output, "factor": factor},
        input_step_ids=[],
    )


@dataclass
class UndeclaredColumnWriteStep(Step):
    step_type = "test.undeclared_column_write"

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(
            new_columns={"hidden": ctx.dataset.df["raw"]},
            new_variables={
                "hidden": Variable(
                    name="hidden",
                    label="hidden",
                    measure=Measure.SCALE,
                    value_labels={},
                    missing_values=[],
                    dtype="float",
                    origin_step_id=self.id,
                )
            },
        )

    def reads(self) -> set[str]:
        return {"raw"}

    def writes(self) -> set[str]:
        return {"declared"}


@dataclass
class MissingDeclaredColumnMetadataStep(Step):
    step_type = "test.missing_declared_column_metadata"

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(new_columns={"declared": ctx.dataset.df["raw"]})

    def reads(self) -> set[str]:
        return {"raw"}

    def writes(self) -> set[str]:
        return {"declared"}


@dataclass
class AnalysisWithoutDeclaredWriteStep(Step):
    step_type = "test.analysis_without_declared_write"

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(analysis={"value": 1})

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return set()


@dataclass
class DeclaredAnalysisWriteWithoutAnalysisStep(Step):
    step_type = "test.declared_analysis_write_without_analysis"

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult()

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return {"analysis:missing"}


@dataclass
class MultipleAnalysisWritesForSingleAnalysisStep(Step):
    step_type = "test.multiple_analysis_writes_for_single_analysis"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(analysis={"value": 1})

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return {"analysis:first", "analysis:second"}


@dataclass
class MisalignedIndexStep(Step):
    step_type = "test.misaligned_index"

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(
            new_columns={
                "shifted": pd.Series([10.0, 20.0, 30.0], index=[1, 2, 3]),
            },
            new_variables={
                "shifted": Variable(
                    name="shifted",
                    label="shifted",
                    measure=Measure.SCALE,
                    value_labels={},
                    missing_values=[],
                    dtype="float",
                    origin_step_id=self.id,
                )
            },
        )

    def reads(self) -> set[str]:
        return {"raw"}

    def writes(self) -> set[str]:
        return {"shifted"}


Step.register_type(UndeclaredColumnWriteStep.step_type, UndeclaredColumnWriteStep)
Step.register_type(
    MissingDeclaredColumnMetadataStep.step_type,
    MissingDeclaredColumnMetadataStep,
)
Step.register_type(
    AnalysisWithoutDeclaredWriteStep.step_type,
    AnalysisWithoutDeclaredWriteStep,
)
Step.register_type(
    DeclaredAnalysisWriteWithoutAnalysisStep.step_type,
    DeclaredAnalysisWriteWithoutAnalysisStep,
)
Step.register_type(
    MultipleAnalysisWritesForSingleAnalysisStep.step_type,
    MultipleAnalysisWritesForSingleAnalysisStep,
)
Step.register_type(MisalignedIndexStep.step_type, MisalignedIndexStep)


@dataclass
class AnalysisWriteStep(Step):
    step_type = "test.analysis_write"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        return StepResult(analysis={"id": self.id})

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return {str(self.params["write_key"])}


Step.register_type(AnalysisWriteStep.step_type, AnalysisWriteStep)


@dataclass
class DynamicWriteStep(Step):
    step_type = "test.dynamic_write"
    writes_are_static = False

    def compute(self, ctx: PipelineContext) -> StepResult:
        output = str(self.params["output"])
        return StepResult(
            new_columns={output: ctx.dataset.df["raw"]},
            new_variables={output: variable(output)},
        )

    def reads(self) -> set[str]:
        return {"raw"}

    def writes(self) -> set[str]:
        return {str(self.params["output"])}


@dataclass
class SideEffectStep(Step):
    step_type = "test.side_effect"

    def compute(self, ctx: PipelineContext) -> StepResult:
        path = self.params["path"]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("side effect")
        return StepResult()

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        return set()


Step.register_type(DynamicWriteStep.step_type, DynamicWriteStep)
Step.register_type(SideEffectStep.step_type, SideEffectStep)


@dataclass
class MetadataOnlyWriteStep(Step):
    step_type = "test.metadata_only_write"

    def compute(self, ctx: PipelineContext) -> StepResult:
        key = str(self.params["variable_key"])
        existing = ctx.dataset.variables[key]
        return StepResult(
            new_variables={
                key: Variable(
                    name=existing.name,
                    label=str(self.params["label"]),
                    measure=existing.measure,
                    value_labels=dict(existing.value_labels),
                    missing_values=list(existing.missing_values),
                    dtype=existing.dtype,
                    origin_step_id=existing.origin_step_id,
                )
            }
        )

    def reads(self) -> set[str]:
        return {str(self.params["variable_key"])}

    def writes(self) -> set[str]:
        return set()

    def metadata_writes(self) -> set[str]:
        return {str(self.params["variable_key"])}


@dataclass
class ChangingDynamicWriteStep(Step):
    step_type = "test.changing_dynamic_write"
    writes_are_static = False
    write_calls: int = 0

    def compute(self, ctx: PipelineContext) -> StepResult:
        output = str(self.params["compute_output"])
        return StepResult(
            new_columns={output: ctx.dataset.df["raw"]},
            new_variables={output: variable(output)},
        )

    def reads(self) -> set[str]:
        return {"raw"}

    def writes(self) -> set[str]:
        self.write_calls += 1
        if self.write_calls == 1:
            return {str(self.params["preflight_output"])}
        return {str(self.params["compute_output"])}


Step.register_type(ChangingDynamicWriteStep.step_type, ChangingDynamicWriteStep)


def test_dataset_requires_matching_dataframe_and_variable_columns() -> None:
    with pytest.raises(ValueError, match="column set"):
        Dataset(
            df=pd.DataFrame({"q1": [1.0, 2.0]}),
            variables={"other": variable("other")},
        )


def test_dataset_rejects_duplicate_dataframe_column_labels() -> None:
    frame = pd.DataFrame([[1.0, 2.0]], columns=["q1", "q1"])

    with pytest.raises(ValueError, match="Dataframe column labels must be unique"):
        Dataset(
            df=frame,
            variables={"q1": variable("q1")},
        )


def test_dataset_masks_declared_missing_values_without_mutating_source_data() -> None:
    dataset = Dataset(
        df=pd.DataFrame({"q1": [1.0, 99.0, 3.0]}),
        variables={"q1": variable("q1", missing_values=[99.0])},
    )

    compute_frame = dataset.frame_for_compute(["q1"])

    assert pd.isna(compute_frame.loc[1, "q1"])
    assert dataset.df.loc[1, "q1"] == 99.0


def test_editing_step_params_recomputes_exact_dependent_downstream_steps() -> None:
    first = multiply_step("double", "raw", "double", 2.0)
    downstream = multiply_step("quad", "double", "quad", 2.0)
    independent = multiply_step("triple", "raw", "triple", 3.0)

    pipeline = Pipeline(source_dataset())
    pipeline.add(first)
    pipeline.add(downstream)
    pipeline.add(independent)
    pipeline.recompute(dirty_from=None)

    assert first.compute_calls == 1
    assert downstream.compute_calls == 1
    assert independent.compute_calls == 1
    assert pipeline.current_dataset.df["quad"].tolist() == [4.0, 8.0, 12.0]

    pipeline.edit_params("double", {"source": "raw", "output": "double", "factor": 3.0})

    assert first.compute_calls == 2
    assert downstream.compute_calls == 2
    assert independent.compute_calls == 1
    assert pipeline.current_dataset.df["quad"].tolist() == [6.0, 12.0, 18.0]
    assert pipeline.current_dataset.df["triple"].tolist() == [3.0, 6.0, 9.0]


def test_pipeline_rejects_duplicate_writes_when_adding_step() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(multiply_step("double-a", "raw", "double", 2.0))

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.add(multiply_step("double-b", "raw", "double", 3.0))

    assert [step.id for step in pipeline.steps] == ["double-a"]


def test_pipeline_rejects_duplicate_metadata_writes_when_adding_step() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        MetadataOnlyWriteStep(
            id="metadata-a",
            title="Metadata A",
            params={"variable_key": "raw", "label": "Raw A"},
        )
    )

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.add(
            MetadataOnlyWriteStep(
                id="metadata-b",
                title="Metadata B",
                params={"variable_key": "raw", "label": "Raw B"},
            )
        )

    assert [step.id for step in pipeline.steps] == ["metadata-a"]


def test_edit_params_rolls_back_when_changed_writes_collide_with_another_step() -> None:
    first = multiply_step("double", "raw", "double", 2.0)
    second = multiply_step("triple", "raw", "triple", 3.0)
    pipeline = Pipeline(source_dataset())
    pipeline.add(first)
    pipeline.add(second)
    pipeline.recompute(dirty_from=None)

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.edit_params(
            "triple",
            {"source": "raw", "output": "double", "factor": 3.0},
        )

    assert second.params == {"source": "raw", "output": "triple", "factor": 3.0}
    assert pipeline.current_dataset.df["double"].tolist() == [2.0, 4.0, 6.0]
    assert pipeline.current_dataset.df["triple"].tolist() == [3.0, 6.0, 9.0]


def test_pipeline_json_round_trip_preserves_source_steps_and_results() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(multiply_step("double", "raw", "double", 2.0))
    pipeline.add(multiply_step("quad", "double", "quad", 2.0))
    pipeline.recompute(dirty_from=None)

    restored = Pipeline.from_json(pipeline.to_json())
    restored.recompute(dirty_from=None)

    assert [step.id for step in restored.steps] == ["double", "quad"]
    assert restored.steps[0].params == {"source": "raw", "output": "double", "factor": 2.0}
    pd.testing.assert_frame_equal(restored.current_dataset.df, pipeline.current_dataset.df)


def test_pipeline_json_round_trip_uses_strict_json_for_native_missing_values() -> None:
    pipeline = Pipeline(
        Dataset(
            df=pd.DataFrame({"raw": [1.0, float("nan"), 3.0]}),
            variables={"raw": variable("raw")},
        )
    )

    payload = pipeline.to_json()

    assert "NaN" not in payload
    restored = Pipeline.from_json(payload)
    assert pd.isna(restored.source_dataset.df.loc[1, "raw"])


@pytest.mark.parametrize(
    "payload, message",
    [
        ("{", "Pipeline JSON is invalid"),
        ("[]", "Pipeline JSON must be an object"),
        ('{"source_dataset": {}, "steps": {}}', "Pipeline JSON steps must be a list"),
        ('{"steps": []}', "Pipeline JSON missing required key: source_dataset"),
        ('{"source_dataset": [], "steps": []}', "Dataset payload must be an object"),
        ('{"source_dataset": {"df": [], "variables": {}}, "steps": []}', "Dataset df payload must be an object"),
        ('{"source_dataset": {"df": {"columns": [], "index": [], "data": []}, "variables": []}, "steps": []}', "Dataset variables must be an object"),
        ('{"source_dataset": {"df": {"columns": ["raw"], "index": [0], "data": [[1]], "extra": true}, "variables": {"raw": "bad"}}, "steps": []}', "Variable payload for raw must be an object"),
        ('{"source_dataset": {"df": {"columns": [], "index": [], "data": []}, "variables": {}}, "steps": [{"type": "test.multiply", "id": "x", "title": "x", "params": "bad"}]}', "Step params must be an object"),
        ('{"source_dataset": {"df": {"columns": [], "index": [], "data": []}, "variables": {}}, "steps": [{"type": "test.multiply", "id": "x", "title": "x", "params": {}, "input_step_ids": "abc"}]}', "Step input_step_ids must be a list of strings"),
        ('{"source_dataset": {"df": {"columns": [], "index": [], "data": []}, "variables": {}}, "steps": [{"type": "missing.step", "id": "x", "title": "x", "params": {}}]}', "Unknown Step type: missing.step"),
        ('{"source_dataset": {"df": {"columns": [], "index": [], "data": []}, "variables": {}}, "steps": ["bad"]}', "Pipeline JSON step entries must be objects"),
    ],
)
def test_pipeline_from_json_rejects_malformed_payloads_clearly(
    payload,
    message,
) -> None:
    with pytest.raises(ValueError, match=message):
        Pipeline.from_json(payload)


def test_dataset_from_dict_rejects_payload_when_explicit_cell_limit_is_exceeded() -> None:
    payload = Dataset(
        df=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
        variables={"a": variable("a"), "b": variable("b")},
    ).to_dict()

    with pytest.raises(ValueError, match="cell limit"):
        Dataset.from_dict(payload, limits=DatasetShapeLimits(max_cells=3))


def test_dataset_from_dict_rejects_variables_payload_before_frame_expansion(
    monkeypatch,
) -> None:
    payload = Dataset(
        df=pd.DataFrame({"a": [1], "b": [2]}),
        variables={"a": variable("a"), "b": variable("b")},
    ).to_dict()

    def dataframe_spy(*args, **kwargs):
        raise AssertionError("DataFrame should not be constructed")

    monkeypatch.setattr("modori.core.model.pd.DataFrame", dataframe_spy)

    with pytest.raises(ValueError, match="variable limit"):
        Dataset.from_dict(payload, limits=DatasetShapeLimits(max_variables=1))


def test_pipeline_from_json_applies_untrusted_dataset_shape_limit() -> None:
    payload = {
        "source_dataset": Dataset(
            df=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
            variables={"a": variable("a"), "b": variable("b")},
        ).to_dict(),
        "steps": [],
    }

    with pytest.raises(ValueError, match="cell limit"):
        Pipeline.from_json(
            json.dumps(payload),
            dataset_limits=DatasetShapeLimits(max_cells=3),
        )


def test_pipeline_from_json_rejects_json_byte_limit_before_parse(monkeypatch) -> None:
    payload = json.dumps(
        {
            "source_dataset": Dataset.empty().to_dict(),
            "steps": [],
        }
    )

    def loads_spy(*args, **kwargs):
        raise AssertionError("json.loads should not be called")

    monkeypatch.setattr("modori.core.pipeline.json.loads", loads_spy)

    with pytest.raises(ValueError, match="JSON byte limit"):
        Pipeline.from_json(payload, dataset_limits=DatasetShapeLimits(max_json_bytes=1))


def test_pipeline_from_json_applies_default_untrusted_dataset_shape_limit(
    monkeypatch,
) -> None:
    payload = {
        "source_dataset": Dataset(
            df=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
            variables={"a": variable("a"), "b": variable("b")},
        ).to_dict(),
        "steps": [],
    }
    monkeypatch.setattr(
        "modori.core.pipeline.DEFAULT_UNTRUSTED_DATASET_LIMITS",
        DatasetShapeLimits(max_cells=3),
    )

    with pytest.raises(ValueError, match="cell limit"):
        Pipeline.from_json(json.dumps(payload))


def test_pipeline_from_json_does_not_apply_default_dataset_limit_to_trusted_project(
    monkeypatch,
) -> None:
    payload = {
        "source_dataset": Dataset(
            df=pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
            variables={"a": variable("a"), "b": variable("b")},
        ).to_dict(),
        "steps": [],
    }
    monkeypatch.setattr(
        "modori.core.pipeline.DEFAULT_UNTRUSTED_DATASET_LIMITS",
        DatasetShapeLimits(max_cells=3),
    )

    pipeline = Pipeline.from_json(json.dumps(payload), trust_project_file=True)

    assert pipeline.source_dataset.df.shape == (2, 2)


def test_pipeline_rejects_step_result_columns_not_declared_in_writes() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        UndeclaredColumnWriteStep(
            id="bad",
            title="Bad write",
            params={},
        )
    )

    with pytest.raises(ValueError, match="returned undeclared column writes"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_step_result_columns_without_metadata() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        MissingDeclaredColumnMetadataStep(
            id="bad",
            title="Bad metadata",
            params={},
        )
    )

    with pytest.raises(ValueError, match="returned columns without metadata"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_step_result_series_with_misaligned_index() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        MisalignedIndexStep(
            id="bad-index",
            title="Bad index",
            params={},
        )
    )

    with pytest.raises(ValueError, match="index must match the current dataset"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_analysis_without_declared_analysis_write() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        AnalysisWithoutDeclaredWriteStep(
            id="bad",
            title="Bad analysis",
            params={},
        )
    )

    with pytest.raises(ValueError, match="returned analysis without declared analysis writes"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_declared_analysis_write_without_analysis() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        DeclaredAnalysisWriteWithoutAnalysisStep(
            id="bad",
            title="Bad missing analysis",
            params={},
        )
    )

    with pytest.raises(ValueError, match="declared writes that were not returned"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_multiple_analysis_writes_for_single_analysis_object() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        MultipleAnalysisWritesForSingleAnalysisStep(
            id="bad",
            title="Bad multiple analysis",
            params={},
        )
    )

    with pytest.raises(ValueError, match="returned one analysis object for multiple analysis writes"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_rejects_analysis_alias_collision_with_declared_write_on_add() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        AnalysisWriteStep(
            id="owner",
            title="Trusted analysis",
            params={"write_key": "analysis:trusted"},
        )
    )

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.add(
            AnalysisWriteStep(
                id="trusted",
                title="Poison alias",
                params={"write_key": "analysis:poison"},
            )
        )


def test_pipeline_rejects_analysis_alias_collision_with_declared_write_at_recompute() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.steps = [
        AnalysisWriteStep(
            id="owner",
            title="Trusted analysis",
            params={"write_key": "analysis:trusted"},
        ),
        AnalysisWriteStep(
            id="trusted",
            title="Poison alias",
            params={"write_key": "analysis:poison"},
        ),
    ]

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.recompute(dirty_from=None)


def test_pipeline_from_json_rejects_analysis_alias_collision_with_declared_write() -> None:
    payload = {
        "source_dataset": source_dataset().to_dict(),
        "steps": [
            {
                "type": "test.analysis_write",
                "id": "owner",
                "title": "Trusted analysis",
                "params": {"write_key": "analysis:trusted"},
            },
            {
                "type": "test.analysis_write",
                "id": "trusted",
                "title": "Poison alias",
                "params": {"write_key": "analysis:poison"},
            },
        ],
    }

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        Pipeline.from_json(json.dumps(payload))


def test_pipeline_from_json_rejects_report_io_steps_by_default(tmp_path) -> None:
    output_dir = tmp_path / "attacker-chosen-output"
    payload = {
        "source_dataset": source_dataset().to_dict(),
        "steps": [
            {
                "type": "report.apa",
                "id": "report",
                "title": "Attacker controlled report",
                "params": {
                    "include": [],
                    "output_dir": str(output_dir),
                    "filename": "report.docx",
                    "language": "ko",
                },
            },
        ],
    }

    with pytest.raises(ValueError, match="requires trusted project JSON"):
        Pipeline.from_json(json.dumps(payload))

    assert not output_dir.exists()


def test_pipeline_from_json_allows_report_io_steps_when_project_file_is_trusted(tmp_path) -> None:
    output_dir = tmp_path / "trusted-output"
    payload = {
        "source_dataset": source_dataset().to_dict(),
        "steps": [
            {
                "type": "report.apa",
                "id": "report",
                "title": "Trusted report",
                "params": {
                    "include": [],
                    "output_dir": str(output_dir),
                    "filename": "report.docx",
                    "language": "ko",
                },
            },
        ],
    }

    pipeline = Pipeline.from_json(json.dumps(payload), trust_project_file=True)

    assert [step.id for step in pipeline.steps] == ["report"]
    assert not output_dir.exists()


def test_pipeline_from_json_rejects_import_io_steps_by_default(tmp_path) -> None:
    csv_path = tmp_path / "attacker-selected.csv"
    csv_path.write_text("raw\n1\n2\n", encoding="utf-8")
    payload = {
        "source_dataset": Dataset.empty().to_dict(),
        "steps": [
            {
                "type": "import.table",
                "id": "import",
                "title": "Attacker controlled import",
                "params": {"path": str(csv_path), "file_type": "csv"},
            },
        ],
    }

    with pytest.raises(ValueError, match="requires trusted project JSON"):
        Pipeline.from_json(json.dumps(payload))


def test_pipeline_from_json_allows_import_io_steps_when_project_file_is_trusted(tmp_path) -> None:
    csv_path = tmp_path / "trusted.csv"
    csv_path.write_text("raw\n1\n2\n", encoding="utf-8")
    payload = {
        "source_dataset": Dataset.empty().to_dict(),
        "steps": [
            {
                "type": "import.table",
                "id": "import",
                "title": "Trusted import",
                "params": {"path": str(csv_path), "file_type": "csv"},
            },
        ],
    }

    pipeline = Pipeline.from_json(json.dumps(payload), trust_project_file=True)

    assert [step.id for step in pipeline.steps] == ["import"]


def test_pipeline_from_json_rejects_regression_import_io_steps_by_default(tmp_path) -> None:
    csv_path = tmp_path / "attacker-selected-regression.csv"
    csv_path.write_text("y,x\n1,2\n3,4\n", encoding="utf-8")
    payload = {
        "source_dataset": Dataset.empty().to_dict(),
        "steps": [
            {
                "type": "import.regression_table",
                "id": "reg-import",
                "title": "Attacker controlled regression import",
                "params": {"path": str(csv_path), "scale_columns": ["y", "x"]},
            },
        ],
    }

    with pytest.raises(ValueError, match="requires trusted project JSON"):
        Pipeline.from_json(json.dumps(payload))


def test_pipeline_validates_dynamic_write_collisions_before_side_effects(tmp_path) -> None:
    marker = tmp_path / "side-effect.txt"
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        DynamicWriteStep(
            id="dynamic-a",
            title="Dynamic A",
            params={"output": "shared"},
        )
    )
    pipeline.add(
        DynamicWriteStep(
            id="dynamic-b",
            title="Dynamic B",
            params={"output": "shared"},
        )
    )
    pipeline.add(
        SideEffectStep(
            id="side-effect",
            title="Side effect",
            params={"path": str(marker)},
        )
    )

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.recompute(dirty_from=None)

    assert not marker.exists()


def test_pipeline_revalidates_dynamic_write_changes_before_downstream_side_effects(tmp_path) -> None:
    marker = tmp_path / "side-effect.txt"
    pipeline = Pipeline(source_dataset())
    pipeline.add(
        MultiplyStep(
            id="owner",
            title="Owner",
            params={"source": "raw", "output": "computed", "factor": 1.0},
        )
    )
    pipeline.add(
        ChangingDynamicWriteStep(
            id="mutating-dynamic",
            title="Mutating dynamic",
            params={"preflight_output": "preflight", "compute_output": "computed"},
        )
    )
    pipeline.add(
        SideEffectStep(
            id="side-effect",
            title="Side effect",
            params={"path": str(marker)},
        )
    )

    with pytest.raises(ValueError, match="Duplicate Step write key"):
        pipeline.recompute(dirty_from=None)

    assert not marker.exists()


def test_dirty_propagation_uses_previous_writes_when_upstream_writes_shrink() -> None:
    first = multiply_step("double", "raw", "double", 2.0)
    downstream = multiply_step("quad", "double", "quad", 2.0)
    pipeline = Pipeline(source_dataset())
    pipeline.add(first)
    pipeline.add(downstream)
    pipeline.recompute(dirty_from=None)

    first.params = {"source": "raw", "output": "renamed", "factor": 3.0}

    with pytest.raises(KeyError, match="double"):
        pipeline.recompute(dirty_from="double")

    assert downstream.compute_calls == 2
    assert pipeline.current_dataset.df["quad"].tolist() == [4.0, 8.0, 12.0]


def test_edit_params_rolls_back_when_new_params_cannot_be_validated() -> None:
    step = multiply_step("double", "raw", "double", 2.0)
    pipeline = Pipeline(source_dataset())
    pipeline.add(step)
    pipeline.recompute(dirty_from=None)

    with pytest.raises(KeyError, match="missing"):
        pipeline.edit_params(
            "double",
            {"source": "missing", "output": "double", "factor": 3.0},
        )

    assert step.params == {"source": "raw", "output": "double", "factor": 2.0}
    assert pipeline.current_dataset.df["double"].tolist() == [2.0, 4.0, 6.0]


def test_replace_source_dataset_rolls_back_when_downstream_recompute_fails() -> None:
    pipeline = Pipeline(source_dataset())
    pipeline.add(multiply_step("double", "raw", "double", 2.0))
    pipeline.recompute(dirty_from=None)
    previous_source = pipeline.source_dataset
    previous_current = pipeline.current_dataset

    incompatible_source = Dataset(
        df=pd.DataFrame({"other": [1.0, 2.0, 3.0]}),
        variables={"other": variable("other")},
    )

    with pytest.raises(KeyError, match="raw"):
        pipeline.replace_source_dataset(incompatible_source)

    assert pipeline.source_dataset is previous_source
    assert pipeline.current_dataset is previous_current
    assert pipeline.current_dataset.df["double"].tolist() == [2.0, 4.0, 6.0]


def test_remove_rolls_back_when_downstream_recompute_fails() -> None:
    first = multiply_step("double", "raw", "double", 2.0)
    downstream = multiply_step("quad", "double", "quad", 2.0)
    pipeline = Pipeline(source_dataset())
    pipeline.add(first)
    pipeline.add(downstream)
    pipeline.recompute(dirty_from=None)

    with pytest.raises(KeyError, match="double"):
        pipeline.remove("double")

    assert [step.id for step in pipeline.steps] == ["double", "quad"]
    assert pipeline.current_dataset.df["quad"].tolist() == [4.0, 8.0, 12.0]
