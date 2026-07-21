from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class MediationEffect:
    name: str
    predictor: str
    outcome: str
    b: float
    se: float
    t: float
    p_value: float
    ci: tuple[float, float]


@dataclass(frozen=True)
class MediationModelFit:
    outcome: str
    predictors: tuple[str, ...]
    r_squared: float


@dataclass(frozen=True)
class MediationResult:
    analysis_key: str
    title_ko: str
    x: str
    mediator: str
    y: str
    covariates: tuple[str, ...]
    n_total: int
    n_used: int
    n_excluded: int
    path_a: MediationEffect
    path_b: MediationEffect
    direct_effect: MediationEffect
    total_effect: MediationEffect
    indirect_effect: float
    indirect_ci: tuple[float, float]
    bootstrap_iterations: int
    bootstrap_seed: int
    bootstrap_ci_level: float
    mediator_model: MediationModelFit
    outcome_model: MediationModelFit
    total_model: MediationModelFit
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
