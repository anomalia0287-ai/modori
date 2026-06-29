from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class TableProvider(Protocol):
    @property
    def row_count(self) -> int: ...

    @property
    def column_count(self) -> int: ...

    def cell(self, row_index: int, column_index: int) -> Any: ...

    def column_header(self, column_index: int) -> str: ...

    def row_id(self, row_index: int) -> str: ...

    def variable_key(self, column_index: int) -> str: ...


class InMemoryTableProvider:
    def __init__(
        self,
        *,
        columns: Sequence[str],
        rows: Sequence[Sequence[Any]],
        row_ids: Sequence[str] | None = None,
    ) -> None:
        self._columns = list(columns)
        self._rows = rows
        if row_ids is None:
            self._row_ids = [f"row-{index:06d}" for index in range(len(rows))]
        else:
            if len(row_ids) != len(rows):
                raise ValueError("row_ids length must match rows length")
            self._row_ids = list(row_ids)

    @property
    def row_count(self) -> int:
        return len(self._rows)

    @property
    def column_count(self) -> int:
        return len(self._columns)

    def cell(self, row_index: int, column_index: int) -> Any:
        return self._rows[row_index][column_index]

    def column_header(self, column_index: int) -> str:
        return self._columns[column_index]

    def row_id(self, row_index: int) -> str:
        return self._row_ids[row_index]

    def variable_key(self, column_index: int) -> str:
        return self._columns[column_index]


class DatasetTableProvider:
    def __init__(self, dataset: object) -> None:
        self._dataset = dataset
        self._frame = getattr(dataset, "df")
        self._columns = [str(column) for column in self._frame.columns]

    @property
    def row_count(self) -> int:
        return int(len(self._frame.index))

    @property
    def column_count(self) -> int:
        return len(self._columns)

    def cell(self, row_index: int, column_index: int) -> Any:
        return self._frame.iat[row_index, column_index]

    def column_header(self, column_index: int) -> str:
        return self._columns[column_index]

    def row_id(self, row_index: int) -> str:
        return f"row-{row_index:06d}"

    def variable_key(self, column_index: int) -> str:
        return self._columns[column_index]
