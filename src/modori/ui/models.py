from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QByteArray, QModelIndex, Qt

from modori.ui.table_provider import TableProvider


class DataTableModel(QAbstractTableModel):
    def __init__(self, provider: TableProvider) -> None:
        super().__init__()
        self._provider = provider

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._provider.row_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._provider.column_count

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        value = self._provider.cell(index.row(), index.column())
        return "" if value is None else str(value)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._provider.column_header(section)
        return str(section + 1)


@dataclass(frozen=True)
class VariableRecord:
    key: str
    label: str
    measure: str
    value_labels: str
    missing_codes: str
    display_type: str


class VariableTableModel(QAbstractTableModel):
    VARIABLE_KEY_ROLE = int(Qt.ItemDataRole.UserRole) + 1
    MEASURE_VALUE_ROLE = int(Qt.ItemDataRole.UserRole) + 2

    _columns = ("이름", "레이블", "측정수준", "값 레이블", "결측", "유형")

    def __init__(self, records: list[VariableRecord] | None = None) -> None:
        super().__init__()
        self._records = list(records or [])

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        record = self._records[index.row()]
        if role == self.VARIABLE_KEY_ROLE:
            return record.key
        if role == self.MEASURE_VALUE_ROLE:
            return record.measure
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        values = (
            record.key,
            record.label,
            record.measure,
            record.value_labels,
            record.missing_codes,
            record.display_type,
        )
        return values[index.column()]

    def roleNames(self) -> dict[int, QByteArray]:
        roles = super().roleNames()
        roles[self.VARIABLE_KEY_ROLE] = QByteArray(b"variableKey")
        roles[self.MEASURE_VALUE_ROLE] = QByteArray(b"measureValue")
        return roles

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section]
        return str(section + 1)


def variable_records_from_dataset(dataset: object) -> list[VariableRecord]:
    variables = getattr(dataset, "variables", {})
    records: list[VariableRecord] = []
    for key, variable in variables.items():
        value_labels = getattr(variable, "value_labels", {}) or {}
        missing_values = getattr(variable, "missing_values", []) or []
        measure = getattr(getattr(variable, "measure", ""), "value", getattr(variable, "measure", ""))
        records.append(
            VariableRecord(
                key=str(key),
                label=str(getattr(variable, "label", "") or ""),
                measure=str(measure),
                value_labels=", ".join(
                    f"{float(label_key)}={label_value}"
                    for label_key, label_value in value_labels.items()
                ),
                missing_codes=", ".join(str(float(value)) for value in missing_values),
                display_type=str(getattr(variable, "dtype", "")),
            )
        )
    return records
