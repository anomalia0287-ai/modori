"""Durable commit-before-publication coordination for the live Research OS."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Literal, TypeAlias

from modori.research_flow.task_session import ResearchTaskHandle
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerEvent,
    LedgerEventKind,
)
from modori.research_memory.ledger_store import (
    DecisionLedgerStore,
    LedgerIntegrityError,
    LedgerPathError,
    LedgerRuntimeError,
    LedgerStoreError,
    default_ledger_path,
)
from modori.research_memory.passport_state import (
    CommittedPassportRecord,
    PassportHistory,
    PassportStateError,
)
from modori.research_memory.promotion import (
    PromotionError,
    ResearchMemoryCoordinator,
)
from modori.research_memory.task_index import (
    ResearchTaskIndex,
    ResearchTaskState,
    TaskIndexConflictError,
    TaskIndexError,
    TaskIndexIntegrityError,
)
from modori.research_os import (
    AnalysisPassport,
    ClarificationAnswerEvent,
    ClarificationLifecycle,
    PrimaryAction,
    ResearchRequest,
    ResearchServiceError,
    build_p1_clarification_registry,
    build_p1_method_space,
    validate_passport_request_binding,
)


class LiveResearchFlowError(RuntimeError):
    """Base failure at the durable live-flow boundary."""


class LiveResearchFlowConflictError(LiveResearchFlowError):
    """Raised when a caller tries to advance stale or already-closed authority."""


class LiveResearchFlowIntegrityError(LiveResearchFlowError):
    """Raised when durable state cannot support one unambiguous projection."""


class LiveResearchFlowUnavailableError(LiveResearchFlowError):
    """Raised when secure local persistence cannot be used."""


_DIGEST_CHARS = frozenset("0123456789abcdef")
_PUBLISHABLE_ACTIONS = frozenset(
    {
        PrimaryAction.RECOMMEND_LOCAL,
        PrimaryAction.CLARIFY,
        PrimaryAction.ABSTAIN,
    }
)
_DURABLE_COORDINATOR_SEAL = object()


def _require_coordinator_seal(value: object) -> None:
    if value is not _DURABLE_COORDINATOR_SEAL:
        raise LiveResearchFlowIntegrityError(
            "durable records require a verified coordinator seal"
        )


def _require_reference(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise LiveResearchFlowIntegrityError(f"{field_name} must be a non-empty string")
    return value


def _require_digest(value: object, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _DIGEST_CHARS for character in value)
    ):
        raise LiveResearchFlowIntegrityError(
            f"{field_name} must be a lowercase SHA-256 digest"
        )
    return value


def _require_sequence(value: object, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise LiveResearchFlowIntegrityError(f"{field_name} must be a positive integer")
    return value


def _request_project_id(request: ResearchRequest) -> str:
    if not isinstance(request, ResearchRequest):
        raise LiveResearchFlowIntegrityError("request must be a ResearchRequest")
    projects = {
        request.question.envelope.project_id,
        request.estimand.envelope.project_id,
        request.study.envelope.project_id,
    }
    if len(projects) != 1:
        raise LiveResearchFlowIntegrityError(
            "request component project IDs do not match"
        )
    return next(iter(projects))


@dataclass(frozen=True, init=False)
class DurableDecision:
    """A V2 passport proven current at one durable ledger head."""

    task_project_id: str
    request: ResearchRequest
    passport: AnalysisPassport
    passport_artifact_id: str
    passport_digest: str
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str
    action: PrimaryAction

    def __init__(
        self,
        task_project_id: str,
        request: ResearchRequest,
        passport: AnalysisPassport,
        passport_artifact_id: str,
        passport_digest: str,
        committed_event_id: str,
        committed_sequence: int,
        committed_head_hash: str,
        action: PrimaryAction,
        *,
        _coordinator_seal: object = None,
    ) -> None:
        _require_coordinator_seal(_coordinator_seal)
        for field_name, value in (
            ("task_project_id", task_project_id),
            ("request", request),
            ("passport", passport),
            ("passport_artifact_id", passport_artifact_id),
            ("passport_digest", passport_digest),
            ("committed_event_id", committed_event_id),
            ("committed_sequence", committed_sequence),
            ("committed_head_hash", committed_head_hash),
            ("action", action),
        ):
            object.__setattr__(self, field_name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        project_id = _require_reference(self.task_project_id, "task_project_id")
        if _request_project_id(self.request) != project_id:
            raise LiveResearchFlowIntegrityError(
                "decision request does not belong to the task"
            )
        if (
            not isinstance(self.passport, AnalysisPassport)
            or self.passport.envelope.schema_version != 2
        ):
            raise LiveResearchFlowIntegrityError(
                "durable decision requires a version 2 AnalysisPassport"
            )
        try:
            validate_passport_request_binding(self.passport, self.request)
            artifact = LedgerArtifact.from_value(self.passport)
        except (ResearchServiceError, ValueError, TypeError) as exc:
            raise LiveResearchFlowIntegrityError(
                "decision passport does not bind its request"
            ) from exc
        if self.passport_artifact_id != artifact.artifact_id:
            raise LiveResearchFlowIntegrityError(
                "passport_artifact_id does not identify the passport"
            )
        _require_digest(self.passport_artifact_id, "passport_artifact_id")
        if self.passport_digest != self.passport.digest():
            raise LiveResearchFlowIntegrityError(
                "passport_digest does not match the passport"
            )
        _require_digest(self.passport_digest, "passport_digest")
        if self.committed_event_id != self.passport.envelope.created_event_ref:
            raise LiveResearchFlowIntegrityError(
                "committed_event_id does not seal the passport"
            )
        _require_reference(self.committed_event_id, "committed_event_id")
        _require_sequence(self.committed_sequence, "committed_sequence")
        _require_digest(self.committed_head_hash, "committed_head_hash")
        if not isinstance(self.action, PrimaryAction):
            raise LiveResearchFlowIntegrityError("action must be a PrimaryAction")
        if self.action is not self.passport.action:
            raise LiveResearchFlowIntegrityError(
                "decision action does not match the passport"
            )
        if self.action not in _PUBLISHABLE_ACTIONS:
            raise LiveResearchFlowIntegrityError(
                "route action is unreachable in the P1 live flow"
            )


@dataclass(frozen=True, init=False)
class DurablePendingDecision:
    """A durable request snapshot whose next passport was never committed."""

    task_project_id: str
    request: ResearchRequest
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str
    reason_code: Literal["decision_not_committed"]

    def __init__(
        self,
        task_project_id: str,
        request: ResearchRequest,
        committed_event_id: str,
        committed_sequence: int,
        committed_head_hash: str,
        reason_code: Literal["decision_not_committed"],
        *,
        _coordinator_seal: object = None,
    ) -> None:
        _require_coordinator_seal(_coordinator_seal)
        for field_name, value in (
            ("task_project_id", task_project_id),
            ("request", request),
            ("committed_event_id", committed_event_id),
            ("committed_sequence", committed_sequence),
            ("committed_head_hash", committed_head_hash),
            ("reason_code", reason_code),
        ):
            object.__setattr__(self, field_name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        project_id = _require_reference(self.task_project_id, "task_project_id")
        if _request_project_id(self.request) != project_id:
            raise LiveResearchFlowIntegrityError(
                "pending request does not belong to the task"
            )
        _require_reference(self.committed_event_id, "committed_event_id")
        _require_sequence(self.committed_sequence, "committed_sequence")
        _require_digest(self.committed_head_hash, "committed_head_hash")
        if self.reason_code != "decision_not_committed":
            raise LiveResearchFlowIntegrityError(
                "pending decision has an unknown reason_code"
            )


@dataclass(frozen=True, init=False)
class DurableRetraction:
    """A terminal local view of one passport retraction event."""

    task_project_id: str
    request: ResearchRequest
    retracted_passport_artifact_id: str
    retracted_passport_digest: str
    committed_event_id: str
    committed_sequence: int
    committed_head_hash: str

    def __init__(
        self,
        task_project_id: str,
        request: ResearchRequest,
        retracted_passport_artifact_id: str,
        retracted_passport_digest: str,
        committed_event_id: str,
        committed_sequence: int,
        committed_head_hash: str,
        *,
        _coordinator_seal: object = None,
    ) -> None:
        _require_coordinator_seal(_coordinator_seal)
        for field_name, value in (
            ("task_project_id", task_project_id),
            ("request", request),
            (
                "retracted_passport_artifact_id",
                retracted_passport_artifact_id,
            ),
            ("retracted_passport_digest", retracted_passport_digest),
            ("committed_event_id", committed_event_id),
            ("committed_sequence", committed_sequence),
            ("committed_head_hash", committed_head_hash),
        ):
            object.__setattr__(self, field_name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        project_id = _require_reference(self.task_project_id, "task_project_id")
        if _request_project_id(self.request) != project_id:
            raise LiveResearchFlowIntegrityError(
                "retracted request does not belong to the task"
            )
        _require_digest(
            self.retracted_passport_artifact_id,
            "retracted_passport_artifact_id",
        )
        _require_digest(
            self.retracted_passport_digest,
            "retracted_passport_digest",
        )
        _require_reference(self.committed_event_id, "committed_event_id")
        _require_sequence(self.committed_sequence, "committed_sequence")
        _require_digest(self.committed_head_hash, "committed_head_hash")


DurableFlowRecord: TypeAlias = (
    DurableDecision | DurablePendingDecision | DurableRetraction
)

IdentityFactory = Callable[[], str]
UtcClock = Callable[[], str | None]
PoisonHook = Callable[[str], None]


class LiveResearchFlowCoordinator:
    """Expose only decisions re-read from the authoritative local ledger."""

    P1_CAPABILITY_COUNT = 6
    P1_RULE_COUNT = 67
    P1_ACTIVE_QUESTION_COUNT = 15
    P1_ROUTE_COUNT = 0

    def __init__(
        self,
        *,
        event_id_factory: IdentityFactory,
        passport_object_id_factory: IdentityFactory,
        utc_clock: UtcClock,
        poison_hook: PoisonHook | None = None,
    ) -> None:
        for value, name in (
            (event_id_factory, "event_id_factory"),
            (passport_object_id_factory, "passport_object_id_factory"),
            (utc_clock, "utc_clock"),
        ):
            if not callable(value):
                raise LiveResearchFlowError(f"{name} must be callable")
        if poison_hook is not None and not callable(poison_hook):
            raise LiveResearchFlowError("poison_hook must be callable or null")
        self._event_id_factory = event_id_factory
        self._passport_object_id_factory = passport_object_id_factory
        self._utc_clock = utc_clock
        self._poison_hook = poison_hook
        self._memory = ResearchMemoryCoordinator()
        self._verify_frozen_inventory()

    @classmethod
    def _verify_frozen_inventory(cls) -> None:
        method_space = build_p1_method_space()
        registry = build_p1_clarification_registry()
        observed = (
            len(method_space.capabilities),
            len(method_space.rules),
            len(registry.questions),
            len(method_space.routes),
        )
        expected = (
            cls.P1_CAPABILITY_COUNT,
            cls.P1_RULE_COUNT,
            cls.P1_ACTIVE_QUESTION_COUNT,
            cls.P1_ROUTE_COUNT,
        )
        if observed != expected or any(
            question.lifecycle is not ClarificationLifecycle.ACTIVE
            for question in registry.questions
        ):
            raise LiveResearchFlowIntegrityError(
                "P1 Method Space or clarification inventory drifted"
            )

    def _poison(self, stage: str) -> None:
        if self._poison_hook is not None:
            self._poison_hook(stage)

    def _next_event_id(self) -> str:
        try:
            return _require_reference(self._event_id_factory(), "event_id")
        except LiveResearchFlowError:
            raise
        except Exception as exc:
            raise LiveResearchFlowUnavailableError(
                "event identity factory failed"
            ) from exc

    def _next_passport_id(self) -> str:
        try:
            return _require_reference(
                self._passport_object_id_factory(),
                "passport_object_id",
            )
        except LiveResearchFlowError:
            raise
        except Exception as exc:
            raise LiveResearchFlowUnavailableError(
                "passport identity factory failed"
            ) from exc

    def _now(self) -> str | None:
        try:
            value = self._utc_clock()
        except Exception as exc:
            raise LiveResearchFlowUnavailableError("UTC clock failed") from exc
        if value is not None and not isinstance(value, str):
            raise LiveResearchFlowIntegrityError(
                "UTC clock must return a string or null"
            )
        return value

    @staticmethod
    def _validate_handle(handle: ResearchTaskHandle) -> None:
        if not isinstance(handle, ResearchTaskHandle):
            raise LiveResearchFlowIntegrityError("handle must be a ResearchTaskHandle")
        if handle.record.state is not ResearchTaskState.ACTIVE:
            raise LiveResearchFlowConflictError(
                "task handle does not name an active locator"
            )
        try:
            expected_path = default_ledger_path(handle.record.task_project_id)
        except LedgerPathError as exc:
            raise LiveResearchFlowIntegrityError(
                "task ledger path cannot be securely derived"
            ) from exc
        if handle.ledger_path != expected_path:
            raise LiveResearchFlowIntegrityError(
                "task handle ledger path is not application-owned"
            )

    @contextmanager
    def _active_task_lease(
        self,
        handle: ResearchTaskHandle,
    ) -> Iterator[None]:
        self._validate_handle(handle)
        try:
            with ResearchTaskIndex.open_or_create() as index:
                with index._active_writer_lease(handle.record):
                    yield
        except LiveResearchFlowError:
            raise
        except TaskIndexConflictError as exc:
            raise LiveResearchFlowConflictError(
                "task handle is no longer the exact active locator"
            ) from exc
        except TaskIndexIntegrityError as exc:
            raise LiveResearchFlowIntegrityError(
                "task locator or active writer lease failed integrity checks"
            ) from exc
        except TaskIndexError as exc:
            raise LiveResearchFlowUnavailableError(
                "task active writer lease is unavailable"
            ) from exc

    @classmethod
    def _open_store(cls, handle: ResearchTaskHandle) -> DecisionLedgerStore:
        cls._validate_handle(handle)
        store: DecisionLedgerStore | None = None
        try:
            store = DecisionLedgerStore.open(
                handle.ledger_path,
                handle.record.task_project_id,
            )
            store.verify(full_integrity=True)
            return store
        except LedgerRuntimeError as exc:
            if store is not None:
                store.close()
            raise LiveResearchFlowUnavailableError(
                "secure Decision Ledger runtime is unavailable"
            ) from exc
        except (
            LedgerPathError,
            LedgerIntegrityError,
            LedgerStoreError,
            OSError,
        ) as exc:
            if store is not None:
                store.close()
            raise LiveResearchFlowIntegrityError(
                "task Decision Ledger failed full verification"
            ) from exc

    @staticmethod
    def _validate_request_for_handle(
        handle: ResearchTaskHandle,
        request: ResearchRequest,
    ) -> None:
        if _request_project_id(request) != handle.record.task_project_id:
            raise LiveResearchFlowIntegrityError(
                "request project does not match the task handle"
            )
        if request.current_dataset_fingerprint != handle.record.dataset_fingerprint:
            raise LiveResearchFlowConflictError(
                "request dataset no longer matches the active task"
            )

    @staticmethod
    def _event_by_id(
        events: tuple[LedgerEvent, ...],
        event_id: str,
    ) -> LedgerEvent:
        matches = tuple(event for event in events if event.event_id == event_id)
        if len(matches) != 1:
            raise LiveResearchFlowIntegrityError(
                "durable event identity is missing or ambiguous"
            )
        return matches[0]

    @staticmethod
    def _current_records(
        history: PassportHistory,
        request: ResearchRequest,
    ) -> tuple[CommittedPassportRecord, ...]:
        records: list[CommittedPassportRecord] = []
        for record in history.records:
            if record.passport.envelope.schema_version != 2:
                continue
            try:
                validate_passport_request_binding(record.passport, request)
            except ResearchServiceError:
                continue
            records.append(record)
        return tuple(records)

    @classmethod
    def _recover_from_store(
        cls,
        store: DecisionLedgerStore,
        handle: ResearchTaskHandle,
    ) -> DurableFlowRecord:
        try:
            report = store.verify(full_integrity=True)
            if report.head.sequence == 0:
                raise LiveResearchFlowConflictError(
                    "task has no committed request to recover"
                )
            request = store.load_request()
            events = store.events()
            artifacts = store.artifacts()
            history = PassportHistory.inspect(events, artifacts)
        except LiveResearchFlowError:
            raise
        except (LedgerStoreError, PassportStateError, ValueError, TypeError) as exc:
            raise LiveResearchFlowIntegrityError(
                "durable Research OS history could not be reconstructed"
            ) from exc
        cls._validate_request_for_handle(handle, request)
        head_event = events[-1]
        if (
            head_event.sequence != report.head.sequence
            or head_event.event_hash != report.head.event_hash
        ):
            raise LiveResearchFlowIntegrityError(
                "verified ledger head does not identify its last event"
            )

        current = cls._current_records(history, request)
        if not current:
            if head_event.event_kind not in {
                LedgerEventKind.PROJECT_CREATED,
                LedgerEventKind.CLARIFICATION_ANSWERED,
                LedgerEventKind.REVISION_ACCEPTED,
            }:
                raise LiveResearchFlowIntegrityError(
                    "ledger head has no current passport and is not resumable"
                )
            return DurablePendingDecision(
                task_project_id=handle.record.task_project_id,
                request=request,
                committed_event_id=head_event.event_id,
                committed_sequence=head_event.sequence,
                committed_head_hash=head_event.event_hash,
                reason_code="decision_not_committed",
                _coordinator_seal=_DURABLE_COORDINATOR_SEAL,
            )

        latest = max(current, key=lambda item: item.commit_sequence)
        outstanding = tuple(record for record in current if record.outstanding)
        if len(outstanding) > 1:
            raise LiveResearchFlowIntegrityError(
                "multiple current passports would fork decision authority"
            )
        if latest.retracted_by_event_id is not None:
            if outstanding:
                raise LiveResearchFlowIntegrityError(
                    "retracted decision coexists with current authority"
                )
            event = cls._event_by_id(events, latest.retracted_by_event_id)
            if (
                event.event_kind is not LedgerEventKind.DECISION_RETRACTED
                or event.sequence != report.head.sequence
                or event.event_hash != report.head.event_hash
            ):
                raise LiveResearchFlowIntegrityError(
                    "retraction is not the current durable head"
                )
            return DurableRetraction(
                task_project_id=handle.record.task_project_id,
                request=request,
                retracted_passport_artifact_id=latest.passport_artifact_id,
                retracted_passport_digest=latest.passport.digest(),
                committed_event_id=event.event_id,
                committed_sequence=event.sequence,
                committed_head_hash=event.event_hash,
                _coordinator_seal=_DURABLE_COORDINATOR_SEAL,
            )
        if latest.consumed_by_event_id is not None or outstanding != (latest,):
            raise LiveResearchFlowIntegrityError(
                "current passport history has no publishable authority"
            )
        event = cls._event_by_id(events, latest.commit_event_id)
        if (
            event.event_kind is not LedgerEventKind.PASSPORT_COMMITTED
            or event.sequence != report.head.sequence
            or event.event_hash != report.head.event_hash
            or event.payload["passport_artifact_id"] != latest.passport_artifact_id
        ):
            raise LiveResearchFlowIntegrityError(
                "current passport commit is not the durable ledger head"
            )
        artifact = tuple(
            item
            for item in artifacts
            if item.artifact_id == latest.passport_artifact_id
            and item.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
        )
        if len(artifact) != 1 or artifact[0].decode_value() != latest.passport:
            raise LiveResearchFlowIntegrityError(
                "current passport artifact failed exact readback"
            )
        return DurableDecision(
            task_project_id=handle.record.task_project_id,
            request=request,
            passport=latest.passport,
            passport_artifact_id=latest.passport_artifact_id,
            passport_digest=latest.passport.digest(),
            committed_event_id=event.event_id,
            committed_sequence=event.sequence,
            committed_head_hash=event.event_hash,
            action=latest.passport.action,
            _coordinator_seal=_DURABLE_COORDINATOR_SEAL,
        )

    def recover_current(self, handle: ResearchTaskHandle) -> DurableFlowRecord:
        """Reconstruct the current durable record without planning or writing."""

        recovered = self.recover_current_or_none(handle)
        if recovered is None:
            raise LiveResearchFlowConflictError(
                "task has no committed request to recover"
            )
        return recovered

    def recover_current_or_none(
        self,
        handle: ResearchTaskHandle,
    ) -> DurableFlowRecord | None:
        """Return null only for a fully verified, authority-free empty task."""

        self._verify_frozen_inventory()
        with self._active_task_lease(handle):
            store = self._open_store(handle)
            try:
                if store.verify(full_integrity=True).head.sequence == 0:
                    return None
                return self._recover_from_store(store, handle)
            finally:
                store.close()

    def _recover_current_leased(
        self,
        handle: ResearchTaskHandle,
    ) -> DurableFlowRecord:
        store = self._open_store(handle)
        try:
            return self._recover_from_store(store, handle)
        finally:
            store.close()

    def _commit_passport(
        self,
        store: DecisionLedgerStore,
        handle: ResearchTaskHandle,
        request: ResearchRequest,
    ) -> DurableDecision:
        self._poison("before_passport_commit")
        event_id = self._next_event_id()
        passport_object_id = self._next_passport_id()
        try:
            receipt = self._memory.commit_current_passport(
                store,
                request,
                event_id=event_id,
                passport_object_id=passport_object_id,
                recorded_at_utc=self._now(),
            )
        except PromotionError as exc:
            raise LiveResearchFlowConflictError(
                "passport commit failed or conflicted"
            ) from exc
        self._poison("after_passport_append")
        self._poison("before_publication_readback")
        recovered = self._recover_from_store(store, handle)
        if (
            not isinstance(recovered, DurableDecision)
            or recovered.request != request
            or recovered.passport != receipt.passport
            or recovered.committed_event_id != receipt.passport_event_id
        ):
            raise LiveResearchFlowIntegrityError(
                "passport receipt disagrees with durable readback"
            )
        self._poison("after_publication_readback")
        return recovered

    def commit_initial(
        self,
        handle: ResearchTaskHandle,
        request: ResearchRequest,
    ) -> DurableDecision:
        """Commit an initial request and its first passport before publication."""

        with self._active_task_lease(handle):
            return self._commit_initial_leased(handle, request)

    def _commit_initial_leased(
        self,
        handle: ResearchTaskHandle,
        request: ResearchRequest,
    ) -> DurableDecision:
        self._validate_handle(handle)
        self._validate_request_for_handle(handle, request)
        created_refs = {
            request.question.envelope.created_event_ref,
            request.estimand.envelope.created_event_ref,
            request.study.envelope.created_event_ref,
        }
        if len(created_refs) != 1:
            raise LiveResearchFlowIntegrityError(
                "initial request components do not share one event identity"
            )
        store = self._open_store(handle)
        try:
            if store.head.sequence != 0:
                current = self._recover_from_store(store, handle)
                if isinstance(current, DurableDecision) and current.request == request:
                    return current
                if (
                    isinstance(current, DurablePendingDecision)
                    and current.request == request
                ):
                    raise LiveResearchFlowConflictError(
                        "initial request is pending; call resume_pending explicitly"
                    )
                raise LiveResearchFlowConflictError(
                    "task already contains a different or retracted decision"
                )
            self._poison("before_request_initialize")
            try:
                self._memory.initialize(
                    store,
                    request,
                    event_id=next(iter(created_refs)),
                    recorded_at_utc=self._now(),
                )
            except PromotionError as exc:
                raise LiveResearchFlowConflictError(
                    "initial request commit failed or conflicted"
                ) from exc
            self._poison("after_request_initialize")
            return self._commit_passport(store, handle, request)
        finally:
            store.close()

    def resume_pending(
        self,
        handle: ResearchTaskHandle,
        pending: DurablePendingDecision,
    ) -> DurableDecision:
        """Explicitly append the one missing passport for an exact pending head."""

        with self._active_task_lease(handle):
            return self._resume_pending_leased(handle, pending)

    def _resume_pending_leased(
        self,
        handle: ResearchTaskHandle,
        pending: DurablePendingDecision,
    ) -> DurableDecision:
        if not isinstance(pending, DurablePendingDecision):
            raise LiveResearchFlowConflictError(
                "resume_pending requires a DurablePendingDecision"
            )
        store = self._open_store(handle)
        try:
            current = self._recover_from_store(store, handle)
            if current != pending:
                raise LiveResearchFlowConflictError(
                    "pending receipt is stale or no longer current"
                )
            return self._commit_passport(store, handle, pending.request)
        finally:
            store.close()

    def commit_answer(
        self,
        handle: ResearchTaskHandle,
        answer: ClarificationAnswerEvent,
    ) -> DurableDecision:
        """Consume one current clarify passport, then commit and read back its successor."""

        with self._active_task_lease(handle):
            return self._commit_answer_leased(handle, answer)

    def _commit_answer_leased(
        self,
        handle: ResearchTaskHandle,
        answer: ClarificationAnswerEvent,
    ) -> DurableDecision:
        if not isinstance(answer, ClarificationAnswerEvent):
            raise LiveResearchFlowIntegrityError(
                "answer must be a ClarificationAnswerEvent"
            )
        store = self._open_store(handle)
        try:
            current = self._recover_from_store(store, handle)
            if not isinstance(current, DurableDecision) or (
                current.action is not PrimaryAction.CLARIFY
            ):
                raise LiveResearchFlowConflictError(
                    "only a current clarify decision can accept an answer"
                )
            self._poison("before_answer_append")
            try:
                receipt = self._memory.commit_ready_answer(
                    store,
                    current.request,
                    current.passport,
                    answer,
                    recorded_at_utc=self._now(),
                )
            except PromotionError as exc:
                raise LiveResearchFlowConflictError(
                    "answer is stale, invalid, consumed, or conflicted"
                ) from exc
            self._poison("after_answer_append")
            return self._commit_passport(store, handle, receipt.request)
        finally:
            store.close()

    def retract_current(self, handle: ResearchTaskHandle) -> DurableRetraction:
        """Append a terminal retraction for the exact current passport."""

        with self._active_task_lease(handle):
            return self._retract_current_leased(handle)

    def _retract_current_leased(
        self,
        handle: ResearchTaskHandle,
    ) -> DurableRetraction:
        store = self._open_store(handle)
        try:
            current = self._recover_from_store(store, handle)
            if not isinstance(current, DurableDecision):
                raise LiveResearchFlowConflictError(
                    "only a current durable decision can be retracted"
                )
            self._poison("before_retraction_append")
            try:
                receipt = self._memory.retract_current_passport(
                    store,
                    current.request,
                    current.passport,
                    event_id=self._next_event_id(),
                    recorded_at_utc=self._now(),
                )
            except PromotionError as exc:
                raise LiveResearchFlowConflictError(
                    "current passport could not be retracted"
                ) from exc
            self._poison("after_retraction_append")
            recovered = self._recover_from_store(store, handle)
            if (
                not isinstance(recovered, DurableRetraction)
                or recovered.committed_event_id
                not in receipt.ledger_receipt.committed_event_ids
                or recovered.retracted_passport_artifact_id
                != current.passport_artifact_id
            ):
                raise LiveResearchFlowIntegrityError(
                    "retraction receipt disagrees with durable readback"
                )
            return recovered
        finally:
            store.close()
