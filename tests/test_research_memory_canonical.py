from __future__ import annotations

import hashlib
import unicodedata

import pytest

from modori.research_memory.canonical import (
    CANONICALIZATION_ID,
    HASH_ALGORITHM,
    ZERO_HASH,
    CanonicalizationError,
    artifact_id,
    canonical_bytes,
    canonical_digest,
    event_hash,
)


def test_canonical_bytes_are_stable_utf8_without_whitespace() -> None:
    assert canonical_bytes({"z": "한글", "a": [True, 1, None]}) == (
        '{"a":[true,1,null],"z":"한글"}'.encode()
    )
    assert CANONICALIZATION_ID == "modori-cjson-v1"
    assert HASH_ALGORITHM == "sha-256"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"value": 1.5}, "floats"),
        ({"value": 9_007_199_254_740_992}, "safe integer"),
        ({"한글": "value"}, "ASCII keys"),
        ({"value": unicodedata.normalize("NFD", "한글")}, "NFC"),
        ({"UPPER": "value"}, "lowercase"),
        ({"hyphen-key": "value"}, "schema key"),
        ({1: "value"}, "string keys"),
        ({"value": b"bytes"}, "unsupported"),
    ],
)
def test_canonical_profile_rejects_ambiguous_values(
    value: object,
    message: str,
) -> None:
    with pytest.raises(CanonicalizationError, match=message):
        canonical_bytes(value)


def test_bool_is_not_treated_as_an_integer_and_negative_safe_integer_is_valid() -> None:
    assert canonical_bytes({"enabled": False, "value": -9_007_199_254_740_991}) == (
        b'{"enabled":false,"value":-9007199254740991}'
    )
    assert canonical_bytes({"value": 9_007_199_254_740_991}) == (
        b'{"value":9007199254740991}'
    )


def test_control_quote_and_backslash_encoding_is_frozen() -> None:
    assert canonical_bytes({"text": 'line\n"quoted"\\tail'}) == (
        b'{"text":"line\\n\\"quoted\\"\\\\tail"}'
    )


def test_lone_surrogate_is_rejected_as_invalid_utf8_text() -> None:
    with pytest.raises(CanonicalizationError, match="UTF-8"):
        canonical_bytes({"text": "\ud800"})


def test_digest_is_sha256_of_canonical_bytes() -> None:
    value = {"schema_id": "modori.decision_event", "schema_version": 1}
    assert canonical_digest(value) == hashlib.sha256(canonical_bytes(value)).hexdigest()


def test_event_hash_changes_for_sequence_previous_hash_and_body() -> None:
    body = canonical_digest({"schema_id": "modori.decision_event"})
    baseline = event_hash(1, ZERO_HASH, body)
    assert body == "f57f6b387a84802f8cafe6c645ed06d862df598c82f58f7d03c766cb490544e8"
    assert baseline == "1fe7ac11d4034a0cdaaca66a02b0745b04efe77fedbc6337192e86d7b24943e3"
    assert artifact_id("question_spec", b"{}") == (
        "9adf57edd87a338ab1537d0ff13b69320c3918ff4c67b5880758c768e57ccb83"
    )
    assert baseline != event_hash(2, ZERO_HASH, body)
    assert baseline != event_hash(1, "a" * 64, body)
    assert baseline != event_hash(1, ZERO_HASH, "b" * 64)
    assert baseline != artifact_id("question_spec", b"{}")


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: event_hash(0, ZERO_HASH, "a" * 64), "positive"),
        (lambda: event_hash(True, ZERO_HASH, "a" * 64), "integer"),
        (lambda: event_hash(1, "A" * 64, "a" * 64), "lowercase"),
        (lambda: event_hash(1, ZERO_HASH, "x" * 64), "lowercase"),
        (lambda: artifact_id("QuestionSpec", b"{}"), "kind"),
        (lambda: artifact_id("question_spec", "{}"), "bytes"),
    ],
)
def test_hash_domains_reject_ambiguous_inputs(call, message: str) -> None:
    with pytest.raises(CanonicalizationError, match=message):
        call()
