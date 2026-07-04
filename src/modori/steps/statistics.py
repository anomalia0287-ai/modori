from __future__ import annotations

import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from modori.cache import matplotlib_cache_dir

_matplotlib_cache = matplotlib_cache_dir()
os.environ["MPLCONFIGDIR"] = str(_matplotlib_cache)

import pingouin as pg
from factor_analyzer import FactorAnalyzer

from modori.core import Measure, PipelineContext, Step, StepResult
from modori.results import ChartSpec, ComparisonResult, GroupDesc, ReliabilityResult


STATISTICS_ENGINE_VOCABULARY = frozenset(
    {
        "alpha_if_deleted",
        "cohen_dz",
        "cohen_d",
        "confidence_interval",
        "corrected_item_total_correlation",
        "cronbach_alpha",
        "df",
        "levene",
        "mann_whitney",
        "mcdonald_omega",
        "p_value",
        "paired_t",
        "rank_biserial",
        "shapiro_wilk",
        "statistic",
        "student_t",
        "welch_t",
        "wilcoxon",
    }
)


@dataclass
class ReliabilityStep(Step):
    step_type = "stats.reliability"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        items = list(self.params["items"])
        if len(set(items)) != len(items):
            raise ValueError("Reliability items must be unique")
        if len(items) < 3:
            raise ValueError(
                "Reliability requires at least three items because "
                "alpha-if-deleted is undefined for two-item scales."
            )
        scale_name = str(self.params.get("scale_name", "scale"))
        frame = ctx.dataset.frame_for_compute(items).dropna(axis=0, how="any")
        if len(frame) < 2:
            raise ValueError("Reliability requires at least two complete cases.")
        non_numeric_items = [
            column
            for column in frame.columns
            if not pd.api.types.is_numeric_dtype(frame[column])
        ]
        if non_numeric_items:
            raise ValueError(
                f"Reliability items must be numeric: {', '.join(non_numeric_items)}"
            )
        zero_variance_items = [
            column for column in frame.columns if frame[column].nunique(dropna=True) < 2
        ]
        if zero_variance_items:
            raise ValueError(
                "Reliability items must have non-zero variance: "
                f"{', '.join(zero_variance_items)}"
            )

        alpha, alpha_ci = pg.cronbach_alpha(data=frame)
        item_total_corr = self._corrected_item_total_correlations(frame)
        alpha_if_deleted = self._alpha_if_deleted(frame)
        omega = self._mcdonald_omega(frame)
        result = ReliabilityResult(
            scale_name=scale_name,
            n_items=len(items),
            n_cases=len(frame),
            cronbach_alpha=float(alpha),
            alpha_ci=(float(alpha_ci[0]), float(alpha_ci[1])),
            mcdonald_omega=omega,
            item_total_corr=item_total_corr,
            alpha_if_deleted=alpha_if_deleted,
            apa_template_id="reliability.v1",
            chart_spec=ChartSpec(
                type="horizontal_bar",
                title="Corrected item-total correlations",
                data={"values": item_total_corr},
                x_label="Corrected item-total correlation",
                y_label="Item",
            ),
        )
        return StepResult(
            new_columns={},
            new_variables={},
            analysis=result,
            notes=[
                f"Cronbach's alpha indicates {self._alpha_grade(alpha)} internal consistency."
            ],
        )

    @staticmethod
    def _corrected_item_total_correlations(frame: pd.DataFrame) -> dict[str, float]:
        total = frame.sum(axis=1)
        return {
            column: float(frame[column].corr(total - frame[column]))
            for column in frame.columns
        }

    @staticmethod
    def _alpha_if_deleted(frame: pd.DataFrame) -> dict[str, float]:
        return {
            column: float(pg.cronbach_alpha(data=frame.drop(columns=[column]))[0])
            for column in frame.columns
        }

    @staticmethod
    def _mcdonald_omega(frame: pd.DataFrame) -> float:
        """Compute omega-total for a unidimensional single-factor model.

        The estimate uses maximum-likelihood loadings from a one-factor model
        and applies omega-total as (sum(lambda))^2 /
        ((sum(lambda))^2 + sum(uniqueness)).
        """
        analyzer = FactorAnalyzer(n_factors=1, rotation=None, method="ml")
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="'force_all_finite' was renamed to 'ensure_all_finite'",
                category=FutureWarning,
            )
            try:
                analyzer.fit(frame)
            except np.linalg.LinAlgError as exc:
                raise ValueError(
                    "McDonald's omega could not be estimated because the item "
                    "correlation matrix is singular."
                ) from exc
        loadings = analyzer.loadings_.ravel()
        uniquenesses = analyzer.get_uniquenesses()
        common_variance = float(loadings.sum() ** 2)
        error_variance = float(uniquenesses.sum())
        return common_variance / (common_variance + error_variance)

    @staticmethod
    def _alpha_grade(alpha: float) -> str:
        if alpha >= 0.90:
            return "excellent"
        if alpha >= 0.80:
            return "good"
        if alpha >= 0.70:
            return "acceptable"
        return "low (caution)"

    def reads(self) -> set[str]:
        return set(self.params["items"])

    def writes(self) -> set[str]:
        scale_name = str(self.params.get("scale_name", "scale"))
        return {f"reliability:{scale_name}"}

    def provenance(self) -> str:
        return f"computed reliability for {self.params.get('scale_name', 'scale')}"


