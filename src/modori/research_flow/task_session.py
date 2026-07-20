"""Crash-recoverable binding between task locators and verified ledgers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modori.research_flow.contracts import DatasetIdentity
from modori.research_memory.ledger_contracts import LedgerHead
from modori.research_memory.ledger_store import (
    DecisionLedgerStore,
    LedgerIntegrityError,
    LedgerPathError,
    LedgerRuntimeError,
    LedgerStoreError,
    default_ledger_path,
)
from modori.research_memory.task_index import (
    ResearchTaskIndex,
    ResearchTaskRecord,
    ResearchTaskState,
    TaskIndexConflictError,
    TaskIndexError,
    TaskIndexIntegrityError,
    TaskIndexUnavailableError,
)


class TaskSessionError(RuntimeError):
    """Base error for recoverable Research OS task sessions."""


class TaskSessionConflictError(TaskSessionError):
    """Raised when caller state no longer names the exact active task."""


class TaskSessionIntegrityError(TaskSessionError):
    """Raised when a locator or ledger cannot be verified as one task."""


class TaskSessionUnavailableError(TaskSessionError):
    """Raised when secure local session storage is unavailable."""


PoisonHook = Callable[[str], None]
TaskIdFactory = Callable[[], str]
UtcClock = Callable[[], str | None]


@dataclass(frozen=True)
class ResearchTaskHandle:
    """A verified locator result without an open store or execution authority."""

    record: ResearchTaskRecord
    ledger_path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.record, ResearchTaskRecord):
            raise TaskSessionIntegrityError("record must be a ResearchTaskRecord")
        if self.record.state is not ResearchTaskState.ACTIVE:
            raise TaskSessionIntegrityError("task handle must name an active record")
        if not isinstance(self.ledger_path, Path) or not self.ledger_path.is_absolute():
            raise TaskSessionIntegrityError("ledger_path must be one absolute Path")


class ResearchTaskSessionStore:
    """Coordinate recoverable locator and ledger boundaries without claiming atomicity."""

    def __init__(
        self,
        *,
        task_id_factory: TaskIdFactory,
        utc_clock: UtcClock,
        poison_hook: PoisonHook | None = None,
    ) -> None:
        if not callable(task_id_factory):
            raise TaskSessionError("task_id_factory must be callable")
        if not callable(utc_clock):
            raise TaskSessionError("utc_clock must be callable")
        if poison_hook is not None and not callable(poison_hook):
            raise TaskSessionError("poison_hook must be callable or null")
        self._task_id_factory = task_id_factory
        self._utc_clock = utc_clock
        self._poison_hook = poison_hook

    def _poison(self, stage: str) -> None:
        if self._poison_hook is not None:
            self._poison_hook(stage)

    @staticmethod
    def _require_identity(identity: object) -> DatasetIdentity:
        if not isinstance(identity, DatasetIdentity):
            raise TaskSessionError("identity must be a DatasetIdentity")
        return identity

    @staticmethod
    def _expected_path(task_project_id: str) -> Path:
        try:
            return default_ledger_path(task_project_id)
        except LedgerPathError as exc:
            raise TaskSessionUnavailableError(
                "application-owned task ledger path is unavailable"
            ) from exc

    @staticmethod
    def _validate_record_for_identity(
        record: ResearchTaskRecord,
        identity: DatasetIdentity,
    ) -> None:
        if (
            record.fingerprint_contract_id != identity.fingerprint_contract_id
            or record.dataset_fingerprint != identity.dataset_fingerprint
        ):
            raise TaskSessionIntegrityError(
                "task locator record does not match the requested dataset identity"
            )

    @staticmethod
    def _same_record_identity(
        supplied: ResearchTaskRecord,
        current: ResearchTaskRecord,
    ) -> bool:
        return (
            supplied.task_project_id == current.task_project_id
            and supplied.fingerprint_contract_id == current.fingerprint_contract_id
            and supplied.dataset_fingerprint == current.dataset_fingerprint
            and supplied.task_ordinal == current.task_ordinal
            and supplied.created_at_utc == current.created_at_utc
        )

    def _create_verified_empty_ledger(
        self,
        task_project_id: str,
        path: Path,
    ) -> None:
        self._poison("before_ledger_create")
        try:
            with DecisionLedgerStore.create(path, task_project_id) as ledger:
                report = ledger.verify(full_integrity=True)
                if (
                    report.head != LedgerHead.genesis()
                    or report.event_count != 0
                    or report.artifact_count != 0
                    or ledger.events()
                    or ledger.artifacts()
                ):
                    raise TaskSessionIntegrityError(
                        "new task ledger is not a genuine empty ledger"
                    )
        except TaskSessionError:
            raise
        except LedgerPathError as exc:
            raise TaskSessionConflictError(
                "fresh task ledger identity or path is already in use"
            ) from exc
        except LedgerRuntimeError as exc:
            raise TaskSessionUnavailableError(
                "secure task ledger runtime is unavailable"
            ) from exc
        except (LedgerIntegrityError, LedgerStoreError, OSError) as exc:
            raise TaskSessionIntegrityError(
                "new task ledger failed full verification"
            ) from exc
        self._poison("after_ledger_create")

    def _verified_handle(self, record: ResearchTaskRecord) -> ResearchTaskHandle:
        if record.state is not ResearchTaskState.ACTIVE:
            raise TaskSessionIntegrityError("located task is not active")
        try:
            path = self._expected_path(record.task_project_id)
        except TaskSessionUnavailableError as exc:
            raise TaskSessionIntegrityError(
                "active task ledger path failed secure derivation"
            ) from exc
        self._poison("before_ledger_verify")
        if not path.is_file():
            raise TaskSessionIntegrityError(
                "active task ledger is missing and will not be recreated"
            )
        try:
            with DecisionLedgerStore.open(path, record.task_project_id) as ledger:
                report = ledger.verify(full_integrity=True)
                if report.head == LedgerHead.genesis():
                    if (
                        report.event_count != 0
                        or report.artifact_count != 0
                        or ledger.events()
                        or ledger.artifacts()
                    ):
                        raise TaskSessionIntegrityError(
                            "empty task ledger contains uncommitted state"
                        )
                else:
                    request = ledger.load_request()
                    project_ids = {
                        request.question.envelope.project_id,
                        request.estimand.envelope.project_id,
                        request.study.envelope.project_id,
                    }
                    if project_ids != {record.task_project_id}:
                        raise TaskSessionIntegrityError(
                            "initialized task ledger project binding is invalid"
                        )
        except TaskSessionError:
            raise
        except LedgerRuntimeError as exc:
            raise TaskSessionUnavailableError(
                "secure task ledger runtime is unavailable"
            ) from exc
        except (
            LedgerPathError,
            LedgerIntegrityError,
            LedgerStoreError,
            OSError,
        ) as exc:
            raise TaskSessionIntegrityError(
                "active task ledger failed full verification"
            ) from exc
        handle = ResearchTaskHandle(record=record, ledger_path=path)
        self._poison("after_ledger_verify")
        return handle

    def _new_task_identity(self) -> tuple[str, Path, str | None]:
        try:
            task_project_id = self._task_id_factory()
            created_at_utc = self._utc_clock()
        except Exception as exc:
            raise TaskSessionUnavailableError(
                "task identity or UTC clock factory failed"
            ) from exc
        if not isinstance(task_project_id, str):
            raise TaskSessionIntegrityError(
                "task ID factory returned a non-string identity"
            )
        path = self._expected_path(task_project_id)
        return task_project_id, path, created_at_utc

    @staticmethod
    def _translate_index_error(exc: TaskIndexError) -> TaskSessionError:
        if isinstance(exc, TaskIndexConflictError):
            return TaskSessionConflictError("task locator transition conflicted")
        if isinstance(exc, TaskIndexUnavailableError):
            return TaskSessionUnavailableError(
                f"task locator is unavailable: {exc.reason_code.value}"
            )
        if isinstance(exc, TaskIndexIntegrityError):
            return TaskSessionIntegrityError("task locator integrity failed")
        return TaskSessionUnavailableError("task locator could not be opened")

    def open_or_allocate(
        self,
        identity: DatasetIdentity,
        *,
        expected_active_task_id: str | None,
    ) -> ResearchTaskHandle:
        """Resume the exact active task or publish a preverified empty ledger."""

        identity = self._require_identity(identity)
        try:
            with ResearchTaskIndex.open_or_create() as index:
                active = index.locate_active(
                    identity.fingerprint_contract_id,
                    identity.dataset_fingerprint,
                )
                if active is not None:
                    if (
                        expected_active_task_id is not None
                        and active.task_project_id != expected_active_task_id
                    ):
                        raise TaskSessionConflictError(
                            "expected active task ID no longer matches the locator"
                        )
                    self._validate_record_for_identity(active, identity)
                    return self._verified_handle(active)
                if expected_active_task_id is not None:
                    raise TaskSessionConflictError(
                        "expected active task is no longer present"
                    )

                task_project_id, path, created_at_utc = self._new_task_identity()
                self._create_verified_empty_ledger(task_project_id, path)
                self._poison("before_index_allocate")
                try:
                    record = index.allocate(
                        identity.fingerprint_contract_id,
                        identity.dataset_fingerprint,
                        task_project_id=task_project_id,
                        created_at_utc=created_at_utc,
                    )
                except TaskIndexConflictError:
                    record = index.locate_active(
                        identity.fingerprint_contract_id,
                        identity.dataset_fingerprint,
                    )
                    if record is None:
                        raise
                self._poison("after_index_allocate")
                self._validate_record_for_identity(record, identity)
                return self._verified_handle(record)
        except TaskSessionError:
            raise
        except TaskIndexError as exc:
            raise self._translate_index_error(exc) from exc

    def locate_existing(
        self,
        identity: DatasetIdentity,
    ) -> ResearchTaskHandle | None:
        """Locate and fully verify an active task without creating any state."""

        identity = self._require_identity(identity)
        try:
            index = ResearchTaskIndex.open_existing()
            if index is None:
                return None
            with index:
                active = index.locate_active(
                    identity.fingerprint_contract_id,
                    identity.dataset_fingerprint,
                )
                if active is None:
                    return None
                self._validate_record_for_identity(active, identity)
                return self._verified_handle(active)
        except TaskSessionError:
            raise
        except TaskIndexError as exc:
            raise self._translate_index_error(exc) from exc

    def start_replan(
        self,
        previous: ResearchTaskHandle,
        new_identity: DatasetIdentity,
        *,
        expected_previous_head: LedgerHead | None = None,
    ) -> ResearchTaskHandle:
        """Create a fresh task while preserving and closing the exact prior locator."""

        if not isinstance(previous, ResearchTaskHandle):
            raise TaskSessionError("previous must be a ResearchTaskHandle")
        new_identity = self._require_identity(new_identity)
        if expected_previous_head is not None:
            if not isinstance(expected_previous_head, LedgerHead):
                raise TaskSessionError(
                    "expected_previous_head must be a LedgerHead or null"
                )
            expected_previous_head.__post_init__()
        try:
            with ResearchTaskIndex.open_or_create() as index:
                current_previous = index.get(previous.record.task_project_id)
                if current_previous is None:
                    raise TaskSessionIntegrityError(
                        "previous task locator record is missing"
                    )
                if not self._same_record_identity(
                    previous.record,
                    current_previous,
                ):
                    raise TaskSessionIntegrityError(
                        "previous handle record no longer matches locator identity"
                    )
                try:
                    expected_path = self._expected_path(previous.record.task_project_id)
                except TaskSessionUnavailableError as exc:
                    raise TaskSessionIntegrityError(
                        "previous task ledger path failed secure derivation"
                    ) from exc
                if previous.ledger_path != expected_path:
                    raise TaskSessionIntegrityError(
                        "previous handle ledger path is not application-derived"
                    )
                if not expected_path.is_file():
                    raise TaskSessionIntegrityError("previous task ledger is missing")

                def verify_previous_ledger() -> None:
                    try:
                        with DecisionLedgerStore.open(
                            expected_path,
                            previous.record.task_project_id,
                        ) as previous_ledger:
                            report = previous_ledger.verify(full_integrity=True)
                    except (LedgerStoreError, OSError) as exc:
                        raise TaskSessionIntegrityError(
                            "previous task ledger failed full verification"
                        ) from exc
                    if (
                        expected_previous_head is not None
                        and report.head != expected_previous_head
                    ):
                        raise TaskSessionConflictError(
                            "previous task ledger head changed before replan"
                        )

                verify_previous_ledger()

                same_index_identity = (
                    previous.record.fingerprint_contract_id
                    == new_identity.fingerprint_contract_id
                    and previous.record.dataset_fingerprint
                    == new_identity.dataset_fingerprint
                )
                if expected_previous_head is not None and not same_index_identity:
                    raise TaskSessionConflictError(
                        "expected ledger head guard requires the same dataset identity"
                    )
                active_new = index.locate_active(
                    new_identity.fingerprint_contract_id,
                    new_identity.dataset_fingerprint,
                )
                if active_new is not None and (
                    active_new.task_project_id != previous.record.task_project_id
                ):
                    self._validate_record_for_identity(active_new, new_identity)
                    if current_previous.state is ResearchTaskState.ACTIVE:
                        index.mark_readonly(current_previous.task_project_id)
                        self._poison("after_previous_mark_readonly")
                    return self._verified_handle(active_new)

                if active_new is None and current_previous.state is not (
                    ResearchTaskState.ACTIVE
                ):
                    raise TaskSessionIntegrityError(
                        "readonly previous task has no recoverable replacement"
                    )
                if (
                    active_new is not None
                    and active_new.task_project_id == previous.record.task_project_id
                    and current_previous.state is not ResearchTaskState.ACTIVE
                ):
                    raise TaskSessionIntegrityError(
                        "locator active state disagrees with previous task"
                    )

                task_project_id, path, created_at_utc = self._new_task_identity()
                if task_project_id == previous.record.task_project_id:
                    raise TaskSessionConflictError("replan task ID must be fresh")
                replace_guard = None
                if same_index_identity and expected_previous_head is not None:

                    def prepare_same_identity_replacement() -> None:
                        verify_previous_ledger()
                        self._create_verified_empty_ledger(task_project_id, path)

                    replace_guard = prepare_same_identity_replacement
                else:
                    self._create_verified_empty_ledger(task_project_id, path)
                self._poison("before_replan_index_allocate")
                record = index.allocate(
                    new_identity.fingerprint_contract_id,
                    new_identity.dataset_fingerprint,
                    task_project_id=task_project_id,
                    created_at_utc=created_at_utc,
                    replaces_task_project_id=(
                        previous.record.task_project_id if same_index_identity else None
                    ),
                    replace_guard=replace_guard,
                )
                self._poison("after_replan_index_allocate")
                if (
                    not same_index_identity
                    and current_previous.state is ResearchTaskState.ACTIVE
                ):
                    index.mark_readonly(current_previous.task_project_id)
                    self._poison("after_previous_mark_readonly")
                self._validate_record_for_identity(record, new_identity)
                return self._verified_handle(record)
        except TaskSessionError:
            raise
        except TaskIndexError as exc:
            raise self._translate_index_error(exc) from exc
