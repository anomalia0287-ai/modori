from __future__ import annotations

from pathlib import Path

from modori.ui.contracts import ImportOptions
from modori.ui.data_session import DataSessionLoader, ImportSessionPipelineFactory


class FakePipelineOps:
    def __init__(self, *, has_downstream_steps: bool) -> None:
        self._has_downstream_steps = has_downstream_steps

    def has_downstream_steps(self) -> bool:
        return self._has_downstream_steps


class FakePipeline:
    marker = "pipeline"


def test_data_session_loader_requires_confirmation_before_replacing_analyzed_session(
    tmp_path,
) -> None:
    calls = []
    loader = DataSessionLoader(
        pipeline_factory=lambda path, options: calls.append((path, options))
    )

    result = loader.open(
        tmp_path / "data.csv",
        ImportOptions(confirm_new_session=False),
        pipeline_ops=FakePipelineOps(has_downstream_steps=True),
        pipeline_version=7,
    )

    assert result.command.ok is False
    assert result.command.error_code == "confirmation_required"
    assert result.command.pipeline_version == 7
    assert result.pipeline is None
    assert calls == []


def test_data_session_loader_maps_factory_failure_without_replacing_pipeline(tmp_path) -> None:
    def factory(path: Path, options: ImportOptions) -> object:
        raise ValueError("cannot parse")

    result = DataSessionLoader(factory).open(
        tmp_path / "bad.csv",
        ImportOptions(confirm_new_session=True),
        pipeline_ops=FakePipelineOps(has_downstream_steps=True),
        pipeline_version=3,
    )

    assert result.command.ok is False
    assert result.command.error_code == "engine_error"
    assert result.command.pipeline_version == 3
    assert result.pipeline is None


def test_data_session_loader_returns_replacement_pipeline_on_success(tmp_path) -> None:
    pipeline = FakePipeline()
    data_path = tmp_path / "survey.csv"

    result = DataSessionLoader(lambda path, options: pipeline).open(
        data_path,
        ImportOptions(confirm_new_session=True),
        pipeline_ops=FakePipelineOps(has_downstream_steps=False),
        pipeline_version=2,
    )

    assert result.command.ok is True
    assert result.command.message_ko == "데이터 파일을 가져왔습니다."
    assert result.command.changed_step_ids == ["import"]
    assert result.command.pipeline_version == 2
    assert result.pipeline is pipeline
    assert result.path == data_path


def test_import_session_pipeline_factory_persists_table_layout_options(tmp_path) -> None:
    data_path = tmp_path / "manual-layout.csv"
    data_path.write_text(
        "\n".join(
            [
                "다운로드 조건,2026-07-06",
                "이 행은 표가 아닙니다,확인용",
                "city,value",
                "Seoul,10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    pipeline = ImportSessionPipelineFactory()(
        data_path,
        ImportOptions(
            confirm_new_session=True,
            table_layout={
                "header_row_index": 2,
                "header_row_count": 1,
            },
        ),
    )

    import_step = pipeline.steps[0]
    assert import_step.params["table_layout"] == {
        "header_row_index": 2,
        "header_row_count": 1,
    }
    assert pipeline.current_dataset.df.columns.tolist() == ["city", "value"]


def test_import_session_pipeline_factory_persists_aggregate_row_option(tmp_path) -> None:
    data_path = tmp_path / "aggregate-row.csv"
    data_path.write_text("지역,인구\n합 계,300\n종로구,100\n", encoding="utf-8")

    pipeline = ImportSessionPipelineFactory()(
        data_path,
        ImportOptions(confirm_new_session=True, drop_aggregate_rows=True),
    )

    import_step = pipeline.steps[0]
    assert import_step.params["drop_aggregate_rows"] is True
    assert pipeline.current_dataset.df.to_dict(orient="records") == [{"지역": "종로구", "인구": 100}]
