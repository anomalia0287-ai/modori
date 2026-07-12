from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import json
from pathlib import Path

from modori.research_memory.canonical import canonical_bytes
from modori.research_memory.evidence_bundle import EvidenceBundle
from modori.research_memory.ledger_contracts import LedgerHead
from modori.research_memory.quarantine import (
    EvidenceBundleQuarantine,
    QuarantineDisposition,
    QuarantineReasonCode,
    QuarantineStage,
)
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


@dataclass(frozen=True)
class _Mutation:
    name: str
    raw: bytes
    local_fingerprint: str
    expected_stage: QuarantineStage
    expected_reason: QuarantineReasonCode


def _mutation_corpus() -> tuple[_Mutation, ...]:
    raw = _raw_bundle()
    base = json.loads(raw)
    mutations: list[_Mutation] = []
    for index in range(30):
        mutations.append(
            _Mutation(
                f"bom_{index:02d}",
                b"\xef\xbb\xbf" + raw + b" " * index,
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.INVALID_UTF8,
            )
        )
        mutations.append(
            _Mutation(
                f"duplicate_{index:02d}",
                b'{"schema_id":"duplicate_' + str(index).encode() + b'",' + raw[1:],
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.DUPLICATE_KEY,
            )
        )
        unknown = json.loads(raw)
        unknown[f"attack_{index:02d}"] = None
        mutations.append(
            _Mutation(
                f"unknown_{index:02d}",
                canonical_bytes(unknown),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.UNKNOWN_FIELD,
            )
        )
        forbidden = json.loads(raw)
        forbidden["command"] = f"attempt_{index:02d}"
        mutations.append(
            _Mutation(
                f"command_{index:02d}",
                canonical_bytes(forbidden),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.FORBIDDEN_KEY,
            )
        )
        mutations.append(
            _Mutation(
                f"float_{index:02d}",
                f'{{"value":{index}.5}}'.encode(),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.INVALID_NUMBER,
            )
        )
        mutations.append(
            _Mutation(
                f"depth_{index:02d}",
                b"[" * 9 + raw + b"]" * 9 + b" " * index,
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.NESTING_LIMIT,
            )
        )
        bad_head = json.loads(raw)
        bad_head["head"]["event_hash"] = f"{index + 1:064x}"
        mutations.append(
            _Mutation(
                f"head_{index:02d}",
                canonical_bytes(bad_head),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.CHAIN_INVALID,
            )
        )
        bad_artifact = json.loads(raw)
        bad_artifact["artifacts"][0]["storage_digest"] = f"{index + 1:064x}"
        mutations.append(
            _Mutation(
                f"artifact_{index:02d}",
                canonical_bytes(bad_artifact),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.ARTIFACT_INVALID,
            )
        )
        mutations.append(
            _Mutation(
                f"whitespace_{index:02d}",
                raw.replace(b"{", b"{" + b" " * (index + 1), 1),
                "a" * 64,
                QuarantineStage.REJECTED,
                QuarantineReasonCode.NONCANONICAL,
            )
        )
        mutations.append(
            _Mutation(
                f"dataset_{index:02d}",
                raw,
                f"{index + 1:064x}",
                QuarantineStage.HELD,
                QuarantineReasonCode.DATASET_MISMATCH,
            )
        )
    assert base["schema_id"] == "modori.evidence_bundle"
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
