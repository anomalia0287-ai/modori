from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modori.results import ChartSpec


@dataclass(frozen=True)
class OneWayAnovaGroupSummary:
    group_value: str
    group_label: str
    n: int
    mean: float
    sd: float
    median: float


@dataclass(frozen=True)
class OneWayAnovaNormalityDiagnostic:
    group_value: str
    group_label: str
    n: int
    test_name: str
    statistic: float
    p_value: float


@dataclass(frozen=True)
class OneWayAnovaAssumptions:
    group_count: int
    min_group_n: int
    max_group_n: int
    min_group_variance: float
    max_group_variance: float
    levene_statistic: float
    levene_p_value: float
    normality: tuple[OneWayAnovaNormalityDiagnostic, ...] = ()
    notes_ko: tuple[str, ...] = ()


@dataclass(frozen=True)
class OneWayAnovaPosthocComparison:
    group1_value: str
    group2_value: str
    group1_label: str
    group2_label: str
    mean_difference: float
    p_value: float
    ci_low: float | None = None
    ci_high: float | None = None
    reject: bool | None = None


@dataclass(frozen=True)
class OneWayAnovaPosthocResult:
    method: str | None
    status: str
    reason_ko: str
    comparisons: tuple[OneWayAnovaPosthocComparison, ...] = ()
    method_details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OneWayAnovaResult:
    analysis_key: str
    title_ko: str
    dv: str
    group: str
    dv_label: str
    group_label: str
    n_total: int
    n_used: int
    n_excluded: int
    groups: tuple[OneWayAnovaGroupSummary, ...]
    assumptions: OneWayAnovaAssumptions
    f_statistic: float
    df_between: int
    df_within: int
    p_value: float
    eta_squared: float
    omega_squared: float
    posthoc: OneWayAnovaPosthocResult
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
