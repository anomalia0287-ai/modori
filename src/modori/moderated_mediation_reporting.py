from __future__ import annotations

from modori.moderated_mediation_results import (
    ConditionalIndirectEffect,
    ModeratedMediationResult,
)


def prose_for_moderated_mediation(
    result: ModeratedMediationResult,
    language: str = "ko",
) -> str:
    if language == "en":
        return (
            f"{result.title_ko} estimated PROCESS-style Model {result.model} "
            f"using {result.n_used} complete cases."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 완전 관측치 "
        f"{result.n_used}건을 사용해 PROCESS식 Model {result.model}의 "
        f"조건부 간접효과를 추정했다. 조절된 매개 index="
        f"{_format_number(result.index_of_moderated_mediation)}, "
        f"{int(result.bootstrap_ci_level * 100)}% bootstrap CI "
        f"[{_format_number(result.index_ci[0])}, {_format_number(result.index_ci[1])}]."
    )
    if result.n_excluded:
        base += f" 결측으로 제외된 관측치는 {result.n_excluded}건이다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_moderated_mediation(
    result: ModeratedMediationResult,
) -> list[dict[str, str]]:
    return [_conditional_row(effect, result) for effect in result.conditional_effects]


def _conditional_row(
    effect: ConditionalIndirectEffect,
    result: ModeratedMediationResult,
) -> dict[str, str]:
    return {
        "model": str(result.model),
        "moderator_level": effect.moderator_label,
        "moderator_value": _format_number(effect.moderator_value),
        "conditional_indirect_effect": _format_number(effect.effect),
        "ci_low": _format_number(effect.ci[0]),
        "ci_high": _format_number(effect.ci[1]),
        "index_of_moderated_mediation": _format_number(
            result.index_of_moderated_mediation
        ),
        "index_ci_low": _format_number(result.index_ci[0]),
        "index_ci_high": _format_number(result.index_ci[1]),
        "bootstrap_iterations": str(result.bootstrap_iterations),
        "warnings": "; ".join(result.warnings_ko),
    }


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"
