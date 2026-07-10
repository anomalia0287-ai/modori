from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, Variable
from modori.ui.controller import UiController
from modori.recommendations import RecommendationCandidate, RecommendationState
from modori.ui.chart_assets import ChartAssetRenderer
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.value_tokens import canonical_value_token, decode_value_token


def _variable(
    name: str,
    measure: Measure,
    *,
    value_labels: dict[float, str] | None = None,
    missing_values: list[float] | None = None,
) -> Variable:
    return Variable(
        name=name,
        label=name,
        measure=measure,
        value_labels={} if value_labels is None else value_labels,
        missing_values=[] if missing_values is None else missing_values,
        dtype="object",
        origin_step_id="fixture",
    )


def _dataset() -> Dataset:
    frame = pd.DataFrame(
        {
            "event": [0, 1, 99, 1, 0, 1],
            "x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "condition": [
                "control",
                "treatment",
                "control",
                "treatment",
                "control",
                "treatment",
            ],
        }
    )
    return Dataset(
        df=frame,
        variables={
            "event": _variable(
                "event",
                Measure.ORDINAL,
                value_labels={0.0: "미완료", 1.0: "완료"},
                missing_values=[99.0],
            ),
            "x": _variable("x", Measure.SCALE),
            "condition": _variable("condition", Measure.NOMINAL),
        },
    )


