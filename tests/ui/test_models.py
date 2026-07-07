from PySide6.QtCore import Qt


class CountingProvider:
    row_count = 10_000
    column_count = 200

    def __init__(self) -> None:
        self.cell_requests: list[tuple[int, int]] = []
        self.row_id_requests: list[int] = []

    def cell(self, row_index: int, column_index: int) -> str:
        self.cell_requests.append((row_index, column_index))
        return f"r{row_index}c{column_index}"

    def column_header(self, column_index: int) -> str:
        return f"v{column_index}"

    def row_id(self, row_index: int) -> str:
        self.row_id_requests.append(row_index)
        return f"row-{row_index}"

    def variable_key(self, column_index: int) -> str:
        return f"v{column_index}"


def test_data_table_model_is_lazy() -> None:
    from modori.ui.models import DataTableModel

    provider = CountingProvider()
    model = DataTableModel(provider)

    assert model.rowCount() == 10_000
    assert model.columnCount() == 200
    assert provider.cell_requests == []

    assert model.data(model.index(123, 45), Qt.ItemDataRole.DisplayRole) == "r123c45"
    assert provider.cell_requests == [(123, 45)]


def test_data_table_model_headers_use_human_row_numbers_without_exposing_internal_ids() -> None:
    from modori.ui.models import DataTableModel

    provider = CountingProvider()
    model = DataTableModel(provider)

    assert model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) == "v2"
    assert model.headerData(3, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole) == "4"
    assert provider.row_id_requests == []


def test_variable_table_model_exposes_metadata_rows() -> None:
    from modori.ui.models import VariableRecord, VariableTableModel

    model = VariableTableModel(
        [
            VariableRecord(
                key="score",
                label="Job satisfaction",
                measure="scale",
                value_labels="",
                missing_codes="",
                display_type="numeric",
            )
        ]
    )

    assert model.rowCount() == 1
    assert model.columnCount() == 6
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "score"
    assert model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "scale"
    role_names = {bytes(value).decode("utf-8") for value in model.roleNames().values()}
    assert "variableKey" in role_names
    assert "measureValue" in role_names
    assert model.data(model.index(0, 4), VariableTableModel.VARIABLE_KEY_ROLE) == "score"
    assert model.data(model.index(0, 4), VariableTableModel.MEASURE_VALUE_ROLE) == "scale"


def test_variable_records_from_engine_dataset() -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.models import variable_records_from_dataset

    dataset = Dataset(
        df=pd.DataFrame({"score": [1]}),
        variables={
            "score": Variable(
                "score",
                "Job satisfaction",
                Measure.SCALE,
                {1.0: "Low"},
                [99.0],
                "int64",
                "import",
            )
        },
    )

    records = variable_records_from_dataset(dataset)

    assert records[0].key == "score"
    assert records[0].label == "Job satisfaction"
    assert records[0].measure == "scale"
    assert "1.0=Low" in records[0].value_labels
    assert records[0].missing_codes == "99.0"
