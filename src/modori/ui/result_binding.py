from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl

from modori.cache import cache_dir
from modori.path_policy import is_link_or_junction


@dataclass(frozen=True)
class ResultBindingState:
    summary_text: str
    table_text: str
    notes_text: str
    chart_paths_text: str
    chart_source_text: str
    chart_paths: list[str]


class ResultBindingPresenter:
    def bind(self, results: list[Any]) -> ResultBindingState:
        chart_paths = self._chart_paths(results)
        chart_paths_text = "\n".join(chart_paths)
        return ResultBindingState(
            summary_text=self._summarize(results),
            table_text=self._format_tables(results),
            notes_text=self._format_notes(results),
            chart_paths_text=chart_paths_text,
            chart_source_text=self._format_chart_source(chart_paths),
            chart_paths=chart_paths,
        )

    @staticmethod
    def cleanup_obsolete_chart_files(old_paths: list[str], new_paths: list[str]) -> None:
        obsolete = set(old_paths) - set(new_paths)
        if not obsolete:
            return
        try:
            root = (cache_dir() / "charts").resolve()
        except OSError:
            return
        if not root.exists() or not root.is_dir() or is_link_or_junction(root):
            return
        for text in obsolete:
            path = Path(text)
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved.suffix.lower() not in {".png", ".svg", ".eps"}:
                continue
            try:
                if resolved.is_file() and resolved.is_relative_to(root):
                    resolved.unlink()
            except OSError:
                continue

    @staticmethod
    def _summarize(results: list[Any]) -> str:
        summaries: list[str] = []
        for result in results:
            prose = getattr(result, "prose_ko", "")
            title = getattr(result, "title_ko", "")
            if title and prose:
                summaries.append(f"{title}\n{prose}")
            elif prose:
                summaries.append(str(prose))
        return "\n\n".join(summaries)

    @staticmethod
    def _format_tables(results: list[Any]) -> str:
        blocks: list[str] = []
        for result in results:
            for table in getattr(result, "tables", []):
                columns = [column.label for column in table.columns]
                lines = [table.caption_ko, "\t".join(columns)]
                lines.extend("\t".join(row) for row in table.rows)
                blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _format_notes(results: list[Any]) -> str:
        blocks: list[str] = []
        for result in results:
            for note in getattr(result, "notes", []):
                title = str(getattr(note, "title", "") or "알림")
                body = str(getattr(note, "body", "") or "")
                if body:
                    blocks.append(f"{title}: {body}")
        return "\n".join(blocks)

    @staticmethod
    def _chart_paths(results: list[Any]) -> list[str]:
        paths: list[str] = []
        for result in results:
            paths.extend(str(path) for path in getattr(result, "chart_paths", []))
        return paths

    @staticmethod
    def _format_chart_source(paths: list[str]) -> str:
        if not paths:
            return ""
        return QUrl.fromLocalFile(str(Path(paths[0]))).toString()
