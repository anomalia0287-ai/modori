from __future__ import annotations

from modori.ancova_results import AncovaResult


def prose_for_ancova(result: AncovaResult, language: str = "ko") -> str:
    if language == "en":
        return (
            f"{result.title_ko} used {result.n_used} of {result.n_total} rows "
            f"with covariates: {', '.join(result.covariate_labels)}. "
            "Group differences are conditional model estimates, not causal claims."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 {result.n_used}건을 사용하고 "
        f"{result.n_excluded}건을 제외했다. 공변량은 "
        f"{', '.join(result.covariate_labels)}이다. "
        f"회귀기울기 동질성 검정 p값은 {_format_number(result.homogeneity_check.p_value)}이다."
    )
    if not result.is_interpretable or result.group_effect is None:
        warning_text = " ".join(result.warnings_ko)
        return f"{base} {warning_text}".strip()

    effect = result.group_effect
    return (
        f"{base} 검정 기준을 통과하여 조정된 집단 차이를 요약했다. "
        f"집단 효과는 F({effect.df_num}, {effect.df_den}) = "
        f"{_format_number(effect.f_statistic)}, p = {_format_number(effect.p_value)}, "
        f"{effect.effect_size_name} = {_format_number(effect.effect_size)}이다. "
        "이 결과는 공변량을 보정한 집단 간 차이 요약이며, 집단 소속만으로 설명하지 않는다."
    )


def table_for_ancova_groups(result: AncovaResult) -> list[dict[str, str]]:
    return [
        {
            "group": group.group_label,
            "n": str(group.n),
            "raw_mean": _format_number(group.raw_mean),
            "raw_sd": _format_optional(group.raw_sd),
            "adjusted_mean": _format_optional(group.adjusted_mean),
        }
        for group in result.groups
    ]


def table_for_ancova_effects(result: AncovaResult) -> list[dict[str, str]]:
    effects = [result.homogeneity_check]
    if result.group_effect is not None:
        effects.append(result.group_effect)
    effects.extend(result.covariate_effects)
    return [
        {
            "term": effect.label_ko,
            "f": _format_number(effect.f_statistic),
            "df_num": str(effect.df_num),
            "df_den": str(effect.df_den),
            "p_value": _format_number(effect.p_value),
            "effect_size": _format_number(effect.effect_size),
        }
        for effect in effects
    ]


def table_for_ancova(result: AncovaResult) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in table_for_ancova_groups(result):
        rows.append(
            {
                "section": "group_summary",
                "group": row["group"],
                "n": row["n"],
                "raw_mean": row["raw_mean"],
                "raw_sd": row["raw_sd"],
                "adjusted_mean": row["adjusted_mean"],
                "term": "",
                "f": "",
                "df_num": "",
                "df_den": "",
                "p_value": "",
                "effect_size": "",
            }
        )
    for row in table_for_ancova_effects(result):
        rows.append(
            {
                "section": "effect",
                "group": "",
                "n": "",
                "raw_mean": "",
                "raw_sd": "",
                "adjusted_mean": "",
                "term": row["term"],
                "f": row["f"],
                "df_num": row["df_num"],
                "df_den": row["df_den"],
                "p_value": row["p_value"],
                "effect_size": row["effect_size"],
            }
        )
    return rows


def _format_optional(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return _format_number(value, digits=digits)


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"
