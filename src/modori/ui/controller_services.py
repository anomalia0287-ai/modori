from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modori.knowledge import Library
from modori.ui.analysis_editor import AnalysisSelectionEditor
from modori.ui.chart_assets import ChartAssetRenderer
from modori.ui.contracts import ImportOptions, ReportExportOptions
from modori.ui.data_transform import DataTransformEditor
from modori.ui.data_session import DataSessionLoader, ImportSessionPipelineFactory
from modori.ui.explanation_service import ExplanationService
from modori.ui.explanations import ExplanationPresenter
from modori.ui.import_flow import UiImportFlow
from modori.ui.metadata_editor import VariableMetadataEditor
from modori.ui.pipeline_ops import PipelineOperations
from modori.recommendations import RecommendationService
from modori.ui.report_export import ReportExportService
from modori.ui.result_binding import ResultBindingPresenter
from modori.ui.result_validation import ResultPayloadValidator
from modori.ui.run_validation import RunConfigurationValidator
from modori.research_os import Language
from modori.ui.research_flow_controller import (
    ResearchFlowPipelineAccess,
    ResearchFlowRuntime,
    build_default_research_flow_runtime,
)


PipelineFactory = Callable[[Path, ImportOptions], object]
ReportExporter = Callable[[object, ReportExportOptions], str | Path]


@dataclass
class UiControllerServices:
    pipeline_ops: PipelineOperations
    chart_renderer: ChartAssetRenderer
    analysis_editor: AnalysisSelectionEditor
    metadata_editor: VariableMetadataEditor
    data_transform_editor: DataTransformEditor
    data_session_loader: DataSessionLoader
    import_flow: UiImportFlow
    report_export_service: ReportExportService
    result_binding_presenter: ResultBindingPresenter
    result_payload_validator: ResultPayloadValidator
    explanation_service: ExplanationService
    explanation_presenter: ExplanationPresenter
    recommendation_service: RecommendationService
    run_validator: RunConfigurationValidator

    @classmethod
    def build(
        cls,
        *,
        pipeline: object | None,
        pipeline_factory: PipelineFactory | None,
        mode_provider: Callable[[], str],
        library: Library | None,
    ) -> UiControllerServices:
        chart_renderer = ChartAssetRenderer()
        pipeline_ops = PipelineOperations(pipeline, chart_renderer=chart_renderer)
        return cls(
            pipeline_ops=pipeline_ops,
            chart_renderer=chart_renderer,
            analysis_editor=AnalysisSelectionEditor(pipeline_ops),
            metadata_editor=VariableMetadataEditor(pipeline_ops),
            data_transform_editor=DataTransformEditor(pipeline_ops),
            data_session_loader=DataSessionLoader(
                pipeline_factory or ImportSessionPipelineFactory()
            ),
            import_flow=UiImportFlow(),
            report_export_service=ReportExportService(),
            result_binding_presenter=ResultBindingPresenter(),
            result_payload_validator=ResultPayloadValidator(),
            explanation_service=ExplanationService(
                library_factory=(lambda: library) if library is not None else None
            ),
            explanation_presenter=ExplanationPresenter(),
            recommendation_service=RecommendationService(),
            run_validator=RunConfigurationValidator(),
        )

    def replace_pipeline(self, pipeline: object | None) -> None:
        self.pipeline_ops = PipelineOperations(
            pipeline,
            chart_renderer=self.chart_renderer,
        )
        self.analysis_editor = AnalysisSelectionEditor(self.pipeline_ops)
        self.metadata_editor = VariableMetadataEditor(self.pipeline_ops)
        self.data_transform_editor = DataTransformEditor(self.pipeline_ops)

    def build_research_flow_runtime(
        self,
        *,
        pipeline_version_provider: Callable[[], int],
    ) -> ResearchFlowRuntime:
        return build_default_research_flow_runtime(
            pipeline_access=ResearchFlowPipelineAccess(lambda: self.pipeline_ops),
            pipeline_version_provider=pipeline_version_provider,
            language=Language.KO,
        )
