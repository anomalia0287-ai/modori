import pandas as pd
import pyreadstat
import pytest
from openpyxl import load_workbook

from modori.table_io import (
    FullReadLimits,
    PreviewReadLimits,
    TableHeaderResult,
    TablePreviewResult,
    TableReadResult,
    read_full,
    read_header,
    read_header_result,
    read_preview,
)


def test_read_full_returns_structured_result_that_stays_tuple_unpackable(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    pd.DataFrame({"score": [1, 2]}).to_csv(path, index=False)

    result = read_full(path, "csv")
    frame, metadata = result

    assert isinstance(result, TableReadResult)
    assert frame.equals(result.frame)
    assert metadata is None
    assert result.source.path == path
    assert result.source.file_type == "csv"
    assert result.columns == ("score",)
    assert result.row_count == 2


def test_read_preview_returns_xlsx_source_context_and_sample_rows(tmp_path) -> None:
    path = tmp_path / "survey.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"respondent_id": [101, 102, 103], "score": [5, 4, 3]}).to_excel(
            writer,
            sheet_name="Survey Responses",
            index=False,
        )
        pd.DataFrame({"code": [1, 2], "label": ["control", "treatment"]}).to_excel(
            writer,
            sheet_name="Codebook",
            index=False,
        )

    result = read_preview(path, "xlsx", limits=PreviewReadLimits(max_rows=2))
    frame, metadata = result

    assert isinstance(result, TablePreviewResult)
    assert metadata is None
    assert frame.shape == (2, 2)
    assert result.source.file_type == "xlsx"
    assert result.source.path == path
    assert result.source.sheet_name == "Survey Responses"
    assert result.source.sheet_names == ("Survey Responses", "Codebook")
    assert result.preview_limit == 2
    assert result.previewed_rows == 2
    assert result.columns == ("respondent_id", "score")
    assert result.sample_rows == (
        {"respondent_id": 101, "score": 5},
        {"respondent_id": 102, "score": 4},
    )


def test_read_header_result_exposes_xlsx_source_context_and_compat_header(tmp_path) -> None:
    path = tmp_path / "survey.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"q1": [1], "q2": [2]}).to_excel(
            writer,
            sheet_name="Responses",
            index=False,
        )
        pd.DataFrame({"code": [1]}).to_excel(writer, sheet_name="Codebook", index=False)

    result = read_header_result(path, "xlsx")

    assert isinstance(result, TableHeaderResult)
    assert result.columns == ("q1", "q2")
    assert tuple(result) == ("q1", "q2")
    assert result.source.file_type == "xlsx"
    assert result.source.sheet_name == "Responses"
    assert result.source.sheet_names == ("Responses", "Codebook")
    assert read_header(path, "xlsx") == ["q1", "q2"]


def test_xlsx_full_header_and_preview_use_same_active_sheet(tmp_path) -> None:
    path = tmp_path / "survey.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"code": [1], "label": ["treatment"]}).to_excel(
            writer,
            sheet_name="Codebook",
            index=False,
        )
        pd.DataFrame({"respondent_id": [101, 102], "score": [5, 4]}).to_excel(
            writer,
            sheet_name="Responses",
            index=False,
        )

    workbook = load_workbook(path)
    workbook.active = workbook.sheetnames.index("Responses")
    workbook.save(path)
    workbook.close()

    preview = read_preview(path, "xlsx", limits=PreviewReadLimits(max_rows=1))
    header = read_header_result(path, "xlsx")
    full = read_full(path, "xlsx")

    assert preview.source.sheet_name == "Responses"
    assert header.source.sheet_name == "Responses"
    assert full.source.sheet_name == "Responses"
    assert preview.columns == ("respondent_id", "score")
    assert header.columns == ("respondent_id", "score")
    assert full.columns == ("respondent_id", "score")
    assert preview.frame.to_dict(orient="list") == {
        "respondent_id": [101],
        "score": [5],
    }
    assert full.frame.to_dict(orient="list") == {
        "respondent_id": [101, 102],
        "score": [5, 4],
    }


