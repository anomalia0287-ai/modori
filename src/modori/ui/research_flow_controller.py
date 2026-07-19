"""Asynchronous, authority-preserving controller for the live Research OS flow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event
from threading import Lock
from time import monotonic_ns
from types import MappingProxyType
from typing import Protocol
import unicodedata
from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from modori.core import Dataset
from modori.research_flow import (
    FINGERPRINT_CONTRACT_ID,
    FINGERPRINT_WORKER_DEADLINE_SECONDS,
    DatasetIdentity,
    DurableDecision,
    DurableFlowRecord,
    DurablePendingDecision,
    FingerprintCancelled,
    FingerprintContractError,
    FingerprintDeadlineExceeded,
    LiveResearchFlowCoordinator,
    LiveResearchFlowConflictError,
    LiveResearchFlowIntegrityError,
    LiveResearchFlowUnavailableError,
    PassportBoundPreparation,
    PreflightDisposition,
    ResearchFlowState,
    ResearchTaskSessionStore,
    SourceSchemaDescriptor,
    StaticBoundary,
    TaskSessionConflictError,
    TaskSessionIntegrityError,
    TaskSessionUnavailableError,
    VariableMeaningReview,
    build_variable_meaning_review,
    fingerprint_dataset,
    map_passport_to_step,
    preflight_mapped_step,
)
from modori.research_os import (
    AnswerKind,
    AnswerValue,
    AnswerValueKind,
    ClarificationAnswerEvent,
    Language,
    P1IntakeDraft,
    P1RoleBindings,
    P1TaskProfile,
    PrimaryAction,
    build_causal_abstention_request,
    build_p1_clarification_registry,
    build_p1_request,
)
from modori.table_io import import_selection_from_params
from modori.ui.contracts import ControllerMode
from modori.ui.research_flow_presenter import (
    ResearchFlowView,
    present_durable_record,
    present_static_boundary,
    present_transient_state,
)
from modori.ui.research_preparation_editor import (
    PreparationReview,
    ResearchPreparationEditor,
)
from modori.ui.worker import EngineJobResult


class ResearchFlowControllerError(ValueError):
    """Raised when two views do not describe the same safe authority."""


class ResearchFlowPipelineError(ValueError):
    """Raised when current pipeline state has no closed source identity."""


class ResearchFlowStaleError(RuntimeError):
    """Raised when a command no longer binds the current pipeline identity."""


class _ResearchFlowRuntime(Protocol):
    def adopt_language(self, language: Language) -> None: ...

    def present_current(
        self,
        *,
        language: Language,
        pipeline_version: int,
    ) -> "ResearchFlowViews | None": ...

    def note_pipeline_version(self, pipeline_version: int) -> None: ...

    def current_dataset_fingerprint(self) -> str | None: ...

    def start(self, **kwargs: object) -> "ResearchFlowViews": ...

    def commit_initial(self, **kwargs: object) -> "ResearchFlowViews": ...

    def review_variable_meanings(self, **kwargs: object) -> "ResearchFlowViews": ...

    def commit_causal_boundary(self, **kwargs: object) -> "ResearchFlowViews": ...

    def answer(self, **kwargs: object) -> "ResearchFlowViews": ...

    def resume(self, **kwargs: object) -> "ResearchFlowViews": ...

    def retract(self, **kwargs: object) -> "ResearchFlowViews": ...

    def replan(self, **kwargs: object) -> "ResearchFlowViews": ...

    def prepare(self, **kwargs: object) -> "ResearchFlowViews": ...


class _ResearchFlowWorker(Protocol):
    def submit(
        self,
        *,
        run_id: int,
        pipeline_version: int,
        job: Callable[[], "ResearchFlowViews"],
    ) -> object: ...


@dataclass(frozen=True)
class ResearchFlowPipelineSnapshot:
    """One worker-local pipeline snapshot with no source path."""

    dataset: Dataset
    source_schema: SourceSchemaDescriptor
    variable_labels: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, Dataset):
            raise ResearchFlowPipelineError("current dataset is unavailable")
        if not isinstance(self.source_schema, SourceSchemaDescriptor):
            raise ResearchFlowPipelineError("source schema is unavailable")
        if not isinstance(self.variable_labels, Mapping):
            raise ResearchFlowPipelineError("variable labels must be a mapping")
        labels = dict(self.variable_labels)
        if any(
            not isinstance(variable_id, str) or not isinstance(label, str)
            for variable_id, label in labels.items()
        ):
            raise ResearchFlowPipelineError(
                "variable labels must contain string keys and values"
            )
        object.__setattr__(self, "variable_labels", MappingProxyType(labels))


def _step_value(step: object, name: str) -> object:
    if isinstance(step, Mapping):
        return step.get(name)
    return getattr(step, name, None)


def _layout_value(layout: object, name: str) -> object:
    if layout is None:
        return None
    if isinstance(layout, Mapping):
        return layout.get(name)
    return getattr(layout, name, None)


class ResearchFlowPipelineAccess:
    """Capture only the data and path-free schema needed by Research OS."""

    def __init__(self, pipeline_ops_provider: Callable[[], object]) -> None:
        if not callable(pipeline_ops_provider):
            raise ResearchFlowPipelineError("pipeline_ops_provider must be callable")
        self._pipeline_ops_provider = pipeline_ops_provider

    def capture(self) -> ResearchFlowPipelineSnapshot:
        ops = self._pipeline_ops_provider()
        dataset = ops.current_dataset()
        if not isinstance(dataset, Dataset):
            raise ResearchFlowPipelineError(
                "Research OS requires one current typed dataset"
            )
        import_steps = tuple(
            step
            for step in ops.steps()
            if _step_value(step, "step_type") == "import.table"
            or (isinstance(step, Mapping) and step.get("type") == "import.table")
        )
        if len(import_steps) != 1:
            raise ResearchFlowPipelineError(
                "Research OS requires exactly one import.table source step"
            )
        step = import_steps[0]
        raw_params = _step_value(step, "params")
        if not isinstance(raw_params, Mapping):
            raise ResearchFlowPipelineError("import step parameters are unavailable")
        params = dict(raw_params)
        source_type = params.get("file_type")
        if not isinstance(source_type, str) or not source_type.strip():
            raise ResearchFlowPipelineError("import source type must be explicit")
        source_type = source_type.strip().lower().lstrip(".")
        layout = params.get("table_layout")
        selection = import_selection_from_params(params.get("import_selection"))
        if selection is None:
            step_id = _step_value(step, "id")
            pipeline = ops.step_collection()
            results = getattr(pipeline, "step_results", None)
            result = results.get(step_id) if isinstance(results, Mapping) else None
            new_columns = getattr(result, "new_columns", None)
            if not isinstance(new_columns, Mapping) or not new_columns:
                raise ResearchFlowPipelineError(
                    "canonical import column order is unavailable"
                )
            source_columns = tuple(str(item) for item in new_columns)
            included_columns = source_columns
        else:
            source_columns = tuple(selection.source_columns)
            included_columns = tuple(selection.included_columns)
        descriptor = SourceSchemaDescriptor(
            source_type=source_type,
            sheet_name=_layout_value(layout, "sheet_name"),
            header_row_index=_layout_value(layout, "header_row_index"),
            header_row_count=_layout_value(layout, "header_row_count"),
            data_start_row_index=_layout_value(layout, "data_start_row_index"),
            source_columns=source_columns,
            included_columns=included_columns,
        )
        labels: dict[str, str] = {}
        for index, variable_id in enumerate(
            (str(column) for column in dataset.df.columns),
            start=1,
        ):
            variable = dataset.variables[variable_id]
            raw_label = variable.label
            normalized = (
                unicodedata.normalize("NFC", raw_label).strip()
                if isinstance(raw_label, str)
                else ""
            )
            labels[variable_id] = (
                normalized if normalized and normalized != variable_id else f"V{index}"
            )
        return ResearchFlowPipelineSnapshot(
            dataset=dataset,
            source_schema=descriptor,
            variable_labels=labels,
        )


@dataclass(frozen=True)
class ResearchFlowViews:
    """The same verified authority projected at two explanation depths."""

    guided: ResearchFlowView
    standard: ResearchFlowView
    preparation: PassportBoundPreparation | None = None
    meaning_review: VariableMeaningReview | None = None

    def __post_init__(self) -> None:
        if self.guided.mode is not ControllerMode.GUIDED:
            raise ResearchFlowControllerError("guided view must use guided mode")
        if self.standard.mode is not ControllerMode.STANDARD:
            raise ResearchFlowControllerError("standard view must use standard mode")
        if self.preparation is not None:
            if not isinstance(self.preparation, PassportBoundPreparation):
                raise ResearchFlowControllerError("preparation must be passport-bound")
            self.preparation.__post_init__()
            if (
                self.preparation.preflight_disposition
                is not PreflightDisposition.PREPARE_READY
            ):
                raise ResearchFlowControllerError(
                    "only a ready preparation may enter the controller"
                )
        if self.meaning_review is not None:
            if not isinstance(self.meaning_review, VariableMeaningReview):
                raise ResearchFlowControllerError(
                    "meaning_review must be a sealed VariableMeaningReview"
                )
            self.meaning_review.__post_init__()
        comparable = (
            "state",
            "language",
            "decision_identity_digest",
            "primary_action",
            "secondary_actions",
            "options",
        )
        for field_name in comparable:
            if getattr(self.guided, field_name) != getattr(self.standard, field_name):
                raise ResearchFlowControllerError(
                    f"view authority differs across modes: {field_name}"
                )
        meaning_state = ResearchFlowState.VARIABLE_MEANING_REVIEW
        if self.standard.state is meaning_state and self.meaning_review is None:
            raise ResearchFlowControllerError(
                "variable_meaning_review requires an exact sealed review"
            )
        if self.meaning_review is not None and self.standard.state is not meaning_state:
            raise ResearchFlowControllerError(
                "meaning review authority requires variable_meaning_review"
            )
        guided_question = self.guided.question
        standard_question = self.standard.question
        if (guided_question is None) != (standard_question is None):
            raise ResearchFlowControllerError(
                "question authority differs across modes: presence"
            )
        if guided_question is not None and standard_question is not None:
            for field_name in (
                "status",
                "status_message",
                "title",
                "question_text",
                "base_reason",
                "selection_summary",
                "remaining_uncertainty",
                "not_sure_guidance",
                "caution",
            ):
                if getattr(guided_question, field_name) != getattr(
                    standard_question, field_name
                ):
                    raise ResearchFlowControllerError(
                        f"question authority differs across modes: {field_name}"
                    )
        guided_candidate = self.guided.candidate
        standard_candidate = self.standard.candidate
        if (guided_candidate is None) != (standard_candidate is None):
            raise ResearchFlowControllerError("candidate presence differs across modes")
        if guided_candidate is not None and standard_candidate is not None:
            for field_name in (
                "capability_label",
                "method_label",
                "claim_boundary",
                "review_status",
                "persistent_boundary",
            ):
                if getattr(guided_candidate, field_name) != getattr(
                    standard_candidate, field_name
                ):
                    raise ResearchFlowControllerError(
                        f"candidate authority differs across modes: {field_name}"
                    )

    def for_mode(self, mode: ControllerMode) -> ResearchFlowView:
        return self.guided if mode is ControllerMode.GUIDED else self.standard


def _transient_views(
    state: ResearchFlowState,
    *,
    language: Language,
    meaning_review: VariableMeaningReview | None = None,
) -> ResearchFlowViews:
    return ResearchFlowViews(
        guided=present_transient_state(
            state,
            mode=ControllerMode.GUIDED,
            language=language,
        ),
        standard=present_transient_state(
            state,
            mode=ControllerMode.STANDARD,
            language=language,
        ),
        meaning_review=meaning_review,
    )


def _static_views(
    boundary: StaticBoundary,
    *,
    language: Language,
) -> ResearchFlowViews:
    return ResearchFlowViews(
        guided=present_static_boundary(
            boundary,
            mode=ControllerMode.GUIDED,
            language=language,
        ),
        standard=present_static_boundary(
            boundary,
            mode=ControllerMode.STANDARD,
            language=language,
        ),
    )


def _action_model(action: object | None) -> dict[str, object] | None:
    if action is None:
        return None
    return {
        "command": action.command.value,
        "label": action.label,
        "enabled": action.enabled,
    }


def _view_model(view: ResearchFlowView) -> dict[str, object]:
    """Return a QML-safe projection without full authority digests."""

    question = view.question
    question_model = (
        None
        if question is None
        else {
            "status": question.status.value,
            "statusMessage": question.status_message,
            "title": question.title,
            "questionText": question.question_text,
            "baseReason": question.base_reason,
            "selectionSummary": question.selection_summary,
            "remainingUncertainty": question.remaining_uncertainty,
            "notSureGuidance": question.not_sure_guidance,
            "caution": question.caution,
            "evidenceRows": [
                {
                    "code": row.code,
                    "label": row.label,
                    "selectedValue": row.selected_value,
                    "runnerUpValue": row.runner_up_value,
                }
                for row in question.evidence_rows
            ],
            "sourceIdentityText": question.source_identity_text,
        }
    )
    candidate = view.candidate
    candidate_model = (
        None
        if candidate is None
        else {
            "capabilityLabel": candidate.capability_label,
            "methodLabel": candidate.method_label,
            "claimBoundary": candidate.claim_boundary,
            "roleRows": [
                {"label": label, "value": value} for label, value in candidate.role_rows
            ],
            "reviewStatus": candidate.review_status,
            "persistentBoundary": candidate.persistent_boundary,
        }
    )
    return {
        "state": view.state.value,
        "mode": view.mode.value,
        "language": view.language.value,
        "title": view.title,
        "body": view.body,
        "stageText": view.stage_text,
        "badgeText": view.badge_text,
        "visiblePassportDigest": view.visible_passport_digest,
        "primaryAction": _action_model(view.primary_action),
        "secondaryActions": [
            _action_model(action) for action in view.secondary_actions
        ],
        "options": [
            {
                "optionId": option.option_id,
                "label": option.label,
                "selected": option.selected,
                "enabled": option.enabled,
            }
            for option in view.options
        ],
        "question": question_model,
        "candidate": candidate_model,
        "evidenceRows": [
            {"label": label, "value": value} for label, value in view.evidence_rows
        ],
    }


class ResearchFlowRuntime:
    """Worker-confined durable runtime behind the UI-safe controller."""

    def __init__(
        self,
        *,
        pipeline_access: object,
        pipeline_version_provider: Callable[[], int],
        session_store: object,
        coordinator: object,
        initial_event_id_factory: Callable[[], str],
        answer_event_id_factory: Callable[[], str],
        language: Language,
        fingerprint: Callable[..., DatasetIdentity] = fingerprint_dataset,
    ) -> None:
        for value, name in (
            (pipeline_version_provider, "pipeline_version_provider"),
            (initial_event_id_factory, "initial_event_id_factory"),
            (answer_event_id_factory, "answer_event_id_factory"),
            (fingerprint, "fingerprint"),
        ):
            if not callable(value):
                raise ResearchFlowControllerError(f"{name} must be callable")
        if not hasattr(pipeline_access, "capture"):
            raise ResearchFlowControllerError("pipeline_access must support capture")
        if language not in {Language.KO, Language.EN}:
            raise ResearchFlowControllerError("language must be Korean or English")
        self._pipeline_access = pipeline_access
        self._pipeline_version_provider = pipeline_version_provider
        self._session_store = session_store
        self._coordinator = coordinator
        self._initial_event_id_factory = initial_event_id_factory
        self._answer_event_id_factory = answer_event_id_factory
        self._language = language
        self._fingerprint = fingerprint
        self._cache_lock = Lock()
        self._identity_cache: dict[tuple[int, str], DatasetIdentity] = {}
        self._identity: DatasetIdentity | None = None
        self._snapshot: ResearchFlowPipelineSnapshot | None = None
        self._handle: object | None = None
        self._record: DurableFlowRecord | None = None

    def adopt_language(self, language: Language) -> None:
        if language not in {Language.KO, Language.EN}:
            raise ResearchFlowControllerError("language must be Korean or English")
        self._language = language

    def present_current(
        self,
        *,
        language: Language,
        pipeline_version: int,
    ) -> ResearchFlowViews | None:
        if language not in {Language.KO, Language.EN}:
            raise ResearchFlowControllerError("language must be Korean or English")
        record = self._record
        identity = self._identity
        snapshot = self._snapshot
        if (
            record is None
            or identity is None
            or snapshot is None
            or identity.pipeline_version != pipeline_version
            or not self._pipeline_is_current(pipeline_version)
        ):
            return None
        previous = self._language
        self._language = language
        try:
            return self._record_views(
                record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        finally:
            self._language = previous

    def note_pipeline_version(self, pipeline_version: int) -> None:
        if type(pipeline_version) is not int or pipeline_version < 0:
            return
        with self._cache_lock:
            self._identity_cache = {
                key: value
                for key, value in self._identity_cache.items()
                if key == (pipeline_version, FINGERPRINT_CONTRACT_ID)
            }

    def current_dataset_fingerprint(self) -> str | None:
        identity = self._identity
        return None if identity is None else identity.dataset_fingerprint

    def _identity_for(
        self,
        snapshot: ResearchFlowPipelineSnapshot,
        *,
        pipeline_version: int,
        cancel_event: Event,
        force: bool = False,
    ) -> DatasetIdentity:
        key = (pipeline_version, FINGERPRINT_CONTRACT_ID)
        with self._cache_lock:
            cached = None if force else self._identity_cache.get(key)
        if cached is not None:
            return cached
        started_ns = monotonic_ns()
        deadline_ns = FINGERPRINT_WORKER_DEADLINE_SECONDS * 1_000_000_000

        def cancel_requested() -> bool:
            return cancel_event.is_set() or monotonic_ns() - started_ns > deadline_ns

        try:
            identity = self._fingerprint(
                snapshot.dataset,
                snapshot.source_schema,
                pipeline_version=pipeline_version,
                cancel_requested=cancel_requested,
            )
        except FingerprintCancelled as exc:
            if cancel_event.is_set():
                raise
            if monotonic_ns() - started_ns > deadline_ns:
                raise FingerprintDeadlineExceeded(
                    "fingerprint worker exceeded its fixed deadline"
                ) from exc
            raise
        if monotonic_ns() - started_ns > deadline_ns:
            raise FingerprintDeadlineExceeded(
                "fingerprint worker exceeded its fixed deadline"
            )
        if not isinstance(identity, DatasetIdentity):
            raise ResearchFlowControllerError("fingerprint returned no DatasetIdentity")
        if identity.pipeline_version != pipeline_version:
            raise ResearchFlowControllerError(
                "fingerprint returned a different pipeline version"
            )
        with self._cache_lock:
            self._identity_cache = {key: identity}
        return identity

    def _pipeline_is_current(self, pipeline_version: int) -> bool:
        try:
            return self._pipeline_version_provider() == pipeline_version
        except Exception:
            return False

    @staticmethod
    def _same_identity(left: DatasetIdentity, right: DatasetIdentity) -> bool:
        return (
            left.fingerprint_contract_id == right.fingerprint_contract_id
            and left.dataset_fingerprint == right.dataset_fingerprint
            and left.source_schema_fingerprint == right.source_schema_fingerprint
            and left.variable_ids == right.variable_ids
            and left.pipeline_version == right.pipeline_version
        )

    def _fresh_context(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> tuple[ResearchFlowPipelineSnapshot, DatasetIdentity]:
        previous = self._identity
        if previous is None or self._snapshot is None:
            raise ResearchFlowStaleError("Research OS intake was not started")
        if previous.pipeline_version != pipeline_version:
            raise ResearchFlowStaleError("captured pipeline version changed")
        snapshot = self._pipeline_access.capture()
        identity = self._identity_for(
            snapshot,
            pipeline_version=pipeline_version,
            cancel_event=cancel_event,
        )
        if not self._pipeline_is_current(pipeline_version) or not self._same_identity(
            identity, previous
        ):
            raise ResearchFlowStaleError("current dataset identity changed")
        self._snapshot = snapshot
        self._identity = identity
        return snapshot, identity

    def _ensure_handle(self, identity: DatasetIdentity) -> object:
        if self._handle is None:
            self._handle = self._session_store.open_or_allocate(
                identity,
                expected_active_task_id=None,
            )
        return self._handle

    def _record_views(
        self,
        record: DurableFlowRecord,
        *,
        identity: DatasetIdentity,
        snapshot: ResearchFlowPipelineSnapshot,
        pipeline_version: int,
    ) -> ResearchFlowViews:
        preflight = None
        if (
            record.request.current_dataset_fingerprint != identity.dataset_fingerprint
            or record.request.study.source_schema_fingerprint
            != identity.source_schema_fingerprint
            or record.request.available_variable_ids != identity.variable_ids
        ):
            return _transient_views(
                ResearchFlowState.REPLAN_REQUIRED,
                language=self._language,
            )
        if isinstance(record, DurableDecision):
            if record.action is PrimaryAction.RECOMMEND_LOCAL:
                mapping = map_passport_to_step(
                    record.passport,
                    record.request,
                    current_dataset_fingerprint=identity.dataset_fingerprint,
                )
                preflight = preflight_mapped_step(
                    mapping,
                    snapshot.dataset,
                    captured_pipeline_version=pipeline_version,
                    current_pipeline_version=self._pipeline_version_provider,
                )
        return ResearchFlowViews(
            guided=present_durable_record(
                record,
                mode=ControllerMode.GUIDED,
                language=self._language,
                preflight=preflight,
                variable_labels=snapshot.variable_labels,
            ),
            standard=present_durable_record(
                record,
                mode=ControllerMode.STANDARD,
                language=self._language,
                preflight=preflight,
                variable_labels=snapshot.variable_labels,
            ),
            preparation=(
                preflight.preparation
                if preflight is not None
                and preflight.disposition is PreflightDisposition.PREPARE_READY
                else None
            ),
        )

    def _typed_error(self, exc: Exception) -> ResearchFlowViews:
        if isinstance(exc, ResearchFlowStaleError):
            state = ResearchFlowState.REPLAN_REQUIRED
        elif isinstance(exc, FingerprintDeadlineExceeded):
            state = ResearchFlowState.MEMORY_UNAVAILABLE
        elif isinstance(exc, FingerprintCancelled):
            state = ResearchFlowState.CANCELLED
        elif isinstance(
            exc,
            (TaskSessionUnavailableError, LiveResearchFlowUnavailableError),
        ):
            state = ResearchFlowState.MEMORY_UNAVAILABLE
        elif isinstance(
            exc,
            (TaskSessionIntegrityError, LiveResearchFlowIntegrityError),
        ):
            state = ResearchFlowState.CORRUPTION
        else:
            state = ResearchFlowState.FAILURE
        return _transient_views(state, language=self._language)

    def start(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            snapshot = self._pipeline_access.capture()
            identity = self._identity_for(
                snapshot,
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("Research OS start was cancelled")
            if not self._pipeline_is_current(pipeline_version):
                return _transient_views(
                    ResearchFlowState.REPLAN_REQUIRED,
                    language=self._language,
                )
            handle = self._session_store.locate_existing(identity)
            self._identity = identity
            self._snapshot = snapshot
            self._handle = handle
            if handle is None:
                self._record = None
                return _transient_views(
                    ResearchFlowState.INTAKE_CAUSAL,
                    language=self._language,
                )
            record = self._coordinator.recover_current_or_none(handle)
            self._record = record
            if record is None:
                return _transient_views(
                    ResearchFlowState.INTAKE_CAUSAL,
                    language=self._language,
                )
            return self._record_views(
                record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowConflictError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def commit_initial(
        self,
        *,
        profile: P1TaskProfile,
        roles: P1RoleBindings,
        meaning_review: VariableMeaningReview,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            if not isinstance(profile, P1TaskProfile) or not isinstance(
                roles, P1RoleBindings
            ):
                raise ResearchFlowControllerError(
                    "initial intake must use closed P1 values"
                )
            if not isinstance(meaning_review, VariableMeaningReview):
                raise ResearchFlowControllerError(
                    "initial intake requires one sealed meaning review"
                )
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("initial intake was cancelled")
            current_review = build_variable_meaning_review(
                snapshot.dataset,
                dataset_fingerprint=identity.dataset_fingerprint,
                pipeline_version=pipeline_version,
                profile=profile,
                roles=roles,
            )
            if current_review != meaning_review:
                raise ResearchFlowStaleError(
                    "confirmed variable meanings no longer match current data"
                )
            handle = self._ensure_handle(identity)
            initial_event_id = self._initial_event_id_factory()
            request = build_p1_request(
                P1IntakeDraft(profile=profile, roles=roles),
                task_project_id=handle.record.task_project_id,
                initial_event_id=initial_event_id,
                dataset_fingerprint=identity.dataset_fingerprint,
                source_schema_fingerprint=identity.source_schema_fingerprint,
                available_variable_ids=identity.variable_ids,
                language=self._language,
                role_confirmation_refs=(
                    initial_event_id,
                    meaning_review.provenance_ref,
                ),
            )
            record = self._coordinator.commit_initial(handle, request)
            self._record = record
            return self._record_views(
                record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowConflictError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def review_variable_meanings(
        self,
        *,
        profile: P1TaskProfile,
        roles: P1RoleBindings,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        """Build a dataset-bound review without allocating storage or a ledger."""

        try:
            if not isinstance(profile, P1TaskProfile) or not isinstance(
                roles, P1RoleBindings
            ):
                raise ResearchFlowControllerError(
                    "meaning review must use closed P1 values"
                )
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("variable meaning review was cancelled")
            review = build_variable_meaning_review(
                snapshot.dataset,
                dataset_fingerprint=identity.dataset_fingerprint,
                pipeline_version=pipeline_version,
                profile=profile,
                roles=roles,
            )
            return _transient_views(
                ResearchFlowState.VARIABLE_MEANING_REVIEW,
                language=self._language,
                meaning_review=review,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def commit_causal_boundary(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("causal boundary record was cancelled")
            handle = self._ensure_handle(identity)
            request = build_causal_abstention_request(
                task_project_id=handle.record.task_project_id,
                initial_event_id=self._initial_event_id_factory(),
                dataset_fingerprint=identity.dataset_fingerprint,
                source_schema_fingerprint=identity.source_schema_fingerprint,
                available_variable_ids=identity.variable_ids,
                language=self._language,
            )
            record = self._coordinator.commit_initial(handle, request)
            self._record = record
            return self._record_views(
                record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowConflictError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def _answer_value(
        self,
        record: DurableDecision,
        *,
        option_id: str,
        variable_ids: tuple[str, ...],
        not_sure: bool,
    ) -> AnswerValue:
        if (
            record.action is not PrimaryAction.CLARIFY
            or record.passport.clarify is None
        ):
            raise ResearchFlowControllerError(
                "only a current clarification can accept an answer"
            )
        reference = record.passport.clarify.clarification_ref
        spec = build_p1_clarification_registry().get(reference.question_id)
        if not_sure:
            if option_id != "not_sure" or variable_ids:
                raise ResearchFlowControllerError("not_sure cannot carry a value")
            return AnswerValue(kind=AnswerValueKind.NOT_SURE)
        variable_kinds = {
            AnswerKind.VARIABLE_SINGLE,
            AnswerKind.VARIABLE_MULTI,
            AnswerKind.ORDERED_VARIABLES,
        }
        if spec.answer_kind in variable_kinds:
            if option_id != "variables":
                raise ResearchFlowControllerError(
                    "variable clarification requires the closed variables token"
                )
            return AnswerValue(
                kind=AnswerValueKind.VARIABLES,
                variable_ids=variable_ids,
            )
        choices = {choice.value for choice in spec.choices}
        if option_id not in choices or variable_ids:
            raise ResearchFlowControllerError(
                "choice answer is outside the committed question"
            )
        return AnswerValue(
            kind=AnswerValueKind.CHOICE,
            choice_value=option_id,
        )

    def answer(
        self,
        *,
        option_id: str,
        variable_ids: tuple[str, ...],
        not_sure: bool,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            record = self._record
            handle = self._handle
            if not isinstance(record, DurableDecision) or handle is None:
                raise ResearchFlowControllerError(
                    "no current durable clarification is available"
                )
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("clarification answer was cancelled")
            reference = record.passport.clarify.clarification_ref
            answer = ClarificationAnswerEvent(
                event_id=self._answer_event_id_factory(),
                project_id=record.task_project_id,
                event_sequence=record.committed_sequence + 1,
                source_passport_digest=record.passport_digest,
                question_id=reference.question_id,
                question_version=reference.question_version,
                question_digest=reference.question_digest,
                fact_address=reference.fact_address,
                answer_value=self._answer_value(
                    record,
                    option_id=option_id,
                    variable_ids=variable_ids,
                    not_sure=not_sure,
                ),
            )
            next_record = self._coordinator.commit_answer(handle, answer)
            self._record = next_record
            return self._record_views(
                next_record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowConflictError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def resume(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        if not isinstance(self._record, DurablePendingDecision):
            return self.start(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
        try:
            record = self._record
            handle = self._handle
            if handle is None:
                raise ResearchFlowControllerError(
                    "pending decision has no verified task handle"
                )
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("pending recovery was cancelled")
            next_record = self._coordinator.resume_pending(handle, record)
            self._record = next_record
            return self._record_views(
                next_record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowConflictError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def retract(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        _ = pipeline_version
        try:
            if not isinstance(self._record, DurableDecision) or self._handle is None:
                raise ResearchFlowControllerError(
                    "no current durable decision can be retracted"
                )
            if cancel_event.is_set():
                raise FingerprintCancelled("decision retraction was cancelled")
            record = self._coordinator.retract_current(self._handle)
            self._record = record
            return self._record_views(
                record,
                identity=self._identity,
                snapshot=self._snapshot,
                pipeline_version=self._identity.pipeline_version,
            )
        except (
            FingerprintCancelled,
            ResearchFlowControllerError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowConflictError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def replan(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            snapshot = self._pipeline_access.capture()
            identity = self._identity_for(
                snapshot,
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
                force=True,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("replan was cancelled")
            if not self._pipeline_is_current(pipeline_version):
                raise ResearchFlowStaleError("pipeline changed during fresh replanning")
            if self._handle is not None:
                self._handle = self._session_store.start_replan(
                    self._handle,
                    identity,
                )
            self._identity = identity
            self._snapshot = snapshot
            self._record = None
            return _transient_views(
                ResearchFlowState.INTAKE_CAUSAL,
                language=self._language,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowConflictError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)

    def prepare(
        self,
        *,
        pipeline_version: int,
        cancel_event: Event,
    ) -> ResearchFlowViews:
        try:
            record = self._record
            if (
                not isinstance(record, DurableDecision)
                or record.action is not PrimaryAction.RECOMMEND_LOCAL
            ):
                raise ResearchFlowControllerError(
                    "only a current local candidate can be prepared"
                )
            snapshot, identity = self._fresh_context(
                pipeline_version=pipeline_version,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise FingerprintCancelled("preparation review was cancelled")
            current = self._record_views(
                record,
                identity=identity,
                snapshot=snapshot,
                pipeline_version=pipeline_version,
            )
            if current.standard.state is not ResearchFlowState.CANDIDATE_READY:
                return current
            if current.preparation is None:
                raise ResearchFlowControllerError(
                    "ready candidate has no sealed preparation"
                )
            review = _transient_views(
                ResearchFlowState.PREPARE_REVIEW, language=self._language
            )
            return ResearchFlowViews(
                guided=review.guided,
                standard=review.standard,
                preparation=current.preparation,
            )
        except (
            FingerprintCancelled,
            FingerprintContractError,
            ResearchFlowControllerError,
            ResearchFlowPipelineError,
            ResearchFlowStaleError,
            TaskSessionUnavailableError,
            TaskSessionConflictError,
            TaskSessionIntegrityError,
            LiveResearchFlowUnavailableError,
            LiveResearchFlowConflictError,
            LiveResearchFlowIntegrityError,
            ValueError,
        ) as exc:
            return self._typed_error(exc)


def _local_reference(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class _LazyDependency:
    def __init__(self, factory: Callable[[], object]) -> None:
        self._factory = factory
        self._value: object | None = None
        self._lock = Lock()

    def __getattr__(self, name: str) -> object:
        value = self._value
        if value is None:
            with self._lock:
                value = self._value
                if value is None:
                    value = self._factory()
                    self._value = value
        return getattr(value, name)


def build_default_research_flow_runtime(
    *,
    pipeline_access: ResearchFlowPipelineAccess,
    pipeline_version_provider: Callable[[], int],
    language: Language,
) -> ResearchFlowRuntime:
    """Build lazy local-only dependencies without opening storage."""

    return ResearchFlowRuntime(
        pipeline_access=pipeline_access,
        pipeline_version_provider=pipeline_version_provider,
        session_store=ResearchTaskSessionStore(
            task_id_factory=lambda: _local_reference("task"),
            utc_clock=_utc_now,
        ),
        coordinator=_LazyDependency(
            lambda: LiveResearchFlowCoordinator(
                event_id_factory=lambda: _local_reference("event"),
                passport_object_id_factory=lambda: _local_reference("passport"),
                utc_clock=_utc_now,
            )
        ),
        initial_event_id_factory=lambda: _local_reference("event"),
        answer_event_id_factory=lambda: _local_reference("event"),
        language=language,
    )


class ResearchFlowController(QObject):
    """Queue expensive Research OS work and publish only closed safe views."""

    stateChanged = Signal()
    workerResultReady = Signal(object)

    def __init__(
        self,
        *,
        runtime: _ResearchFlowRuntime,
        worker: _ResearchFlowWorker,
        pipeline_version_provider: Callable[[], int],
        mode_change_request: Callable[[str], bool],
        initial_mode: ControllerMode,
        language: Language,
        preparation_editor: ResearchPreparationEditor | None = None,
        confirmation_published: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._runtime = runtime
        self._worker = worker
        self._pipeline_version_provider = pipeline_version_provider
        self._mode_change_request = mode_change_request
        self._mode = initial_mode
        self._language = language
        self._views = _transient_views(ResearchFlowState.IDLE, language=language)
        self._busy = False
        self._run_id = 0
        self._active_pipeline_version = pipeline_version_provider()
        self._cancel_event: Event | None = None
        self._previous_views = self._views
        self._selected_profile: P1TaskProfile | None = None
        self._pending_roles: P1RoleBindings | None = None
        self._preparation_editor = preparation_editor
        self._confirmation_published = confirmation_published or (lambda: None)
        self._preparation_review: PreparationReview | None = None
        self.workerResultReady.connect(self._apply_worker_result)

    @property
    def current_view(self) -> ResearchFlowView:
        return self._views.for_mode(self._mode)

    @Property("QVariantMap", notify=stateChanged)
    def stateModel(self) -> dict[str, object]:
        model = _view_model(self.current_view)
        meaning_review = self._views.meaning_review
        if (
            meaning_review is not None
            and self.current_view.state is ResearchFlowState.VARIABLE_MEANING_REVIEW
        ):
            model["meaningReview"] = {
                "visibleReviewDigest": (
                    meaning_review.review_digest[:12]
                    if self._mode is ControllerMode.STANDARD
                    else ""
                ),
                "profileId": meaning_review.profile_id,
                "rows": [
                    {
                        "role": row.role,
                        "variableId": row.variable_id,
                        "label": row.label or "",
                        "measure": row.measure,
                        "valueLabels": [
                            {"value": value, "label": label}
                            for value, label in row.value_labels
                        ],
                        "missingCodes": list(row.missing_codes),
                        "storageDtype": row.storage_dtype,
                        "evidenceSource": row.evidence_source,
                        "conceptDefinitionStatus": (row.concept_definition_status),
                        "unitStatus": row.unit_status,
                    }
                    for row in meaning_review.rows
                ],
            }
        review = self._preparation_review
        if review is not None and self.current_view.state in {
            ResearchFlowState.PREPARE_REVIEW,
            ResearchFlowState.CONFIRMED,
        }:
            preparation = review.preparation
            model["preparationReview"] = {
                "stepType": preparation.step_type,
                "visiblePreparationDigest": preparation.preparation_digest[:12],
                "experimental": True,
                "automaticRun": False,
                "settingsRows": [
                    {"label": label, "value": value}
                    for label, value in review.settings_rows
                ],
            }
        return model

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Slot(result=bool)
    def start(self) -> bool:
        if self.current_view.state not in {
            ResearchFlowState.IDLE,
            ResearchFlowState.CANCELLED,
            ResearchFlowState.FAILURE,
            ResearchFlowState.MEMORY_UNAVAILABLE,
        }:
            return False
        return self._submit_runtime(
            ResearchFlowState.FINGERPRINTING,
            lambda version, cancel_event: self._runtime.start(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    def _submit_runtime(
        self,
        busy_state: ResearchFlowState,
        operation: Callable[[int, Event], ResearchFlowViews],
    ) -> bool:
        if self._busy:
            return False
        version = self._pipeline_version_provider()
        self._run_id += 1
        run_id = self._run_id
        self._active_pipeline_version = version
        cancel_event = Event()
        self._cancel_event = cancel_event
        self._previous_views = self._views
        self._busy = True
        self._views = _transient_views(busy_state, language=self._language)
        self.stateChanged.emit()
        future = self._worker.submit(
            run_id=run_id,
            pipeline_version=version,
            job=lambda: operation(version, cancel_event),
        )
        future.add_done_callback(
            lambda completed: self.workerResultReady.emit(completed.result())
        )
        return True

    def _publish_transient(self, state: ResearchFlowState) -> bool:
        if self._busy:
            return False
        self._views = _transient_views(state, language=self._language)
        self.stateChanged.emit()
        return True

    def _publish_static(self, boundary: StaticBoundary) -> bool:
        if self._busy:
            return False
        self._views = _static_views(boundary, language=self._language)
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def chooseCausalNo(self) -> bool:
        if self.current_view.state is not ResearchFlowState.INTAKE_CAUSAL:
            return False
        return self._publish_transient(ResearchFlowState.INTAKE_PROFILE)

    @Slot(result=bool)
    def chooseCausalYes(self) -> bool:
        if self.current_view.state is not ResearchFlowState.INTAKE_CAUSAL:
            return False
        return self._publish_static(StaticBoundary.CAUSAL_SCOPE_NOTICE)

    @Slot(result=bool)
    def chooseCausalNotSure(self) -> bool:
        if self.current_view.state is not ResearchFlowState.INTAKE_CAUSAL:
            return False
        return self._publish_static(StaticBoundary.CAUSAL_INTENT_UNKNOWN)

    @Slot(result=bool)
    def recordCausalBoundary(self) -> bool:
        if self.current_view.state is not ResearchFlowState.CAUSAL_SCOPE_NOTICE:
            return False
        return self._submit_runtime(
            ResearchFlowState.COMMITTING,
            lambda version, cancel_event: self._runtime.commit_causal_boundary(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def back(self) -> bool:
        state = self.current_view.state
        if state is ResearchFlowState.VARIABLE_MEANING_REVIEW:
            self._pending_roles = None
            return self._publish_transient(ResearchFlowState.INTAKE_ROLES)
        if state in {
            ResearchFlowState.CAUSAL_SCOPE_NOTICE,
            ResearchFlowState.INTAKE_BLOCKED,
        }:
            return self._publish_transient(ResearchFlowState.INTAKE_CAUSAL)
        if state is ResearchFlowState.SCOPE_BOUNDARY:
            return self._publish_transient(ResearchFlowState.INTAKE_PROFILE)
        return False

    @Slot(str, result=bool)
    def selectProfile(self, profile: str) -> bool:
        if self.current_view.state is not ResearchFlowState.INTAKE_PROFILE:
            return False
        try:
            selected = P1TaskProfile(profile)
        except ValueError:
            return False
        self._selected_profile = selected
        return self._publish_transient(ResearchFlowState.INTAKE_ROLES)

    @Slot(result=bool)
    def chooseNoMatchingProfile(self) -> bool:
        if self.current_view.state is not ResearchFlowState.INTAKE_PROFILE:
            return False
        return self._publish_static(StaticBoundary.SCOPE_BOUNDARY)

    @staticmethod
    def _roles_from_model(model: object) -> P1RoleBindings | None:
        if not isinstance(model, Mapping):
            return None
        allowed = {
            "outcome",
            "group",
            "focal_predictor",
            "repeated_measure_order",
        }
        if not set(model).issubset(allowed):
            return None
        values: dict[str, tuple[str, ...]] = {}
        for name in allowed:
            raw = model.get(name, ())
            if not isinstance(raw, (list, tuple)) or any(
                not isinstance(item, str) for item in raw
            ):
                return None
            values[name] = tuple(raw)
        try:
            return P1RoleBindings(**values)
        except ValueError:
            return None

    @Slot("QVariantMap", result=bool)
    def submitRoles(self, model: object) -> bool:
        if (
            self.current_view.state is not ResearchFlowState.INTAKE_ROLES
            or self._selected_profile is None
        ):
            return False
        roles = self._roles_from_model(model)
        if roles is None:
            return False
        profile = self._selected_profile
        self._pending_roles = roles
        submitted = self._submit_runtime(
            ResearchFlowState.MEANING_REVIEWING,
            lambda version, cancel_event: self._runtime.review_variable_meanings(
                profile=profile,
                roles=roles,
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )
        if not submitted:
            self._pending_roles = None
        return submitted

    @Slot(result=bool)
    def confirmVariableMeanings(self) -> bool:
        review = self._views.meaning_review
        profile = self._selected_profile
        roles = self._pending_roles
        if (
            self.current_view.state is not ResearchFlowState.VARIABLE_MEANING_REVIEW
            or review is None
            or profile is None
            or roles is None
        ):
            return False
        return self._submit_runtime(
            ResearchFlowState.COMMITTING,
            lambda version, cancel_event: self._runtime.commit_initial(
                profile=profile,
                roles=roles,
                meaning_review=review,
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(str, "QVariantList", result=bool)
    def answer(self, option_id: str, variable_ids: object) -> bool:
        if self.current_view.state is not ResearchFlowState.CLARIFY_READY:
            return False
        if not isinstance(variable_ids, (list, tuple)) or any(
            not isinstance(item, str) for item in variable_ids
        ):
            return False
        selected_ids = tuple(variable_ids)
        closed_options = {
            option.option_id
            for option in self.current_view.options
            if option.option_id != "not_sure"
        }
        if option_id == "variables":
            if closed_options:
                return False
        elif option_id not in closed_options or selected_ids:
            return False
        return self._submit_runtime(
            ResearchFlowState.COMMITTING,
            lambda version, cancel_event: self._runtime.answer(
                option_id=option_id,
                variable_ids=selected_ids,
                not_sure=False,
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def answerNotSure(self) -> bool:
        if self.current_view.state is not ResearchFlowState.CLARIFY_READY:
            return False
        return self._submit_runtime(
            ResearchFlowState.COMMITTING,
            lambda version, cancel_event: self._runtime.answer(
                option_id="not_sure",
                variable_ids=(),
                not_sure=True,
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def resume(self) -> bool:
        if self.current_view.state not in {
            ResearchFlowState.RECOVERY_PENDING,
            ResearchFlowState.MEMORY_UNAVAILABLE,
            ResearchFlowState.FAILURE,
            ResearchFlowState.CANCELLED,
        }:
            return False
        busy_state = (
            ResearchFlowState.COMMITTING
            if self.current_view.state is ResearchFlowState.RECOVERY_PENDING
            else ResearchFlowState.FINGERPRINTING
        )
        return self._submit_runtime(
            busy_state,
            lambda version, cancel_event: self._runtime.resume(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def retract(self) -> bool:
        if self.current_view.state is ResearchFlowState.PREPARE_REVIEW:
            self._discard_pending_confirmation()
        if self.current_view.state not in {
            ResearchFlowState.CLARIFY_READY,
            ResearchFlowState.CANDIDATE_READY,
            ResearchFlowState.PREPARATION_BLOCKED,
            ResearchFlowState.ABSTAIN_READY,
        }:
            return False
        return self._submit_runtime(
            ResearchFlowState.COMMITTING,
            lambda version, cancel_event: self._runtime.retract(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def replan(self) -> bool:
        if self.current_view.state not in {
            ResearchFlowState.REPLAN_REQUIRED,
            ResearchFlowState.RETRACTED,
            ResearchFlowState.ABSTAIN_READY,
        }:
            return False
        return self._submit_runtime(
            ResearchFlowState.FINGERPRINTING,
            lambda version, cancel_event: self._runtime.replan(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def prepare(self) -> bool:
        if self.current_view.state is not ResearchFlowState.CANDIDATE_READY:
            return False
        return self._submit_runtime(
            ResearchFlowState.HANDOFF_PREFLIGHT,
            lambda version, cancel_event: self._runtime.prepare(
                pipeline_version=version,
                cancel_event=cancel_event,
            ),
        )

    @Slot(result=bool)
    def confirm(self) -> bool:
        review = self._preparation_review
        if (
            self._busy
            or self.current_view.state is not ResearchFlowState.PREPARE_REVIEW
            or review is None
            or self._preparation_editor is None
        ):
            return False
        result = self._preparation_editor.confirm(
            review,
            pipeline_version=self._pipeline_version_provider(),
        )
        if not result.ok:
            self._preparation_review = None
            state = (
                ResearchFlowState.REPLAN_REQUIRED
                if result.error_code
                in {
                    "research_preparation_stale",
                    "research_preparation_blocked",
                }
                else ResearchFlowState.FAILURE
            )
            self._views = _transient_views(state, language=self._language)
            self.stateChanged.emit()
            return False
        self._active_pipeline_version = result.pipeline_version
        self._runtime.note_pipeline_version(result.pipeline_version)
        confirmed = _transient_views(
            ResearchFlowState.CONFIRMED,
            language=self._language,
        )
        self._views = ResearchFlowViews(
            guided=confirmed.guided,
            standard=confirmed.standard,
            preparation=review.preparation,
        )
        self._confirmation_published()
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def cancel(self) -> bool:
        if not self._busy or self._cancel_event is None:
            return False
        self._cancel_event.set()
        self._busy = False
        self._pending_roles = None
        durable_states = {
            ResearchFlowState.CLARIFY_READY,
            ResearchFlowState.CANDIDATE_READY,
            ResearchFlowState.PREPARATION_BLOCKED,
            ResearchFlowState.ABSTAIN_READY,
            ResearchFlowState.RECOVERY_PENDING,
            ResearchFlowState.RETRACTED,
        }
        self._views = (
            self._previous_views
            if self._previous_views.standard.state in durable_states
            else _transient_views(
                ResearchFlowState.CANCELLED,
                language=self._language,
            )
        )
        self.stateChanged.emit()
        return True

    @Slot(str, result=bool)
    def syncMode(self, mode: str) -> bool:
        try:
            requested = ControllerMode(mode)
        except ValueError:
            return False
        if requested is self._mode:
            return True
        if not self._mode_change_request(requested.value):
            return False
        if self._mode is not requested:
            self._discard_pending_confirmation()
            self._mode = requested
            self.stateChanged.emit()
        return True

    def adoptMode(self, mode: str) -> None:
        try:
            adopted = ControllerMode(mode)
        except ValueError:
            return
        if adopted is self._mode:
            return
        self._discard_pending_confirmation()
        self._mode = adopted
        self.stateChanged.emit()

    @Slot(str, result=bool)
    def adoptLanguage(self, language: str) -> bool:
        try:
            adopted = Language(language)
        except (ValueError, ResearchFlowControllerError):
            return False
        if adopted is self._language:
            return True
        state = self.current_view.state
        static_boundaries = {
            ResearchFlowState.CAUSAL_SCOPE_NOTICE: StaticBoundary.CAUSAL_SCOPE_NOTICE,
            ResearchFlowState.INTAKE_BLOCKED: StaticBoundary.CAUSAL_INTENT_UNKNOWN,
            ResearchFlowState.SCOPE_BOUNDARY: StaticBoundary.SCOPE_BOUNDARY,
        }
        durable_states = {
            ResearchFlowState.CLARIFY_READY,
            ResearchFlowState.CANDIDATE_READY,
            ResearchFlowState.PREPARATION_BLOCKED,
            ResearchFlowState.ABSTAIN_READY,
            ResearchFlowState.RECOVERY_PENDING,
            ResearchFlowState.RETRACTED,
        }
        try:
            if state in static_boundaries:
                translated = _static_views(
                    static_boundaries[state],
                    language=adopted,
                )
            elif state in durable_states:
                translated = self._runtime.present_current(
                    language=adopted,
                    pipeline_version=self._pipeline_version_provider(),
                )
                if translated is None:
                    return False
            elif state is ResearchFlowState.VARIABLE_MEANING_REVIEW:
                translated = _transient_views(
                    state,
                    language=adopted,
                    meaning_review=self._views.meaning_review,
                )
            else:
                translated = _transient_views(state, language=adopted)
        except (ValueError, ResearchFlowControllerError):
            return False
        self._runtime.adopt_language(adopted)
        self._language = adopted
        self._views = ResearchFlowViews(
            guided=translated.guided,
            standard=translated.standard,
            preparation=self._views.preparation,
            meaning_review=self._views.meaning_review,
        )
        self.stateChanged.emit()
        return True

    def _discard_pending_confirmation(self) -> None:
        if (
            self._preparation_review is None
            or self.current_view.state is not ResearchFlowState.PREPARE_REVIEW
        ):
            return
        if self._previous_views.standard.state is ResearchFlowState.CANDIDATE_READY:
            self._views = self._previous_views
        self._preparation_review = None

    @Slot()
    def syncPipelineVersion(self) -> None:
        version = self._pipeline_version_provider()
        if version == self._active_pipeline_version:
            return
        was_idle = self.current_view.state is ResearchFlowState.IDLE
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._run_id += 1
        self._active_pipeline_version = version
        self._runtime.note_pipeline_version(version)
        self._busy = False
        self._preparation_review = None
        self._selected_profile = None
        self._pending_roles = None
        if was_idle:
            return
        self._views = _transient_views(
            ResearchFlowState.REPLAN_REQUIRED,
            language=self._language,
        )
        self.stateChanged.emit()

    def _apply_worker_result(
        self,
        result: EngineJobResult[ResearchFlowViews],
    ) -> None:
        if result.run_id != self._run_id:
            return
        if result.pipeline_version != self._pipeline_version_provider():
            return
        self._busy = False
        self._cancel_event = None
        if result.ok and isinstance(result.payload, ResearchFlowViews):
            payload = result.payload
            if payload.standard.state is ResearchFlowState.PREPARE_REVIEW:
                if self._preparation_editor is None or payload.preparation is None:
                    self._views = _transient_views(
                        ResearchFlowState.FAILURE,
                        language=self._language,
                    )
                    self._preparation_review = None
                else:
                    try:
                        self._preparation_review = self._preparation_editor.review(
                            payload.preparation,
                            pipeline_version=result.pipeline_version,
                        )
                        self._views = payload
                    except (TypeError, ValueError):
                        self._views = _transient_views(
                            ResearchFlowState.FAILURE,
                            language=self._language,
                        )
                        self._preparation_review = None
            else:
                self._views = payload
                if payload.standard.state is not ResearchFlowState.CANDIDATE_READY:
                    self._preparation_review = None
            if payload.standard.state is not ResearchFlowState.VARIABLE_MEANING_REVIEW:
                self._pending_roles = None
                self._selected_profile = None
        else:
            self._views = _transient_views(
                ResearchFlowState.FAILURE,
                language=self._language,
            )
            self._pending_roles = None
            self._selected_profile = None
        self.stateChanged.emit()
