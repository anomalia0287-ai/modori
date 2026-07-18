from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import json
from time import perf_counter
from types import SimpleNamespace
from threading import Event

import pandas as pd
import pytest

from modori.core import Dataset, Measure, Pipeline, StepResult, Variable
from modori.research_flow import (
    FINGERPRINT_CONTRACT_ID,
    FINGERPRINT_WORKER_DEADLINE_SECONDS,
    DatasetIdentity,
    FingerprintCancelled,
    LiveResearchFlowCoordinator,
    ResearchFlowState,
    ResearchTaskSessionStore,
    SourceSchemaDescriptor,
    TaskSessionIntegrityError,
    TaskSessionUnavailableError,
    preflight_mapped_step,
)
from modori.research_os import Language
from modori.ui.contracts import ControllerMode
from modori.ui.controller import UiController
from modori.ui.controller_services import UiControllerServices
from modori.ui.research_flow_controller import (
    ResearchFlowController,
    ResearchFlowControllerError,
    ResearchFlowPipelineAccess,
    ResearchFlowPipelineSnapshot,
    ResearchFlowRuntime,
    ResearchFlowViews,
)
from modori.ui.pipeline_ops import PipelineOperations
from modori.ui.research_preparation_editor import ResearchPreparationEditor
from modori.ui.research_flow_presenter import (
    ResearchUiCommand,
    present_transient_state,
)
from modori.ui.worker import EngineJobResult
from tests.ui.test_research_flow_presenter import (
    _clarify_record,
    _labels,
    _preflight,
    _terminal_record,
)
from tests.test_research_flow_preflight import _mapping, _valid_dataset
from modori.research_os import P1RoleBindings, P1TaskProfile
from modori.ui.research_flow_presenter import present_durable_record


def _transient_views(state: ResearchFlowState) -> ResearchFlowViews:
    return ResearchFlowViews(
        guided=present_transient_state(
            state,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
        ),
        standard=present_transient_state(
            state,
            mode=ControllerMode.STANDARD,
            language=Language.KO,
        ),
    )


def _candidate_views() -> ResearchFlowViews:
    record = _terminal_record(P1TaskProfile.LINEAR_CO_MOVEMENT)
    preflight = _preflight(record)
    labels = _labels(record)
    return ResearchFlowViews(
        guided=present_durable_record(
            record,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
            preflight=preflight,
            variable_labels=labels,
        ),
        standard=present_durable_record(
            record,
            mode=ControllerMode.STANDARD,
            language=Language.KO,
            preflight=preflight,
            variable_labels=labels,
        ),
    )


def _ready_preparation(profile: P1TaskProfile, *, version: int = 1):
    result = preflight_mapped_step(
        _mapping(profile),
        _valid_dataset(profile),
        captured_pipeline_version=version,
        current_pipeline_version=lambda: version,
    )
    assert result.preparation is not None
    return result.preparation


def _clarify_views() -> ResearchFlowViews:
    record = _clarify_record()
    return ResearchFlowViews(
        guided=present_durable_record(
            record,
            mode=ControllerMode.GUIDED,
            language=Language.KO,
            preflight=None,
        ),
        standard=present_durable_record(
            record,
            mode=ControllerMode.STANDARD,
            language=Language.KO,
            preflight=None,
        ),
    )


class FakeRuntime:
    def __init__(
        self,
        start_result: ResearchFlowViews,
        *,
        dataset_fingerprint: str | None = None,
    ) -> None:
        self.start_result = start_result
        self.dataset_fingerprint = dataset_fingerprint
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.noted_versions: list[int] = []

    def note_pipeline_version(self, pipeline_version: int) -> None:
        self.noted_versions.append(pipeline_version)

    def current_dataset_fingerprint(self) -> str | None:
        return self.dataset_fingerprint

    def start(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("start", kwargs))
        return self.start_result

    def commit_initial(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("commit_initial", kwargs))
        return self.start_result

    def commit_causal_boundary(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("commit_causal_boundary", kwargs))
        return self.start_result

    def answer(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("answer", kwargs))
        return self.start_result

    def resume(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("resume", kwargs))
        return self.start_result

    def retract(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("retract", kwargs))
        return self.start_result

    def replan(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("replan", kwargs))
        return self.start_result

    def prepare(self, **kwargs: object) -> ResearchFlowViews:
        self.calls.append(("prepare", kwargs))
        return self.start_result


class FakeFuture:
    def __init__(self) -> None:
        self.callback = None
        self.payload: EngineJobResult[ResearchFlowViews] | None = None

    def add_done_callback(self, callback) -> None:
        self.callback = callback

    def result(self, timeout=None):
        _ = timeout
        assert self.payload is not None
        return self.payload


@dataclass(frozen=True)
class Submission:
    run_id: int
    pipeline_version: int
    job: object
    future: FakeFuture


