"""A deliberately small canonical JSON profile and separated hash domains."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata


CANONICALIZATION_ID = "modori-cjson-v1"
HASH_ALGORITHM = "sha-256"
ZERO_HASH = "0" * 64

_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_EVENT_DOMAIN = b"modori.decision-ledger.event.v1\0"
_ARTIFACT_DOMAIN = b"modori.decision-ledger.artifact.v1\0"
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
_ARTIFACT_KIND = re.compile(r"^[a-z][a-z0-9_]*$")


class CanonicalizationError(ValueError):
    """Raised when a value has no representation in ``modori-cjson-v1``."""


def _validate_text(value: str, *, field: str) -> str:
    if value != unicodedata.normalize("NFC", value):
        raise CanonicalizationError(f"{field} must use NFC Unicode")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError(f"{field} must be valid UTF-8 text") from exc
    return value


def _validate_and_copy(value: object, *, depth: int) -> object:
    if depth > 64:
        raise CanonicalizationError("canonical value exceeds the nesting limit")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise CanonicalizationError("integer is outside the JSON safe integer range")
        return value
    if isinstance(value, float):
        raise CanonicalizationError("floats are excluded from modori-cjson-v1")
    if isinstance(value, str):
        return _validate_text(value, field="string")
    if isinstance(value, list):
        return [_validate_and_copy(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        copied: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("objects require string keys")
            _validate_text(key, field="object key")
            if not key.isascii():
                raise CanonicalizationError("object keys must be ASCII keys")
            if key.lower() != key:
                raise CanonicalizationError("object keys must be lowercase")
            if not _SCHEMA_KEY.fullmatch(key):
                raise CanonicalizationError(
                    "object key must be a lowercase ASCII schema key"
                )
            copied[key] = _validate_and_copy(item, depth=depth + 1)
        return copied
    raise CanonicalizationError(
        f"unsupported canonical value type: {type(value).__name__}"
    )


def canonical_bytes(value: object) -> bytes:
    """Return the sole UTF-8 JSON representation accepted by this profile."""

    normalized = _validate_and_copy(value, depth=0)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: object) -> str:
    """Return SHA-256 over :func:`canonical_bytes`."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _digest_bytes(value: str, *, field: str) -> bytes:
    if not isinstance(value, str) or not _HEX_DIGEST.fullmatch(value):
        raise CanonicalizationError(
            f"{field} must be a 64-character lowercase hexadecimal digest"
        )
    return bytes.fromhex(value)


def event_hash(sequence: int, previous_event_hash: str, body_digest: str) -> str:
    """Hash a ledger event using fixed-width and domain-separated framing."""

    if type(sequence) is not int:
        raise CanonicalizationError("event sequence must be an integer")
    if sequence < 1:
        raise CanonicalizationError("event sequence must be positive")
    if sequence > _MAX_SAFE_INTEGER:
        raise CanonicalizationError("event sequence exceeds the safe integer range")
    previous = _digest_bytes(previous_event_hash, field="previous_event_hash")
    body = _digest_bytes(body_digest, field="body_digest")
    framed = _EVENT_DOMAIN + sequence.to_bytes(8, "big") + previous + body
    return hashlib.sha256(framed).hexdigest()


def artifact_id(kind: str, body: bytes) -> str:
    """Return a domain-separated content ID for one typed artifact body."""

    if not isinstance(kind, str) or not _ARTIFACT_KIND.fullmatch(kind):
        raise CanonicalizationError(
            "artifact kind must be a lowercase ASCII snake-case identifier"
        )
    if not isinstance(body, bytes):
        raise CanonicalizationError("artifact body must be bytes")
    return hashlib.sha256(_ARTIFACT_DOMAIN + kind.encode("ascii") + b"\0" + body).hexdigest()
