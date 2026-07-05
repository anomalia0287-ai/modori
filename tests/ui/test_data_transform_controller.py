from __future__ import annotations

from pathlib import Path

import pandas as pd

from modori.ui.contracts import ImportOptions
from modori.ui.controller import UiController


def _write_csv(path: Path) -> None:
    pd.DataFrame({"q1": [1, 2], "q2": [2, 3], "q3": [5, 4], "group": [1, 2]}).to_csv(
        path,
        index=False,
    )


def test_controller_applies_reverse_code_transform_and_marks_results_stale(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    assert controller.openDataFile(data_path, ImportOptions(confirm_new_session=True)).ok is True
    before_version = controller.pipeline_version

    result = controller.applyReverseCodeTransform(
        {"columns": ["q3"], "scale_min": 1, "scale_max": 5, "suffix": "_R"}
    )

    assert result.ok is True
    assert result.changed_step_ids == ["transform:reverse"]
    assert controller.pipeline_version == before_version + 1
    assert controller.stale is True
    assert "Reverse-code items" in controller.stepChainText
    assert "q3_R" in controller.pipeline.current_dataset.df.columns


def test_controller_applies_scale_score_transform(tmp_path: Path) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))

    result = controller.applyScaleScoreTransform(
        {
            "items": ["q1", "q2", "q3"],
            "name": "score",
            "method": "mean",
            "missing_policy": {"preset": "survey", "min_valid": 0.8},
        }
    )

    assert result.ok is True
    assert "Compose scale score" in controller.stepChainText
    assert "score" in controller.pipeline.current_dataset.df.columns


def test_controller_rejects_invalid_transform_without_version_bump(
    tmp_path: Path,
) -> None:
    data_path = tmp_path / "survey.csv"
    _write_csv(data_path)
    controller = UiController()
    controller.openDataFile(data_path, ImportOptions(confirm_new_session=True))
    before_version = controller.pipeline_version

    result = controller.applyScaleScoreTransform(
        {
            "items": ["q1"],
            "name": "",
            "method": "mean",
            "missing_policy": {"preset": "survey"},
        }
    )

    assert result.ok is False
    assert result.error_code == "invalid_transform"
    assert controller.pipeline_version == before_version
    assert "score" not in controller.pipeline.current_dataset.df.columns