class ControllableWorker:
    def __init__(self) -> None:
        self.submissions: list[Submission] = []

    def submit(self, *, run_id: int, pipeline_version: int, job: object):
        future = FakeFuture()
        self.submissions.append(Submission(run_id, pipeline_version, job, future))
        return future

    def execute(self, index: int = -1) -> ResearchFlowViews:
        job = self.submissions[index].job
        assert callable(job)
        return job()

    def finish(
        self,
        payload: ResearchFlowViews,
        *,
        index: int = -1,
        ok: bool = True,
    ) -> None:
        submission = self.submissions[index]
        submission.future.payload = EngineJobResult(
            run_id=submission.run_id,
            pipeline_version=submission.pipeline_version,
            ok=ok,
            payload=payload if ok else None,
            error_code=None if ok else "engine_error",
            message_ko="" if ok else "오류",
        )
        assert submission.future.callback is not None
        submission.future.callback(submission.future)


def _controller(
    runtime: FakeRuntime,
    worker: ControllableWorker,
    version: list[int],
) -> ResearchFlowController:
    return ResearchFlowController(
        runtime=runtime,
        worker=worker,
        pipeline_version_provider=lambda: version[0],
        mode_change_request=lambda _mode: True,
        initial_mode=ControllerMode.STANDARD,
        language=Language.KO,
    )


def test_start_acknowledges_under_100ms_and_defers_all_runtime_work() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    version = [7]
    controller = _controller(runtime, worker, version)

    started = perf_counter()
    accepted = controller.start()
    elapsed = perf_counter() - started

    assert accepted is True
    assert elapsed < 0.1
    assert controller.busy is True
    assert controller.stateModel["state"] == "fingerprinting"
    assert runtime.calls == []
    assert len(worker.submissions) == 1
    assert worker.submissions[0].pipeline_version == 7

    payload = worker.execute()
    assert runtime.calls[0][0] == "start"
    worker.finish(payload)

    assert controller.busy is False
    assert controller.current_view.state is ResearchFlowState.INTAKE_CAUSAL
    assert controller.stateModel["state"] == "intake_causal"
    assert "decisionIdentityDigest" not in controller.stateModel


def test_late_result_is_discarded_after_pipeline_version_change() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    version = [3]
    controller = _controller(runtime, worker, version)
    assert controller.start() is True

    version[0] = 4
    controller.syncPipelineVersion()
    assert controller.current_view.state is ResearchFlowState.REPLAN_REQUIRED

    payload = worker.execute()
    worker.finish(payload)

    assert controller.current_view.state is ResearchFlowState.REPLAN_REQUIRED
    assert controller.busy is False
    assert runtime.noted_versions[-1] == 4


def test_pipeline_change_before_start_keeps_idle_without_false_replan() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    version = [1]
    controller = _controller(runtime, worker, version)

    version[0] = 2
    controller.syncPipelineVersion()

    assert controller.current_view.state is ResearchFlowState.IDLE
    assert runtime.noted_versions == [2]
    assert worker.submissions == []


def test_mode_switch_changes_depth_but_not_candidate_authority_or_action() -> None:
    runtime = FakeRuntime(_candidate_views())
    worker = ControllableWorker()
    version = [5]
    controller = _controller(runtime, worker, version)
    controller.start()
    payload = worker.execute()
    worker.finish(payload)

    standard = controller.current_view
    assert standard.mode is ControllerMode.STANDARD
    assert standard.primary_action is not None
    assert standard.primary_action.command is ResearchUiCommand.PREPARE
    assert standard.visible_passport_digest

    assert controller.syncMode("guided") is True
    guided = controller.current_view

    assert guided.mode is ControllerMode.GUIDED
    assert guided.decision_identity_digest == standard.decision_identity_digest
    assert guided.visible_passport_digest == ""
    assert guided.primary_action is not None
    assert guided.primary_action.command is standard.primary_action.command
    assert guided.candidate is not None
    assert standard.candidate is not None
    assert guided.candidate.capability_label == standard.candidate.capability_label


def test_state_model_contains_closed_question_and_candidate_projections_only() -> None:
    runtime = FakeRuntime(_candidate_views())
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [5])
    controller.start()
    worker.finish(worker.execute())

    candidate_model = controller.stateModel
    assert candidate_model["candidate"]["methodLabel"]
    assert candidate_model["candidate"]["claimBoundary"]
    assert candidate_model["evidenceRows"]
    assert "decisionIdentityDigest" not in candidate_model
    serialized = json.dumps(candidate_model, ensure_ascii=False)
    assert controller.current_view.decision_identity_digest not in serialized

    controller._views = _clarify_views()
    question_model = controller.stateModel
    assert question_model["question"]["questionText"]
    assert question_model["question"]["baseReason"]
    assert "question" in question_model


