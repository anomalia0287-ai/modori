from __future__ import annotations

UI_HELP_KEYS: dict[str, str] = {
    "ui.result.cronbach_alpha": "cronbach_alpha",
    "ui.result.mcdonald_omega": "mcdonald_omega",
    "ui.result.welch_t": "welch_t",
    "ui.result.student_t": "student_t",
    "ui.result.mann_whitney": "mann_whitney",
    "ui.result.cohen_d": "cohen_d",
    "ui.result.rank_biserial": "rank_biserial",
    "ui.result.p_value": "p_value",
    "ui.result.confidence_interval": "confidence_interval",
    "ui.result.r_squared": "r_squared",
    "ui.result.adjusted_r_squared": "adjusted_r_squared",
    "ui.result.vif": "vif",
}

NOT_EXPLAINABLE_UI_LABELS = frozenset(
    {
        "파일",
        "데이터",
        "분석",
        "보고서",
        "다시 실행",
        "안내",
        "표준",
    }
)


def ui_entity_to_library_key(entity_key: str) -> str:
    return UI_HELP_KEYS.get(entity_key, entity_key)
