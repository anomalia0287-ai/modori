"""Atomic coordination between pure Research OS transitions and durable memory."""

from __future__ import annotations

from dataclasses import dataclass

from modori.research_memory.canonical import canonical_digest
from modori.research_memory.ledger_contracts import (
    ImportedAssertion,
    ImportSourceRecord,
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerCommit,
    LedgerContractError,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
    LedgerReceipt,
    ResearchRequestSnapshot,
)
from modori.research_memory.ledger_store import (
    DecisionLedgerStore,
    LedgerConflictError,
    LedgerStoreError,
)
from modori.research_memory.passport_state import (
    CommittedPassportRecord,
    PassportHistory,
    PassportStateError,
)
from modori.research_memory.quarantine import (
    QuarantineResult,
    QuarantineStage,
)
from modori.research_os import (
    AnalysisPassport,
    ClarificationAnswerEvent,
    ClarificationTransitionService,
    ClarifyPayloadV2,
    ResearchOsService,
    ResearchRequest,
    ResearchServiceError,
    RevisionAcceptanceCertificate,
    SchemaEnvelope,
    TransitionError,
    validate_passport_request_binding,
)


class PromotionError(RuntimeError):
    """Raised before any unsafe or incomplete memory promotion can commit."""


@dataclass(frozen=True)
class PromotionReceipt:
    request: ResearchRequest
    ledger_receipt: LedgerReceipt
    imported_assertions: tuple[ImportedAssertion, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, ResearchRequest):
            raise PromotionError("promotion receipt requires a ResearchRequest")
        if not isinstance(self.ledger_receipt, LedgerReceipt):
            raise PromotionError("promotion receipt requires a durable ledger receipt")
        if not isinstance(self.imported_assertions, tuple):
            raise PromotionError("imported_assertions must be a tuple")


@dataclass(frozen=True)
class PassportCommitReceipt:
    request: ResearchRequest
    passport: AnalysisPassport
    head: LedgerHead
    passport_event_id: str
    appended: bool

    def __post_init__(self) -> None:
        if not isinstance(self.request, ResearchRequest):
            raise PromotionError("passport receipt requires a ResearchRequest")
        if not isinstance(self.passport, AnalysisPassport):
            raise PromotionError("passport receipt requires an AnalysisPassport")
        if self.passport.envelope.schema_version != 2:
            raise PromotionError("passport receipt requires schema version 2")
        if not isinstance(self.head, LedgerHead) or self.head.sequence < 1:
            raise PromotionError("passport receipt requires a durable ledger head")
        if (
            not isinstance(self.passport_event_id, str)
            or not self.passport_event_id
        ):
            raise PromotionError("passport_event_id must be a non-empty string")
        if self.passport.envelope.created_event_ref != self.passport_event_id:
            raise PromotionError("passport receipt event identity mismatch")
        if type(self.appended) is not bool:
            raise PromotionError("appended must be a boolean")


def _request_project_id(request: ResearchRequest) -> str:
    if not isinstance(request, ResearchRequest):
        raise PromotionError("request must be a ResearchRequest")
    project_ids = {
        request.question.envelope.project_id,
        request.estimand.envelope.project_id,
        request.study.envelope.project_id,
    }
    if len(project_ids) != 1:
        raise PromotionError("request component project IDs must match")
    return next(iter(project_ids))


