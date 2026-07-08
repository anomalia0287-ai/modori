from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class FactorPcaComponent:
    name: str
    eigenvalue: float | None = None
    explained_variance_ratio: float | None = None
    cumulative_variance_ratio: float | None = None


@dataclass(frozen=True)
class FactorPcaLoading:
    variable: str
    variable_label: str
    dimension: str
    loading: float


@dataclass(frozen=True)
class KmoResult:
    overall: float
    per_variable: dict[str, float]


@dataclass(frozen=True)
class BartlettSphericityResult:
    chi_square: float
    p_value: float


@dataclass(frozen=True)
class ParallelAnalysisResult:
    seed: int
    iterations: int
    percentile: float
    suggested_factor_count: int
    observed_eigenvalues: tuple[float, ...]
    random_mean_eigenvalues: tuple[float, ...]
    random_percentile_eigenvalues: tuple[float, ...]


@dataclass(frozen=True)
class FactorPcaResult:
    analysis_key: str
    title_ko: str
    method: str
    variables: tuple[str, ...]
    variable_labels: dict[str, str]
    n_total: int
    n_used: int
    n_excluded: int
    missing_policy: str
    rotation: str
    factor_count: int | None
    extraction_method: str | None
    components: tuple[FactorPcaComponent, ...]
    loadings: tuple[FactorPcaLoading, ...]
    communalities: dict[str, float]
    uniquenesses: dict[str, float]
    kmo: KmoResult | None
    bartlett: BartlettSphericityResult | None
    parallel_analysis: ParallelAnalysisResult | None
    warnings_ko: tuple[str, ...]
    notes_ko: tuple[str, ...]
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
