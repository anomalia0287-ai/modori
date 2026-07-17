from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import (
    Property,
    Q_ARG,
    QMetaObject,
    QObject,
    QUrl,
    Signal,
    Slot,
    qInstallMessageHandler,
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from modori.app import AppBootstrap


QML_ROOT = Path("src/modori/ui/qml")


def _base_model(state: str) -> dict[str, object]:
    return {
        "state": state,
        "mode": "guided",
        "language": "ko",
        "title": f"{state} 제목",
        "body": f"{state} 본문",
        "stageText": "",
        "badgeText": "로컬 Research OS",
        "visiblePassportDigest": "",
        "primaryAction": None,
        "secondaryActions": [],
        "options": [],
        "question": None,
        "candidate": None,
        "evidenceRows": [],
    }


def _action(command: str, label: str = "계속") -> dict[str, object]:
    return {"command": command, "label": label, "enabled": True}


def _model_for(state: str) -> dict[str, object]:
    model = _base_model(state)
    if state == "idle":
        model["primaryAction"] = _action("start", "연구과업 시작")
    elif state in {"fingerprinting", "committing", "handoff_preflight"}:
        model["stageText"] = "데이터 버전을 확인하는 중"
        model["primaryAction"] = _action("cancel", "중단")
    elif state == "intake_causal":
        model["primaryAction"] = _action("causal_no", "아니요")
        model["secondaryActions"] = [
            _action("causal_yes", "예"),
            _action("causal_not_sure", "잘 모르겠습니다"),
        ]
    elif state == "causal_scope_notice":
        model["primaryAction"] = _action("causal_record", "이 제한을 기록하고 계속")
        model["secondaryActions"] = [_action("back", "돌아가기")]
    elif state == "intake_profile":
        model["primaryAction"] = _action("select_profile", "연구과업 선택")
    elif state == "intake_roles":
        model["primaryAction"] = _action("submit_roles", "변수 역할 확인")
    elif state == "clarify_ready":
        model["primaryAction"] = _action("answer", "답변 기록")
        model["secondaryActions"] = [
            _action("answer_not_sure", "잘 모르겠습니다"),
            _action("retract", "이 결정 철회"),
        ]
        model["options"] = [
            {
                "optionId": "independent",
                "label": "서로 독립적입니다",
                "selected": False,
                "enabled": True,
            },
            {
                "optionId": "not_sure",
                "label": "잘 모르겠습니다",
                "selected": False,
                "enabled": True,
            },
        ]
        model["question"] = {
            "status": "available",
            "statusMessage": "",
            "title": "이 질문을 드리는 이유",
            "questionText": "관측 단위가 서로 독립적입니까?",
            "baseReason": "표본 구조에 따라 지원 경계가 달라집니다.",
            "selectionSummary": "다른 미확인 조건보다 먼저 확인합니다.",
            "remainingUncertainty": "가중치 사용 여부는 아직 확인되지 않았습니다.",
            "notSureGuidance": "모르면 기권을 포함한 안전한 경로를 다시 계산합니다.",
            "caution": "이 설명은 분석의 타당성을 보증하지 않습니다.",
            "evidenceRows": [],
            "sourceIdentityText": "",
        }
    elif state in {"candidate_ready", "preparation_blocked"}:
        model["visiblePassportDigest"] = "0123456789ab"
        model["primaryAction"] = (
            _action("prepare", "구성 검토로 이동")
            if state == "candidate_ready"
            else None
        )
        model["candidate"] = {
            "capabilityLabel": "서로 겹치지 않는 두 집단의 평균 차이",
            "methodLabel": "Welch 두 독립표본 t 방법",
            "claimBoundary": "관측된 차이이며 인과효과로 해석하지 않습니다.",
            "roleRows": [
                {"label": "결과 변수", "value": "삶의 만족도"},
                {"label": "집단 변수", "value": "처치 집단"},
            ],
            "reviewStatus": (
                "검토 필요"
                if state == "candidate_ready"
                else "현재 데이터에서는 구성을 준비할 수 없음"
            ),
            "persistentBoundary": "검증 중인 분석 후보 · 자동 실행 안 함",
        }
        model["evidenceRows"] = [
            {"label": "실행 전 구조 검사", "value": "구성 검토 가능"}
        ]
    elif state == "prepare_review":
        model["preparationReview"] = {
            "stepType": "stats.compare_groups",
            "visiblePreparationDigest": "abcdef012345",
            "experimental": True,
            "automaticRun": False,
            "settingsRows": [
                {"label": "결과 변수", "value": "삶의 만족도"},
                {"label": "집단 변수", "value": "처치 집단"},
            ],
        }
    elif state == "confirmed":
        model["preparationReview"] = {
            "stepType": "stats.compare_groups",
            "visiblePreparationDigest": "abcdef012345",
            "experimental": True,
            "automaticRun": False,
            "settingsRows": [
                {"label": "결과 변수", "value": "삶의 만족도"},
            ],
        }
    elif state in {"recovery_pending", "memory_unavailable", "failure", "cancelled"}:
        model["primaryAction"] = _action("resume", "기록에서 다시 확인")
    elif state in {"retracted", "replan_required", "abstain_ready"}:
        model["primaryAction"] = _action("replan", "현재 데이터로 다시 계획")
    elif state in {"corruption", "intake_blocked", "scope_boundary"}:
        model["primaryAction"] = _action("back", "돌아가기")
    return model


class FakeResearchFlow(QObject):
    stateChanged = Signal()

    def __init__(self, model: dict[str, object]) -> None:
        super().__init__()
        self._model = model
        self.calls: list[tuple[str, object]] = []

    @Property("QVariantMap", notify=stateChanged)
    def stateModel(self) -> dict[str, object]:
        return self._model

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._model["state"] in {
            "fingerprinting",
            "committing",
            "handoff_preflight",
        }

    def set_model(self, model: dict[str, object]) -> None:
        self._model = model
        self.stateChanged.emit()

    def _record(self, command: str, payload: object = None) -> bool:
        self.calls.append((command, payload))
        return True

    @Slot(result=bool)
    def start(self) -> bool:
        return self._record("start")

    @Slot(result=bool)
    def chooseCausalNo(self) -> bool:
        return self._record("causal_no")

    @Slot(result=bool)
    def chooseCausalYes(self) -> bool:
        return self._record("causal_yes")

    @Slot(result=bool)
    def chooseCausalNotSure(self) -> bool:
        return self._record("causal_not_sure")

    @Slot(result=bool)
    def recordCausalBoundary(self) -> bool:
        return self._record("causal_record")

    @Slot(result=bool)
    def back(self) -> bool:
        return self._record("back")

    @Slot(str, result=bool)
    def selectProfile(self, profile: str) -> bool:
        return self._record("select_profile", profile)

    @Slot(result=bool)
    def chooseNoMatchingProfile(self) -> bool:
        return self._record("no_matching_profile")

    @Slot("QVariantMap", result=bool)
    def submitRoles(self, roles: object) -> bool:
        return self._record("submit_roles", roles)

    @Slot(str, "QVariantList", result=bool)
    def answer(self, option_id: str, variable_ids: object) -> bool:
        return self._record("answer", (option_id, tuple(variable_ids)))

    @Slot(result=bool)
    def answerNotSure(self) -> bool:
        return self._record("answer_not_sure")

    @Slot(result=bool)
    def resume(self) -> bool:
        return self._record("resume")

    @Slot(result=bool)
    def retract(self) -> bool:
        return self._record("retract")

    @Slot(result=bool)
    def replan(self) -> bool:
        return self._record("replan")

    @Slot(result=bool)
    def prepare(self) -> bool:
        return self._record("prepare")

    @Slot(result=bool)
    def confirm(self) -> bool:
        return self._record("confirm")

    @Slot(result=bool)
    def cancel(self) -> bool:
        return self._record("cancel")


def _app() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _component_errors(component: QQmlComponent) -> str:
    return "\n".join(error.toString() for error in component.errors())


def _load_panel(controller: QObject) -> tuple[QQmlEngine, QObject]:
    app = _app()
    engine = QQmlEngine()
    bootstrap = AppBootstrap()
    engine._bootstrap = bootstrap
    engine.rootContext().setContextProperty("appBootstrap", bootstrap)
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(
            str((QML_ROOT / "components/ResearchFlowPanel.qml").resolve())
        ),
    )
    assert component.status() == QQmlComponent.Status.Ready, _component_errors(
        component
    )
    obj = component.createWithInitialProperties(
        {"controller": controller, "width": 340.0}
    )
    assert obj is not None, _component_errors(component)
    engine._component = component
    engine._panel = obj
    app.processEvents()
    return engine, obj


