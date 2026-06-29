from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PreviewReadLimits:
    max_rows: int = 30


@dataclass(frozen=True)
class FullReadLimits:
    max_file_bytes: int | None = None
    max_rows: int | None = None
    max_columns: int | None = None
    max_cells: int | None = None


DEFAULT_PREVIEW_READ_LIMITS = PreviewReadLimits()
DEFAULT_FULL_READ_LIMITS = FullReadLimits()


def normalize_file_type(path: Path, file_type: str | None = None) -> str:
    value = file_type if file_type else path.suffix
    normalized = str(value).lower().lstrip(".")
    if normalized not in {"csv", "xlsx", "xls", "sav"}:
        raise ValueError(f"Unsupported table file type: {value}")
    return normalized


def read_full(
    path: Path,
    file_type: str | None = None,
    *,
    limits: FullReadLimits = DEFAULT_FULL_READ_LIMITS,
) -> tuple[pd.DataFrame, Any | None]:
    normalized = normalize_file_type(path, file_type)
    _enforce_file_size(path, limits.max_file_bytes)
    if normalized == "csv":
        read_kwargs = {}
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_csv(path, **read_kwargs)
        metadata = None
    elif normalized == "xlsx":
        if _xlsx_needs_limited_read(limits):
            frame = _read_xlsx_limited(path, limits)
        else:
            frame = pd.read_excel(path)
        metadata = None
    elif normalized == "xls":
        read_kwargs = {}
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_excel(path, **read_kwargs)
        metadata = None
    elif normalized == "sav":
        import pyreadstat

        read_kwargs = {"user_missing": True}
        if limits.max_rows is not None:
            read_kwargs["row_limit"] = limits.max_rows + 1
        frame, metadata = pyreadstat.read_sav(path, **read_kwargs)
    else:
        raise ValueError(f"Unsupported table file type: {normalized}")
    _enforce_shape_limits(frame, limits)
    return frame, metadata


def read_header(path: Path, file_type: str | None = None) -> list[str]:
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        columns = pd.read_csv(path, nrows=0).columns
    elif normalized in {"xlsx", "xls"}:
        columns = pd.read_excel(path, nrows=0).columns
    elif normalized == "sav":
        import pyreadstat

        frame, metadata = pyreadstat.read_sav(
            path,
            metadataonly=True,
            user_missing=True,
        )
        columns = getattr(metadata, "column_names", None) or frame.columns
    else:
        raise ValueError(f"Unsupported table file type: {normalized}")
    return [str(column) for column in columns]


def read_preview(
    path: Path,
    file_type: str | None = None,
    *,
    limits: PreviewReadLimits = DEFAULT_PREVIEW_READ_LIMITS,
) -> tuple[pd.DataFrame, Any | None]:
    if limits.max_rows < 1:
        raise ValueError("Preview max_rows must be at least 1")
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        return pd.read_csv(path, nrows=limits.max_rows), None
    if normalized == "xlsx":
        return _read_xlsx_preview(path, limits.max_rows), None
    if normalized == "xls":
        return pd.read_excel(path, nrows=limits.max_rows), None
    if normalized == "sav":
        import pyreadstat

        frame, metadata = pyreadstat.read_sav(
            path,
            row_limit=limits.max_rows,
            user_missing=True,
        )
        return frame, metadata
    raise ValueError(f"Unsupported table file type: {normalized}")


def _read_xlsx_preview(path: Path, max_rows: int) -> pd.DataFrame:
    return _read_xlsx_rows(path, max_rows)


def _read_xlsx_limited(path: Path, limits: FullReadLimits) -> pd.DataFrame:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        iterator = worksheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return pd.DataFrame()
        columns = _xlsx_columns(header)
        row_limit = _xlsx_limited_row_read_count(limits, len(columns))
        rows = []
        for row in iterator:
            rows.append(list(row))
            if row_limit is not None and len(rows) >= row_limit:
                break
        return pd.DataFrame(rows, columns=columns)
    finally:
        workbook.close()


def _read_xlsx_rows(path: Path, max_rows: int) -> pd.DataFrame:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        iterator = worksheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return pd.DataFrame()
        columns = _xlsx_columns(header)
        rows = []
        for _, row in zip(range(max_rows), iterator, strict=False):
            rows.append(list(row))
        return pd.DataFrame(rows, columns=columns)
    finally:
        workbook.close()


def _load_xlsx_workbook(path: Path):
    from openpyxl import load_workbook

    return load_workbook(path, read_only=True, data_only=True)


def _xlsx_columns(header: tuple[Any, ...]) -> list[str]:
    return [
        str(value) if value is not None else f"Unnamed: {index}"
        for index, value in enumerate(header)
    ]


def _xlsx_needs_limited_read(limits: FullReadLimits) -> bool:
    return (
        limits.max_rows is not None
        or limits.max_columns is not None
        or limits.max_cells is not None
    )


def _xlsx_limited_row_read_count(
    limits: FullReadLimits,
    column_count: int,
) -> int | None:
    row_limit = limits.max_rows + 1 if limits.max_rows is not None else None
    if limits.max_cells is not None and column_count > 0:
        cell_row_limit = limits.max_cells // column_count + 1
        if row_limit is None:
            return cell_row_limit
        return min(row_limit, cell_row_limit)
    return row_limit


def _enforce_file_size(path: Path, max_file_bytes: int | None) -> None:
    if max_file_bytes is None:
        return
    if path.stat().st_size > max_file_bytes:
        raise ValueError(f"Table file exceeds the configured size limit of {max_file_bytes} bytes.")


def _enforce_shape_limits(frame: pd.DataFrame, limits: FullReadLimits) -> None:
    row_count = int(frame.shape[0])
    column_count = int(frame.shape[1])
    if limits.max_rows is not None and row_count > limits.max_rows:
        raise ValueError(
            f"Table row count {row_count} exceeds the configured row limit "
            f"of {limits.max_rows}."
        )
    if limits.max_columns is not None and column_count > limits.max_columns:
        raise ValueError(
            f"Table column count {column_count} exceeds the configured column limit "
            f"of {limits.max_columns}."
        )
    if limits.max_cells is None:
        return
    cell_count = int(frame.shape[0] * frame.shape[1])
    if cell_count > limits.max_cells:
        raise ValueError(
            f"Table contains {cell_count} cells, exceeding the cell limit "
            f"of {limits.max_cells}."
        )
