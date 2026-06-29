from __future__ import annotations

import pytest

from modori.ui.commands import AnalysisSelectionCommandBuilder, normalize_variable_metadata_patch
from modori.ui.patches import PatchValidationError


class FakeStep:
    def __init__(self, step_id: str, step_type: str, params: dict[str, object]) -> None:
        self.id = step_id
        self.step_type = step_type
        self.params = params


class FakePipeline:
    def __init__(self) -> None:
        self.steps = [
            FakeStep(
                "reliability",
                "stats.reliability",
                {"items": ["q1", "q2", "q3"], "language": "ko"},
            ),
            FakeStep(
                "regression",
                "stats.regression_ols",
                {"dv": "y", "predictors": ["x1"]},
            ),
        ]


def test_analysis_command_builder_builds_reliability_step_edit() -> None:
    command = AnalysisSelectionCommandBuilder(
        pipeline=FakePipeline(),
        variable_keys={"q1", "q2", "q3", "q4", "y", "x1", "x2"},
    ).reliability("q1, q2, q4")

    assert command.step_id == "reliability"
    assert command.params["items"] == ["q1", "q2", "q4"]
    assert command.params["scale_name"] == "selected_scale"
    assert command.message_ko == "신뢰도 분석 변수가 변경되었습니다."


def test_analysis_command_builder_rejects_regression_outcome_in_predictors() -> None:
    with pytest.raises(PatchValidationError) as error:
        AnalysisSelectionCommandBuilder(
            pipeline=FakePipeline(),
            variable_keys={"y", "x1", "x2"},
        ).regression("y", "x1, y")

    assert error.value.error_code == "invalid_selection"
    assert "종속 변수" in error.value.message_ko


def test_analysis_command_builder_uses_explicit_step_contract() -> None:
    import inspect

    source = inspect.getsource(AnalysisSelectionCommandBuilder)

    assert "getattr(" not in source


def test_normalize_variable_metadata_patch_maps_missing_codes_to_engine_name() -> None:
    assert normalize_variable_metadata_patch({"missing_codes": [99]}) == {
        "missing_values": [99]
    }


def test_normalize_variable_metadata_patch_rejects_display_type() -> None:
    with pytest.raises(PatchValidationError) as error:
        normalize_variable_metadata_patch({"display_type": "numeric"})

    assert error.value.error_code == "unsupported_metadata_patch"
