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
from modori.regression_design import (
    CategoricalEncoding as _CategoricalEncoding,
    InteractionSpec as _InteractionSpec,
    RegressionDesignMatrix as _DesignMatrix,
    TermMetadata as _TermMetadata,
    build_regression_design_matrix,
)
from modori.results import ChartSpec, CoefficientRow, RegressionResult, SimpleSlopeRow
from modori.statistics_numerics import require_well_conditioned_ols_design
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


def _level_label(value: object) -> str:
    return str(value)


def _require_regression_schema_version(params: Mapping[str, object], current: int) -> int | None:
    version = params.get("schema_version")
    if version is None:
        return None
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("regression_ols schema_version must be an integer")
    if version > current:
        raise ValueError("regression_ols params use a newer schema_version")
    if version < current:
        raise ValueError(f"unsupported regression_ols schema_version: {version}")
    return version


def _reject_unknown_regression_params(
    params: Mapping[str, object],
    allowed: set[str],
) -> None:
    unknown = set(params) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown regression_ols params: {names}")


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
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {"preset": "classic"},
        },
        "legacy": {"dv": "y", "predictors": ["x"], "policy": {"preset": "classic"}},
        "newer": {"schema_version": 999, "dv": "y", "predictors": ["x"]},
        "unknown_current": {
            "schema_version": 1,
            "dv": "y",
            "predictors": ["x"],
            "regression_policy": {"preset": "classic"},
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = _require_regression_schema_version(
            params,
            cls.CURRENT_SCHEMA_VERSION,
        )
        migrated = dict(params)
        if version is None:
            migrated["schema_version"] = cls.CURRENT_SCHEMA_VERSION
        if "policy" in migrated:
            if "regression_policy" in migrated:
                raise ValueError(
                    "regression_ols params cannot include both policy and regression_policy"
                )
            migrated["regression_policy"] = migrated.pop("policy")
        return migrated

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        _reject_unknown_regression_params(
            params,
            {"schema_version", "dv", "predictors", "regression_policy"},
        )
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("regression_ols params were not migrated to the current schema")
        dv = params.get("dv")
        if not isinstance(dv, str) or not dv:
            raise ValueError("regression_ols param dv must be a non-empty string")
        predictors = params.get("predictors")
        if (
            not isinstance(predictors, list)
            or not all(isinstance(item, str) and item for item in predictors)
        ):
            raise ValueError("regression_ols param predictors must be a list of strings")
        policy = params.get("regression_policy", {"preset": "modern"})
        if not isinstance(policy, Mapping):
            raise ValueError("regression_ols param regression_policy must be an object")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "dv": dv,
            "predictors": list(predictors),
            "regression_policy": dict(policy),
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        dv = str(params["dv"])
        predictors = [str(predictor) for predictor in params["predictors"]]
        policy = dict(params["regression_policy"])
        categorical_encodings = self._categorical_encodings(policy)
        interactions = self._interaction_specs(policy)
        simple_slopes_enabled = self._simple_slopes_enabled(policy, interactions)
        effective_predictors = self._effective_predictors(predictors, interactions)
        self._validate_contract(
            ctx.dataset,
            dv,
            predictors,
            effective_predictors,
            policy,
            categorical_encodings,
            interactions,
        )

        order_var = policy.get("order_var")
        ordered_data = bool(policy.get("ordered_data", False)) or bool(order_var)
        compute_columns = [dv, *effective_predictors]
        if order_var:
            compute_columns.append(str(order_var))

        frame = ctx.dataset.frame_for_compute(compute_columns).dropna()
        if order_var:
            frame = frame.sort_values(str(order_var), kind="mergesort")

        n_total = int(len(ctx.dataset.df))
        n_obs = int(len(frame))
        n_dropped = int(n_total - n_obs)

        y = pd.to_numeric(frame[dv], errors="raise").astype(float)
        design = self._build_design_matrix(
            frame=frame,
            predictors=effective_predictors,
            categorical_encodings=categorical_encodings,
            interactions=interactions,
            policy=policy,
        )
        x_pred = design.x_pred
        term_names = list(x_pred.columns)
        if n_obs <= len(term_names) + 1:
            raise ValueError(
                "Regression requires more complete observations than estimated parameters."
            )
        values = pd.concat([y.rename(dv), x_pred], axis=1)
        if not np.all(np.isfinite(values.to_numpy(dtype=float))):
            raise ValueError("Regression inputs must be finite numeric values.")

        self._validate_variance(values, dv, term_names)
        x = sm.add_constant(x_pred, has_constant="add")
        x = x.rename(columns={"const": "(Intercept)"})
        x_arr = x.to_numpy(dtype=float)
        y_arr = y.to_numpy(dtype=float)
        if np.linalg.matrix_rank(x_arr) < x_arr.shape[1]:
            raise ValueError(
                "Regression predictors are rank deficient or perfectly collinear: "
                f"{', '.join(term_names)}"
            )
        condition_number = require_well_conditioned_ols_design(
            x_arr,
            label="Regression OLS",
        )

        y_offset = float(y_arr.mean())
        model = sm.OLS(y_arr - y_offset, x_arr).fit()
        if model.df_resid <= 0:
            raise ValueError("Regression residual degrees of freedom must be positive.")
        centered_total_ss = float((y_arr - y_offset) @ (y_arr - y_offset))
        residual_variance_floor = max(
            1e-12,
            np.finfo(float).eps * max(centered_total_ss, 1.0),
        )
        if (
            not np.isfinite(model.ssr)
            or float(model.ssr) <= residual_variance_floor
        ):
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
        params_for_output = params.copy()
        t_values_for_output = t_values.copy()
        p_values_for_output = p_values.copy()
        ci_for_output = ci.copy()
        params_for_output[0] += y_offset
        ci_for_output[0, :] += y_offset
        t_values_for_output[0] = params_for_output[0] / ses[0]
        if getattr(selected, "use_t", True):
            p_values_for_output[0] = 2 * stats.t.sf(
                abs(t_values_for_output[0]),
                float(model.df_resid),
            )
        else:
            p_values_for_output[0] = 2 * stats.norm.sf(abs(t_values_for_output[0]))
        _require_finite("coefficients", params)
        _require_finite("standard errors", ses)
        _require_finite("t values", t_values)
        _require_finite("p values", p_values)
        _require_finite("confidence intervals", ci)

        f_statistic, f_p_value = self._model_test(selected, model, len(term_names), se_type)
        vif_by_predictor = self._vifs(x_arr, term_names)
        coefficients = self._coefficient_rows(
            names=["(Intercept)", *term_names],
            params=params_for_output,
            ses=ses,
            t_values=t_values_for_output,
            p_values=p_values_for_output,
            ci=ci_for_output,
            y=y,
            x_pred=x_pred,
            vif_by_predictor=vif_by_predictor,
            term_metadata=design.term_metadata,
        )
        simple_slopes = self._simple_slopes(
            interactions=interactions,
            categorical_encodings=categorical_encodings,
            design=design,
            params=params,
            covariance=np.asarray(selected.cov_params(), dtype=float),
            df_resid=float(model.df_resid),
            term_names=["(Intercept)", *term_names],
        ) if simple_slopes_enabled else []

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
            "categorical_predictors": {
                name: {"reference": encoding.reference, "levels": list(encoding.levels)}
                for name, encoding in categorical_encodings.items()
                if name in effective_predictors
            },
            "interactions": [list(interaction.terms) for interaction in interactions],
            "transformed_terms": design.transformed_terms,
            "centers": design.centers,
            "condition_number": condition_number,
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
            fitted=np.asarray(model.fittedvalues, dtype=float) + y_offset,
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
            predictors=effective_predictors,
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
            simple_slopes=simple_slopes,
        )
        return StepResult(
            new_columns={},
            new_variables={},
            analysis=result,
            notes=[f"Fitted OLS regression for {dv} with {len(predictors)} predictors."],
        )

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        policy = dict(params["regression_policy"])
        interactions = self._interaction_specs(policy)
        effective_predictors = self._effective_predictors(
            [str(item) for item in params["predictors"]],
            interactions,
        )
        reads = {str(params["dv"]), *effective_predictors}
        if policy.get("order_var"):
            reads.add(str(policy["order_var"]))
        return reads

    def writes(self) -> set[str]:
        return {f"analysis:{self.id}"}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        policy = dict(params["regression_policy"])
        interactions = self._interaction_specs(policy)
        predictors = ", ".join(
            self._effective_predictors([str(item) for item in params["predictors"]], interactions)
        )
        return f"OLS regression {params['dv']} on {predictors}"

    @staticmethod
    def _validate_contract(
        dataset: Dataset,
        dv: str,
        predictors: list[str],
        effective_predictors: list[str],
        policy: dict[str, Any],
        categorical_encodings: dict[str, _CategoricalEncoding],
        interactions: list[_InteractionSpec],
    ) -> None:
        if not predictors:
            raise ValueError("MultipleRegressionStep requires at least one predictor.")
        if len(set(predictors)) != len(predictors):
            raise ValueError("Regression predictors must be unique.")
        if dv in effective_predictors:
            raise ValueError("Regression dependent variable cannot also be a predictor.")
        MultipleRegressionStep._require_scale_numeric(dataset, dv, "dependent variable")
        for predictor in effective_predictors:
            if predictor in categorical_encodings:
                MultipleRegressionStep._require_present(dataset, predictor, "categorical predictor")
            else:
                variable = dataset.variables.get(predictor)
                if variable is not None and variable.measure == Measure.NOMINAL:
                    raise ValueError(
                        f"Regression categorical predictor {predictor} requires explicit encoding "
                        "in regression_policy.categorical_predictors."
                    )
                MultipleRegressionStep._require_scale_numeric(dataset, predictor, "predictor")
        extra_encodings = set(categorical_encodings) - set(effective_predictors)
        if extra_encodings:
            names = ", ".join(sorted(extra_encodings))
            raise ValueError(f"Regression categorical encoding declared for non-predictor: {names}")
        if interactions:
            MultipleRegressionStep._validate_interaction_contract(
                dataset,
                categorical_encodings,
                interactions,
                policy,
            )
        order_var = policy.get("order_var")
        if order_var and str(order_var) not in dataset.variables:
            raise ValueError(f"Regression order_var {order_var} is not present in the dataset.")

    @staticmethod
    def _require_present(dataset: Dataset, column: str, role: str) -> None:
        if column not in dataset.variables:
            raise ValueError(f"Regression {role} {column} is not present in the dataset.")

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
    def _categorical_encodings(policy: dict[str, Any]) -> dict[str, _CategoricalEncoding]:
        raw = policy.get("categorical_predictors", {})
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ValueError("regression_policy.categorical_predictors must be an object")

        encodings: dict[str, _CategoricalEncoding] = {}
        for variable, spec in raw.items():
            name = str(variable)
            if not name:
                raise ValueError("categorical predictor names must be non-empty")
            if not isinstance(spec, Mapping):
                raise ValueError(f"categorical encoding for {name} must be an object")
            if "reference" not in spec:
                raise ValueError(f"categorical encoding for {name} requires a reference level")
            raw_levels = spec.get("levels", spec.get("order"))
            if not isinstance(raw_levels, list | tuple) or not raw_levels:
                raise ValueError(f"categorical encoding for {name} requires explicit levels")

            reference = _level_label(spec["reference"])
            levels = tuple(_level_label(level) for level in raw_levels)
            if len(set(levels)) != len(levels):
                raise ValueError(f"categorical encoding for {name} has duplicate levels")
            if reference not in levels:
                raise ValueError(
                    f"categorical encoding for {name} reference must appear in levels"
                )
            if len(levels) < 2:
                raise ValueError(f"categorical encoding for {name} requires at least two levels")
            encodings[name] = _CategoricalEncoding(
                variable=name,
                reference=reference,
                levels=levels,
            )
        return encodings

    @staticmethod
    def _interaction_specs(policy: dict[str, Any]) -> list[_InteractionSpec]:
        raw = policy.get("interactions", [])
        if raw is None:
            return []
        if not isinstance(raw, list | tuple):
            raise ValueError("regression_policy.interactions must be a list")

        specs: list[_InteractionSpec] = []
        seen: set[tuple[str, str]] = set()
        for item in raw:
            if isinstance(item, Mapping):
                terms = item.get("terms")
            else:
                terms = item
            if not isinstance(terms, list | tuple) or len(terms) != 2:
                raise ValueError("regression interactions must declare exactly two terms")
            first, second = (str(terms[0]), str(terms[1]))
            if not first or not second:
                raise ValueError("regression interaction terms must be non-empty")
            if first == second:
                raise ValueError("regression interaction terms must be distinct")
            duplicate_key = tuple(sorted((first, second)))
            if duplicate_key in seen:
                raise ValueError(f"duplicate interaction: {first}:{second}")
            seen.add(duplicate_key)
            specs.append(_InteractionSpec(first=first, second=second))
        return specs

    @staticmethod
    def _simple_slopes_enabled(
        policy: dict[str, Any],
        interactions: list[_InteractionSpec],
    ) -> bool:
        raw = policy.get("simple_slopes")
        if raw is None:
            return bool(interactions)
        if raw is True:
            if not interactions:
                raise ValueError("Regression simple slopes require an explicit supported interaction.")
            return True
        if raw is False:
            return False
        if raw == "auto":
            return bool(interactions)
        raise ValueError(
            "Unsupported regression simple_slopes policy; supported values are true, false, or 'auto'."
        )

    @staticmethod
    def _effective_predictors(
        predictors: list[str],
        interactions: list[_InteractionSpec],
    ) -> list[str]:
        effective = list(predictors)
        for interaction in interactions:
            for term in interaction.terms:
                if term not in effective:
                    effective.append(term)
        return effective

    @staticmethod
    def _validate_interaction_contract(
        dataset: Dataset,
        categorical_encodings: dict[str, _CategoricalEncoding],
        interactions: list[_InteractionSpec],
        policy: dict[str, Any],
    ) -> None:
        center_policy = policy.get("center_scale_interactions")
        if center_policy != "mean":
            raise ValueError(
                "Regression scale interactions require explicit mean centering with "
                "regression_policy.center_scale_interactions='mean'."
            )
        for interaction in interactions:
            kinds = []
            for term in interaction.terms:
                MultipleRegressionStep._require_present(dataset, term, "interaction term")
                kinds.append("categorical" if term in categorical_encodings else "scale")
            if kinds == ["categorical", "categorical"]:
                raise ValueError("Regression unsupported categorical-by-categorical interaction.")
            if "scale" in kinds:
                for term, kind in zip(interaction.terms, kinds, strict=True):
                    if kind == "scale":
                        MultipleRegressionStep._require_scale_numeric(
                            dataset,
                            term,
                            "interaction term",
                        )

    @staticmethod
    def _build_design_matrix(
        *,
        frame: pd.DataFrame,
        predictors: list[str],
        categorical_encodings: dict[str, _CategoricalEncoding],
        interactions: list[_InteractionSpec],
        policy: dict[str, Any],
    ) -> _DesignMatrix:
        return build_regression_design_matrix(
            frame=frame,
            predictors=predictors,
            categorical_encodings=categorical_encodings,
            interactions=interactions,
            center_scale_interactions=(
                policy.get("center_scale_interactions") == "mean"
            ),
            error_prefix="Regression",
        )

    @staticmethod
    def _simple_slopes(
        *,
        interactions: list[_InteractionSpec],
        categorical_encodings: dict[str, _CategoricalEncoding],
        design: _DesignMatrix,
        params: np.ndarray,
        covariance: np.ndarray,
        df_resid: float,
        term_names: list[str],
    ) -> list[SimpleSlopeRow]:
        if not interactions:
            return []
        index_by_name = {name: index for index, name in enumerate(term_names)}
        rows: list[SimpleSlopeRow] = []
        for interaction in interactions:
            first, second = interaction.terms
            first_is_categorical = first in categorical_encodings
            second_is_categorical = second in categorical_encodings
            if not first_is_categorical and not second_is_categorical:
                rows.extend(
                    MultipleRegressionStep._scale_scale_simple_slopes(
                        focal=first,
                        moderator=second,
                        design=design,
                        params=params,
                        covariance=covariance,
                        df_resid=df_resid,
                        index_by_name=index_by_name,
                    )
                )
                continue

            scale_var = second if first_is_categorical else first
            categorical_var = first if first_is_categorical else second
            rows.extend(
                MultipleRegressionStep._scale_categorical_simple_slopes(
                    scale_var=scale_var,
                    categorical_var=categorical_var,
                    encoding=categorical_encodings[categorical_var],
                    design=design,
                    params=params,
                    covariance=covariance,
                    df_resid=df_resid,
                    index_by_name=index_by_name,
                )
            )
        return rows

    @staticmethod
    def _scale_scale_simple_slopes(
        *,
        focal: str,
        moderator: str,
        design: _DesignMatrix,
        params: np.ndarray,
        covariance: np.ndarray,
        df_resid: float,
        index_by_name: dict[str, int],
    ) -> list[SimpleSlopeRow]:
        focal_term = design.scale_terms[focal].name
        moderator_term = design.scale_terms[moderator].name
        interaction_term = f"{focal_term}:{moderator_term}"
        focal_index = index_by_name[focal_term]
        interaction_index = index_by_name[interaction_term]
        moderator_series = design.x_pred[moderator_term]
        moderator_sd = _as_float(moderator_series.std(ddof=1), f"SD for {moderator}")
        moderator_center = design.centers[moderator]
        rows = []
        for label, centered_value in [
            ("mean - 1 SD", -moderator_sd),
            ("mean", 0.0),
            ("mean + 1 SD", moderator_sd),
        ]:
            rows.append(
                MultipleRegressionStep._simple_slope_row(
                    focal_predictor=focal,
                    moderator=moderator,
                    moderator_value=moderator_center + centered_value,
                    moderator_label=label,
                    slope_weights={focal_index: 1.0, interaction_index: centered_value},
                    params=params,
                    covariance=covariance,
                    df_resid=df_resid,
                    interaction_term=interaction_term,
                )
            )
        return rows

    @staticmethod
    def _scale_categorical_simple_slopes(
        *,
        scale_var: str,
        categorical_var: str,
        encoding: _CategoricalEncoding,
        design: _DesignMatrix,
        params: np.ndarray,
        covariance: np.ndarray,
        df_resid: float,
        index_by_name: dict[str, int],
    ) -> list[SimpleSlopeRow]:
        scale_term = design.scale_terms[scale_var].name
        scale_index = index_by_name[scale_term]
        rows: list[SimpleSlopeRow] = []
        for level in encoding.levels:
            if level == encoding.reference:
                rows.append(
                    MultipleRegressionStep._simple_slope_row(
                        focal_predictor=scale_var,
                        moderator=categorical_var,
                        moderator_value=level,
                        moderator_label=f"{level} (reference)",
                        slope_weights={scale_index: 1.0},
                        params=params,
                        covariance=covariance,
                        df_resid=df_resid,
                        interaction_term=scale_term,
                    )
                )
                continue
            categorical_term = design.categorical_terms[categorical_var][level]
            interaction_term = f"{scale_term}:{categorical_term}"
            rows.append(
                MultipleRegressionStep._simple_slope_row(
                    focal_predictor=scale_var,
                    moderator=categorical_var,
                    moderator_value=level,
                    moderator_label=level,
                    slope_weights={
                        scale_index: 1.0,
                        index_by_name[interaction_term]: 1.0,
                    },
                    params=params,
                    covariance=covariance,
                    df_resid=df_resid,
                    interaction_term=interaction_term,
                )
            )
        return rows

    @staticmethod
    def _simple_slope_row(
        *,
        focal_predictor: str,
        moderator: str,
        moderator_value: float | str,
        moderator_label: str,
        slope_weights: dict[int, float],
        params: np.ndarray,
        covariance: np.ndarray,
        df_resid: float,
        interaction_term: str,
    ) -> SimpleSlopeRow:
        weights = np.zeros(len(params), dtype=float)
        for index, weight in slope_weights.items():
            weights[index] = weight
        slope = _as_float(weights @ params, "simple slope")
        variance = _as_float(weights @ covariance @ weights, "simple slope variance")
        if variance < 0 and np.isclose(variance, 0.0, atol=1e-12):
            variance = 0.0
        if variance <= 0:
            raise ValueError("Simple slope standard error must be positive.")
        se = float(np.sqrt(variance))
        t_value = _as_float(slope / se, "simple slope t value")
        p_value = _as_float(2 * stats.t.sf(abs(t_value), df_resid), "simple slope p-value")
        critical = _as_float(stats.t.ppf(0.975, df_resid), "simple slope critical value")
        ci = (float(slope - critical * se), float(slope + critical * se))
        _require_finite("simple slope confidence interval", ci)
        return SimpleSlopeRow(
            focal_predictor=focal_predictor,
            moderator=moderator,
            moderator_value=moderator_value,
            moderator_label=moderator_label,
            slope=slope,
            se=se,
            t=t_value,
            p_value=p_value,
            ci=ci,
            interaction_term=interaction_term,
        )

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
        term_metadata: dict[str, _TermMetadata],
    ) -> list[CoefficientRow]:
        y_sd = float(y.std(ddof=1))
        rows: list[CoefficientRow] = []
        for index, name in enumerate(names):
            beta = None
            beta_ci = None
            vif = None
            metadata = term_metadata.get(
                name,
                _TermMetadata(name=name, term_type="intercept" if name == "(Intercept)" else "term"),
            )
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
                    term_type=metadata.term_type,
                    source_variable=metadata.source_variable,
                    level=metadata.level,
                    reference_level=metadata.reference_level,
                    components=metadata.components,
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
            if row.term_type not in {"scale", "scale_centered"}:
                continue
            direction = "increases" if row.beta > 0 else "decreases"
            display_name = row.source_variable or row.name
            interpretation.append(
                f"When {display_name} is one standard deviation higher, {result_dv} tends to "
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
