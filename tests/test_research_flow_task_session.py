from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sqlite3

import pytest

from modori.research_flow import (
    FINGERPRINT_CONTRACT_ID,
    DatasetIdentity,
    ResearchTaskHandle,
    ResearchTaskSessionStore,
    TaskSessionConflictError,
    TaskSessionIntegrityError,
)
from modori.research_memory import (
    DecisionLedgerStore,
    ResearchMemoryCoordinator,
    ResearchTaskIndex,
    ResearchTaskState,
    default_ledger_path,
)
from modori.research_os import (
    Language,
    P1IntakeDraft,
    P1RoleBindings,
    P1TaskProfile,
    build_p1_request,
)


class SimulatedCrash(RuntimeError):
    pass


def _set_local_app_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = (tmp_path / "local-app-data").resolve()
    monkeypatch.setenv("LOCALAPPDATA", str(root))
    return root


def _identity(
    *,
    dataset: str = "a" * 64,
    schema: str = "b" * 64,
    pipeline_version: int = 1,
) -> DatasetIdentity:
    return DatasetIdentity(
        fingerprint_contract_id=FINGERPRINT_CONTRACT_ID,
        dataset_fingerprint=dataset,
        source_schema_fingerprint=schema,
        variable_ids=("outcome", "x"),
        pipeline_version=pipeline_version,
    )


def _id_factory(*values: str):
    iterator = iter(values)

    def next_id() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError("task ID factory was called too many times") from exc

    return next_id


def _session(
    *task_ids: str,
    poison_stage: str | None = None,
) -> ResearchTaskSessionStore:
    fired = False

    def poison(stage: str) -> None:
        nonlocal fired
        if not fired and stage == poison_stage:
            fired = True
            raise SimulatedCrash(stage)

    return ResearchTaskSessionStore(
        task_id_factory=_id_factory(*task_ids),
        utc_clock=lambda: "2026-07-17T00:00:00Z",
        poison_hook=poison,
    )


def _initialize(handle: ResearchTaskHandle) -> None:
    request = build_p1_request(
        P1IntakeDraft(
            P1TaskProfile.NUMERIC_DISTRIBUTION,
            P1RoleBindings(outcome=("outcome", "x")),
        ),
        task_project_id=handle.record.task_project_id,
        initial_event_id="event:project:1",
        dataset_fingerprint=handle.record.dataset_fingerprint,
        source_schema_fingerprint="b" * 64,
        available_variable_ids=("outcome", "x"),
        language=Language.KO,
    )
    with DecisionLedgerStore.open(
        handle.ledger_path,
        handle.record.task_project_id,
    ) as ledger:
        ResearchMemoryCoordinator().initialize(
            ledger,
            request,
            event_id="event:project:1",
            recorded_at_utc=None,
        )


def test_handle_is_frozen_exact_and_carries_no_store_authority() -> None:
    assert tuple(ResearchTaskHandle.__dataclass_fields__) == (
        "record",
        "ledger_path",
    )
    forbidden = {"connection", "store", "execute", "request", "passport"}
    assert forbidden.isdisjoint(ResearchTaskHandle.__dataclass_fields__)


def test_new_session_creates_verified_empty_ledger_before_active_locator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    handle = _session("task:first").open_or_allocate(
        identity,
        expected_active_task_id=None,
    )

    assert handle.record.task_project_id == "task:first"
    assert handle.record.task_ordinal == 1
    assert handle.record.state is ResearchTaskState.ACTIVE
    assert handle.ledger_path == default_ledger_path("task:first")
    assert handle.ledger_path.is_file()
    with pytest.raises(FrozenInstanceError):
        handle.ledger_path = Path("other")  # type: ignore[misc]
    with DecisionLedgerStore.open(handle.ledger_path, "task:first") as ledger:
        report = ledger.verify(full_integrity=True)
        assert report.head.sequence == 0
        assert report.event_count == 0
        assert report.artifact_count == 0
        assert ledger.events() == ()
        assert ledger.artifacts() == ()
    with ResearchTaskIndex.open_or_create() as index:
        assert (
            index.locate_active(
                identity.fingerprint_contract_id,
                identity.dataset_fingerprint,
            )
            == handle.record
        )


def test_initialized_session_reopens_exact_task_without_allocating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    handle = _session("task:first").open_or_allocate(
        identity,
        expected_active_task_id=None,
    )
    _initialize(handle)

    def forbidden_id() -> str:
        pytest.fail("verified active task attempted to allocate another ID")

    reopened = ResearchTaskSessionStore(
        task_id_factory=forbidden_id,
        utc_clock=lambda: None,
    ).open_or_allocate(
        identity,
        expected_active_task_id="task:first",
    )

    assert reopened == handle
    with DecisionLedgerStore.open(reopened.ledger_path, "task:first") as ledger:
        report = ledger.verify(full_integrity=True)
        assert report.head.sequence == 1
        assert report.event_count == 1
        assert ledger.load_request().question.envelope.project_id == "task:first"


_INITIAL_CRASH_STAGES = (
    "before_ledger_create",
    "after_ledger_create",
    "before_index_allocate",
    "after_index_allocate",
    "before_ledger_verify",
    "after_ledger_verify",
)


@pytest.mark.parametrize("stage", _INITIAL_CRASH_STAGES)
def test_crash_recovery_never_spends_a_second_ordinal_or_recreates_missing_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    session = _session("task:first", "task:second", poison_stage=stage)

    with pytest.raises(SimulatedCrash, match=stage):
        session.open_or_allocate(identity, expected_active_task_id=None)

    recovered = session.open_or_allocate(identity, expected_active_task_id=None)
    assert recovered.record.task_ordinal == 1
    if stage in {
        "after_index_allocate",
        "before_ledger_verify",
        "after_ledger_verify",
    }:
        assert recovered.record.task_project_id == "task:first"
    else:
        assert recovered.record.task_project_id == "task:second"
    with ResearchTaskIndex.open_or_create() as index:
        assert index.verify(full_integrity=True).row_count == 1
    with DecisionLedgerStore.open(
        recovered.ledger_path,
        recovered.record.task_project_id,
    ) as ledger:
        assert ledger.verify(full_integrity=True).head.sequence == 0

    first_path = default_ledger_path("task:first")
    if stage in {"after_ledger_create", "before_index_allocate"}:
        assert first_path.is_file()
        with DecisionLedgerStore.open(first_path, "task:first") as orphan:
            assert orphan.verify(full_integrity=True).head.sequence == 0


def test_expected_active_identity_mismatch_fails_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    handle = _session("task:first").open_or_allocate(
        identity,
        expected_active_task_id=None,
    )
    with ResearchTaskIndex.open_or_create() as index:
        before = index.verify(full_integrity=True)

    with pytest.raises(TaskSessionConflictError, match="expected|active"):
        _session("task:unused").open_or_allocate(
            identity,
            expected_active_task_id="task:other",
        )
    with ResearchTaskIndex.open_or_create() as index:
        assert index.verify(full_integrity=True) == before
        assert index.get(handle.record.task_project_id) == handle.record


@pytest.mark.parametrize("damage", ("missing", "corrupt", "foreign", "reparse"))
def test_active_locator_never_recreates_missing_foreign_or_corrupt_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    handle = _session("task:first").open_or_allocate(
        identity,
        expected_active_task_id=None,
    )
    path = handle.ledger_path
    if damage == "missing":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(b"not-sqlite")
    elif damage == "foreign":
        external = sqlite3.connect(path, isolation_level=None)
        external.execute("PRAGMA application_id=1")
        external.close()
    else:
        target = path.with_name("real-ledger.sqlite3")
        path.replace(target)
        try:
            path.symlink_to(target)
        except OSError as exc:
            target.replace(path)
            pytest.skip(f"file symlink creation unavailable: {exc}")

    with pytest.raises(TaskSessionIntegrityError):
        _session("task:must-not-be-used").open_or_allocate(
            identity,
            expected_active_task_id="task:first",
        )
    with ResearchTaskIndex.open_or_create() as index:
        assert index.get("task:first") == handle.record
        assert index.verify(full_integrity=True).row_count == 1
    if damage == "missing":
        assert not path.exists()


def test_session_rejects_locator_record_or_ledger_project_splice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    wrong_path = default_ledger_path("task:spliced")
    with DecisionLedgerStore.create(wrong_path, "task:other"):
        pass
    with ResearchTaskIndex.open_or_create() as index:
        record = index.allocate(
            identity.fingerprint_contract_id,
            identity.dataset_fingerprint,
            task_project_id="task:spliced",
            created_at_utc=None,
        )

    with pytest.raises(TaskSessionIntegrityError, match="ledger|project"):
        _session("task:unused").open_or_allocate(
            identity,
            expected_active_task_id=record.task_project_id,
        )


def test_same_fingerprint_correction_allocates_next_ordinal_and_preserves_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    session = _session("task:first", "task:corrected")
    previous = session.open_or_allocate(identity, expected_active_task_id=None)
    _initialize(previous)
    with DecisionLedgerStore.open(
        previous.ledger_path,
        previous.record.task_project_id,
    ) as old:
        old_head = old.head
        old_events = old.events()
        old_artifacts = old.artifacts()

    corrected = session.start_replan(previous, identity)

    assert corrected.record.task_project_id == "task:corrected"
    assert corrected.record.task_ordinal == 2
    assert corrected.record.state is ResearchTaskState.ACTIVE
    with ResearchTaskIndex.open_or_create() as index:
        assert index.get("task:first").state is ResearchTaskState.READONLY
        assert index.locate_active(
            identity.fingerprint_contract_id,
            identity.dataset_fingerprint,
        ) == corrected.record
    with DecisionLedgerStore.open(
        previous.ledger_path,
        previous.record.task_project_id,
    ) as old:
        assert old.verify(full_integrity=True).head == old_head
        assert old.events() == old_events
        assert old.artifacts() == old_artifacts
    with DecisionLedgerStore.open(
        corrected.ledger_path,
        corrected.record.task_project_id,
    ) as new:
        assert new.verify(full_integrity=True).head.sequence == 0


def test_dataset_drift_allocates_new_identity_and_marks_previous_readonly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    old_identity = _identity()
    new_identity = _identity(dataset="c" * 64, schema="d" * 64)
    session = _session("task:first", "task:drift")
    previous = session.open_or_allocate(
        old_identity,
        expected_active_task_id=None,
    )

    current = session.start_replan(previous, new_identity)

    assert current.record.task_project_id == "task:drift"
    assert current.record.dataset_fingerprint == new_identity.dataset_fingerprint
    assert current.record.task_ordinal == 1
    with ResearchTaskIndex.open_or_create() as index:
        assert index.get("task:first").state is ResearchTaskState.READONLY
        assert index.locate_active(
            new_identity.fingerprint_contract_id,
            new_identity.dataset_fingerprint,
        ) == current.record


@pytest.mark.parametrize(
    "stage",
    ("after_replan_index_allocate", "after_previous_mark_readonly"),
)
def test_drift_replan_recovers_cross_index_boundary_without_new_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    old_identity = _identity()
    new_identity = _identity(dataset="c" * 64, schema="d" * 64)
    initial = _session("task:first")
    previous = initial.open_or_allocate(
        old_identity,
        expected_active_task_id=None,
    )
    crashing = _session("task:drift", poison_stage=stage)
    with pytest.raises(SimulatedCrash, match=stage):
        crashing.start_replan(previous, new_identity)

    def forbidden_id() -> str:
        pytest.fail("replan recovery attempted to allocate a second task")

    recovered = ResearchTaskSessionStore(
        task_id_factory=forbidden_id,
        utc_clock=lambda: None,
    ).start_replan(previous, new_identity)

    assert recovered.record.task_project_id == "task:drift"
    assert recovered.record.task_ordinal == 1
    with ResearchTaskIndex.open_or_create() as index:
        assert index.get("task:first").state is ResearchTaskState.READONLY
        assert index.verify(full_integrity=True).row_count == 2


def test_replan_rejects_tampered_previous_identity_before_allocating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_local_app_data(tmp_path, monkeypatch)
    identity = _identity()
    previous = _session("task:first").open_or_allocate(
        identity,
        expected_active_task_id=None,
    )
    forged = replace(
        previous,
        record=replace(previous.record, dataset_fingerprint="f" * 64),
    )

    with pytest.raises(TaskSessionIntegrityError, match="record|identity"):
        _session("task:unused").start_replan(forged, identity)
    with ResearchTaskIndex.open_or_create() as index:
        assert index.verify(full_integrity=True).row_count == 1
