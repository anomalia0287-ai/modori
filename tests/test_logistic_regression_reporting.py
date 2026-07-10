from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd

from modori.core import Dataset, Measure, PipelineContext, Variable
from modori.logistic_regression_reporting import (
    LOGISTIC_WARNING_TEXTS,
    prose_for_logistic,
    table_for_logistic,
    warnings_for_logistic,
)
from modori.logistic_regression_results import (
    LOGISTIC_WARNING_CODES,
    LogisticRegressionResult,
)
from modori.results import ReportResult
from modori.steps.logistic_regression import BinaryLogisticRegressionStep
from modori.steps.reporting import (
    ReportStep,
    _odds_ratio_ticks,
    prose_for,
    render_chart,
    table_for,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "logistic_regression"


def _frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_DIR / "continuous.csv")


def _dataset(frame: pd.DataFrame) -> Dataset:
    return Dataset(
        df=frame,
        variables={
            column: Variable(
                name=column,
                label=column,
                measure=Measure.ORDINAL if column == "event" else Measure.SCALE,
                value_labels={0: "비사건", 1: "사건"} if column == "event" else {},
                missing_values=[],
                dtype="float",
                origin_step_id="fixture",
            )
            for column in frame.columns
        },
    )


def _fit(
    frame: pd.DataFrame | None = None,
    *,
    predictors: list[str] | None = None,
    threshold: float = 0.5,
    calibration_bins: int = 10,
    language: str = "ko",
) -> LogisticRegressionResult:
    data = _frame() if frame is None else frame
    result = BinaryLogisticRegressionStep(
        id="logistic",
        title="Binary logistic regression",
        params={
            "schema_version": 1,
            "outcome": "event",
            "event_value": 1,
            "predictors": predictors or ["x1", "x2"],
            "logistic_policy": {
                "preset": "conservative",
                "classification_threshold": threshold,
                "calibration_bins": calibration_bins,
                "categorical_predictors": {},
            },
            "language": language,
        },
    ).compute_context_free(_dataset(data)).analysis
    assert isinstance(result, LogisticRegressionResult)
    return result


def test_logistic_warning_registry_has_korean_and_english_for_every_code() -> None:
    assert set(LOGISTIC_WARNING_TEXTS) == set(LOGISTIC_WARNING_CODES)
    for messages in LOGISTIC_WARNING_TEXTS.values():
        assert messages["ko"].strip()
        assert messages["en"].strip()


def test_engine_warning_codes_render_without_mixed_language() -> None:
    frame = _frame()
    frame.loc[[1, 8, 16, 24], "x2"] = None
    result = _fit(frame, language="en")

    assert "same_sample_metrics" in result.warning_codes
    assert "high_missing_fraction" in result.warning_codes
    assert result.warnings == warnings_for_logistic(result, language="en")
    assert all(message == LOGISTIC_WARNING_TEXTS[code]["en"] for code, message in zip(
        result.warning_codes,
        result.warnings,
        strict=True,
    ))


def test_logistic_chart_titles_and_axes_follow_result_language() -> None:
    korean = _fit(language="ko")
    english = _fit(language="en")

    assert [spec.title for spec in korean.chart_specs] == [
        "승산비",
        "표본 내 ROC 곡선",
        "표본 내 기술적 보정",
    ]
    assert korean.chart_specs[0].x_label == "승산비"
    assert korean.chart_specs[2].y_label == "관측 사건 비율"
    assert [spec.title for spec in english.chart_specs] == [
        "Odds ratios",
        "In-sample ROC curve",
        "In-sample descriptive calibration",
    ]


def test_logistic_prose_reports_event_direction_and_association_without_overclaim() -> None:
    result = _fit()

    korean = prose_for_logistic(result, language="ko")
    english = prose_for_logistic(result, language="en")

    assert "사건(event) = 사건(1)" in korean
    assert "비사건 = 비사건(0)" in korean
    assert "LR χ²(2)" in korean
    assert "OR =" in korean
    assert "분류 임계값 = .50" in korean
    assert "x1:" in korean
    assert "x1는" not in korean
    assert "Brier 점수 = .21로 나타났다" in korean
    assert "동일 자료" in korean
    assert "외부 예측 성능을 입증하지" in korean
    assert "원인이었다" not in korean
    assert "유발하였다" not in korean
    assert "검증된 예측 정확도" not in korean

    assert "the event was coded as 사건 (1)" in english
    assert "the non-event as 비사건 (0)" in english
    assert "LR χ²(2)" in english
    assert "OR =" in english
    assert "classification threshold = .50" in english
    assert "in-sample descriptive" in english
    assert "do not establish out-of-sample predictive performance" in english
    assert "caused" not in english
    assert "validated prediction" not in english

    assert result.warning_codes
    assert len(result.warning_codes) == len(result.warnings)
    for warning in warnings_for_logistic(result, language="ko"):
        assert warning in korean
    for warning in warnings_for_logistic(result, language="en"):
        assert warning in english


