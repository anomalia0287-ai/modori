from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import importlib
import json
import math

import numpy as np
import pytest
from scipy import stats

from modori.factorial_anova_numerics import (
    evaluate_hypothesis,
    factorial_hypotheses,
    holm_adjust,
    marginal_estimates,
    simple_effect_hypotheses,
    summarize_factorial_cells,
)
from modori.results import ChartSpec
from modori.value_tokens import canonical_value_token


METHOD_DETAILS = {
    "sum_of_squares": "type_iii_equal_cell_weight",
    "contrast_basis": "scipy_helmert",
    "simple_effects": "interaction_gated_holm_one_family",
    "alpha": 0.05,
    "effect_size": "partial_eta_squared",
    "omega_squared": "omitted_unresolved_unbalanced_estimand",
    "tail_function": "scipy.stats.f.sf",
}


def _results():
    return importlib.import_module("modori.factorial_anova_results")


def _levels():
    results = _results()
    levels_a = tuple(
        results.FactorialLevel(
            factor_key="treatment",
            raw_value=value,
            token=canonical_value_token(value),
            label=label,
        )
        for value, label in (("control", "Control"), ("active", "Active"))
    )
    levels_b = tuple(
        results.FactorialLevel(
            factor_key="site",
            raw_value=value,
            token=canonical_value_token(value),
            label=label,
        )
        for value, label in ((1, "North"), (2, "South"))
    )
    return levels_a, levels_b


def _raw_cells() -> tuple[tuple[float, ...], ...]:
    means = (1.0, 2.0, 3.0, 8.0)
    offsets = (-0.3, -0.1, 0.1, 0.3)
    return tuple(tuple(mean + offset for offset in offsets) for mean in means)


