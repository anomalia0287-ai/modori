from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class FriedmanLevelSummary:
    variable: str
    level_index: int
    level_label: str
    n: int
    median: float
    mean_rank: float
    mean: float | None = None
    sd: float | None = None


@dataclass(frozen=True)
class FriedmanResult:
    analysis_key: str
    title_ko: str
    measures: tuple[str, ...]
    within_factor: str
    n_total: int
    n_used: int
    n_excluded: int
    levels: tuple[FriedmanLevelSummary, ...]
    statistic_label: str
    statistic: float
    degrees_of_freedom: int
    p_value: float
    kendalls_w: float
    posthoc: object | None = None
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
