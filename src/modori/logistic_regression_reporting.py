from __future__ import annotations

from modori.logistic_regression_results import (
    LOGISTIC_CLASSIFICATION_METRIC_LABELS,
    LOGISTIC_WARNING_TEXTS,
    LogisticCoefficientRow,
    LogisticRegressionResult,
    render_logistic_warning,
)


def _language_base(language: str) -> str:
    base = str(language).lower().split("-")[0]
    if base not in {"ko", "en"}:
        raise ValueError("Logistic report language must be Korean or English")
    return base


def _number(
    value: float,
    digits: int = 2,
    *,
    omit_leading_zero: bool = True,
) -> str:
    text = f"{float(value):.{digits}f}"
    if omit_leading_zero:
        if text.startswith("-0."):
            return "-" + text[2:]
        if text.startswith("0."):
            return text[1:]
    return text


def _p_value(value: float) -> str:
    if value < 0.001:
        return "p < .001"
    return f"p = {_number(value, 3)}"


def _coded_value(label: str, value: object) -> str:
    return f"{label}({value})"


def _undefined_metric_names(
    result: LogisticRegressionResult,
    language: str,
) -> list[str]:
    return [
        LOGISTIC_CLASSIFICATION_METRIC_LABELS[language][name]
        for name in LOGISTIC_CLASSIFICATION_METRIC_LABELS[language]
        if getattr(result.classification, name) is None
    ]


def warnings_for_logistic(
    result: LogisticRegressionResult,
    language: str = "ko",
) -> tuple[str, ...]:
    language_base = _language_base(language)
    rendered: list[str] = []
    for code in result.warning_codes:
        detail = None
        if code == "undefined_classification_metrics":
            detail = ", ".join(_undefined_metric_names(result, language_base))
        rendered.append(
            render_logistic_warning(
                code,
                language_base,
                detail=detail,
            )
        )
    return tuple(rendered)


def _coefficient_sentence_ko(row: LogisticCoefficientRow) -> str:
    significance = (
        "통계적으로 유의한 연관을 보였다"
        if row.p_value < 0.05
        else "통계적으로 유의한 연관을 보이지 않았다"
    )
    odds = ""
    if row.odds_ratio is not None and row.odds_ratio_ci is not None:
        odds = (
            f", OR = {_number(row.odds_ratio)}, "
            f"95% CI [{_number(row.odds_ratio_ci[0])}, "
            f"{_number(row.odds_ratio_ci[1])}]"
        )
    return (
        f"{row.name}: 선택한 사건과 {significance}"
        f"(b = {_number(row.b)}, SE = {_number(row.se)}, "
        f"z = {_number(row.wald_z)}, {_p_value(row.p_value)}{odds})"
    )


def _coefficient_sentence_en(row: LogisticCoefficientRow) -> str:
    significance = (
        "was statistically associated with"
        if row.p_value < 0.05
        else "was not statistically associated with"
    )
    odds = ""
    if row.odds_ratio is not None and row.odds_ratio_ci is not None:
        odds = (
            f", OR = {_number(row.odds_ratio)}, "
            f"95% CI [{_number(row.odds_ratio_ci[0])}, "
            f"{_number(row.odds_ratio_ci[1])}]"
        )
    return (
        f"{row.name} {significance} the selected event "
        f"(b = {_number(row.b)}, SE = {_number(row.se)}, "
        f"z = {_number(row.wald_z)}, {_p_value(row.p_value)}{odds})"
    )


def _classification_sentence(result: LogisticRegressionResult, language: str) -> str:
    classification = result.classification
    metrics = {
        "sensitivity": classification.sensitivity,
        "specificity": classification.specificity,
        "positive predictive value": classification.positive_predictive_value,
        "negative predictive value": classification.negative_predictive_value,
    }
    if language == "ko":
        labels = {
            "sensitivity": "민감도",
            "specificity": "특이도",
            "positive predictive value": "양성예측도",
            "negative predictive value": "음성예측도",
        }
        metric_text = ", ".join(
            f"{labels[name]} = {_number(value, 2) if value is not None else '정의되지 않음'}"
            for name, value in metrics.items()
        )
        undefined = ""
        if classification.positive_predictive_value is None:
            undefined = " 양성예측도는 정의되지 않습니다."
        if classification.negative_predictive_value is None:
            undefined += " 음성예측도는 정의되지 않습니다."
        return (
            f"분류 임계값 = {_number(classification.threshold)}에서 "
            f"TN = {classification.tn}, FP = {classification.fp}, "
            f"FN = {classification.fn}, TP = {classification.tp}, {metric_text}, "
            f"정확도 = {_number(classification.accuracy)}, "
            f"ROC AUC = {_number(result.roc_auc)}, "
            f"Brier 점수 = {_number(result.brier_score)}로 나타났다.{undefined}"
        )
    metric_text = ", ".join(
        f"{name} = {_number(value, 2) if value is not None else 'undefined'}"
        for name, value in metrics.items()
    )
    undefined = ""
    if classification.positive_predictive_value is None:
        undefined = " The positive predictive value is undefined at this threshold."
    if classification.negative_predictive_value is None:
        undefined += " The negative predictive value is undefined at this threshold."
    return (
        f"At classification threshold = {_number(classification.threshold)}, "
        f"TN = {classification.tn}, FP = {classification.fp}, "
        f"FN = {classification.fn}, TP = {classification.tp}, {metric_text}, "
        f"accuracy = {_number(classification.accuracy)}, "
        f"ROC AUC = {_number(result.roc_auc)}, and "
        f"Brier score = {_number(result.brier_score)}.{undefined}"
    )


