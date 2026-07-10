from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from modori.results import ChartSpec


LOGISTIC_WARNING_TEXTS: dict[str, dict[str, str]] = {
    "same_sample_metrics": {
        "ko": "분류와 보정 지표는 동일 자료에서 계산한 기술적 요약이며 외부 예측 성능을 입증하지 않습니다.",
        "en": "Classification and calibration are in-sample descriptive summaries and do not establish out-of-sample predictive performance.",
    },
    "small_outcome_class": {
        "ko": "사건 또는 비사건이 20건 미만이므로 점근 추론이 불안정할 수 있습니다.",
        "en": "The event or non-event class has fewer than 20 observations, so asymptotic inference may be unstable.",
    },
    "low_events_per_parameter": {
        "ko": "더 작은 결과 범주의 비절편 모수당 관측 수가 10 미만입니다.",
        "en": "The smaller outcome class has fewer than 10 observations per non-intercept parameter.",
    },
    "high_missing_fraction": {
        "ko": "결측값의 목록별 제거로 전체 행의 5%를 초과해 제외했습니다.",
        "en": "Listwise deletion excluded more than 5% of all rows.",
    },
    "undefined_classification_metrics": {
        "ko": "선택한 분류 임계값에서 일부 분류 지표의 분모가 0이므로 정의되지 않습니다.",
        "en": "One or more classification metrics are undefined at the selected threshold because their denominator is zero.",
    },
    "high_information_condition": {
        "ko": "로지스틱 정보행렬의 조건수가 높아 추론이 수치적으로 민감합니다.",
        "en": "The logistic information matrix has a high condition number, so inference is numerically sensitive.",
    },
    "extreme_fitted_probabilities": {
        "ko": "일부 적합확률이 0 또는 1에 매우 가까워 추론이 민감할 수 있습니다.",
        "en": "Some fitted probabilities are very close to zero or one, so inference may be sensitive.",
    },
    "large_predictor_offset": {
        "ko": "예측변수의 큰 오프셋 때문에 원척도 절편은 소거에 민감한 외삽값입니다. 확률 계산은 안정화된 경로를 사용했습니다.",
        "en": "A large predictor offset makes the original-scale intercept a cancellation-sensitive extrapolation. Probability calculations used the stabilized path.",
    },
    "intercept_odds_ratio_undefined": {
        "ko": "원척도 절편의 승산비는 부동소수점 범위를 벗어나 정의하지 않았습니다.",
        "en": "The original-scale intercept odds ratio is undefined because it exceeds the floating-point range.",
    },
    "calibration_suppressed": {
        "ko": "서로 다른 적합확률이 부족해 보정 구간 표와 그림을 생략했습니다.",
        "en": "The calibration table and plot were omitted because there were too few distinct fitted probabilities.",
    },
    "calibration_sparse": {
        "ko": "유효 보정 구간이 5개 미만이므로 보정 요약이 거칩니다.",
        "en": "The calibration summary is coarse because fewer than five effective bins were available.",
    },
}
LOGISTIC_WARNING_CODES = frozenset(LOGISTIC_WARNING_TEXTS)
LOGISTIC_CLASSIFICATION_METRIC_LABELS: dict[str, dict[str, str]] = {
    "ko": {
        "sensitivity": "민감도",
        "specificity": "특이도",
        "positive_predictive_value": "양성예측도",
        "negative_predictive_value": "음성예측도",
    },
    "en": {
        "sensitivity": "sensitivity",
        "specificity": "specificity",
        "positive_predictive_value": "positive predictive value",
        "negative_predictive_value": "negative predictive value",
    },
}


