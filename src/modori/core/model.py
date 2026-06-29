from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

import pandas as pd


class Measure(Enum):
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    SCALE = "scale"


@dataclass(frozen=True)
class DatasetShapeLimits:
    max_json_bytes: int | None = None
    max_rows: int | None = None
    max_columns: int | None = None
    max_variables: int | None = None
    max_cells: int | None = None


def _require_mapping(value: Any, message: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(message)
    return value


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...], context: str) -> None:
    for key in keys:
        if key not in payload:
            raise ValueError(f"{context} missing required key: {key}")


@dataclass(frozen=True)
class Variable:
    name: str
    label: str | None
    measure: Measure
    value_labels: dict[float, str]
    missing_values: list[float]
    dtype: str
    origin_step_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "measure": self.measure.value,
            "value_labels": [[key, value] for key, value in self.value_labels.items()],
            "missing_values": self.missing_values,
            "dtype": self.dtype,
            "origin_step_id": self.origin_step_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Variable:
        payload = _require_mapping(payload, "Variable payload must be an object")
        _require_keys(payload, ("name", "measure", "dtype"), "Variable payload")
        raw_value_labels = payload.get("value_labels", [])
        if isinstance(raw_value_labels, Mapping):
            value_label_items = raw_value_labels.items()
        elif isinstance(raw_value_labels, list):
            value_label_items = raw_value_labels
        else:
            raise ValueError("Variable value_labels must be an object or list of pairs")

        try:
            value_labels = {float(key): str(value) for key, value in value_label_items}
            missing_values = [
                float(value) for value in payload.get("missing_values", [])
            ]
            measure = Measure(str(payload["measure"]))
        except (TypeError, ValueError) as exc:
            raise ValueError("Variable payload contains invalid typed values") from exc

        return cls(
            name=str(payload["name"]),
            label=None if payload.get("label") is None else str(payload.get("label")),
            measure=measure,
            value_labels=value_labels,
            missing_values=missing_values,
            dtype=str(payload["dtype"]),
            origin_step_id=(
                None
                if payload.get("origin_step_id") is None
                else str(payload.get("origin_step_id"))
            ),
        )