def test_mode_pair_rejects_forged_question_authority() -> None:
    views = _clarify_views()
    assert views.standard.question is not None
    forged_question = replace(
        views.standard.question,
        question_text="조작된 질문",
    )
    forged_standard = replace(views.standard, question=forged_question)

    with pytest.raises(ResearchFlowControllerError, match="question authority"):
        ResearchFlowViews(
            guided=views.guided,
            standard=forged_standard,
        )


def test_worker_failure_enters_closed_failure_without_free_form_error_copy() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [1])
    controller.start()

    worker.finish(
        _transient_views(ResearchFlowState.FAILURE),
        ok=False,
    )

    assert controller.busy is False
    assert controller.current_view.state is ResearchFlowState.FAILURE
    assert controller.stateModel["body"] != "오류"


def test_static_causal_and_scope_choices_never_submit_runtime_work() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [1])
    controller.start()
    worker.finish(worker.execute())
    baseline_submissions = len(worker.submissions)
    baseline_calls = len(runtime.calls)

    assert controller.chooseCausalYes() is True
    assert controller.current_view.state is ResearchFlowState.CAUSAL_SCOPE_NOTICE
    assert controller.back() is True
    assert controller.current_view.state is ResearchFlowState.INTAKE_CAUSAL
    assert controller.chooseCausalNotSure() is True
    assert controller.current_view.state is ResearchFlowState.INTAKE_BLOCKED
    assert controller.back() is True
    assert controller.chooseCausalNo() is True
    assert controller.current_view.state is ResearchFlowState.INTAKE_PROFILE
    assert controller.chooseNoMatchingProfile() is True
    assert controller.current_view.state is ResearchFlowState.SCOPE_BOUNDARY

    assert len(worker.submissions) == baseline_submissions
    assert len(runtime.calls) == baseline_calls
    commands = {
        action["command"]
        for action in (
            [controller.stateModel["primaryAction"]]
            + controller.stateModel["secondaryActions"]
        )
        if action is not None
    }
    assert "route" not in commands


def test_only_explicit_causal_record_schedules_persistent_work() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [4])
    controller._views = _transient_views(ResearchFlowState.INTAKE_CAUSAL)

    assert controller.chooseCausalYes() is True
    assert controller.recordCausalBoundary() is True
    assert controller.current_view.state is ResearchFlowState.COMMITTING
    assert len(worker.submissions) == 1
    assert runtime.calls == []

    payload = worker.execute()
    assert runtime.calls[0][0] == "commit_causal_boundary"
    worker.finish(payload)


def test_profile_and_roles_are_tentative_until_one_explicit_commit() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [6])
    controller._views = _transient_views(ResearchFlowState.INTAKE_PROFILE)

    assert controller.selectProfile("linear_co_movement") is True
    assert controller.current_view.state is ResearchFlowState.INTAKE_ROLES
    assert worker.submissions == []
    assert (
        controller.submitRoles(
            {
                "outcome": ["outcome"],
                "focal_predictor": ["predictor"],
            }
        )
        is True
    )
    assert controller.current_view.state is ResearchFlowState.COMMITTING
    assert len(worker.submissions) == 1

    worker.execute()
    assert runtime.calls[0][0] == "commit_initial"
    assert runtime.calls[0][1]["profile"] is P1TaskProfile.LINEAR_CO_MOVEMENT


def test_cancel_before_publication_is_immediate_and_later_commit_can_recover() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.INTAKE_CAUSAL))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [2])

    assert controller.start() is True
    assert controller.cancel() is True
    assert controller.busy is False
    assert controller.current_view.state is ResearchFlowState.CANCELLED

    payload = worker.execute()
    worker.finish(payload)
    assert controller.current_view.state is ResearchFlowState.INTAKE_CAUSAL


def test_typed_answer_is_queued_without_generic_execute_surface() -> None:
    runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
    worker = ControllableWorker()
    controller = _controller(runtime, worker, [8])
    controller._views = _clarify_views()

    assert not hasattr(controller, "execute")
    option_id = "variables"
    assert controller.answer(option_id, []) is True
    assert controller.current_view.state is ResearchFlowState.COMMITTING
    worker.execute()
    assert runtime.calls[0][0] == "answer"
    assert runtime.calls[0][1]["option_id"] == option_id


def _small_dataset() -> Dataset:
    frame = pd.DataFrame({"outcome": [1.0, 2.0], "group": [0, 1]})
    return Dataset(
        df=frame,
        variables={
            "outcome": Variable(
                name="outcome",
                label="결과 점수",
                measure=Measure.SCALE,
                value_labels={},
                missing_values=[],
                dtype="float",
                origin_step_id="import",
            ),
            "group": Variable(
                name="group",
                label="group",
                measure=Measure.NOMINAL,
                value_labels={0.0: "A", 1.0: "B"},
                missing_values=[],
                dtype="int",
                origin_step_id="import",
            ),
        },
    )


