from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.logistic_regression_results import LogisticRegressionResult
from modori.steps import (
    AncovaStep,
    BinaryLogisticRegressionStep,
    CompareGroupsStep,
    CorrelationStep,
    DescriptivesTableStep,
    FactorPcaStep,
    FrequencyCrosstabStep,
    FriedmanStep,
    KruskalWallisStep,
    MediationStep,
    ModeratedMediationStep,
    MultipleRegressionStep,
    OneWayAnovaStep,
    PairedComparisonStep,
    ReliabilityStep,
    RepeatedMeasuresAnovaStep,
)


def v1_statistics_smoke_payload() -> dict[str, object]:
    checks = [_run_check(key, factory) for key, factory in _CHECK_FACTORIES]
    return {
        "ok": all(bool(check["ok"]) for check in checks),
        "checks": checks,
    }


def _run_check(key: str, factory: Callable[[], tuple[object, Dataset, Callable[[Any], None]]]) -> dict[str, object]:
    try:
        step, dataset, assert_result = factory()
        result = step.compute_context_free(dataset).analysis
        if result is None:
            raise ValueError(f"{key} did not produce an analysis result")
        assert_result(result)
        return {
            "key": key,
            "ok": True,
            "analysis_type": type(result).__name__,
        }
    except Exception as exc:
        return {
            "key": key,
            "ok": False,
            "analysis_type": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _dataset(
    rows: list[dict[str, object]],
    measures: dict[str, Measure],
    *,
    labels: dict[str, str] | None = None,
    value_labels: dict[str, dict[object, str]] | None = None,
) -> Dataset:
    frame = pd.DataFrame(rows)
    labels = {} if labels is None else labels
    value_labels = {} if value_labels is None else value_labels
    variables = {
        column: Variable(
            name=column,
            label=labels.get(column, column),
            measure=measures.get(column, Measure.SCALE),
            value_labels=value_labels.get(column, {}),
            missing_values=[],
            dtype="float" if pd.api.types.is_numeric_dtype(frame[column]) else "string",
            origin_step_id=None,
        )
        for column in frame.columns
    }
    return Dataset(df=frame, variables=variables)


def _scale_dataset(frame: pd.DataFrame, *, nominal: set[str] | None = None) -> Dataset:
    nominal = set() if nominal is None else nominal
    rows = frame.to_dict(orient="records")
    measures = {
        column: (Measure.NOMINAL if column in nominal else Measure.SCALE)
        for column in frame.columns
    }
    return _dataset(rows, measures)


def _assert_test_name(expected: str) -> Callable[[Any], None]:
    def assert_result(result: Any) -> None:
        if getattr(result, "test_name", None) != expected:
            raise ValueError(f"expected {expected}, got {getattr(result, 'test_name', None)}")

    return assert_result


def _assert_noop(_result: Any) -> None:
    return None


def _assert_factor_method(expected: str) -> Callable[[Any], None]:
    def assert_result(result: Any) -> None:
        if getattr(result, "method", None) != expected:
            raise ValueError(f"expected {expected}, got {getattr(result, 'method', None)}")

    return assert_result


def _assert_regression_interaction(result: Any) -> None:
    if not getattr(result, "simple_slopes", None):
        raise ValueError("regression interaction smoke did not produce simple slopes")


def _assert_logistic_result(result: Any) -> None:
    if not isinstance(result, LogisticRegressionResult):
        raise ValueError(
            f"expected LogisticRegressionResult, got {type(result).__name__}"
        )
    if not np.isfinite(result.likelihood_ratio_chi_square):
        raise ValueError("logistic omnibus statistic is not finite")
    if not result.coefficients:
        raise ValueError("logistic smoke did not produce coefficient rows")
    for row in result.coefficients:
        if not all(np.isfinite(value) for value in (row.b, row.se, row.p_value)):
            raise ValueError(f"logistic coefficient row is not finite: {row.name}")
    classification = result.classification
    classified = classification.tn + classification.fp + classification.fn + classification.tp
    if classified != result.n_obs:
        raise ValueError(
            f"logistic classification counts cover {classified}, expected {result.n_obs}"
        )
    if not isinstance(result.warning_codes, tuple) or not isinstance(result.warnings, tuple):
        raise ValueError("logistic warning disclosure is not immutable")
    if len(result.warning_codes) != len(result.warnings):
        raise ValueError("logistic warning codes and messages do not align")


def _assert_positive_attr(attribute: str) -> Callable[[Any], None]:
    def assert_result(result: Any) -> None:
        value = getattr(result, attribute, None)
        if value is None or not np.isfinite(float(value)) or float(value) <= 0:
            raise ValueError(f"expected positive finite {attribute}, got {value}")

    return assert_result


def _assert_finite_attr(attribute: str) -> Callable[[Any], None]:
    def assert_result(result: Any) -> None:
        value = getattr(result, attribute, None)
        if value is None or not np.isfinite(float(value)):
            raise ValueError(f"expected finite {attribute}, got {value}")

    return assert_result


def _assert_non_empty_attr(attribute: str) -> Callable[[Any], None]:
    def assert_result(result: Any) -> None:
        if not getattr(result, attribute, None):
            raise ValueError(f"expected non-empty {attribute}")

    return assert_result


def _descriptives_check() -> tuple[DescriptivesTableStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            {"group": "A", "age": 22.0, "gender": "F"},
            {"group": "A", "age": 24.0, "gender": "M"},
            {"group": "B", "age": 31.0, "gender": "F"},
            {"group": "B", "age": 35.0, "gender": "M"},
        ],
        {"group": Measure.NOMINAL, "age": Measure.SCALE, "gender": Measure.NOMINAL},
    )
    return (
        DescriptivesTableStep(
            id="smoke-descriptives-table1",
            title="Smoke descriptives",
            params={
                "schema_version": 1,
                "variables": ["gender", "age"],
                "group": "group",
            },
        ),
        dataset,
        _assert_noop,
    )


