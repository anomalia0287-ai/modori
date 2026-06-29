from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from modori.steps.data_prep import metadata_variables
from modori.table_io import TablePreviewResult
from modori.ui.models import DataTableModel, VariableTableModel, variable_records_from_dataset
from modori.ui.table_provider import DatasetTableProvider


@dataclass(frozen=True)
class VisibleDatasetModels:
    data_model: DataTableModel
    variable_model: VariableTableModel
    notice: str


def models_for_dataset(dataset: object) -> VisibleDatasetModels:
    data_model = DataTableModel(DatasetTableProvider(dataset))
    variable_model = VariableTableModel(variable_records_from_dataset(dataset))
    rows, columns = _dataset_shape(dataset, data_model)
    return VisibleDatasetModels(
        data_model=data_model,
        variable_model=variable_model,
        notice=f"가져온 데이터: {rows}행 · {columns}열",
    )


def models_for_table_preview(preview: TablePreviewResult) -> VisibleDatasetModels:
    frame = preview.frame.rename(columns={column: str(column) for column in preview.frame.columns})
    variables = metadata_variables(frame, origin_step_id="preview", metadata=preview.metadata)
    preview_dataset = SimpleNamespace(df=frame, variables=variables)
    return VisibleDatasetModels(
        data_model=DataTableModel(DatasetTableProvider(preview_dataset)),
        variable_model=VariableTableModel(variable_records_from_dataset(preview_dataset)),
        notice=(
            f"가져온 데이터 미리보기: {preview.previewed_rows}행 · "
            f"{len(preview.columns)}열"
        ),
    )


def _dataset_shape(dataset: object, data_model: DataTableModel) -> tuple[int, int]:
    frame: Any | None = getattr(dataset, "df", None)
    if frame is None:
        return data_model.rowCount(), data_model.columnCount()
    return len(frame.index), len(frame.columns)
