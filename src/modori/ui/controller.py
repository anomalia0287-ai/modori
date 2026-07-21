from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Mapping

from PySide6.QtCore import Property, QObject, Signal, Slot

from modori.knowledge import Library
from modori.research_flow import PassportBoundPreparation
from modori.research_os import Language as ResearchLanguage
from modori.ui.analysis_selection_controller import AnalysisSelectionControllerMixin
from modori.ui.contracts import (
    CommandResult,
    ControllerMode,
    DisplayResult,
    ExplainResult,
    ImportOptions,
    ReportExportOptions,
)
from modori.ui.controller_services import UiControllerServices
from modori.ui.data_transform_controller import DataTransformControllerMixin
from modori.ui.import_layout_controller import ImportLayoutControllerMixin
from modori.ui.importing import review_rows
from modori.ui.localization import localize_message
from modori.ui.localization_controller import (
    UiLocalizationControllerMixin,
    localized_step_chain,
)
from modori.value_clustering import unification_suggestions
from modori.value_inventory import value_recode_inventory
from modori.ui.patches import PatchValidationError, parse_step_patch
from modori.ui.paths import local_path_from_qml
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.pipeline_state import UiPipelineState
from modori.ui.preview_models import models_for_dataset
from modori.ui.recommendation_controller import (
    RecommendationControllerMixin,
    empty_recommendation_state,
)
from modori.ui.research_flow_controller import ResearchFlowController
from modori.ui.research_preparation_editor import ResearchPreparationEditor
from modori.ui.result_state import UiResultState
from modori.ui.report_export_controller import ReportExportControllerMixin
from modori.ui.run_tracker import UiRunTracker
from modori.ui.selection_provenance_controller import SelectionProvenanceControllerMixin
from modori.ui.session import UiSessionState
from modori.ui.settings import UiSettingsStore
from modori.ui.worker import EngineJobResult, SerializedEngineWorker


_RECONFIRMATION_ERROR_CODE = "experimental_confirmation_required"
_RECONFIRMATION_RUN_MESSAGE = (
    "변경된 데이터 구성을 다시 확인하거나 분석 방법을 직접 구성해 주세요."
)
_RECONFIRMATION_REPORT_MESSAGE = (
    "변경된 데이터 구성을 다시 확인한 뒤 보고서를 저장해 주세요."
)


def export_report_from_pipeline(
    pipeline: object,
    options: ReportExportOptions,
) -> Path:
    return PipelineOperations(pipeline).export_report(options)


def _worker_boundaries(
    owner: object,
    worker: object | None,
) -> tuple[object, ResearchFlowController]:
    bound_worker = worker or SerializedEngineWorker()
    owner.workerResultReady.connect(owner.apply_worker_result)
    runtime = owner._services.build_research_flow_runtime(
        pipeline_version_provider=lambda: owner.pipeline_version
    )
    preparation_editor = ResearchPreparationEditor(
        pipeline_ops_provider=lambda: owner._services.pipeline_ops,
        version_provider=lambda: owner.pipeline_version,
        current_dataset_fingerprint=runtime.current_dataset_fingerprint,
        commit_pipeline_change=lambda preparation: _commit_research_preparation(
            owner,
            preparation,
        ),
    )
    flow = ResearchFlowController(
        runtime=runtime,
        worker=bound_worker,
        pipeline_version_provider=lambda: owner.pipeline_version,
        mode_change_request=lambda mode: owner.setMode(mode).ok,
        initial_mode=ControllerMode(owner._mode),
        language=ResearchLanguage.KO,
        preparation_editor=preparation_editor,
        confirmation_published=owner.stateChanged.emit,
    )
    owner.stateChanged.connect(flow.syncPipelineVersion)
    return bound_worker, flow


def _commit_research_preparation(
    owner: object,
    preparation: PassportBoundPreparation,
) -> int:
    owner._pipeline_state.mark_step_changed(
        owner._services.pipeline_ops,
        fallback=owner.stepsModel,
    )
    owner.stepsModel = owner._pipeline_state.steps_model
    owner._result_state.clear()
    owner.resultsModel = owner._result_state.results_model
    owner._session.mark_research_os_assisted(preparation.preparation_digest)
    owner._last_error = ""
    owner._last_message = (
        "분석 설정을 확정했습니다. 실행 버튼을 눌러야 계산이 시작됩니다."
    )
    return owner.pipeline_version


