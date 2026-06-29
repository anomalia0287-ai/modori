from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChartSpec:
    type: str
    title: str
    data: dict[str, Any]
    x_label: str
    y_label: str


@dataclass(frozen=True)
class ReliabilityResult:
    scale_name: str
    n_items: int
    n_cases: int
    cronbach_alpha: float
    alpha_ci: tuple[float, float]
    mcdonald_omega: float
    item_total_corr: dict[str, float]
    alpha_if_deleted: dict[str, float]
    apa_template_id: str
    chart_spec: ChartSpec


@dataclass(frozen=True)
class GroupDesc:
    n: int
    mean: float
    sd: float
    median: float


@dataclass(frozen=True)
class ComparisonResult:
    dv: str
    group_var: str
    test_name: str
    route_reason: str
    groups: dict[str, GroupDesc]
    statistic: float
    df: float | None
    p_value: float
    effect_name: str
    effect_value: float
    mean_diff_ci: tuple[float, float] | None
    assumptions: dict[str, float]
    apa_template_id: str
    chart_spec: ChartSpec
    dv_label: str | None = None
    group_label: str | None = None


@dataclass(frozen=True)
class ReportResult:
    prose: list[str]
    tables: dict[str, list[dict[str, str]]]
    docx_path: str
    figure_paths: dict[str, list[str]]
    apa_template_id: str

@dataclass(frozen=True)
class CoefficientRow:
    name: str
    b: float
    se: float
    beta: float | None
    beta_ci: tuple[float, float] | None
    t: float
    p_value: float
    ci: tuple[float, float]
    vif: float | None


@dataclass(frozen=True)
class RegressionResult:
    dv: str
    predictors: list[str]
    n_obs: int
    n_total: int
    n_dropped: int
    se_type: str
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    df_model: int
    df_resid: int
    f_p_value: float
    coefficients: list[CoefficientRow]
    diagnostics: dict[str, object]
    warnings: list[str]
    apa_template_id: str
    chart_spec: ChartSpec
    educational_interpretation: list[str] = field(default_factory=list)
    diagnostic_chart_specs: list[ChartSpec] = field(default_factory=list)
