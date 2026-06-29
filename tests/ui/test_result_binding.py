from __future__ import annotations

from modori.ui.contracts import DisplayColumn, DisplayNote, DisplayResult, DisplayTable
from modori.ui.result_binding import ResultBindingPresenter


def test_result_binding_formats_summary_tables_notes_and_chart_paths() -> None:
    presenter = ResultBindingPresenter()
    result = DisplayResult(
        result_id="comparison",
        kind="comparison",
        title_ko="집단비교",
        title_en="Comparison",
        prose_ko="한국어 문장",
        prose_en="English sentence",
        tables=[
            DisplayTable(
                caption_ko="표 1",
                caption_en="Table 1",
                columns=[DisplayColumn(label="값"), DisplayColumn(label="p")],
                rows=[["1.23", ".04"]],
            )
        ],
        chart_paths=["C:/tmp/chart.png"],
        notes=[DisplayNote(title="그림", body="그림 파일을 찾을 수 없습니다")],
    )

    binding = presenter.bind([result])

    assert binding.summary_text == "집단비교\n한국어 문장"
    assert binding.table_text == "표 1\n값\tp\n1.23\t.04"
    assert binding.notes_text == "그림: 그림 파일을 찾을 수 없습니다"
    assert binding.chart_paths_text == "C:/tmp/chart.png"