def _valid_result():
    results = _results()
    levels_a, levels_b = _levels()
    moments = summarize_factorial_cells(_raw_cells())
    critical = float(stats.t.ppf(0.975, moments.df_error))
    cells = []
    for index, (level_a, level_b) in enumerate(
        (pair for level_a in levels_a for pair in ((level_a, levels_b[0]), (level_a, levels_b[1])))
    ):
        se = math.sqrt(moments.mse / moments.counts[index])
        cells.append(
            results.FactorialCellSummary(
                factor_a_level=level_a,
                factor_b_level=level_b,
                n=moments.counts[index],
                mean=moments.means[index],
                sd=moments.sample_sds[index],
                se=se,
                ci_low=moments.means[index] - critical * se,
                ci_high=moments.means[index] + critical * se,
            )
        )

    marginal_rows = tuple(
        results.FactorialMarginalSummary(
            factor_role="factor_a" if estimate.factor == "A" else "factor_b",
            level=(levels_a if estimate.factor == "A" else levels_b)[
                estimate.level_index
            ],
            mean=estimate.mean,
            se=estimate.se,
            ci_low=estimate.ci_low,
            ci_high=estimate.ci_high,
        )
        for estimate in marginal_estimates(moments, 2, 2)
    )
    effect_names = (
        ("factor_a", "Treatment"),
        ("factor_b", "Site"),
        ("interaction", "Treatment x Site"),
    )
    effect_stats = tuple(
        evaluate_hypothesis(moments, contrast)
        for contrast in factorial_hypotheses(2, 2)
    )
    effects = tuple(
        results.FactorialEffectResult(
            effect=effect,
            label=label,
            ss=value.ss,
            df_num=value.df_num,
            df_den=moments.df_error,
            ms=value.ms,
            f_value=value.f_value,
            p_value=value.p_value,
            partial_eta_squared=value.partial_eta_squared,
            condition_number=value.condition_number,
        )
        for (effect, label), value in zip(effect_names, effect_stats, strict=True)
    )

    simple_stats = tuple(
        evaluate_hypothesis(moments, contrast)
        for _, _, contrast in simple_effect_hypotheses(2, 2)
    )
    adjusted = holm_adjust(tuple(value.p_value for value in simple_stats))
    simple_effects = []
    for (direction, index, _), value, adjusted_p in zip(
        simple_effect_hypotheses(2, 2),
        simple_stats,
        adjusted,
        strict=True,
    ):
        tested = "factor_a" if direction == "A_within_B" else "factor_b"
        conditioning = "factor_b" if tested == "factor_a" else "factor_a"
        level = (levels_b if conditioning == "factor_b" else levels_a)[index]
        simple_effects.append(
            results.FactorialSimpleEffectResult(
                tested_factor=tested,
                conditioning_factor=conditioning,
                conditioning_level=level,
                ss=value.ss,
                df_num=value.df_num,
                df_den=moments.df_error,
                ms=value.ms,
                f_value=value.f_value,
                p_value=value.p_value,
                adjusted_p_value=adjusted_p,
                reject=adjusted_p < 0.05,
                partial_eta_squared=value.partial_eta_squared,
                condition_number=value.condition_number,
            )
        )

    assumptions = results.FactorialAssumptions(
        levene_status="available",
        levene_statistic=0.5,
        levene_p_value=0.5,
        shapiro_status="available",
        shapiro_statistic=0.98,
        shapiro_p_value=0.5,
        min_cell_n=4,
        max_cell_n=4,
        imbalance_ratio=1.0,
        zero_variance_cells=(),
    )
    warning_codes = (
        "high_missing_fraction",
        "small_cell",
        "significant_interaction",
    )
    chart = ChartSpec(
        type="factorial_interaction",
        title="Equal-cell Type III interaction plot",
        x_label="Treatment",
        y_label="Score",
        data={
            "factor_a": [
                {"token": level.token, "label": level.label} for level in levels_a
            ],
            "series": [
                {
                    "factor_b_token": level_b.token,
                    "factor_b_label": level_b.label,
                    "means": [cells[index * 2 + j].mean for index in range(2)],
                    "ci_low": [cells[index * 2 + j].ci_low for index in range(2)],
                    "ci_high": [cells[index * 2 + j].ci_high for index in range(2)],
                }
                for j, level_b in enumerate(levels_b)
            ],
        },
    )
    return results.FactorialAnovaResult(
        analysis_key="anova_factorial",
        dv="score",
        factor_a="treatment",
        factor_b="site",
        dv_label="Score",
        factor_a_label="Treatment",
        factor_b_label="Site",
        levels_a=levels_a,
        levels_b=levels_b,
        n_total=17,
        n_used=16,
        n_excluded=1,
        cells=tuple(cells),
        marginals=marginal_rows,
        effects=effects,
        sse=moments.sse,
        df_error=moments.df_error,
        mse=moments.mse,
        simple_effects=tuple(simple_effects),
        assumptions=assumptions,
        language="ko",
        warning_codes=warning_codes,
        warnings=tuple(
            results.render_factorial_warning(code, "ko") for code in warning_codes
        ),
        method_details=dict(METHOD_DETAILS),
        chart_specs=(chart,),
        apa_template_id="factorial_anova_v1",
    )


