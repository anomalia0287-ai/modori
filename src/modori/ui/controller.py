from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from PySide6.QtCore import Property, QObject, Signal, Slot

from modori.knowledge import Library
from modori.ui.contracts import CommandResult, ExplainResult, ImportOptions, ReportExportOptions
from modori.ui.controller_services import UiControllerServices
from modori.ui.models import DataTableModel, VariableTableModel, variable_records_from_dataset
from modori.ui.patches import PatchValidationError, parse_step_patch
from modori.ui.paths import local_path_from_qml
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.pipeline_state import UiPipelineState
from modori.ui.result_state import UiResultState
from modori.ui.run_tracker import UiRunTracker
from modori.ui.session import UiSessionState
from modori.ui.settings import UiSettingsStore
from modori.ui.table_provider import DatasetTableProvider
from modori.ui.worker import EngineJobResult, SerializedEngineWorker


class UiController(QObject):
    stateChanged = Signal()
    workerResultReady = Signal(object)

    def __init__(
        self,
        *,
        pipeline: object | None = None,
        pipeline_factory: Callable[[Path, ImportOptions], object] | None = None,
        report_exporter: Callable[[object, ReportExportOptions], str | Path] | None = None,
        library: Library | None = None,
        reduce_effects: bool | None = None,
        settings_store: UiSettingsStore | None = None,
        worker: object | None = None,
    ) -> None:
        super().__init__()
        self.pipeline = pipeline
        self._services = UiControllerServices.build(
            pipeline=pipeline,
            pipeline_factory=pipeline_factory,
            mode_provider=lambda: self.mode,
            library=library,
        )
        self._report_exporter = report_exporter
        self._settings_store = settings_store or UiSettingsStore()
        self._session = UiSessionState(
            self._settings_store,
            reduce_effects_override=reduce_effects,
        )
        self._mode = "guided"
        self._last_error = ""
        self._result_state = UiResultState()
        self._report_path = ""
        self._pipeline_state = UiPipelineState.initial(
            self._services.pipeline_ops,
            status="empty" if pipeline is None else "ready",
        )
        self.stepsModel = self._pipeline_state.steps_model
        self._data_model = None
        self._variable_model = None
        self.resultsModel: list[Any] = self._result_state.results_model
        self._run_tracker = UiRunTracker()
        self._worker = worker or SerializedEngineWorker()
        self.workerResultReady.connect(self.apply_worker_result)

    @property
    def pipeline_version(self) -> int:
        return self._pipeline_state.pipeline_version

    @Property(str, notify=stateChanged)
    def mode(self) -> str:
        return self._mode

    @Property(bool, notify=stateChanged)
    def reduceEffects(self) -> bool:
        return self._session.reduce_effects

    @Property(str, notify=stateChanged)
    def status(self) -> str:
        return self._pipeline_state.status

    @Property(bool, notify=stateChanged)
    def stale(self) -> bool:
        return self._pipeline_state.stale

    @Property(str, notify=stateChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, notify=stateChanged)
    def resultSummary(self) -> str:
        return self._result_state.summary_text

    @Property(str, notify=stateChanged)
    def resultTableText(self) -> str:
        return self._result_state.table_text

    @Property(str, notify=stateChanged)
    def resultNotesText(self) -> str:
        return self._result_state.notes_text

    @Property(str, notify=stateChanged)
    def chartPathsText(self) -> str:
        return self._result_state.chart_paths_text

    @Property(str, notify=stateChanged)
    def chartSourceText(self) -> str:
        return self._result_state.chart_source_text

    @Property(str, notify=stateChanged)
    def reportPath(self) -> str:
        return self._report_path

    @Property(str, notify=stateChanged)
    def importPreviewText(self) -> str:
        return self._services.import_flow.preview_text

    @Property(str, notify=stateChanged)
    def stepChainText(self) -> str:
        return self._pipeline_state.step_chain_text

    @Property(str, notify=stateChanged)
    def recentFilesText(self) -> str:
        return self._session.recent_files_text

    @Property(bool, notify=stateChanged)
    def recentFilesEnabled(self) -> bool:
        return self._session.recent_files_enabled

    @Property(QObject, notify=stateChanged)
    def dataModel(self) -> QObject | None:
        return self._data_model

    @Property(QObject, notify=stateChanged)
    def variableModel(self) -> QObject | None:
        return self._variable_model

    def setMode(self, mode: str) -> CommandResult:
        if mode not in {"guided", "standard"}:
            return CommandResult(
                ok=False,
                message_ko="지원하지 않는 모드입니다.",
                error_code="invalid_mode",
                pipeline_version=self._pipeline_state.pipeline_version,
            )
        self._mode = mode
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko="모드가 변경되었습니다.",
            pipeline_version=self._pipeline_state.pipeline_version,
        )

    @Slot(bool, result=bool)
    def setReduceEffects(self, enabled: bool) -> bool:
        self._session.set_reduce_effects(enabled)
        self.stateChanged.emit()
        return True

    @Slot(str, result=bool)
    def chooseMode(self, mode: str) -> bool:
        return self.setMode(mode).ok

    def updateStep(self, step_id: str, patch: Mapping[str, Any]) -> CommandResult:
        kind = patch.get("kind") if isinstance(patch, Mapping) else None
        if not isinstance(kind, str):
            return CommandResult(
                ok=False,
                message_ko="패치 종류가 필요합니다.",
                error_code="invalid_step_patch",
                pipeline_version=self._pipeline_state.pipeline_version,
            )
        try:
            typed_patch = parse_step_patch(
                kind,
                patch,
                variable_keys=self._services.pipeline_ops.variable_keys(),
            )
        except PatchValidationError as exc:
            return CommandResult(
                ok=False,
                message_ko=exc.message_ko,
                error_code=exc.error_code,
                pipeline_version=self._pipeline_state.pipeline_version,
            )

        self._services.pipeline_ops.edit_params_if_available(step_id, typed_patch)

        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self.stepsModel = self._pipeline_state.steps_model
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko="단계가 변경되었습니다.",
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=[step_id],
        )

    def openDataFile(self, path: str | Path, options: ImportOptions) -> CommandResult:
        load_result = self._services.data_session_loader.open(
            path,
            options,
            pipeline_ops=self._services.pipeline_ops,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        if not load_result.command.ok:
            return load_result.command

        self.pipeline = load_result.pipeline
        self._services.replace_pipeline(load_result.pipeline)
        if load_result.path is not None:
            self._remember_recent_file(load_result.path)
        self._pipeline_state.mark_pipeline_replaced(self._services.pipeline_ops)
        self.stepsModel = self._pipeline_state.steps_model
        self._result_state.clear()
        self.resultsModel = self._result_state.results_model
        self._data_model = None
        self._variable_model = None
        self._last_error = ""
        self._report_path = ""
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=load_result.command.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=load_result.command.changed_step_ids,
        )

    @Slot(str, result=bool)
    def openDataFilePath(self, path: str) -> bool:
        local_path = local_path_from_qml(path)
        result = self.openDataFile(local_path, ImportOptions(confirm_new_session=True))
        return result.ok

    @Slot(str, result=bool)
    def previewDataFilePath(self, path: str) -> bool:
        local_path = local_path_from_qml(path)
        ok = self._services.import_flow.preview(local_path)
        self.stateChanged.emit()
        return ok

    @Slot(result=bool)
    def confirmPendingImport(self) -> bool:
        pending_path = self._services.import_flow.require_pending_path()
        if pending_path is None:
            self.stateChanged.emit()
            return False
        result = self.openDataFile(
            pending_path,
            ImportOptions(confirm_new_session=True),
        )
        return result.ok

    @Slot(bool, result=bool)
    def setRecentFilesEnabled(self, enabled: bool) -> bool:
        self._session.set_recent_files_enabled(enabled)
        self.stateChanged.emit()
        return True

    def updateVariableMetadata(
        self,
        variable_key: str,
        patch: Mapping[str, Any],
    ) -> CommandResult:
        result = self._services.metadata_editor.update(
            str(variable_key),
            patch,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        if not result.ok:
            return result

        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )

    @Slot(str, str, result=bool)
    def changeVariableMeasure(self, variable_key: str, measure: str) -> bool:
        return self.updateVariableMetadata(variable_key, {"measure": measure}).ok

    def configureReliabilitySelection(self, item_keys_text: str) -> CommandResult:
        result = self._services.analysis_editor.reliability(
            item_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, result=bool)
    def configureReliabilityFromText(self, item_keys_text: str) -> bool:
        return self.configureReliabilitySelection(item_keys_text).ok

    def configureComparisonSelection(self, outcome_key: str, group_key: str) -> CommandResult:
        result = self._services.analysis_editor.comparison(
            outcome_key,
            group_key,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureComparisonFromText(self, outcome_key: str, group_key: str) -> bool:
        return self.configureComparisonSelection(outcome_key, group_key).ok

    def configureRegressionSelection(
        self,
        outcome_key: str,
        predictor_keys_text: str,
    ) -> CommandResult:
        result = self._services.analysis_editor.regression(
            outcome_key,
            predictor_keys_text,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        return self._apply_step_edit_result(result)

    @Slot(str, str, result=bool)
    def configureRegressionFromText(self, outcome_key: str, predictor_keys_text: str) -> bool:
        return self.configureRegressionSelection(outcome_key, predictor_keys_text).ok

    def rerun(self) -> CommandResult:
        if self.pipeline is None:
            return CommandResult(
                ok=False,
                message_ko="다시 실행할 분석이 없습니다.",
                error_code="no_pipeline",
                pipeline_version=self._pipeline_state.pipeline_version,
            )
        run_id = self._run_tracker.submit(
            worker=self._worker,
            pipeline_version=self._pipeline_state.pipeline_version,
            job=self._services.pipeline_ops.recompute_and_display_results,
            emit_result=self.workerResultReady.emit,
        )
        self._pipeline_state.mark_running()
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko="다시 실행을 시작했습니다.",
            run_id=run_id,
            pipeline_version=self._pipeline_state.pipeline_version,
        )

    @Slot(result=bool)
    def rerunNow(self) -> bool:
        return self.rerun().ok

    def exportReport(self, options: ReportExportOptions) -> CommandResult:
        exporter = self._report_exporter or self._export_report_from_pipeline
        result = self._services.report_export_service.export(
            pipeline=self.pipeline,
            options=options,
            exporter=exporter,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        if not result.ok:
            if result.error_code == "engine_error":
                self._last_error = result.message_ko
                self.stateChanged.emit()
            return result
        self._report_path = result.result_ids[0]
        self._last_error = ""
        self.stateChanged.emit()
        return result

    @Slot(result=bool)
    def exportReportNow(self) -> bool:
        return self.exportReport(ReportExportOptions(language="ko")).ok

    @Slot(str, bool, result=bool)
    def exportReportWithOptions(self, language: str, include_figures: bool) -> bool:
        return self.exportReportWithSelections(
            language,
            True,
            True,
            True,
            include_figures,
        )

    @Slot(str, bool, bool, bool, bool, result=bool)
    def exportReportWithSelections(
        self,
        language: str,
        include_reliability: bool,
        include_comparison: bool,
        include_regression: bool,
        include_figures: bool,
    ) -> bool:
        selected_language = "en" if language == "en" else "ko"
        return self.exportReport(
            ReportExportOptions(
                language=selected_language,
                include_reliability=bool(include_reliability),
                include_comparison=bool(include_comparison),
                include_regression=bool(include_regression),
                include_figures=bool(include_figures),
            )
        ).ok

    def explain(self, entity_key: str, language: str) -> ExplainResult:
        return self._services.explanation_service.explain(entity_key, language)

    @Slot(str, str, result=str)
    def explainPlainText(self, entity_key: str, language: str) -> str:
        result = self.explain(entity_key, language)
        if not result.ok:
            return result.message_ko
        return self._services.explanation_presenter.plain_text(
            title=result.title,
            content=result.content,
            fallback=result.message_ko,
        )

    @Slot(str, str, result=str)
    def explainRichText(self, entity_key: str, language: str) -> str:
        result = self.explain(entity_key, language)
        if not result.ok:
            return result.message_ko
        return self._services.explanation_presenter.rich_text(
            title=str(result.title),
            content=result.content,
            language=language,
            fallback=result.message_ko,
        )

    def apply_worker_result(self, result: EngineJobResult[Any]) -> bool:
        if not self._run_tracker.accepts(result, self._pipeline_state.pipeline_version):
            return False
        if not result.ok:
            self._pipeline_state.mark_error()
            self._last_error = result.message_ko
            self.stateChanged.emit()
            return True
        self._refresh_dataset_models()
        previous_chart_paths, chart_paths = self._result_state.bind_payload(
            result.payload,
            self._services.result_binding_presenter,
        )
        self.resultsModel = self._result_state.results_model
        self._services.result_binding_presenter.cleanup_obsolete_chart_files(
            previous_chart_paths,
            chart_paths,
        )
        self._pipeline_state.mark_ready_fresh()
        self._last_error = ""
        self.stateChanged.emit()
        return True

    def waitForLastRun(self, timeout: float | None = None) -> bool:
        result = self._run_tracker.wait(timeout=timeout)
        if result is None:
            return False
        return self.apply_worker_result(result)

    def _apply_step_edit_result(self, result: CommandResult) -> CommandResult:
        if not result.ok:
            self._last_error = result.message_ko
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self._last_error = ""
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )

    def _command_error(self, message_ko: str, error_code: str) -> CommandResult:
        self._last_error = message_ko
        self._pipeline_state.mark_ready_unless_empty()
        self.stateChanged.emit()
        return CommandResult(
            ok=False,
            message_ko=message_ko,
            error_code=error_code,
            pipeline_version=self._pipeline_state.pipeline_version,
        )

    def _export_report_from_pipeline(
        self,
        pipeline: object,
        options: ReportExportOptions,
    ) -> Path:
        return PipelineOperations(pipeline).export_report(options)

    def _refresh_dataset_models(self) -> None:
        current_dataset = self._services.pipeline_ops.current_dataset()
        if current_dataset is None:
            return
        self._data_model = DataTableModel(DatasetTableProvider(current_dataset))
        self._variable_model = VariableTableModel(variable_records_from_dataset(current_dataset))

    def _remember_recent_file(self, path: Path) -> None:
        self._session.remember_recent_file(path)

