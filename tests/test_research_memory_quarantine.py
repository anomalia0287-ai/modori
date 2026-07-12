from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import json
from pathlib import Path
import unicodedata

from modori.research_memory.canonical import (
    artifact_id,
    canonical_bytes,
    canonical_digest,
)
from modori.research_memory.evidence_bundle import EvidenceBundle
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerEvent,
    LedgerEventKind,
    LedgerHead,
)
from modori.research_memory.quarantine import (
    EvidenceBundleQuarantine,
    QuarantineDisposition,
    QuarantineReasonCode,
    QuarantineStage,
)
from modori.research_os import MissingCodeMeaning, ResearchOsService, SchemaEnvelope
from tests.test_research_memory_evidence_bundle import _two_event_bundle
from tests.test_research_memory_ledger_contracts import _request
from tests.test_research_memory_ledger_store import _genesis_commit


def _raw_bundle(request=None) -> bytes:
    commit = _genesis_commit(request or _request())
    return EvidenceBundle.create(
        source_project_id="project-1",
        head=LedgerHead(
            sequence=commit.events[-1].sequence,
            event_hash=commit.events[-1].event_hash,
        ),
        artifacts=commit.artifacts,
        events=commit.events,
        exported_at_utc=None,
    ).to_bytes()


def _passport_bundle(*, stale: bool, stale_version: str = "stale_v0") -> bytes:
    request = _request()
    passport = ResearchOsService().plan(
        request,
        SchemaEnvelope(
            schema_id="modori.analysis_passport",
            schema_version=1,
            project_id="project-1",
            object_id="passport-1",
            revision=1,
            supersedes_revision=None,
            created_event_ref="event:passport:1",
        ),
    )
    if stale:
        passport = replace(passport, method_space_version=stale_version)
    passport_artifact = LedgerArtifact.from_value(passport)
    base = EvidenceBundle.from_bytes(_raw_bundle())
    artifacts = tuple(
        sorted((*base.artifacts, passport_artifact), key=lambda item: item.artifact_id)
    )
    original = base.events[0]
    event = LedgerEvent.create(
        project_id=original.project_id,
        event_id=original.event_id,
        sequence=original.sequence,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(item.artifact_id for item in artifacts),
        payload=original.payload,
        previous_event_hash=original.previous_event_hash,
        recorded_at_utc=original.recorded_at_utc,
    )
    return EvidenceBundle.create(
        source_project_id=base.source_project_id,
        head=LedgerHead(sequence=1, event_hash=event.event_hash),
        artifacts=artifacts,
        events=(event,),
        exported_at_utc=None,
    ).to_bytes()


def _validly_hashed_unresolved_subject_raw() -> bytes:
    base = EvidenceBundle.from_bytes(_raw_bundle())
    original = base.events[0]
    snapshot_id = original.payload["resulting_snapshot_artifact_id"]
    forged = LedgerEvent.create(
        project_id=original.project_id,
        event_id=original.event_id,
        sequence=1,
        event_kind=LedgerEventKind.PROJECT_CREATED,
        subject_artifact_ids=tuple(
            sorted((*original.subject_artifact_ids, "f" * 64))
        ),
        payload={"resulting_snapshot_artifact_id": snapshot_id},
        previous_event_hash=original.previous_event_hash,
        recorded_at_utc=None,
    )
    payload = json.loads(base.to_bytes())
    payload["events"] = [forged.to_mapping()]
    payload["head"] = {
        "sequence": forged.sequence,
        "event_hash": forged.event_hash,
    }
    return canonical_bytes(payload)


def _sensitive_question_raw(text: str) -> bytes:
    payload = json.loads(_raw_bundle())
    index = next(
        position
        for position, item in enumerate(payload["artifacts"])
        if item["artifact_kind"] == "question_spec"
    )
    sensitive = replace(_request().question, local_text=text)
    body = sensitive.to_mapping()
    body_bytes = canonical_bytes(body)
    replacement = dict(payload["artifacts"][index])
    replacement["body"] = body
    replacement["semantic_digest"] = sensitive.digest()
    replacement["storage_digest"] = canonical_digest(body)
    replacement["artifact_id"] = artifact_id("question_spec", body_bytes)
    payload["artifacts"][index] = replacement
    payload["artifacts"].sort(key=lambda item: item["artifact_id"])
    return canonical_bytes(payload)