def test_factorial_level_preserves_typed_canonical_identity() -> None:
    results = _results()
    level = results.FactorialLevel(
        factor_key="condition",
        raw_value="control",
        token=canonical_value_token("control"),
        label="대조군",
    )

    assert level.token == canonical_value_token(level.raw_value)
    with pytest.raises(FrozenInstanceError):
        level.label = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"raw_value": ["unsupported"]}, "raw value"),
        ({"token": '{ "type": "str", "value": "control" }'}, "canonical"),
        ({"label": " \u200b "}, "label"),
        ({"factor_key": ""}, "factor key"),
    ],
)
def test_factorial_level_rejects_invalid_identity(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    values = {
        "factor_key": "condition",
        "raw_value": "control",
        "token": canonical_value_token("control"),
        "label": "Control",
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialLevel(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"n": 2}, "at least three"),
        ({"mean": np.nan}, "finite"),
        ({"sd": -0.1}, "nonnegative"),
        ({"se": 0.0}, "positive"),
        ({"ci_low": 2.0, "ci_high": 1.0}, "ordered"),
        ({"ci_low": 1.1}, "contain"),
    ],
)
def test_cell_summary_rejects_invalid_values(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    levels_a, levels_b = _levels()
    values = {
        "factor_a_level": levels_a[0],
        "factor_b_level": levels_b[0],
        "n": 3,
        "mean": 1.0,
        "sd": 0.0,
        "se": 0.2,
        "ci_low": 0.5,
        "ci_high": 1.5,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialCellSummary(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"effect": "other"}, "effect"),
        ({"ss": -0.1}, "nonnegative"),
        ({"df_num": 0}, "degrees"),
        ({"p_value": 1.1}, "between 0 and 1"),
        ({"partial_eta_squared": -0.1}, "between 0 and 1"),
        ({"ms": 9.0}, "SS divided"),
        ({"p_value": 0.5}, "survival"),
        ({"condition_number": 0.0}, "condition"),
        ({"ss": "4.0"}, "numeric"),
    ],
)
def test_effect_result_rejects_invalid_statistics(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    values = {
        "effect": "factor_a",
        "label": "Treatment",
        "ss": 4.0,
        "df_num": 2,
        "df_den": 20,
        "ms": 2.0,
        "f_value": 2.0,
        "p_value": float(stats.f.sf(2.0, 2, 20)),
        "partial_eta_squared": 0.2,
        "condition_number": 1.0,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialEffectResult(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"factor_role": "interaction"}, "factor role"),
        ({"se": 0.0}, "positive"),
        ({"ci_low": 2.0, "ci_high": 1.0}, "ordered"),
        ({"mean": "1.0"}, "numeric"),
    ],
)
def test_marginal_summary_rejects_invalid_values(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    values = {
        "factor_role": "factor_a",
        "level": _levels()[0][0],
        "mean": 1.0,
        "se": 0.2,
        "ci_low": 0.5,
        "ci_high": 1.5,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialMarginalSummary(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"tested_factor": "other"}, "tested factor"),
        ({"conditioning_factor": "factor_a"}, "conditioning factor"),
        ({"adjusted_p_value": -0.1}, "between 0 and 1"),
        ({"adjusted_p_value": 0.0}, "below raw"),
        ({"reject": 1}, "boolean"),
        ({"df_den": 0}, "degrees"),
    ],
)
def test_simple_effect_result_rejects_invalid_values(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    raw_p = float(stats.f.sf(2.0, 1, 20))
    values = {
        "tested_factor": "factor_a",
        "conditioning_factor": "factor_b",
        "conditioning_level": _levels()[1][0],
        "ss": 2.0,
        "df_num": 1,
        "df_den": 20,
        "ms": 2.0,
        "f_value": 2.0,
        "p_value": raw_p,
        "adjusted_p_value": min(1.0, raw_p * 2.0),
        "reject": False,
        "partial_eta_squared": 0.1,
        "condition_number": 1.0,
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialSimpleEffectResult(**values)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"levene_status": "omitted"}, "Levene status"),
        (
            {
                "levene_status": "unavailable",
                "levene_statistic": 0.5,
                "levene_p_value": 0.5,
            },
            "must be None",
        ),
        ({"shapiro_statistic": 1.1}, "between 0 and 1"),
        ({"min_cell_n": 2}, "at least 3"),
        ({"imbalance_ratio": 2.0}, "max n / min n"),
        ({"zero_variance_cells": (("not-a-token", "also-bad"),)}, "canonical"),
    ],
)
def test_assumptions_reject_invalid_states(
    changes: dict[str, object],
    message: str,
) -> None:
    results = _results()
    values = {
        "levene_status": "available",
        "levene_statistic": 0.5,
        "levene_p_value": 0.5,
        "shapiro_status": "available",
        "shapiro_statistic": 0.98,
        "shapiro_p_value": 0.5,
        "min_cell_n": 4,
        "max_cell_n": 4,
        "imbalance_ratio": 1.0,
        "zero_variance_cells": (),
    }
    values.update(changes)

    with pytest.raises(ValueError, match=message):
        results.FactorialAssumptions(**values)


