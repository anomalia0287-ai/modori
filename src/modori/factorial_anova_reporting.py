from __future__ import annotations

from modori.factorial_anova_results import (
    FactorialAnovaResult,
    FactorialEffectResult,
    FactorialSimpleEffectResult,
    render_factorial_warning,
)


FACTORIAL_TABLE_COLUMNS = (
    "section",
    "label",
    "factor",
    "conditioning_factor",
    "conditioning_level",
    "factor_a_level",
    "factor_b_level",
    "n",
    "estimate",
    "se",
    "ci95",
    "ss",
    "df_num",
    "df_den",
    "ms",
    "f",
    "p",
    "adjusted_p",
    "partial_eta_squared",
    "decision",
    "status",
    "statistic",
    "detail",
)


def _language_base(language: str) -> str:
    base = str(language).lower().split("-")[0]
    if base not in {"ko", "en"}:
        raise ValueError("Factorial report language must be Korean or English")
    return base


def _number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def _p_value(value: float) -> str:
    if value < 0.001:
        return "p < .001"
    return f"p = {_number(value)}"


def _ci(lower: float, upper: float) -> str:
    return f"[{_number(lower)}, {_number(upper)}]"


def _effect(result: FactorialAnovaResult, effect: str) -> FactorialEffectResult:
    return next(row for row in result.effects if row.effect == effect)


def _test_text_ko(label: str, row: FactorialEffectResult) -> str:
    return (
        f"{label}, F({row.df_num}, {row.df_den}) = {_number(row.f_value)}, "
        f"{_p_value(row.p_value)}, partial eta squared = "
        f"{_number(row.partial_eta_squared)}"
    )


def _test_text_en(label: str, row: FactorialEffectResult) -> str:
    return (
        f"{label}, F({row.df_num}, {row.df_den}) = {_number(row.f_value)}, "
        f"{_p_value(row.p_value)}, partial eta squared = "
        f"{_number(row.partial_eta_squared)}"
    )


def _simple_text_ko(
    result: FactorialAnovaResult,
    row: FactorialSimpleEffectResult,
) -> str:
    tested = (
        result.factor_a_label
        if row.tested_factor == "factor_a"
        else result.factor_b_label
    )
    conditioned = (
        result.factor_a_label
        if row.conditioning_factor == "factor_a"
        else result.factor_b_label
    )
    decision = "기각" if row.reject else "기각하지 않음"
    return (
        f"{conditioned}={row.conditioning_level.label}에서 {tested}, "
        f"F({row.df_num}, {row.df_den}) = {_number(row.f_value)}, "
        f"원 p = {_number(row.p_value)}, Holm p = "
        f"{_number(row.adjusted_p_value)}, {decision}"
    )


def _simple_text_en(
    result: FactorialAnovaResult,
    row: FactorialSimpleEffectResult,
) -> str:
    tested = (
        result.factor_a_label
        if row.tested_factor == "factor_a"
        else result.factor_b_label
    )
    conditioned = (
        result.factor_a_label
        if row.conditioning_factor == "factor_a"
        else result.factor_b_label
    )
    decision = "reject" if row.reject else "do not reject"
    return (
        f"{tested} within {conditioned}={row.conditioning_level.label}, "
        f"F({row.df_num}, {row.df_den}) = {_number(row.f_value)}, "
        f"raw p = {_number(row.p_value)}, Holm p = "
        f"{_number(row.adjusted_p_value)}, {decision}"
    )


def _marginal_text(result: FactorialAnovaResult) -> str:
    values = []
    for row in result.marginals:
        factor = (
            result.factor_a_label
            if row.factor_role == "factor_a"
            else result.factor_b_label
        )
        values.append(
            f"{factor}={row.level.label}: M={_number(row.mean)}, "
            f"SE={_number(row.se)}, 95% CI {_ci(row.ci_low, row.ci_high)}"
        )
    return "; ".join(values)


def _cell_text(result: FactorialAnovaResult) -> str:
    return "; ".join(
        (
            f"{result.factor_a_label}={row.factor_a_level.label}, "
            f"{result.factor_b_label}={row.factor_b_level.label}: "
            f"n={row.n}, M={_number(row.mean)}, SD={_number(row.sd)}, "
            f"95% CI {_ci(row.ci_low, row.ci_high)}"
        )
        for row in result.cells
    )