def render_logistic_warning(
    code: str,
    language: str,
    *,
    detail: str | None = None,
) -> str:
    if code not in LOGISTIC_WARNING_TEXTS:
        raise ValueError(f"Unknown logistic warning code: {code}")
    language_base = str(language).lower().split("-")[0]
    if language_base not in {"ko", "en"}:
        raise ValueError("Logistic warning language must be Korean or English")
    message = LOGISTIC_WARNING_TEXTS[code][language_base]
    return f"{message.rstrip('.')}: {detail}" if detail else message


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _probability(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    result = _finite(value, label)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _count(value: int, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} confusion counts must be nonnegative integers")
    return value


def _ordered_pair(
    value: tuple[float, float],
    label: str,
    *,
    positive: bool = False,
) -> tuple[float, float]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError(f"{label} must be a two-value tuple")
    lower = _finite(value[0], f"{label} lower")
    upper = _finite(value[1], f"{label} upper")
    if lower > upper:
        raise ValueError(f"{label} limits must be ordered")
    if positive and lower <= 0:
        raise ValueError(f"{label} limits must be positive")
    return lower, upper


@dataclass(frozen=True)
class LogisticCoefficientRow:
    name: str
    b: float
    se: float
    wald_z: float
    wald_chi_square: float
    p_value: float
    odds_ratio: float | None
    ci: tuple[float, float]
    odds_ratio_ci: tuple[float, float] | None
    term_type: str = "term"
    source_variable: str | None = None
    level: str | None = None
    reference_level: str | None = None
    components: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Logistic coefficient name must be non-empty")
        b = _finite(self.b, "Logistic coefficient")
        se = _finite(self.se, "Logistic coefficient standard error")
        z_value = _finite(self.wald_z, "Logistic Wald z")
        chi_square = _finite(self.wald_chi_square, "Logistic Wald chi-square")
        p_value = _probability(self.p_value, "Logistic coefficient p-value")
        ci = _ordered_pair(self.ci, "Logistic coefficient CI")
        odds_ratio: float | None
        odds_ratio_ci: tuple[float, float] | None
        if self.odds_ratio is None or self.odds_ratio_ci is None:
            if self.odds_ratio is not None or self.odds_ratio_ci is not None:
                raise ValueError("Logistic odds ratio and CI must both be defined or undefined")
            if self.term_type != "intercept":
                raise ValueError("Only the logistic intercept may have an undefined odds ratio")
            odds_ratio = None
            odds_ratio_ci = None
        else:
            odds_ratio = _finite(self.odds_ratio, "Logistic odds ratio")
            odds_ratio_ci = _ordered_pair(
                self.odds_ratio_ci,
                "Logistic odds-ratio CI",
                positive=True,
            )
        if se <= 0 or chi_square < 0 or (odds_ratio is not None and odds_ratio <= 0):
            raise ValueError("Logistic coefficient SE and defined odds ratio must be positive")
        if not math.isclose(chi_square, z_value * z_value, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("Logistic Wald chi-square must equal z squared")
        if odds_ratio is not None and odds_ratio_ci is not None:
            if not math.isclose(odds_ratio, math.exp(b), rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError("Logistic odds ratio must equal exp(b)")
            expected_odds_ci = (math.exp(ci[0]), math.exp(ci[1]))
            if not all(
                math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)
                for actual, expected in zip(odds_ratio_ci, expected_odds_ci, strict=True)
            ):
                raise ValueError("Logistic odds-ratio CI must equal exp(coefficient CI)")
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "se", se)
        object.__setattr__(self, "wald_z", z_value)
        object.__setattr__(self, "wald_chi_square", chi_square)
        object.__setattr__(self, "p_value", p_value)
        object.__setattr__(self, "odds_ratio", odds_ratio)
        object.__setattr__(self, "ci", ci)
        object.__setattr__(self, "odds_ratio_ci", odds_ratio_ci)


@dataclass(frozen=True)
class BinaryClassificationTable:
    threshold: float
    tn: int
    fp: int
    fn: int
    tp: int
    sensitivity: float | None
    specificity: float | None
    positive_predictive_value: float | None
    negative_predictive_value: float | None
    accuracy: float

    def __post_init__(self) -> None:
        threshold = _finite(self.threshold, "Classification threshold")
        if not 0.0 < threshold < 1.0:
            raise ValueError("Classification threshold must be strictly between 0 and 1")
        counts = tuple(
            _count(value, label)
            for value, label in (
                (self.tn, "tn"),
                (self.fp, "fp"),
                (self.fn, "fn"),
                (self.tp, "tp"),
            )
        )
        if sum(counts) == 0:
            raise ValueError("Classification confusion counts must include observations")
        for field_name in (
            "sensitivity",
            "specificity",
            "positive_predictive_value",
            "negative_predictive_value",
            "accuracy",
        ):
            object.__setattr__(self, field_name, _probability(getattr(self, field_name), field_name))
        expected_metrics = {
            "sensitivity": None if counts[3] + counts[2] == 0 else counts[3] / (counts[3] + counts[2]),
            "specificity": None if counts[0] + counts[1] == 0 else counts[0] / (counts[0] + counts[1]),
            "positive_predictive_value": (
                None if counts[3] + counts[1] == 0 else counts[3] / (counts[3] + counts[1])
            ),
            "negative_predictive_value": (
                None if counts[0] + counts[2] == 0 else counts[0] / (counts[0] + counts[2])
            ),
            "accuracy": (counts[0] + counts[3]) / sum(counts),
        }
        for field_name, expected in expected_metrics.items():
            actual = getattr(self, field_name)
            if actual is None or expected is None:
                if actual is not expected:
                    raise ValueError(f"Classification {field_name} is inconsistent with counts")
            elif not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Classification {field_name} is inconsistent with counts")
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "tn", counts[0])
        object.__setattr__(self, "fp", counts[1])
        object.__setattr__(self, "fn", counts[2])
        object.__setattr__(self, "tp", counts[3])


