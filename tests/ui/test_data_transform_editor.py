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


def test_reverse_code_rejects_output_collision_without_mutating_pipeline(
    tmp_path: Path,
) -> None:
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
