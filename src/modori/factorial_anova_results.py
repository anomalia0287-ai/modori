from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, TypeAlias

from scipy import stats

from modori.factorial_anova_numerics import holm_adjust
from modori.results import ChartSpec
from modori.value_tokens import (
    canonical_value_token,
    decode_value_token,
    display_label_key,
    normalized_value_key,
)


ScalarValue: TypeAlias = bool | int | float | str


class _FrozenDict(dict[str, Any]):
    def _immutable(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("Frozen factorial mappings cannot be modified")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __copy__(self) -> _FrozenDict:
        return self

    def __deepcopy__(self, _memo: dict[int, object]) -> _FrozenDict:
        return self


def _freeze_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _FrozenDict(
            {str(key): _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


FACTORIAL_METHOD_DETAILS: Mapping[str, object] = _FrozenDict({
    "sum_of_squares": "type_iii_equal_cell_weight",
    "contrast_basis": "scipy_helmert",
    "simple_effects": "interaction_gated_holm_one_family",
    "alpha": 0.05,
    "effect_size": "partial_eta_squared",
    "omega_squared": "omitted_unresolved_unbalanced_estimand",
    "tail_function": "scipy.stats.f.sf",
})

FACTORIAL_WARNING_TEXTS: Mapping[str, Mapping[str, str]] = _freeze_value({  # type: ignore[assignment]
    "high_missing_fraction": {
        "ko": "목록별 결측 제거로 전체 행의 5%를 초과해 제외했습니다.",
        "en": "Listwise deletion excluded more than 5% of all rows.",
    },
    "small_cell": {
        "ko": "하나 이상의 셀에 완전 관측 행이 10개 미만입니다.",
        "en": "One or more cells contain fewer than 10 complete observations.",
    },
    "severe_imbalance": {
        "ko": "최대 셀과 최소 셀의 표본 수 비가 10을 초과합니다.",
        "en": "The largest-to-smallest cell-count ratio exceeds 10.",
    },
    "zero_variance_cell": {
        "ko": "하나 이상의 셀에서 결과값의 셀 내 분산이 0입니다.",
        "en": "One or more cells have zero within-cell outcome variance.",
    },
    "levene_rejected": {
        "ko": "중앙값 중심 Levene 검정에서 등분산 가정에 주의가 필요합니다.",
        "en": "The median-centered Levene test indicates a potential variance-homogeneity violation.",
    },
    "levene_unavailable": {
        "ko": "Levene 등분산 진단을 유효하게 계산하지 못했습니다.",
        "en": "A valid Levene variance-homogeneity diagnostic could not be computed.",
    },
    "shapiro_rejected": {
        "ko": "전체 모형 잔차의 Shapiro-Wilk 검정에서 정규성 가정에 주의가 필요합니다.",
        "en": "The full-model residual Shapiro-Wilk test indicates a potential normality violation.",
    },
    "shapiro_omitted": {
        "ko": "완전 관측 행이 5,000개를 초과해 잔차 Shapiro-Wilk p값을 생략했습니다.",
        "en": "The residual Shapiro-Wilk p-value was omitted because more than 5,000 complete observations were used.",
    },
    "shapiro_unavailable": {
        "ko": "잔차 Shapiro-Wilk 진단을 유효하게 계산하지 못했습니다.",
        "en": "A valid residual Shapiro-Wilk diagnostic could not be computed.",
    },
    "significant_interaction": {
        "ko": "상호작용이 유의하여 주효과보다 상호작용과 Holm 보정 단순효과를 우선 해석해야 합니다.",
        "en": "The interaction is significant, so interpretation should prioritize the interaction and Holm-adjusted simple effects over isolated main effects.",
    },
})
FACTORIAL_WARNING_CODES = frozenset(FACTORIAL_WARNING_TEXTS)


def render_factorial_warning(code: str, language: str) -> str:
    if code not in FACTORIAL_WARNING_TEXTS:
        raise ValueError(f"Unknown factorial warning code: {code}")
    language_base = str(language).lower().split("-")[0]
    if language_base not in {"ko", "en"}:
        raise ValueError("Factorial warning language must be Korean or English")
    return FACTORIAL_WARNING_TEXTS[code][language_base]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be finite numeric data")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _probability(value: object, label: str) -> float:
    result = _finite(value, label)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _integer(value: object, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer of at least {minimum}")
    return value


def _nonblank(value: object, label: str) -> str:
    if not isinstance(value, str) or not display_label_key(value):
        raise ValueError(f"{label} must be a non-blank visible string")
    return value.strip()


def _close(
    actual: float,
    expected: float,
    *,
    rel_tol: float = 1e-12,
    abs_tol: float = 1e-12,
) -> bool:
    return math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)


def _location_close(actual: float, expected: float) -> bool:
    tolerance = max(
        1e-12,
        8.0 * math.ulp(actual),
        8.0 * math.ulp(expected),
    )
    return abs(actual - expected) <= tolerance


def _summary_values(
    *,
    mean: object,
    se: object,
    ci_low: object,
    ci_high: object,
    label: str,
) -> tuple[float, float, float, float]:
    mean_value = _finite(mean, f"{label} mean")
    se_value = _finite(se, f"{label} SE")
    lower = _finite(ci_low, f"{label} CI lower")
    upper = _finite(ci_high, f"{label} CI upper")
    if se_value <= 0.0:
        raise ValueError(f"{label} SE must be positive")
    if lower > upper:
        raise ValueError(f"{label} CI must be ordered")
    if not lower <= mean_value <= upper:
        raise ValueError(f"{label} CI must contain its mean")
    return mean_value, se_value, lower, upper


@dataclass(frozen=True)
class FactorialLevel:
    factor_key: str
    raw_value: ScalarValue
    token: str
    label: str

    def __post_init__(self) -> None:
        factor_key = _nonblank(self.factor_key, "Factorial factor key")
        label = _nonblank(self.label, "Factorial level label")
        try:
            expected_token = canonical_value_token(self.raw_value)
        except ValueError as exc:
            raise ValueError("Factorial level raw value is unsupported") from exc
        if not isinstance(self.token, str) or self.token != expected_token:
            raise ValueError("Factorial level token must be canonical for its raw value")
        raw_value = decode_value_token(self.token)
        object.__setattr__(self, "factor_key", factor_key)
        object.__setattr__(self, "raw_value", raw_value)
        object.__setattr__(self, "label", label)


@dataclass(frozen=True)
class FactorialCellSummary:
    factor_a_level: FactorialLevel
    factor_b_level: FactorialLevel
    n: int
    mean: float
    sd: float
    se: float
    ci_low: float
    ci_high: float

    def __post_init__(self) -> None:
        if not isinstance(self.factor_a_level, FactorialLevel) or not isinstance(
            self.factor_b_level, FactorialLevel
        ):
            raise ValueError("Factorial cell levels must be FactorialLevel values")
        if self.factor_a_level.factor_key == self.factor_b_level.factor_key:
            raise ValueError("Factorial cell levels must belong to distinct factors")
        if isinstance(self.n, bool) or not isinstance(self.n, int) or self.n < 3:
            raise ValueError("Factorial cell n requires at least three observations")
        n = self.n
        mean, se, lower, upper = _summary_values(
            mean=self.mean,
            se=self.se,
            ci_low=self.ci_low,
            ci_high=self.ci_high,
            label="Factorial cell",
        )
        sd = _finite(self.sd, "Factorial cell SD")
        if sd < 0.0:
            raise ValueError("Factorial cell SD must be nonnegative")
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "sd", sd)
        object.__setattr__(self, "se", se)
        object.__setattr__(self, "ci_low", lower)
        object.__setattr__(self, "ci_high", upper)


@dataclass(frozen=True)
class FactorialMarginalSummary:
    factor_role: str
    level: FactorialLevel
    mean: float
    se: float
    ci_low: float
    ci_high: float

    def __post_init__(self) -> None:
        if self.factor_role not in {"factor_a", "factor_b"}:
            raise ValueError("Factorial marginal factor role is invalid")
        if not isinstance(self.level, FactorialLevel):
            raise ValueError("Factorial marginal level must be a FactorialLevel")
        mean, se, lower, upper = _summary_values(
            mean=self.mean,
            se=self.se,
            ci_low=self.ci_low,
            ci_high=self.ci_high,
            label="Factorial marginal",
        )
        object.__setattr__(self, "mean", mean)
        object.__setattr__(self, "se", se)
        object.__setattr__(self, "ci_low", lower)
        object.__setattr__(self, "ci_high", upper)


def _test_values(
    *,
    ss: object,
    df_num: object,
    df_den: object,
    ms: object,
    f_value: object,
    p_value: object,
    partial_eta_squared: object,
    condition_number: object,
    label: str,
) -> tuple[float, int, int, float, float, float, float, float]:
    ss_value = _finite(ss, f"{label} SS")
    numerator_df = _integer(df_num, f"{label} numerator degrees of freedom", 1)
    denominator_df = _integer(df_den, f"{label} denominator degrees of freedom", 1)
    ms_value = _finite(ms, f"{label} MS")
    f_statistic = _finite(f_value, f"{label} F")
    p = _probability(p_value, f"{label} p-value")
    eta = _probability(partial_eta_squared, f"{label} partial eta squared")
    condition = _finite(condition_number, f"{label} condition number")
    if ss_value < 0.0 or ms_value < 0.0 or f_statistic < 0.0:
        raise ValueError(f"{label} SS, MS, and F must be nonnegative")
    if condition <= 0.0:
        raise ValueError(f"{label} condition number must be positive")
    if not _close(ms_value, ss_value / numerator_df):
        raise ValueError(f"{label} MS must equal SS divided by numerator df")
    expected_p = float(stats.f.sf(f_statistic, numerator_df, denominator_df))
    if not _close(p, expected_p, rel_tol=1e-11, abs_tol=1e-15):
        raise ValueError(f"{label} p-value must equal the F survival probability")
    return (
        ss_value,
        numerator_df,
        denominator_df,
        ms_value,
        f_statistic,
        p,
        eta,
        condition,
    )


@dataclass(frozen=True)
class FactorialEffectResult:
    effect: str
    label: str
    ss: float
    df_num: int
    df_den: int
    ms: float
    f_value: float
    p_value: float
    partial_eta_squared: float
    condition_number: float

    def __post_init__(self) -> None:
        if self.effect not in {"factor_a", "factor_b", "interaction"}:
            raise ValueError("Factorial effect name is invalid")
        label = _nonblank(self.label, "Factorial effect label")
        values = _test_values(
            ss=self.ss,
            df_num=self.df_num,
            df_den=self.df_den,
            ms=self.ms,
            f_value=self.f_value,
            p_value=self.p_value,
            partial_eta_squared=self.partial_eta_squared,
            condition_number=self.condition_number,
            label="Factorial effect",
        )
        object.__setattr__(self, "label", label)
        for field_name, value in zip(
            (
                "ss",
                "df_num",
                "df_den",
                "ms",
                "f_value",
                "p_value",
                "partial_eta_squared",
                "condition_number",
            ),
            values,
            strict=True,
        ):
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True)
class FactorialSimpleEffectResult:
    tested_factor: str
    conditioning_factor: str
    conditioning_level: FactorialLevel
    ss: float
    df_num: int
    df_den: int
    ms: float
    f_value: float
    p_value: float
    adjusted_p_value: float
    reject: bool
    partial_eta_squared: float
    condition_number: float

    def __post_init__(self) -> None:
        if self.tested_factor not in {"factor_a", "factor_b"}:
            raise ValueError("Factorial simple tested factor is invalid")
        if self.conditioning_factor not in {"factor_a", "factor_b"} or (
            self.conditioning_factor == self.tested_factor
        ):
            raise ValueError("Factorial simple conditioning factor is invalid")
        if not isinstance(self.conditioning_level, FactorialLevel):
            raise ValueError("Factorial simple conditioning level is invalid")
        if not isinstance(self.reject, bool):
            raise ValueError("Factorial simple rejection decision must be boolean")
        values = _test_values(
            ss=self.ss,
            df_num=self.df_num,
            df_den=self.df_den,
            ms=self.ms,
            f_value=self.f_value,
            p_value=self.p_value,
            partial_eta_squared=self.partial_eta_squared,
            condition_number=self.condition_number,
            label="Factorial simple effect",
        )
        adjusted = _probability(
            self.adjusted_p_value,
            "Factorial simple adjusted p-value",
        )
        if adjusted + 1e-15 < values[5]:
            raise ValueError("Factorial simple adjusted p-value cannot be below raw p")
        for field_name, value in zip(
            (
                "ss",
                "df_num",
                "df_den",
                "ms",
                "f_value",
                "p_value",
                "partial_eta_squared",
                "condition_number",
            ),
            values,
            strict=True,
        ):
            object.__setattr__(self, field_name, value)
        object.__setattr__(self, "adjusted_p_value", adjusted)


def _diagnostic_values(
    *,
    status: str,
    statistic: object,
    p_value: object,
    allowed: set[str],
    label: str,
    statistic_probability: bool = False,
) -> tuple[str, float | None, float | None]:
    if status not in allowed:
        raise ValueError(f"{label} status is invalid")
    if status == "available":
        statistic_value = (
            _probability(statistic, f"{label} statistic")
            if statistic_probability
            else _finite(statistic, f"{label} statistic")
        )
        if statistic_value < 0.0:
            raise ValueError(f"{label} statistic must be nonnegative")
        return status, statistic_value, _probability(p_value, f"{label} p-value")
    if statistic is not None or p_value is not None:
        raise ValueError(f"Unavailable {label} values must be None")
    return status, None, None


@dataclass(frozen=True)
class FactorialAssumptions:
    levene_status: str
    levene_statistic: float | None
    levene_p_value: float | None
    shapiro_status: str
    shapiro_statistic: float | None
    shapiro_p_value: float | None
    min_cell_n: int
    max_cell_n: int
    imbalance_ratio: float
    zero_variance_cells: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        levene = _diagnostic_values(
            status=self.levene_status,
            statistic=self.levene_statistic,
            p_value=self.levene_p_value,
            allowed={"available", "unavailable"},
            label="Levene",
        )
        shapiro = _diagnostic_values(
            status=self.shapiro_status,
            statistic=self.shapiro_statistic,
            p_value=self.shapiro_p_value,
            allowed={"available", "omitted", "unavailable"},
            label="Shapiro",
            statistic_probability=True,
        )
        minimum = _integer(self.min_cell_n, "Minimum factorial cell n", 3)
        maximum = _integer(self.max_cell_n, "Maximum factorial cell n", minimum)
        ratio = _finite(self.imbalance_ratio, "Factorial cell imbalance ratio")
        if ratio < 1.0 or not _close(ratio, maximum / minimum):
            raise ValueError("Factorial cell imbalance ratio must equal max n / min n")
        if not isinstance(self.zero_variance_cells, tuple):
            raise ValueError("Zero-variance cell identities must be a tuple")
        seen: set[tuple[str, str]] = set()
        for pair in self.zero_variance_cells:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("Zero-variance cell identities must contain token pairs")
            for token in pair:
                decode_value_token(token)
            if pair in seen:
                raise ValueError("Zero-variance cell identities must be unique")
            seen.add(pair)
        object.__setattr__(self, "levene_status", levene[0])
        object.__setattr__(self, "levene_statistic", levene[1])
        object.__setattr__(self, "levene_p_value", levene[2])
        object.__setattr__(self, "shapiro_status", shapiro[0])
        object.__setattr__(self, "shapiro_statistic", shapiro[1])
        object.__setattr__(self, "shapiro_p_value", shapiro[2])
        object.__setattr__(self, "min_cell_n", minimum)
        object.__setattr__(self, "max_cell_n", maximum)
        object.__setattr__(self, "imbalance_ratio", ratio)


@dataclass(frozen=True)
class FactorialAnovaResult:
    analysis_key: str
    dv: str
    factor_a: str
    factor_b: str
    dv_label: str
    factor_a_label: str
    factor_b_label: str
    levels_a: tuple[FactorialLevel, ...]
    levels_b: tuple[FactorialLevel, ...]
    n_total: int
    n_used: int
    n_excluded: int
    cells: tuple[FactorialCellSummary, ...]
    marginals: tuple[FactorialMarginalSummary, ...]
    effects: tuple[FactorialEffectResult, ...]
    sse: float
    df_error: int
    mse: float
    simple_effects: tuple[FactorialSimpleEffectResult, ...]
    assumptions: FactorialAssumptions
    language: str
    warning_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    method_details: Mapping[str, Any]
    chart_specs: tuple[ChartSpec, ...]
    apa_template_id: str

    def __post_init__(self) -> None:
        self._validate_identity()
        if not isinstance(self.method_details, Mapping):
            raise ValueError("Factorial method details must be a mapping")
        method_details = dict(self.method_details)
        if method_details != FACTORIAL_METHOD_DETAILS:
            raise ValueError("Factorial method details do not match the frozen method")
        object.__setattr__(self, "method_details", _freeze_value(method_details))

        levels_a = self._validate_levels(self.levels_a, self.factor_a, "A")
        levels_b = self._validate_levels(self.levels_b, self.factor_b, "B")
        counts = self._validate_counts_and_cells(levels_a, levels_b)
        sse, df_error, mse = self._validate_pooled_error(counts)
        self._validate_cell_statistics(mse, df_error)
        effects = self._validate_effects(levels_a, levels_b, sse, df_error, mse)
        self._validate_marginals(levels_a, levels_b, mse, df_error)
        self._validate_simple_effects(levels_a, levels_b, effects[2], sse, df_error, mse)
        self._validate_assumptions()
        self._validate_warnings(effects[2])
        self._validate_chart(levels_a, levels_b)

        object.__setattr__(self, "sse", sse)
        object.__setattr__(self, "df_error", df_error)
        object.__setattr__(self, "mse", mse)
        object.__setattr__(
            self,
            "chart_specs",
            tuple(
                ChartSpec(
                    type=chart.type,
                    title=chart.title,
                    data=_freeze_value(chart.data),  # type: ignore[arg-type]
                    x_label=chart.x_label,
                    y_label=chart.y_label,
                )
                for chart in self.chart_specs
            ),
        )

    def _validate_identity(self) -> None:
        if self.analysis_key != "anova_factorial":
            raise ValueError("Factorial analysis key must be anova_factorial")
        roles = tuple(_nonblank(value, "Factorial role") for value in (self.dv, self.factor_a, self.factor_b))
        if len(set(roles)) != 3:
            raise ValueError("Factorial roles must be distinct")
        labels = tuple(
            _nonblank(value, "Factorial role label")
            for value in (self.dv_label, self.factor_a_label, self.factor_b_label)
        )
        if self.language not in {"ko", "en"}:
            raise ValueError("Factorial result language must be ko or en")
        if self.apa_template_id != "factorial_anova_v1":
            raise ValueError("Factorial report template is invalid")
        for field_name, value in zip(
            ("dv", "factor_a", "factor_b"),
            roles,
            strict=True,
        ):
            object.__setattr__(self, field_name, value)
        for field_name, value in zip(
            ("dv_label", "factor_a_label", "factor_b_label"),
            labels,
            strict=True,
        ):
            object.__setattr__(self, field_name, value)
        for collection, label in (
            (self.levels_a, "levels A"),
            (self.levels_b, "levels B"),
            (self.cells, "cells"),
            (self.marginals, "marginals"),
            (self.effects, "effects"),
            (self.simple_effects, "simple effects"),
            (self.warning_codes, "warning codes"),
            (self.warnings, "warnings"),
            (self.chart_specs, "chart specs"),
        ):
            if not isinstance(collection, tuple):
                raise ValueError(f"Factorial {label} must be tuples")

    @staticmethod
    def _validate_levels(
        levels: tuple[FactorialLevel, ...],
        factor_key: str,
        label: str,
    ) -> tuple[FactorialLevel, ...]:
        if not 2 <= len(levels) <= 6 or not all(
            isinstance(level, FactorialLevel) for level in levels
        ):
            raise ValueError(f"Factorial levels {label} must contain 2 through 6 levels")
        if any(level.factor_key != factor_key for level in levels):
            raise ValueError(f"Factorial levels {label} do not match their factor key")
        identities = [normalized_value_key(level.raw_value) for level in levels]
        labels = [display_label_key(level.label) for level in levels]
        if len(set(identities)) != len(levels):
            raise ValueError(f"Factorial levels {label} must have unique typed identities")
        if len(set(labels)) != len(levels):
            raise ValueError(f"Factorial levels {label} have ambiguous display labels")
        return levels

    def _validate_counts_and_cells(
        self,
        levels_a: tuple[FactorialLevel, ...],
        levels_b: tuple[FactorialLevel, ...],
    ) -> tuple[int, int, int]:
        n_total = _integer(self.n_total, "Factorial total count", 1)
        n_used = _integer(self.n_used, "Factorial used count", 1)
        n_excluded = _integer(self.n_excluded, "Factorial excluded count", 0)
        if n_used + n_excluded != n_total:
            raise ValueError("Factorial observation counts are inconsistent")
        if len(self.cells) != len(levels_a) * len(levels_b) or not all(
            isinstance(cell, FactorialCellSummary) for cell in self.cells
        ):
            raise ValueError("Factorial cells must cover the complete Cartesian product")
        expected = tuple((level_a, level_b) for level_a in levels_a for level_b in levels_b)
        actual = tuple((cell.factor_a_level, cell.factor_b_level) for cell in self.cells)
        if actual != expected:
            raise ValueError("Factorial cells must follow unique A-major/B-fast Cartesian order")
        if sum(cell.n for cell in self.cells) != n_used:
            raise ValueError("Factorial cell counts must sum to the used count")
        return n_total, n_used, n_excluded

    def _validate_pooled_error(self, counts: tuple[int, int, int]) -> tuple[float, int, float]:
        _, n_used, _ = counts
        sse = _finite(self.sse, "Factorial pooled SSE")
        mse = _finite(self.mse, "Factorial pooled MSE")
        df_error = _integer(self.df_error, "Factorial error df", 1)
        expected_df = n_used - len(self.cells)
        if df_error != expected_df:
            raise ValueError("Factorial error df must equal N minus the cell count")
        if sse <= 0.0 or mse <= 0.0:
            raise ValueError("Factorial pooled SSE and MSE must be positive")
        if not _close(mse, sse / df_error):
            raise ValueError("Factorial MSE must equal SSE divided by error df")
        reconstructed_sse = math.fsum((cell.n - 1) * cell.sd * cell.sd for cell in self.cells)
        if not _close(sse, reconstructed_sse, rel_tol=1e-9):
            raise ValueError("Factorial pooled SSE must agree with cell sample SDs")
        return sse, df_error, mse

    def _validate_cell_statistics(self, mse: float, df_error: int) -> None:
        critical = float(stats.t.ppf(0.975, df_error))
        for cell in self.cells:
            expected_se = math.sqrt(mse / cell.n)
            if not _close(cell.se, expected_se):
                raise ValueError("Factorial cell SE must use pooled MSE")
            self._validate_interval(cell.mean, cell.se, cell.ci_low, cell.ci_high, critical, "cell")

    def _validate_effects(
        self,
        levels_a: tuple[FactorialLevel, ...],
        levels_b: tuple[FactorialLevel, ...],
        sse: float,
        df_error: int,
        mse: float,
    ) -> tuple[FactorialEffectResult, ...]:
        if len(self.effects) != 3 or not all(isinstance(value, FactorialEffectResult) for value in self.effects):
            raise ValueError("Factorial effects must contain three rows")
        expected = (
            ("factor_a", len(levels_a) - 1),
            ("factor_b", len(levels_b) - 1),
            ("interaction", (len(levels_a) - 1) * (len(levels_b) - 1)),
        )
        if tuple(value.effect for value in self.effects) != tuple(value[0] for value in expected):
            raise ValueError("Factorial effect order must be A, B, interaction")
        for effect, (_, expected_df) in zip(self.effects, expected, strict=True):
            if effect.df_num != expected_df:
                raise ValueError("Factorial effect numerator df is inconsistent")
            self._validate_test_against_error(effect, sse, df_error, mse)
        return self.effects

    def _validate_marginals(
        self,
        levels_a: tuple[FactorialLevel, ...],
        levels_b: tuple[FactorialLevel, ...],
        mse: float,
        df_error: int,
    ) -> None:
        expected_identity = tuple(("factor_a", level) for level in levels_a) + tuple(("factor_b", level) for level in levels_b)
        actual_identity = tuple((row.factor_role, row.level) for row in self.marginals)
        if actual_identity != expected_identity:
            raise ValueError("Factorial marginals must follow factor A then factor B level order")
        critical = float(stats.t.ppf(0.975, df_error))
        b = len(levels_b)
        for index, row in enumerate(self.marginals[: len(levels_a)]):
            cells = self.cells[index * b : (index + 1) * b]
            expected_mean = math.fsum(cell.mean for cell in cells) / b
            expected_se = math.sqrt(mse * math.fsum(1.0 / cell.n for cell in cells) / (b * b))
            self._validate_marginal_row(row, expected_mean, expected_se, critical)
        a = len(levels_a)
        for index, row in enumerate(self.marginals[a:]):
            cells = tuple(self.cells[level_a * b + index] for level_a in range(a))
            expected_mean = math.fsum(cell.mean for cell in cells) / a
            expected_se = math.sqrt(mse * math.fsum(1.0 / cell.n for cell in cells) / (a * a))
            self._validate_marginal_row(row, expected_mean, expected_se, critical)

    def _validate_simple_effects(
        self,
        levels_a: tuple[FactorialLevel, ...],
        levels_b: tuple[FactorialLevel, ...],
        interaction: FactorialEffectResult,
        sse: float,
        df_error: int,
        mse: float,
    ) -> None:
        gate_open = interaction.p_value < 0.05
        if not gate_open:
            if self.simple_effects:
                raise ValueError("Factorial simple effects must be absent when the interaction gate is closed")
            return
        if len(self.simple_effects) != len(levels_a) + len(levels_b):
            raise ValueError("Factorial interaction gate requires every omnibus simple effect")
        expected = tuple(("factor_a", "factor_b", level, len(levels_a) - 1) for level in levels_b) + tuple(("factor_b", "factor_a", level, len(levels_b) - 1) for level in levels_a)
        actual = tuple((row.tested_factor, row.conditioning_factor, row.conditioning_level, row.df_num) for row in self.simple_effects)
        if actual != expected:
            raise ValueError("Factorial simple effects do not follow the frozen gate order")
        adjusted = holm_adjust(tuple(row.p_value for row in self.simple_effects))
        for row, expected_adjusted in zip(self.simple_effects, adjusted, strict=True):
            self._validate_test_against_error(row, sse, df_error, mse)
            if not _close(row.adjusted_p_value, expected_adjusted, rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("Factorial simple effects must use one-family Holm adjustment")
            if row.reject != (row.adjusted_p_value < 0.05):
                raise ValueError("Factorial simple-effect decision must use adjusted p")

    def _validate_assumptions(self) -> None:
        if not isinstance(self.assumptions, FactorialAssumptions):
            raise ValueError("Factorial assumptions are invalid")
        counts = tuple(cell.n for cell in self.cells)
        if self.assumptions.min_cell_n != min(counts) or self.assumptions.max_cell_n != max(counts):
            raise ValueError("Factorial assumption cell-count range is inconsistent")
        expected_zero = tuple((cell.factor_a_level.token, cell.factor_b_level.token) for cell in self.cells if cell.sd == 0.0)
        if self.assumptions.zero_variance_cells != expected_zero:
            raise ValueError("Factorial zero-variance cell identities are inconsistent")
        if self.n_used > 5000 and self.assumptions.shapiro_status != "omitted":
            raise ValueError("Factorial Shapiro policy requires omission above 5000 rows")
        if self.n_used <= 5000 and self.assumptions.shapiro_status == "omitted":
            raise ValueError("Factorial Shapiro policy permits omission only above 5000 rows")

    def _validate_warnings(self, interaction: FactorialEffectResult) -> None:
        if len(set(self.warning_codes)) != len(self.warning_codes) or any(code not in FACTORIAL_WARNING_CODES for code in self.warning_codes):
            raise ValueError("Factorial warning codes must be unique and known")
        expected_codes: list[str] = []
        if self.n_excluded / self.n_total > 0.05:
            expected_codes.append("high_missing_fraction")
        if self.assumptions.min_cell_n < 10:
            expected_codes.append("small_cell")
        if self.assumptions.imbalance_ratio > 10.0:
            expected_codes.append("severe_imbalance")
        if self.assumptions.zero_variance_cells:
            expected_codes.append("zero_variance_cell")
        if self.assumptions.levene_status == "unavailable":
            expected_codes.append("levene_unavailable")
        elif self.assumptions.levene_p_value is not None and self.assumptions.levene_p_value < 0.05:
            expected_codes.append("levene_rejected")
        if self.assumptions.shapiro_status == "omitted":
            expected_codes.append("shapiro_omitted")
        elif self.assumptions.shapiro_status == "unavailable":
            expected_codes.append("shapiro_unavailable")
        elif self.assumptions.shapiro_p_value is not None and self.assumptions.shapiro_p_value < 0.05:
            expected_codes.append("shapiro_rejected")
        if interaction.p_value < 0.05:
            expected_codes.append("significant_interaction")
        if self.warning_codes != tuple(expected_codes):
            raise ValueError("Factorial warning codes do not match result thresholds")
        expected_warnings = tuple(render_factorial_warning(code, self.language) for code in expected_codes)
        if self.warnings != expected_warnings:
            raise ValueError("Factorial rendered warnings do not align with warning codes")

    def _validate_chart(
        self,
        levels_a: tuple[FactorialLevel, ...],
        levels_b: tuple[FactorialLevel, ...],
    ) -> None:
        if len(self.chart_specs) != 1 or not isinstance(self.chart_specs[0], ChartSpec):
            raise ValueError("Factorial result requires one interaction chart")
        chart = self.chart_specs[0]
        if (
            chart.type != "factorial_interaction"
            or chart.title != "Equal-cell Type III interaction plot"
            or chart.x_label != self.factor_a_label
            or chart.y_label != self.dv_label
        ):
            raise ValueError("Factorial chart metadata is inconsistent")
        b = len(levels_b)
        expected_data = {
            "factor_a": [
                {"token": level.token, "label": level.label} for level in levels_a
            ],
            "series": [
                {
                    "factor_b_token": level_b.token,
                    "factor_b_label": level_b.label,
                    "means": [self.cells[index * b + j].mean for index in range(len(levels_a))],
                    "ci_low": [self.cells[index * b + j].ci_low for index in range(len(levels_a))],
                    "ci_high": [self.cells[index * b + j].ci_high for index in range(len(levels_a))],
                }
                for j, level_b in enumerate(levels_b)
            ],
        }
        if _freeze_value(chart.data) != _freeze_value(expected_data):
            raise ValueError("Factorial chart data do not match cell summaries")

    @staticmethod
    def _validate_interval(
        mean: float,
        se: float,
        lower: float,
        upper: float,
        critical: float,
        label: str,
    ) -> None:
        if not _location_close(lower, mean - critical * se) or not _location_close(upper, mean + critical * se):
            raise ValueError(f"Factorial {label} CI must use the pooled-error t interval")

    @classmethod
    def _validate_marginal_row(
        cls,
        row: FactorialMarginalSummary,
        expected_mean: float,
        expected_se: float,
        critical: float,
    ) -> None:
        if not _location_close(row.mean, expected_mean):
            raise ValueError("Factorial marginal mean must be equal-cell weighted")
        if not _close(row.se, expected_se):
            raise ValueError("Factorial marginal SE must use pooled MSE and equal cell weights")
        cls._validate_interval(row.mean, row.se, row.ci_low, row.ci_high, critical, "marginal")

    @staticmethod
    def _validate_test_against_error(
        row: FactorialEffectResult | FactorialSimpleEffectResult,
        sse: float,
        df_error: int,
        mse: float,
    ) -> None:
        if row.df_den != df_error:
            raise ValueError("Factorial test denominator df must equal error df")
        if row.condition_number > 1e10:
            raise ValueError("Factorial test condition number exceeds the policy limit")
        if not _close(row.f_value, row.ms / mse):
            raise ValueError("Factorial F must equal effect MS divided by pooled MSE")
        expected_eta = row.ss / (row.ss + sse)
        if not _close(row.partial_eta_squared, expected_eta):
            raise ValueError("Factorial partial eta squared is inconsistent with SS and SSE")
