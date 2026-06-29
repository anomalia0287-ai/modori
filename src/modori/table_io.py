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
    max_file_bytes: int | None = None
    max_rows: int = 30
    max_columns: int | None = 50
    max_cells: int | None = 1_500


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
            source = _xlsx_source(path)
            frame = pd.read_excel(path, **_xlsx_read_excel_kwargs(source))
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
    elif normalized == "xlsx":
        source = _safe_xlsx_source(path)
        columns = pd.read_excel(
            path,
            nrows=0,
            **_xlsx_read_excel_kwargs(source),
        ).columns
    elif normalized == "xls":
        columns = pd.read_excel(path, nrows=0).columns
        source = _table_source(path, normalized)
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
    _validate_preview_limits(limits)
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        _enforce_file_size(path, limits.max_file_bytes)
        frame, warnings = _read_csv_preview(path, limits)
        return _preview_result(
            frame,
            None,
            _table_source(path, normalized),
            preview_limit=_preview_row_limit(limits),
            warnings=warnings,
        )
    if normalized == "xlsx":
        _enforce_file_size(path, limits.max_file_bytes)
        frame, source, warnings = _read_xlsx_preview(path, limits)
        return _preview_result(
            frame,
            None,
            source,
            preview_limit=_preview_row_limit(limits),
            warnings=warnings,
        )
    if normalized == "xls":
        _enforce_file_size(path, limits.max_file_bytes)
        frame, warnings = _read_excel_preview(path, limits)
        return _preview_result(
            frame,
            None,
            _table_source(path, normalized),
            preview_limit=_preview_row_limit(limits),
            warnings=warnings,
        )
    if normalized == "sav":
        import pyreadstat

        _enforce_file_size(path, limits.max_file_bytes)
        _, preview_metadata = pyreadstat.read_sav(
            path,
            metadataonly=True,
            user_missing=True,
        )
        columns = tuple(str(column) for column in getattr(preview_metadata, "column_names", ()))
        selected_columns, warnings = _limited_preview_columns(columns, limits)
        read_kwargs: dict[str, Any] = {
            "row_limit": _preview_row_limit(limits),
            "user_missing": True,
        }
        if selected_columns is not None:
            read_kwargs["usecols"] = list(selected_columns)
        frame, metadata = pyreadstat.read_sav(
            path,
            **read_kwargs,
        )
        return _preview_result(
            frame,
            metadata,
            _table_source(path, normalized),
            preview_limit=_preview_row_limit(limits),
            warnings=warnings,
        )
    raise ValueError(f"Unsupported table file type: {normalized}")


def _read_csv_preview(path: Path, limits: PreviewReadLimits) -> tuple[pd.DataFrame, tuple[str, ...]]:
    header = pd.read_csv(path, nrows=0)
    selected_columns, warnings = _limited_preview_columns(
        tuple(str(column) for column in header.columns),
        limits,
    )
    read_kwargs: dict[str, Any] = {"nrows": _preview_row_limit(limits)}
    if selected_columns is not None:
        read_kwargs["usecols"] = list(selected_columns)
    return pd.read_csv(path, **read_kwargs), warnings


def _read_excel_preview(path: Path, limits: PreviewReadLimits) -> tuple[pd.DataFrame, tuple[str, ...]]:
    header = pd.read_excel(path, nrows=0)
    selected_columns, warnings = _limited_preview_columns(
        tuple(str(column) for column in header.columns),
        limits,
    )
    read_kwargs: dict[str, Any] = {"nrows": _preview_row_limit(limits)}
    if selected_columns is not None:
        read_kwargs["usecols"] = list(selected_columns)
    return pd.read_excel(path, **read_kwargs), warnings


def _read_xlsx_preview(
    path: Path,
    limits: PreviewReadLimits,
) -> tuple[pd.DataFrame, TableReadSource, tuple[str, ...]]:
    return _read_xlsx_rows(path, _preview_row_limit(limits), _preview_column_limit(limits))


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


def _read_xlsx_rows(
    path: Path,
    max_rows: int,
    max_columns: int | None = None,
) -> tuple[pd.DataFrame, TableReadSource, tuple[str, ...]]:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        source = _xlsx_source_from_workbook(path, workbook, worksheet)
        iterator = worksheet.iter_rows(values_only=True)
        try:
            header = next(iterator)
        except StopIteration:
            return pd.DataFrame(), source, ()
        columns = _xlsx_columns(header)
        selected_columns, warnings = _limited_preview_columns(tuple(columns), max_columns)
        if selected_columns is not None:
            columns = list(selected_columns)
        rows = []
        for _, row in zip(range(max_rows), iterator, strict=False):
            rows.append(list(row[: len(columns)]))
        return pd.DataFrame(rows, columns=columns), source, warnings
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


def _xlsx_read_excel_kwargs(source: TableReadSource) -> dict[str, str]:
    if source.sheet_name is None:
        return {}
    return {"sheet_name": source.sheet_name}


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
    warnings: tuple[str, ...] = (),
) -> TablePreviewResult:
    return TablePreviewResult(
        frame=frame,
        metadata=metadata,
        source=source,
        warnings=warnings,
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


def _validate_preview_limits(limits: PreviewReadLimits) -> None:
    if limits.max_rows < 1:
        raise ValueError("Preview max_rows must be at least 1")
    if limits.max_file_bytes is not None and limits.max_file_bytes < 1:
        raise ValueError("Preview max_file_bytes must be at least 1")
    if limits.max_columns is not None and limits.max_columns < 1:
        raise ValueError("Preview max_columns must be at least 1")
    if limits.max_cells is not None and limits.max_cells < 1:
        raise ValueError("Preview max_cells must be at least 1")


def _preview_row_limit(limits: PreviewReadLimits) -> int:
    column_limit = _preview_column_limit(limits)
    if limits.max_cells is None or column_limit is None:
        return limits.max_rows
    return min(limits.max_rows, max(1, limits.max_cells // column_limit))


def _preview_column_limit(limits: PreviewReadLimits) -> int | None:
    column_limit = limits.max_columns
    if limits.max_cells is None:
        return column_limit
    cell_column_limit = max(1, limits.max_cells // limits.max_rows)
    if column_limit is None:
        return cell_column_limit
    return min(column_limit, cell_column_limit)


def _limited_preview_columns(
    columns: tuple[str, ...],
    limits_or_max_columns: PreviewReadLimits | int | None,
) -> tuple[tuple[str, ...] | None, tuple[str, ...]]:
    if isinstance(limits_or_max_columns, PreviewReadLimits):
        max_columns = _preview_column_limit(limits_or_max_columns)
    else:
        max_columns = limits_or_max_columns
    if max_columns is None or len(columns) <= max_columns:
        return None, ()
    return (
        tuple(columns[:max_columns]),
        (f"미리보기 열 제한: {len(columns)}개 중 {max_columns}개 열만 표시합니다.",),
    )


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