def prose_for_logistic(
    result: LogisticRegressionResult,
    language: str = "ko",
) -> str:
    language_base = _language_base(language)
    predictor_rows = [
        row for row in result.coefficients if row.term_type != "intercept"
    ]
    warning_text = " ".join(warnings_for_logistic(result, language_base))
    significant = result.likelihood_ratio_p_value < 0.05

    if language_base == "ko":
        coding = (
            f"결과변수 {result.outcome}의 코딩은 사건(event) = "
            f"{_coded_value(result.event_label, result.event_value)}, "
            f"비사건 = {_coded_value(result.non_event_label, result.non_event_value)}이다. "
            f"전체 {result.n_total}행 중 {result.n_obs}행을 사용했고 "
            f"{result.n_dropped}행을 결측으로 제외했다."
        )
        model = (
            f"이항 로지스틱 회귀모형의 우도비 검정은 "
            f"{'통계적으로 유의했다' if significant else '통계적으로 유의하지 않았다'}("
            f"LR χ²({result.likelihood_ratio_df}) = "
            f"{_number(result.likelihood_ratio_chi_square)}, "
            f"{_p_value(result.likelihood_ratio_p_value)}, "
            f"-2LL = {_number(result.minus_two_log_likelihood)}, "
            f"AIC = {_number(result.aic)}, "
            f"McFadden R² = {_number(result.mcfadden_r_squared)})."
        )
        coefficients = "; ".join(
            _coefficient_sentence_ko(row) for row in predictor_rows
        )
        classification = _classification_sentence(result, language_base)
        calibration = (
            f"보정 요약은 {len(result.calibration_bins)}개 구간의 동일 자료 기술치다."
            if result.calibration_bins
            else ""
        )
        return " ".join(
            part
            for part in (coding, model, coefficients + ".", classification, calibration, warning_text)
            if part
        )

    coding = (
        f"For {result.outcome}, the event was coded as "
        f"{result.event_label} ({result.event_value}) and the non-event as "
        f"{result.non_event_label} ({result.non_event_value}). "
        f"The model used {result.n_obs} of {result.n_total} rows and excluded "
        f"{result.n_dropped} rows for missing values."
    )
    model = (
        f"The likelihood-ratio test for the binary logistic model was "
        f"{'statistically significant' if significant else 'not statistically significant'}, "
        f"LR χ²({result.likelihood_ratio_df}) = "
        f"{_number(result.likelihood_ratio_chi_square)}, "
        f"{_p_value(result.likelihood_ratio_p_value)}, "
        f"-2LL = {_number(result.minus_two_log_likelihood)}, "
        f"AIC = {_number(result.aic)}, and "
        f"McFadden R² = {_number(result.mcfadden_r_squared)}."
    )
    coefficients = "; ".join(
        _coefficient_sentence_en(row) for row in predictor_rows
    )
    classification = _classification_sentence(result, language_base)
    calibration = (
        f"The calibration summary contains {len(result.calibration_bins)} "
        "in-sample descriptive bins."
        if result.calibration_bins
        else ""
    )
    return " ".join(
        part
        for part in (coding, model, coefficients + ".", classification, calibration, warning_text)
        if part
    )


def table_for_logistic(result: LogisticRegressionResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for coefficient in result.coefficients:
        odds_ratio = (
            "" if coefficient.odds_ratio is None else _number(coefficient.odds_ratio)
        )
        odds_ratio_ci = (
            ""
            if coefficient.odds_ratio_ci is None
            else (
                f"[{_number(coefficient.odds_ratio_ci[0])}, "
                f"{_number(coefficient.odds_ratio_ci[1])}]"
            )
        )
        rows.append(
            {
                "term": coefficient.name,
                "b": _number(coefficient.b),
                "SE": _number(coefficient.se),
                "Wald z": _number(coefficient.wald_z),
                "Wald chi-square": _number(coefficient.wald_chi_square),
                "p": _p_value(coefficient.p_value),
                "odds ratio": odds_ratio,
                "95% CI (b)": (
                    f"[{_number(coefficient.ci[0])}, "
                    f"{_number(coefficient.ci[1])}]"
                ),
                "95% CI (OR)": odds_ratio_ci,
            }
        )
    return rows


__all__ = [
    "LOGISTIC_WARNING_TEXTS",
    "prose_for_logistic",
    "table_for_logistic",
    "warnings_for_logistic",
]
