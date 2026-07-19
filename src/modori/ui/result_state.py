from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UiResultState:
    results_model: list[Any] = field(default_factory=list)
    summary_text: str = ""
    table_text: str = ""
    notes_text: str = ""
    chart_paths_text: str = ""
    chart_source_text: str = ""

    def clear(self) -> None:
        self.results_model = []
        self.summary_text = ""
        self.table_text = ""
        self.notes_text = ""
        self.chart_paths_text = ""
        self.chart_source_text = ""

    def bind_payload(
        self,
        payload: object,
        presenter: object,
        *,
        language: str = "ko",
    ) -> tuple[list[str], list[str]]:
        previous_chart_paths = [path for path in self.chart_paths_text.splitlines() if path]
        if isinstance(payload, list):
            self.results_model = payload
        elif payload is None:
            self.results_model = []
        else:
            self.results_model = [payload]

        binding = self._bind(presenter, language)
        self._apply_binding(binding)
        return previous_chart_paths, list(binding.chart_paths)

    def rebind(self, presenter: object, *, language: str = "ko") -> None:
        binding = self._bind(presenter, language)
        self._apply_binding(binding)

    def _bind(self, presenter: object, language: str) -> object:
        if language == "ko":
            return presenter.bind(self.results_model)
        return presenter.bind(self.results_model, language=language)

    def _apply_binding(self, binding: object) -> None:
        self.summary_text = binding.summary_text
        self.table_text = binding.table_text
        self.notes_text = binding.notes_text
        self.chart_paths_text = binding.chart_paths_text
        self.chart_source_text = binding.chart_source_text
