from __future__ import annotations

from itertools import product
from types import SimpleNamespace

import pandas as pd

from modori.core import Dataset, Measure, Variable
from modori.recommendation_policy import RecommendationRoutingTier
from modori.recommendations import RecommendationService


def _provider():
    from modori.anova_factorial_recommendation import eligibility_provider

    return eligibility_provider()


def _dataset(
    *,
    factor_levels: dict[str, tuple[object, ...]] | None = None,
    outcome_keys: tuple[str, ...] = ("score",),
    rows_per_cell: int = 3,
    omitted_cells: set[tuple[object, ...]] | None = None,
) -> Dataset:
    factor_levels = factor_levels or {
        "condition": ("control", "active"),
        "site": (1, 2),
    }
    omitted_cells = omitted_cells or set()
    rows: list[dict[str, object]] = []
    for cell_index, combination in enumerate(product(*factor_levels.values())):
        if combination in omitted_cells:
            continue
        for replicate in range(rows_per_cell):
            row = {
                key: value
                for key, value in zip(factor_levels, combination, strict=True)
            }
            for outcome_index, outcome_key in enumerate(outcome_keys):
                row[outcome_key] = (
                    10.0 * (outcome_index + 1)
                    + cell_index
                    + 0.1 * replicate
                )
            rows.append(row)
    frame = pd.DataFrame(rows, columns=[*outcome_keys, *factor_levels])
    variables = {
        key: Variable(
            name=key,
            label=key,
            measure=Measure.SCALE,
            value_labels={},
            missing_values=[],
            dtype=str(frame[key].dtype),
            origin_step_id="fixture",
        )
        for key in outcome_keys
    }
    variables.update(
        {
            key: Variable(
                name=key,
                label=key,
                measure=Measure.NOMINAL,
                value_labels={},
                missing_values=[],
                dtype=str(frame[key].dtype),
                origin_step_id="fixture",
            )
            for key in factor_levels
        }
    )
    return Dataset(df=frame, variables=variables)


def _with_column(
    dataset: Dataset,
    key: str,
    values: list[object],
    *,
    measure: Measure,
) -> Dataset:
    frame = dataset.df.copy(deep=True)
    frame[key] = values
    variables = dict(dataset.variables)
    variables[key] = Variable(
        name=key,
        label=key,
        measure=measure,
        value_labels={},
        missing_values=[],
        dtype=str(frame[key].dtype),
        origin_step_id="fixture",
    )
    return Dataset(df=frame, variables=variables)


def test_factorial_provider_emits_configuration_required_complete_cell_candidate() -> None:
    candidates = _provider().candidates(_dataset())

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_id == "anova_factorial:score:condition:site"
    assert candidate.kind == "anova_factorial"
    assert candidate.routing_tier is RecommendationRoutingTier.SECONDARY
    assert candidate.outcome_key == "score"
    assert candidate.factor_a_key == "condition"
    assert candidate.factor_b_key == "site"
    assert candidate.requires_configuration is True


def test_factorial_provider_requires_exactly_two_plausible_factors() -> None:
    provider = _provider()

    assert provider.candidates(
        _dataset(factor_levels={"condition": ("control", "active")})
    ) == []
    assert provider.candidates(
        _dataset(
            factor_levels={
                "condition": ("control", "active"),
                "site": (1, 2),
                "cohort": ("first", "second"),
            }
        )
    ) == []


def test_factorial_provider_abstains_when_multiple_scale_outcomes_are_plausible() -> None:
    candidates = _provider().candidates(
        _dataset(outcome_keys=("score_a", "score_b"))
    )

    assert candidates == []


def test_factorial_provider_rejects_one_or_seven_level_factors() -> None:
    provider = _provider()

    assert provider.candidates(
        _dataset(
            factor_levels={
                "condition": ("only",),
                "site": (1, 2),
            }
        )
    ) == []
    assert provider.candidates(
        _dataset(
            factor_levels={
                "condition": tuple(range(7)),
                "site": (1, 2),
            }
        )
    ) == []


def test_factorial_provider_rejects_incomplete_or_low_count_cells() -> None:
    provider = _provider()

    assert provider.candidates(
        _dataset(omitted_cells={("active", 2)})
    ) == []
    assert provider.candidates(_dataset(rows_per_cell=2)) == []


def test_factorial_provider_ignores_unique_admin_id_but_rejects_repeated_id_evidence() -> None:
    provider = _provider()
    dataset = _dataset()
    unique = _with_column(
        dataset,
        "participant_id",
        list(range(len(dataset.df))),
        measure=Measure.NOMINAL,
    )
    repeated = _with_column(
        dataset,
        "participant_id",
        [index // 2 for index in range(len(dataset.df))],
        measure=Measure.NOMINAL,
    )

    assert len(provider.candidates(unique)) == 1
    assert provider.candidates(repeated) == []

    repeated_case_id = _with_column(
        dataset,
        "case_id",
        [index // 2 for index in range(len(dataset.df))],
        measure=Measure.NOMINAL,
    )
    assert provider.candidates(repeated_case_id) == []


def test_factorial_provider_rejects_non_scale_outcome_and_declared_structures() -> None:
    provider = _provider()
    dataset = _dataset()
    non_scale_variables = dict(dataset.variables)
    non_scale_variables["score"] = Variable(
        name="score",
        label="score",
        measure=Measure.ORDINAL,
        value_labels={},
        missing_values=[],
        dtype=str(dataset.df["score"].dtype),
        origin_step_id="fixture",
    )
    non_scale = Dataset(df=dataset.df, variables=non_scale_variables)

    assert provider.candidates(non_scale) == []
    for attribute in ("weights", "clusters", "repeated_id"):
        wrapped = SimpleNamespace(
            df=dataset.df,
            variables=dataset.variables,
            **{attribute: [1]},
        )
        assert provider.candidates(wrapped) == []


def test_factorial_provider_suppresses_active_analysis_and_is_row_order_stable() -> None:
    provider = _provider()
    dataset = _dataset(outcome_keys=("score_a", "score_b"))
    permuted = Dataset(
        df=dataset.df.sample(frac=1.0, random_state=23).reset_index(drop=True),
        variables=dataset.variables,
    )

    assert provider.candidates(dataset, active_analysis=True) == []
    assert provider.candidates(dataset) == provider.candidates(permuted)


def test_factorial_provider_rejects_scale_metadata_over_numeric_strings() -> None:
    dataset = _dataset()
    frame = dataset.df.copy(deep=True)
    frame["score"] = frame["score"].map(str)
    variables = dict(dataset.variables)
    variables["score"] = Variable(
        name="score",
        label="score",
        measure=Measure.SCALE,
        value_labels={},
        missing_values=[],
        dtype=str(frame["score"].dtype),
        origin_step_id="fixture",
    )

    assert _provider().candidates(Dataset(df=frame, variables=variables)) == []


def test_factorial_candidate_is_never_default_and_has_configuration_message() -> None:
    state = RecommendationService(providers=[_provider()]).recommend(_dataset())

    assert len(state.candidates) == 1
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
    assert "설정 확인" in state.message_ko


def test_default_recommendation_service_registers_factorial_after_oneway() -> None:
    service = RecommendationService()

    module_keys = [provider.module_key for provider in service._providers]
    state = service.recommend(_dataset())

    assert module_keys.index("anova_factorial") == module_keys.index("anova_oneway") + 1
    candidate = next(
        candidate for candidate in state.candidates if candidate.kind == "anova_factorial"
    )
    assert candidate.requires_configuration is True
    assert state.selected_candidate is None
    assert not hasattr(state, "default_candidate")