def test_foreign_user_confirmation_becomes_external_assertion_only() -> None:
    result = EvidenceBundleQuarantine.inspect(
        _raw_bundle(),
        local_dataset_fingerprint="a" * 64,
    )
    assert result.stage is QuarantineStage.ASSERTION_READY
    assert result.disposition is QuarantineDisposition.ACCEPT_AS_ASSERTIONS
    assertion = next(
        item
        for item in result.imported_assertions
        if item.fact_address == "study.dependence_structure"
    )
    assert assertion.foreign_fact_state == "user_confirmed"
    assert assertion.project_id == "project-1"
    assert not hasattr(assertion, "local_fact")
    assert not hasattr(result, "research_request")
    assert not hasattr(result, "pipeline")


def test_extraction_covers_closed_c1_addresses_without_importing_authority() -> None:
    result = EvidenceBundleQuarantine.inspect(
        _raw_bundle(),
        local_dataset_fingerprint="a" * 64,
    )
    addresses = tuple(item.fact_address for item in result.imported_assertions)
    assert addresses == tuple(sorted(addresses))
    assert {
        "question.research_goal",
        "question.causal_intent",
        "estimand.template",
        "study.design_family",
        "study.dependence_structure",
    } <= set(addresses)
    assert len(addresses) == len(set(addresses))
    assert all(item.source_bundle_digest == result.source_bundle_digest for item in result.imported_assertions)


def test_dataset_mismatch_is_held_without_partial_assertions() -> None:
    result = EvidenceBundleQuarantine.inspect(
        _raw_bundle(),
        local_dataset_fingerprint="d" * 64,
    )
    assert result.stage is QuarantineStage.HELD
    assert result.disposition is QuarantineDisposition.HELD
    assert result.imported_assertions == ()
    assert result.findings[0].reason_code is QuarantineReasonCode.DATASET_MISMATCH


def test_invalid_bytes_are_rejected_without_partially_decoded_bundle() -> None:
    result = EvidenceBundleQuarantine.inspect(
        b"not-json",
        local_dataset_fingerprint="a" * 64,
    )
    assert result.stage is QuarantineStage.REJECTED
    assert result.disposition is QuarantineDisposition.REJECTED
    assert result.imported_assertions == ()
    assert result.source_project_id is None
    assert result.findings


def test_internally_inconsistent_source_dataset_is_rejected_not_held() -> None:
    request = _request()
    inconsistent = replace(
        request,
        study=replace(request.study, dataset_fingerprint="c" * 64),
    )
    result = EvidenceBundleQuarantine.inspect(
        _raw_bundle(inconsistent),
        local_dataset_fingerprint="a" * 64,
    )
    assert result.stage is QuarantineStage.REJECTED
    assert result.findings[0].reason_code is QuarantineReasonCode.SOURCE_INTEGRITY


def test_current_passport_is_ignored_as_authority_but_stale_catalog_is_rejected() -> None:
    current = EvidenceBundleQuarantine.inspect(
        _passport_bundle(stale=False),
        local_dataset_fingerprint="a" * 64,
    )
    assert current.stage is QuarantineStage.ASSERTION_READY
    stale = EvidenceBundleQuarantine.inspect(
        _passport_bundle(stale=True),
        local_dataset_fingerprint="a" * 64,
    )
    assert stale.stage is QuarantineStage.REJECTED
    assert stale.findings[0].reason_code is QuarantineReasonCode.STALE_CATALOG


def test_legitimate_missing_value_code_is_not_mistaken_for_execution_code() -> None:
    request = _request()
    request = replace(
        request,
        study=replace(
            request.study,
            missing_code_meanings=(
                MissingCodeMeaning(
                    variable_id="score",
                    code="999",
                    meaning="declared missing value",
                ),
            ),
        ),
    )
    result = EvidenceBundleQuarantine.inspect(
        _raw_bundle(request),
        local_dataset_fingerprint="a" * 64,
    )
    assert result.stage is QuarantineStage.ASSERTION_READY


@dataclass(frozen=True)
class _Mutation:
    name: str
    raw: bytes
    local_fingerprint: str
    expected_stage: QuarantineStage
    expected_reason: QuarantineReasonCode


