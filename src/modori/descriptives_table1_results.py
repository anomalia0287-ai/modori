from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class DescriptiveCategoryRow:
    value: str
    label: str
    count: int
    percent: float


@dataclass(frozen=True)
class DescriptiveVariableSummary:
    key: str
    label: str
    measure: str
    n_obs: int
    n_missing: int
    mean: float | None = None
    sd: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    categories: tuple[DescriptiveCategoryRow, ...] = ()


@dataclass(frozen=True)
class DescriptiveGroupSummary:
    group_value: str
    group_label: str
    n_total: int
    variables: tuple[DescriptiveVariableSummary, ...]


@dataclass(frozen=True)
class DescriptivesTableResult:
    analysis_key: str
    title_ko: str
    variables: tuple[str, ...]
    group: str | None
    n_total: int
    summaries: tuple[DescriptiveVariableSummary, ...]
    grouped_summaries: tuple[DescriptiveGroupSummary, ...] = ()
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
