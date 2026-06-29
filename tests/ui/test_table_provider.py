def test_in_memory_table_provider_exposes_stable_row_ids() -> None:
    from modori.ui.table_provider import InMemoryTableProvider

    provider = InMemoryTableProvider(
        columns=["q1", "q2"],
        rows=[[1, 2], [3, 4]],
    )

    assert provider.row_count == 2
    assert provider.column_count == 2
    assert provider.row_id(0) == "row-000000"
    assert provider.row_id(1) == "row-000001"
    assert provider.variable_key(1) == "q2"
    assert provider.cell(1, 0) == 3


def test_table_provider_accepts_explicit_row_ids() -> None:
    from modori.ui.table_provider import InMemoryTableProvider

    provider = InMemoryTableProvider(
        columns=["score"],
        rows=[[10], [11]],
        row_ids=["case-a", "case-b"],
    )

    assert provider.row_id(0) == "case-a"
    assert provider.row_id(1) == "case-b"


def test_dataset_table_provider_reads_engine_dataset_without_materializing_matrix() -> None:
    import pandas as pd

    from modori.core import Dataset, Measure, Variable
    from modori.ui.table_provider import DatasetTableProvider

    dataset = Dataset(
        df=pd.DataFrame({"score": [1, 2], "group": ["A", "B"]}),
        variables={
            "score": Variable("score", "Score", Measure.SCALE, {}, [], "int64", "import"),
            "group": Variable("group", "Group", Measure.NOMINAL, {}, [], "object", "import"),
        },
    )
    provider = DatasetTableProvider(dataset)

    assert provider.row_count == 2
    assert provider.column_count == 2
    assert provider.column_header(0) == "score"
    assert provider.row_id(1) == "row-000001"
    assert provider.cell(1, 1) == "B"
