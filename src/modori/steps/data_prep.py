from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from modori.core import Measure, PipelineContext, Step, StepResult, Variable
from modori.table_io import (
    ImportSelection,
    TableLayoutOverride,
    import_selection_from_params,
    read_full,
    read_header,
)
from modori.value_inventory import value_recode_ineligibility_reason


def _dtype_name(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "int"
    if pd.api.types.is_numeric_dtype(series):
        return "float"
    return "string"


def _infer_measure(series: pd.Series) -> Measure:
    non_missing = series.dropna()
    if pd.api.types.is_numeric_dtype(non_missing):
        unique_values = non_missing.unique()
        all_integer_like = all(float(value).is_integer() for value in unique_values)
        if len(unique_values) <= 10 and all_integer_like:
            return Measure.ORDINAL
        return Measure.SCALE
    return Measure.NOMINAL


def read_table(
    path: Path,
    file_type: str,
    *,
    layout: TableLayoutOverride | None = None,
    selection: ImportSelection | None = None,
    drop_aggregate_rows: bool = False,
    drop_duplicate_rows: bool = False,
) -> tuple[pd.DataFrame, Any | None]:
    return read_full(
        path,
        file_type,
        layout=layout,
        selection=selection,
        drop_aggregate_rows=drop_aggregate_rows,
        drop_duplicate_rows=drop_duplicate_rows,
    )


def read_columns(
    path: Path,
    file_type: str,
    *,
    layout: TableLayoutOverride | None = None,
    selection: ImportSelection | None = None,
) -> list[str]:
    return read_header(path, file_type, layout=layout, selection=selection)


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


@dataclass(frozen=True)
class ImportReadParams:
    path: Path
    file_type: str
    layout: TableLayoutOverride | None
    selection: ImportSelection | None
    drop_aggregate_rows: bool
    drop_duplicate_rows: bool


def import_read_params_from_step_params(params: dict[str, Any]) -> ImportReadParams:
    path = Path(params["path"])
    return ImportReadParams(
        path=path,
        file_type=_file_type_from_params(path, params),
        layout=_layout_override_from_params(params),
        selection=import_selection_from_params(params.get("import_selection")),
        drop_aggregate_rows=bool(params.get("drop_aggregate_rows", False)),
        drop_duplicate_rows=bool(params.get("drop_duplicate_rows", False)),
    )


def metadata_variables(
    frame: pd.DataFrame,
    *,
    origin_step_id: str,
    metadata: Any | None,
) -> dict[str, Variable]:
    variables: dict[str, Variable] = {}
    column_labels = getattr(metadata, "column_labels", None) or []
    value_labels_by_column = getattr(metadata, "variable_value_labels", None) or {}
    missing_ranges = getattr(metadata, "missing_ranges", None) or {}
    variable_measure = getattr(metadata, "variable_measure", None) or {}

    for index, column in enumerate(frame.columns):
        label = column_labels[index] if index < len(column_labels) else str(column)
        raw_value_labels = value_labels_by_column.get(column, {})
        value_labels = {float(key): str(value) for key, value in raw_value_labels.items()}
        raw_missing = missing_ranges.get(column, []) if isinstance(missing_ranges, dict) else []
        missing_values: list[float] = []
        for item in raw_missing:
            if isinstance(item, dict):
                if item.get("lo") != item.get("hi"):
                    raise ValueError(
                        "SPSS missing value ranges are not supported yet; "
                        f"column {column} declares {item!r}."
                    )
                missing_values.append(float(item["lo"]))
            else:
                missing_values.append(float(item))
        measure = _infer_measure(frame[column])
        if isinstance(variable_measure, dict) and column in variable_measure:
            metadata_measure = str(variable_measure[column]).lower()
            valid_measure_values = {item.value for item in Measure}
            if metadata_measure in valid_measure_values:
                measure = Measure(metadata_measure)
        variables[str(column)] = Variable(
            name=str(column),
            label=label,
            measure=measure,
            value_labels=value_labels,
            missing_values=missing_values,
            dtype=_dtype_name(frame[column]),
            origin_step_id=origin_step_id,
        )
    return variables


@dataclass
class ImportStep(Step):
    step_type = "import.table"
    writes_are_static = False
    safe_for_untrusted_project_json = False

    def compute(self, ctx: PipelineContext) -> StepResult:
        read_params = import_read_params_from_step_params(self.params)
        read_kwargs: dict[str, Any] = {}
        if read_params.layout is not None:
            read_kwargs["layout"] = read_params.layout
        if read_params.selection is not None:
            read_kwargs["selection"] = read_params.selection
        if read_params.drop_aggregate_rows:
            read_kwargs["drop_aggregate_rows"] = True
        if read_params.drop_duplicate_rows:
            read_kwargs["drop_duplicate_rows"] = True
        table = read_table(
            read_params.path,
            read_params.file_type,
            **read_kwargs,
        )
        frame, metadata = table
        frame = frame.rename(columns={column: str(column) for column in frame.columns})
        variables = metadata_variables(
            frame,
            origin_step_id=self.id,
            metadata=metadata,
        )
        missing_cells = int(frame.isna().sum().sum())
        notes = [
            f"Imported {len(frame)} rows, {len(frame.columns)} columns, "
            f"and {missing_cells} missing cells."
        ]
        notes.extend(getattr(table, "warnings", ()))
        return StepResult(
            new_columns={column: frame[column] for column in frame.columns},
            new_variables=variables,
            analysis=None,
            notes=notes,
        )

    def reads(self) -> set[str]:
        return set()

    def writes(self) -> set[str]:
        read_params = import_read_params_from_step_params(self.params)
        read_kwargs: dict[str, Any] = {}
        if read_params.layout is not None:
            read_kwargs["layout"] = read_params.layout
        if read_params.selection is not None:
            read_kwargs["selection"] = read_params.selection
        columns = read_columns(read_params.path, read_params.file_type, **read_kwargs)
        return set(columns)

    def provenance(self) -> str:
        return f"imported {self.params['path']}"


@dataclass
class RecodeReverseStep(Step):
    step_type = "data.recode_reverse"

    def compute(self, ctx: PipelineContext) -> StepResult:
        columns = list(self.params["columns"])
        if len(set(columns)) != len(columns):
            raise ValueError("RecodeReverseStep columns must be unique")
        scale_min = float(self.params["scale_min"])
        scale_max = float(self.params["scale_max"])
        if scale_min >= scale_max:
            raise ValueError("scale_min must be less than scale_max")
        new_columns: dict[str, pd.Series] = {}
        new_variables: dict[str, Variable] = {}

        for column in columns:
            output = f"{column}{self._suffix()}"
            source = ctx.dataset.frame_for_compute([column])[column]
            new_columns[output] = (scale_min + scale_max) - source
            source_variable = ctx.dataset.variables[column]
            new_variables[output] = Variable(
                name=output,
                label=f"{source_variable.label or column} (reverse-coded)",
                measure=source_variable.measure,
                value_labels={
                    (scale_min + scale_max) - key: value
                    for key, value in source_variable.value_labels.items()
                },
                missing_values=[],
                dtype=source_variable.dtype,
                origin_step_id=self.id,
            )

        return StepResult(
            new_columns=new_columns,
            new_variables=new_variables,
            analysis=None,
            notes=[
                f"Reverse-coded {', '.join(columns)} "
                f"on a {scale_min:g}-{scale_max:g} scale."
            ],
        )

    def reads(self) -> set[str]:
        return set(self.params["columns"])

    def writes(self) -> set[str]:
        return {f"{column}{self._suffix()}" for column in self.params["columns"]}

    def provenance(self) -> str:
        return (
            f"reverse-coded {', '.join(self.params['columns'])} "
            f"on a {self.params['scale_min']}-{self.params['scale_max']} scale"
        )

    def _suffix(self) -> str:
        return str(self.params.get("suffix", "_R"))


@dataclass
class VariableMetadataPatchStep(Step):
    step_type = "data.variable_metadata_patch"

    def compute(self, ctx: PipelineContext) -> StepResult:
        variable_key = str(self.params["variable_key"])
        try:
            variable = ctx.dataset.variables[variable_key]
        except KeyError as exc:
            raise KeyError(f"Unknown variable for metadata patch: {variable_key}") from exc

        updates: dict[str, Any] = {}
        if "label" in self.params:
            raw_label = self.params["label"]
            updates["label"] = None if raw_label is None else str(raw_label)
        if "measure" in self.params:
            updates["measure"] = Measure(str(self.params["measure"]))
        if "value_labels" in self.params:
            updates["value_labels"] = self._coerce_value_labels(
                self.params["value_labels"]
            )
        if "missing_values" in self.params:
            updates["missing_values"] = [
                float(value) for value in self.params["missing_values"]
            ]

        updated = replace(
            variable,
            name=variable_key,
            origin_step_id=variable.origin_step_id,
            **updates,
        )
        return StepResult(
            new_variables={variable_key: updated},
            notes=[f"Updated metadata for {variable_key}."],
        )

    @staticmethod
    def _coerce_value_labels(value: Any) -> dict[float, str]:
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return {float(key): str(label) for key, label in value.items()}
        if isinstance(value, list):
            return {float(key): str(label) for key, label in value}
        raise ValueError("value_labels must be a mapping or a list of pairs")

    def reads(self) -> set[str]:
        return {str(self.params["variable_key"])}

    def writes(self) -> set[str]:
        return set()

    def metadata_writes(self) -> set[str]:
        return {str(self.params["variable_key"])}

    def provenance(self) -> str:
        return f"updated metadata for {self.params['variable_key']}"


@dataclass
class ComposeScaleStep(Step):
    step_type = "data.compose_scale"

    def compute(self, ctx: PipelineContext) -> StepResult:
        items = list(self.params["items"])
        if not items:
            raise ValueError("ComposeScaleStep requires at least one item")
        if len(set(items)) != len(items):
            raise ValueError("ComposeScaleStep items must be unique")
        method = str(self.params.get("method", "mean"))
        output = str(self.params["name"])
        policy = dict(self.params.get("missing_policy", {"preset": "survey"}))
        preset = str(policy.get("preset", "survey"))
        min_valid = self._min_valid_ratio(preset, policy)

        frame = ctx.dataset.frame_for_compute(items)
        valid_counts = frame.notna().sum(axis=1)
        required_count = len(items) * min_valid
        enough_values = valid_counts >= required_count

        if method == "mean":
            values = frame.mean(axis=1, skipna=True)
        elif method == "sum":
            values = frame.sum(axis=1, skipna=True)
        else:
            raise ValueError(f"Unsupported compose method: {method}")

        values = values.where(enough_values)
        dropped = int((~enough_values).sum())
        variable = Variable(
            name=output,
            label=output,
            measure=Measure.SCALE,
            value_labels={},
            missing_values=[],
            dtype="float",
            origin_step_id=self.id,
        )
        return StepResult(
            new_columns={output: values},
            new_variables={output: variable},
            analysis=None,
            notes=[
                f"Applied {preset} missing policy with min_valid={min_valid:g}.",
                f"Composed {len(items)} items into {output} using {method}.",
                f"Dropped {dropped} cases for missingness.",
            ],
        )

    @staticmethod
    def _min_valid_ratio(preset: str, policy: dict[str, Any]) -> float:
        if preset == "survey":
            min_valid = float(policy.get("min_valid", 0.8))
            ComposeScaleStep._validate_min_valid(min_valid)
            return min_valid
        if preset == "custom":
            if "min_valid" not in policy:
                raise ValueError("custom missing_policy requires min_valid")
            min_valid = float(policy["min_valid"])
            ComposeScaleStep._validate_min_valid(min_valid)
            return min_valid
        if preset == "conservative":
            return 1.0
        raise ValueError(f"Unsupported missing_policy preset: {preset}")

    @staticmethod
    def _validate_min_valid(min_valid: float) -> None:
        if not 0 < min_valid <= 1:
            raise ValueError("min_valid must be greater than 0 and at most 1")

    def reads(self) -> set[str]:
        return set(self.params["items"])

    def writes(self) -> set[str]:
        return {str(self.params["name"])}

    def provenance(self) -> str:
        return f"composed {self.params['name']} from {len(self.params['items'])} items"


@dataclass
class UnifyValuesStep(Step):
    step_type = "recode.unify_values"

    def compute(self, ctx: PipelineContext) -> StepResult:
        column = str(self.params["column"])
        mapping = {str(key): str(value) for key, value in dict(self.params["mapping"]).items()}
        if not mapping:
            raise ValueError("UnifyValuesStep mapping must not be empty")
        output = f"{column}{self._suffix()}"
        source = ctx.dataset.frame_for_compute([column])[column]
        unified = source.map(lambda value: mapping.get(value, value) if isinstance(value, str) else value)
        replaced = int((source != unified).sum())
        source_variable = ctx.dataset.variables[column]
        new_variables = {
            output: Variable(
                name=output,
                label=f"{source_variable.label or column} (unified)",
                measure=source_variable.measure,
                value_labels={},
                missing_values=[],
                dtype=source_variable.dtype,
                origin_step_id=self.id,
            )
        }
        return StepResult(
            new_columns={output: unified},
            new_variables=new_variables,
            analysis=None,
            notes=[
                f"Unified {replaced} values in {column} "
                f"into {len(set(mapping.values()))} canonical labels."
            ],
        )

    def reads(self) -> set[str]:
        return {str(self.params["column"])}

    def writes(self) -> set[str]:
        return {f"{self.params['column']}{self._suffix()}"}

    def provenance(self) -> str:
        return (
            f"unified {len(self.params['mapping'])} value variants "
            f"in {self.params['column']}"
        )

    def _suffix(self) -> str:
        return str(self.params.get("suffix", "_정리"))


@dataclass
class MapValuesStep(Step):
    step_type = "recode.map_values"

    def compute(self, ctx: PipelineContext) -> StepResult:
        column = str(self.params.get("column", "")).strip()
        suffix = str(self.params.get("suffix", "_수정")).strip()
        raw_mapping = self.params.get("mapping", {})
        raw_to_missing = self.params.get("to_missing", [])
        if (
            not column
            or not suffix
            or not isinstance(raw_mapping, Mapping)
            or not isinstance(raw_to_missing, list)
        ):
            raise ValueError("값 수정 설정을 확인해 주세요.")

        mapping = {str(key): str(value) for key, value in raw_mapping.items()}
        to_missing = {str(value) for value in raw_to_missing}
        if not mapping and not to_missing:
            raise ValueError("값 수정 설정을 확인해 주세요.")
        if any(not key.strip() or not value.strip() for key, value in mapping.items()):
            raise ValueError("값 수정 설정을 확인해 주세요.")
        if any(not value.strip() for value in to_missing):
            raise ValueError("값 수정 설정을 확인해 주세요.")
        if set(mapping).intersection(to_missing):
            raise ValueError("값 수정 설정을 확인해 주세요.")

        reason = value_recode_ineligibility_reason(ctx.dataset, column)
        if reason is not None:
            raise ValueError(reason)

        output = f"{column}{suffix}"
        source = ctx.dataset.df[column]

        def recode(value: object) -> object:
            if pd.isna(value):
                return value
            text = str(value)
            if text in to_missing:
                return pd.NA
            return mapping.get(text, value)

        recoded = source.map(recode)
        replaced_count = int(source.map(lambda value: str(value) in mapping if pd.notna(value) else False).sum())
        missing_count = int(source.map(lambda value: str(value) in to_missing if pd.notna(value) else False).sum())
        source_variable = ctx.dataset.variables[column]
        new_variables = {
            output: Variable(
                name=output,
                label=f"{source_variable.label or column} (recoded)",
                measure=source_variable.measure,
                value_labels={},
                missing_values=[],
                dtype=_dtype_name(recoded),
                origin_step_id=self.id,
            )
        }
        return StepResult(
            new_columns={output: recoded},
            new_variables=new_variables,
            notes=[
                f"Recoded {replaced_count} values in {column} "
                f"({len(mapping)} rules); {missing_count} value set to missing."
            ],
        )

    def reads(self) -> set[str]:
        return {str(self.params["column"])}

    def writes(self) -> set[str]:
        return {f"{self.params['column']}{self._suffix()}"}

    def provenance(self) -> str:
        return f"mapped {len(self.params.get('mapping', {}))} values in {self.params['column']}"

    def _suffix(self) -> str:
        return str(self.params.get("suffix", "_수정"))


Step.register_type(ImportStep.step_type, ImportStep)
Step.register_type(UnifyValuesStep.step_type, UnifyValuesStep)
Step.register_type(MapValuesStep.step_type, MapValuesStep)
Step.register_type(RecodeReverseStep.step_type, RecodeReverseStep)
Step.register_type(VariableMetadataPatchStep.step_type, VariableMetadataPatchStep)
Step.register_type(ComposeScaleStep.step_type, ComposeScaleStep)