def _diagnostics_ko(result: FactorialAnovaResult) -> str:
    assumptions = result.assumptions
    levene = (
        f"Levene W={_number(assumptions.levene_statistic)}, "
        f"{_p_value(assumptions.levene_p_value)}"
        if assumptions.levene_status == "available"
        and assumptions.levene_statistic is not None
        and assumptions.levene_p_value is not None
        else "Levene 계산 불가"
    )
    if (
        assumptions.shapiro_status == "available"
        and assumptions.shapiro_statistic is not None
        and assumptions.shapiro_p_value is not None
    ):
        shapiro = (
            f"잔차 Shapiro-Wilk W={_number(assumptions.shapiro_statistic)}, "
            f"{_p_value(assumptions.shapiro_p_value)}"
        )
    elif assumptions.shapiro_status == "omitted":
        shapiro = "잔차 Shapiro-Wilk p값 생략(N>5000)"
    else:
        shapiro = "잔차 Shapiro-Wilk 계산 불가"
    return (
        f"셀 n 범위 {assumptions.min_cell_n}-{assumptions.max_cell_n}, "
        f"불균형비 {_number(assumptions.imbalance_ratio)}; {levene}; {shapiro}"
    )


def _diagnostics_en(result: FactorialAnovaResult) -> str:
    assumptions = result.assumptions
    levene = (
        f"Levene W={_number(assumptions.levene_statistic)}, "
        f"{_p_value(assumptions.levene_p_value)}"
        if assumptions.levene_status == "available"
        and assumptions.levene_statistic is not None
        and assumptions.levene_p_value is not None
        else "Levene unavailable"
    )
    if (
        assumptions.shapiro_status == "available"
        and assumptions.shapiro_statistic is not None
        and assumptions.shapiro_p_value is not None
    ):
        shapiro = (
            f"residual Shapiro-Wilk W={_number(assumptions.shapiro_statistic)}, "
            f"{_p_value(assumptions.shapiro_p_value)}"
        )
    elif assumptions.shapiro_status == "omitted":
        shapiro = "residual Shapiro-Wilk p-value omitted (N>5000)"
    else:
        shapiro = "residual Shapiro-Wilk unavailable"
    return (
        f"cell n range {assumptions.min_cell_n}-{assumptions.max_cell_n}, "
        f"imbalance ratio {_number(assumptions.imbalance_ratio)}; {levene}; {shapiro}"
    )


