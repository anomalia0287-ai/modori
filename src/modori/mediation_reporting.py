from __future__ import annotations

from modori.mediation_results import MediationEffect, MediationResult


def prose_for_mediation(result: MediationResult, language: str = "ko") -> str:
    if language == "en":
        return (
            f"{result.title_ko} estimated an indirect-effect model linking "
            f"{result.x}, {result.mediator}, and {result.y} using "
            f"{result.n_used} complete cases."
        )

    base = (
        f"{result.title_ko}은 전체 {result.n_total}건 중 완전 관측치 "
        f"{result.n_used}건을 사용해 {result.x}, {result.mediator}, {result.y}의 "
        f"간접효과 모형을 추정했다. a={_format_number(result.path_a.b)}, "
        f"b={_format_number(result.path_b.b)}, c'={_format_number(result.direct_effect.b)}, "
        f"간접효과={_format_number(result.indirect_effect)}, "
        f"{int(result.bootstrap_ci_level * 100)}% bootstrap CI "
        f"[{_format_number(result.indirect_ci[0])}, {_format_number(result.indirect_ci[1])}]."
    )
    if result.n_excluded:
        base += f" 결측으로 제외된 관측치는 {result.n_excluded}건이다."
    if result.warnings_ko:
        base += " " + " ".join(result.warnings_ko)
    return base


def table_for_mediation(result: MediationResult) -> list[dict[str, str]]:
    return [
        _effect_row(effect, result)
        for effect in (
            result.path_a,
            result.path_b,
            result.direct_effect,
            result.total_effect,
        )
    ]


def _effect_row(
    effect: MediationEffect,
    result: MediationResult,
) -> dict[str, str]:
    return {
        "effect": effect.name,
        "predictor": effect.predictor,
        "outcome": effect.outcome,
        "b": _format_number(effect.b),
        "SE": _format_number(effect.se),
        "t": _format_number(effect.t),
        "p_value": _format_number(effect.p_value),
        "ci_low": _format_number(effect.ci[0]),
        "ci_high": _format_number(effect.ci[1]),
        "indirect_effect": _format_number(result.indirect_effect),
        "indirect_ci_low": _format_number(result.indirect_ci[0]),
        "indirect_ci_high": _format_number(result.indirect_ci[1]),
        "bootstrap_iterations": str(result.bootstrap_iterations),
        "warnings": "; ".join(result.warnings_ko),
    }


def _format_number(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"
