from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from docx import Document
from PySide6.QtCore import Q_ARG, QMetaObject, QObject

from modori.research_flow import DurableDecision, ResearchFlowState
from modori.research_os import PrimaryAction
from modori.ui.contracts import ReportExportOptions
from modori.ui.controller import UiController
from tests.ui.test_research_flow_controller import ControllableWorker
from tests.ui.test_research_flow_qml import _app, _load_panel


def _finish(worker: ControllableWorker) -> None:
    worker.finish(worker.execute())
    _app().processEvents()


def _invoke(panel: QObject, method: str, argument: str | None = None) -> bool:
    if argument is None:
        return bool(QMetaObject.invokeMethod(panel, method))
    return bool(
        QMetaObject.invokeMethod(
            panel,
            method,
            Q_ARG("QVariant", argument),
        )
    )


def test_korean_beginner_qml_flow_is_ledger_bound_manual_and_recoverable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "LOCALAPPDATA",
        str((tmp_path / "local-app-data").resolve()),
    )
    data_path = tmp_path / "score.csv"
    data_path.write_text(
        "score\n" + "\n".join(str(value) for value in range(1, 11)) + "\n",
        encoding="utf-8",
    )
    worker = ControllableWorker()
    host = UiController(worker=worker)

    assert host.previewDataFilePath(str(data_path)) is True
    assert len(host.importColumnRows) == 1
    assert len(host.importReviewRows) == 4
    assert host.variableModel is None
    assert host.confirmPendingImport() is True
    assert host.variableModel is not None
    assert host.pipeline is not None
    dataset = host._services.pipeline_ops.current_dataset()
    assert dataset is not None
    assert dataset.variables["score"].measure.value == "ordinal"
    assert host.updateVariableMetadata(
        "score",
        {"label": "인지 점수", "measure": "scale"},
    ).ok
    dataset = host._services.pipeline_ops.current_dataset()
    assert dataset is not None
    assert dataset.variables["score"].label == "인지 점수"

    flow = host.researchFlow
    engine, panel = _load_panel(flow)
    try:
        assert _invoke(panel, "invokeCommand", "start")
        _finish(worker)
        assert flow.current_view.state is ResearchFlowState.INTAKE_CAUSAL
        assert _invoke(panel, "invokeCommand", "causal_no")
        assert _invoke(panel, "chooseProfile", "numeric_distribution")

        outcome = panel.findChild(QObject, "researchRoleOutcome")
        assert outcome is not None
        outcome.setProperty("text", "score")
        _app().processEvents()
        assert _invoke(panel, "submitRoleDraft")
        assert flow.current_view.state is ResearchFlowState.MEANING_REVIEWING
        assert flow._runtime._handle is None
        assert flow._runtime._record is None

        _finish(worker)
        assert flow.current_view.state is ResearchFlowState.VARIABLE_MEANING_REVIEW
        meaning_model = flow.stateModel["meaningReview"]
        assert meaning_model["rows"] == [
            {
                "role": "outcome",
                "variableId": "score",
                "label": "인지 점수",
                "measure": "scale",
                "valueLabels": [],
                "missingCodes": [],
                "storageDtype": "int",
                "evidenceSource": "current_dataset_metadata",
                "conceptDefinitionStatus": "not_recorded",
                "unitStatus": "not_recorded",
            }
        ]
        meaning_digest = flow._views.meaning_review.review_digest
        meaning_surface = panel.findChild(QObject, "researchVariableMeaningReview")
        assert meaning_surface is not None
        assert meaning_surface.property("visible") is True
        assert meaning_surface.property("conceptDefinitionUnknown") is True
        assert _invoke(panel, "confirmMeaningReview")
        assert flow.current_view.state is ResearchFlowState.COMMITTING
        _finish(worker)
        assert flow._runtime._handle is not None
        assert Path(flow._runtime._handle.ledger_path).is_file()

        question = panel.findChild(QObject, "researchQuestionCard")
        assert question is not None
        observed_questions: list[str] = []
        for answer in ("variables", "independent", "variables"):
            assert flow.current_view.state is ResearchFlowState.CLARIFY_READY
            observed_questions.append(str(flow.stateModel["question"]["title"]))
            if answer == "independent":
                question.setProperty("selectedOptionId", answer)
            assert QMetaObject.invokeMethod(question, "submitAnswer")
            _finish(worker)
        assert len(observed_questions) == 3
        assert flow.current_view.state is ResearchFlowState.CANDIDATE_READY

        record = flow._runtime._record
        assert isinstance(record, DurableDecision)
        assert record.action is PrimaryAction.RECOMMEND_LOCAL
        role_fact = record.request.estimand.target_roles[0].variable_ids
        assert role_fact.provenance_refs == (
            record.request.question.envelope.created_event_ref,
            f"variable-meaning-review:v1:{meaning_digest}",
        )
        preparation = flow._views.preparation
        assert preparation is not None
        assert preparation.step_type == "stats.descriptives_table1"
        assert json.loads(preparation.canonical_step_params) == {
            "group": None,
            "include_missing_counts": True,
            "language": "ko",
            "schema_version": 1,
            "variables": ["score"],
        }
        assert host._recommendation_state.candidates
        assert all(
            not hasattr(candidate, "passport_digest")
            for candidate in host._recommendation_state.candidates
        )

        handle = flow._runtime._handle
        assert handle is not None
        ledger_uri = f"{Path(handle.ledger_path).as_uri()}?mode=ro"
        with closing(sqlite3.connect(ledger_uri, uri=True)) as connection:
            head_sequence = connection.execute(
                "SELECT sequence FROM ledger_head WHERE singleton=1"
            ).fetchone()[0]
            event_count = connection.execute(
                "SELECT COUNT(*) FROM ledger_events"
            ).fetchone()[0]
            passport_count = connection.execute(
                "SELECT COUNT(*) FROM ledger_artifacts "
                "WHERE artifact_kind='analysis_passport'"
            ).fetchone()[0]
        assert (head_sequence, event_count, passport_count) == (8, 8, 4)

        submissions_before_prepare = len(worker.submissions)
        assert _invoke(panel, "invokeCommand", "prepare")
        _finish(worker)
        assert flow.current_view.state is ResearchFlowState.PREPARE_REVIEW
        assert len(worker.submissions) == submissions_before_prepare + 1
        submissions_before_confirm = len(worker.submissions)
        assert _invoke(panel, "confirmReview")
        assert flow.current_view.state is ResearchFlowState.CONFIRMED
        assert len(worker.submissions) == submissions_before_confirm
        assert host.resultsModel == []

        early_export = host.exportReport(
            ReportExportOptions(language="ko", include_figures=False)
        )
        assert early_export.ok is False
        submissions_before_run = len(worker.submissions)
        assert host.rerun().ok is True
        _finish(worker)
        assert len(worker.submissions) == submissions_before_run + 1
        assert [result.result_id for result in host.resultsModel] == [
            "descriptives_table1"
        ]
        steps_before_export = list(host.pipeline.steps)
        exported = host.exportReport(
            ReportExportOptions(language="ko", include_figures=False)
        )
        assert exported.ok is True
        report_path = Path(exported.result_ids[0])
        report_text = "\n".join(
            paragraph.text for paragraph in Document(report_path).paragraphs
        )
        assert "Research OS" in report_text
        assert "추천 타당성을 보증하지 않습니다" in report_text
        assert host.pipeline.steps == steps_before_export

        assert host.updateVariableMetadata("score", {"label": "변경된 점수"}).ok
        _app().processEvents()
        assert flow.current_view.state is ResearchFlowState.REPLAN_REQUIRED
        assert host.selectionConfirmationRequired is True
        blocked = host.rerun()
        assert blocked.ok is False
        assert blocked.error_code == "experimental_confirmation_required"
        assert _invoke(panel, "invokeCommand", "replan")
        _finish(worker)
        assert flow.current_view.state is ResearchFlowState.INTAKE_CAUSAL
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine
