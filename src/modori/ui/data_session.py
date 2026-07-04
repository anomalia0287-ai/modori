from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modori.ui.contracts import CommandResult, ImportOptions
from modori.ui.service_contracts import DataSessionPipelineOps
from modori.core import Dataset, Pipeline
from modori.steps import ImportStep
from modori.workflow import AnalysisPreferences, build_reference_slice_pipeline


PipelineFactory = Callable[[Path, ImportOptions], object]


@dataclass(frozen=True)
class DataSessionLoadResult:
    command: CommandResult
    pipeline: object | None = None
    path: Path | None = None


class ReferencePipelineFactory:
    def __init__(self, mode_provider: Callable[[], str]) -> None:
        self._mode_provider = mode_provider

    def __call__(self, path: Path, options: ImportOptions) -> object:
        _ = options
        return build_reference_slice_pipeline(
            data_path=path,
            output_dir=path.parent / "modori-output",
            mode=self._mode_provider(),
            preferences=AnalysisPreferences(),
        )


class ImportSessionPipelineFactory:
    def __call__(self, path: Path, options: ImportOptions) -> object:
        _ = options
        pipeline = Pipeline(Dataset.empty())
        pipeline.add(
            ImportStep(
                id="import",
                title="Import data",
                params={
                    "path": str(path),
                    "file_type": path.suffix.lower().lstrip("."),
                },
            )
        )
        pipeline.recompute(dirty_from="import")
        return pipeline


class DataSessionLoader:
    def __init__(self, pipeline_factory: PipelineFactory) -> None:
        self._pipeline_factory = pipeline_factory

    def open(
        self,
        path: str | Path,
        options: ImportOptions,
        *,
        pipeline_ops: DataSessionPipelineOps,
        pipeline_version: int,
    ) -> DataSessionLoadResult:
        data_path = Path(path)
        if pipeline_ops.has_downstream_steps() and not options.confirm_new_session:
            return DataSessionLoadResult(
                command=CommandResult(
                    ok=False,
                    message_ko="새 데이터 파일을 열면 현재 분석 단계가 초기화됩니다.",
                    error_code="confirmation_required",
                    pipeline_version=pipeline_version,
                )
            )
        try:
            new_pipeline = self._pipeline_factory(data_path, options)
        except Exception:
            return DataSessionLoadResult(
                command=CommandResult(
                    ok=False,
                    message_ko="데이터 파일을 가져오지 못했습니다.",
                    error_code="engine_error",
                    pipeline_version=pipeline_version,
                )
            )
        return DataSessionLoadResult(
            command=CommandResult(
                ok=True,
                message_ko="데이터 파일을 가져왔습니다.",
                pipeline_version=pipeline_version,
                changed_step_ids=["import"],
            ),
            pipeline=new_pipeline,
            path=data_path,
        )
