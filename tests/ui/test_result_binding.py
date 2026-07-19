from __future__ import annotations

import pytest

from modori.ui.contracts import DisplayColumn, DisplayNote, DisplayResult, DisplayTable
from modori.ui.result_binding import ResultBindingPresenter
from modori.ui.result_validation import ResultPayloadValidator
from modori.ui.results import display_result_from_engine_result


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

    english = presenter.bind([result], language="en")

    assert english.summary_text == "Comparison\nEnglish sentence"
    assert english.table_text == "Table 1\n값\tp\n1.23\t.04"
    assert english.notes_text == "Figure: Figure file could not be found"


def test_factorial_result_kind_has_bilingual_product_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("modori.ui.results.prose_for", lambda _result, language: language)
    monkeypatch.setattr("modori.ui.results.table_for", lambda _result: [])

    display = display_result_from_engine_result(
        object(),
        result_id="anova_factorial",
        kind="anova_factorial",  # type: ignore[arg-type]
    )

    assert display.kind == "anova_factorial"
    assert display.title_ko == "이원 Type III 분산분석"
    assert display.title_en == "Two-factor Type III ANOVA"


@pytest.mark.parametrize("kind", ["logistic_regression", "anova_factorial"])
def test_result_payload_validator_accepts_all_registered_model_kinds(kind: str) -> None:
    payload = [
        DisplayResult(
            result_id=kind,
            kind=kind,  # type: ignore[arg-type]
            title_ko="결과",
            title_en="Result",
            prose_ko="요약",
            prose_en="Summary",
        )
    ]

    assert ResultPayloadValidator().validate(payload).ok is True