def _mutation_corpus() -> tuple[_Mutation, ...]:
    raw = _raw_bundle()
    mutations: list[_Mutation] = []
    local_fingerprint = "a" * 64

    def add(
        family: str,
        index: int,
        mutated: bytes,
        reason: QuarantineReasonCode,
        *,
        stage: QuarantineStage = QuarantineStage.REJECTED,
        fingerprint: str = local_fingerprint,
    ) -> None:
        mutations.append(
            _Mutation(
                f"{family}_{index:02d}",
                mutated,
                fingerprint,
                stage,
                reason,
            )
        )

    def mapping(source: bytes = raw) -> dict[str, object]:
        return json.loads(source)

    def artifact(payload: dict[str, object], kind: str) -> dict[str, object]:
        return next(
            item for item in payload["artifacts"] if item["artifact_kind"] == kind
        )

    resource_payloads = (
        (
            b"x" * (16 * 1024 * 1024 + 1),
            QuarantineReasonCode.BYTE_LIMIT,
        ),
        (
            canonical_bytes({"value": "x" * 513}),
            QuarantineReasonCode.RESOURCE_LIMIT,
        ),
        (
            canonical_bytes(mapping() | {"events": [None] * 10_001}),
            QuarantineReasonCode.RESOURCE_LIMIT,
        ),
        (
            canonical_bytes(mapping() | {"artifacts": [None] * 30_001}),
            QuarantineReasonCode.RESOURCE_LIMIT,
        ),
        (
            canonical_bytes([None] * 2_000_001),
            QuarantineReasonCode.RESOURCE_LIMIT,
        ),
        (
            b"[" * 9 + raw + b"]" * 9,
            QuarantineReasonCode.NESTING_LIMIT,
        ),
    )
    for index in range(30):
        mutated, reason = resource_payloads[index % len(resource_payloads)]
        add("resource", index, mutated, reason)

    nfc = "조사 대상 표본"
    encoding_payloads: list[tuple[bytes, QuarantineReasonCode]] = []
    for index in range(30):
        variant = index % 6
        if variant == 0:
            item = b"\xff" + raw
            reason = QuarantineReasonCode.INVALID_UTF8
        elif variant == 1:
            item = b"\xef\xbb\xbf" + raw
            reason = QuarantineReasonCode.INVALID_UTF8
        elif variant == 2:
            item = (
                b'{"schema_id":"duplicate_' + str(index).encode() + b'",' + raw[1:]
            )
            reason = QuarantineReasonCode.DUPLICATE_KEY
        elif variant == 3:
            nfd = unicodedata.normalize("NFD", nfc) + str(index)
            item = raw.replace(nfc.encode(), nfd.encode(), 1)
            reason = QuarantineReasonCode.NONCANONICAL
        elif variant == 4:
            item = raw.replace(b"project-1", b"\\ud800" + str(index).encode(), 1)
            reason = QuarantineReasonCode.NONCANONICAL
        else:
            item = raw + f"/*polyglot_{index}*/".encode()
            reason = QuarantineReasonCode.INVALID_JSON
        encoding_payloads.append((item, reason))
    for index, (mutated, reason) in enumerate(encoding_payloads):
        add("encoding", index, mutated, reason)

    for index in range(30):
        payload = mapping()
        variant = index % 10
        if variant == 0:
            payload["schema_id"] = f"modori.unknown_{index}"
            reason = QuarantineReasonCode.SCHEMA_INVALID
        elif variant == 1:
            payload["schema_version"] = index + 2
            reason = QuarantineReasonCode.SCHEMA_INVALID
        elif variant == 2:
            payload["canonicalization_id"] = f"unknown_{index}"
            reason = QuarantineReasonCode.SCHEMA_INVALID
        elif variant == 3:
            payload["hash_algorithm"] = f"sha-{index}"
            reason = QuarantineReasonCode.SCHEMA_INVALID
        elif variant == 4:
            payload[f"unknown_{index}"] = None
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        elif variant == 5:
            payload["artifacts"][0]["artifact_kind"] = f"unknown_{index}"
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 6:
            payload["events"][0]["body"]["event_kind"] = f"unknown_{index}"
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 7:
            artifact(payload, "question_spec")["body"]["capture_mode"] = (
                f"unknown_{index}"
            )
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 8:
            artifact(payload, "study_spec")["body"][f"unknown_{index}"] = None
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        else:
            payload["events"][0]["body"][f"unknown_{index}"] = None
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        add("schema", index, canonical_bytes(payload), reason)

    for index in range(30):
        payload = mapping()
        digest = f"{index + 1:064x}"
        variant = index % 10
        if variant == 0:
            payload["head"]["event_hash"] = digest
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 1:
            payload["events"][0]["event_hash"] = digest
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 2:
            payload["events"][0]["body_digest"] = digest
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 3:
            payload["events"][0]["previous_event_hash"] = digest
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 4:
            payload["artifacts"][0]["artifact_id"] = digest
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 5:
            payload["artifacts"][0]["storage_digest"] = digest
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 6:
            payload["artifacts"][0]["semantic_digest"] = digest
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 7:
            payload["events"][0]["body"]["payload"][
                "resulting_snapshot_artifact_id"
            ] = digest
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 8:
            payload["events"][0]["body"]["project_id"] = f"foreign-{index}"
            reason = QuarantineReasonCode.CHAIN_INVALID
        else:
            payload["events"][0]["body"]["recorded_at_utc"] = "not-utc"
            reason = QuarantineReasonCode.CHAIN_INVALID
        add("hash", index, canonical_bytes(payload), reason)

    two_event_raw = _two_event_bundle().to_bytes()
    for index in range(30):
        payload = mapping(two_event_raw)
        variant = index % 6
        if variant == 0:
            payload["events"][1]["body"]["sequence"] = 3 + index
        elif variant == 1:
            payload["events"].append(payload["events"][1])
        elif variant == 2:
            payload["events"] = list(reversed(payload["events"]))
        elif variant == 3:
            payload["events"][1]["previous_event_hash"] = f"{index + 1:064x}"
        elif variant == 4:
            payload["events"].pop()
        else:
            payload["source_project_id"] = f"foreign-{index}"
        add(
            "chain",
            index,
            canonical_bytes(payload),
            QuarantineReasonCode.CHAIN_INVALID,
        )

    unresolved_raw = _validly_hashed_unresolved_subject_raw()
    for index in range(30):
        payload = mapping()
        variant = index % 10
        if variant in {0, 8}:
            payload["artifacts"].pop(0)
            reason = QuarantineReasonCode.CHAIN_INVALID
            mutated = canonical_bytes(payload)
        elif variant in {1, 9}:
            payload["artifacts"].insert(1, payload["artifacts"][0])
            reason = QuarantineReasonCode.ARTIFACT_INVALID
            mutated = canonical_bytes(payload)
        elif variant == 2:
            reason = QuarantineReasonCode.CHAIN_INVALID
            mutated = unresolved_raw
        elif variant == 3:
            subjects = payload["events"][0]["body"]["subject_digests"]
            subjects.append(subjects[0])
            reason = QuarantineReasonCode.CHAIN_INVALID
            mutated = canonical_bytes(payload)
        elif variant in {4, 6, 7}:
            snapshot = artifact(payload, "request_snapshot")
            if variant == 4:
                snapshot["body"]["question_artifact_id"] = snapshot["artifact_id"]
            elif variant == 6:
                snapshot["body"]["decision_evidence_artifact_ids"] = [
                    snapshot["artifact_id"]
                ]
            else:
                snapshot["body"]["study_artifact_id"] = f"{index + 1:064x}"
            reason = QuarantineReasonCode.ARTIFACT_INVALID
            mutated = canonical_bytes(payload)
        else:
            selected = payload["artifacts"][0]
            if variant == 5:
                selected["project_id"] = f"foreign-{index}"
            else:
                selected["schema_id"] = f"modori.wrong_{index}"
            reason = QuarantineReasonCode.ARTIFACT_INVALID
            mutated = canonical_bytes(payload)
        add("reference", index, mutated, reason)

    current_passport_raw = _passport_bundle(stale=False)
    for index in range(30):
        payload = mapping(current_passport_raw if index % 10 in {2, 3, 9} else raw)
        variant = index % 10
        if variant == 0:
            fact = artifact(payload, "question_spec")["body"]["research_goal"]
            fact.update(
                {
                    "state": "user_confirmed",
                    "value": "describe",
                    "provenance_refs": [],
                }
            )
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 1:
            fact = artifact(payload, "study_spec")["body"][
                "dependence_structure"
            ]
            fact.update(
                {
                    "state": "user_confirmed",
                    "value": "independent",
                    "provenance_refs": [],
                }
            )
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 2:
            artifact(payload, "analysis_passport")["body"][
                "method_space_digest"
            ] = f"{index + 1:064x}"
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 3:
            artifact(payload, "analysis_passport")["semantic_digest"] = (
                f"{index + 1:064x}"
            )
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        elif variant == 4:
            payload["source_project_id"] = f"forged-{index}"
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 5:
            payload["events"][0]["body"]["event_id"] = f"forged:event:{index}"
            reason = QuarantineReasonCode.CHAIN_INVALID
        elif variant == 6:
            payload["route_external"] = {"route_id": "forged"}
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        elif variant == 7:
            payload["source_signature"] = f"self-{index}"
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        elif variant == 8:
            payload["user_confirmed"] = True
            reason = QuarantineReasonCode.UNKNOWN_FIELD
        else:
            artifact(payload, "analysis_passport")["body"]["route_external"] = {}
            reason = QuarantineReasonCode.ARTIFACT_INVALID
        add("forgery", index, canonical_bytes(payload), reason)

    forbidden_keys = (
        "path",
        "file_path",
        "filesystem_path",
        "url",
        "uri",
        "command",
        "script",
        "executable",
        "pipeline",
        "tool_call",
        "tool",
        "worker",
        "persistence",
        "execution",
        "execution_token",
        "plugin",
        "plugin_call",
        "callback",
        "endpoint",
        "host",
        "sql",
        "query",
        "shell",
        "process",
        "thread",
        "browser",
        "file",
        "write_path",
        "read_path",
        "network",
    )
    for index, key in enumerate(forbidden_keys):
        payload = mapping()
        payload[key] = f"attempt-{index}"
        add(
            "authority",
            index,
            canonical_bytes(payload),
            QuarantineReasonCode.FORBIDDEN_KEY,
        )

    stale_payloads = tuple(
        _passport_bundle(stale=True, stale_version=f"stale_v{index}")
        for index in range(15)
    )
    for index in range(30):
        if index < 15:
            add(
                "freshness",
                index,
                raw,
                QuarantineReasonCode.DATASET_MISMATCH,
                stage=QuarantineStage.HELD,
                fingerprint=f"{index + 1:064x}",
            )
        else:
            add(
                "freshness",
                index,
                stale_payloads[index - 15],
                QuarantineReasonCode.STALE_CATALOG,
            )

    for index in range(30):
        variant = index % 10
        if variant == 0:
            mutated = b"SQLite format 3\x00" + str(index).encode()
            reason = QuarantineReasonCode.FORBIDDEN_FORMAT
        elif variant == 1:
            mutated = b"PK\x03\x04" + str(index).encode()
            reason = QuarantineReasonCode.FORBIDDEN_FORMAT
        elif variant in {2, 9}:
            mutated = _sensitive_question_raw(f"<script>{index}</script>")
            reason = QuarantineReasonCode.UNSUPPORTED_SENSITIVE_PAYLOAD
        elif variant == 3:
            mutated = raw + raw
            reason = QuarantineReasonCode.INVALID_JSON
        elif variant == 4:
            mutated = raw + b"\x00"
            reason = QuarantineReasonCode.INVALID_JSON
        elif variant == 5:
            mutated = f"/*comment-{index}*/".encode() + raw
            reason = QuarantineReasonCode.INVALID_JSON
        elif variant == 6:
            mutated = raw[:-1] + b",}"
            reason = QuarantineReasonCode.INVALID_JSON
        elif variant == 7:
            mutated = b"\xef\xbb\xbf" + raw
            reason = QuarantineReasonCode.INVALID_UTF8
        else:
            mutated = b"PK\x05\x06" + str(index).encode()
            reason = QuarantineReasonCode.FORBIDDEN_FORMAT
        add("polyglot", index, mutated, reason)

    family_counts: dict[str, int] = {}
    for mutation in mutations:
        family = mutation.name.rsplit("_", 1)[0]
        family_counts[family] = family_counts.get(family, 0) + 1
    assert set(family_counts.values()) == {30}
    assert len(family_counts) == 10
    assert len(mutations) == 300
    return tuple(mutations)


def test_300_deterministic_mutations_are_rejected_or_held_as_declared() -> None:
    observed: dict[str, tuple[QuarantineStage, QuarantineReasonCode]] = {}
    for mutation in _mutation_corpus():
        result = EvidenceBundleQuarantine.inspect(
            mutation.raw,
            local_dataset_fingerprint=mutation.local_fingerprint,
        )
        observed[mutation.name] = (
            result.stage,
            result.findings[0].reason_code,
        )
        assert result.stage is mutation.expected_stage, mutation.name
        assert result.findings[0].reason_code is mutation.expected_reason, mutation.name
        assert result.imported_assertions == ()
    assert len(observed) == 300


def test_quarantine_module_has_no_io_archive_execution_or_calculation_imports() -> None:
    source_path = Path("src/modori/research_memory/quarantine.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
    assert imported_roots.isdisjoint(
        {
            "sqlite3",
            "zipfile",
            "tarfile",
            "pickle",
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "PySide6",
            "modori.steps",
            "modori.workflow",
        }
    )
    assert called_names.isdisjoint(
        {"open", "read_text", "read_bytes", "write_text", "write_bytes", "unlink"}
    )
