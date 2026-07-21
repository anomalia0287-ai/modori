from __future__ import annotations

from dataclasses import dataclass

from modori.results import ChartSpec


@dataclass(frozen=True)
class ConditionalIndirectEffect:
    moderator_label: str
    moderator_value: float
    effect: float
    ci: tuple[float, float]


@dataclass(frozen=True)
class ModeratedMediationModelFit:
    outcome: str
    predictors: tuple[str, ...]
    r_squared: float


@dataclass(frozen=True)
class ModeratedMediationResult:
    analysis_key: str
    title_ko: str
    model: int
    x: str
    mediator: str
    moderator: str
    y: str
    covariates: tuple[str, ...]
    n_total: int
    n_used: int
    n_excluded: int
    moderator_mean: float
    moderator_sd: float
    conditional_effects: tuple[ConditionalIndirectEffect, ...]
    index_of_moderated_mediation: float
    index_ci: tuple[float, float]
    bootstrap_iterations: int
    bootstrap_seed: int
    bootstrap_ci_level: float
    mediator_model: ModeratedMediationModelFit
    outcome_model: ModeratedMediationModelFit
    warnings_ko: tuple[str, ...] = ()
    notes_ko: tuple[str, ...] = ()
    apa_template_id: str | None = None
    chart_spec: ChartSpec | None = None
    no_canonical_chart_reason_ko: str | None = None