@pytest.mark.parametrize(
    ("state", "visible_region"),
    [
        ("idle", "researchTransformationNotice"),
        ("fingerprinting", "researchBusyStage"),
        ("intake_causal", "researchCausalActions"),
        ("causal_scope_notice", "researchStaticBoundary"),
        ("intake_profile", "researchProfileChoices"),
        ("intake_roles", "researchRoleForm"),
        ("clarify_ready", "researchQuestionCard"),
        ("candidate_ready", "researchCandidateCard"),
        ("preparation_blocked", "researchCandidateCard"),
        ("abstain_ready", "researchStatusPanel"),
        ("memory_unavailable", "researchStatusPanel"),
        ("failure", "researchStatusPanel"),
        ("corruption", "researchStatusPanel"),
        ("recovery_pending", "researchStatusPanel"),
        ("retracted", "researchStatusPanel"),
        ("replan_required", "researchStatusPanel"),
        ("cancelled", "researchStatusPanel"),
        ("prepare_review", "researchPreparationReview"),
        ("confirmed", "researchPreparationReview"),
    ],
)
def test_real_panel_renders_each_closed_state_region(
    state: str, visible_region: str
) -> None:
    controller = FakeResearchFlow(_model_for(state))
    engine, panel = _load_panel(controller)
    try:
        region = panel.findChild(QObject, visible_region)
        assert region is not None
        assert region.property("visible") is True
        assert panel.property("routeReadyRenderable") is False
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_all_closed_states_load_without_significant_qml_runtime_warnings() -> None:
    from tests.ui.test_qml_runtime_load import _significant_warnings

    states = (
        "idle",
        "fingerprinting",
        "intake_causal",
        "causal_scope_notice",
        "intake_profile",
        "intake_roles",
        "clarify_ready",
        "candidate_ready",
        "preparation_blocked",
        "abstain_ready",
        "memory_unavailable",
        "failure",
        "corruption",
        "recovery_pending",
        "retracted",
        "replan_required",
        "cancelled",
        "prepare_review",
        "confirmed",
    )
    messages: list[str] = []
    runtime_messages: list[str] = []

    def message_handler(msg_type, context, message) -> None:
        del msg_type, context
        messages.append(message)

    previous_handler = qInstallMessageHandler(message_handler)
    try:
        for state in states:
            messages.clear()
            controller = FakeResearchFlow(_model_for(state))
            engine, panel = _load_panel(controller)
            _app().processEvents()
            runtime_messages.extend(messages)
            panel.deleteLater()
            _app().processEvents()
            del engine
    finally:
        qInstallMessageHandler(previous_handler)

    assert _significant_warnings(runtime_messages) == []


