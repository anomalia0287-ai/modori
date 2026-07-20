class FakeEngineResult:
    chart_paths: list[str]

    def __init__(self, chart_paths: list[str] | None = None) -> None:
        self.chart_paths = chart_paths or []


def test_display_result_uses_reporting_helpers(monkeypatch) -> None:
    from modori.ui import results as ui_results

    prose_calls: list[str] = []
    table_calls: list[object] = []

    def fake_prose_for(result, language="ko"):
        prose_calls.append(language)
        return "한국어 문장" if language == "ko" else "English sentence"

    def fake_table_for(result, *, language="ko"):
        table_calls.append((result, language))
        warning = "주의" if language == "ko" else "Caution"
        return [{"statistic": "t", "p": ".012", "warning": warning}]

    monkeypatch.setattr(ui_results, "prose_for", fake_prose_for)
    monkeypatch.setattr(ui_results, "table_for", fake_table_for)

    engine_result = FakeEngineResult()
    display = ui_results.display_result_from_engine_result(
        engine_result,
        result_id="comparison:score:group",
        kind="comparison",
    )

    assert prose_calls == ["ko", "en"]
    assert table_calls == [(engine_result, "ko"), (engine_result, "en")]
    assert display.result_id == "comparison:score:group"
    assert display.kind == "comparison"
    assert display.prose_ko == "한국어 문장"
    assert display.prose_en == "English sentence"
    assert display.tables[0].columns[0].label == "statistic"
    assert display.tables[0].rows == [["t", ".012", "주의"]]
    assert display.tables[0].rows_en == [["t", ".012", "Caution"]]


def test_missing_chart_path_becomes_display_note(monkeypatch, tmp_path) -> None:
    from modori.ui import results as ui_results

    missing = tmp_path / "missing.png"
    monkeypatch.setattr(ui_results, "prose_for", lambda result, language="ko": "문장")
    monkeypatch.setattr(
        ui_results,
        "table_for",
        lambda result, *, language="ko": [],
    )

    display = ui_results.display_result_from_engine_result(
        FakeEngineResult(chart_paths=[str(missing)]),
        result_id="charted",
        kind="regression",
    )

    assert display.chart_paths == []
    assert display.notes[0].body == "그림 파일을 찾을 수 없습니다"


def test_existing_chart_path_is_preserved(monkeypatch, tmp_path) -> None:
    from modori.ui import results as ui_results

    chart = tmp_path / "chart.png"
    chart.write_text("png placeholder", encoding="utf-8")
    monkeypatch.setattr(ui_results, "prose_for", lambda result, language="ko": "문장")
    monkeypatch.setattr(
        ui_results,
        "table_for",
        lambda result, *, language="ko": [],
    )

    display = ui_results.display_result_from_engine_result(
        FakeEngineResult(chart_paths=[str(chart)]),
        result_id="charted",
        kind="regression",
    )

    assert display.chart_paths == [str(chart)]
    assert display.notes == []


def test_report_export_delegates_to_report_step_path(tmp_path) -> None:
    from modori.ui.contracts import ReportExportOptions
    from modori.ui.controller import UiController

    output = tmp_path / "report.docx"

    def exporter(pipeline, options):
        output.write_text("docx placeholder", encoding="utf-8")
        return output

    controller = UiController(pipeline=object(), report_exporter=exporter)

    result = controller.exportReport(ReportExportOptions(language="ko"))

    assert result.ok is True
    assert result.result_ids == [str(output)]
    assert output.exists()
