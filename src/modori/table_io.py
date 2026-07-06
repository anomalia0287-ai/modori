from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
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


@dataclass(frozen=True)
class _DelimitedReadContext:
    encoding: str | None
    delimiter: str
    header_row_index: int
    header_cells: tuple[Any, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _XlsxReadContext:
    source: TableReadSource
    header_row_index: int
    header_cells: tuple[Any, ...]
    warnings: tuple[str, ...] = ()


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
        context = _csv_read_context(path)
        read_kwargs = _csv_read_kwargs(context)
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_csv(path, **read_kwargs)
        frame, cleanup_warnings = _sanitize_frame(frame, context.header_cells)
        metadata = None
        source = _table_source(path, normalized)
        warnings = _merge_warnings(context.warnings, cleanup_warnings)
    elif normalized == "xlsx":
        if _xlsx_needs_limited_read(limits):
            frame, source, warnings = _read_xlsx_limited(path, limits)
        else:
            context = _xlsx_read_context(path)
            source = context.source
            frame = pd.read_excel(
                path,
                header=context.header_row_index,
                **_xlsx_read_excel_kwargs(source),
            )
            frame, cleanup_warnings = _sanitize_frame(frame, context.header_cells)
            warnings = _merge_warnings(context.warnings, cleanup_warnings)
        metadata = None
    elif normalized == "xls":
        read_kwargs = {}
        if limits.max_rows is not None:
            read_kwargs["nrows"] = limits.max_rows + 1
        frame = pd.read_excel(path, **read_kwargs)
        metadata = None
        source = _table_source(path, normalized)
        frame, cleanup_warnings = _sanitize_frame(frame, tuple(frame.columns))
        warnings = cleanup_warnings
    elif normalized == "sav":
        import pyreadstat

        read_kwargs = {"user_missing": True}
        if limits.max_rows is not None:
            read_kwargs["row_limit"] = limits.max_rows + 1
        frame, metadata = pyreadstat.read_sav(path, **read_kwargs)
        source = _table_source(path, normalized)
        warnings = ()
    else:
        raise ValueError(f"Unsupported table file type: {normalized}")
    _enforce_shape_limits(frame, limits)
    return TableReadResult(frame=frame, metadata=metadata, source=source, warnings=warnings)


def read_header(path: Path, file_type: str | None = None) -> list[str]:
    return list(read_header_result(path, file_type).columns)


def read_header_result(path: Path, file_type: str | None = None) -> TableHeaderResult:
    normalized = normalize_file_type(path, file_type)
    if normalized == "csv":
        context = _csv_read_context(path)
        frame = pd.read_csv(path, nrows=0, **_csv_read_kwargs(context))
        frame, _ = _sanitize_frame(frame, context.header_cells)
        columns = frame.columns
        source = _table_source(path, normalized)
    elif normalized == "xlsx":
        context = _safe_xlsx_read_context(path)
        source = context.source
        read_kwargs = _xlsx_read_excel_kwargs(source)
        if context.header_row_index > 0:
            read_kwargs["header"] = context.header_row_index
        frame = pd.read_excel(
            path,
            nrows=0,
            **read_kwargs,
        )
        frame, _ = _sanitize_frame(frame, context.header_cells)
        columns = frame.columns
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
    context = _csv_read_context(path)
    header = pd.read_csv(path, nrows=0, **_csv_read_kwargs(context))
    selected_columns, warnings = _limited_preview_columns(
        tuple(str(column) for column in header.columns),
        limits,
    )
    read_kwargs: dict[str, Any] = {
        **_csv_read_kwargs(context),
        "nrows": _preview_row_limit(limits),
    }
    header_cells = context.header_cells
    if selected_columns is not None:
        read_kwargs["usecols"] = list(selected_columns)
        header_cells = _selected_header_cells(header.columns, context.header_cells, selected_columns)
    frame = pd.read_csv(path, **read_kwargs)
    frame, cleanup_warnings = _sanitize_frame(frame, header_cells)
    return frame, _merge_warnings(context.warnings, warnings, cleanup_warnings)


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


def _read_xlsx_limited(
    path: Path,
    limits: FullReadLimits,
    context: _XlsxReadContext | None = None,
) -> tuple[pd.DataFrame, TableReadSource, tuple[str, ...]]:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        context = context or _xlsx_read_context_from_workbook(path, workbook, worksheet)
        iterator = worksheet.iter_rows(values_only=True)
        _skip_rows(iterator, context.header_row_index + 1)
        columns = _xlsx_columns(context.header_cells)
        row_limit = _xlsx_limited_row_read_count(limits, len(columns))
        rows = []
        for row in iterator:
            rows.append(list(row))
            if row_limit is not None and len(rows) >= row_limit:
                break
        frame = pd.DataFrame(rows, columns=columns)
        frame, cleanup_warnings = _sanitize_frame(frame, context.header_cells)
        return frame, context.source, _merge_warnings(context.warnings, cleanup_warnings)
    finally:
        workbook.close()


def _read_xlsx_rows(
    path: Path,
    max_rows: int,
    max_columns: int | None = None,
) -> tuple[pd.DataFrame, TableReadSource, tuple[str, ...]]:
    context = _xlsx_read_context(path)
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        iterator = worksheet.iter_rows(values_only=True)
        _skip_rows(iterator, context.header_row_index + 1)
        if not context.header_cells:
            return pd.DataFrame(), context.source, context.warnings
        columns = _xlsx_columns(context.header_cells)
        selected_columns, warnings = _limited_preview_columns(tuple(columns), max_columns)
        header_cells = context.header_cells
        if selected_columns is not None:
            columns = list(selected_columns)
            header_cells = tuple(header_cells[: len(columns)])
        rows = []
        for _, row in zip(range(max_rows), iterator, strict=False):
            rows.append(list(row[: len(columns)]))
        frame = pd.DataFrame(rows, columns=columns)
        frame, cleanup_warnings = _sanitize_frame(frame, header_cells)
        return frame, context.source, _merge_warnings(context.warnings, warnings, cleanup_warnings)
    finally:
        workbook.close()


def _load_xlsx_workbook(path: Path):
    from openpyxl import load_workbook

    return load_workbook(path, read_only=True, data_only=True)


def _csv_read_context(path: Path) -> _DelimitedReadContext:
    sample = path.read_bytes()[:128 * 1024]
    if not sample:
        return _DelimitedReadContext(
            encoding=None,
            delimiter=",",
            header_row_index=0,
            header_cells=(),
        )
    encoding, encoding_warnings = _detect_text_encoding(sample)
    text = sample.decode(encoding, errors="strict")
    delimiter = _detect_delimiter(text)
    rows = _parse_delimited_sample(text, delimiter)
    header_row_index = _detect_header_row_index(rows)
    header_cells = tuple(rows[header_row_index]) if header_row_index < len(rows) else ()
    warnings = list(encoding_warnings)
    if delimiter != ",":
        warnings.append(f"CSV 구분자: {_delimiter_label(delimiter)}")
    warnings.extend(_header_offset_warnings(header_row_index))
    return _DelimitedReadContext(
        encoding=None if encoding in {"utf-8", "utf-8-sig"} else encoding,
        delimiter=delimiter,
        header_row_index=header_row_index,
        header_cells=header_cells,
        warnings=tuple(warnings),
    )


def _detect_text_encoding(sample: bytes) -> tuple[str, tuple[str, ...]]:
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", ()
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            sample.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
        if encoding == "utf-8":
            return encoding, ()
        return encoding, (f"CSV 인코딩: {encoding}",)
    return "utf-8", ()


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(line for line in text.splitlines()[:20] if line.strip())
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        counts = {
            delimiter: sum(line.count(delimiter) for line in sample.splitlines())
            for delimiter in (",", "\t", ";", "|")
        }
        delimiter, count = max(counts.items(), key=lambda item: item[1])
        return delimiter if count > 0 else ","


def _delimiter_label(delimiter: str) -> str:
    return "탭" if delimiter == "\t" else delimiter


def _parse_delimited_sample(text: str, delimiter: str) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for row in csv.reader(StringIO(text), delimiter=delimiter):
        rows.append(tuple(row))
        if len(rows) >= 30:
            break
    return rows


def _csv_read_kwargs(context: _DelimitedReadContext) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if context.encoding:
        kwargs["encoding"] = context.encoding
    if context.delimiter != ",":
        kwargs["sep"] = context.delimiter
        kwargs["engine"] = "python"
    if context.header_row_index > 0:
        kwargs["skiprows"] = context.header_row_index
    return kwargs


def _safe_xlsx_read_context(path: Path) -> _XlsxReadContext:
    try:
        return _xlsx_read_context(path)
    except Exception:
        return _XlsxReadContext(
            source=_table_source(path, "xlsx"),
            header_row_index=0,
            header_cells=(),
        )


def _xlsx_read_context(path: Path) -> _XlsxReadContext:
    workbook = _load_xlsx_workbook(path)
    try:
        worksheet = workbook.active
        return _xlsx_read_context_from_workbook(path, workbook, worksheet)
    finally:
        workbook.close()


def _xlsx_read_context_from_workbook(
    path: Path,
    workbook: Any,
    worksheet: Any,
) -> _XlsxReadContext:
    source = _xlsx_source_from_workbook(path, workbook, worksheet)
    rows: list[tuple[Any, ...]] = []
    for _, row in zip(range(30), worksheet.iter_rows(values_only=True), strict=False):
        rows.append(tuple(row))
    header_row_index = _detect_header_row_index(rows)
    header_cells = tuple(rows[header_row_index]) if header_row_index < len(rows) else ()
    return _XlsxReadContext(
        source=source,
        header_row_index=header_row_index,
        header_cells=header_cells,
        warnings=tuple(_header_offset_warnings(header_row_index)),
    )


def _detect_header_row_index(rows: list[tuple[Any, ...]]) -> int:
    best_index = 0
    best_score = float("-inf")
    for index, row in enumerate(rows[:20]):
        cells = _trim_cells(row)
        non_empty = [cell for cell in cells if cell]
        if len(non_empty) < 2:
            continue
        width = len(cells)
        score = float(len(non_empty))
        if any(not _is_number_like(cell) for cell in non_empty):
            score += 4
        if all(_is_number_like(cell) for cell in non_empty):
            score -= 8
        if _looks_like_metadata_row(non_empty):
            score -= 10
        score += _following_data_row_score(rows, index, width)
        if len(set(non_empty)) == len(non_empty):
            score += 2
        else:
            score -= 1
        if index == 0:
            score += 1
        elif any(_row_width(previous) < width for previous in rows[:index]):
            score += 2
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def _trim_cells(row: tuple[Any, ...]) -> tuple[str, ...]:
    cells = ["" if cell is None else str(cell).strip() for cell in row]
    while cells and not cells[-1]:
        cells.pop()
    return tuple(cells)


def _row_width(row: tuple[Any, ...]) -> int:
    return len(_trim_cells(row))


def _looks_like_metadata_row(non_empty: list[str]) -> bool:
    if len(non_empty) > 2:
        return False
    marker_text = " ".join(non_empty)
    return any(
        marker in marker_text
        for marker in ("자료기준", "기준일", "단위", "출처", "제공기관", "저작권")
    )


def _is_number_like(value: str) -> bool:
    cleaned = "".join(character for character in value if character not in ",%").strip()
    if not cleaned:
        return False
    try:
        float(cleaned)
    except ValueError:
        return False
    return True


def _following_data_row_score(
    rows: list[tuple[Any, ...]],
    header_index: int,
    header_width: int,
) -> float:
    score = 0.0
    for row in rows[header_index + 1 : header_index + 6]:
        cells = _trim_cells(row)
        non_empty = [cell for cell in cells if cell]
        if len(non_empty) < 2:
            continue
        if abs(len(cells) - header_width) <= 1:
            score += 3
        if any(_is_number_like(cell) for cell in non_empty):
            score += 1
    return score


def _header_offset_warnings(header_row_index: int) -> tuple[str, ...]:
    if header_row_index <= 0:
        return ()
    return (f"표 헤더 앞의 안내 행 {header_row_index}개를 건너뛰었습니다.",)


def _selected_header_cells(
    columns: Any,
    header_cells: tuple[Any, ...],
    selected_columns: tuple[str, ...],
) -> tuple[Any, ...]:
    column_names = [str(column) for column in columns]
    selected_cells: list[Any] = []
    for selected in selected_columns:
        try:
            index = column_names.index(selected)
        except ValueError:
            selected_cells.append(selected)
            continue
        selected_cells.append(header_cells[index] if index < len(header_cells) else selected)
    return tuple(selected_cells)


def _skip_rows(iterator: Any, count: int) -> None:
    for _ in range(count):
        try:
            next(iterator)
        except StopIteration:
            return


def _sanitize_frame(
    frame: pd.DataFrame,
    header_cells: tuple[Any, ...],
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    if frame.empty and len(frame.columns) == 0:
        return frame, ()
    keep_indexes: list[int] = []
    names: list[str] = []
    dropped_blank = 0
    renamed_blank = 0
    duplicate_count = 0
    seen: dict[str, int] = {}
    for index, current in enumerate(frame.columns):
        raw = header_cells[index] if index < len(header_cells) else current
        name = _clean_column_name(raw)
        series = frame.iloc[:, index]
        if not name:
            if _is_empty_column(series):
                dropped_blank += 1
                continue
            renamed_blank += 1
            name = f"column_{index + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        if count:
            duplicate_count += 1
            name = f"{name}_{count + 1}"
        keep_indexes.append(index)
        names.append(name)
    cleaned = frame.iloc[:, keep_indexes].copy()
    cleaned.columns = names
    warnings: list[str] = []
    if dropped_blank:
        warnings.append(f"빈 열 {dropped_blank}개를 제외했습니다.")
    if renamed_blank:
        warnings.append(f"빈 헤더 {renamed_blank}개를 column_N 형식으로 바꿨습니다.")
    if duplicate_count:
        warnings.append(f"중복 열 이름 {duplicate_count}개를 고유한 이름으로 바꿨습니다.")
    return cleaned, tuple(warnings)


def _clean_column_name(value: Any) -> str:
    if value is None:
        return ""
    name = str(value).strip()
    if not name:
        return ""
    if name.lower().startswith("unnamed:"):
        return ""
    return name


def _is_empty_column(series: pd.Series) -> bool:
    for value in series:
        if pd.isna(value):
            continue
        if str(value).strip() == "":
            continue
        return False
    return True


def _merge_warnings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged: list[str] = []
    for group in groups:
        for warning in group:
            if warning and warning not in merged:
                merged.append(warning)
    return tuple(merged)


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