class FakePipelineOps:
    def __init__(self, step: object, dataset: Dataset, result: StepResult) -> None:
        self._step = step
        self._dataset = dataset
        self._pipeline = SimpleNamespace(step_results={getattr(step, "id"): result})

    def current_dataset(self) -> Dataset:
        return self._dataset

    def steps(self) -> list[object]:
        return [self._step]

    def step_collection(self) -> object:
        return self._pipeline


def test_source_schema_uses_import_contract_and_never_retains_path() -> None:
    dataset = _small_dataset()
    step = SimpleNamespace(
        id="import",
        step_type="import.table",
        params={
            "path": Path("C:/Users/private/secret-study.xlsx"),
            "file_type": "xlsx",
            "table_layout": {
                "sheet_name": "응답",
                "header_row_index": 2,
                "header_row_count": 1,
                "data_start_row_index": 3,
            },
            "import_selection": {
                "source_columns": ["outcome", "group", "unused"],
                "included_columns": ["outcome", "group"],
                "schema_fingerprint": "f" * 64,
                "schema_version": 1,
                "created_from": "preview",
            },
        },
    )
    ops = FakePipelineOps(
        step,
        dataset,
        StepResult(
            new_columns={key: dataset.df[key] for key in dataset.df.columns},
            new_variables=dataset.variables,
        ),
    )

    snapshot = ResearchFlowPipelineAccess(lambda: ops).capture()

    assert snapshot.dataset is dataset
    assert snapshot.source_schema.source_type == "xlsx"
    assert snapshot.source_schema.sheet_name == "응답"
    assert snapshot.source_schema.source_columns == (
        "outcome",
        "group",
        "unused",
    )
    assert snapshot.source_schema.included_columns == ("outcome", "group")
    assert "secret-study" not in repr(snapshot.source_schema)
    assert snapshot.variable_labels["outcome"] == "결과 점수"
    assert snapshot.variable_labels["group"] != "group"

    with pytest.raises(TypeError):
        snapshot.variable_labels["outcome"] = "변조"


def test_source_schema_without_selection_uses_import_result_order() -> None:
    dataset = _small_dataset()
    step = SimpleNamespace(
        id="import",
        step_type="import.table",
        params={
            "path": "D:/sensitive/raw.csv",
            "file_type": "csv",
        },
    )
    result = StepResult(
        new_columns={"outcome": dataset.df["outcome"], "group": dataset.df["group"]},
        new_variables=dataset.variables,
    )

    snapshot = ResearchFlowPipelineAccess(
        lambda: FakePipelineOps(step, dataset, result)
    ).capture()

    assert snapshot.source_schema.source_columns == ("outcome", "group")
    assert snapshot.source_schema.included_columns == ("outcome", "group")
    assert "sensitive" not in repr(snapshot.source_schema)


class SnapshotAccess:
    def __init__(self, snapshot: ResearchFlowPipelineSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def capture(self) -> ResearchFlowPipelineSnapshot:
        self.calls += 1
        return self.snapshot


class ReadOnlySession:
    def __init__(self) -> None:
        self.located: list[DatasetIdentity] = []

    def locate_existing(self, identity: DatasetIdentity):
        self.located.append(identity)
        return None

    def open_or_allocate(self, *args: object, **kwargs: object):
        raise AssertionError("start allocated a ledger before intake commit")


class UnusedCoordinator:
    def recover_current_or_none(self, handle: object):
        raise AssertionError("start recovered a nonexistent ledger")


class RaisingSession:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def locate_existing(self, identity: DatasetIdentity):
        _ = identity
        raise self.error


def test_runtime_start_caches_exact_version_and_never_allocates() -> None:
    dataset = _small_dataset()
    source_schema = (
        ResearchFlowPipelineAccess(
            lambda: FakePipelineOps(
                SimpleNamespace(
                    id="import",
                    step_type="import.table",
                    params={"file_type": "csv"},
                ),
                dataset,
                StepResult(
                    new_columns={key: dataset.df[key] for key in dataset.df.columns},
                    new_variables=dataset.variables,
                ),
            )
        )
        .capture()
        .source_schema
    )
    access = SnapshotAccess(
        ResearchFlowPipelineSnapshot(
            dataset=dataset,
            source_schema=source_schema,
            variable_labels={"outcome": "결과 점수", "group": "집단"},
        )
    )
    session = ReadOnlySession()
    fingerprint_calls: list[int] = []

    def fingerprinter(
        dataset: Dataset,
        source_schema: object,
        *,
        pipeline_version: int,
        cancel_requested: object,
    ) -> DatasetIdentity:
        _ = dataset, source_schema, cancel_requested
        fingerprint_calls.append(pipeline_version)
        return DatasetIdentity(
            fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
            dataset_fingerprint="a" * 64,
            source_schema_fingerprint="b" * 64,
            variable_ids=("outcome", "group"),
            pipeline_version=pipeline_version,
        )

    version = [11]
    runtime = ResearchFlowRuntime(
        pipeline_access=access,
        pipeline_version_provider=lambda: version[0],
        session_store=session,
        coordinator=UnusedCoordinator(),
        initial_event_id_factory=lambda: "event:initial:1",
        answer_event_id_factory=lambda: "event:answer:1",
        language=Language.KO,
        fingerprint=fingerprinter,
    )

    first = runtime.start(pipeline_version=11, cancel_event=Event())
    second = runtime.start(pipeline_version=11, cancel_event=Event())
    assert first.standard.state is ResearchFlowState.INTAKE_CAUSAL
    assert second.standard.state is ResearchFlowState.INTAKE_CAUSAL
    assert fingerprint_calls == [11]
    assert len(session.located) == 2

    version[0] = 12
    runtime.note_pipeline_version(12)
    runtime.start(pipeline_version=12, cancel_event=Event())
    assert fingerprint_calls == [11, 12]


@pytest.mark.parametrize(
    ("error", "expected_state"),
    (
        (
            TaskSessionUnavailableError("storage unavailable"),
            ResearchFlowState.MEMORY_UNAVAILABLE,
        ),
        (
            TaskSessionIntegrityError("ledger integrity"),
            ResearchFlowState.CORRUPTION,
        ),
        (ValueError("ordinary failure"), ResearchFlowState.FAILURE),
    ),
)
def test_runtime_preserves_closed_error_taxonomy(
    error: Exception,
    expected_state: ResearchFlowState,
) -> None:
    dataset = _small_dataset()
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="csv",
            sheet_name=None,
            header_row_index=None,
            header_row_count=None,
            data_start_row_index=None,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과", "group": "집단"},
    )
    runtime = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=RaisingSession(error),
        coordinator=UnusedCoordinator(),
        initial_event_id_factory=_queue(),
        answer_event_id_factory=_queue(),
        language=Language.KO,
    )

    views = runtime.start(pipeline_version=1, cancel_event=Event())

    assert views.standard.state is expected_state