def test_logistic_reporting_dispatch_and_coefficient_table_preserve_or_intervals() -> None:
    result = _fit()

    rows = table_for_logistic(result)

    assert prose_for(result, language="ko") == prose_for_logistic(result, language="ko")
    assert table_for(result) == rows
    assert [row["term"] for row in rows] == ["(Intercept)", "x1", "x2"]
    assert rows[1]["odds ratio"]
    assert rows[1]["95% CI (OR)"].startswith("[")
    assert rows[1]["95% CI (b)"].startswith("[")
    assert rows[1]["Wald z"]
    assert rows[1]["p"]


def test_logistic_prose_discloses_undefined_metrics_and_suppressed_calibration() -> None:
    undefined = _fit(threshold=0.999999)
    assert undefined.classification.positive_predictive_value is None
    assert all(".:" not in warning for warning in undefined.warnings)
    undefined_warning = undefined.warnings[
        undefined.warning_codes.index("undefined_classification_metrics")
    ]
    assert "양성예측도" in undefined_warning
    assert "positive_predictive_value" not in undefined_warning
    assert "양성예측도는 정의되지 않습니다" in prose_for_logistic(undefined, "ko")
    assert "positive predictive value is undefined" in prose_for_logistic(
        undefined,
        "en",
    )

    frame = _frame()
    frame["binary_x"] = [0, 1] * 30
    suppressed = _fit(frame, predictors=["binary_x"])
    assert suppressed.calibration_bins == ()
    assert "보정 구간 표와 그림을 생략" in prose_for_logistic(suppressed, "ko")
    assert "calibration table and plot were omitted" in prose_for_logistic(
        suppressed,
        "en",
    )


def test_report_step_renders_all_logistic_chart_specs(tmp_path: Path) -> None:
    result = _fit()
    assert [spec.type for spec in result.chart_specs] == [
        "odds_ratio_forest",
        "roc_curve",
        "calibration_plot",
    ]
    step = ReportStep(
        id="report",
        title="APA report",
        params={
            "include": ["logistic"],
            "output_dir": str(tmp_path),
            "filename": "logistic.docx",
            "language": "ko",
        },
    )

    report = step.compute(
        PipelineContext(dataset=Dataset.empty(), analyses={"logistic": result})
    ).analysis

    assert isinstance(report, ReportResult)
    assert Path(report.docx_path).is_file()
    paths = [Path(path) for path in report.figure_paths["logistic"]]
    assert len(paths) == 9
    assert sorted(path.suffix for path in paths) == [
        ".eps",
        ".eps",
        ".eps",
        ".png",
        ".png",
        ".png",
        ".svg",
        ".svg",
        ".svg",
    ]
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)


def test_odds_ratio_forest_renders_without_missing_log_tick_glyphs(
    tmp_path: Path,
) -> None:
    odds_ratio_chart = _fit().chart_specs[0]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        render_chart(odds_ratio_chart, tmp_path / "odds-ratio.png")

    assert not [
        warning
        for warning in caught
        if "does not have a glyph" in str(warning.message)
    ]


def test_odds_ratio_log_ticks_use_plain_ascii_labels() -> None:
    ticks, labels = _odds_ratio_ticks(0.22, 2.40)

    assert ticks == [0.5, 1.0, 2.0]
    assert labels == ["0.5", "1", "2"]
    assert all("−" not in label and "^" not in label for label in labels)


def test_report_step_cleans_earlier_logistic_charts_when_later_chart_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    result = _fit()
    output_dir = tmp_path / "report-output"
    calls = 0

    def fail_on_second_chart(spec, chart_dir, key=None):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("second logistic chart failed")
        path = Path(chart_dir) / f"{key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"generated chart")
        return str(path)

    monkeypatch.setattr("modori.steps.reporting.render_chart", fail_on_second_chart)
    step = ReportStep(
        id="report",
        title="APA report",
        params={
            "include": ["logistic"],
            "output_dir": str(output_dir),
            "filename": "logistic.docx",
            "language": "ko",
        },
    )

    try:
        step.compute(
            PipelineContext(dataset=Dataset.empty(), analyses={"logistic": result})
        )
    except ValueError as exc:
        assert "second logistic chart failed" in str(exc)
    else:
        raise AssertionError("The second chart failure was not propagated")

    assert not list(tmp_path.rglob("*.png"))
    assert not (output_dir / "logistic.docx").exists()
