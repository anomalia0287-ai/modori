from __future__ import annotations

from dataclasses import dataclass

from modori.ui.result_state import UiResultState


@dataclass(frozen=True)
class FakeBinding:
    summary_text: str
    table_text: str
    notes_text: str
    chart_paths_text: str
    chart_source_text: str
    chart_paths: list[str]


class FakePresenter:
    def __init__(self) -> None:
        self.payloads: list[list[object]] = []

    def bind(self, results_model):
        self.payloads.append(list(results_model))
        return FakeBinding(
            summary_text="summary",
            table_text="table",
            notes_text="notes",
            chart_paths_text="new-chart.png",
            chart_source_text="chart-source",
            chart_paths=["new-chart.png"],
        )


def test_result_state_clears_all_bound_result_fields() -> None:
    state = UiResultState()
    state.summary_text = "summary"
    state.table_text = "table"
    state.notes_text = "notes"
    state.chart_paths_text = "old-chart.png"
    state.chart_source_text = "source"
    state.results_model = ["old"]

    state.clear()

    assert state.results_model == []
    assert state.summary_text == ""
    assert state.table_text == ""
    assert state.notes_text == ""
    assert state.chart_paths_text == ""
    assert state.chart_source_text == ""


def test_result_state_binds_payload_and_returns_chart_cleanup_boundary() -> None:
    state = UiResultState()
    state.chart_paths_text = "old-chart.png"
    presenter = FakePresenter()

    previous_paths, current_paths = state.bind_payload("fresh", presenter)

    assert state.results_model == ["fresh"]
    assert state.summary_text == "summary"
    assert state.table_text == "table"
    assert state.notes_text == "notes"
    assert state.chart_paths_text == "new-chart.png"
    assert state.chart_source_text == "chart-source"
    assert previous_paths == ["old-chart.png"]
    assert current_paths == ["new-chart.png"]
    assert presenter.payloads == [["fresh"]]


def test_result_state_binds_list_payload_without_wrapping() -> None:
    state = UiResultState()
    presenter = FakePresenter()

    state.bind_payload(["a", "b"], presenter)

    assert state.results_model == ["a", "b"]
    assert presenter.payloads == [["a", "b"]]