def test_runtime_cancellation_is_not_reported_as_failure() -> None:
    dataset = _small_dataset()
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="csv",
            sheet_name=None,
            header_row_index=None,
            header_row_count=None,
            data_start_row_index=None,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과", "group": "집단"},
    )
    runtime = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=ReadOnlySession(),
        coordinator=UnusedCoordinator(),
        initial_event_id_factory=_queue(),
        answer_event_id_factory=_queue(),
        language=Language.KO,
    )
    cancelled = Event()
    cancelled.set()

    views = runtime.start(pipeline_version=1, cancel_event=cancelled)

    assert views.standard.state is ResearchFlowState.CANCELLED


@pytest.mark.parametrize("cooperative", (False, True))
def test_runtime_fingerprint_deadline_is_unavailable_and_never_cached(
    monkeypatch,
    cooperative: bool,
) -> None:
    dataset = _small_dataset()
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="csv",
            sheet_name=None,
            header_row_index=None,
            header_row_count=None,
            data_start_row_index=None,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과", "group": "집단"},
    )
    deadline_ns = FINGERPRINT_WORKER_DEADLINE_SECONDS * 1_000_000_000
    ticks = iter((0, deadline_ns + 1, deadline_ns + 2))
    monkeypatch.setattr(
        "modori.ui.research_flow_controller.monotonic_ns",
        lambda: next(ticks),
        raising=False,
    )

    def slow_fingerprint(
        _dataset,
        _source_schema,
        *,
        pipeline_version: int,
        cancel_requested,
    ) -> DatasetIdentity:
        if cooperative and cancel_requested():
            raise FingerprintCancelled("injected deadline cancellation")
        return DatasetIdentity(
            fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
            dataset_fingerprint="a" * 64,
            source_schema_fingerprint="b" * 64,
            variable_ids=("outcome", "group"),
            pipeline_version=pipeline_version,
        )

    session = ReadOnlySession()
    runtime = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=session,
        coordinator=UnusedCoordinator(),
        initial_event_id_factory=_queue(),
        answer_event_id_factory=_queue(),
        language=Language.KO,
        fingerprint=slow_fingerprint,
    )

    views = runtime.start(pipeline_version=1, cancel_event=Event())

    assert views.standard.state is ResearchFlowState.MEMORY_UNAVAILABLE
    assert runtime.current_dataset_fingerprint() is None
    assert session.located == []


def _queue(*values: str):
    iterator = iter(values)

    def next_value() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError("identity factory exhausted") from exc

    return next_value


