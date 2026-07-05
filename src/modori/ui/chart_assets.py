from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from modori.cache import cache_dir
from modori.results import ChartSpec
from modori.steps.reporting import render_chart as default_render_chart


CHART_RENDER_ERROR_KO = "자동 그래프를 생성하지 못했습니다."
ChartRenderCallable = Callable[[ChartSpec, str | Path, str | None], str | list[str]]


@dataclass(frozen=True)
class ChartAssetResult:
    paths: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ChartAssetRenderer:
    chart_dir: Path | None = None
    render_chart: ChartRenderCallable = default_render_chart

    def render_for_display(
        self,
        *,
        result_id: str,
        chart_spec: ChartSpec | None,
    ) -> ChartAssetResult:
        if chart_spec is None:
            return ChartAssetResult()

        output_path = self._display_chart_path(result_id)
        try:
            rendered = self.render_chart(chart_spec, output_path, None)
        except Exception:
            self._remove_partial(output_path)
            return ChartAssetResult(error=CHART_RENDER_ERROR_KO)

        paths = [rendered] if isinstance(rendered, str) else list(rendered)
        display_paths = [
            str(path)
            for path in (Path(item) for item in paths)
            if path.suffix.lower() == ".png" and path.exists()
        ]
        if not display_paths:
            return ChartAssetResult(error=CHART_RENDER_ERROR_KO)
        return ChartAssetResult(paths=display_paths)

    def _display_chart_path(self, result_id: str) -> Path:
        chart_dir = self.chart_dir or (cache_dir() / "charts")
        chart_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{_safe_chart_name(result_id)}-{uuid.uuid4().hex[:8]}"
        return chart_dir / f"{stem}.png"

    @staticmethod
    def _remove_partial(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _safe_chart_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value).strip("._-")
    return safe or "chart"
