from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

import pandas as pd

from modori.core import Dataset, Measure, PipelineContext, Step, StepResult, Variable
from modori.descriptives_table1_results import (
    DescriptiveCategoryRow,
    DescriptiveGroupSummary,
    DescriptiveVariableSummary,
    DescriptivesTableResult,
)
from modori.steps.input_validation import (
    raise_for_step_input_issues,
    validate_step_input,
)


@dataclass
class DescriptivesTableStep(Step):
    step_type = "stats.descriptives_table1"
    produces_analysis = True
    CURRENT_SCHEMA_VERSION = 1
    CONTRACT_PARAM_EXAMPLES = {
        "current": {
            "schema_version": 1,
            "variables": ["age"],
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
        },
        "newer": {"schema_version": 999, "variables": ["age"]},
        "unknown_current": {
            "schema_version": 1,
            "variables": ["age"],
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
            "extra": "bad",
        },
    }

    @classmethod
    def migrate_params(cls, params: dict[str, object]) -> dict[str, object]:
        version = params.get("schema_version")
        if version is None:
            raise ValueError("descriptives_table1 params require schema_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("schema_version must be an integer")
        if version > cls.CURRENT_SCHEMA_VERSION:
            raise ValueError("descriptives_table1 params use a newer schema_version")
        if version == 1:
            return params
        raise ValueError(f"unsupported descriptives_table1 schema_version: {version}")

    @classmethod
    def validate_params(cls, params: dict[str, object]) -> dict[str, object]:
        allowed = {
            "schema_version",
            "variables",
            "group",
            "include_missing_counts",
            "language",
        }
        unknown = set(params) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unknown descriptives_table1 params: {names}")
        if params.get("schema_version") != cls.CURRENT_SCHEMA_VERSION:
            raise ValueError(
                "descriptives_table1 params were not migrated to the current schema"
            )
        variables = params.get("variables")
        if (
            not isinstance(variables, list)
            or not variables
            or not all(isinstance(variable, str) for variable in variables)
        ):
            raise ValueError("variables must be a non-empty list of variable keys")
        group = params.get("group")
        if group is not None and not isinstance(group, str):
            raise ValueError("group must be null or a variable key")
        include_missing_counts = params.get("include_missing_counts", True)
        if not isinstance(include_missing_counts, bool):
            raise ValueError("include_missing_counts must be boolean")
        language = params.get("language", "ko")
        if language not in {"ko", "en"}:
            raise ValueError("language must be ko or en")
        return {
            "schema_version": cls.CURRENT_SCHEMA_VERSION,
            "variables": list(variables),
            "group": group,
            "include_missing_counts": include_missing_counts,
            "language": language,
        }

    def compute(self, ctx: PipelineContext) -> StepResult:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        result = self._compute_result(ctx, params)
        return StepResult(analysis=result)

    def reads(self) -> set[str]:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        keys = set(params["variables"])
        if params["group"] is not None:
            keys.add(str(params["group"]))
        return keys

    def writes(self) -> set[str]:
        return {self.id}

    def provenance(self) -> str:
        params = self.validate_params(self.migrate_params(dict(self.params)))
        variables = ", ".join(str(key) for key in params["variables"])
        return f"descriptives table for {variables}"

    def _compute_result(
        self,
        ctx: PipelineContext,
        params: dict[str, object],
    ) -> DescriptivesTableResult:
        dataset = ctx.dataset
        self._validate_dataset(dataset, params)
        variables = [str(variable) for variable in params["variables"]]
        group = None if params["group"] is None else str(params["group"])
        columns = list(dict.fromkeys([*variables, *([group] if group else [])]))
        frame = dataset.frame_for_compute(columns)
        summaries = tuple(
            self._summary_for_variable(dataset, frame, variable)
            for variable in variables
        )
        grouped_summaries = (
            self._grouped_summaries(dataset, frame, variables, group)
            if group is not None
            else ()
        )
        return DescriptivesTableResult(
            analysis_key="descriptives_table1",
            title_ko="기술통계 표 1",
            variables=tuple(variables),
            group=group,
            n_total=int(len(frame)),
            summaries=summaries,
            grouped_summaries=grouped_summaries,
            warnings_ko=(),
            notes_ko=(),
            apa_template_id=None,
            chart_spec=None,
        )

    @staticmethod
    def _validate_dataset(dataset: Dataset, params: dict[str, object]) -> None:
        issues = validate_step_input(
            dataset,
            DescriptivesTableStep.step_type,
            params,
        )
        raise_for_step_input_issues(DescriptivesTableStep.step_type, issues)

    def _grouped_summaries(
        self,
        dataset: Dataset,
        frame: pd.DataFrame,
        variables: list[str],
        group: str,
    ) -> tuple[DescriptiveGroupSummary, ...]:
        group_variable = dataset.variables[group]
        group_values = self._ordered_values(frame[group], group_variable)
        summaries: list[DescriptiveGroupSummary] = []
        for group_value in group_values:
            group_frame = frame.loc[frame[group] == group_value]
            summaries.append(
                DescriptiveGroupSummary(
                    group_value=self._display_value(group_value),
                    group_label=self._label_for_value(group_variable, group_value),
                    n_total=int(len(group_frame)),
                    variables=tuple(
                        self._summary_for_variable(dataset, group_frame, variable)
                        for variable in variables
                    ),
                )
            )
        return tuple(summaries)

    def _summary_for_variable(
        self,
        dataset: Dataset,
        frame: pd.DataFrame,
        key: str,
    ) -> DescriptiveVariableSummary:
        variable = dataset.variables[key]
        series = frame[key]
        n_obs = int(series.notna().sum())
        n_missing = int(len(series) - n_obs)
        label = variable.label or key
        if variable.measure is Measure.SCALE:
            return self._scale_summary(key, label, series, n_obs, n_missing)
        return self._categorical_summary(
            key,
            label,
            variable,
            series,
            n_obs,
            n_missing,
        )

    @staticmethod
    def _scale_summary(
        key: str,
        label: str,
        series: pd.Series,
        n_obs: int,
        n_missing: int,
    ) -> DescriptiveVariableSummary:
        non_missing = series.dropna()
        values = pd.to_numeric(non_missing, errors="raise").astype(float)
        decimal_values = _decimal_values(non_missing, key)
        if n_obs == 0:
            mean = median = minimum = maximum = None
        else:
            mean = _decimal_mean(decimal_values)
            median = float(values.median())
            minimum = float(values.min())
            maximum = float(values.max())
        sd = None if n_obs < 2 else _decimal_sample_sd(decimal_values)
        return DescriptiveVariableSummary(
            key=key,
            label=label,
            measure=Measure.SCALE.value,
            n_obs=n_obs,
            n_missing=n_missing,
            mean=mean,
            sd=sd,
            median=median,
            minimum=minimum,
            maximum=maximum,
            categories=(),
        )

    def _categorical_summary(
        self,
        key: str,
        label: str,
        variable: Variable,
        series: pd.Series,
        n_obs: int,
        n_missing: int,
    ) -> DescriptiveVariableSummary:
        non_missing = series.dropna()
        categories = []
        for value in self._ordered_values(non_missing, variable):
            count = int((non_missing == value).sum())
            percent = 0.0 if n_obs == 0 else (count / n_obs) * 100.0
            categories.append(
                DescriptiveCategoryRow(
                    value=self._display_value(value),
                    label=self._label_for_value(variable, value),
                    count=count,
                    percent=float(percent),
                )
            )
        return DescriptiveVariableSummary(
            key=key,
            label=label,
            measure=variable.measure.value,
            n_obs=n_obs,
            n_missing=n_missing,
            categories=tuple(categories),
        )

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


def _decimal_values(values: pd.Series, key: str) -> list[Decimal]:
    decimals: list[Decimal] = []
    for value in values:
        try:
            decimals.append(Decimal(str(value).strip()))
        except InvalidOperation as exc:
            raise ValueError(f"척도형 변수는 숫자여야 합니다: {key}") from exc
    return decimals


def _decimal_mean(decimals: list[Decimal]) -> float:
    with localcontext() as context:
        context.prec = 50
        return float(sum(decimals) / Decimal(len(decimals)))


def _decimal_sample_sd(decimals: list[Decimal]) -> float:
    with localcontext() as context:
        context.prec = 50
        mean = sum(decimals) / Decimal(len(decimals))
        sum_squares = sum((value - mean) ** 2 for value in decimals)
        variance = sum_squares / Decimal(len(decimals) - 1)
        return float(variance.sqrt())


Step.register_type(DescriptivesTableStep.step_type, DescriptivesTableStep)
