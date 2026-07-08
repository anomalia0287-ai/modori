from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class RepeatedMeasureLevelSummary:
    variable: str
    level_index: int
    level_label: str
    n: int
    mean: float
    sd: float
    median: float


@dataclass(frozen=True)
class RepeatedMeasuresSphericity:
    method: str
    sphericity_assumed: bool
    w_statistic: float
    chi_square: float
    dof: int
    p_value: float
    epsilon_gg: float
    epsilon_hf: float


@dataclass(frozen=True)
class RepeatedMeasuresAnovaResult:
    analysis_key: str
    title_ko: str
    measures: tuple[str, ...]
    within_factor: str
    n_total: int
    n_used: int
    n_excluded: int
    levels: tuple[RepeatedMeasureLevelSummary, ...]
    sphericity: RepeatedMeasuresSphericity
    ss_effect: float
    ss_error: float
    df_effect: float
    df_error: float
    f_statistic: float
    p_value: float
    partial_eta_squared: float
    correction_method: str
    corrected_df_effect: float | None = None
    corrected_df_error: float | None = None
    corrected_p_value: float | None = None
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
