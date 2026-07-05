from __future__ import annotations

from pathlib import Path

from modori.results import ChartSpec
from modori.ui.chart_assets import ChartAssetRenderer


def test_chart_asset_renderer_writes_display_png_under_cache_with_injected_renderer(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("MODORI_CACHE_DIR", str(tmp_path / "cache"))
    calls: list[tuple[ChartSpec, Path, object]] = []

    def fake_render_chart(spec: ChartSpec, output_path: str | Path, key: str | None = None):
        path = Path(output_path)
        calls.append((spec, path, key))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        return str(path)

    spec = ChartSpec(
        type="horizontal_bar",
        title="Corrected item-total correlations",
        data={"values": {"q1": 0.42}},
        x_label="Correlation",
        y_label="Item",
    )

    result = ChartAssetRenderer(render_chart=fake_render_chart).render_for_display(
        result_id="reliability:job sat",
        chart_spec=spec,
    )

    assert len(result.paths) == 1
    assert result.error is None
    chart_path = Path(result.paths[0])
    assert chart_path.parent == tmp_path / "cache" / "charts"
    assert chart_path.suffix == ".png"
    assert "reliability_job_sat" in chart_path.stem
    assert chart_path.read_bytes() == b"png"
    assert calls == [(spec, chart_path, None)]


def test_chart_asset_renderer_returns_error_without_raising_when_render_fails(
    tmp_path,
) -> None:
    def failing_render_chart(
        spec: ChartSpec,
        output_path: str | Path,
        key: str | None = None,
    ):
        raise ValueError("unsupported")

    spec = ChartSpec(
        type="unsupported",
        title="Unsupported",
        data={},
        x_label="x",
        y_label="y",
    )

    result = ChartAssetRenderer(
        chart_dir=tmp_path / "charts",
        render_chart=failing_render_chart,
    ).render_for_display(
        result_id="broken",
        chart_spec=spec,
    )

    assert result.paths == []
    assert result.error == "자동 그래프를 생성하지 못했습니다."