def _snapshot_artifact(
    artifacts: tuple[LedgerArtifact, ...],
) -> LedgerArtifact:
    snapshots = tuple(
        artifact
        for artifact in artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    if len(snapshots) != 1:
        raise PromotionError("snapshot capture must produce exactly one snapshot")
    return snapshots[0]


def _merge_artifacts(
    *groups: tuple[LedgerArtifact, ...],
) -> tuple[LedgerArtifact, ...]:
    merged: dict[str, LedgerArtifact] = {}
    for artifact in (item for group in groups for item in group):
        prior = merged.get(artifact.artifact_id)
        if prior is not None and prior != artifact:
            raise PromotionError("artifact ID collision during coordination")
        merged[artifact.artifact_id] = artifact
    return tuple(merged[key] for key in sorted(merged))


def _subjects(*groups: tuple[LedgerArtifact, ...]) -> tuple[str, ...]:
    return tuple(
        sorted({artifact.artifact_id for group in groups for artifact in group})
    )


def _artifact_for_value(value: object) -> LedgerArtifact:
    try:
        return LedgerArtifact.from_value(value)
    except (LedgerContractError, ValueError, TypeError) as exc:
        raise PromotionError("transition produced a non-durable artifact") from exc


class ResearchMemoryCoordinator:
    """Commit validated local transitions without acquiring execution authority."""

    def __init__(
        self,
        transition_service: ClarificationTransitionService | None = None,
        research_service: ResearchOsService | None = None,
    ) -> None:
        self._transition = transition_service or ClarificationTransitionService()
        self._research_service = research_service or ResearchOsService()
        if not isinstance(self._transition, ClarificationTransitionService):
            raise PromotionError(
                "transition_service must be a ClarificationTransitionService"
            )
        if not isinstance(self._research_service, ResearchOsService):
            raise PromotionError("research_service must be a ResearchOsService")
        if (
            self._transition.clarification_registry_digest
            != self._research_service.clarification_registry_digest
        ):
            raise PromotionError(
                "planning and transition clarification registries must match"
            )

    @staticmethod
    def _history(store: DecisionLedgerStore) -> PassportHistory:
        try:
            return PassportHistory.inspect(store.events(), store.artifacts())
        except PassportStateError as exc:
            raise PromotionError("durable passport history is invalid") from exc

    def _current_outstanding(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
    ) -> tuple[CommittedPassportRecord, ...]:
        return self._history(store).outstanding_for(
            project_id=_request_project_id(request),
            request_binding_digest=request.request_binding_digest(),
            clarification_registry_digest=(
                self._research_service.clarification_registry_digest
            ),
        )

    def _require_active_committed_passport(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        passport: AnalysisPassport,
    ) -> CommittedPassportRecord:
        if (
            not isinstance(passport, AnalysisPassport)
            or passport.envelope.schema_version != 2
            or not isinstance(passport.clarify, ClarifyPayloadV2)
        ):
            raise PromotionError(
                "clarification passport is not an active committed version 2 passport"
            )
        records = self._current_outstanding(store, request)
        if len(records) != 1:
            raise PromotionError("clarification passport is not active")
        record = records[0]
        passport_artifact = _artifact_for_value(passport)
        if (
            record.passport_artifact_id != passport_artifact.artifact_id
            or record.passport != passport
            or passport.clarification_registry_digest
            != self._research_service.clarification_registry_digest
        ):
            raise PromotionError("clarification passport is not active")
        return record

    @staticmethod
    def _ensure_store_binding(
        store: DecisionLedgerStore,
        request: ResearchRequest,
        *,
        require_empty: bool,
    ) -> tuple[str, LedgerHead]:
        if not isinstance(store, DecisionLedgerStore):
            raise PromotionError("store must be a DecisionLedgerStore")
        project_id = _request_project_id(request)
        if store.project_id != project_id:
            raise PromotionError("store project does not match request")
        head = store.head
        if require_empty:
            if head != LedgerHead.genesis() or store.events() or store.artifacts():
                raise PromotionError("operation requires a fresh empty local ledger")
        else:
            if head.sequence < 1:
                raise PromotionError("transition requires an initialized ledger")
            try:
                durable_request = store.load_request()
            except LedgerStoreError as exc:
                raise PromotionError("ledger has no valid current request") from exc
            if durable_request != request:
                raise PromotionError("request no longer matches durable ledger state")
        return project_id, head

    @staticmethod
    def _append(
        store: DecisionLedgerStore,
        commit: LedgerCommit,
        request: ResearchRequest,
        imported_assertions: tuple[ImportedAssertion, ...] = (),
    ) -> PromotionReceipt:
        try:
            ledger_receipt = store.append(commit)
        except (LedgerStoreError, LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError("durable transition commit failed") from exc
        return PromotionReceipt(
            request=request,
            ledger_receipt=ledger_receipt,
            imported_assertions=imported_assertions,
        )

    def initialize(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        *,
        event_id: str,
        recorded_at_utc: str | None,
    ) -> PromotionReceipt:
        project_id, head = self._ensure_store_binding(
            store,
            request,
            require_empty=True,
        )
        try:
            _snapshot, artifacts = ResearchRequestSnapshot.capture(request)
            snapshot_artifact = _snapshot_artifact(artifacts)
            event = LedgerEvent.create(
                project_id=project_id,
                event_id=event_id,
                sequence=1,
                event_kind=LedgerEventKind.PROJECT_CREATED,
                subject_artifact_ids=_subjects(artifacts),
                payload={
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(event,),
                artifacts=artifacts,
                resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
            )
        except (LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError("initial request cannot enter durable memory") from exc
        return self._append(store, commit, request)

    def commit_current_passport(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        *,
        event_id: str,
        passport_object_id: str,
        recorded_at_utc: str | None,
    ) -> PassportCommitReceipt:
        project_id, head = self._ensure_store_binding(
            store,
            request,
            require_empty=False,
        )
        existing = self._current_outstanding(store, request)
        if len(existing) == 1:
            record = existing[0]
            return PassportCommitReceipt(
                request=request,
                passport=record.passport,
                head=store.head,
                passport_event_id=record.commit_event_id,
                appended=False,
            )
        if len(existing) > 1:
            raise PromotionError("multiple active clarification passports exist")

        artifacts_before = store.artifacts()
        if any(
            artifact.artifact_kind is LedgerArtifactKind.ANALYSIS_PASSPORT
            and artifact.object_id == passport_object_id
            for artifact in artifacts_before
        ):
            raise PromotionError("passport object identity has already been used")
        if any(event.event_id == event_id for event in store.events()):
            raise PromotionError("passport event identity has already been used")

        try:
            envelope = SchemaEnvelope(
                schema_id="modori.analysis_passport",
                schema_version=2,
                project_id=project_id,
                object_id=passport_object_id,
                revision=1,
                supersedes_revision=None,
                created_event_ref=event_id,
            )
            resolved = self._research_service.resolve_and_plan(request, envelope)
            passport = resolved.passport
            _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(request)
            snapshot_artifact = _snapshot_artifact(snapshot_artifacts)
            passport_artifact = _artifact_for_value(passport)
            artifacts = _merge_artifacts(
                snapshot_artifacts,
                (passport_artifact,),
            )
            event = LedgerEvent.create(
                project_id=project_id,
                event_id=event_id,
                sequence=head.sequence + 1,
                event_kind=LedgerEventKind.PASSPORT_COMMITTED,
                subject_artifact_ids=_subjects(
                    snapshot_artifacts,
                    (passport_artifact,),
                ),
                payload={
                    "passport_artifact_id": passport_artifact.artifact_id,
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(event,),
                artifacts=artifacts,
                resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
            )
        except (
            ResearchServiceError,
            LedgerContractError,
            ValueError,
            TypeError,
        ) as exc:
            raise PromotionError("current passport could not be constructed") from exc

        try:
            receipt = store.append(commit)
        except LedgerConflictError:
            try:
                store.verify()
                if store.load_request() != request:
                    raise PromotionError(
                        "ledger changed to a different request during passport commit"
                    )
                winner = self._current_outstanding(store, request)
            except LedgerStoreError as exc:
                raise PromotionError(
                    "ledger conflict could not be safely reverified"
                ) from exc
            if len(winner) != 1:
                raise PromotionError(
                    "ledger changed without an equivalent active passport"
                )
            record = winner[0]
            return PassportCommitReceipt(
                request=request,
                passport=record.passport,
                head=store.head,
                passport_event_id=record.commit_event_id,
                appended=False,
            )
        except (LedgerStoreError, LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError("durable passport commit failed") from exc

        return PassportCommitReceipt(
            request=request,
            passport=passport,
            head=receipt.head,
            passport_event_id=event.event_id,
            appended=True,
        )

    def retract_current_passport(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        passport: AnalysisPassport,
        *,
        event_id: str,
        recorded_at_utc: str | None = None,
    ) -> PromotionReceipt:
        """Close the latest durable passport without deleting its history."""

        project_id, head = self._ensure_store_binding(
            store,
            request,
            require_empty=False,
        )
        if (
            not isinstance(passport, AnalysisPassport)
            or passport.envelope.schema_version != 2
        ):
            raise PromotionError(
                "only a current durable version 2 passport can be retracted"
            )
        try:
            validate_passport_request_binding(passport, request)
            passport_artifact = _artifact_for_value(passport)
        except (ResearchServiceError, LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError(
                "passport is not current for the durable request"
            ) from exc

        history = self._history(store)
        exact_matches = tuple(
            record
            for record in history.records
            if record.passport_artifact_id == passport_artifact.artifact_id
            and record.passport == passport
        )
        if len(exact_matches) != 1:
            raise PromotionError("passport is not a durable committed decision")
        target = exact_matches[0]
        if not target.outstanding:
            raise PromotionError("passport is no longer active and cannot be retracted")

        current_records: list[CommittedPassportRecord] = []
        for record in history.records:
            candidate = record.passport
            if (
                candidate.envelope.schema_version != 2
                or candidate.envelope.project_id != project_id
            ):
                continue
            try:
                validate_passport_request_binding(candidate, request)
            except ResearchServiceError:
                continue
            current_records.append(record)
        if not current_records or target != max(
            current_records,
            key=lambda record: record.commit_sequence,
        ):
            raise PromotionError("passport is not the current durable decision")

        if any(event.event_id == event_id for event in store.events()):
            raise PromotionError("retraction event identity has already been used")

        try:
            _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(request)
            snapshot_artifact = _snapshot_artifact(snapshot_artifacts)
            event = LedgerEvent.create(
                project_id=project_id,
                event_id=event_id,
                sequence=head.sequence + 1,
                event_kind=LedgerEventKind.DECISION_RETRACTED,
                subject_artifact_ids=_subjects(snapshot_artifacts),
                payload={
                    "retracted_event_id": target.commit_event_id,
                    "reason_code": "user_retracted",
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(event,),
                artifacts=snapshot_artifacts,
                resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
            )
        except (LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError("passport retraction could not be constructed") from exc

        receipt = self._append(store, commit, request)
        refreshed = self._history(store)
        closed = tuple(
            record
            for record in refreshed.records
            if record.passport_artifact_id == target.passport_artifact_id
            and record.passport == target.passport
        )
        if (
            len(closed) != 1
            or closed[0].retracted_by_event_id != event.event_id
            or closed[0].outstanding
        ):
            raise PromotionError("durable passport retraction did not verify")
        return receipt

    def commit_ready_answer(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        passport: AnalysisPassport,
        answer: ClarificationAnswerEvent,
        *,
        recorded_at_utc: str | None = None,
    ) -> PromotionReceipt:
        project_id, head = self._ensure_store_binding(
            store,
            request,
            require_empty=False,
        )
        if not isinstance(answer, ClarificationAnswerEvent):
            raise PromotionError("answer must be a ClarificationAnswerEvent")
        if answer.event_sequence != head.sequence + 1:
            raise PromotionError("answer sequence must immediately extend ledger head")
        self._require_active_committed_passport(store, request, passport)
        try:
            candidate = self._transition.propose(request, passport, answer)
            committed_request = self._transition.commit_ready(request, candidate)
            _snapshot, snapshot_artifacts = ResearchRequestSnapshot.capture(
                committed_request
            )
            snapshot_artifact = _snapshot_artifact(snapshot_artifacts)
            passport_artifact = _artifact_for_value(passport)
            answer_artifact = _artifact_for_value(answer)
            evidence_artifact = _artifact_for_value(
                committed_request.decision_evidence_refs[-1]
            )
            supporting = (passport_artifact, answer_artifact, evidence_artifact)
            artifacts = _merge_artifacts(snapshot_artifacts, supporting)
            event = LedgerEvent.create(
                project_id=project_id,
                event_id=answer.event_id,
                sequence=answer.event_sequence,
                event_kind=LedgerEventKind.CLARIFICATION_ANSWERED,
                subject_artifact_ids=_subjects(snapshot_artifacts, supporting),
                payload={
                    "answer_artifact_id": answer_artifact.artifact_id,
                    "evidence_ref_artifact_id": evidence_artifact.artifact_id,
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(event,),
                artifacts=artifacts,
                resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
            )
        except (TransitionError, LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError("ready clarification transition was rejected") from exc
        return self._append(store, commit, committed_request)

    def commit_accepted_answer(
        self,
        store: DecisionLedgerStore,
        request: ResearchRequest,
        passport: AnalysisPassport,
        answer: ClarificationAnswerEvent,
        certificate: RevisionAcceptanceCertificate | None,
        *,
        recorded_at_utc: str | None = None,
    ) -> PromotionReceipt:
        project_id, head = self._ensure_store_binding(
            store,
            request,
            require_empty=False,
        )
        if not isinstance(answer, ClarificationAnswerEvent):
            raise PromotionError("answer must be a ClarificationAnswerEvent")
        if not isinstance(certificate, RevisionAcceptanceCertificate):
            raise PromotionError("accepted transition requires a certificate")
        if answer.event_sequence != head.sequence + 1:
            raise PromotionError("answer sequence must immediately extend ledger head")
        if certificate.event_sequence != head.sequence + 2:
            raise PromotionError("acceptance sequence must immediately follow answer")
        self._require_active_committed_passport(store, request, passport)
        try:
            candidate = self._transition.propose(
                request,
                passport,
                answer,
                acceptance_certificate_id=certificate.certificate_id,
            )
            committed_request = self._transition.commit_accepted(
                request,
                candidate,
                certificate,
            )
            _old_snapshot, old_snapshot_artifacts = ResearchRequestSnapshot.capture(
                request
            )
            old_snapshot_artifact = _snapshot_artifact(old_snapshot_artifacts)
            _new_snapshot, new_snapshot_artifacts = ResearchRequestSnapshot.capture(
                committed_request
            )
            new_snapshot_artifact = _snapshot_artifact(new_snapshot_artifacts)
            passport_artifact = _artifact_for_value(passport)
            answer_artifact = _artifact_for_value(answer)
            certificate_artifact = _artifact_for_value(certificate)
            answer_evidence = _artifact_for_value(
                committed_request.decision_evidence_refs[-2]
            )
            acceptance_evidence = _artifact_for_value(
                committed_request.decision_evidence_refs[-1]
            )
            answer_support = (
                passport_artifact,
                answer_artifact,
                answer_evidence,
            )
            acceptance_support = (
                certificate_artifact,
                acceptance_evidence,
            )
            answer_event = LedgerEvent.create(
                project_id=project_id,
                event_id=answer.event_id,
                sequence=answer.event_sequence,
                event_kind=LedgerEventKind.CLARIFICATION_ANSWERED,
                subject_artifact_ids=_subjects(
                    old_snapshot_artifacts,
                    answer_support,
                ),
                payload={
                    "answer_artifact_id": answer_artifact.artifact_id,
                    "evidence_ref_artifact_id": answer_evidence.artifact_id,
                    "resulting_snapshot_artifact_id": (
                        old_snapshot_artifact.artifact_id
                    ),
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            acceptance_event = LedgerEvent.create(
                project_id=project_id,
                event_id=certificate.certificate_id,
                sequence=certificate.event_sequence,
                event_kind=LedgerEventKind.REVISION_ACCEPTED,
                subject_artifact_ids=_subjects(
                    new_snapshot_artifacts,
                    acceptance_support,
                ),
                payload={
                    "acceptance_artifact_id": certificate_artifact.artifact_id,
                    "evidence_ref_artifact_id": acceptance_evidence.artifact_id,
                    "resulting_snapshot_artifact_id": (
                        new_snapshot_artifact.artifact_id
                    ),
                },
                previous_event_hash=answer_event.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            artifacts = _merge_artifacts(
                old_snapshot_artifacts,
                new_snapshot_artifacts,
                answer_support,
                acceptance_support,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(answer_event, acceptance_event),
                artifacts=artifacts,
                resulting_snapshot_artifact_id=new_snapshot_artifact.artifact_id,
            )
        except (TransitionError, LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError(
                "accepted clarification transition was rejected"
            ) from exc
        return self._append(store, commit, committed_request)

    def promote_imported_assertions(
        self,
        store: DecisionLedgerStore,
        local_request: ResearchRequest,
        result: QuarantineResult,
        *,
        project_event_id: str,
        import_event_id: str,
        recorded_at_utc: str | None = None,
    ) -> PromotionReceipt:
        local_project_id, head = self._ensure_store_binding(
            store,
            local_request,
            require_empty=True,
        )
        if not isinstance(result, QuarantineResult):
            raise PromotionError("result must be a QuarantineResult")
        if result.stage is not QuarantineStage.ASSERTION_READY:
            raise PromotionError(
                "only assertion-ready quarantine results can be promoted"
            )
        if (
            result.source_project_id is None
            or result.source_project_id == local_project_id
        ):
            raise PromotionError("import requires a fresh local project identity")
        if result.source_head is None:
            raise PromotionError("import requires a verified foreign source head")
        if (
            result.source_dataset_fingerprint
            != local_request.current_dataset_fingerprint
        ):
            raise PromotionError("import dataset fingerprint no longer matches locally")
        if not result.imported_assertions:
            raise PromotionError("import has no authority-free assertions")
        try:
            _snapshot, local_artifacts = ResearchRequestSnapshot.capture(local_request)
            snapshot_artifact = _snapshot_artifact(local_artifacts)
            local_assertions: list[ImportedAssertion] = []
            for source in result.imported_assertions:
                identity = canonical_digest(
                    {
                        "local_project_id": local_project_id,
                        "source_bundle_digest": result.source_bundle_digest,
                        "source_assertion_id": source.assertion_id,
                    }
                )
                source_mapping = source.to_mapping()
                local_assertions.append(
                    ImportedAssertion(
                        assertion_id=f"imported:{identity}",
                        project_id=local_project_id,
                        source_project_id=source.source_project_id,
                        source_bundle_digest=source.source_bundle_digest,
                        source_artifact_id=source.source_artifact_id,
                        fact_address=source.fact_address,
                        foreign_fact_state=source.foreign_fact_state,
                        value=source_mapping["value"],
                        provenance_refs=source.provenance_refs,
                    )
                )
            local_assertions.sort(key=lambda item: item.fact_address)
            assertion_artifacts = tuple(
                _artifact_for_value(assertion) for assertion in local_assertions
            )
            genesis = LedgerEvent.create(
                project_id=local_project_id,
                event_id=project_event_id,
                sequence=1,
                event_kind=LedgerEventKind.PROJECT_CREATED,
                subject_artifact_ids=_subjects(local_artifacts),
                payload={
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=head.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            assertion_artifact_ids = tuple(
                sorted(artifact.artifact_id for artifact in assertion_artifacts)
            )
            imported = LedgerEvent.create(
                project_id=local_project_id,
                event_id=import_event_id,
                sequence=2,
                event_kind=LedgerEventKind.IMPORT_ACCEPTED_AS_ASSERTIONS,
                subject_artifact_ids=tuple(
                    sorted(
                        {
                            snapshot_artifact.artifact_id,
                            *assertion_artifact_ids,
                        }
                    )
                ),
                payload={
                    "source_bundle_digest": result.source_bundle_digest,
                    "source_head_hash": result.source_head.event_hash,
                    "source_project_id": result.source_project_id,
                    "assertion_artifact_ids": list(assertion_artifact_ids),
                    "resulting_snapshot_artifact_id": snapshot_artifact.artifact_id,
                },
                previous_event_hash=genesis.event_hash,
                recorded_at_utc=recorded_at_utc,
            )
            all_artifacts = _merge_artifacts(local_artifacts, assertion_artifacts)
            import_source = ImportSourceRecord(
                project_id=local_project_id,
                source_project_id=result.source_project_id,
                source_bundle_digest=result.source_bundle_digest,
                source_head_hash=result.source_head.event_hash,
                assertion_artifact_ids=assertion_artifact_ids,
                imported_at_utc=recorded_at_utc,
            )
            commit = LedgerCommit(
                expected_head=head,
                events=(genesis, imported),
                artifacts=all_artifacts,
                resulting_snapshot_artifact_id=snapshot_artifact.artifact_id,
                import_source=import_source,
            )
        except (LedgerContractError, ValueError, TypeError) as exc:
            raise PromotionError(
                "authority-free assertion promotion was rejected"
            ) from exc
        return self._append(
            store,
            commit,
            local_request,
            tuple(local_assertions),
        )