def test_read_preview_uses_bounded_csv_columns(tmp_path, monkeypatch) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        if kwargs.get("nrows") == 0:
            return pd.DataFrame(columns=["a", "b", "c"])
        return pd.DataFrame({"a": [1], "b": [2]})

    monkeypatch.setattr("modori.table_io.pd.read_csv", read_csv_spy)

    result = read_preview(path, "csv", limits=PreviewReadLimits(max_rows=2, max_columns=2))

    assert result.columns == ("a", "b")
    assert result.warnings == ("미리보기 열 제한: 3개 중 2개 열만 표시합니다.",)
    assert calls == [
        {"nrows": 0},
        {"nrows": 2, "usecols": ["a", "b"]},
    ]


def test_default_preview_limits_do_not_block_by_file_size() -> None:
    assert PreviewReadLimits().max_file_bytes is None


def test_read_preview_limits_xlsx_columns(tmp_path) -> None:
    path = tmp_path / "survey.xlsx"
    pd.DataFrame(
        {
            "a": [1, 4],
            "b": [2, 5],
            "c": [3, 6],
        }
    ).to_excel(path, index=False)

    result = read_preview(path, "xlsx", limits=PreviewReadLimits(max_rows=2, max_columns=2))

    assert result.columns == ("a", "b")
    assert result.frame.to_dict(orient="list") == {"a": [1, 4], "b": [2, 5]}
    assert result.warnings == ("미리보기 열 제한: 3개 중 2개 열만 표시합니다.",)


def test_read_full_rejects_csv_when_explicit_row_limit_is_exceeded(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="row limit"):
        read_full(path, "csv", limits=FullReadLimits(max_rows=2))


def test_read_full_rejects_csv_when_explicit_column_limit_is_exceeded(tmp_path) -> None:
    path = tmp_path / "survey.csv"
    pd.DataFrame({"a": [1], "b": [2]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="column limit"):
        read_full(path, "csv", limits=FullReadLimits(max_columns=1))


def test_read_full_uses_bounded_csv_read_when_row_limit_is_set(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "survey.csv"
    path.write_text("a\n1\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"a": [1]})

    monkeypatch.setattr("modori.table_io.pd.read_csv", read_csv_spy)

    read_full(path, "csv", limits=FullReadLimits(max_rows=2))

    assert calls == [{"nrows": 3}]


def test_read_full_uses_streaming_xlsx_read_when_row_limit_is_set(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "survey.xlsx"
    path.write_bytes(b"placeholder")
    calls = []

    def read_excel_spy(*args, **kwargs):
        raise AssertionError("pandas.read_excel should not be used for bounded xlsx")

    class FakeWorksheet:
        def iter_rows(self, *, values_only):
            assert values_only is True
            return iter(
                [
                    ("a", "b"),
                    (1, 2),
                    (3, 4),
                    (5, 6),
                ]
            )

    class FakeWorkbook:
        active = FakeWorksheet()

        def close(self):
            calls.append("closed")

    def load_workbook_spy(path_arg, *args, **kwargs):
        calls.append(
            {
                "path": path_arg,
                "read_only": kwargs.get("read_only"),
                "data_only": kwargs.get("data_only"),
            }
        )
        return FakeWorkbook()

    monkeypatch.setattr("modori.table_io.pd.read_excel", read_excel_spy)
    monkeypatch.setattr("openpyxl.load_workbook", load_workbook_spy)

    with pytest.raises(ValueError, match="row limit"):
        read_full(path, "xlsx", limits=FullReadLimits(max_rows=2))

    assert calls == [
        {"path": path, "read_only": True, "data_only": True},
        "closed",
    ]


def test_read_full_passes_sav_row_limit_when_row_limit_is_set(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "survey.sav"
    path.write_bytes(b"placeholder")
    calls = []

    def read_sav_spy(path_arg, *args, **kwargs):
        calls.append({"path": path_arg, **kwargs})
        return pd.DataFrame({"a": [1, 2]}), object()

    monkeypatch.setattr(pyreadstat, "read_sav", read_sav_spy)

    read_full(path, "sav", limits=FullReadLimits(max_rows=2))

    assert calls == [{"path": path, "row_limit": 3, "user_missing": True}]
