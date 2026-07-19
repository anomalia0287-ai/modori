from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from modori.steps.data_prep import metadata_variables
from modori.table_io import TablePreviewResult
from modori.ui.models import DataTableModel, VariableTableModel, variable_records_from_dataset
from modori.ui.localization import localize_message
from modori.ui.table_provider import DatasetTableProvider


@dataclass(frozen=True)
class VisibleDatasetModels:
    data_model: DataTableModel
    variable_model: VariableTableModel
    notice: str


def models_for_dataset(dataset: object, *, language: str = "ko") -> VisibleDatasetModels:
    selected_language = "en" if language == "en" else "ko"
    data_model = DataTableModel(DatasetTableProvider(dataset))
    variable_model = VariableTableModel(
        variable_records_from_dataset(dataset),
        language=selected_language,
    )
    rows, columns = _dataset_shape(dataset, data_model)
    notice = (
        f"Imported data: {rows} rows · {columns} columns"
        if selected_language == "en"
        else f"가져온 데이터: {rows}행 · {columns}열"
    )
    return VisibleDatasetModels(
        data_model=data_model,
        variable_model=variable_model,
        notice=notice,
    )


def models_for_table_preview(
    preview: TablePreviewResult,
    *,
    language: str = "ko",
) -> VisibleDatasetModels:
    selected_language = "en" if language == "en" else "ko"
    frame = preview.frame.rename(columns={column: str(column) for column in preview.frame.columns})
    variables = metadata_variables(frame, origin_step_id="preview", metadata=preview.metadata)
    preview_dataset = SimpleNamespace(df=frame, variables=variables)
    notice = (
        f"Imported data preview: {preview.previewed_rows} rows · {len(preview.columns)} columns"
        if selected_language == "en"
        else f"가져온 데이터 미리보기: {preview.previewed_rows}행 · {len(preview.columns)}열"
    )
    if preview.warnings:
        warning = localize_message(preview.warnings[0], selected_language)
        label = "Check" if selected_language == "en" else "확인"
        notice = f"{notice} · {label}: {warning}"
    return VisibleDatasetModels(
        data_model=DataTableModel(DatasetTableProvider(preview_dataset)),
        variable_model=VariableTableModel(
            variable_records_from_dataset(preview_dataset),
            language=selected_language,
        ),
        notice=notice,
    )


def _dataset_shape(dataset: object, data_model: DataTableModel) -> tuple[int, int]:
    frame: Any | None = getattr(dataset, "df", None)
    if frame is None:
        return data_model.rowCount(), data_model.columnCount()
    return len(frame.index), len(frame.columns)