def _reliability_check() -> tuple[ReliabilityStep, Dataset, Callable[[Any], None]]:
    dataset = _scale_dataset(
        pd.DataFrame(
            {
                "q1": [3, 3, 4, 4, 5, 5, 2, 3, 4, 5],
                "q2": [3, 4, 4, 5, 5, 4, 2, 3, 4, 5],
                "q3": [2, 3, 4, 4, 5, 5, 2, 3, 5, 4],
                "q4": [3, 3, 5, 4, 5, 4, 2, 4, 4, 5],
            }
        )
    )
    return (
        ReliabilityStep(
            id="smoke-reliability",
            title="Smoke reliability",
            params={"schema_version": 1, "items": ["q1", "q2", "q3", "q4"], "scale_name": "q"},
        ),
        dataset,
        _assert_noop,
    )


def _frequency_check() -> tuple[FrequencyCrosstabStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [{"gender": value} for value in ["F", "M", "F", "F", "M", "M"]],
        {"gender": Measure.NOMINAL},
    )
    return (
        FrequencyCrosstabStep(
            id="smoke-frequency",
            title="Smoke frequency",
            params={"schema_version": 1, "mode": "frequency", "variables": ["gender"]},
        ),
        dataset,
        _assert_noop,
    )


def _crosstab_fisher_check() -> tuple[FrequencyCrosstabStep, Dataset, Callable[[Any], None]]:
    rows = [{"group": "A", "event": "yes"}] * 8
    rows.extend(
        [
            {"group": "A", "event": "no"},
            {"group": "B", "event": "yes"},
            {"group": "B", "event": "no"},
        ]
    )
    dataset = _dataset(rows, {"group": Measure.NOMINAL, "event": Measure.NOMINAL})
    return (
        FrequencyCrosstabStep(
            id="smoke-crosstab",
            title="Smoke crosstab",
            params={
                "schema_version": 1,
                "mode": "crosstab",
                "row_variable": "group",
                "column_variable": "event",
            },
        ),
        dataset,
        _assert_noop,
    )


def _pearson_check() -> tuple[CorrelationStep, Dataset, Callable[[Any], None]]:
    dataset = _scale_dataset(pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 4, 5, 8, 11]}))
    return (
        CorrelationStep(
            id="smoke-pearson",
            title="Smoke Pearson",
            params={"schema_version": 1, "pairs": [["x", "y"]], "method": "pearson"},
        ),
        dataset,
        _assert_noop,
    )


def _spearman_check() -> tuple[CorrelationStep, Dataset, Callable[[Any], None]]:
    dataset = _scale_dataset(
        pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "ranked": [1, 1, 3, 4, 6, 5]})
    )
    return (
        CorrelationStep(
            id="smoke-spearman",
            title="Smoke Spearman",
            params={"schema_version": 1, "pairs": [["x", "ranked"]], "method": "spearman"},
        ),
        dataset,
        _assert_noop,
    )


