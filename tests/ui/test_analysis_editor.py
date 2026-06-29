from __future__ import annotations

from modori.ui.analysis_editor import AnalysisSelectionEditor


class FakeStep:
    def __init__(self, step_id: str, step_type: str, params: dict[str, object]) -> None:
        self.id = step_id
        self.step_type = step_type
        self.params = params


class FakePipelineOps:
    def __init__(self) -> None:
        self.pipeline = self
        self.variable_keys = {"q1", "q2", "q3", "q4", "score", "group", "y", "x1", "x2"}
        self.steps = [
            FakeStep(
                "reliability",
                "stats.reliability",
                {"items": ["q1", "q2", "q3"], "language": "ko"},
            ),
            FakeStep(
                "comparison",
                "stats.compare_groups",
                {"dv": "score", "group": "group"},
            ),
            FakeStep(
                "regression",
                "stats.regression_ols",
                {"dv": "y", "predictors": ["x1"]},
            ),
        ]
        self.edits: list[tuple[str, dict[str, object]]] = []

    def step_collection(self):
        return self.pipeline

    def known_variable_keys(self) -> set[str]:
        return set(self.variable_keys)

    def edit_params(self, step_id: str, params: dict[str, object]) -> None:
        self.edits.append((step_id, params))


def test_analysis_editor_updates_reliability_selection() -> None:
    ops = FakePipelineOps()

    result = AnalysisSelectionEditor(ops).reliability("q1, q2, q4", pipeline_version=3)

    assert result.ok is True
    assert result.pipeline_version == 3
    assert result.changed_step_ids == ["reliability"]
    assert result.message_ko == "신뢰도 분석 변수가 변경되었습니다."
    assert ops.edits == [
        (
            "reliability",
            {"items": ["q1", "q2", "q4"], "language": "ko", "scale_name": "selected_scale"},
        )
    ]


def test_analysis_editor_returns_validation_error_without_editing() -> None:
    ops = FakePipelineOps()

    result = AnalysisSelectionEditor(ops).regression("y", "x1, y", pipeline_version=5)

    assert result.ok is False
    assert result.error_code == "invalid_selection"
    assert result.pipeline_version == 5
    assert ops.edits == []


def test_analysis_editor_translates_pipeline_edit_failure() -> None:
    class FailingOps(FakePipelineOps):
        def edit_params(self, step_id: str, params: dict[str, object]) -> None:
            raise RuntimeError("boom")

    result = AnalysisSelectionEditor(FailingOps()).comparison(
        "score",
        "group",
        pipeline_version=2,
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert result.message_ko == "분석 단계를 수정하지 못했습니다."
