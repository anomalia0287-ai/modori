from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class FrequencyCategoryRow:
    value: str
    label: str
    count: int
    percent: float


@dataclass(frozen=True)
class FrequencyVariableTable:
    key: str
    label: str
    measure: str
    n_total: int
    n_obs: int
    n_missing: int
    categories: tuple[FrequencyCategoryRow, ...]


@dataclass(frozen=True)
class CrosstabCell:
    row_value: str
    row_label: str
    column_value: str
    column_label: str
    count: int
    row_percent: float
    column_percent: float
    total_percent: float
    expected_count: float


@dataclass(frozen=True)
class AssociationTestResult:
    pearson_chi_square: float
    df: int
    pearson_p_value: float
    expected_counts: tuple[tuple[float, ...], ...]
    expected_cell_warning: bool
    min_expected_count: float | None
    low_expected_cell_count: int
    low_expected_cell_percent: float
    cramers_v: float | None
    selected_method: str
    selected_p_value: float | None
    fisher_odds_ratio: float | None = None


@dataclass(frozen=True)
class CrosstabTableResult:
    row_variable: str
    row_label: str
    column_variable: str
    column_label: str
    row_labels: tuple[str, ...]
    column_labels: tuple[str, ...]
    n_total: int
    n_obs: int
    n_missing_row: int
    n_missing_column: int
    n_excluded: int
    cells: tuple[tuple[CrosstabCell, ...], ...]
    test: AssociationTestResult


@dataclass(frozen=True)
class FrequencyCrosstabResult:
    analysis_key: str
    title_ko: str
    mode: str
    variables: tuple[str, ...]
    n_total: int
    frequency_tables: tuple[FrequencyVariableTable, ...] = ()
    crosstab: CrosstabTableResult | None = None
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
