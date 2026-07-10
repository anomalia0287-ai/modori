from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
import math
from numbers import Real
import warnings

import numpy as np
from scipy import stats

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable
from modori.factorial_anova_numerics import (
    FactorialMoments,
    HypothesisStatistic,
    evaluate_hypothesis,
    decimal_location_summary,
    factorial_hypotheses,
    holm_adjust,
    marginal_estimates,
    simple_effect_hypotheses,
    summarize_factorial_cells,
)
from modori.factorial_anova_results import (
    FACTORIAL_METHOD_DETAILS,
    FactorialAnovaResult,
    FactorialAssumptions,
    FactorialCellSummary,
    FactorialEffectResult,
    FactorialLevel,
    FactorialMarginalSummary,
    FactorialSimpleEffectResult,
    render_factorial_warning,
)
from modori.results import ChartSpec
from modori.value_tokens import (
    canonical_value_token,
    decode_value_token,
    display_label_key,
    display_value_label,
    normalized_value_key,
)


_TOP_LEVEL_KEYS = {
    "schema_version",
    "dv",
    "factor_a",
    "factor_b",
    "factor_a_levels",
    "factor_b_levels",
    "factorial_policy",
    "language",
}
_POLICY_KEYS = {"sum_of_squares", "simple_effects", "alpha"}
_FACTOR_MEASURES = {Measure.NOMINAL, Measure.ORDINAL}