def prose_for_factorial_anova(
    result: FactorialAnovaResult,
    language: str = "ko",
) -> str:
    language_base = _language_base(language)
    interaction = _effect(result, "interaction")
    factor_a = _effect(result, "factor_a")
    factor_b = _effect(result, "factor_b")
    rendered_warnings = tuple(
        render_factorial_warning(code, language_base) for code in result.warning_codes
    )

    if language_base == "ko":
        simple = (
            "; ".join(_simple_text_ko(result, row) for row in result.simple_effects)
            if result.simple_effects
            else "상호작용 p값이 .05 이상이어서 생성하지 않았다"
        )
        warning_text = " ".join(rendered_warnings) if rendered_warnings else "없음."
        paragraphs = (
            "완전 셀 고정효과 이원 설계에서 "
            f"{result.dv_label}을 분석했다. 전체 {result.n_total}행 중 완전 관측 "
            f"{result.n_used}행을 사용하고 {result.n_excluded}행을 목록별 제외했다.",
            "동일 셀 가중 Type III 검정은 다른 요인의 각 수준을 표본 수와 무관하게 "
            "동일 가중하여 주효과를 정의한다. 세 Type III 제곱합은 전체 변동의 "
            "상호 배타적 비율로 합산하지 않는다. 세 검정은 계획된 옴니버스 "
            "검정이며 서로 다중성 보정하지 않았다. 따라서 세 옴니버스 검정 "
            "전체의 가족오류율 통제를 주장하지 않는다.",
            "상호작용: "
            + _test_text_ko(
                f"{result.factor_a_label} x {result.factor_b_label}", interaction
            )
            + ".",
            "상호작용 게이트를 통과한 Holm 보정 단순효과: "
            + simple
            + ". 모든 방향의 단순효과를 하나의 Holm 가족으로 보정했다. "
            "상호작용 검정과 후속 검정 전체의 가족오류율 통제를 주장하지 않는다.",
            "주효과: "
            + "; ".join(
                (
                    _test_text_ko(result.factor_a_label, factor_a),
                    _test_text_ko(result.factor_b_label, factor_b),
                )
            )
            + ". 상호작용이 유의한 경우 고립된 주효과보다 상호작용과 "
            "보정 단순효과를 우선 해석한다.",
            "동일 셀 가중 주변평균: "
            + _marginal_text(result)
            + ". 이 구간은 점별 95% 신뢰구간이며 동시 신뢰구간이 아니다.",
            "셀 평균: "
            + _cell_text(result)
            + ". 이 구간도 풀링 MSE를 사용한 점별 95% 신뢰구간이다.",
            "진단: " + _diagnostics_ko(result) + ".",
            "경고: " + warning_text,
        )
        return "\n\n".join(paragraphs)

    simple = (
        "; ".join(_simple_text_en(result, row) for row in result.simple_effects)
        if result.simple_effects
        else "not generated because the interaction p-value was at least .05"
    )
    warning_text = " ".join(rendered_warnings) if rendered_warnings else "None."
    paragraphs = (
        "A complete-cell fixed-effects two-factor design analyzed "
        f"{result.dv_label}. It used {result.n_used} of {result.n_total} rows as "
        f"{result.n_used} complete cases and excluded {result.n_excluded} rows listwise.",
        "The equal-cell-weight Type III tests define each main effect by assigning "
        "equal weight to every level of the other factor regardless of cell size. "
        "The three Type III sums of squares are not additive shares of total variation. "
        "The three planned omnibus tests are not multiplicity-adjusted, and this "
        "report makes no familywise-error-control claim across those three tests.",
        "Interaction: "
        + _test_text_en(
            f"{result.factor_a_label} x {result.factor_b_label}", interaction
        )
        + ".",
        "Interaction-gated Holm-adjusted simple effects: "
        + simple
        + ". All directional simple effects share one Holm family. This report "
        "does not claim familywise-error control across the interaction gate and follow-ups.",
        "Main effects: "
        + "; ".join(
            (
                _test_text_en(result.factor_a_label, factor_a),
                _test_text_en(result.factor_b_label, factor_b),
            )
        )
        + ". When the interaction is significant, interpretation prioritizes the "
        "interaction and adjusted simple effects over isolated main effects.",
        "Equal-cell-weight marginal means: "
        + _marginal_text(result)
        + ". These are pointwise 95% confidence intervals, not simultaneous intervals.",
        "Cell means: "
        + _cell_text(result)
        + ". These are also pooled-MSE pointwise 95% confidence intervals.",
        "Diagnostics: " + _diagnostics_en(result) + ".",
        "Warnings: " + warning_text,
    )
    return "\n\n".join(paragraphs)


def _row(**values: str) -> dict[str, str]:
    unknown = set(values) - set(FACTORIAL_TABLE_COLUMNS)
    if unknown:
        raise ValueError(f"Unknown factorial table columns: {sorted(unknown)}")
    return {column: values.get(column, "") for column in FACTORIAL_TABLE_COLUMNS}


def _effect_row(
    section: str,
    row: FactorialEffectResult,
    *,
    factor: str,
) -> dict[str, str]:
    return _row(
        section=section,
        label=row.label,
        factor=factor,
        ss=_number(row.ss),
        df_num=str(row.df_num),
        df_den=str(row.df_den),
        ms=_number(row.ms),
        f=_number(row.f_value),
        p=_number(row.p_value),
        partial_eta_squared=_number(row.partial_eta_squared),
        status="planned_omnibus",
        detail=f"condition_number={row.condition_number:.6g}",
    )


def table_for_factorial_anova(
    result: FactorialAnovaResult,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    interaction = _effect(result, "interaction")
    rows.append(
        _effect_row(
            "interaction",
            interaction,
            factor=f"{result.factor_a_label} x {result.factor_b_label}",
        )
    )
    for simple in result.simple_effects:
        tested = (
            result.factor_a_label
            if simple.tested_factor == "factor_a"
            else result.factor_b_label
        )
        conditioned = (
            result.factor_a_label
            if simple.conditioning_factor == "factor_a"
            else result.factor_b_label
        )
        rows.append(
            _row(
                section="simple_effect",
                label=f"{tested} within {conditioned}",
                factor=tested,
                conditioning_factor=conditioned,
                conditioning_level=simple.conditioning_level.label,
                ss=_number(simple.ss),
                df_num=str(simple.df_num),
                df_den=str(simple.df_den),
                ms=_number(simple.ms),
                f=_number(simple.f_value),
                p=_number(simple.p_value),
                adjusted_p=_number(simple.adjusted_p_value),
                partial_eta_squared=_number(simple.partial_eta_squared),
                decision="reject" if simple.reject else "do_not_reject",
                status="interaction_gated_holm_one_family",
                detail=f"condition_number={simple.condition_number:.6g}",
            )
        )
    rows.extend(
        (
            _effect_row(
                "main_effect",
                _effect(result, "factor_a"),
                factor=result.factor_a_label,
            ),
            _effect_row(
                "main_effect",
                _effect(result, "factor_b"),
                factor=result.factor_b_label,
            ),
        )
    )
    for marginal in result.marginals:
        factor = (
            result.factor_a_label
            if marginal.factor_role == "factor_a"
            else result.factor_b_label
        )
        rows.append(
            _row(
                section="marginal_mean",
                label=marginal.level.label,
                factor=factor,
                estimate=_number(marginal.mean),
                se=_number(marginal.se),
                ci95=_ci(marginal.ci_low, marginal.ci_high),
                status="equal_cell_weight_pointwise_95_ci",
            )
        )
    for cell in result.cells:
        rows.append(
            _row(
                section="cell_summary",
                label=(f"{cell.factor_a_level.label} x {cell.factor_b_level.label}"),
                factor_a_level=cell.factor_a_level.label,
                factor_b_level=cell.factor_b_level.label,
                n=str(cell.n),
                estimate=_number(cell.mean),
                se=_number(cell.se),
                ci95=_ci(cell.ci_low, cell.ci_high),
                statistic=f"SD={_number(cell.sd)}",
                status="raw_cell_mean_pointwise_95_ci",
            )
        )
    assumptions = result.assumptions
    factor_a_labels = {level.token: level.label for level in result.levels_a}
    factor_b_labels = {level.token: level.label for level in result.levels_b}
    zero_variance_detail = "; ".join(
        f"{factor_a_labels[token_a]} x {factor_b_labels[token_b]}"
        for token_a, token_b in assumptions.zero_variance_cells
    )
    rows.extend(
        (
            _row(
                section="diagnostic",
                label="complete_cases",
                n=str(result.n_used),
                status="available",
                detail=f"total={result.n_total}; excluded={result.n_excluded}",
            ),
            _row(
                section="diagnostic",
                label="pooled_error",
                ss=_number(result.sse),
                df_den=str(result.df_error),
                ms=_number(result.mse),
                status="available",
                detail="within_cell_saturated_error",
            ),
            _row(
                section="diagnostic",
                label="cell_balance",
                n=str(assumptions.min_cell_n),
                statistic=_number(assumptions.imbalance_ratio),
                status="available",
                detail=f"min={assumptions.min_cell_n}; max={assumptions.max_cell_n}",
            ),
            _row(
                section="diagnostic",
                label="zero_variance_cells",
                status=("present" if assumptions.zero_variance_cells else "none"),
                detail=zero_variance_detail,
            ),
            _row(
                section="diagnostic",
                label="levene",
                p=(
                    ""
                    if assumptions.levene_p_value is None
                    else _number(assumptions.levene_p_value)
                ),
                status=assumptions.levene_status,
                statistic=(
                    ""
                    if assumptions.levene_statistic is None
                    else _number(assumptions.levene_statistic)
                ),
                detail="median_centered",
            ),
            _row(
                section="diagnostic",
                label="shapiro",
                p=(
                    ""
                    if assumptions.shapiro_p_value is None
                    else _number(assumptions.shapiro_p_value)
                ),
                status=assumptions.shapiro_status,
                statistic=(
                    ""
                    if assumptions.shapiro_statistic is None
                    else _number(assumptions.shapiro_statistic)
                ),
                detail="full_model_residuals",
            ),
        )
    )
    rows.extend(
        _row(
            section="diagnostic",
            label=f"warning:{code}",
            status="warning",
            detail=code,
        )
        for code in result.warning_codes
    )
    return rows


__all__ = [
    "FACTORIAL_TABLE_COLUMNS",
    "prose_for_factorial_anova",
    "table_for_factorial_anova",
]