@dataclass(frozen=True)
class CalibrationBin:
    index: int
    probability_lower: float
    probability_upper: float
    count: int
    events: int
    mean_predicted: float
    observed_rate: float

    def __post_init__(self) -> None:
        if not isinstance(self.index, int) or isinstance(self.index, bool) or self.index < 1:
            raise ValueError("Calibration bin index must be a positive integer")
        lower = _probability(self.probability_lower, "Calibration probability lower")
        upper = _probability(self.probability_upper, "Calibration probability upper")
        if lower is None or upper is None or lower > upper:
            raise ValueError("Calibration probability bounds must be ordered")
        count = _count(self.count, "Calibration count")
        events = _count(self.events, "Calibration event")
        if count == 0 or events > count:
            raise ValueError("Calibration bin counts are inconsistent")
        object.__setattr__(self, "probability_lower", lower)
        object.__setattr__(self, "probability_upper", upper)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "events", events)
        object.__setattr__(
            self,
            "mean_predicted",
            _probability(self.mean_predicted, "Calibration mean prediction"),
        )
        object.__setattr__(
            self,
            "observed_rate",
            _probability(self.observed_rate, "Calibration observed rate"),
        )
        if not math.isclose(self.observed_rate, events / count, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("Calibration observed rate is inconsistent with event count")


@dataclass(frozen=True)
class LogisticRegressionResult:
    outcome: str
    predictors: tuple[str, ...]
    event_value: bool | int | float | str
    non_event_value: bool | int | float | str
    event_label: str
    non_event_label: str
    n_obs: int
    n_total: int
    n_dropped: int
    event_count: int
    non_event_count: int
    log_likelihood: float
    null_log_likelihood: float
    minus_two_log_likelihood: float
    aic: float
    likelihood_ratio_chi_square: float
    likelihood_ratio_df: int
    likelihood_ratio_p_value: float
    mcfadden_r_squared: float
    cox_snell_r_squared: float
    nagelkerke_r_squared: float
    coefficients: tuple[LogisticCoefficientRow, ...]
    classification: BinaryClassificationTable
    roc_auc: float
    brier_score: float
    calibration_bins: tuple[CalibrationBin, ...]
    diagnostics: dict[str, Any]
    warning_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    apa_template_id: str
    chart_specs: tuple[ChartSpec, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.outcome or not self.predictors:
            raise ValueError("Logistic result roles must be non-empty")
        counts = tuple(
            _count(value, label)
            for value, label in (
                (self.n_obs, "n_obs"),
                (self.n_total, "n_total"),
                (self.n_dropped, "n_dropped"),
                (self.event_count, "event_count"),
                (self.non_event_count, "non_event_count"),
            )
        )
        if counts[0] + counts[2] != counts[1] or counts[3] + counts[4] != counts[0]:
            raise ValueError("Logistic result observation counts are inconsistent")
        if self.classification.tn + self.classification.fp != self.non_event_count:
            raise ValueError("Logistic classification non-event counts are inconsistent")
        if self.classification.fn + self.classification.tp != self.event_count:
            raise ValueError("Logistic classification event counts are inconsistent")
        if not self.coefficients:
            raise ValueError("Logistic result requires coefficient rows")
        if len(self.warning_codes) != len(self.warnings):
            raise ValueError("Logistic warning codes and rendered warnings must align")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("Logistic warning codes must be unique")
        unknown_warning_codes = set(self.warning_codes) - LOGISTIC_WARNING_CODES
        if unknown_warning_codes:
            raise ValueError(
                f"Unknown logistic warning codes: {sorted(unknown_warning_codes)}"
            )
        if not all(isinstance(message, str) and message for message in self.warnings):
            raise ValueError("Logistic rendered warnings must be non-empty strings")
        for field_name in (
            "log_likelihood",
            "null_log_likelihood",
            "minus_two_log_likelihood",
            "aic",
            "likelihood_ratio_chi_square",
            "mcfadden_r_squared",
            "cox_snell_r_squared",
            "nagelkerke_r_squared",
        ):
            object.__setattr__(self, field_name, _finite(getattr(self, field_name), field_name))
        for field_name in (
            "likelihood_ratio_p_value",
            "roc_auc",
            "brier_score",
        ):
            object.__setattr__(self, field_name, _probability(getattr(self, field_name), field_name))
        if self.likelihood_ratio_chi_square < 0 or self.likelihood_ratio_df < 1:
            raise ValueError("Logistic likelihood-ratio test is invalid")