def test_real_runtime_commits_then_recovers_multi_round_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "LOCALAPPDATA",
        str((tmp_path / "local-app-data").resolve()),
    )
    dataset = _small_dataset()
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="csv",
            sheet_name=None,
            header_row_index=0,
            header_row_count=1,
            data_start_row_index=1,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과 점수", "group": "집단"},
    )
    version = [1]
    runtime = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: version[0],
        session_store=ResearchTaskSessionStore(
            task_id_factory=_queue("task:live:1", "task:live:2"),
            utc_clock=lambda: "2026-07-17T00:00:00Z",
        ),
        coordinator=LiveResearchFlowCoordinator(
            event_id_factory=_queue(
                "event:passport:1",
                "event:passport:2",
                "event:passport:3",
                "event:passport:4",
                "event:retract:1",
            ),
            passport_object_id_factory=_queue(
                "passport:live:1",
                "passport:live:2",
                "passport:live:3",
                "passport:live:4",
            ),
            utc_clock=lambda: "2026-07-17T00:00:00Z",
        ),
        initial_event_id_factory=_queue("event:initial:1"),
        answer_event_id_factory=_queue(
            "event:answer:1",
            "event:answer:2",
            "event:answer:3",
        ),
        language=Language.KO,
    )

    started = runtime.start(pipeline_version=1, cancel_event=Event())
    assert started.standard.state is ResearchFlowState.INTAKE_CAUSAL
    assert not (tmp_path / "local-app-data" / "Modori").exists()

    current = runtime.commit_initial(
        profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
        roles=P1RoleBindings(outcome=("outcome",)),
        pipeline_version=1,
        cancel_event=Event(),
    )
    assert current.standard.state is ResearchFlowState.CLARIFY_READY
    assert (tmp_path / "local-app-data" / "Modori").is_dir()

    rounds = 0
    while current.standard.state is ResearchFlowState.CLARIFY_READY:
        rounds += 1
        assert rounds <= 3
        choices = tuple(
            option.option_id
            for option in current.standard.options
            if option.option_id != "not_sure"
        )
        if choices:
            current = runtime.answer(
                option_id=choices[0],
                variable_ids=(),
                not_sure=False,
                pipeline_version=1,
                cancel_event=Event(),
            )
        else:
            current = runtime.answer(
                option_id="variables",
                variable_ids=(),
                not_sure=False,
                pipeline_version=1,
                cancel_event=Event(),
            )

    assert rounds == 3
    assert current.standard.state is ResearchFlowState.CANDIDATE_READY
    assert current.standard.candidate is not None
    assert current.standard.primary_action is not None
    assert current.standard.primary_action.command is ResearchUiCommand.PREPARE

    recovered = runtime.start(pipeline_version=1, cancel_event=Event())
    assert recovered.standard.decision_identity_digest == (
        current.standard.decision_identity_digest
    )

    prepared = runtime.prepare(pipeline_version=1, cancel_event=Event())
    assert prepared.standard.state is ResearchFlowState.PREPARE_REVIEW
    assert prepared.preparation is not None
    assert prepared.preparation.preflight_disposition.value == "prepare_ready"

    retracted = runtime.retract(pipeline_version=1, cancel_event=Event())
    assert retracted.standard.state is ResearchFlowState.RETRACTED

    not_revived = runtime.resume(pipeline_version=1, cancel_event=Event())
    assert not_revived.standard.state is ResearchFlowState.RETRACTED

    replanned = runtime.replan(pipeline_version=1, cancel_event=Event())
    assert replanned.standard.state is ResearchFlowState.INTAKE_CAUSAL


def test_controller_queues_only_typed_durable_commands() -> None:
    cases = (
        (
            _clarify_views(),
            "retract",
            lambda controller: controller.retract(),
        ),
        (
            _candidate_views(),
            "prepare",
            lambda controller: controller.prepare(),
        ),
        (
            _transient_views(ResearchFlowState.REPLAN_REQUIRED),
            "replan",
            lambda controller: controller.replan(),
        ),
        (
            _transient_views(ResearchFlowState.MEMORY_UNAVAILABLE),
            "resume",
            lambda controller: controller.resume(),
        ),
    )
    for views, expected_call, invoke in cases:
        runtime = FakeRuntime(_transient_views(ResearchFlowState.FAILURE))
        worker = ControllableWorker()
        controller = _controller(runtime, worker, [9])
        controller._views = views

        assert invoke(controller) is True
        assert len(worker.submissions) == 1
        worker.execute()
        assert runtime.calls[0][0] == expected_call


