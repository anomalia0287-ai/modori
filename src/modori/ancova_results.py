from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class AncovaGroupSummary:
    group_value: str
    group_label: str
    n: int
    raw_mean: float
    raw_sd: float | None
    adjusted_mean: float | None


@dataclass(frozen=True)
class AncovaEffectResult:
    term: str
    label_ko: str
    f_statistic: float
    df_num: int
    df_den: int
    p_value: float
    effect_size_name: str
    effect_size: float


@dataclass(frozen=True)
class AncovaResult:
    analysis_key: str
    title_ko: str
    dv: str
    dv_label: str
    group: str
    group_label: str
    covariates: tuple[str, ...]
    covariate_labels: tuple[str, ...]
    homogeneity_alpha: float
    n_total: int
    n_used: int
    n_excluded: int
    groups: tuple[AncovaGroupSummary, ...]
    homogeneity_check: AncovaEffectResult
    group_effect: AncovaEffectResult | None
    covariate_effects: tuple[AncovaEffectResult, ...]
    is_interpretable: bool
    warnings_ko: tuple[str, ...]
    notes_ko: tuple[str, ...]
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