@pytest.mark.parametrize("value", [False, 7, -0.0, 1.25, "완료"])
def test_value_tokens_are_canonical_and_round_trip_exact_scalar_types(
    value: bool | int | float | str,
) -> None:
    token = canonical_value_token(value)

    assert (
        json.dumps(
            json.loads(token),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        == token
    )
    decoded = decode_value_token(token)
    assert type(decoded) is type(value)
    assert decoded == value


@pytest.mark.parametrize(
    "value",
    [None, np.nan, np.inf, -np.inf, complex(1, 2), [1]],
)
def test_value_tokens_reject_unsupported_or_nonfinite_values(value: object) -> None:
    with pytest.raises(ValueError):
        canonical_value_token(value)


@pytest.mark.parametrize(
    "token",
    [
        '{"type":"int","value":1} ',
        '{"type":"int","value":true}',
        '{"type":"float","value":NaN}',
        '{"type":"str","value":"x","extra":1}',
        "not-json",
    ],
)
def test_value_token_decoder_rejects_noncanonical_or_forged_tokens(token: str) -> None:
    with pytest.raises(ValueError):
        decode_value_token(token)


def test_controller_returns_two_nonmissing_outcome_values_with_labels_and_raw_tokens() -> (
    None
):
    controller = UiController(pipeline=Pipeline(_dataset()))

    rows = controller.logisticOutcomeOptions("event")

    assert rows == [
        {"token": canonical_value_token(0), "label": "미완료 (0)"},
        {"token": canonical_value_token(1), "label": "완료 (1)"},
    ]
    assert [type(decode_value_token(row["token"])) for row in rows] == [int, int]


def test_controller_rejects_outcome_values_with_identical_display_labels() -> None:
    dataset = _dataset()
    frame = dataset.df.copy()
    frame["event"] = np.asarray(["1", 1, "1", 1, "1", 1], dtype=object)
    dataset = Dataset(
        df=frame,
        variables={
            **dataset.variables,
            "event": _variable("event", Measure.ORDINAL),
        },
    )

    assert (
        UiController(pipeline=Pipeline(dataset)).logisticOutcomeOptions("event") == []
    )


@pytest.mark.parametrize(
    ("text_value", "typed_value"),
    [
        ("True", True),
        ("１", 1),
        ("1 ", 1),
    ],
)
def test_controller_rejects_visually_confusable_outcome_labels(
    text_value: str,
    typed_value: bool | int,
) -> None:
    dataset = _dataset()
    frame = dataset.df.copy()
    frame["event"] = np.asarray(
        [text_value, typed_value, text_value, typed_value, text_value, typed_value],
        dtype=object,
    )
    dataset = Dataset(
        df=frame,
        variables={
            **dataset.variables,
            "event": _variable("event", Measure.ORDINAL),
        },
    )

    assert (
        UiController(pipeline=Pipeline(dataset)).logisticOutcomeOptions("event") == []
    )


def test_controller_rejects_blank_outcome_display_labels() -> None:
    dataset = _dataset()
    frame = dataset.df.copy()
    frame["event"] = np.asarray(["", 1, "", 1, "", 1], dtype=object)
    dataset = Dataset(
        df=frame,
        variables={
            **dataset.variables,
            "event": _variable("event", Measure.ORDINAL),
        },
    )

    assert (
        UiController(pipeline=Pipeline(dataset)).logisticOutcomeOptions("event") == []
    )


def test_controller_formats_integral_float_outcomes_like_other_categorical_levels() -> (
    None
):
    dataset = _dataset()
    frame = dataset.df.copy()
    frame["event"] = np.asarray([0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    dataset = Dataset(
        df=frame,
        variables={
            **dataset.variables,
            "event": _variable("event", Measure.ORDINAL),
        },
    )

    rows = UiController(pipeline=Pipeline(dataset)).logisticOutcomeOptions("event")

    assert rows == [
        {"token": canonical_value_token(0.0), "label": "0"},
        {"token": canonical_value_token(1.0), "label": "1"},
    ]


def test_controller_returns_reference_options_only_for_selected_categorical_predictors() -> (
    None
):
    controller = UiController(pipeline=Pipeline(_dataset()))

    rows = controller.logisticCategoricalReferenceOptions("x, condition")

    assert rows == [
        {
            "variable": "condition",
            "levels": [
                {
                    "token": canonical_value_token("control"),
                    "label": "control",
                },
                {
                    "token": canonical_value_token("treatment"),
                    "label": "treatment",
                },
            ],
        }
    ]


def test_outcome_query_exposes_nonbinary_levels_so_commit_can_be_disabled() -> None:
    dataset = _dataset()
    frame = dataset.df.copy()
    frame.loc[len(frame)] = [2, 7.0, "control"]
    controller = UiController(
        pipeline=Pipeline(Dataset(df=frame, variables=dict(dataset.variables)))
    )

    rows = controller.logisticOutcomeOptions("event")

    assert [decode_value_token(row["token"]) for row in rows] == [0, 1, 2]


def test_controller_configures_value_backed_logistic_step_and_report() -> None:
    pipeline = Pipeline(_dataset())
    controller = UiController(pipeline=pipeline)
    before_version = controller.pipeline_version

    result = controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x, condition",
        {"condition": canonical_value_token("control")},
    )

    assert result.ok is True
    assert result.changed_step_ids == ["logistic_regression"]
    assert controller.pipeline_version == before_version + 1
    assert controller.stale is True
    assert [step.step_type for step in pipeline.steps] == [
        "stats.logistic_regression",
        "report.apa",
    ]
    assert pipeline.steps[0].params["event_value"] == 1
    assert type(pipeline.steps[0].params["event_value"]) is int
    assert pipeline.steps[1].params["include"] == ["logistic_regression"]


def test_logistic_configuration_round_trips_pipeline_json_without_type_loss() -> None:
    pipeline = Pipeline(_dataset())
    controller = UiController(pipeline=pipeline)
    assert controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x",
    ).ok

    restored = Pipeline.from_json(pipeline.to_json(), trust_project_file=True)

    assert [step.step_type for step in restored.steps] == [
        "stats.logistic_regression",
        "report.apa",
    ]
    assert restored.steps[0].params["event_value"] == 1
    assert type(restored.steps[0].params["event_value"]) is int
    assert restored.steps[0].params["logistic_policy"]["categorical_predictors"] == {}


def test_stale_event_token_is_rejected_without_mutating_pipeline_or_version() -> None:
    dataset = _dataset()
    pipeline = Pipeline(dataset)
    controller = UiController(pipeline=pipeline)
    stale_token = controller.logisticOutcomeOptions("event")[1]["token"]
    replacement = Dataset(
        df=dataset.df.assign(event=[2, 3, 99, 3, 2, 3]),
        variables=dict(dataset.variables),
    )
    pipeline.replace_source_dataset(replacement)
    before_version = controller.pipeline_version

    result = controller.configureLogisticRegression("event", stale_token, "x")

    assert result.ok is False
    assert result.error_code == "invalid_selection"
    assert pipeline.steps == []
    assert controller.pipeline_version == before_version


def test_logistic_configuration_rolls_back_when_report_step_addition_fails() -> None:
    pipeline = Pipeline(_dataset())
    original_add = pipeline.add

    def fail_on_report(step: object) -> None:
        if getattr(step, "step_type", "") == "report.apa":
            raise RuntimeError("report failure")
        original_add(step)

    pipeline.add = fail_on_report  # type: ignore[method-assign]
    controller = UiController(pipeline=pipeline)
    before_version = controller.pipeline_version

    result = controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x",
    )

    assert result.ok is False
    assert result.error_code == "engine_error"
    assert pipeline.steps == []
    assert pipeline.current_dataset is pipeline.source_dataset
    assert controller.pipeline_version == before_version


