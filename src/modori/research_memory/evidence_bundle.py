"""Canonical, resource-bounded evidence exchange without file or execution authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from typing import Any, NoReturn

from modori.research_memory.canonical import (
    CANONICALIZATION_ID,
    HASH_ALGORITHM,
    ZERO_HASH,
    CanonicalizationError,
    canonical_bytes,
)
from modori.research_memory.ledger_contracts import (
    LedgerArtifact,
    LedgerArtifactKind,
    LedgerContractError,
    LedgerEvent,
    LedgerHead,
    ResearchRequestSnapshot,
)


class EvidenceBundleErrorCode(str, Enum):
    BYTE_LIMIT = "byte_limit"
    FORBIDDEN_FORMAT = "forbidden_format"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_JSON = "invalid_json"
    DUPLICATE_KEY = "duplicate_key"
    INVALID_NUMBER = "invalid_number"
    NESTING_LIMIT = "nesting_limit"
    STRING_LIMIT = "string_limit"
    ITEM_LIMIT = "item_limit"
    RESOURCE_LIMIT = "resource_limit"
    FORBIDDEN_KEY = "forbidden_key"
    UNKNOWN_FIELD = "unknown_field"
    NONCANONICAL = "noncanonical"
    SCHEMA_INVALID = "schema_invalid"
    ARTIFACT_INVALID = "artifact_invalid"
    CHAIN_INVALID = "chain_invalid"
    PROJECT_MISMATCH = "project_mismatch"
    UNRESOLVED_SUBJECT = "unresolved_subject"
    INCOMPLETE_HISTORY = "incomplete_history"
    UNSUPPORTED_SENSITIVE_PAYLOAD = "unsupported_sensitive_payload"


class EvidenceBundleError(ValueError):
    """A closed, non-content-bearing evidence import failure."""

    def __init__(self, code: EvidenceBundleErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class EvidenceBundleLimits:
    max_bytes: int = 16 * 1024 * 1024
    max_events: int = 10_000
    max_artifacts: int = 30_000
    max_depth: int = 8
    max_event_bytes: int = 8 * 1024
    max_artifact_bytes: int = 128 * 1024
    max_string_length: int = 512
    max_collection_items: int = 10_000
    max_preparse_container_items: int = 30_000
    max_items: int = 1_000_000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")


_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "canonicalization_id",
        "hash_algorithm",
        "source_project_id",
        "exported_at_utc",
        "head",
        "artifacts",
        "events",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
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
        "socket",
    }
)
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_EVENT_WIRE_OVERHEAD = len(
    canonical_bytes(
        {
            "body": {},
            "body_digest": "0" * 64,
            "previous_event_hash": "0" * 64,
            "event_hash": "0" * 64,
        }
    )
) - len(b"{}")


def _event_wire_size(event: LedgerEvent) -> int:
    """Return exact canonical wire bytes without reparsing the verified body."""

    return len(event.canonical_body) + _EVENT_WIRE_OVERHEAD


def _raise(code: EvidenceBundleErrorCode, message: str) -> NoReturn:
    raise EvidenceBundleError(code, message)


class _DuplicateKey(ValueError):
    pass


class _InvalidNumber(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _parse_integer(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise _InvalidNumber(
            "integer cannot be decoded within its resource limit"
        ) from exc
    if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
        raise _InvalidNumber("integer outside safe range")
    return value


def _reject_number(_raw: str) -> NoReturn:
    raise _InvalidNumber("floats and constants are excluded")


def _scan_json_structure(raw: bytes, limits: EvidenceBundleLimits) -> None:
    stack: list[list[int]] = []
    total_items = 1
    index = 0
    while index < len(raw):
        character = raw[index]
        if character == 34:
            if stack:
                stack[-1][2] = 1
            search = index + 1
            while True:
                closing = raw.find(b'"', search)
                if closing < 0:
                    return
                slash = closing - 1
                while slash > index and raw[slash] == 92:
                    slash -= 1
                if (closing - 1 - slash) % 2 == 0:
                    index = closing + 1
                    break
                search = closing + 1
            continue
        if character in (91, 123):
            if stack:
                stack[-1][2] = 1
            stack.append([character, 0, 0])
            if len(stack) > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
        elif character == 44 and stack:
            frame = stack[-1]
            frame[1] += 1
            container_limit = (
                limits.max_collection_items
                if frame[0] == 123
                else limits.max_preparse_container_items
            )
            if frame[1] + 1 > container_limit:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle contains an oversized container",
                )
            total_items += 2 if frame[0] == 123 else 1
            if total_items > limits.max_items:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle exceeds its total item limit",
                )
        elif character in (93, 125) and stack:
            kind, commas, has_content = stack.pop()
            if has_content:
                container_limit = (
                    limits.max_collection_items
                    if kind == 123
                    else limits.max_preparse_container_items
                )
                if commas + 1 > container_limit:
                    _raise(
                        EvidenceBundleErrorCode.ITEM_LIMIT,
                        "evidence bundle contains an oversized container",
                    )
                total_items += 2 if kind == 123 else 1
                if total_items > limits.max_items:
                    _raise(
                        EvidenceBundleErrorCode.ITEM_LIMIT,
                        "evidence bundle exceeds its total item limit",
                    )
        elif character not in (9, 10, 13, 32) and stack:
            stack[-1][2] = 1
        index += 1


def _walk_resources(
    value: object,
    *,
    limits: EvidenceBundleLimits,
) -> None:
    items = 0
    stack = [(value, 1, limits.max_collection_items)]
    while stack:
        current, depth, collection_limit = stack.pop()
        items += 1
        if items > limits.max_items:
            _raise(
                EvidenceBundleErrorCode.ITEM_LIMIT,
                "evidence bundle exceeds its total item limit",
            )
        if isinstance(current, str):
            if len(current) > limits.max_string_length:
                _raise(
                    EvidenceBundleErrorCode.STRING_LIMIT,
                    "evidence bundle contains an oversized string",
                )
        elif isinstance(current, Mapping):
            if depth > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
            if len(current) > limits.max_collection_items:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle contains an oversized mapping",
                )
            for key, item in current.items():
                if key in _FORBIDDEN_KEYS:
                    _raise(
                        EvidenceBundleErrorCode.FORBIDDEN_KEY,
                        "evidence bundle contains a forbidden authority-bearing key",
                    )
                child_limit = limits.max_collection_items
                if depth == 1 and key in {"artifacts", "events"}:
                    child_limit = limits.max_preparse_container_items
                stack.append((key, depth + 1, limits.max_collection_items))
                stack.append((item, depth + 1, child_limit))
        elif isinstance(current, list):
            if depth > limits.max_depth:
                _raise(
                    EvidenceBundleErrorCode.NESTING_LIMIT,
                    "evidence bundle exceeds its nesting limit",
                )
            if len(current) > collection_limit:
                _raise(
                    EvidenceBundleErrorCode.ITEM_LIMIT,
                    "evidence bundle contains an oversized list",
                )
            stack.extend(
                (item, depth + 1, limits.max_collection_items) for item in current
            )


def _require_exact_top_level(payload: Mapping[str, Any]) -> None:
    unknown = sorted(set(payload) - _TOP_LEVEL_FIELDS)
    if unknown:
        _raise(
            EvidenceBundleErrorCode.UNKNOWN_FIELD,
            "evidence bundle contains an unknown top-level field",
        )
    missing = sorted(_TOP_LEVEL_FIELDS - set(payload))
    if missing:
        _raise(
            EvidenceBundleErrorCode.SCHEMA_INVALID,
            "evidence bundle is missing a required top-level field",
        )


def _require_project_id(value: object) -> str:
    if not isinstance(value, str) or not _REFERENCE_RE.fullmatch(value):
        _raise(
            EvidenceBundleErrorCode.SCHEMA_INVALID,
            "source_project_id must be a closed identifier",
        )
    return value


def _require_utc(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _UTC_RE.fullmatch(value):
        _raise(
            EvidenceBundleErrorCode.SCHEMA_INVALID,
            "exported_at_utc must be an RFC 3339 UTC timestamp",
        )
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        _raise(
            EvidenceBundleErrorCode.SCHEMA_INVALID,
            "exported_at_utc is not a valid UTC timestamp",
        )
    return value


def _artifact_error(exc: Exception) -> NoReturn:
    message = str(exc)
    if "unsupported_sensitive_payload" in message:
        _raise(
            EvidenceBundleErrorCode.UNSUPPORTED_SENSITIVE_PAYLOAD,
            "evidence bundle contains unsupported sensitive content",
        )
    if "unknown field" in message:
        _raise(
            EvidenceBundleErrorCode.UNKNOWN_FIELD,
            "evidence artifact contains an unknown field",
        )
    _raise(
        EvidenceBundleErrorCode.ARTIFACT_INVALID,
        "evidence artifact failed typed identity verification",
    )


def _event_error(exc: Exception) -> NoReturn:
    if "unknown field" in str(exc):
        _raise(
            EvidenceBundleErrorCode.UNKNOWN_FIELD,
            "evidence event contains an unknown field",
        )
    _raise(
        EvidenceBundleErrorCode.CHAIN_INVALID,
        "evidence event failed typed chain verification",
    )


@dataclass(frozen=True)
class EvidenceBundle:
    source_project_id: str
    head: LedgerHead
    artifacts: tuple[LedgerArtifact, ...]
    events: tuple[LedgerEvent, ...]
    exported_at_utc: str | None

    @classmethod
    def create(
        cls,
        *,
        source_project_id: str,
        head: LedgerHead,
        artifacts: tuple[LedgerArtifact, ...],
        events: tuple[LedgerEvent, ...],
        exported_at_utc: str | None,
        limits: EvidenceBundleLimits | None = None,
    ) -> EvidenceBundle:
        limits = limits or EvidenceBundleLimits()
        source_project_id = _require_project_id(source_project_id)
        exported_at_utc = _require_utc(exported_at_utc)
        if not isinstance(head, LedgerHead) or head.sequence < 1:
            _raise(
                EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
                "evidence bundle requires a non-empty declared head",
            )
        if not isinstance(artifacts, tuple) or not isinstance(events, tuple):
            _raise(
                EvidenceBundleErrorCode.SCHEMA_INVALID,
                "artifacts and events must be tuples",
            )
        if not events:
            _raise(
                EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
                "evidence bundle requires complete history from genesis",
            )
        if len(events) > limits.max_events or len(artifacts) > limits.max_artifacts:
            _raise(
                EvidenceBundleErrorCode.RESOURCE_LIMIT,
                "evidence bundle exceeds event or artifact count limits",
            )
        sorted_artifacts = tuple(sorted(artifacts, key=lambda item: item.artifact_id))
        bundle = cls(
            source_project_id=source_project_id,
            head=head,
            artifacts=sorted_artifacts,
            events=events,
            exported_at_utc=exported_at_utc,
        )
        bundle._verify_with_limits(limits)
        bundle_mapping = bundle.to_mapping()
        raw = canonical_bytes(bundle_mapping)
        if len(raw) > limits.max_bytes:
            _raise(
                EvidenceBundleErrorCode.BYTE_LIMIT,
                "evidence bundle exceeds its byte limit",
            )
        _walk_resources(bundle_mapping, limits=limits)
        return bundle

    def _verify_with_limits(
        self,
        limits: EvidenceBundleLimits,
        *,
        typed_identities_verified: bool = False,
    ) -> None:
        _require_project_id(self.source_project_id)
        _require_utc(self.exported_at_utc)
        if not isinstance(self.head, LedgerHead) or self.head.sequence < 1:
            _raise(
                EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
                "evidence bundle requires a non-empty declared head",
            )
        if (
            len(self.events) > limits.max_events
            or len(self.artifacts) > limits.max_artifacts
        ):
            _raise(
                EvidenceBundleErrorCode.RESOURCE_LIMIT,
                "evidence bundle exceeds event or artifact count limits",
            )
        artifact_lookup: dict[str, LedgerArtifact] = {}
        for artifact in self.artifacts:
            if not isinstance(artifact, LedgerArtifact):
                _raise(
                    EvidenceBundleErrorCode.ARTIFACT_INVALID,
                    "artifact collection contains an untyped value",
                )
            if len(artifact.canonical_body) > limits.max_artifact_bytes:
                _raise(
                    EvidenceBundleErrorCode.RESOURCE_LIMIT,
                    "artifact exceeds its per-item byte limit",
                )
            if not typed_identities_verified:
                try:
                    artifact.verify()
                except (LedgerContractError, ValueError, TypeError) as exc:
                    _artifact_error(exc)
            if artifact.project_id != self.source_project_id:
                _raise(
                    EvidenceBundleErrorCode.PROJECT_MISMATCH,
                    "artifact project does not match bundle source project",
                )
            if artifact.artifact_id in artifact_lookup:
                _raise(
                    EvidenceBundleErrorCode.ARTIFACT_INVALID,
                    "artifact IDs cannot repeat",
                )
            artifact_lookup[artifact.artifact_id] = artifact
        previous = ZERO_HASH
        referenced: set[str] = set()
        for expected_sequence, event in enumerate(self.events, start=1):
            if not isinstance(event, LedgerEvent):
                _raise(
                    EvidenceBundleErrorCode.CHAIN_INVALID,
                    "event collection contains an untyped value",
                )
            if _event_wire_size(event) > limits.max_event_bytes:
                _raise(
                    EvidenceBundleErrorCode.RESOURCE_LIMIT,
                    "event exceeds its per-item byte limit",
                )
            if not typed_identities_verified:
                try:
                    event.verify()
                except (LedgerContractError, ValueError, TypeError) as exc:
                    _event_error(exc)
            if event.project_id != self.source_project_id:
                _raise(
                    EvidenceBundleErrorCode.PROJECT_MISMATCH,
                    "event project does not match bundle source project",
                )
            if (
                event.sequence != expected_sequence
                or event.previous_event_hash != previous
            ):
                _raise(
                    EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
                    "event history must be consecutive from genesis",
                )
            unresolved = set(event.subject_artifact_ids) - set(artifact_lookup)
            if unresolved:
                _raise(
                    EvidenceBundleErrorCode.UNRESOLVED_SUBJECT,
                    "event references an unresolved subject artifact",
                )
            try:
                event.require_snapshot_subject(artifact_lookup)
            except LedgerContractError as exc:
                _event_error(exc)
            referenced.update(event.subject_artifact_ids)
            previous = event.event_hash
        last = self.events[-1]
        if (
            self.head.sequence != last.sequence
            or self.head.event_hash != last.event_hash
        ):
            _raise(
                EvidenceBundleErrorCode.INCOMPLETE_HISTORY,
                "declared head does not equal the complete event history",
            )
        if set(artifact_lookup) != referenced:
            _raise(
                EvidenceBundleErrorCode.ARTIFACT_INVALID,
                "bundle cannot carry unreferenced artifact content",
            )
        for artifact in self.artifacts:
            if artifact.artifact_kind is LedgerArtifactKind.REQUEST_SNAPSHOT:
                snapshot = artifact.decode_value()
                if not isinstance(snapshot, ResearchRequestSnapshot):
                    _raise(
                        EvidenceBundleErrorCode.ARTIFACT_INVALID,
                        "request snapshot decoded to the wrong type",
                    )
                try:
                    snapshot.restore(artifact_lookup)
                except (LedgerContractError, ValueError) as exc:
                    _artifact_error(exc)

    def verify(self) -> None:
        self._verify_with_limits(EvidenceBundleLimits())

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_id": "modori.evidence_bundle",
            "schema_version": 1,
            "canonicalization_id": CANONICALIZATION_ID,
            "hash_algorithm": HASH_ALGORITHM,
            "source_project_id": self.source_project_id,
            "exported_at_utc": self.exported_at_utc,
            "head": self.head.to_mapping(),
            "artifacts": [artifact.to_mapping() for artifact in self.artifacts],
            "events": [event.to_mapping() for event in self.events],
        }

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_mapping())

    @property
    def source_bundle_digest(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()

    @classmethod
    def from_bytes(
        cls,
        raw: bytes,
        *,
        limits: EvidenceBundleLimits | None = None,
    ) -> EvidenceBundle:
        limits = limits or EvidenceBundleLimits()
        if not isinstance(raw, bytes):
            _raise(
                EvidenceBundleErrorCode.INVALID_UTF8,
                "evidence input must be bytes",
            )
        if len(raw) > limits.max_bytes:
            _raise(
                EvidenceBundleErrorCode.BYTE_LIMIT,
                "evidence input exceeds its byte limit",
            )
        if raw.startswith(b"SQLite format 3\x00") or raw.startswith(
            (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        ):
            _raise(
                EvidenceBundleErrorCode.FORBIDDEN_FORMAT,
                "database and archive formats are not evidence bundles",
            )
        if raw.startswith(b"\xef\xbb\xbf"):
            _raise(
                EvidenceBundleErrorCode.INVALID_UTF8,
                "UTF-8 BOM is not accepted",
            )
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _raise(
                EvidenceBundleErrorCode.INVALID_UTF8,
                "evidence input is not strict UTF-8",
            )
        _scan_json_structure(raw, limits)
        try:
            parsed = json.loads(
                text,
                object_pairs_hook=_pairs_hook,
                parse_int=_parse_integer,
                parse_float=_reject_number,
                parse_constant=_reject_number,
            )
        except RecursionError:
            _raise(
                EvidenceBundleErrorCode.NESTING_LIMIT,
                "evidence bundle exceeds its nesting limit",
            )
        except _DuplicateKey:
            _raise(
                EvidenceBundleErrorCode.DUPLICATE_KEY,
                "evidence JSON contains a duplicate key",
            )
        except _InvalidNumber:
            _raise(
                EvidenceBundleErrorCode.INVALID_NUMBER,
                "evidence JSON contains an excluded numeric form",
            )
        except json.JSONDecodeError:
            _raise(
                EvidenceBundleErrorCode.INVALID_JSON,
                "evidence input is not valid JSON",
            )
        _walk_resources(parsed, limits=limits)
        if not isinstance(parsed, Mapping):
            _raise(
                EvidenceBundleErrorCode.SCHEMA_INVALID,
                "evidence bundle root must be an object",
            )
        _require_exact_top_level(parsed)
        try:
            if canonical_bytes(parsed) != raw:
                _raise(
                    EvidenceBundleErrorCode.NONCANONICAL,
                    "evidence bytes are not the sole canonical representation",
                )
        except CanonicalizationError as exc:
            _raise(
                EvidenceBundleErrorCode.NONCANONICAL,
                f"evidence value is outside the canonical profile: {exc}",
            )
        if (
            parsed["schema_id"] != "modori.evidence_bundle"
            or parsed["schema_version"] != 1
            or parsed["canonicalization_id"] != CANONICALIZATION_ID
            or parsed["hash_algorithm"] != HASH_ALGORITHM
        ):
            _raise(
                EvidenceBundleErrorCode.SCHEMA_INVALID,
                "evidence bundle schema or hash profile is unsupported",
            )
        raw_artifacts = parsed["artifacts"]
        raw_events = parsed["events"]
        if not isinstance(raw_artifacts, list) or not isinstance(raw_events, list):
            _raise(
                EvidenceBundleErrorCode.SCHEMA_INVALID,
                "artifacts and events must be arrays",
            )
        if (
            len(raw_artifacts) > limits.max_artifacts
            or len(raw_events) > limits.max_events
        ):
            _raise(
                EvidenceBundleErrorCode.RESOURCE_LIMIT,
                "evidence bundle exceeds event or artifact count limits",
            )
        artifacts: list[LedgerArtifact] = []
        for item in raw_artifacts:
            if not isinstance(item, Mapping):
                _raise(
                    EvidenceBundleErrorCode.ARTIFACT_INVALID,
                    "artifact must be an object",
                )
            try:
                artifacts.append(LedgerArtifact.from_mapping(item))
            except (LedgerContractError, ValueError, TypeError) as exc:
                _artifact_error(exc)
        if tuple(item.artifact_id for item in artifacts) != tuple(
            sorted(item.artifact_id for item in artifacts)
        ):
            _raise(
                EvidenceBundleErrorCode.NONCANONICAL,
                "artifact array must use deterministic artifact-ID order",
            )
        events: list[LedgerEvent] = []
        for item in raw_events:
            if not isinstance(item, Mapping):
                _raise(
                    EvidenceBundleErrorCode.CHAIN_INVALID,
                    "event must be an object",
                )
            try:
                events.append(LedgerEvent.from_mapping(item))
            except (LedgerContractError, ValueError, TypeError) as exc:
                _event_error(exc)
        raw_head = parsed["head"]
        if not isinstance(raw_head, Mapping):
            _raise(
                EvidenceBundleErrorCode.CHAIN_INVALID,
                "declared head must be an object",
            )
        try:
            head = LedgerHead.from_mapping(raw_head)
        except (LedgerContractError, ValueError, TypeError) as exc:
            _event_error(exc)
        bundle = cls(
            source_project_id=parsed["source_project_id"],
            head=head,
            artifacts=tuple(artifacts),
            events=tuple(events),
            exported_at_utc=parsed["exported_at_utc"],
        )
        bundle._verify_with_limits(limits, typed_identities_verified=True)
        return bundle