@pytest.mark.parametrize("language", ["ko", "en", "ko-KR", "en-US"])
def test_warning_renderer_supports_frozen_languages(language: str) -> None:
    message = _results().render_factorial_warning("small_cell", language)

    assert isinstance(message, str)
    assert message.strip()


def test_warning_renderer_rejects_unknown_inputs() -> None:
    results = _results()
    with pytest.raises(ValueError, match="Unknown"):
        results.render_factorial_warning("unknown", "ko")
    with pytest.raises(ValueError, match="language"):
        results.render_factorial_warning("small_cell", "fr")


def test_warning_vocabulary_matches_the_frozen_policy() -> None:
    assert _results().FACTORIAL_WARNING_CODES == {
        "high_missing_fraction",
        "small_cell",
        "severe_imbalance",
        "zero_variance_cell",
        "levene_rejected",
        "levene_unavailable",
        "shapiro_rejected",
        "shapiro_omitted",
        "shapiro_unavailable",
        "significant_interaction",
    }


def test_valid_factorial_result_rechecks_every_cross_field_identity() -> None:
    result = _valid_result()

    assert len(result.cells) == 4
    assert [effect.effect for effect in result.effects] == [
        "factor_a",
        "factor_b",
        "interaction",
    ]
    assert len(result.simple_effects) == 4
    assert result.warning_codes == (
        "high_missing_fraction",
        "small_cell",
        "significant_interaction",
    )
    with pytest.raises(FrozenInstanceError):
        result.n_used = 0  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.method_details["alpha"] = 0.1  # type: ignore[index]
    with pytest.raises(TypeError):
        result.chart_specs[0].data["series"] = []
    with pytest.raises(TypeError):
        result.chart_specs[0].data["series"][0]["means"] = ()
    assert json.loads(json.dumps(result.chart_specs[0].data))["series"]


def _offset_result(offset: float):
    result = _valid_result()
    cells = tuple(
        replace(
            cell,
            mean=cell.mean + offset,
            ci_low=cell.ci_low + offset,
            ci_high=cell.ci_high + offset,
        )
        for cell in result.cells
    )
    marginals = tuple(
        replace(
            row,
            mean=row.mean + offset,
            ci_low=row.ci_low + offset,
            ci_high=row.ci_high + offset,
        )
        for row in result.marginals
    )
    b = len(result.levels_b)
    chart = replace(
        result.chart_specs[0],
        data={
            "factor_a": [
                {"token": level.token, "label": level.label}
                for level in result.levels_a
            ],
            "series": [
                {
                    "factor_b_token": level_b.token,
                    "factor_b_label": level_b.label,
                    "means": [
                        cells[index * b + j].mean
                        for index in range(len(result.levels_a))
                    ],
                    "ci_low": [
                        cells[index * b + j].ci_low
                        for index in range(len(result.levels_a))
                    ],
                    "ci_high": [
                        cells[index * b + j].ci_high
                        for index in range(len(result.levels_a))
                    ],
                }
                for j, level_b in enumerate(result.levels_b)
            ],
        },
    )
    return replace(
        result,
        cells=cells,
        marginals=marginals,
        chart_specs=(chart,),
    )


def test_large_location_marginal_drift_is_not_hidden_by_relative_tolerance() -> None:
    result = _offset_result(1e12)
    first = result.marginals[0]
    shifted = replace(
        first,
        mean=first.mean + 0.01,
        ci_low=first.ci_low + 0.01,
        ci_high=first.ci_high + 0.01,
    )

    with pytest.raises(ValueError, match="marginal mean"):
        replace(result, marginals=(shifted,) + result.marginals[1:])


