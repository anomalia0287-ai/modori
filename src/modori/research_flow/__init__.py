"""Application boundary for the live, local Research OS flow."""

from modori.research_flow.contracts import (
    FINGERPRINT_CONTRACT_ID,
    P1_REACHABLE_STATES,
    DatasetIdentity,
    FlowErrorKind,
    PassportBoundPreparation,
    PassportStepMapping,
    PreflightDisposition,
    ResearchFlowContractError,
    ResearchFlowState,
    StaticBoundary,
)
from modori.research_flow.coordinator import (
    DurableDecision,
    DurableFlowRecord,
    DurablePendingDecision,
    DurableRetraction,
    LiveResearchFlowConflictError,
    LiveResearchFlowCoordinator,
    LiveResearchFlowError,
    LiveResearchFlowIntegrityError,
    LiveResearchFlowUnavailableError,
)
from modori.research_flow.fingerprint import (
    FINGERPRINT_CANCELLATION_INTERVAL_CELLS,
    FINGERPRINT_DEFAULT_MAX_CELLS,
    FINGERPRINT_WORKER_DEADLINE_SECONDS,
    FingerprintCancelled,
    FingerprintContractError,
    FingerprintDeadlineExceeded,
    FingerprintLimitError,
    SourceSchemaDescriptor,
    fingerprint_dataset,
)
from modori.research_flow.handoff import (
    PassportHandoffError,
    map_passport_to_step,
    validate_passport_bound_preparation,
)
from modori.research_flow.task_session import (
    ResearchTaskHandle,
    ResearchTaskSessionStore,
    TaskSessionConflictError,
    TaskSessionError,
    TaskSessionIntegrityError,
    TaskSessionUnavailableError,
)

__all__ = [
    "FINGERPRINT_CONTRACT_ID",
    "FINGERPRINT_CANCELLATION_INTERVAL_CELLS",
    "FINGERPRINT_DEFAULT_MAX_CELLS",
    "FINGERPRINT_WORKER_DEADLINE_SECONDS",
    "P1_REACHABLE_STATES",
    "DatasetIdentity",
    "DurableDecision",
    "DurableFlowRecord",
    "DurablePendingDecision",
    "DurableRetraction",
    "FlowErrorKind",
    "FingerprintCancelled",
    "FingerprintContractError",
    "FingerprintDeadlineExceeded",
    "FingerprintLimitError",
    "LiveResearchFlowConflictError",
    "LiveResearchFlowCoordinator",
    "LiveResearchFlowError",
    "LiveResearchFlowIntegrityError",
    "LiveResearchFlowUnavailableError",
    "PassportBoundPreparation",
    "PassportHandoffError",
    "PassportStepMapping",
    "PreflightResult",
    "PreflightDisposition",
    "ResearchFlowContractError",
    "ResearchFlowState",
    "ResearchTaskHandle",
    "ResearchTaskSessionStore",
    "SourceSchemaDescriptor",
    "StaticBoundary",
    "StepInputIssue",
    "TaskSessionConflictError",
    "TaskSessionError",
    "TaskSessionIntegrityError",
    "TaskSessionUnavailableError",
    "fingerprint_dataset",
    "map_passport_to_step",
    "preflight_mapped_step",
    "validate_passport_bound_preparation",
]


def __getattr__(name: str):
    if name in {"PreflightResult", "StepInputIssue", "preflight_mapped_step"}:
        from modori.research_flow.preflight import (
            PreflightResult,
            preflight_mapped_step,
        )
        from modori.steps.input_validation import StepInputIssue

        lazy_exports = {
            "PreflightResult": PreflightResult,
            "StepInputIssue": StepInputIssue,
            "preflight_mapped_step": preflight_mapped_step,
        }
        globals().update(lazy_exports)
        return lazy_exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
