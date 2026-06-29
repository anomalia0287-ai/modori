from __future__ import annotations

import pandas as pd

from modori.ui.importing import ImportPreviewService


def test_import_preview_service_returns_variable_summary(tmp_path) -> None:
    data_path = tmp_path / "survey.csv"
    pd.DataFrame({"group": [1, 2], "score": [3.5, 4.5]}).to_csv(data_path, index=False)

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert preview.pending_path == data_path
    assert "2 cases" in preview.text
    assert "2 variables" in preview.text
    assert "group" in preview.text
    assert "score" in preview.text


def test_import_preview_service_reads_bounded_csv_preview(tmp_path, monkeypatch) -> None:
    data_path = tmp_path / "large-survey.csv"
    data_path.write_text("score\n1\n2\n", encoding="utf-8")
    calls = []

    def read_csv_spy(path_arg, *args, **kwargs):
        calls.append(kwargs)
        return pd.DataFrame({"score": [1, 2, 3]})

    monkeypatch.setattr("modori.table_io.pd.read_csv", read_csv_spy)

    preview = ImportPreviewService().preview(data_path)

    assert preview.ok is True
    assert calls == [{"nrows": 30}]