def test_prepare_reviews_exact_settings_and_confirm_never_submits_run() -> None:
    profile = P1TaskProfile.LINEAR_CO_MOVEMENT
    preparation = _ready_preparation(profile)
    dataset = _valid_dataset(profile)
    pipeline = Pipeline(dataset)
    version = [1]
    commits: list[str] = []
    publications: list[str] = []

    def commit_pipeline_change(value) -> int:
        commits.append(value.preparation_digest)
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
        confirmation_published=lambda: publications.append("published"),
    )
    controller._views = candidate_views

    assert controller.prepare() is True
    assert len(worker.submissions) == 1
    worker.finish(worker.execute())

    assert controller.current_view.state is ResearchFlowState.PREPARE_REVIEW
    assert pipeline.steps == []
    review_model = controller.stateModel["preparationReview"]
    assert review_model["stepType"] == "stats.correlation"
    assert (
        review_model["visiblePreparationDigest"]
        == (preparation.preparation_digest[:12])
    )
    assert review_model["automaticRun"] is False

    assert controller.confirm() is True

    assert len(worker.submissions) == 1
    assert len(pipeline.steps) == 1
    assert pipeline.analysis_objects == {}
    assert version == [2]
    assert commits == [preparation.preparation_digest]
    assert publications == ["published"]
    assert controller.current_view.state is ResearchFlowState.CONFIRMED

    controller.adoptMode("guided")

    assert controller.current_view.state is ResearchFlowState.CONFIRMED
    assert controller.stateModel["preparationReview"] == review_model
    assert len(pipeline.steps) == 1
    assert controller.confirm() is False


def test_mode_change_discards_pending_confirmation_but_keeps_candidate() -> None:
    preparation = _ready_preparation(P1TaskProfile.LINEAR_CO_MOVEMENT)
    candidate_base = _candidate_views()
    review_base = _transient_views(ResearchFlowState.PREPARE_REVIEW)
    candidate = ResearchFlowViews(
        guided=candidate_base.guided,
        standard=candidate_base.standard,
        preparation=preparation,
    )
    review = ResearchFlowViews(
        guided=review_base.guided,
        standard=review_base.standard,
        preparation=preparation,
    )
    runtime = FakeRuntime(review)
    worker = ControllableWorker()
    version = [1]
    editor = ResearchPreparationEditor(
        PipelineOperations(Pipeline(_valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT))),
        version_provider=lambda: version[0],
        current_dataset_fingerprint=lambda: preparation.dataset_fingerprint,
        commit_pipeline_change=lambda _preparation: 2,
    )
    controller = ResearchFlowController(
        runtime=runtime,
        worker=worker,
        pipeline_version_provider=lambda: version[0],
        mode_change_request=lambda _mode: True,
        initial_mode=ControllerMode.STANDARD,
        language=Language.KO,
        preparation_editor=editor,
    )
    controller._views = candidate
    assert controller.prepare() is True
    worker.finish(worker.execute())
    assert controller.current_view.state is ResearchFlowState.PREPARE_REVIEW

    controller.adoptMode("guided")

    assert controller.current_view.state is ResearchFlowState.CANDIDATE_READY
    assert controller.confirm() is False


def test_retract_from_prepare_review_discards_uncommitted_confirmation() -> None:
    preparation = _ready_preparation(P1TaskProfile.LINEAR_CO_MOVEMENT)
    candidate_base = _candidate_views()
    review_base = _transient_views(ResearchFlowState.PREPARE_REVIEW)
    candidate = ResearchFlowViews(
        guided=candidate_base.guided,
        standard=candidate_base.standard,
        preparation=preparation,
    )
    review = ResearchFlowViews(
        guided=review_base.guided,
        standard=review_base.standard,
        preparation=preparation,
    )
    runtime = FakeRuntime(review)
    worker = ControllableWorker()
    version = [1]
    pipeline = Pipeline(_valid_dataset(P1TaskProfile.LINEAR_CO_MOVEMENT))
    editor = ResearchPreparationEditor(
        PipelineOperations(pipeline),
        version_provider=lambda: version[0],
        current_dataset_fingerprint=lambda: preparation.dataset_fingerprint,
        commit_pipeline_change=lambda _preparation: 2,
    )
    controller = ResearchFlowController(
        runtime=runtime,
        worker=worker,
        pipeline_version_provider=lambda: version[0],
        mode_change_request=lambda _mode: True,
        initial_mode=ControllerMode.STANDARD,
        language=Language.KO,
        preparation_editor=editor,
    )
    controller._views = candidate
    assert controller.prepare() is True
    worker.finish(worker.execute())
    assert controller.current_view.state is ResearchFlowState.PREPARE_REVIEW

    runtime.start_result = _transient_views(ResearchFlowState.FAILURE)
    assert controller.retract() is True

    assert controller.confirm() is False
    assert pipeline.steps == []
    assert len(worker.submissions) == 2
    retracted = worker.execute()
    assert runtime.calls[-1][0] == "retract"
    worker.finish(retracted)
    assert controller.current_view.state is ResearchFlowState.FAILURE