def test_route_ready_has_no_visible_content_or_action_path() -> None:
    controller = FakeResearchFlow(_model_for("route_ready"))
    engine, panel = _load_panel(controller)
    try:
        assert panel.property("supportedState") is False
        content = panel.findChild(QObject, "researchFlowContent")
        assert content is not None
        assert content.property("visible") is False
        assert controller.calls == []
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_panel_dispatches_only_typed_controller_commands() -> None:
    controller = FakeResearchFlow(_model_for("intake_causal"))
    engine, panel = _load_panel(controller)
    try:
        assert QMetaObject.invokeMethod(
            panel,
            "invokeCommand",
            Q_ARG("QVariant", "causal_yes"),
        )
        assert controller.calls == [("causal_yes", None)]
        assert QMetaObject.invokeMethod(
            panel,
            "invokeCommand",
            Q_ARG("QVariant", "route"),
        )
        assert controller.calls == [("causal_yes", None)]
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_prepare_confirm_and_run_remain_three_distinct_actions() -> None:
    controller = FakeResearchFlow(_model_for("candidate_ready"))
    engine, panel = _load_panel(controller)
    try:
        assert QMetaObject.invokeMethod(
            panel,
            "invokeCommand",
            Q_ARG("QVariant", "prepare"),
        )
        controller.set_model(_model_for("prepare_review"))
        _app().processEvents()
        assert QMetaObject.invokeMethod(panel, "confirmReview")
        assert controller.calls == [("prepare", None), ("confirm", None)]

        work_source = (QML_ROOT / "screens/WorkScreen.qml").read_text(encoding="utf-8")
        assert "onClicked: uiController.rerunNow()" in work_source
        assert "rerunNow" not in (
            QML_ROOT / "components/ResearchFlowPanel.qml"
        ).read_text(encoding="utf-8")
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_real_controller_static_causal_back_is_write_free_and_record_is_explicit() -> (
    None
):
    from modori.research_flow import ResearchFlowState
    from tests.ui.test_research_flow_controller import (
        ControllableWorker,
        FakeRuntime,
        _controller,
        _transient_views,
    )

    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [1])
    controller._views = _transient_views(ResearchFlowState.INTAKE_CAUSAL)
    engine, panel = _load_panel(controller)
    try:
        assert QMetaObject.invokeMethod(
            panel, "invokeCommand", Q_ARG("QVariant", "causal_yes")
        )
        assert controller.stateModel["state"] == "causal_scope_notice"
        assert worker.submissions == []

        assert QMetaObject.invokeMethod(
            panel, "invokeCommand", Q_ARG("QVariant", "back")
        )
        assert controller.stateModel["state"] == "intake_causal"
        assert worker.submissions == []

        assert QMetaObject.invokeMethod(
            panel, "invokeCommand", Q_ARG("QVariant", "causal_yes")
        )
        assert QMetaObject.invokeMethod(
            panel, "invokeCommand", Q_ARG("QVariant", "causal_record")
        )
        assert controller.stateModel["state"] == "committing"
        assert len(worker.submissions) == 1
        worker.execute()
        assert runtime.calls[-1][0] == "commit_causal_boundary"
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_real_controller_receives_ordered_role_draft_from_qml() -> None:
    from modori.research_flow import ResearchFlowState
    from tests.ui.test_research_flow_controller import (
        ControllableWorker,
        FakeRuntime,
        _controller,
        _transient_views,
    )

    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [1])
    controller._views = _transient_views(ResearchFlowState.INTAKE_PROFILE)
    engine, panel = _load_panel(controller)
    try:
        assert QMetaObject.invokeMethod(
            panel,
            "chooseProfile",
            Q_ARG("QVariant", "paired_two_time_mean_change"),
        )
        assert controller.stateModel["state"] == "intake_roles"

        before = panel.findChild(QObject, "researchRoleBefore")
        after = panel.findChild(QObject, "researchRoleAfter")
        submit = panel.findChild(QObject, "researchRoleSubmit")
        assert before is not None
        assert after is not None
        assert submit is not None
        assert submit.property("enabled") is False
        before.setProperty("text", "before_score")
        after.setProperty("text", "after_score")
        _app().processEvents()
        assert submit.property("enabled") is True
        assert QMetaObject.invokeMethod(panel, "submitRoleDraft")
        assert controller.stateModel["state"] == "committing"
        assert len(worker.submissions) == 1

        worker.execute()
        call_name, payload = runtime.calls[-1]
        assert call_name == "commit_initial"
        assert payload["roles"].repeated_measure_order == (
            "before_score",
            "after_score",
        )
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_question_card_sends_variable_answer_and_not_sure_through_real_controller() -> (
    None
):
    from modori.research_flow import ResearchFlowState
    from tests.ui.test_research_flow_controller import (
        ControllableWorker,
        FakeRuntime,
        _clarify_views,
        _controller,
        _transient_views,
    )

    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [1])
    controller._views = _clarify_views()
    engine, panel = _load_panel(controller)
    try:
        question = panel.findChild(QObject, "researchQuestionCard")
        variable_field = panel.findChild(QObject, "researchQuestionVariables")
        assert question is not None
        assert variable_field is not None
        variable_field.setProperty("text", "school_id, class_id")
        assert QMetaObject.invokeMethod(question, "submitAnswer")
        assert controller.stateModel["state"] == "committing"
        worker.execute()
        assert runtime.calls[-1][0] == "answer"
        assert runtime.calls[-1][1]["option_id"] == "variables"
        assert runtime.calls[-1][1]["variable_ids"] == (
            "school_id",
            "class_id",
        )
        assert runtime.calls[-1][1]["not_sure"] is False

        controller._busy = False
        controller._views = _clarify_views()
        controller.stateChanged.emit()
        _app().processEvents()
        assert QMetaObject.invokeMethod(question, "submitNotSure")
        worker.execute()
        assert runtime.calls[-1][0] == "answer"
        assert runtime.calls[-1][1]["not_sure"] is True
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_variable_question_deduplicates_ordered_ids_without_inventing_values() -> None:
    model = _model_for("clarify_ready")
    model["options"] = [
        {
            "optionId": "not_sure",
            "label": "잘 모르겠습니다",
            "selected": False,
            "enabled": True,
        }
    ]
    controller = FakeResearchFlow(model)
    engine, panel = _load_panel(controller)
    try:
        field = panel.findChild(QObject, "researchQuestionVariables")
        question = panel.findChild(QObject, "researchQuestionCard")
        assert field is not None
        assert question is not None
        field.setProperty("text", "school_id, class_id, school_id")
        assert QMetaObject.invokeMethod(question, "submitAnswer")
        assert controller.calls == [
            ("answer", ("variables", ("school_id", "class_id")))
        ]
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_closed_question_sends_only_the_selected_registered_option() -> None:
    controller = FakeResearchFlow(_model_for("clarify_ready"))
    engine, panel = _load_panel(controller)
    try:
        question = panel.findChild(QObject, "researchQuestionCard")
        assert question is not None
        question.setProperty("selectedOptionId", "independent")
        assert QMetaObject.invokeMethod(question, "submitAnswer")
        assert controller.calls == [("answer", ("independent", ()))]
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_qml_prepare_and_confirm_use_real_controller_without_running_analysis() -> None:
    from modori.core import Pipeline
    from modori.research_flow import ResearchFlowState
    from modori.research_os import Language, P1TaskProfile
    from modori.ui.contracts import ControllerMode
    from modori.ui.pipeline_ops import PipelineOperations
    from modori.ui.research_flow_controller import (
        ResearchFlowController,
        ResearchFlowViews,
    )
    from modori.ui.research_preparation_editor import ResearchPreparationEditor
    from tests.test_research_flow_preflight import _valid_dataset
    from tests.ui.test_research_flow_controller import (
        ControllableWorker,
        FakeRuntime,
        _candidate_views,
        _ready_preparation,
        _transient_views,
    )

    profile = P1TaskProfile.LINEAR_CO_MOVEMENT
    preparation = _ready_preparation(profile)
    pipeline = Pipeline(_valid_dataset(profile))
    version = [1]

    def commit_pipeline_change(_preparation) -> int:
        version[0] += 1
        return version[0]

    editor = ResearchPreparationEditor(
        PipelineOperations(pipeline),
        version_provider=lambda: version[0],
        current_dataset_fingerprint=lambda: preparation.dataset_fingerprint,
        commit_pipeline_change=commit_pipeline_change,
    )
    review_base = _transient_views(ResearchFlowState.PREPARE_REVIEW)
    review_views = ResearchFlowViews(
        guided=review_base.guided,
        standard=review_base.standard,
        preparation=preparation,
    )
    candidate_base = _candidate_views()
    candidate_views = ResearchFlowViews(
        guided=candidate_base.guided,
        standard=candidate_base.standard,
        preparation=preparation,
    )
    runtime = FakeRuntime(review_views)
    worker = ControllableWorker()
    controller = ResearchFlowController(
        runtime=runtime,
        worker=worker,
        pipeline_version_provider=lambda: version[0],
        mode_change_request=lambda _mode: True,
        initial_mode=ControllerMode.STANDARD,
        language=Language.KO,
        preparation_editor=editor,
    )
    controller._views = candidate_views
    engine, panel = _load_panel(controller)
    try:
        assert QMetaObject.invokeMethod(
            panel, "invokeCommand", Q_ARG("QVariant", "prepare")
        )
        assert pipeline.steps == []
        worker.finish(worker.execute())
        _app().processEvents()
        assert controller.stateModel["state"] == "prepare_review"
        review = panel.findChild(QObject, "researchPreparationReview")
        assert review is not None
        assert review.property("visible") is True
        assert pipeline.steps == []

        assert QMetaObject.invokeMethod(panel, "confirmReview")
        assert controller.stateModel["state"] == "confirmed"
        assert len(pipeline.steps) == 1
        assert pipeline.analysis_objects == {}
        assert len(worker.submissions) == 1
    finally:
        panel.deleteLater()
        _app().processEvents()
        del engine