def _welch_check() -> tuple[CompareGroupsStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            *({"group": "A", "score": value} for value in [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]),
            *({"group": "B", "score": value} for value in [20.0, 22.0, 23.0, 25.0, 28.0, 31.0]),
        ],
        {"group": Measure.NOMINAL, "score": Measure.SCALE},
    )
    return (
        CompareGroupsStep(
            id="smoke-welch",
            title="Smoke Welch",
            params={
                "schema_version": 1,
                "dv": "score",
                "group": "group",
                "routing_policy": {"preset": "always_welch"},
            },
        ),
        dataset,
        _assert_test_name("welch_t"),
    )


def _mann_whitney_check() -> tuple[CompareGroupsStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            *({"group": "A", "score": value} for value in [1.0, 1.2, 1.3, 1.5, 18.0, 20.0]),
            *({"group": "B", "score": value} for value in [3.0, 3.2, 3.4, 3.6, 4.0, 22.0]),
        ],
        {"group": Measure.NOMINAL, "score": Measure.SCALE},
    )
    return (
        CompareGroupsStep(
            id="smoke-mann-whitney",
            title="Smoke Mann-Whitney",
            params={
                "schema_version": 1,
                "dv": "score",
                "group": "group",
                "routing_policy": {"preset": "modern", "normality_p": 0.999},
            },
        ),
        dataset,
        _assert_test_name("mann_whitney"),
    )


def _paired_t_check() -> tuple[PairedComparisonStep, Dataset, Callable[[Any], None]]:
    dataset = _scale_dataset(
        pd.DataFrame(
            {
                "pre": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
                "post": [11.0, 12.5, 13.2, 14.4, 15.3, 16.2],
            }
        )
    )
    return (
        PairedComparisonStep(
            id="smoke-paired-t",
            title="Smoke paired t",
            params={
                "schema_version": 1,
                "before": "pre",
                "after": "post",
                "routing_policy": {"preset": "classic"},
            },
        ),
        dataset,
        _assert_test_name("paired_t"),
    )


def _wilcoxon_check() -> tuple[PairedComparisonStep, Dataset, Callable[[Any], None]]:
    dataset = _scale_dataset(
        pd.DataFrame(
            {
                "pre": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
                "post": [11.0, 10.5, 14.0, 15.5, 14.5, 18.0],
            }
        )
    )
    return (
        PairedComparisonStep(
            id="smoke-wilcoxon",
            title="Smoke Wilcoxon",
            params={
                "schema_version": 1,
                "before": "pre",
                "after": "post",
                "routing_policy": {"preset": "always_wilcoxon"},
            },
        ),
        dataset,
        _assert_test_name("wilcoxon"),
    )


def _anova_check() -> tuple[OneWayAnovaStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            *({"arm": "A", "score": value} for value in [9.0, 10.0, 11.0, 12.0]),
            *({"arm": "B", "score": value} for value in [13.0, 14.0, 15.0, 16.0]),
            *({"arm": "C", "score": value} for value in [18.0, 19.0, 20.0, 21.0]),
        ],
        {"arm": Measure.NOMINAL, "score": Measure.SCALE},
    )
    return (
        OneWayAnovaStep(
            id="smoke-anova",
            title="Smoke ANOVA",
            params={"schema_version": 1, "dv": "score", "group": "arm", "posthoc": "auto"},
        ),
        dataset,
        _assert_noop,
    )


def _kruskal_check() -> tuple[KruskalWallisStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            *({"arm": "A", "score": value} for value in [9.0, 10.0, 11.0]),
            *({"arm": "B", "score": value} for value in [1.0, 2.0, 3.0]),
            *({"arm": "C", "score": value} for value in [7.0, 8.0, 12.0]),
        ],
        {"arm": Measure.NOMINAL, "score": Measure.SCALE},
    )
    return (
        KruskalWallisStep(
            id="smoke-kruskal",
            title="Smoke Kruskal",
            params={"schema_version": 1, "dependent": "score", "group": "arm"},
        ),
        dataset,
        _assert_noop,
    )


def _ancova_check() -> tuple[AncovaStep, Dataset, Callable[[Any], None]]:
    dataset = _dataset(
        [
            {"group": 2.0, "pretest": 3.0, "outcome": 18.7},
            {"group": 1.0, "pretest": 2.0, "outcome": 12.5},
            {"group": 3.0, "pretest": 5.0, "outcome": 23.1},
            {"group": 2.0, "pretest": 4.0, "outcome": 19.7},
            {"group": 1.0, "pretest": 3.0, "outcome": 13.5},
            {"group": 3.0, "pretest": 6.0, "outcome": 24.1},
            {"group": 2.0, "pretest": 5.0, "outcome": 21.05},
            {"group": 1.0, "pretest": 4.0, "outcome": 14.85},
            {"group": 3.0, "pretest": 7.0, "outcome": 25.45},
            {"group": 2.0, "pretest": 6.0, "outcome": 22.15},
            {"group": 1.0, "pretest": 5.0, "outcome": 15.95},
            {"group": 3.0, "pretest": 8.0, "outcome": 26.55},
        ],
        {"group": Measure.NOMINAL, "pretest": Measure.SCALE, "outcome": Measure.SCALE},
    )
    return (
        AncovaStep(
            id="smoke-ancova",
            title="Smoke ANCOVA",
            params={
                "schema_version": 1,
                "dv": "outcome",
                "group": "group",
                "covariates": ["pretest"],
            },
        ),
        dataset,
        _assert_noop,
    )


def _repeated_measures_dataset() -> Dataset:
    return _scale_dataset(
        pd.DataFrame(
            {
                "time1": [10.0, 11.0, 9.0, 12.0, 13.0, 8.0, 14.0, 10.5],
                "time2": [12.0, 12.0, 10.0, 13.5, 14.2, 9.5, 14.8, 12.0],
                "time3": [13.5, 13.2, 11.5, 15.0, 15.7, 10.2, 16.0, 13.1],
            }
        )
    )


def _repeated_measures_anova_check() -> tuple[
    RepeatedMeasuresAnovaStep,
    Dataset,
    Callable[[Any], None],
]:
    return (
        RepeatedMeasuresAnovaStep(
            id="smoke-repeated-measures-anova",
            title="Smoke repeated measures ANOVA",
            params={
                "schema_version": 1,
                "measures": ["time1", "time2", "time3"],
                "within_factor": "time",
                "level_labels": ["time1", "time2", "time3"],
                "correction": "auto",
                "sphericity_alpha": 0.05,
                "language": "ko",
            },
        ),
        _repeated_measures_dataset(),
        _assert_positive_attr("f_statistic"),
    )


def _friedman_check() -> tuple[FriedmanStep, Dataset, Callable[[Any], None]]:
    return (
        FriedmanStep(
            id="smoke-friedman",
            title="Smoke Friedman",
            params={
                "schema_version": 1,
                "measures": ["time1", "time2", "time3"],
                "within_factor": "time",
                "level_labels": ["time1", "time2", "time3"],
                "posthoc_method": "none",
                "p_adjust": "none",
                "language": "ko",
            },
        ),
        _repeated_measures_dataset(),
        _assert_finite_attr("kendalls_w"),
    )


def _mediation_frame() -> pd.DataFrame:
    x = np.linspace(-2.5, 3.0, 28)
    c1 = np.array([0.2, -0.4, 0.1, 0.6, -0.2, 0.3, -0.1] * 4)
    m_noise = np.array(
        [
            0.10,
            -0.08,
            0.04,
            0.12,
            -0.06,
            0.02,
            -0.04,
            0.05,
            -0.03,
            0.07,
            -0.09,
            0.11,
            -0.02,
            0.08,
            -0.05,
            0.06,
            -0.07,
            0.03,
            0.09,
            -0.11,
            0.01,
            0.04,
            -0.06,
            0.10,
            -0.08,
            0.05,
            -0.03,
            0.07,
        ]
    )
    y_noise = np.array(
        [
            -0.12,
            0.04,
            -0.03,
            0.08,
            -0.05,
            0.06,
            -0.01,
            0.09,
            -0.10,
            0.02,
            0.07,
            -0.04,
            0.05,
            -0.08,
            0.11,
            -0.02,
            0.03,
            -0.07,
            0.10,
            -0.06,
            0.04,
            -0.03,
            0.08,
            -0.09,
            0.02,
            0.06,
            -0.05,
            0.07,
        ]
    )
    mediator = 1.0 + 0.65 * x + 0.25 * c1 + m_noise
    y = 2.0 + 0.35 * x + 0.8 * mediator + 0.15 * c1 + y_noise
    return pd.DataFrame({"x": x, "m": mediator, "y": y, "c1": c1})