def test_ui_controller_commits_research_os_provenance_once_and_manual_edit_clears_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = P1TaskProfile.LINEAR_CO_MOVEMENT
    preparation = _ready_preparation(profile, version=0)
    candidate_base = _candidate_views()
    review_base = _transient_views(ResearchFlowState.PREPARE_REVIEW)
    candidate = ResearchFlowViews(
        guided=candidate_base.guided,
        standard=candidate_base.standard,
        preparation=preparation,
    )
    review = ResearchFlowViews(
        guided=review_base.guided,
        standard=review_base.standard,
        preparation=preparation,
    )
    runtime = FakeRuntime(
        review,
        dataset_fingerprint=preparation.dataset_fingerprint,
    )
    monkeypatch.setattr(
        UiControllerServices,
        "build_research_flow_runtime",
        lambda self, *, pipeline_version_provider: runtime,
    )
    worker = ControllableWorker()
    host = UiController(pipeline=Pipeline(_valid_dataset(profile)), worker=worker)
    flow = host.researchFlow
    assert isinstance(flow, ResearchFlowController)
    flow._views = candidate

    assert flow.prepare() is True
    worker.finish(worker.execute())
    assert flow.confirm() is True

    assert host.pipeline_version == 1
    assert len(host.pipeline.steps) == 1
    assert host.selectionProvenance == "research_os_assisted"
    assert host._session.research_os_preparation_digest == (
        preparation.preparation_digest
    )
    assert flow.current_view.state is ResearchFlowState.CONFIRMED
    assert len(worker.submissions) == 1

    changed = host.configureCorrelationSelection("y, x")

    assert changed.ok is True
    assert host.selectionProvenance == "manual"
    assert host._session.research_os_preparation_digest is None
    assert flow.current_view.state is ResearchFlowState.REPLAN_REQUIRED


class SimulatedRuntimeCrash(RuntimeError):
    pass


def test_reopen_publishes_pending_and_only_explicit_resume_commits_passport(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "LOCALAPPDATA",
        str((tmp_path / "local-app-data").resolve()),
    )
    dataset = _small_dataset()
    snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="csv",
            sheet_name=None,
            header_row_index=0,
            header_row_count=1,
            data_start_row_index=1,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과 점수", "group": "집단"},
    )
    session = ResearchTaskSessionStore(
        task_id_factory=_queue("task:pending:1"),
        utc_clock=lambda: None,
    )

    def poison(stage: str) -> None:
        if stage == "after_request_initialize":
            raise SimulatedRuntimeCrash(stage)

    interrupted = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=session,
        coordinator=LiveResearchFlowCoordinator(
            event_id_factory=_queue("event:unused:1"),
            passport_object_id_factory=_queue("passport:unused:1"),
            utc_clock=lambda: None,
            poison_hook=poison,
        ),
        initial_event_id_factory=_queue("event:initial:pending"),
        answer_event_id_factory=_queue(),
        language=Language.KO,
    )
    interrupted.start(pipeline_version=1, cancel_event=Event())
    with pytest.raises(SimulatedRuntimeCrash, match="after_request_initialize"):
        interrupted.commit_initial(
            profile=P1TaskProfile.NUMERIC_DISTRIBUTION,
            roles=P1RoleBindings(outcome=("outcome",)),
            pipeline_version=1,
            cancel_event=Event(),
        )

    passport_events: list[str] = []

    def passport_event() -> str:
        passport_events.append("event:passport:resumed")
        return passport_events[-1]

    reopened = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=session,
        coordinator=LiveResearchFlowCoordinator(
            event_id_factory=passport_event,
            passport_object_id_factory=_queue("passport:resumed:1"),
            utc_clock=lambda: None,
        ),
        initial_event_id_factory=_queue(),
        answer_event_id_factory=_queue(),
        language=Language.KO,
    )

    pending = reopened.start(pipeline_version=1, cancel_event=Event())
    assert pending.standard.state is ResearchFlowState.RECOVERY_PENDING
    assert passport_events == []

    drifted_snapshot = ResearchFlowPipelineSnapshot(
        dataset=dataset,
        source_schema=SourceSchemaDescriptor(
            source_type="xlsx",
            sheet_name="다른 시트",
            header_row_index=1,
            header_row_count=1,
            data_start_row_index=2,
            source_columns=("outcome", "group"),
            included_columns=("outcome", "group"),
        ),
        variable_labels={"outcome": "결과 점수", "group": "집단"},
    )
    drifted = ResearchFlowRuntime(
        pipeline_access=SnapshotAccess(drifted_snapshot),
        pipeline_version_provider=lambda: 1,
        session_store=session,
        coordinator=LiveResearchFlowCoordinator(
            event_id_factory=_queue(),
            passport_object_id_factory=_queue(),
            utc_clock=lambda: None,
        ),
        initial_event_id_factory=_queue(),
        answer_event_id_factory=_queue(),
        language=Language.KO,
    ).start(pipeline_version=1, cancel_event=Event())
    assert drifted.standard.state is ResearchFlowState.REPLAN_REQUIRED

    resumed = reopened.resume(pipeline_version=1, cancel_event=Event())
    assert resumed.standard.state is ResearchFlowState.CLARIFY_READY
    assert passport_events == ["event:passport:resumed"]