Step.register_type(ReliabilityStep.step_type, ReliabilityStep)


@dataclass
class CompareGroupsStep(Step):
    step_type = "stats.compare_groups"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        dv = str(self.params["dv"])
        group_var = str(self.params["group"])
        if dv == group_var:
            raise ValueError(
                "CompareGroupsStep dependent variable and group variable must differ."
            )
        source_frame = ctx.dataset.frame_for_compute([dv, group_var])
        n_total = len(source_frame)
        frame = source_frame.dropna(axis=0, how="any")
        n_obs = len(frame)
        n_dropped = n_total - n_obs
        if not pd.api.types.is_numeric_dtype(frame[dv]):
            raise ValueError("CompareGroupsStep dependent variable must be numeric.")
        group_values = sorted(
            list(pd.unique(frame[group_var])),
            key=self._group_sort_key,
        )
        if len(group_values) != 2:
            raise ValueError("CompareGroupsStep requires exactly two groups.")

        first_value, second_value = group_values
        first = frame.loc[frame[group_var] == first_value, dv]
        second = frame.loc[frame[group_var] == second_value, dv]
        self._validate_group_sizes(first, second)
        labels = self._group_labels(ctx, group_var, group_values)
        if labels[0] == labels[1]:
            raise ValueError("CompareGroupsStep group labels must be unique.")
        dv_label = ctx.dataset.variables[dv].label or dv
        group_label = ctx.dataset.variables[group_var].label or group_var
        assumptions = self._assumptions(first, second)
        route, route_reason = self._route(first, second, assumptions)

        if route == "mann_whitney":
            analysis = self._mann_whitney_result(
                dv,
                group_var,
                dv_label,
                group_label,
                labels,
                first,
                second,
                assumptions,
                route_reason=route_reason,
                n_obs=n_obs,
                n_total=n_total,
                n_dropped=n_dropped,
            )
            note_test_name = "Mann-Whitney U"
        else:
            analysis = self._t_result(
                dv,
                group_var,
                dv_label,
                group_label,
                labels,
                first,
                second,
                assumptions,
                correction=(route == "welch_t"),
                route_reason=route_reason,
                n_obs=n_obs,
                n_total=n_total,
                n_dropped=n_dropped,
            )
            note_test_name = (
                "Welch's t-test" if route == "welch_t" else "Student's t-test"
            )

        return StepResult(
            new_columns={},
            new_variables={},
            analysis=analysis,
            notes=[f"Selected {note_test_name} because {analysis.route_reason}."],
        )

    def _route(
        self,
        first: pd.Series,
        second: pd.Series,
        assumptions: dict[str, float],
    ) -> tuple[str, str]:
        policy = dict(self.params.get("routing_policy", {"preset": "modern"}))
        preset = str(policy.get("preset", "modern"))
        if preset not in {"modern", "always_welch", "classic", "custom"}:
            raise ValueError(f"Unsupported routing_policy preset: {preset}")
        if preset == "always_welch":
            return "welch_t", "always_welch policy"

        normality_threshold = float(policy.get("normality_p", 0.05))
        nonparametric_cutoff = int(policy.get("nonparametric_n_cutoff", 30))
        if not 0 < normality_threshold < 1:
            raise ValueError("normality_p must be greater than 0 and less than 1")
        if nonparametric_cutoff < 3:
            raise ValueError("nonparametric_n_cutoff must be at least 3")
        use_levene = bool(policy.get("use_levene", True))
        allow_nonparametric = preset != "classic"

        normality_violated = (
            assumptions["shapiro_g1_p"] < normality_threshold
            or assumptions["shapiro_g2_p"] < normality_threshold
        )
        variance_unequal = use_levene and assumptions["levene_p"] < 0.05
        if (
            allow_nonparametric
            and normality_violated
            and min(len(first), len(second)) < nonparametric_cutoff
        ):
            return "mann_whitney", "normality violated + small sample"
        if preset == "classic":
            if variance_unequal:
                return "welch_t", "unequal variance -> Welch correction"
            if normality_violated:
                return "student_t", "classic policy: nonparametric auto-reroute off"
            return "student_t", "assumptions met"
        if preset == "custom" and policy.get("default_test") == "student_t":
            if variance_unequal:
                return "welch_t", "unequal variance -> Welch correction"
            if normality_violated:
                return "student_t", "custom policy: nonparametric cutoff not met"
            return "student_t", "custom policy: default_test student_t"
        return "welch_t", "Welch-first policy"

    @staticmethod
    def _assumptions(first: pd.Series, second: pd.Series) -> dict[str, float]:
        homoscedasticity = pg.homoscedasticity(
            [first.to_numpy(), second.to_numpy()],
            method="levene",
            center="median",
        )
        return {
            "shapiro_g1_p": float(stats.shapiro(first).pvalue),
            "shapiro_g2_p": float(stats.shapiro(second).pvalue),
            "levene_p": float(homoscedasticity.loc["levene", "pval"]),
        }

    @staticmethod
    def _validate_group_sizes(first: pd.Series, second: pd.Series) -> None:
        if len(first) < 3 or len(second) < 3:
            raise ValueError(
                "CompareGroupsStep requires at least three valid cases per group."
            )
        if first.nunique(dropna=True) < 2 or second.nunique(dropna=True) < 2:
            raise ValueError(
                "CompareGroupsStep requires non-zero variance in each group."
            )

    def _t_result(
        self,
        dv: str,
        group_var: str,
        dv_label: str,
        group_label: str,
        labels: tuple[str, str],
        first: pd.Series,
        second: pd.Series,
        assumptions: dict[str, float],
        *,
        correction: bool,
        route_reason: str,
        n_obs: int,
        n_total: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.ttest(first, second, correction=correction).iloc[0]
        test_name = "welch_t" if correction else "student_t"
        ci = tuple(float(value) for value in test["CI95"])
        return ComparisonResult(
            dv=dv,
            group_var=group_var,
            test_name=test_name,
            route_reason=route_reason,
            groups=self._group_descriptions(labels, first, second),
            statistic=float(test["T"]),
            df=float(test["dof"]),
            p_value=float(test["p_val"]),
            effect_name="cohen_d",
            effect_value=self._signed_cohen_d(float(test["cohen_d"]), first, second),
            mean_diff_ci=(ci[0], ci[1]),
            assumptions=assumptions,
            apa_template_id="ttest.v1",
            chart_spec=ChartSpec(
                type="mean_ci_jitter",
                title="Group means with 95% CI",
                data=self._group_chart_payload(labels, first, second, include_ci=True),
                x_label=group_var,
                y_label=dv,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=dv_label,
            group_label=group_label,
        )

    def _mann_whitney_result(
        self,
        dv: str,
        group_var: str,
        dv_label: str,
        group_label: str,
        labels: tuple[str, str],
        first: pd.Series,
        second: pd.Series,
        assumptions: dict[str, float],
        *,
        route_reason: str,
        n_obs: int,
        n_total: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.mwu(first, second).iloc[0]
        return ComparisonResult(
            dv=dv,
            group_var=group_var,
            test_name="mann_whitney",
            route_reason=route_reason,
            groups=self._group_descriptions(labels, first, second),
            statistic=float(test["U_val"]),
            df=None,
            p_value=float(test["p_val"]),
            effect_name="rank_biserial",
            effect_value=float(test["RBC"]),
            mean_diff_ci=None,
            assumptions=assumptions,
            apa_template_id="mwu.v1",
            chart_spec=ChartSpec(
                type="box",
                title="Group distributions",
                data=self._group_chart_payload(labels, first, second),
                x_label=group_var,
                y_label=dv,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=dv_label,
            group_label=group_label,
        )

    @staticmethod
    def _group_descriptions(
        labels: tuple[str, str],
        first: pd.Series,
        second: pd.Series,
    ) -> dict[str, GroupDesc]:
        return {
            labels[0]: GroupDesc(
                n=int(first.count()),
                mean=float(first.mean()),
                sd=float(first.std(ddof=1)),
                median=float(first.median()),
            ),
            labels[1]: GroupDesc(
                n=int(second.count()),
                mean=float(second.mean()),
                sd=float(second.std(ddof=1)),
                median=float(second.median()),
            ),
        }

    @staticmethod
    def _group_chart_payload(
        labels: tuple[str, str],
        first: pd.Series,
        second: pd.Series,
        *,
        include_ci: bool = False,
    ) -> dict[str, list[dict[str, object]]]:
        groups: list[dict[str, object]] = []
        for label, values in ((labels[0], first), (labels[1], second)):
            numeric = [float(value) for value in values.tolist()]
            mean = float(values.mean())
            payload: dict[str, object] = {
                "label": label,
                "values": numeric,
                "mean": mean,
            }
            if include_ci and len(values) > 1:
                margin = float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))
                payload["ci95"] = (mean - margin, mean + margin)
            groups.append(payload)
        return {"groups": groups}

    @staticmethod
    def _group_labels(
        ctx: PipelineContext,
        group_var: str,
        group_values: list[object],
    ) -> tuple[str, str]:
        value_labels = ctx.dataset.variables[group_var].value_labels
        labels = []
        missing_label = object()
        for value in group_values:
            label = value_labels.get(value, missing_label)
            if label is missing_label:
                try:
                    label = value_labels.get(float(value), missing_label)
                except (TypeError, ValueError):
                    label = missing_label
            labels.append(str(value) if label is missing_label else str(label))
        return labels[0], labels[1]

    @staticmethod
    def _group_sort_key(value: object) -> tuple[int, float | str]:
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, str(value))

    @staticmethod
    def _signed_cohen_d(magnitude: float, first: pd.Series, second: pd.Series) -> float:
        mean_difference = float(first.mean() - second.mean())
        if mean_difference == 0:
            return 0.0
        return abs(magnitude) if mean_difference > 0 else -abs(magnitude)

    def reads(self) -> set[str]:
        return {str(self.params["dv"]), str(self.params["group"])}

    def writes(self) -> set[str]:
        return {f"comparison:{self.params['dv']}:{self.params['group']}"}

    def provenance(self) -> str:
        return f"compared {self.params['dv']} by {self.params['group']}"


Step.register_type(CompareGroupsStep.step_type, CompareGroupsStep)


@dataclass
class PairedComparisonStep(Step):
    step_type = "stats.paired_comparison"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        before = str(self.params["before"])
        after = str(self.params["after"])
        if before == after:
            raise ValueError(
                "PairedComparisonStep before and after variables must differ."
            )
        self._validate_variables(ctx, before, after)

        source_frame = ctx.dataset.frame_for_compute([before, after])
        n_total = len(source_frame)
        if not (
            pd.api.types.is_numeric_dtype(source_frame[before])
            and pd.api.types.is_numeric_dtype(source_frame[after])
        ):
            raise ValueError(
                "PairedComparisonStep before and after variables must be numeric."
            )

        frame = source_frame.dropna(axis=0, how="any")
        n_obs = len(frame)
        n_dropped = n_total - n_obs
        if n_obs < 3:
            raise ValueError(
                "PairedComparisonStep requires at least three complete pairs."
            )

        before_scores = frame[before]
        after_scores = frame[after]
        differences = after_scores - before_scores
        if differences.nunique(dropna=True) < 2:
            raise ValueError(
                "PairedComparisonStep requires non-zero variance in paired differences."
            )

        assumptions = {
            "shapiro_diff_p": float(stats.shapiro(differences).pvalue),
        }
        route, route_reason = self._route(n_obs, assumptions)
        before_label = ctx.dataset.variables[before].label or before
        after_label = ctx.dataset.variables[after].label or after
        if before_label == after_label:
            raise ValueError("PairedComparisonStep labels must be unique.")

        if route == "wilcoxon":
            analysis = self._wilcoxon_result(
                before,
                after,
                before_label,
                after_label,
                before_scores,
                after_scores,
                assumptions,
                route_reason=route_reason,
                n_obs=n_obs,
                n_total=n_total,
                n_dropped=n_dropped,
            )
            note_test_name = "Wilcoxon signed-rank test"
        else:
            analysis = self._paired_t_result(
                before,
                after,
                before_label,
                after_label,
                before_scores,
                after_scores,
                assumptions,
                route_reason=route_reason,
                n_obs=n_obs,
                n_total=n_total,
                n_dropped=n_dropped,
            )
            note_test_name = "paired t-test"

        return StepResult(
            new_columns={},
            new_variables={},
            analysis=analysis,
            notes=[f"Selected {note_test_name} because {analysis.route_reason}."],
        )

    @staticmethod
    def _validate_variables(
        ctx: PipelineContext,
        before: str,
        after: str,
    ) -> None:
        missing = [
            column for column in (before, after) if column not in ctx.dataset.variables
        ]
        if missing:
            raise KeyError(f"Unknown columns requested: {sorted(missing)}")
        if (
            ctx.dataset.variables[before].measure is not Measure.SCALE
            or ctx.dataset.variables[after].measure is not Measure.SCALE
        ):
            raise ValueError(
                "PairedComparisonStep before and after variables must be SCALE."
            )

    def _route(
        self,
        n_obs: int,
        assumptions: dict[str, float],
    ) -> tuple[str, str]:
        policy = dict(self.params.get("routing_policy", {"preset": "modern"}))
        preset = str(policy.get("preset", "modern"))
        if preset not in {"modern", "always_wilcoxon", "classic"}:
            raise ValueError(f"Unsupported routing_policy preset: {preset}")

        normality_threshold = float(policy.get("normality_p", 0.05))
        nonparametric_cutoff = int(policy.get("nonparametric_n_cutoff", 30))
        if not 0 < normality_threshold < 1:
            raise ValueError("normality_p must be greater than 0 and less than 1")
        if nonparametric_cutoff < 3:
            raise ValueError("nonparametric_n_cutoff must be at least 3")

        if preset == "always_wilcoxon":
            return "wilcoxon", "always_wilcoxon policy"
        if preset == "classic":
            return "paired_t", "classic policy"
        if (
            assumptions["shapiro_diff_p"] < normality_threshold
            and n_obs < nonparametric_cutoff
        ):
            return "wilcoxon", "non-normal paired differences + small sample"
        return "paired_t", "paired differences compatible with t-test"

    def _paired_t_result(
        self,
        before: str,
        after: str,
        before_label: str,
        after_label: str,
        before_scores: pd.Series,
        after_scores: pd.Series,
        assumptions: dict[str, float],
        *,
        route_reason: str,
        n_obs: int,
        n_total: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.ttest(after_scores, before_scores, paired=True).iloc[0]
        ci = tuple(float(value) for value in test["CI95"])
        return ComparisonResult(
            dv=after,
            group_var=before,
            test_name="paired_t",
            route_reason=route_reason,
            groups=self._paired_descriptions(
                (before_label, after_label),
                before_scores,
                after_scores,
            ),
            statistic=float(test["T"]),
            df=float(test["dof"]),
            p_value=float(test["p_val"]),
            effect_name="cohen_dz",
            effect_value=float(test["T"]) / float(np.sqrt(n_obs)),
            mean_diff_ci=(ci[0], ci[1]),
            assumptions=assumptions,
            apa_template_id="paired_t.v1",
            chart_spec=self._paired_chart(
                before,
                after,
                before_label,
                after_label,
                before_scores,
                after_scores,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=after_label,
            group_label=before_label,
            paired=True,
            before_label=before_label,
            after_label=after_label,
        )

    def _wilcoxon_result(
        self,
        before: str,
        after: str,
        before_label: str,
        after_label: str,
        before_scores: pd.Series,
        after_scores: pd.Series,
        assumptions: dict[str, float],
        *,
        route_reason: str,
        n_obs: int,
        n_total: int,
        n_dropped: int,
    ) -> ComparisonResult:
        test = pg.wilcoxon(after_scores, before_scores).iloc[0]
        return ComparisonResult(
            dv=after,
            group_var=before,
            test_name="wilcoxon",
            route_reason=route_reason,
            groups=self._paired_descriptions(
                (before_label, after_label),
                before_scores,
                after_scores,
            ),
            statistic=float(test["W_val"]),
            df=None,
            p_value=float(test["p_val"]),
            effect_name="rank_biserial",
            effect_value=float(test["RBC"]),
            mean_diff_ci=None,
            assumptions=assumptions,
            apa_template_id="wilcoxon.v1",
            chart_spec=self._paired_chart(
                before,
                after,
                before_label,
                after_label,
                before_scores,
                after_scores,
            ),
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            dv_label=after_label,
            group_label=before_label,
            paired=True,
            before_label=before_label,
            after_label=after_label,
        )

    @staticmethod
    def _paired_descriptions(
        labels: tuple[str, str],
        before_scores: pd.Series,
        after_scores: pd.Series,
    ) -> dict[str, GroupDesc]:
        return {
            labels[0]: GroupDesc(
                n=int(before_scores.count()),
                mean=float(before_scores.mean()),
                sd=float(before_scores.std(ddof=1)),
                median=float(before_scores.median()),
            ),
            labels[1]: GroupDesc(
                n=int(after_scores.count()),
                mean=float(after_scores.mean()),
                sd=float(after_scores.std(ddof=1)),
                median=float(after_scores.median()),
            ),
        }

    @staticmethod
    def _paired_chart(
        before: str,
        after: str,
        before_label: str,
        after_label: str,
        before_scores: pd.Series,
        after_scores: pd.Series,
    ) -> ChartSpec:
        return ChartSpec(
            type="paired_line",
            title="Paired scores",
            data={
                "before": before_scores.tolist(),
                "after": after_scores.tolist(),
                "before_variable": before,
                "after_variable": after,
                "before_label": before_label,
                "after_label": after_label,
            },
            x_label="Time",
            y_label="Score",
        )

    def reads(self) -> set[str]:
        return {str(self.params["before"]), str(self.params["after"])}

    def writes(self) -> set[str]:
        return {f"comparison:{self.params['before']}:{self.params['after']}:paired"}

    def provenance(self) -> str:
        return f"compared paired {self.params['before']} and {self.params['after']}"


Step.register_type(PairedComparisonStep.step_type, PairedComparisonStep)
