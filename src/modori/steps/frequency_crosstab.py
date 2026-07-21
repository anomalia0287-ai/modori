from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from modori.core import Dataset, PipelineContext, Step, StepResult, Variable
from modori.frequency_crosstab_results import (
    AssociationTestResult,
    CrosstabCell,
    CrosstabTableResult,
    FrequencyCategoryRow,
    FrequencyCrosstabResult,
    FrequencyVariableTable,
)
from modori.steps.input_validation import (
    raise_for_step_input_issues,
    validate_step_input,
)


@dataclass
class FrequencyCrosstabStep(Step):
    step_type = "stats.frequency_crosstab"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "mode": "frequency",
            "variables": ["gender"],
        },
        "newer": {"schema_version": 999, "mode": "frequency", "variables": ["gender"]},
        "unknown_current": {
            "schema_version": 1,
            "mode": "frequency",
            "variables": ["gender"],
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("frequency_crosstab params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("frequency_crosstab params use a newer schema_version")
        if version == 1:
            return params
        raise ValueError(f"unsupported frequency_crosstab schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "mode",
            "variables",
            "row_variable",
            "column_variable",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown frequency_crosstab params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "frequency_crosstab params were not migrated to the current schema"
            )
        mode = params.get("mode")
        if mode not in {"frequency", "crosstab"}:
            raise ValueError("mode must be frequency or crosstab")
        language = params.get("language", "ko")
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")

        if mode == "frequency":
            variables = params.get("variables")
            if (
                not isinstance(variables, list)
                or not variables
                or not all(isinstance(variable, str) for variable in variables)
            ):
                raise ValueError("variables must be a non-empty list of variable keys")
            return {
                "schema_version": cls.CURRENT_SCHEMA_VERSION,
                "mode": "frequency",
                "variables": list(variables),
                "row_variable": None,
                "column_variable": None,
                "language": language,
            }

        row_variable = params.get("row_variable")
        column_variable = params.get("column_variable")
        if not isinstance(row_variable, str) or not isinstance(column_variable, str):
            raise ValueError("row_variable and column_variable must be variable keys")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "mode": "crosstab",
            "variables": [row_variable, column_variable],
            "row_variable": row_variable,
            "column_variable": column_variable,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        return set(str(variable) for variable in params["variables"])

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        variables = ", ".join(str(key) for key in params["variables"])
        return f"frequency crosstab for {variables}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> FrequencyCrosstabResult:
        dataset = ctx.dataset
        self._validate_dataset(dataset, params)
        variables = [str(variable) for variable in params["variables"]]
        frame = dataset.frame_for_compute(variables)
        if params["mode"] == "frequency":
            tables = tuple(
                self._frequency_table(dataset, frame, variable)
                for variable in variables
            )
            return FrequencyCrosstabResult(
                analysis_key="frequency_crosstab",
                title_ko="빈도분석",
                mode="frequency",
                variables=tuple(variables),
                n_total=int(len(frame)),
                frequency_tables=tables,
            )

        crosstab, warnings = self._crosstab_table(
            dataset,
            frame,
            str(params["row_variable"]),
            str(params["column_variable"]),
        )
        return FrequencyCrosstabResult(
            analysis_key="frequency_crosstab",
            title_ko="교차분석",
            mode="crosstab",
            variables=tuple(variables),
            n_total=int(len(frame)),
            crosstab=crosstab,
            warnings_ko=tuple(warnings),
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, params: dict[str, object]) -> None:
        issues = validate_step_input(
            dataset,
            FrequencyCrosstabStep.step_type,
            params,
        )
        raise_for_step_input_issues(FrequencyCrosstabStep.step_type, issues)

    def _frequency_table(
        self,
        dataset: Dataset,
        frame: pd.DataFrame,
        key: str,
    ) -> FrequencyVariableTable:
        variable = dataset.variables[key]
        series = frame[key]
        n_total = int(len(series))
        n_obs = int(series.notna().sum())
        n_missing = int(n_total - n_obs)
        non_missing = series.dropna()
        categories = []
        for value in self._ordered_values(non_missing, variable):
            count = int((non_missing == value).sum())
            percent = 0.0 if n_obs == 0 else (count / n_obs) * 100.0
            categories.append(
                FrequencyCategoryRow(
                    value=self._display_value(value),
                    label=self._label_for_value(variable, value),
                    count=count,
                    percent=float(percent),
                )
            )
        return FrequencyVariableTable(
            key=key,
            label=variable.label or key,
            measure=variable.measure.value,
            n_total=n_total,
            n_obs=n_obs,
            n_missing=n_missing,
            categories=tuple(categories),
        )

    def _crosstab_table(
        self,
        dataset: Dataset,
        frame: pd.DataFrame,
        row_key: str,
        column_key: str,
    ) -> tuple[CrosstabTableResult, list[str]]:
        row_variable = dataset.variables[row_key]
        column_variable = dataset.variables[column_key]
        row_series = frame[row_key]
        column_series = frame[column_key]
        observed = frame.loc[row_series.notna() & column_series.notna()]
        n_total = int(len(frame))
        n_obs = int(len(observed))
        n_missing_row = int(row_series.isna().sum())
        n_missing_column = int(column_series.isna().sum())
        n_excluded = int(n_total - n_obs)
        row_values = self._ordered_values(observed[row_key], row_variable)
        column_values = self._ordered_values(observed[column_key], column_variable)
        counts = np.array(
            [
                [
                    int(
                        (
                            (observed[row_key] == row_value)
                            & (observed[column_key] == column_value)
                        ).sum()
                    )
                    for column_value in column_values
                ]
                for row_value in row_values
            ],
            dtype=int,
        )
        test, warnings = self._association_test(counts)
        row_totals = counts.sum(axis=1) if counts.size else np.array([], dtype=int)
        column_totals = counts.sum(axis=0) if counts.size else np.array([], dtype=int)
        cells: list[tuple[CrosstabCell, ...]] = []
        for row_index, row_value in enumerate(row_values):
            row_cells = []
            for column_index, column_value in enumerate(column_values):
                count = int(counts[row_index, column_index])
                row_total = int(row_totals[row_index])
                column_total = int(column_totals[column_index])
                row_cells.append(
                    CrosstabCell(
                        row_value=self._display_value(row_value),
                        row_label=self._label_for_value(row_variable, row_value),
                        column_value=self._display_value(column_value),
                        column_label=self._label_for_value(
                            column_variable,
                            column_value,
                        ),
                        count=count,
                        row_percent=0.0
                        if row_total == 0
                        else float((count / row_total) * 100.0),
                        column_percent=0.0
                        if column_total == 0
                        else float((count / column_total) * 100.0),
                        total_percent=0.0
                        if n_obs == 0
                        else float((count / n_obs) * 100.0),
                        expected_count=test.expected_counts[row_index][column_index],
                    )
                )
            cells.append(tuple(row_cells))

        return (
            CrosstabTableResult(
                row_variable=row_key,
                row_label=row_variable.label or row_key,
                column_variable=column_key,
                column_label=column_variable.label or column_key,
                row_labels=tuple(
                    self._label_for_value(row_variable, value) for value in row_values
                ),
                column_labels=tuple(
                    self._label_for_value(column_variable, value)
                    for value in column_values
                ),
                n_total=n_total,
                n_obs=n_obs,
                n_missing_row=n_missing_row,
                n_missing_column=n_missing_column,
                n_excluded=n_excluded,
                cells=tuple(cells),
                test=test,
            ),
            warnings,
        )

    @staticmethod
    def _association_test(
        counts: np.ndarray,
    ) -> tuple[AssociationTestResult, list[str]]:
        try:
            chi2, p_value, df, expected = stats.chi2_contingency(
                counts,
                correction=False,
            )
        except ValueError as exc:
            raise ValueError("카이제곱 검정을 계산할 수 없는 교차표입니다.") from exc

        expected_array = np.asarray(expected, dtype=float)
        low_expected = expected_array < 5
        low_count = int(low_expected.sum())
        low_percent = float((low_count / expected_array.size) * 100.0)
        min_expected = float(expected_array.min()) if expected_array.size else None
        expected_warning = min_expected is not None and (
            min_expected < 1.0 or low_percent > 20.0
        )
        n_obs = int(counts.sum())
        min_dimension = min(counts.shape)
        cramers_v = None
        if n_obs > 0 and min_dimension > 1:
            cramers_v = float(np.sqrt(float(chi2) / (n_obs * (min_dimension - 1))))

        selected_method = "pearson_chi_square"
        selected_p_value: float | None = float(p_value)
        fisher_odds_ratio: float | None = None
        warnings: list[str] = []
        if expected_warning:
            warnings.append(
                "기대빈도가 낮은 셀이 있어 Pearson 카이제곱 검정 해석에 주의가 필요합니다."
            )
            if counts.shape == (2, 2):
                odds_ratio, fisher_p = stats.fisher_exact(counts)
                selected_method = "fisher_exact"
                selected_p_value = float(fisher_p)
                fisher_odds_ratio = float(odds_ratio)
                warnings.append(
                    "2x2 교차표에서는 기대빈도 조건이 약해 Fisher 정확검정을 함께 제시했다."
                )
            else:
                selected_method = "unsupported_exact"
                selected_p_value = None
                warnings.append(
                    "2x2보다 큰 교차표의 정확검정은 현재 지원하지 않습니다."
                )

        test = AssociationTestResult(
            pearson_chi_square=float(chi2),
            df=int(df),
            pearson_p_value=float(p_value),
            expected_counts=tuple(
                tuple(float(value) for value in row) for row in expected_array
            ),
            expected_cell_warning=expected_warning,
            min_expected_count=min_expected,
            low_expected_cell_count=low_count,
            low_expected_cell_percent=low_percent,
            cramers_v=cramers_v,
            selected_method=selected_method,
            selected_p_value=selected_p_value,
            fisher_odds_ratio=fisher_odds_ratio,
        )
        return test, warnings

    def _ordered_values(
        self, series: pd.Series, variable: Variable
    ) -> tuple[object, ...]:
        observed_values = list(pd.unique(series.dropna()))
        return tuple(
            sorted(
                observed_values,
                key=lambda value: self._value_sort_key(variable, value),
            )
        )

    @classmethod
    def _value_sort_key(
        cls,
        variable: Variable,
        value: object,
    ) -> tuple[int, int | str, str]:
        value_labels = variable.value_labels or {}
        label_key = cls._value_label_key(value_labels, value)
        if label_key is not None:
            label_order = {
                candidate: index for index, candidate in enumerate(value_labels)
            }
            return (0, label_order[label_key], cls._normalized(value))
        return (1, cls._normalized(value), cls._display_value(value))

    @classmethod
    def _label_for_value(cls, variable: Variable, value: object) -> str:
        value_labels = variable.value_labels or {}
        label_key = cls._value_label_key(value_labels, value)
        if label_key is None:
            return cls._display_value(value)
        return str(value_labels[label_key])

    @staticmethod
    def _value_label_key(
        value_labels: Mapping[object, str],
        value: object,
    ) -> object | None:
        try:
            if value in value_labels:
                return value
        except TypeError:
            return None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None
        if numeric_value in value_labels:
            return numeric_value
        return None

    @staticmethod
    def _display_value(value: object) -> str:
        return str(value)

    @staticmethod
    def _normalized(value: object) -> str:
        return unicodedata.normalize("NFKC", str(value)).casefold()


Step.register_type(FrequencyCrosstabStep.step_type, FrequencyCrosstabStep)