def test_research_qml_never_accepts_authority_or_arbitrary_analysis_settings() -> None:
    sources = "\n".join(
        (QML_ROOT / "components" / name).read_text(encoding="utf-8")
        for name in (
            "ResearchFlowPanel.qml",
            "ResearchQuestionCard.qml",
            "ResearchCandidateCard.qml",
        )
    )
    forbidden = {
        "decisionIdentityDigest",
        "datasetFingerprint",
        "sourceSchemaFingerprint",
        "canonicalStepParams",
        "passportMapping",
        "ledgerPath",
        "storePath",
        "genericMethod",
    }
    assert {token for token in forbidden if token in sources} == set()
    assert "uiController.researchFlow" not in sources


def test_research_qml_keeps_one_question_wrapped_accessible_and_reduced_motion_safe() -> (
    None
):
    panel = (QML_ROOT / "components/ResearchFlowPanel.qml").read_text(encoding="utf-8")
    question = (QML_ROOT / "components/ResearchQuestionCard.qml").read_text(
        encoding="utf-8"
    )
    candidate = (QML_ROOT / "components/ResearchCandidateCard.qml").read_text(
        encoding="utf-8"
    )

    assert panel.count("ResearchQuestionCard {") == 1
    assert "visible: !root.reduceEffects" in panel
    assert "Accessible.role: Accessible.StatusBar" in panel
    for source in (panel, question, candidate):
        assert "Accessible.name" in source
        assert "wrapMode: Text.WordWrap" in source


def test_work_surface_keeps_research_os_and_legacy_provenance_separate() -> None:
    work = (QML_ROOT / "screens/WorkScreen.qml").read_text(encoding="utf-8")
    guide = (QML_ROOT / "components/GuideRail.qml").read_text(encoding="utf-8")

    assert "researchRailOpen" in work
    assert "researchOnly" in work
    assert "ResearchFlowPanel" in guide
    assert "uiController.researchFlow" in guide
    assert "showLegacyCandidates" in guide
    assert "guide.experimental_status" in guide
    assert "recommendationReason" not in (
        QML_ROOT / "components/ResearchFlowPanel.qml"
    ).read_text(encoding="utf-8")
