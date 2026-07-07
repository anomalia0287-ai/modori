from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable
from modori.results import ChartSpec, CoefficientRow, RegressionResult
from modori.steps.data_prep import import_read_params_from_step_params
from modori.table_io import TableLayoutOverride, read_full, read_header


REGRESSION_ENGINE_VOCABULARY = frozenset(
    {
        "adjusted_r_squared",
        "b",
        "breusch_pagan",
        "confidence_interval",
        "cooks_distance",
        "df",
        "durbin_watson",
        "f_statistic",
        "listwise_deletion",
        "p_value",
        "r_squared",
        "se",
        "shapiro_wilk",
        "standardized_beta",
        "t",
        "vif",
    }
)


def _dtype_name(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_numeric_dtype(series):
        return "float"
    return "string"


def _require_finite(label: str, values: Any) -> None:
    arr = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"Regression produced non-finite {label}; inference is undefined.")


def _as_float(value: Any, label: str) -> float:
    scalar = float(np.asarray(value).squeeze())
    _require_finite(label, [scalar])
    return scalar


def _file_type_from_params(path: Path, params: dict[str, Any]) -> str:
    explicit = params.get("file_type")
    if explicit:
        return str(explicit).lower().lstrip(".")
    return path.suffix.lower().lstrip(".")