@dataclass(frozen=True)
class Dataset:
    df: pd.DataFrame
    variables: dict[str, Variable]

    def __post_init__(self) -> None:
        if not self.df.columns.is_unique:
            raise ValueError("Dataframe column labels must be unique")

        dataframe_columns = set(self.df.columns)
        variable_columns = set(self.variables)
        if dataframe_columns != variable_columns:
            raise ValueError(
                "Dataset column set must match variable metadata keys: "
                f"df={sorted(dataframe_columns)}, variables={sorted(variable_columns)}"
            )

        mismatched_names = [
            key for key, variable in self.variables.items() if variable.name != key
        ]
        if mismatched_names:
            raise ValueError(
                "Variable.name must match its dataset column key: "
                f"{sorted(mismatched_names)}"
            )

    @classmethod
    def empty(cls) -> Dataset:
        return cls(df=pd.DataFrame(), variables={})

    def frame_for_compute(self, columns: list[str] | None = None) -> pd.DataFrame:
        selected_columns = list(self.df.columns) if columns is None else columns
        missing_columns = set(selected_columns) - set(self.df.columns)
        if missing_columns:
            raise KeyError(f"Unknown columns requested: {sorted(missing_columns)}")

        frame = self.df.loc[:, selected_columns].copy(deep=True)
        for column in selected_columns:
            missing_values = self.variables[column].missing_values
            if missing_values:
                frame[column] = frame[column].mask(frame[column].isin(missing_values))
        return frame

    def with_updates(
        self,
        new_columns: Mapping[str, pd.Series],
        new_variables: Mapping[str, Variable],
    ) -> Dataset:
        self._validate_new_column_indexes(new_columns)
        missing_metadata = set(new_columns) - set(new_variables)
        if missing_metadata:
            raise ValueError(
                "Every new or updated column must include Variable metadata: "
                f"{sorted(missing_metadata)}"
            )

        updated_df = self.df.copy(deep=True)
        updated_variables = dict(self.variables)
        for column, series in new_columns.items():
            updated_df[column] = series
            updated_variables[column] = new_variables[column]

        for column, variable in new_variables.items():
            if column not in updated_df.columns:
                raise ValueError(
                    f"Variable metadata supplied for missing dataframe column: {column}"
                )
            updated_variables[column] = variable

        return Dataset(df=updated_df, variables=updated_variables)

    def _validate_new_column_indexes(self, new_columns: Mapping[str, pd.Series]) -> None:
        if not new_columns:
            return
        non_series_columns = [
            column
            for column, series in new_columns.items()
            if not isinstance(series, pd.Series)
        ]
        if non_series_columns:
            raise ValueError(
                "StepResult new_columns values must be pandas Series: "
                f"{sorted(non_series_columns)}"
            )

        if len(self.df.index) == 0 and len(self.df.columns) == 0:
            first_index = next(iter(new_columns.values())).index
            mismatched_columns = [
                column
                for column, series in new_columns.items()
                if not series.index.equals(first_index)
            ]
            if mismatched_columns:
                raise ValueError(
                    "New column indexes must match each other for an empty dataset: "
                    f"{sorted(mismatched_columns)}"
                )
            return

        mismatched_columns = [
            column
            for column, series in new_columns.items()
            if not series.index.equals(self.df.index)
        ]
        if mismatched_columns:
            raise ValueError(
                "New column index must match the current dataset index: "
                f"{sorted(mismatched_columns)}"
            )

    def to_dict(self) -> dict[str, Any]:
        json_safe_frame = self.df.astype(object).where(pd.notna(self.df), None)
        split_frame = json_safe_frame.to_dict(orient="split")
        return {
            "df": {
                "columns": split_frame["columns"],
                "index": split_frame["index"],
                "data": split_frame["data"],
            },
            "variables": {
                name: variable.to_dict() for name, variable in self.variables.items()
            },
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        limits: DatasetShapeLimits | None = None,
    ) -> Dataset:
        payload = _require_mapping(payload, "Dataset payload must be an object")
        _require_keys(payload, ("df", "variables"), "Dataset payload")
        frame_payload = payload["df"]
        frame_payload = _require_mapping(
            frame_payload,
            "Dataset df payload must be an object",
        )
        _require_keys(frame_payload, ("columns", "index", "data"), "Dataset df payload")
        variables_payload = _require_mapping(
            payload["variables"],
            "Dataset variables must be an object",
        )
        if limits is not None:
            _validate_dataset_payload_shape(frame_payload, variables_payload, limits)
        try:
            frame = pd.DataFrame(
                data=frame_payload["data"],
                columns=frame_payload["columns"],
                index=frame_payload["index"],
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Dataset df payload is invalid") from exc
        variables = {}
        for name, variable_payload in variables_payload.items():
            if not isinstance(variable_payload, Mapping):
                raise ValueError(f"Variable payload for {name} must be an object")
            variables[str(name)] = Variable.from_dict(variable_payload)
        return cls(df=frame, variables=variables)


def _validate_dataset_payload_shape(
    frame_payload: Mapping[str, Any],
    variables_payload: Mapping[str, Any],
    limits: DatasetShapeLimits,
) -> None:
    columns = frame_payload["columns"]
    data = frame_payload["data"]
    variable_count = len(variables_payload)
    if limits.max_variables is not None and variable_count > limits.max_variables:
        raise ValueError(
            f"Dataset variable count {variable_count} exceeds the configured "
            f"variable limit of {limits.max_variables}."
        )
    if not isinstance(columns, list) or not isinstance(data, list):
        return
    row_count = len(data)
    column_count = len(columns)
    if limits.max_rows is not None and row_count > limits.max_rows:
        raise ValueError(
            f"Dataset row count {row_count} exceeds the configured row limit "
            f"of {limits.max_rows}."
        )
    if limits.max_columns is not None and column_count > limits.max_columns:
        raise ValueError(
            f"Dataset column count {column_count} exceeds the configured column limit "
            f"of {limits.max_columns}."
        )
    if limits.max_cells is not None:
        cell_count = row_count * column_count
        if cell_count > limits.max_cells:
            raise ValueError(
                f"Dataset contains {cell_count} cells, exceeding the cell limit "
                f"of {limits.max_cells}."
            )


@dataclass(frozen=True)
class StepResult:
    new_columns: dict[str, pd.Series] = field(default_factory=dict)
    new_variables: dict[str, Variable] = field(default_factory=dict)
    analysis: Any | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PipelineContext:
    dataset: Dataset
    analyses: Mapping[str, Any]


@dataclass
class Step(ABC):
    id: str
    title: str
    params: dict[str, Any]
    input_step_ids: list[str] = field(default_factory=list)

    step_type: ClassVar[str]
    writes_are_static: ClassVar[bool] = True
    produces_analysis: ClassVar[bool] = False
    safe_for_untrusted_project_json: ClassVar[bool] = True
    _registry: ClassVar[dict[str, type[Step]]] = {}

    @abstractmethod
    def compute(self, ctx: PipelineContext) -> StepResult:
        raise NotImplementedError

    @abstractmethod
    def reads(self) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    def writes(self) -> set[str]:
        raise NotImplementedError

    def metadata_writes(self) -> set[str]:
        return set()

    def compute_context_free(self, dataset: Dataset) -> StepResult:
        return self.compute(PipelineContext(dataset=dataset, analyses={}))

    def provenance(self) -> str:
        return self.title

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.step_type,
            "id": self.id,
            "title": self.title,
            "params": self.params,
            "input_step_ids": self.input_step_ids,
        }

    @classmethod
    def register_type(cls, type_name: str, step_cls: type[Step]) -> None:
        cls._registry[type_name] = step_cls

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Step:
        payload = _require_mapping(payload, "Step payload must be an object")
        _require_keys(payload, ("type", "id", "title"), "Step payload")
        step_type = str(payload["type"])
        try:
            step_cls = cls._registry[step_type]
        except KeyError as exc:
            raise ValueError(f"Unknown Step type: {step_type}") from exc
        params = payload.get("params", {})
        if not isinstance(params, Mapping):
            raise ValueError("Step params must be an object")
        input_step_ids = payload.get("input_step_ids", [])
        if (
            not isinstance(input_step_ids, list)
            or not all(isinstance(step_id, str) for step_id in input_step_ids)
        ):
            raise ValueError("Step input_step_ids must be a list of strings")

        return step_cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            params=dict(params),
            input_step_ids=list(input_step_ids),
        )