def test_shapiro_omission_state_must_match_sample_size_policy() -> None:
    result = _valid_result()
    assumptions = replace(
        result.assumptions,
        shapiro_status="omitted",
        shapiro_statistic=None,
        shapiro_p_value=None,
    )
    warning_codes = result.warning_codes[:-1] + (
        "shapiro_omitted",
        "significant_interaction",
    )
    warnings = tuple(
        _results().render_factorial_warning(code, result.language)
        for code in warning_codes
    )

    with pytest.raises(ValueError, match="Shapiro policy"):
        replace(
            result,
            assumptions=assumptions,
            warning_codes=warning_codes,
            warnings=warnings,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: replace(value, n_total=18), "counts"),
        (lambda value: replace(value, cells=value.cells[:-1] + (value.cells[0],)), "Cartesian"),
        (lambda value: replace(value, df_error=value.df_error + 1), "error df"),
        (lambda value: replace(value, mse=value.mse * 2.0), "MSE"),
        (lambda value: replace(value, effects=(value.effects[1], value.effects[0], value.effects[2])), "order"),
        (
            lambda value: replace(
                value,
                effects=(
                    replace(
                        value.effects[0],
                        df_num=2,
                        ms=value.effects[0].ss / 2,
                        p_value=float(
                            stats.f.sf(
                                value.effects[0].f_value,
                                2,
                                value.effects[0].df_den,
                            )
                        ),
                    ),
                )
                + value.effects[1:],
            ),
            "numerator df",
        ),
        (
            lambda value: replace(
                value,
                marginals=(
                    replace(
                        value.marginals[0],
                        mean=value.marginals[0].mean + 1.0,
                        ci_low=value.marginals[0].ci_low + 1.0,
                        ci_high=value.marginals[0].ci_high + 1.0,
                    ),
                )
                + value.marginals[1:],
            ),
            "marginal mean",
        ),
        (lambda value: replace(value, marginals=(replace(value.marginals[0], se=value.marginals[0].se * 2.0),) + value.marginals[1:]), "marginal SE"),
        (lambda value: replace(value, simple_effects=()), "gate"),
        (lambda value: replace(value, simple_effects=(replace(value.simple_effects[0], adjusted_p_value=0.99, reject=False),) + value.simple_effects[1:]), "Holm"),
        (lambda value: replace(value, warning_codes=value.warning_codes[:-1], warnings=value.warnings[:-1]), "warning"),
        (lambda value: replace(value, chart_specs=(replace(value.chart_specs[0], data={**value.chart_specs[0].data, "series": []}),)), "chart"),
        (lambda value: replace(value, method_details={**value.method_details, "alpha": 0.1}), "method"),
    ],
)
def test_whole_result_rejects_cross_field_drift(mutation, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        mutation(_valid_result())


def test_whole_result_rejects_ambiguous_level_labels() -> None:
    result = _valid_result()
    duplicate = replace(result.levels_a[1], label=" control ")

    with pytest.raises(ValueError, match="display labels"):
        replace(result, levels_a=(result.levels_a[0], duplicate))


def test_simple_effects_must_be_absent_when_interaction_gate_is_closed() -> None:
    result = _valid_result()
    interaction = replace(
        result.effects[2],
        f_value=0.0,
        p_value=1.0,
        ss=0.0,
        ms=0.0,
        partial_eta_squared=0.0,
    )
    effects = result.effects[:2] + (interaction,)
    warning_codes = result.warning_codes[:-1]
    warnings = result.warnings[:-1]

    closed = replace(
        result,
        effects=effects,
        simple_effects=(),
        warning_codes=warning_codes,
        warnings=warnings,
    )
    assert closed.simple_effects == ()

    with pytest.raises(ValueError, match="gate"):
        replace(closed, simple_effects=result.simple_effects)