def _mediation_check() -> tuple[MediationStep, Dataset, Callable[[Any], None]]:
    return (
        MediationStep(
            id="smoke-mediation",
            title="Smoke mediation",
            params={
                "schema_version": 1,
                "x": "x",
                "mediator": "m",
                "y": "y",
                "covariates": ["c1"],
                "bootstrap": {"iterations": 60, "seed": 20260708, "ci": 0.95},
                "standardize": False,
                "language": "ko",
            },
        ),
        _scale_dataset(_mediation_frame()),
        _assert_positive_attr("indirect_effect"),
    )


def _moderated_mediation_frame() -> pd.DataFrame:
    x = np.linspace(-3.0, 3.0, 32)
    w = np.array([-1.4, -0.8, 0.2, 1.1, -1.1, -0.4, 0.6, 1.5] * 4)
    c1 = np.array([0.2, -0.3, 0.4, -0.1] * 8)
    x_centered = x - x.mean()
    w_centered = w - w.mean()
    m_noise = np.array([0.04, -0.03, 0.05, -0.04, 0.02, -0.01, 0.03, -0.02] * 4)
    y_noise = np.array([-0.05, 0.04, -0.02, 0.03, -0.01, 0.02, -0.04, 0.05] * 4)
    mediator = (
        1.0
        + 0.55 * x_centered
        + 0.25 * w_centered
        + 0.35 * x_centered * w_centered
        + 0.2 * c1
        + m_noise
    )
    y = (
        2.0
        + 0.28 * x_centered
        + 0.72 * mediator
        + 0.22 * w_centered
        + 0.31 * mediator * w_centered
        + 0.12 * c1
        + y_noise
    )
    return pd.DataFrame({"x": x, "w": w, "m": mediator, "y": y, "c1": c1})


def _moderated_mediation_check() -> tuple[
    ModeratedMediationStep,
    Dataset,
    Callable[[Any], None],
]:
    return (
        ModeratedMediationStep(
            id="smoke-moderated-mediation",
            title="Smoke moderated mediation",
            params={
                "schema_version": 1,
                "model": 7,
                "x": "x",
                "mediator": "m",
                "moderator": "w",
                "y": "y",
                "covariates": ["c1"],
                "bootstrap": {"iterations": 60, "seed": 20260708, "ci": 0.95},
                "moderator_values": "mean_sd",
                "center": "mean",
                "language": "ko",
            },
        ),
        _scale_dataset(_moderated_mediation_frame()),
        _assert_non_empty_attr("conditional_effects"),
    )


def _factor_dataset() -> Dataset:
    rng = np.random.default_rng(20260708)
    f1 = rng.normal(size=80)
    f2 = rng.normal(size=80)
    frame = pd.DataFrame(
        {
            "q1": f1 + rng.normal(scale=0.2, size=80),
            "q2": 0.8 * f1 + rng.normal(scale=0.25, size=80),
            "q3": f2 + rng.normal(scale=0.2, size=80),
            "q4": 0.75 * f2 + rng.normal(scale=0.25, size=80),
            "q5": 0.45 * f1 + 0.45 * f2 + rng.normal(scale=0.3, size=80),
        }
    )
    return _scale_dataset(frame)


def _factor_pca_check() -> tuple[FactorPcaStep, Dataset, Callable[[Any], None]]:
    return (
        FactorPcaStep(
            id="smoke-factor-pca",
            title="Smoke PCA",
            params={
                "schema_version": 1,
                "variables": ["q1", "q2", "q3", "q4", "q5"],
                "method": "pca",
                "missing_policy": "listwise",
                "rotation": "none",
                "parallel_analysis": {"seed": 20260708, "iterations": 20, "percentile": 95.0},
            },
        ),
        _factor_dataset(),
        _assert_factor_method("pca"),
    )


def _factor_efa_check() -> tuple[FactorPcaStep, Dataset, Callable[[Any], None]]:
    return (
        FactorPcaStep(
            id="smoke-factor-efa",
            title="Smoke EFA",
            params={
                "schema_version": 1,
                "variables": ["q1", "q2", "q3", "q4", "q5"],
                "method": "efa",
                "factor_count": 2,
                "missing_policy": "listwise",
                "rotation": "varimax",
                "extraction_method": "minres",
                "parallel_analysis": {"seed": 20260708, "iterations": 20, "percentile": 95.0},
            },
        ),
        _factor_dataset(),
        _assert_factor_method("efa"),
    )