def test_logistic_rerun_passes_run_validation_and_submits_worker() -> None:
    class _Future:
        def add_done_callback(self, callback) -> None:
            self.callback = callback

    class _Worker:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int, object]] = []

        def submit(self, *, run_id: int, pipeline_version: int, job: object) -> _Future:
            self.calls.append((run_id, pipeline_version, job))
            return _Future()

    pipeline = Pipeline(_dataset())
    worker = _Worker()
    controller = UiController(pipeline=pipeline, worker=worker)
    assert controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x",
    ).ok

    result = controller.rerun()

    assert result.ok is True
    assert len(worker.calls) == 1
    assert controller.status == "running"


def test_numeric_categorical_reference_survives_declared_missing_upcast() -> None:
    frame = pd.read_csv("tests/fixtures/logistic_regression/continuous.csv")
    frame["condition"] = [1, 2] * (len(frame) // 2)
    frame.loc[0, "condition"] = 99
    dataset = Dataset(
        df=frame,
        variables={
            "event": _variable("event", Measure.ORDINAL),
            "x1": _variable("x1", Measure.SCALE),
            "x2": _variable("x2", Measure.SCALE),
            "condition": _variable(
                "condition",
                Measure.NOMINAL,
                missing_values=[99.0],
            ),
        },
    )
    pipeline = Pipeline(dataset)
    controller = UiController(pipeline=pipeline)

    configured = controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x1, condition",
        {"condition": canonical_value_token(1)},
    )

    assert configured.ok is True
    result = pipeline.steps[0].compute_context_free(dataset).analysis
    assert result.diagnostics["categorical_predictors"]["condition"] == {
        "reference": "1",
        "levels": ["2", "1"],
    }


def test_real_logistic_pipeline_produces_display_charts_and_report(tmp_path) -> None:
    frame = pd.read_csv("tests/fixtures/logistic_regression/continuous.csv")
    dataset = Dataset(
        df=frame,
        variables={
            "event": _variable("event", Measure.ORDINAL),
            "x1": _variable("x1", Measure.SCALE),
            "x2": _variable("x2", Measure.SCALE),
        },
    )
    pipeline = Pipeline(dataset)
    controller = UiController(pipeline=pipeline)
    assert controller.configureLogisticRegression(
        "event",
        canonical_value_token(1),
        "x1, x2",
    ).ok
    pipeline.steps[1].params = {
        **pipeline.steps[1].params,
        "output_dir": str(tmp_path / "report"),
        "filename": "logistic.docx",
    }

    pipeline.recompute(dirty_from=None)
    displays = PipelineOperations(
        pipeline,
        chart_renderer=ChartAssetRenderer(chart_dir=tmp_path / "display-charts"),
    ).display_results()

    assert set(pipeline.analysis_objects) == {
        "logistic_regression",
        "analysis:logistic_regression",
        "report",
        "analysis:report",
        "report:report",
    }
    assert (tmp_path / "report" / "logistic.docx").is_file()
    assert len(displays) == 1
    display = displays[0]
    assert display.kind == "logistic_regression"
    assert display.title_ko == "이항 로지스틱 회귀"
    assert display.tables and display.tables[0].rows
    assert "사건(event)" in display.prose_ko
    assert len(display.chart_paths) == 3
    assert all(Path(path).is_file() for path in display.chart_paths)


def test_controller_exposes_configuration_required_recommendation_state() -> None:
    controller = UiController(pipeline=Pipeline(_dataset()))
    candidate = RecommendationCandidate(
        candidate_id="logistic-caution:event:x",
        kind="logistic_regression",
        title_ko="이항 로지스틱 회귀 후보",
        level="주의 필요",
        reason_ko="사건값 확인이 필요합니다.",
        outcome_key="event",
        predictor_keys=["x"],
        requires_configuration=True,
    )
    controller._recommendation_state = RecommendationState(
        candidates=[candidate],
        default_candidate=None,
        selected_candidate=candidate,
        message_ko="",
    )

    assert controller.recommendationKind == "logistic_regression"
    assert controller.recommendationRequiresConfiguration is True
    assert controller.preparedOutcomeKey == "event"
    assert controller.preparedPredictorKeys == "x"


def test_qml_uses_value_backed_logistic_selectors_without_free_text_values() -> None:
    guide = Path("src/modori/ui/qml/components/GuideRail.qml").read_text(
        encoding="utf-8"
    )
    pipeline = Path("src/modori/ui/qml/components/PipelineRail.qml").read_text(
        encoding="utf-8"
    )

    for source in (guide, pipeline):
        assert "configureLogisticRegressionFromTokens" in source
        assert "logisticOutcomeOptions" in source
        assert "logisticCategoricalReferenceOptions" in source
        assert "ComboBox" in source
        assert "logisticEventTokenField" not in source
        assert "logisticReferenceTokenField" not in source
    assert "recommendationCandidateRequiresConfigurationAt" in guide
    assert 'root.selectedIntent = "logistic_regression"' in guide
