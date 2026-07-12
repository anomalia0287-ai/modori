from __future__ import annotations

from dataclasses import replace
import json

import pytest

import modori.research_memory.evidence_bundle as evidence_bundle
from modori.research_memory.canonical import canonical_bytes
from modori.research_memory.evidence_bundle import (
    EvidenceBundle,
    EvidenceBundleError,
    EvidenceBundleErrorCode,
    EvidenceBundleLimits,
    _event_wire_size,
)
from modori.research_memory.ledger_contracts import (
    LedgerArtifactKind,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
)
from tests.test_research_memory_ledger_contracts import _request
from tests.test_research_memory_ledger_store import _genesis_commit


def _bundle() -> EvidenceBundle:
    commit = _genesis_commit(_request(with_evidence=True))
    return EvidenceBundle.create(
        source_project_id="project-1",
        head=LedgerHead(
            sequence=commit.events[-1].sequence,
            event_hash=commit.events[-1].event_hash,
        ),
        artifacts=commit.artifacts,
        events=commit.events,
        exported_at_utc=None,
    )


def _mapping(bundle: EvidenceBundle | None = None) -> dict[str, object]:
    return json.loads((bundle or _bundle()).to_bytes())


def _two_event_bundle(*, forked: bool = False) -> EvidenceBundle:
    first = _bundle()
    snapshot = next(
        artifact
        for artifact in first.artifacts
        if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT
    )
    second = LedgerEvent.create(
        project_id="project-1",
        event_id="event:invalidation:2",
        sequence=2,
        event_kind=LedgerEventKind.FACT_INVALIDATED,
        subject_artifact_ids=(snapshot.artifact_id,),
        payload={
            "fact_address": "study.dependence_structure",
            "reason_code": "source_changed",
            "resulting_snapshot_artifact_id": snapshot.artifact_id,
        },
        previous_event_hash=("f" * 64 if forked else first.head.event_hash),
        recorded_at_utc=None,
    )
    if forked:
        payload = _mapping(first)
        payload["events"].append(second.to_mapping())
        payload["head"] = {
            "sequence": second.sequence,
            "event_hash": second.event_hash,
        }
        with pytest.raises(EvidenceBundleError) as caught:
            EvidenceBundle.from_bytes(canonical_bytes(payload))
        assert caught.value.code is EvidenceBundleErrorCode.INCOMPLETE_HISTORY
        return first
    return EvidenceBundle.create(
        source_project_id="project-1",
        head=LedgerHead(sequence=2, event_hash=second.event_hash),
        artifacts=first.artifacts,
        events=(*first.events, second),
        exported_at_utc=None,
    )


def _canonical_mutation(mutator) -> bytes:
    payload = _mapping()
    mutator(payload)
    return canonical_bytes(payload)


def test_bundle_roundtrip_is_deterministic_and_complete() -> None:
    bundle = _bundle()
    raw = bundle.to_bytes()
    restored = EvidenceBundle.from_bytes(raw)
    assert restored == bundle
    assert restored.to_bytes() == raw
    assert tuple(item.artifact_id for item in restored.artifacts) == tuple(
        sorted(item.artifact_id for item in restored.artifacts)
    )
    assert restored.verify() is None
    assert _event_wire_size(restored.events[0]) == len(
        canonical_bytes(restored.events[0].to_mapping())
    )


def test_bundle_depth_is_enforced_without_a_separate_raw_scan(monkeypatch) -> None:
    raw = _bundle().to_bytes()
    monkeypatch.setattr(
        evidence_bundle,
        "_scan_depth",
        lambda *_args: pytest.fail("separate raw depth scan was called"),
        raising=False,
    )
    assert EvidenceBundle.from_bytes(raw).to_bytes() == raw


def test_bundle_decoder_recursion_is_closed_as_nesting_limit() -> None:
    raw = b"[" * 2048 + b"0" + b"]" * 2048
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(raw)
    assert caught.value.code is EvidenceBundleErrorCode.NESTING_LIMIT


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda raw: b"\xef\xbb\xbf" + raw, EvidenceBundleErrorCode.INVALID_UTF8),
        (
            lambda raw: b'{"schema_id":"modori.evidence_bundle",' + raw[1:],
            EvidenceBundleErrorCode.DUPLICATE_KEY,
        ),
        (
            lambda _raw: _canonical_mutation(
                lambda payload: payload.update({"unknown": None})
            ),
            EvidenceBundleErrorCode.UNKNOWN_FIELD,
        ),
        (lambda raw: raw.replace(b"{", b"{ ", 1), EvidenceBundleErrorCode.NONCANONICAL),
        (
            lambda raw: b"[" * 9 + raw + b"]" * 9,
            EvidenceBundleErrorCode.NESTING_LIMIT,
        ),
    ],
)
def test_bundle_rejects_ambiguous_wire_forms(mutator, code) -> None:
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(mutator(_bundle().to_bytes()))
    assert caught.value.code is code


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"SQLite format 3\x00garbage", EvidenceBundleErrorCode.FORBIDDEN_FORMAT),
        (b"PK\x03\x04garbage", EvidenceBundleErrorCode.FORBIDDEN_FORMAT),
        (b'{"value":1.5}', EvidenceBundleErrorCode.INVALID_NUMBER),
        (b'{"path":"C:/secret"}', EvidenceBundleErrorCode.FORBIDDEN_KEY),
        (b'{"url":"https://example.test"}', EvidenceBundleErrorCode.FORBIDDEN_KEY),
        (b'{"command":"run"}', EvidenceBundleErrorCode.FORBIDDEN_KEY),
    ],
)
def test_bundle_rejects_non_evidence_attack_surfaces(raw: bytes, code) -> None:
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(raw)
    assert caught.value.code is code