@dataclass
class FactorialAnovaStep(Step):
    step_type = "stats.anova_factorial"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "dv": "score",
            "factor_a": "treatment",
            "factor_b": "site",
            "factor_a_levels": ["control", "active"],
            "factor_b_levels": [1, 2],
            "factorial_policy": {
                "sum_of_squares": "type_iii_equal_cell_weight",
                "simple_effects": "interaction_gated_holm",
                "alpha": 0.05,
            },
            "language": "ko",
        },
        "newer": {
            "schema_version": 999,
            "dv": "score",
            "factor_a": "treatment",
            "factor_b": "site",
        },
        "unknown_current": {
            "schema_version": 1,
            "dv": "score",
            "factor_a": "treatment",
            "factor_b": "site",
            "factor_a_levels": ["control", "active"],
            "factor_b_levels": [1, 2],
            "factorial_policy": {
                "sum_of_squares": "type_iii_equal_cell_weight",
                "simple_effects": "interaction_gated_holm",
                "alpha": 0.05,
            },
            "language": "ko",
            "extra": True,
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        migrated = dict(params)
        version = migrated.get("schema_version")
        if version is None:
            raise ValueError("anova_factorial params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("anova_factorial schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("anova_factorial params use a newer schema_version")
        if version < cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(f"unsupported anova_factorial schema_version: {version}")
        return migrated

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        unknown = set(params) - _TOP_LEVEL_KEYS
        if unknown:
            raise ValueError(
                f"unknown anova_factorial params: {', '.join(sorted(unknown))}"
            )
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("anova_factorial params were not migrated")
        roles = tuple(
            _required_key(params.get(key), f"anova_factorial {key}")
            for key in ("dv", "factor_a", "factor_b")
        )
        if len(set(roles)) != 3:
            raise ValueError("anova_factorial roles must be distinct")
        levels_a = _validate_level_params(params.get("factor_a_levels"), "factor_a")
        levels_b = _validate_level_params(params.get("factor_b_levels"), "factor_b")
        language = params.get("language")
        if language not in {"ko", "en"}:
            raise ValueError("anova_factorial language must be 'ko' or 'en'")
        policy = params.get("factorial_policy")
        if not isinstance(policy, Mapping):
            raise ValueError("anova_factorial factorial_policy must be an object")
        clean_policy = _validate_policy(policy)
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "dv": roles[0],
            "factor_a": roles[1],
            "factor_b": roles[2],
            "factor_a_levels": levels_a,
            "factor_b_levels": levels_b,
            "factorial_policy": clean_policy,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx.dataset, params)
        return StepResult(
            analysis=result,
            notes=[
                "Computed complete-cell two-factor ANOVA with equal-cell-weight "
                "Type III hypotheses."
            ],
        )

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return {
            str(params["dv"]),
            str(params["factor_a"]),
            str(params["factor_b"]),
        }

    def writes(self) -> set[str]:
        return {f"analysis:{self.id}"}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return (
            f"Complete-cell factorial ANOVA for {params['dv']} by "
            f"{params['factor_a']} and {params['factor_b']}"
        )

    def _compute_result(
        self,
        dataset: Dataset,
        params: dict[str, object],
    ) -> FactorialAnovaResult:
        dv = str(params["dv"])
        factor_a = str(params["factor_a"])
        factor_b = str(params["factor_b"])
        self._validate_dataset(dataset, dv, factor_a, factor_b)

        source = _frame_for_factorial_compute(dataset, (dv, factor_a, factor_b))
        n_total = int(len(source))
        frame = source.dropna(axis=0, how="any")
        n_used = int(len(frame))
        n_excluded = n_total - n_used
        if n_used == 0:
            raise ValueError("anova_factorial has no complete rows after listwise deletion")

        outcomes = tuple(_outcome_value(value) for value in frame[dv].tolist())
        declared_a = tuple(params["factor_a_levels"])
        declared_b = tuple(params["factor_b_levels"])
        identities_a = tuple(normalized_value_key(value) for value in declared_a)
        identities_b = tuple(normalized_value_key(value) for value in declared_b)
        observed_a = tuple(_factor_identity(value, factor_a) for value in frame[factor_a].tolist())
        observed_b = tuple(_factor_identity(value, factor_b) for value in frame[factor_b].tolist())
        if set(observed_a) != set(identities_a):
            raise ValueError("anova_factorial factor_a observed levels do not match declared levels")
        if set(observed_b) != set(identities_b):
            raise ValueError("anova_factorial factor_b observed levels do not match declared levels")

        levels_a = _result_levels(dataset.variables[factor_a], declared_a)
        levels_b = _result_levels(dataset.variables[factor_b], declared_b)
        _validate_display_labels(levels_a, "factor_a")
        _validate_display_labels(levels_b, "factor_b")

        grouped: dict[tuple[tuple[str, object], tuple[str, object]], list[object]] = {
            (identity_a, identity_b): []
            for identity_a in identities_a
            for identity_b in identities_b
        }
        for outcome, identity_a, identity_b in zip(
            outcomes,
            observed_a,
            observed_b,
            strict=True,
        ):
            grouped[(identity_a, identity_b)].append(outcome)
        cell_values = tuple(
            tuple(grouped[(identity_a, identity_b)])
            for identity_a in identities_a
            for identity_b in identities_b
        )
        if any(len(values) == 0 for values in cell_values):
            raise ValueError("anova_factorial requires a complete Cartesian cell product")
        if any(len(values) < 3 for values in cell_values):
            raise ValueError("anova_factorial requires at least three complete rows per cell")

        moments = summarize_factorial_cells(cell_values)
        a = len(levels_a)
        b = len(levels_b)
        omnibus_matrices = factorial_hypotheses(a, b)
        interaction_statistic = evaluate_hypothesis(moments, omnibus_matrices[2])
        statistic_a = evaluate_hypothesis(moments, omnibus_matrices[0])
        statistic_b = evaluate_hypothesis(moments, omnibus_matrices[1])
        dv_label = _variable_label(dataset.variables[dv], dv)
        factor_a_label = _variable_label(dataset.variables[factor_a], factor_a)
        factor_b_label = _variable_label(dataset.variables[factor_b], factor_b)
        effects = (
            _effect_result("factor_a", factor_a_label, statistic_a, moments.df_error),
            _effect_result("factor_b", factor_b_label, statistic_b, moments.df_error),
            _effect_result(
                "interaction",
                f"{factor_a_label} x {factor_b_label}",
                interaction_statistic,
                moments.df_error,
            ),
        )
        cells = _cell_summaries(moments, levels_a, levels_b)
        marginals = _marginal_summaries(moments, levels_a, levels_b)
        simple_effects = _simple_effect_results(
            moments,
            levels_a,
            levels_b,
            interaction_statistic,
        )
        assumptions = _assumptions(moments, levels_a, levels_b)
        warning_codes = _warning_codes(
            n_total=n_total,
            n_excluded=n_excluded,
            assumptions=assumptions,
            interaction_p=interaction_statistic.p_value,
        )
        language = str(params["language"])
        warnings_rendered = tuple(
            render_factorial_warning(code, language) for code in warning_codes
        )
        chart = _interaction_chart(
            cells,
            levels_a,
            levels_b,
            factor_a_label=factor_a_label,
            factor_b_label=factor_b_label,
            dv_label=dv_label,
        )
        return FactorialAnovaResult(
            analysis_key="anova_factorial",
            dv=dv,
            factor_a=factor_a,
            factor_b=factor_b,
            dv_label=dv_label,
            factor_a_label=factor_a_label,
            factor_b_label=factor_b_label,
            levels_a=levels_a,
            levels_b=levels_b,
            n_total=n_total,
            n_used=n_used,
            n_excluded=n_excluded,
            cells=cells,
            marginals=marginals,
            effects=effects,
            sse=moments.sse,
            df_error=moments.df_error,
            mse=moments.mse,
            simple_effects=simple_effects,
            assumptions=assumptions,
            language=language,
            warning_codes=warning_codes,
            warnings=warnings_rendered,
            method_details=dict(FACTORIAL_METHOD_DETAILS),
            chart_specs=(chart,),
            apa_template_id="factorial_anova_v1",
        )

    @staticmethod
    def _validate_dataset(
        dataset: Dataset,
        dv: str,
        factor_a: str,
        factor_b: str,
    ) -> None:
        if dataset.df.empty:
            raise ValueError("anova_factorial cannot run on an empty dataset")
        missing = [
            key for key in (dv, factor_a, factor_b) if key not in dataset.variables
        ]
        if missing:
            raise ValueError(
                f"anova_factorial variables are missing: {', '.join(missing)}"
            )
        if dataset.variables[dv].measure is not Measure.SCALE:
            raise ValueError("anova_factorial dv must have scale measure")
        if dataset.variables[factor_a].measure not in _FACTOR_MEASURES or (
            dataset.variables[factor_b].measure not in _FACTOR_MEASURES
        ):
            raise ValueError(
                "anova_factorial factors must have nominal or ordinal measures"
            )


def _required_key(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_level_params(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or not 2 <= len(value) <= 6:
        raise ValueError(f"anova_factorial {label}_levels must contain 2 through 6 values")
    clean: list[object] = []
    identities: list[tuple[str, object]] = []
    for raw in value:
        try:
            scalar = decode_value_token(canonical_value_token(raw))
        except ValueError as exc:
            raise ValueError(
                f"anova_factorial {label}_levels must contain supported scalar values"
            ) from exc
        clean.append(scalar)
        identities.append(normalized_value_key(scalar))
    if len(set(identities)) != len(identities):
        raise ValueError(f"anova_factorial {label}_levels must be unique")
    return clean


def _validate_policy(policy: Mapping[str, object]) -> dict[str, object]:
    unknown = set(policy) - _POLICY_KEYS
    if unknown:
        raise ValueError(
            f"unknown factorial_policy keys: {', '.join(sorted(unknown))}"
        )
    if set(policy) != _POLICY_KEYS:
        missing = _POLICY_KEYS - set(policy)
        raise ValueError(
            f"factorial_policy is missing keys: {', '.join(sorted(missing))}"
        )
    if policy.get("sum_of_squares") != "type_iii_equal_cell_weight":
        raise ValueError(
            "factorial_policy sum_of_squares must be type_iii_equal_cell_weight"
        )
    if policy.get("simple_effects") != "interaction_gated_holm":
        raise ValueError(
            "factorial_policy simple_effects must be interaction_gated_holm"
        )
    alpha = policy.get("alpha")
    if (
        isinstance(alpha, bool)
        or not isinstance(alpha, Real)
        or not math.isfinite(float(alpha))
        or float(alpha) != 0.05
    ):
        raise ValueError("factorial_policy alpha must be exactly 0.05")
    return {
        "sum_of_squares": "type_iii_equal_cell_weight",
        "simple_effects": "interaction_gated_holm",
        "alpha": 0.05,
    }


def _outcome_value(value: object) -> object:
    if isinstance(value, bool | np.bool_):
        raise ValueError("anova_factorial outcomes must be non-boolean numeric values")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("anova_factorial outcomes must be finite")
        return value
    if not isinstance(value, Real):
        raise ValueError("anova_factorial outcomes must be non-boolean numeric values")
    if not math.isfinite(float(value)):
        raise ValueError("anova_factorial outcomes must be finite")
    return value


def _frame_for_factorial_compute(
    dataset: Dataset,
    columns: tuple[str, str, str],
):
    frame = dataset.df.loc[:, list(columns)].copy(deep=True)
    for column in columns:
        markers = dataset.variables[column].missing_values
        if not markers:
            continue
        mask = frame[column].map(
            lambda value: any(
                _matches_declared_missing(value, marker) for marker in markers
            )
        )
        frame[column] = frame[column].mask(mask)
    return frame


def _matches_declared_missing(value: object, marker: object) -> bool:
    if isinstance(value, bool | np.bool_) or isinstance(marker, bool | np.bool_):
        return isinstance(value, bool | np.bool_) and isinstance(
            marker, bool | np.bool_
        ) and bool(value) == bool(marker)
    if isinstance(value, Decimal):
        if not value.is_finite() or not isinstance(marker, Real):
            return False
        return value == Decimal(str(marker))
    value_identity = _optional_factor_identity(value)
    marker_identity = _optional_factor_identity(marker)
    return value_identity is not None and value_identity == marker_identity


def _optional_factor_identity(value: object) -> tuple[str, object] | None:
    try:
        return normalized_value_key(value)
    except ValueError:
        return None


def _factor_identity(value: object, factor_key: str) -> tuple[str, object]:
    try:
        return normalized_value_key(value)
    except ValueError as exc:
        raise ValueError(
            f"anova_factorial factor {factor_key} contains an unsupported level"
        ) from exc


def _result_levels(
    variable: Variable,
    values: tuple[object, ...],
) -> tuple[FactorialLevel, ...]:
    rows: list[FactorialLevel] = []
    for value in values:
        token = canonical_value_token(value)
        scalar = decode_value_token(token)
        rows.append(
            FactorialLevel(
                factor_key=variable.name,
                raw_value=scalar,
                token=token,
                label=display_value_label(variable, scalar),
            )
        )
    return tuple(rows)


def _validate_display_labels(
    levels: tuple[FactorialLevel, ...],
    factor_name: str,
) -> None:
    keys = tuple(display_label_key(level.label) for level in levels)
    if any(not key for key in keys):
        raise ValueError(f"anova_factorial {factor_name} display labels are blank")
    if len(set(keys)) != len(keys):
        raise ValueError(
            f"anova_factorial {factor_name} has ambiguous display labels"
        )


def _variable_label(variable: Variable, fallback: str) -> str:
    if variable.label is not None and display_label_key(variable.label):
        return variable.label.strip()
    return fallback


def _effect_result(
    effect: str,
    label: str,
    value: HypothesisStatistic,
    df_error: int,
) -> FactorialEffectResult:
    return FactorialEffectResult(
        effect=effect,
        label=label,
        ss=value.ss,
        df_num=value.df_num,
        df_den=df_error,
        ms=value.ms,
        f_value=value.f_value,
        p_value=value.p_value,
        partial_eta_squared=value.partial_eta_squared,
        condition_number=value.condition_number,
    )


def _cell_summaries(
    moments: FactorialMoments,
    levels_a: tuple[FactorialLevel, ...],
    levels_b: tuple[FactorialLevel, ...],
) -> tuple[FactorialCellSummary, ...]:
    critical = float(stats.t.ppf(0.975, moments.df_error))
    rows: list[FactorialCellSummary] = []
    for level_a in levels_a:
        for level_b in levels_b:
            index = len(rows)
            se = math.sqrt(moments.mse / moments.counts[index])
            mean, ci_low, ci_high = decimal_location_summary(
                moments.decimal_means[index],
                se,
                critical,
            )
            rows.append(
                FactorialCellSummary(
                    factor_a_level=level_a,
                    factor_b_level=level_b,
                    n=moments.counts[index],
                    mean=mean,
                    sd=moments.sample_sds[index],
                    se=se,
                    ci_low=ci_low,
                    ci_high=ci_high,
                )
            )
    return tuple(rows)


def _marginal_summaries(
    moments: FactorialMoments,
    levels_a: tuple[FactorialLevel, ...],
    levels_b: tuple[FactorialLevel, ...],
) -> tuple[FactorialMarginalSummary, ...]:
    rows = marginal_estimates(moments, len(levels_a), len(levels_b))
    return tuple(
        FactorialMarginalSummary(
            factor_role="factor_a" if row.factor == "A" else "factor_b",
            level=(levels_a if row.factor == "A" else levels_b)[row.level_index],
            mean=row.mean,
            se=row.se,
            ci_low=row.ci_low,
            ci_high=row.ci_high,
        )
        for row in rows
    )


def _simple_effect_results(
    moments: FactorialMoments,
    levels_a: tuple[FactorialLevel, ...],
    levels_b: tuple[FactorialLevel, ...],
    interaction: HypothesisStatistic,
) -> tuple[FactorialSimpleEffectResult, ...]:
    if interaction.p_value >= 0.05:
        return ()
    hypotheses = simple_effect_hypotheses(len(levels_a), len(levels_b))
    statistics = tuple(
        evaluate_hypothesis(moments, matrix) for _, _, matrix in hypotheses
    )
    adjusted = holm_adjust(tuple(value.p_value for value in statistics))
    rows: list[FactorialSimpleEffectResult] = []
    for (direction, index, _), value, adjusted_p in zip(
        hypotheses,
        statistics,
        adjusted,
        strict=True,
    ):
        tested_factor = "factor_a" if direction == "A_within_B" else "factor_b"
        conditioning_factor = (
            "factor_b" if tested_factor == "factor_a" else "factor_a"
        )
        conditioning_level = (
            levels_b if conditioning_factor == "factor_b" else levels_a
        )[index]
        rows.append(
            FactorialSimpleEffectResult(
                tested_factor=tested_factor,
                conditioning_factor=conditioning_factor,
                conditioning_level=conditioning_level,
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
    return tuple(rows)


def _assumptions(
    moments: FactorialMoments,
    levels_a: tuple[FactorialLevel, ...],
    levels_b: tuple[FactorialLevel, ...],
) -> FactorialAssumptions:
    levene_status, levene_statistic, levene_p = _levene_diagnostic(
        moments.residual_groups
    )
    shapiro_status, shapiro_statistic, shapiro_p = _shapiro_diagnostic(
        moments.residual_groups
    )
    minimum = min(moments.counts)
    maximum = max(moments.counts)
    zero_variance = tuple(
        (levels_a[index // len(levels_b)].token, levels_b[index % len(levels_b)].token)
        for index, sample_sd in enumerate(moments.sample_sds)
        if sample_sd == 0.0
    )
    return FactorialAssumptions(
        levene_status=levene_status,
        levene_statistic=levene_statistic,
        levene_p_value=levene_p,
        shapiro_status=shapiro_status,
        shapiro_statistic=shapiro_statistic,
        shapiro_p_value=shapiro_p,
        min_cell_n=minimum,
        max_cell_n=maximum,
        imbalance_ratio=maximum / minimum,
        zero_variance_cells=zero_variance,
    )


def _levene_diagnostic(
    residual_groups: tuple[tuple[float, ...], ...],
) -> tuple[str, float | None, float | None]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            warnings.simplefilter("error", UserWarning)
            result = stats.levene(*residual_groups, center="median")
    except (RuntimeWarning, UserWarning, ValueError, FloatingPointError):
        return "unavailable", None, None
    return _available_diagnostic(result.statistic, result.pvalue)


def _shapiro_diagnostic(
    residual_groups: tuple[tuple[float, ...], ...],
) -> tuple[str, float | None, float | None]:
    residuals = tuple(value for group in residual_groups for value in group)
    if len(residuals) > 5000:
        return "omitted", None, None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            warnings.simplefilter("error", UserWarning)
            result = stats.shapiro(residuals)
    except (RuntimeWarning, UserWarning, ValueError, FloatingPointError):
        return "unavailable", None, None
    return _available_diagnostic(
        result.statistic,
        result.pvalue,
        statistic_is_probability=True,
    )


def _available_diagnostic(
    statistic: object,
    p_value: object,
    *,
    statistic_is_probability: bool = False,
) -> tuple[str, float | None, float | None]:
    try:
        statistic_value = float(statistic)
        p = float(p_value)
    except (TypeError, ValueError, OverflowError):
        return "unavailable", None, None
    if (
        not math.isfinite(statistic_value)
        or not math.isfinite(p)
        or statistic_value < 0.0
        or (statistic_is_probability and statistic_value > 1.0)
        or not 0.0 <= p <= 1.0
    ):
        return "unavailable", None, None
    return "available", statistic_value, p


def _warning_codes(
    *,
    n_total: int,
    n_excluded: int,
    assumptions: FactorialAssumptions,
    interaction_p: float,
) -> tuple[str, ...]:
    codes: list[str] = []
    if n_excluded / n_total > 0.05:
        codes.append("high_missing_fraction")
    if assumptions.min_cell_n < 10:
        codes.append("small_cell")
    if assumptions.imbalance_ratio > 10.0:
        codes.append("severe_imbalance")
    if assumptions.zero_variance_cells:
        codes.append("zero_variance_cell")
    if assumptions.levene_status == "unavailable":
        codes.append("levene_unavailable")
    elif assumptions.levene_p_value is not None and assumptions.levene_p_value < 0.05:
        codes.append("levene_rejected")
    if assumptions.shapiro_status == "omitted":
        codes.append("shapiro_omitted")
    elif assumptions.shapiro_status == "unavailable":
        codes.append("shapiro_unavailable")
    elif assumptions.shapiro_p_value is not None and assumptions.shapiro_p_value < 0.05:
        codes.append("shapiro_rejected")
    if interaction_p < 0.05:
        codes.append("significant_interaction")
    return tuple(codes)


def _interaction_chart(
    cells: tuple[FactorialCellSummary, ...],
    levels_a: tuple[FactorialLevel, ...],
    levels_b: tuple[FactorialLevel, ...],
    *,
    factor_a_label: str,
    factor_b_label: str,
    dv_label: str,
) -> ChartSpec:
    b = len(levels_b)
    return ChartSpec(
        type="factorial_interaction",
        title="Equal-cell Type III interaction plot",
        x_label=factor_a_label,
        y_label=dv_label,
        data={
            "factor_b_label": factor_b_label,
            "factor_a": [
                {"token": level.token, "label": level.label} for level in levels_a
            ],
            "series": [
                {
                    "factor_b_token": level_b.token,
                    "factor_b_label": level_b.label,
                    "means": [cells[index * b + j].mean for index in range(len(levels_a))],
                    "ci_low": [cells[index * b + j].ci_low for index in range(len(levels_a))],
                    "ci_high": [cells[index * b + j].ci_high for index in range(len(levels_a))],
                }
                for j, level_b in enumerate(levels_b)
            ],
        },
    )


Step.register_type(FactorialAnovaStep.step_type, FactorialAnovaStep)
