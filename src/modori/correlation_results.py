from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modori.results import ChartSpec


@dataclass(frozen=True)
class CorrelationPairResult:
    x: str
    y: str
    x_label: str
    y_label: str
    method: str
    statistic_label: str
    coefficient: float
    p_value: float
    n: int
    excluded_n: int
    ci: tuple[float, float] | None = None
    p_adjusted: float | None = None
    warnings_ko: tuple[str, ...] = ()
    method_details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CorrelationResult:
    analysis_key: str
    title_ko: str
    variables: tuple[str, ...]
    method_policy: str
    missing_policy: str
    n_total: int
    pairs: tuple[CorrelationPairResult, ...]
    warnings_ko: tuple[str, ...]
    notes_ko: tuple[str, ...]
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