def _layout_override_from_params(params: dict[str, Any]) -> TableLayoutOverride | None:
    raw = params.get("table_layout")
    if raw is None:
        return None
    if isinstance(raw, TableLayoutOverride):
        return raw
    if not isinstance(raw, Mapping):
        return None
    return TableLayoutOverride(
        sheet_name=_optional_str(raw.get("sheet_name")),
        header_row_index=_optional_int(raw.get("header_row_index")),
        header_row_count=_optional_int(raw.get("header_row_count")),
        data_start_row_index=_optional_int(raw.get("data_start_row_index")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


@dataclass
class RegressionCsvImportStep(Step):
    step_type = "import.regression_table"
    writes_are_static = False
    safe_for_untrusted_project_json = False

    def compute(self, ctx: PipelineContext) -> StepResult:
        read_params = import_read_params_from_step_params(self.params)
        scale_columns = {str(column) for column in self.params.get("scale_columns", [])}
        table = read_full(
            read_params.path,
            read_params.file_type,
            layout=read_params.layout,
            selection=read_params.selection,
            drop_aggregate_rows=read_params.drop_aggregate_rows,
            drop_duplicate_rows=read_params.drop_duplicate_rows,
        )
        frame = table.frame
        frame = frame.rename(columns={column: str(column) for column in frame.columns})
        variables: dict[str, Variable] = {}
        for column in frame.columns:
            measure = Measure.SCALE if column in scale_columns else (
                Measure.SCALE if pd.api.types.is_numeric_dtype(frame[column]) else Measure.NOMINAL
            )
            if measure == Measure.SCALE and not pd.api.types.is_numeric_dtype(frame[column]):
                raise ValueError(f"Regression column {column} must be numeric to be marked SCALE")
            variables[str(column)] = Variable(
                name=str(column),
                label=str(column),
                measure=measure,
                value_labels={},
                missing_values=[],
                dtype=_dtype_name(frame[column]),
                origin_step_id=self.id,
            )
        return StepResult(
            new_columns={str(column): frame[column] for column in frame.columns},
            new_variables=variables,
            analysis=None,
            notes=[
                f"Imported {len(frame)} rows and {len(frame.columns)} columns for regression.",
                *table.warnings,
            ],
        )

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        read_params = import_read_params_from_step_params(self.params)
        return set(
            read_header(
                read_params.path,
                read_params.file_type,
                layout=read_params.layout,
                selection=read_params.selection,
            )
        )


@dataclass
class MultipleRegressionStep(Step):
    step_type = "stats.regression_ols"
    produces_analysis = True

    def compute(self, ctx: PipelineContext) -> StepResult:
        dv = str(self.params["dv"])
        predictors = [str(predictor) for predictor in self.params.get("predictors", [])]
        policy = dict(
            self.params.get(
                "regression_policy",
                self.params.get("policy", {"preset": "modern"}),
            )
        )
        self._validate_contract(ctx.dataset, dv, predictors, policy)

        order_var = policy.get("order_var")
        ordered_data = bool(policy.get("ordered_data", False)) or bool(order_var)
        compute_columns = [dv, *predictors]
        if order_var:
            compute_columns.append(str(order_var))

        frame = ctx.dataset.frame_for_compute(compute_columns).dropna()
        if order_var:
            frame = frame.sort_values(str(order_var), kind="mergesort")

        n_total = int(len(ctx.dataset.df))
        n_obs = int(len(frame))
        n_dropped = int(n_total - n_obs)
        if n_obs <= len(predictors) + 1:
            raise ValueError(
                "Regression requires more complete observations than estimated parameters."
            )

        y = pd.to_numeric(frame[dv], errors="raise").astype(float)
        x_pred = frame[predictors].apply(pd.to_numeric, errors="raise").astype(float)
        values = pd.concat([y.rename(dv), x_pred], axis=1)
        if not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError("Regression inputs must be finite numeric values.")

        self._validate_variance(values, dv, predictors)
        x = sm.add_constant(x_pred, has_constant="add")
        x = x.rename(columns={"const": "(Intercept)"})
        x_arr = x.to_numpy(dtype=float)
        y_arr = y.to_numpy(dtype=float)
        if np.linalg.matrix_rank(x_arr) < x_arr.shape[1]:
            raise ValueError(
                "Regression predictors are perfectly collinear: "
                f"{', '.join(predictors)}"
            )

        model = sm.OLS(y_arr, x_arr).fit()
        if model.df_resid <= 0:
            raise ValueError("Regression residual degrees of freedom must be positive.")
        if not np.isfinite(model.ssr) or np.isclose(float(model.ssr), 0.0, atol=1e-12):
            raise ValueError(
                "Regression model has zero residual variance; inferential statistics are undefined."
            )

        influence = model.get_influence()
        leverage = np.asarray(influence.hat_matrix_diag, dtype=float)
        _require_finite("leverage values", leverage)
        bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, x_arr)
        bp_p = _as_float(bp_p, "Breusch-Pagan p-value")
        dw = _as_float(durbin_watson(model.resid), "Durbin-Watson statistic")
        shapiro_p = self._shapiro_p(model.resid)
        cooks = np.asarray(influence.cooks_distance[0], dtype=float)
        _require_finite("Cook's distance", cooks)

        se_type = self._select_se_type(policy, bp_p)
        selected = model
        if se_type == "HC3":
            if np.any(leverage >= 1.0 - 1e-12):
                raise ValueError(
                    "HC3 robust covariance is undefined because at least one leverage value is 1."
                )
            selected = model.get_robustcov_results(cov_type="HC3")
            _require_finite("HC3 covariance", selected.cov_params())

        params = np.asarray(selected.params, dtype=float)
        ses = np.asarray(selected.bse, dtype=float)
        t_values = np.asarray(selected.tvalues, dtype=float)
        p_values = np.asarray(selected.pvalues, dtype=float)
        ci = np.asarray(selected.conf_int(alpha=0.05), dtype=float)
        _require_finite("coefficients", params)
        _require_finite("standard errors", ses)
        _require_finite("t values", t_values)
        _require_finite("p values", p_values)
        _require_finite("confidence intervals", ci)

        f_statistic, f_p_value = self._model_test(selected, model, len(predictors), se_type)
        vif_by_predictor = self._vifs(x_arr, predictors)
        coefficients = self._coefficient_rows(
            names=["(Intercept)", *predictors],
            params=params,
            ses=ses,
            t_values=t_values,
            p_values=p_values,
            ci=ci,
            y=y,
            x_pred=x_pred,
            vif_by_predictor=vif_by_predictor,
        )

        max_vif = max(vif_by_predictor.values()) if vif_by_predictor else None
        diagnostics: dict[str, object] = {
            "breusch_pagan_statistic": _as_float(bp_stat, "Breusch-Pagan statistic"),
            "breusch_pagan_p": bp_p,
            "bp_p": bp_p,
            "durbin_watson": dw,
            "dw": dw,
            "shapiro_resid_p": shapiro_p,
            "shapiro_p": shapiro_p,
            "max_cooks": _as_float(np.max(cooks), "maximum Cook's distance"),
            "cook_threshold": 4.0 / n_obs,
            "max_vif": max_vif,
            "vif": vif_by_predictor,
            "model_test": "robust_wald_f" if se_type == "HC3" else "classical_f",
        }
        warnings = self._warnings(
            policy=policy,
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            bp_p=bp_p,
            shapiro_p=shapiro_p,
            se_type=se_type,
            dw=dw,
            ordered_data=ordered_data,
            max_cooks=float(diagnostics["max_cooks"]),
            cook_threshold=float(diagnostics["cook_threshold"]),
            max_vif=max_vif,
        )
        educational_interpretation = self._educational_interpretation(
            result_dv=dv,
            coefficients=coefficients,
            r_squared=_as_float(model.rsquared, "R-squared"),
            warnings=warnings,
        )
        diagnostic_chart_specs = self._diagnostic_chart_specs(
            residuals=np.asarray(model.resid, dtype=float),
            fitted=np.asarray(model.fittedvalues, dtype=float),
            cooks=cooks,
            bp_p=bp_p,
            shapiro_p=shapiro_p,
            n_obs=n_obs,
            max_cooks=float(diagnostics["max_cooks"]),
            cook_threshold=float(diagnostics["cook_threshold"]),
            policy=policy,
        )

        chart_rows = [
            {
                "name": row.name,
                "b": row.b,
                "beta": row.beta,
                "ci": row.beta_ci,
                "p_value": row.p_value,
            }
            for row in coefficients
            if row.name != "(Intercept)"
        ]
        result = RegressionResult(
            dv=dv,
            predictors=predictors,
            n_obs=n_obs,
            n_total=n_total,
            n_dropped=n_dropped,
            se_type=se_type,
            r_squared=_as_float(model.rsquared, "R-squared"),
            adj_r_squared=_as_float(model.rsquared_adj, "adjusted R-squared"),
            f_statistic=f_statistic,
            df_model=int(round(float(model.df_model))),
            df_resid=int(round(float(model.df_resid))),
            f_p_value=f_p_value,
            coefficients=coefficients,
            diagnostics=diagnostics,
            warnings=warnings,
            apa_template_id="regression.v1",
            chart_spec=ChartSpec(
                type="coefficient_forest",
                title="Standardized regression coefficients",
                data={"rows": chart_rows, "se_type": se_type},
                x_label="Standardized beta",
                y_label="Predictor",
            ),
            educational_interpretation=educational_interpretation,
            diagnostic_chart_specs=diagnostic_chart_specs,
        )
        return StepResult(
            new_columns={},
            new_variables={},
            analysis=result,
            notes=[f"Fitted OLS regression for {dv} with {len(predictors)} predictors."],
        )

    def reads(self) -> set[str]:
        policy = dict(self.params.get("regression_policy", self.params.get("policy", {})))
        reads = {str(self.params["dv"]), *{str(item) for item in self.params.get("predictors", [])}}
        if policy.get("order_var"):
            reads.add(str(policy["order_var"]))
        return reads

    def writes(self) -> set[str]:
        return {f"analysis:{self.id}"}

    def provenance(self) -> str:
        predictors = ", ".join(str(item) for item in self.params.get("predictors", []))
        return f"OLS regression {self.params['dv']} on {predictors}"

    @staticmethod
    def _validate_contract(
        dataset: Dataset,
        dv: str,
        predictors: list[str],
        policy: dict[str, Any],
    ) -> None:
        if not predictors:
            raise ValueError("MultipleRegressionStep requires at least one predictor.")
        if len(set(predictors)) != len(predictors):
            raise ValueError("Regression predictors must be unique.")
        if dv in predictors:
            raise ValueError("Regression dependent variable cannot also be a predictor.")
        MultipleRegressionStep._require_scale_numeric(dataset, dv, "dependent variable")
        for predictor in predictors:
            MultipleRegressionStep._require_scale_numeric(dataset, predictor, "predictor")
        order_var = policy.get("order_var")
        if order_var and str(order_var) not in dataset.variables:
            raise ValueError(f"Regression order_var {order_var} is not present in the dataset.")

    @staticmethod
    def _require_scale_numeric(dataset: Dataset, column: str, role: str) -> None:
        if column not in dataset.variables:
            raise ValueError(f"Regression {role} {column} is not present in the dataset.")
        variable = dataset.variables[column]
        if variable.measure != Measure.SCALE:
            raise ValueError(f"Regression {role} must be SCALE: {column}")
        series = dataset.frame_for_compute([column])[column]
        if not pd.api.types.is_numeric_dtype(series.dropna()):
            raise ValueError(f"Regression {role} must be numeric: {column}")

    @staticmethod
    def _validate_variance(values: pd.DataFrame, dv: str, predictors: list[str]) -> None:
        for column in [dv, *predictors]:
            if values[column].nunique(dropna=True) < 2:
                raise ValueError(f"Regression variable {column} must have non-zero variance.")

    @staticmethod
    def _select_se_type(policy: dict[str, Any], bp_p: float) -> str:
        preset = str(policy.get("preset", "modern")).lower()
        alpha = float(policy.get("heteroscedasticity_alpha", policy.get("alpha", 0.05)))
        explicit = policy.get("se_type")
        if explicit is not None:
            se_type = str(explicit).upper()
            if se_type not in {"CLASSICAL", "HC3"}:
                raise ValueError(f"Unsupported regression se_type: {explicit}")
            return "classical" if se_type == "CLASSICAL" else "HC3"
        if preset == "classic":
            return "classical"
        if preset == "modern":
            return "HC3" if bp_p < alpha else "classical"
        if preset == "hc3":
            return "HC3"
        if preset == "custom":
            if policy.get("use_hc3") is True or policy.get("robust") is True:
                return "HC3"
            if policy.get("use_hc3") is False or policy.get("robust") is False:
                return "classical"
            return "HC3" if bp_p < alpha else "classical"
        raise ValueError(f"Unsupported regression policy preset: {preset}")

    @staticmethod
    def _shapiro_p(residuals: np.ndarray) -> float | None:
        n_obs = len(residuals)
        if not 3 <= n_obs <= 5000:
            return None
        return _as_float(stats.shapiro(residuals).pvalue, "Shapiro-Wilk p-value")

    @staticmethod
    def _model_test(selected: Any, model: Any, n_predictors: int, se_type: str) -> tuple[float, float]:
        if se_type == "HC3":
            constraints = np.zeros((n_predictors, n_predictors + 1))
            constraints[:, 1:] = np.eye(n_predictors)
            test = selected.f_test(constraints)
            return (
                _as_float(test.fvalue, "robust Wald F statistic"),
                _as_float(test.pvalue, "robust Wald F p-value"),
            )
        return (
            _as_float(model.fvalue, "classical F statistic"),
            _as_float(model.f_pvalue, "classical F p-value"),
        )

    @staticmethod
    def _vifs(x_arr: np.ndarray, predictors: list[str]) -> dict[str, float]:
        if len(predictors) < 2:
            return {}
        vifs: dict[str, float] = {}
        for offset, predictor in enumerate(predictors, start=1):
            value = float(variance_inflation_factor(x_arr, offset))
            _require_finite(f"VIF for {predictor}", [value])
            vifs[predictor] = value
        return vifs

    @staticmethod
    def _coefficient_rows(
        *,
        names: list[str],
        params: np.ndarray,
        ses: np.ndarray,
        t_values: np.ndarray,
        p_values: np.ndarray,
        ci: np.ndarray,
        y: pd.Series,
        x_pred: pd.DataFrame,
        vif_by_predictor: dict[str, float],
    ) -> list[CoefficientRow]:
        y_sd = float(y.std(ddof=1))
        rows: list[CoefficientRow] = []
        for index, name in enumerate(names):
            beta = None
            beta_ci = None
            vif = None
            if name != "(Intercept)":
                x_sd = float(x_pred[name].std(ddof=1))
                if x_sd <= 0 or y_sd <= 0:
                    raise ValueError("Regression standardized beta requires non-zero variance.")
                scale = x_sd / y_sd
                beta = float(params[index] * scale)
                beta_ci = (float(ci[index, 0] * scale), float(ci[index, 1] * scale))
                _require_finite(f"standardized beta for {name}", [beta, *beta_ci])
                vif = vif_by_predictor.get(name)
            rows.append(
                CoefficientRow(
                    name=name,
                    b=float(params[index]),
                    se=float(ses[index]),
                    beta=beta,
                    beta_ci=beta_ci,
                    t=float(t_values[index]),
                    p_value=float(p_values[index]),
                    ci=(float(ci[index, 0]), float(ci[index, 1])),
                    vif=vif,
                )
            )
        return rows

    @staticmethod
    def _educational_interpretation(
        *,
        result_dv: str,
        coefficients: list[CoefficientRow],
        r_squared: float,
        warnings: list[str],
    ) -> list[str]:
        interpretation = [
            f"This model explains approximately {r_squared * 100:.1f}% of the variance in {result_dv}."
        ]
        for row in coefficients:
            if row.name == "(Intercept)" or row.beta is None or row.p_value >= 0.05:
                continue
            direction = "increases" if row.beta > 0 else "decreases"
            interpretation.append(
                f"When {row.name} is one standard deviation higher, {result_dv} tends to "
                f"{direction} by about {abs(row.beta):.2f} standard deviations, holding the "
                "other predictors constant."
            )
        for warning in warnings:
            interpretation.append(f"Diagnostic note: {warning}")
        return interpretation

    @staticmethod
    def _diagnostic_chart_specs(
        *,
        residuals: np.ndarray,
        fitted: np.ndarray,
        cooks: np.ndarray,
        bp_p: float,
        shapiro_p: float | None,
        n_obs: int,
        max_cooks: float,
        cook_threshold: float,
        policy: dict[str, Any],
    ) -> list[ChartSpec]:
        specs: list[ChartSpec] = []
        alpha = float(policy.get("heteroscedasticity_alpha", policy.get("alpha", 0.05)))
        if bp_p < alpha:
            specs.append(
                ChartSpec(
                    type="residual_vs_fitted",
                    title="Residuals vs fitted values",
                    data={
                        "fitted": [float(value) for value in fitted],
                        "residuals": [float(value) for value in residuals],
                    },
                    x_label="Fitted value",
                    y_label="Residual",
                )
            )
        shapiro_alpha = float(policy.get("shapiro_alpha", policy.get("normality_alpha", 0.05)))
        if shapiro_p is not None and n_obs < 30 and shapiro_p < shapiro_alpha:
            ordered = np.sort(residuals)
            probabilities = (np.arange(1, n_obs + 1) - 0.5) / n_obs
            theoretical = stats.norm.ppf(probabilities)
            specs.append(
                ChartSpec(
                    type="residual_qq",
                    title="Residual Q-Q plot",
                    data={
                        "theoretical": [float(value) for value in theoretical],
                        "sample": [float(value) for value in ordered],
                    },
                    x_label="Theoretical normal quantile",
                    y_label="Ordered residual",
                )
            )
        if max_cooks > cook_threshold:
            specs.append(
                ChartSpec(
                    type="cooks_distance",
                    title="Cook's distance",
                    data={
                        "index": list(range(1, len(cooks) + 1)),
                        "cooks": [float(value) for value in cooks],
                        "threshold": float(cook_threshold),
                    },
                    x_label="Case",
                    y_label="Cook's distance",
                )
            )
        return specs

    @staticmethod
    def _warnings(
        *,
        policy: dict[str, Any],
        n_obs: int,
        n_total: int,
        n_dropped: int,
        bp_p: float,
        shapiro_p: float | None,
        se_type: str,
        dw: float,
        ordered_data: bool,
        max_cooks: float,
        cook_threshold: float,
        max_vif: float | None,
    ) -> list[str]:
        warnings: list[str] = []
        if n_dropped:
            warnings.append(
                f"Listwise deletion dropped {n_dropped} of {n_total} rows for missing regression inputs."
            )
        missing_threshold = policy.get(
            "missing_warning_threshold",
            policy.get("missing_threshold", policy.get("max_missing_ratio", 0.10)),
        )
        if n_total:
            if n_dropped / n_total > float(missing_threshold):
                warnings.append(
                    f"Missingness exceeded the configured threshold ({float(missing_threshold):.3g})."
                )
        alpha = float(policy.get("heteroscedasticity_alpha", policy.get("alpha", 0.05)))
        if bp_p < alpha and se_type == "HC3":
            warnings.append(
                f"Breusch-Pagan p={bp_p:.3g}; using HC3 robust standard errors."
            )
        elif bp_p < alpha:
            warnings.append(
                f"Breusch-Pagan p={bp_p:.3g}; heteroscedasticity was detected, "
                "but classical standard errors were retained by policy."
            )
        shapiro_alpha = float(policy.get("shapiro_alpha", policy.get("normality_alpha", 0.05)))
        if shapiro_p is not None and n_obs < 30 and shapiro_p < shapiro_alpha:
            warnings.append(
                f"Shapiro-Wilk residual normality p={shapiro_p:.3g}; residuals deviate "
                "from normality in this small-sample model."
            )
        elif shapiro_p is None and n_obs > 5000:
            warnings.append(
                "Shapiro-Wilk residual normality check was skipped because the sample "
                f"size ({n_obs}) exceeds the supported range."
            )
        dw_distance = float(policy.get("durbin_watson_warning_distance", 0.5))
        if ordered_data and abs(dw - 2.0) > dw_distance:
            warnings.append(
                f"Durbin-Watson statistic was {dw:.3g}; residual autocorrelation may be present."
            )
        if max_cooks > cook_threshold:
            warnings.append(
                f"Maximum Cook's distance {max_cooks:.3g} exceeded the 4/n threshold {cook_threshold:.3g}."
            )
        vif_moderate_threshold = float(
            policy.get("vif_warning_threshold", policy.get("vif_moderate_threshold", 5.0))
        )
        vif_severe_threshold = float(
            policy.get("vif_severe_threshold", policy.get("vif_strong_warning_threshold", 10.0))
        )
        if max_vif is not None and max_vif > vif_severe_threshold:
            warnings.append(f"Severe VIF {max_vif:.3g} indicates severe multicollinearity.")
        elif max_vif is not None and max_vif > vif_moderate_threshold:
            warnings.append(f"Moderate VIF {max_vif:.3g} indicates moderate multicollinearity.")
        return warnings


Step.register_type(RegressionCsvImportStep.step_type, RegressionCsvImportStep)
Step.register_type(MultipleRegressionStep.step_type, MultipleRegressionStep)