class UiController(
    QObject,
    UiLocalizationControllerMixin,
    RecommendationControllerMixin,
    AnalysisSelectionControllerMixin,
    DataTransformControllerMixin,
    ImportLayoutControllerMixin,
    ReportExportControllerMixin,
    SelectionProvenanceControllerMixin,
):
    stateChanged = Signal()
    workerResultReady = Signal(object)

    def __init__(
        self,
        *,
        pipeline: object | None = None,
        pipeline_factory: Callable[[Path, ImportOptions], object] | None = None,
        report_exporter: Callable[[object, ReportExportOptions], str | Path]
        | None = None,
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
        self._session = UiSessionState(
            settings_store or UiSettingsStore(),
            reduce_effects_override=reduce_effects,
        )
        self._mode = "standard"
        self._ui_language = "ko"
        self._last_error = ""
        self._last_message = ""
        self._result_state = UiResultState()
        self._report_path = ""
        self._pipeline_state = UiPipelineState.initial(
            self._services.pipeline_ops,
            status="empty" if pipeline is None else "ready",
        )
        self.stepsModel = self._pipeline_state.steps_model
        self._data_model = None
        self._variable_model = None
        self._data_view_notice = ""
        self._recommendation_state = empty_recommendation_state()
        self._recommendation_preparation = None
        self._experimental_recommendation_confirmed = False
        self.resultsModel: list[Any] = self._result_state.results_model
        self._run_tracker = UiRunTracker()
        self._worker, self._research_flow = _worker_boundaries(self, worker)

    @property
    def pipeline_version(self) -> int:
        return self._pipeline_state.pipeline_version

    @Property(QObject, constant=True)
    def researchFlow(self) -> QObject:
        return self._research_flow

    @Property(str, notify=stateChanged)
    def mode(self) -> str:
        return self._mode

    @Property(bool, notify=stateChanged)
    def reduceEffects(self) -> bool:
        return self._session.reduce_effects

    @Property(bool, notify=stateChanged)
    def explainModeEnabled(self) -> bool:
        return self._session.explain_mode_enabled

    @Property(bool, notify=stateChanged)
    def canExplainCronbachAlphaResult(self) -> bool:
        return any(
            isinstance(result, DisplayResult) and result.kind == "reliability"
            for result in self._result_state.results_model
        )

    @Property(str, notify=stateChanged)
    def status(self) -> str:
        return self._pipeline_state.status

    @Property(str, notify=stateChanged)
    def analysisSelectionOrigin(self) -> str:
        return self._session.selection_provenance

    @Property(bool, notify=stateChanged)
    def canRerun(self) -> bool:
        if self.status in {"empty", "running"}:
            return False
        if self._session.selection_confirmation_required:
            return False
        validation = self._services.run_validator.validate(self._services.pipeline_ops)
        return validation.ok

    @Property(bool, notify=stateChanged)
    def selectionConfirmationRequired(self) -> bool:
        return self._session.selection_confirmation_required

    @Property(bool, notify=stateChanged)
    def stale(self) -> bool:
        return self._pipeline_state.stale

    @Property(str, notify=stateChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, notify=stateChanged)
    def lastMessage(self) -> str:
        return self._last_message

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

    @Property("QVariantList", notify=stateChanged)
    def importReviewRows(self) -> list:
        return review_rows(
            self._services.import_flow.table_preview,
            language=self._ui_language,
        )

    @Property("QVariantList", notify=stateChanged)
    def importColumnRows(self) -> list:
        return self._services.import_flow.column_rows()

    @Property("QVariantList", notify=stateChanged)
    def valueUnificationSuggestions(self) -> list:
        return unification_suggestions(self._services.pipeline_ops.current_dataset())

    @Property("QVariantList", notify=stateChanged)
    def valueRecodeInventory(self) -> list:
        return value_recode_inventory(
            self._services.pipeline_ops.current_dataset(),
            existing_steps=self._services.pipeline_ops.steps(),
        )

    @Property(str, notify=stateChanged)
    def stepChainText(self) -> str:
        return self._pipeline_state.step_chain_text

    @Property(str, notify=stateChanged)
    def stepChainDisplayText(self) -> str:
        return localized_step_chain(self._pipeline_state.step_chain_text, "ko")

    @Property(str, notify=stateChanged)
    def recentFilesText(self) -> str:
        return self._session.recent_files_text

    @Property(QObject, notify=stateChanged)
    def recentFilesModel(self) -> QObject:
        return self._session.recent_files_model

    @Property(bool, notify=stateChanged)
    def recentFilesEnabled(self) -> bool:
        return self._session.recent_files_enabled

    @Property(str, notify=stateChanged)
    def dataViewNotice(self) -> str:
        return self._data_view_notice

    @Property(QObject, notify=stateChanged)
    def dataModel(self) -> QObject | None:
        return self._data_model

    @Property(QObject, notify=stateChanged)
    def variableModel(self) -> QObject | None:
        return self._variable_model

    def setMode(self, mode: str) -> CommandResult:
        if mode not in {"guided", "standard"}:
            return self._command_error("지원하지 않는 모드입니다.", "invalid_mode")
        changed = mode != self._mode
        self._mode = mode
        if changed:
            self._research_flow.adoptMode(mode)
        if changed:
            self._refresh_recommendations()
        self._last_error = ""
        self._last_message = "모드가 변경되었습니다."
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

    @Slot(bool, result=bool)
    def setExplainModeEnabled(self, enabled: bool) -> bool:
        self._session.set_explain_mode_enabled(enabled)
        self.stateChanged.emit()
        return True

    @Slot(str, result=bool)
    def chooseMode(self, mode: str) -> bool:
        return self.setMode(mode).ok

    def updateStep(self, step_id: str, patch: Mapping[str, Any]) -> CommandResult:
        kind = patch.get("kind") if isinstance(patch, Mapping) else None
        if not isinstance(kind, str):
            return self._command_error("패치 종류가 필요합니다.", "invalid_step_patch")
        try:
            typed_patch = parse_step_patch(
                kind,
                patch,
                variable_keys=self._services.pipeline_ops.variable_keys(),
            )
        except PatchValidationError as exc:
            return self._command_error(exc.message_ko, exc.error_code)

        self._services.pipeline_ops.edit_params_if_available(step_id, typed_patch)

        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self.stepsModel = self._pipeline_state.steps_model
        if kind in {"reliability", "comparison", "regression"}:
            self._session.clear_selection_provenance()
        elif kind in {"variable_metadata", "data_cell"}:
            self._session.invalidate_selection_confirmation()
        self._last_error = ""
        self._last_message = "단계가 변경되었습니다."
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
            self._clear_recommendations()
            self._last_error = load_result.command.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return load_result.command

        self.pipeline = load_result.pipeline
        self._services.replace_pipeline(load_result.pipeline)
        self._session.clear_selection_provenance()
        self._refresh_recommendations()
        if load_result.path is not None:
            self._session.remember_recent_file(load_result.path)
        self._pipeline_state.mark_pipeline_replaced(self._services.pipeline_ops)
        self.stepsModel = self._pipeline_state.steps_model
        self._result_state.clear()
        self.resultsModel = self._result_state.results_model
        self._data_model = None
        self._variable_model = None
        self._data_view_notice = ""
        if load_result.path is not None:
            self._bind_import_preview_models(load_result.path, options)
        self._last_error = ""
        self._last_message = load_result.command.message_ko
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

    @Slot(int, result=bool)
    def openRecentFileAt(self, index: int) -> bool:
        recent_files = self._session.recent_files
        if index < 0 or index >= len(recent_files):
            return self._command_error(
                "최근 파일을 찾을 수 없습니다.", "recent_file_missing"
            ).ok
        recent_path = Path(recent_files[index])
        if not recent_path.exists():
            return self._command_error(
                "최근 파일을 찾을 수 없습니다.", "recent_file_missing"
            ).ok
        return self.openDataFile(
            recent_path, ImportOptions(confirm_new_session=True)
        ).ok

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
            self._last_error = result.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result

        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self._session.invalidate_selection_confirmation()
        self._refresh_recommendations()
        self._last_error = ""
        self._last_message = result.message_ko
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )

    def rerun(self) -> CommandResult:
        if self.pipeline is None:
            return self._command_error("다시 실행할 분석이 없습니다.", "no_pipeline")
        if self._session.selection_confirmation_required:
            return self._command_error(
                _RECONFIRMATION_RUN_MESSAGE, _RECONFIRMATION_ERROR_CODE
            )
        validation = self._services.run_validator.validate(self._services.pipeline_ops)
        if not validation.ok:
            return self._command_error(
                validation.message_ko,
                validation.error_code or "invalid_run_configuration",
            )
        run_id = self._run_tracker.submit(
            worker=self._worker,
            pipeline_version=self._pipeline_state.pipeline_version,
            job=self._services.pipeline_ops.recompute_and_display_results,
            emit_result=self.workerResultReady.emit,
        )
        self._pipeline_state.mark_running()
        self._last_error = ""
        self._last_message = "다시 실행을 시작했습니다."
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
        if self._session.selection_confirmation_required:
            return self._command_error(
                _RECONFIRMATION_REPORT_MESSAGE, _RECONFIRMATION_ERROR_CODE
            )
        exporter = self._report_exporter or export_report_from_pipeline
        selection_origin = self._session.selection_provenance
        effective_options = replace(
            options,
            selection_provenance=selection_origin,
            selection_origin=selection_origin,
        )
        result = self._services.report_export_service.export(
            pipeline=self.pipeline,
            options=effective_options,
            exporter=exporter,
            pipeline_version=self._pipeline_state.pipeline_version,
        )
        if not result.ok:
            self._last_error = result.message_ko
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._report_path = result.result_ids[0]
        self._last_error = ""
        self._last_message = result.message_ko
        self.stateChanged.emit()
        return result

    @Slot(bool, result=bool)
    def markCurrentSelectionExperimental(self, assisted: bool) -> bool:
        if assisted:
            self._session.mark_experimental_candidate_assisted()
        else:
            self._session.clear_selection_provenance()
        self.stateChanged.emit()
        return True

    def explain(self, entity_key: str, language: str) -> ExplainResult:
        return self._services.explanation_service.explain(entity_key, language)

    @Slot(str, str, result=str)
    def explainPlainText(self, entity_key: str, language: str) -> str:
        result = self.explain(entity_key, language)
        if not result.ok:
            return localize_message(result.message_ko, language)
        return self._services.explanation_presenter.plain_text(
            title=result.title,
            content=result.content,
            fallback=result.message_ko,
        )

    @Slot(str, str, result=str)
    def explainRichText(self, entity_key: str, language: str) -> str:
        result = self.explain(entity_key, language)
        if not result.ok:
            return localize_message(result.message_ko, language)
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
            self._last_message = ""
            self.stateChanged.emit()
            return True
        validation = self._services.result_payload_validator.validate(result.payload)
        if not validation.ok:
            self._pipeline_state.mark_error()
            self._result_state.clear()
            self.resultsModel = self._result_state.results_model
            self._last_error = validation.message_ko
            self._last_message = ""
            self.stateChanged.emit()
            return True
        self._refresh_dataset_models()
        previous_chart_paths, chart_paths = self._result_state.bind_payload(
            result.payload,
            self._services.result_binding_presenter,
            language=self._ui_language,
        )
        self.resultsModel = self._result_state.results_model
        self._services.result_binding_presenter.cleanup_obsolete_chart_files(
            previous_chart_paths,
            chart_paths,
        )
        self._pipeline_state.mark_ready_fresh()
        self._last_error = ""
        self._last_message = "분석 결과가 업데이트되었습니다."
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
            self._last_message = ""
            self._pipeline_state.mark_ready_unless_empty()
            self.stateChanged.emit()
            return result
        self._pipeline_state.mark_step_changed(
            self._services.pipeline_ops,
            fallback=self.stepsModel,
        )
        self._last_error = ""
        self._last_message = result.message_ko
        self.stepsModel = self._pipeline_state.steps_model
        self._refresh_dataset_models()
        self._session.clear_selection_provenance()
        self.stateChanged.emit()
        return CommandResult(
            ok=True,
            message_ko=result.message_ko,
            pipeline_version=self._pipeline_state.pipeline_version,
            changed_step_ids=result.changed_step_ids,
        )

    def _command_error(self, message_ko: str, error_code: str) -> CommandResult:
        self._last_error = message_ko
        self._last_message = ""
        self._pipeline_state.mark_ready_unless_empty()
        self.stateChanged.emit()
        return CommandResult(
            ok=False,
            message_ko=message_ko,
            error_code=error_code,
            pipeline_version=self._pipeline_state.pipeline_version,
        )

    def _refresh_dataset_models(self) -> None:
        current_dataset = self._services.pipeline_ops.current_dataset()
        if current_dataset is None:
            return
        models = models_for_dataset(current_dataset, language=self._ui_language)
        self._data_model = models.data_model
        self._variable_model = models.variable_model
        self._data_view_notice = models.notice
