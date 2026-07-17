from __future__ import annotations

import ast
from pathlib import Path

import pytest

import modori.research_memory as research_memory
from modori.research_memory.ledger_contracts import LedgerEvent, LedgerEventKind
from modori.research_memory.passport_state import (
    PassportHistory,
    PassportStateError,
)
from tests.research_memory_passport_fixtures import (
    forged_v2_answer_history,
    forged_passport_history,
    history_with_legacy_v1_answer,
    history_with_passport_commit,
    history_with_retraction,
    history_with_v2_answer,
)


def test_passport_commit_is_outstanding_only_after_exact_unchanged_snapshot() -> None:
    events, artifacts, request, passport = history_with_passport_commit()

    history = PassportHistory.inspect(events, artifacts)
    assert passport.clarification_registry_digest is not None
    records = history.outstanding_for(
        project_id="project-1",
        request_binding_digest=request.request_binding_digest(),
        clarification_registry_digest=passport.clarification_registry_digest,
    )

    assert len(records) == 1
    assert records[0].passport == passport
    assert records[0].commit_event_id == passport.envelope.created_event_ref


def test_v2_record_key_rejects_missing_binding_digest() -> None:
    events, artifacts, _request, _passport = history_with_passport_commit()
    record = PassportHistory.inspect(events, artifacts).records[0]
    object.__setattr__(record.passport, "request_binding_digest", None)

    with pytest.raises(PassportStateError, match="binding digests"):
        _ = record.key


@pytest.mark.parametrize(
    "forgery",
    (
        "wrong_created_event_ref",
        "changed_resulting_snapshot",
        "missing_snapshot_subject",
        "extra_subject",
        "request_binding_splice",
        "second_outstanding_same_key",
    ),
)
def test_passport_history_rejects_commit_forgery(forgery: str) -> None:
    events, artifacts = forged_passport_history(forgery)

    with pytest.raises(PassportStateError):
        PassportHistory.inspect(events, artifacts)


def test_v2_answer_without_a_prior_commit_is_rejected() -> None:
    events, artifacts, _request, _passport = history_with_v2_answer(
        include_commit=False
    )

    with pytest.raises(PassportStateError, match="prior outstanding commit"):
        PassportHistory.inspect(events, artifacts)


def test_historical_v1_answer_without_a_commit_remains_replayable() -> None:
    events, artifacts = history_with_legacy_v1_answer()

    history = PassportHistory.inspect(events, artifacts)

    assert history.records == ()


def test_valid_v2_answer_consumes_the_exact_committed_passport() -> None:
    events, artifacts, request, passport = history_with_v2_answer(
        include_commit=True
    )

    history = PassportHistory.inspect(events, artifacts)

    assert len(history.records) == 1
    assert history.records[0].consumed_by_event_id == events[-1].event_id
    assert passport.clarification_registry_digest is not None
    assert history.outstanding_for(
        project_id="project-1",
        request_binding_digest=request.request_binding_digest(),
        clarification_registry_digest=passport.clarification_registry_digest,
    ) == ()


@pytest.mark.parametrize(
    "forgery",
    ("missing_passport_subject", "extra_historical_snapshot_subject"),
)
def test_v2_answer_rejects_nonexact_subject_closure(forgery: str) -> None:
    events, artifacts = forged_v2_answer_history(forgery)

    with pytest.raises(PassportStateError):
        PassportHistory.inspect(events, artifacts)


def test_decision_retraction_makes_a_committed_passport_not_outstanding() -> None:
    events, artifacts = history_with_retraction()

    history = PassportHistory.inspect(events, artifacts)

    assert len(history.records) == 1
    assert history.records[0].retracted_by_event_id == events[-1].event_id
    assert history.records[0].outstanding is False


def test_retraction_fold_is_deterministic_and_rejects_a_second_retraction() -> None:
    events, artifacts = history_with_retraction()

    assert PassportHistory.inspect(events, artifacts) == PassportHistory.inspect(
        events,
        artifacts,
    )
    first_retraction = events[-1]
    duplicate = LedgerEvent.create(
        project_id=first_retraction.project_id,
        event_id="event:retract:duplicate:4",
        sequence=first_retraction.sequence + 1,
        event_kind=LedgerEventKind.DECISION_RETRACTED,
        subject_artifact_ids=first_retraction.subject_artifact_ids,
        payload={
            "retracted_event_id": first_retraction.payload["retracted_event_id"],
            "reason_code": "user_retracted",
            "resulting_snapshot_artifact_id": first_retraction.payload[
                "resulting_snapshot_artifact_id"
            ],
        },
        previous_event_hash=first_retraction.event_hash,
        recorded_at_utc=None,
    )

    with pytest.raises(PassportStateError, match="ambiguous"):
        PassportHistory.inspect((*events, duplicate), artifacts)


def test_passport_history_rejects_duplicate_artifact_identities() -> None:
    events, artifacts, _request, _passport = history_with_passport_commit()

    with pytest.raises(PassportStateError, match="duplicate artifact ID"):
        PassportHistory.inspect(events, (*artifacts, artifacts[0]))


def test_passport_state_reducer_has_no_io_model_or_calculation_imports() -> None:
    path = Path("src/modori/research_memory/passport_state.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])

    assert roots.isdisjoint(
        {
            "PySide6",
            "httpx",
            "numpy",
            "pandas",
            "pathlib",
            "requests",
            "scipy",
            "sklearn",
            "socket",
            "sqlite3",
            "statsmodels",
            "subprocess",
            "urllib",
        }
    )


def test_passport_state_contract_is_exposed_from_memory_package() -> None:
    assert research_memory.PassportHistory is PassportHistory
    assert research_memory.PassportStateError is PassportStateError
