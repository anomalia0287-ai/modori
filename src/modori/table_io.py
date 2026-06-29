from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TableReadSource:
    path: Path
    file_type: str
    sheet_name: str | None = None
    sheet_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableReadResult:
    frame: pd.DataFrame
    metadata: Any | None
    source: TableReadSource
    warnings: tuple[str, ...] = ()

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(str(column) for column in self.frame.columns)

    @property
    def row_count(self) -> int:
        return int(self.frame.shape[0])

    def __iter__(self):
        yield self.frame
        yield self.metadata


@dataclass(frozen=True)
class TableHeaderResult:
    columns: tuple[str, ...]
    source: TableReadSource

    def __iter__(self):
        return iter(self.columns)

    def __len__(self) -> int:
        return len(self.columns)

    def __getitem__(self, index: int) -> str:
        return self.columns[index]


@dataclass(frozen=True)
class TablePreviewResult(TableReadResult):
    preview_limit: int = 0
    sample_rows: tuple[dict[str, Any], ...] = ()

    @property
    def previewed_rows(self) -> int:
        return self.row_count


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
) -> TableReadResult:
    normalized = normalize_file_type(path, file_type)
    _enforce_file_size(path, limits.max_file_bytes)
    if normalized == "csv":
        read_kwargs = {}
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_csv(path, **read_kwargs)
        metadata = None
        source = _table_source(path, normalized)
    elif normalized == "xlsx":
        if _xlsx_needs_limited_read(limits):
            frame, source = _read_xlsx_limited(path, limits)
        else:
            frame = pd.read_excel(path)
            source = _xlsx_source(path)
        metadata = None
    elif normalized == "xls":
        read_kwargs = {}
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_excel(path, **read_kwargs)
        metadata = None
        source = _table_source(path, normalized)
    elif normalized == "sav":
        import pyreadstat

        read_kwargs = {"user_missing": True}
        if limits.max_rows is not None:
            read_kwargs["row_limit"] = limits.max_rows + 1
        frame, metadata = pyreadstat.read_sav(path, **read_kwargs)
        source = _table_source(path, normalized)
    else:
        raise ValueError(f"Unsupported table file type: {normalized}")
    _enforce_shape_limits(frame, limits)
    return TableReadResult(frame=frame, metadata=metadata, source=source)


def read_header(path: Path, file_type: str | None = None) -> list[str]:
    return list(read_header_result(path, file_type).columns)


def read_header_result(path: Path, file_type: str | None = None) -> TableHeaderResult:
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        columns = pd.read_csv(path, nrows=0).columns
        source = _table_source(path, normalized)
    elif normalized in {"xlsx", "xls"}:
        columns = pd.read_excel(path, nrows=0).columns
        source = (
            _safe_xlsx_source(path)
            if normalized == "xlsx"
            else _table_source(path, normalized)
        )
    elif normalized == "sav":
        import pyreadstat

        frame, metadata = pyreadstat.read_sav(
            path,
            metadataonly=True,
            user_missing=True,
        )
        columns = getattr(metadata, "column_names", None) or frame.columns
        source = _table_source(path, normalized)
    else:
        raise ValueError(f"Unsupported table file type: {normalized}")
    return TableHeaderResult(
        columns=tuple(str(column) for column in columns),
        source=source,
    )


def read_preview(
    path: Path,
    file_type: str | None = None,
    *,
    limits: PreviewReadLimits = DEFAULT_PREVIEW_READ_LIMITS,
) -> TablePreviewResult:
    if limits.max_rows < 1:
        raise ValueError("Preview max_rows must be at least 1")
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        frame = pd.read_csv(path, nrows=limits.max_rows)
        return _preview_result(
            frame,
            None,
            _table_source(path, normalized),
            preview_limit=limits.max_rows,
        )
    if normalized == "xlsx":
        frame, source = _read_xlsx_preview(path, limits.max_rows)
        return _preview_result(frame, None, source, preview_limit=limits.max_rows)
    if normalized == "xls":
        frame = pd.read_excel(path, nrows=limits.max_rows)
        return _preview_result(
            frame,
            None,
            _table_source(path, normalized),
            preview_limit=limits.max_rows,
        )
    if normalized == "sav":
        import pyreadstat

        frame, metadata = pyreadstat.read_sav(
            path,
            row_limit=limits.max_rows,
            user_missing=True,
        )
        return _preview_result(
            frame,
            metadata,
            _table_source(path, normalized),
            preview_limit=limits.max_rows,
        )
    raise ValueError(f"Unsupported table file type: {normalized}")


def _read_xlsx_preview(path: Path, max_rows: int) -> tuple[pd.DataFrame, TableReadSource]:
    return _read_xlsx_rows(path, max_rows)


def _read_xlsx_limited(path: Path, limits: FullReadLimits) -> tuple[pd.DataFrame, TableReadSource]:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        source = _xlsx_source_from_workbook(path, workbook, worksheet)
        iterator = worksheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return pd.DataFrame(), source
        columns = _xlsx_columns(header)
        row_limit = _xlsx_limited_row_read_count(limits, len(columns))
        rows = []
        for row in iterator:
            rows.append(list(row))
            if row_limit is not None and len(rows) >= row_limit:
                break
        return pd.DataFrame(rows, columns=columns), source
    finally:
        workbook.close()


def _read_xlsx_rows(path: Path, max_rows: int) -> tuple[pd.DataFrame, TableReadSource]:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        source = _xlsx_source_from_workbook(path, workbook, worksheet)
        iterator = worksheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return pd.DataFrame(), source
        columns = _xlsx_columns(header)
        rows = []
        for _, row in zip(range(max_rows), iterator, strict=False):
            rows.append(list(row))
        return pd.DataFrame(rows, columns=columns), source
    finally:
        workbook.close()


def _load_xlsx_workbook(path: Path):
    from openpyxl import load_workbook

    return load_workbook(path, read_only=True, data_only=True)


def _table_source(path: Path, file_type: str) -> TableReadSource:
    return TableReadSource(path=path, file_type=file_type)


def _xlsx_source(path: Path) -> TableReadSource:
    workbook = _load_xlsx_workbook(path)
    try:
        return _xlsx_source_from_workbook(path, workbook, workbook.active)
    finally:
        workbook.close()


def _safe_xlsx_source(path: Path) -> TableReadSource:
    try:
        return _xlsx_source(path)
    except Exception:
        return _table_source(path, "xlsx")


def _xlsx_source_from_workbook(
    path: Path,
    workbook: Any,
    worksheet: Any,
) -> TableReadSource:
    return TableReadSource(
        path=path,
        file_type="xlsx",
        sheet_name=getattr(worksheet, "title", None),
        sheet_names=tuple(str(name) for name in getattr(workbook, "sheetnames", ())),
    )


def _preview_result(
    frame: pd.DataFrame,
    metadata: Any | None,
    source: TableReadSource,
    *,
    preview_limit: int,
) -> TablePreviewResult:
    return TablePreviewResult(
        frame=frame,
        metadata=metadata,
        source=source,
        preview_limit=preview_limit,
        sample_rows=_sample_rows(frame),
    )


def _sample_rows(frame: pd.DataFrame) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        rows.append({str(key): _display_cell(value) for key, value in row.items()})
    return tuple(rows)


def _display_cell(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


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
