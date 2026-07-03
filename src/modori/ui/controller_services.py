from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modori.knowledge import Library
from modori.ui.analysis_editor import AnalysisSelectionEditor
from modori.ui.contracts import ImportOptions, ReportExportOptions
from modori.ui.data_session import DataSessionLoader, ReferencePipelineFactory
from modori.ui.explanation_service import ExplanationService
from modori.ui.explanations import ExplanationPresenter
from modori.ui.import_flow import UiImportFlow
from modori.ui.metadata_editor import VariableMetadataEditor
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.recommendations import RecommendationService
from modori.ui.report_export import ReportExportService
from modori.ui.result_binding import ResultBindingPresenter


PipelineFactory = Callable[[Path, ImportOptions], object]
ReportExporter = Callable[[object, ReportExportOptions], str | Path]


@dataclass
class UiControllerServices:
    pipeline_ops: PipelineOperations
    analysis_editor: AnalysisSelectionEditor
    metadata_editor: VariableMetadataEditor
    data_session_loader: DataSessionLoader
    import_flow: UiImportFlow
    report_export_service: ReportExportService
    result_binding_presenter: ResultBindingPresenter
    explanation_service: ExplanationService
    explanation_presenter: ExplanationPresenter
    recommendation_service: RecommendationService

    @classmethod
    def build(
        cls,
        *,
        pipeline: object | None,
        pipeline_factory: PipelineFactory | None,
        mode_provider: Callable[[], str],
        library: Library | None,
    ) -> UiControllerServices:
        pipeline_ops = PipelineOperations(pipeline)
        return cls(
            pipeline_ops=pipeline_ops,
            analysis_editor=AnalysisSelectionEditor(pipeline_ops),
            metadata_editor=VariableMetadataEditor(pipeline_ops),
            data_session_loader=DataSessionLoader(
                pipeline_factory or ReferencePipelineFactory(mode_provider)
            ),
            import_flow=UiImportFlow(),
            report_export_service=ReportExportService(),
            result_binding_presenter=ResultBindingPresenter(),
            explanation_service=ExplanationService(
                library_factory=(lambda: library) if library is not None else None
            ),
            explanation_presenter=ExplanationPresenter(),
            recommendation_service=RecommendationService(),
        )

    def replace_pipeline(self, pipeline: object | None) -> None:
        self.pipeline_ops = PipelineOperations(pipeline)
        self.analysis_editor = AnalysisSelectionEditor(self.pipeline_ops)
        self.metadata_editor = VariableMetadataEditor(self.pipeline_ops)