def _regression_interaction_check() -> tuple[MultipleRegressionStep, Dataset, Callable[[Any], None]]:
    x = np.array([1.0, 2.0, 3.5, 4.0, 5.0, 6.5, 7.0, 8.0, 9.5, 10.0, 11.0, 12.5])
    group = np.array(
        [
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
            "control",
            "treat",
            "placebo",
        ]
    )
    intercept = {"control": 0.0, "treat": 1.0, "placebo": -0.5}
    slope = {"control": 0.4, "treat": 1.2, "placebo": -0.1}
    noise = np.array([0.12, -0.04, 0.07, -0.1, 0.05, -0.03, 0.09, -0.06, 0.04, -0.08, 0.03, -0.05])
    y = 3.0 + np.array([intercept[value] for value in group])
    y = y + np.array([slope[value] for value in group]) * x + noise
    dataset = _scale_dataset(pd.DataFrame({"y": y, "x": x, "group": group}), nominal={"group"})
    return (
        MultipleRegressionStep(
            id="smoke-regression-interaction",
            title="Smoke regression interaction",
            params={
                "schema_version": 1,
                "dv": "y",
                "predictors": ["x", "group"],
                "regression_policy": {
                    "preset": "classic",
                    "categorical_predictors": {
                        "group": {
                            "reference": "control",
                            "levels": ["control", "treat", "placebo"],
                        }
                    },
                    "center_scale_interactions": "mean",
                    "interactions": [{"terms": ["x", "group"]}],
                },
            },
        ),
        dataset,
        _assert_regression_interaction,
    )


def _logistic_regression_check() -> tuple[
    BinaryLogisticRegressionStep,
    Dataset,
    Callable[[Any], None],
]:
    event_counts = {
        -2.0: {-1.0: 2, 0.0: 1, 1.0: 1},
        -1.0: {-1.0: 2, 0.0: 1, 1.0: 1},
        0.0: {-1.0: 3, 0.0: 3, 1.0: 1},
        1.0: {-1.0: 3, 0.0: 3, 1.0: 2},
        2.0: {-1.0: 3, 0.0: 3, 1.0: 2},
    }
    rows = [
        {"event": int(replicate < event_counts[x1][x2]), "x1": x1, "x2": x2}
        for x1 in (-2.0, -1.0, 0.0, 1.0, 2.0)
        for x2 in (-1.0, 0.0, 1.0)
        for replicate in range(4)
    ]
    dataset = _dataset(
        rows,
        {"event": Measure.NOMINAL, "x1": Measure.SCALE, "x2": Measure.SCALE},
        value_labels={"event": {0: "non-event", 1: "event"}},
    )
    return (
        BinaryLogisticRegressionStep(
            id="smoke-logistic-regression",
            title="Smoke binary logistic regression",
            params={
                "schema_version": 1,
                "outcome": "event",
                "event_value": 1,
                "predictors": ["x1", "x2"],
                "logistic_policy": {
                    "preset": "conservative",
                    "classification_threshold": 0.5,
                    "calibration_bins": 10,
                    "categorical_predictors": {},
                },
                "language": "ko",
            },
        ),
        dataset,
        _assert_logistic_result,
    )


_CHECK_FACTORIES: tuple[tuple[str, Callable[[], tuple[object, Dataset, Callable[[Any], None]]]], ...] = (
    ("descriptives_table1", _descriptives_check),
    ("reliability", _reliability_check),
    ("frequency", _frequency_check),
    ("crosstab_fisher", _crosstab_fisher_check),
    ("pearson_correlation", _pearson_check),
    ("spearman_correlation", _spearman_check),
    ("welch_t", _welch_check),
    ("mann_whitney", _mann_whitney_check),
    ("paired_t", _paired_t_check),
    ("wilcoxon", _wilcoxon_check),
    ("anova_oneway", _anova_check),
    ("kruskal_wallis", _kruskal_check),
    ("ancova", _ancova_check),
    ("repeated_measures_anova", _repeated_measures_anova_check),
    ("friedman", _friedman_check),
    ("mediation", _mediation_check),
    ("moderated_mediation", _moderated_mediation_check),
    ("factor_pca_pca", _factor_pca_check),
    ("factor_pca_efa", _factor_efa_check),
    ("regression_categorical_interaction", _regression_interaction_check),
    ("logistic_regression", _logistic_regression_check),
)