def test_bundle_rejects_byte_and_count_limits_before_typed_use() -> None:
    raw = _bundle().to_bytes()
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(raw, limits=EvidenceBundleLimits(max_bytes=10))
    assert caught.value.code is EvidenceBundleErrorCode.BYTE_LIMIT
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(
            raw,
            limits=replace(EvidenceBundleLimits(), max_artifacts=1),
        )
    assert caught.value.code is EvidenceBundleErrorCode.RESOURCE_LIMIT
    bundle = _bundle()
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.create(
            source_project_id=bundle.source_project_id,
            head=bundle.head,
            artifacts=bundle.artifacts,
            events=bundle.events,
            exported_at_utc=None,
            limits=replace(EvidenceBundleLimits(), max_string_length=1),
        )
    assert caught.value.code is EvidenceBundleErrorCode.STRING_LIMIT


@pytest.mark.parametrize("mutation", ["gap", "duplicate", "bad_head", "truncated"])
def test_bundle_rejects_incomplete_or_forged_chains(mutation: str) -> None:
    payload = _mapping()
    events = payload["events"]
    assert isinstance(events, list)
    if mutation == "gap":
        events[0]["body"]["sequence"] = 2
    elif mutation == "duplicate":
        events.append(events[0])
    elif mutation == "bad_head":
        payload["head"]["event_hash"] = "f" * 64
    else:
        payload["head"]["sequence"] = 2
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(canonical_bytes(payload))
    assert caught.value.code in {
        EvidenceBundleErrorCode.CHAIN_INVALID,
        EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
    }


def test_bundle_rejects_reordered_history_and_validly_hashed_fork() -> None:
    bundle = _two_event_bundle()
    payload = _mapping(bundle)
    payload["events"] = list(reversed(payload["events"]))
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(canonical_bytes(payload))
    assert caught.value.code is EvidenceBundleErrorCode.INCOMPLETE_HISTORY
    _two_event_bundle(forked=True)


def test_bundle_rejects_validly_hashed_unresolved_subject() -> None:
    bundle = _bundle()
    original = bundle.events[0]
    snapshot_id = original.payload["resulting_snapshot_artifact_id"]
    forged = LedgerEvent.create(
        project_id=original.project_id,
        event_id=original.event_id,
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(sorted((snapshot_id, "f" * 64))),
        payload={"resulting_snapshot_artifact_id": snapshot_id},
        previous_event_hash=original.previous_event_hash,
        recorded_at_utc=None,
    )
    payload = _mapping()
    payload["events"] = [forged.to_mapping()]
    payload["head"] = {
        "sequence": forged.sequence,
        "event_hash": forged.event_hash,
    }
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(canonical_bytes(payload))
    assert caught.value.code is EvidenceBundleErrorCode.UNRESOLVED_SUBJECT


def test_bundle_rejects_artifact_metadata_or_body_forgery() -> None:
    for field, value in (
        ("storage_digest", "f" * 64),
        ("semantic_digest", "e" * 64),
        ("artifact_id", "d" * 64),
    ):
        payload = _mapping()
        payload["artifacts"][0][field] = value
        with pytest.raises(EvidenceBundleError) as caught:
            EvidenceBundle.from_bytes(canonical_bytes(payload))
        assert caught.value.code is EvidenceBundleErrorCode.ARTIFACT_INVALID


def test_bundle_rejects_sensitive_local_question_text() -> None:
    bundle = _bundle()
    artifacts = list(bundle.artifacts)
    question_index = next(
        index
        for index, artifact in enumerate(artifacts)
        if artifact.artifact_kind is LedgerArtifactKind.QUESTION_SPEC
    )
    question = artifacts[question_index].decode_value()
    sensitive = replace(question, local_text="민감한 원문")
    body = sensitive.to_mapping()
    artifact_mapping = artifacts[question_index].to_mapping()
    artifact_mapping["body"] = body
    artifact_mapping["semantic_digest"] = sensitive.digest()
    from modori.research_memory.canonical import artifact_id, canonical_digest

    body_bytes = canonical_bytes(body)
    artifact_mapping["storage_digest"] = canonical_digest(body)
    artifact_mapping["artifact_id"] = artifact_id("question_spec", body_bytes)
    payload = _mapping()
    payload["artifacts"][question_index] = artifact_mapping
    with pytest.raises(EvidenceBundleError) as caught:
        EvidenceBundle.from_bytes(canonical_bytes(payload))
    assert caught.value.code is EvidenceBundleErrorCode.UNSUPPORTED_SENSITIVE_PAYLOAD
