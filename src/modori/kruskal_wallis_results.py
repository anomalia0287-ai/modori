from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class KruskalWallisGroupSummary:
    group_value: str
    group_label: str
    n: int
    median: float
    mean_rank: float
    mean: float | None = None
    sd: float | None = None


@dataclass(frozen=True)
class KruskalWallisResult:
    analysis_key: str
    title_ko: str
    dependent: str
    dependent_label: str
    group: str
    group_label: str
    n_total: int
    n_used: int
    n_excluded: int
    groups: tuple[KruskalWallisGroupSummary, ...]
    statistic_label: str
    statistic: float
    degrees_of_freedom: int
    p_value: float
    effect_size_label: str
    effect_size: float
    posthoc: object | None
    warnings_ko: tuple[str, ...]
    notes_ko: tuple[str, ...]
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
