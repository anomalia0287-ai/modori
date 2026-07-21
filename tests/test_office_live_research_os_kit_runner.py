from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

from scripts.live_research_os_office_benchmark import (
    canonical_result_bytes,
    canonical_summary_bytes,
    seal_result,
)
from scripts.live_research_os_office_kit import (
    canonical_json_bytes,
    identity_bytes,
    sha256_bytes,
)
from scripts.verify_office_live_research_os_kit import (
    verify_returned_result,
    verify_returned_result_bytes,
)
from tests.test_live_research_os_office_benchmark_contract import _base_result
from tests.test_office_live_research_os_kit_verifier import _identity


def _sealed(*, duration_ns: int = 10_000_000) -> dict[str, object]:
    identity = _identity()
    base = _base_result(duration_ns=duration_ns)
    base["source_commit"] = identity.source_commit
    base["kit_identity_digest"] = sha256_bytes(identity_bytes(identity))
    return seal_result(base)


def _returned_bytes(result: dict[str, object]):
    raw = canonical_result_bytes(result)
    name = f"modori-live-research-os-office-benchmark-{result['run_id']}.json"
    sidecar = f"{hashlib.sha256(raw).hexdigest()}  {name}\n".encode("ascii")
    summary = canonical_summary_bytes(result)
    return name, raw, sidecar, summary


def _rehash_forged_mapping(result: dict[str, object]) -> bytes:
    hashing_view = {key: value for key, value in result.items() if key != "result_hash"}
    result["result_hash"] = hashlib.sha256(
        canonical_json_bytes(hashing_view)
    ).hexdigest()
    return canonical_json_bytes(result)


def test_returned_verifier_recomputes_a_valid_pass_and_stop() -> None:
    for duration, expected in (
        (10_000_000, "valid_pass"),
        (30_000_000_001, "valid_stop"),
    ):
        result = _sealed(duration_ns=duration)
        name, raw, sidecar, summary = _returned_bytes(result)
        verified = verify_returned_result_bytes(
            _identity(),
            json_name=name,
            result_bytes=raw,
            sidecar_bytes=sidecar,
            summary_bytes=summary,
        )
        assert verified.status == expected
        assert verified.reason_code is None
        assert verified.evaluation is not None
        assert verified.evaluation.disposition == result["evaluation"]["disposition"]
        assert verified.origin_authenticated is False


def test_stored_pass_is_rejected_when_raw_observation_is_slow() -> None:
    original = _sealed()
    forged = deepcopy(original)
    forged["observations"]["identity_waits"][0]["duration_ns"] = 30_000_000_001
    raw = _rehash_forged_mapping(forged)
    name = f"modori-live-research-os-office-benchmark-{forged['run_id']}.json"
    sidecar = f"{hashlib.sha256(raw).hexdigest()}  {name}\n".encode("ascii")
    verified = verify_returned_result_bytes(
        _identity(),
        json_name=name,
        result_bytes=raw,
        sidecar_bytes=sidecar,
        summary_bytes=canonical_summary_bytes(original),
    )
    assert verified.status == "invalid_run"
    assert verified.reason_code == "result_contract_invalid"


def test_observation_deletion_reorder_and_protocol_drift_are_invalid_runs() -> None:
    mutations = []
    deleted = deepcopy(_sealed())
    deleted["observations"]["decision_waits"].pop()
    mutations.append(deleted)
    reordered = deepcopy(_sealed())
    reordered["observations"]["identity_waits"].reverse()
    mutations.append(reordered)
    protocol = deepcopy(_sealed())
    protocol["protocol"]["cold_processes_per_stratum"] = 19
    mutations.append(protocol)

    for mutation in mutations:
        raw = _rehash_forged_mapping(mutation)
        name = f"modori-live-research-os-office-benchmark-{mutation['run_id']}.json"
        sidecar = f"{hashlib.sha256(raw).hexdigest()}  {name}\n".encode("ascii")
        verified = verify_returned_result_bytes(
            _identity(),
            json_name=name,
            result_bytes=raw,
            sidecar_bytes=sidecar,
            summary_bytes=b"forged",
        )
        assert verified.status == "invalid_run"
        assert verified.reason_code in {
            "result_contract_invalid",
            "kit_binding_invalid",
        }


def test_invalid_execution_conditions_are_not_mislabeled_product_stop() -> None:
    result = _sealed()
    result["execution_conditions"]["ac_power"] = False
    result = seal_result(
        {
            key: value
            for key, value in result.items()
            if key not in {"evaluation", "result_hash"}
        }
    )
    name, raw, sidecar, summary = _returned_bytes(result)
    verified = verify_returned_result_bytes(
        _identity(),
        json_name=name,
        result_bytes=raw,
        sidecar_bytes=sidecar,
        summary_bytes=summary,
    )
    assert verified.status == "invalid_run"
    assert verified.reason_code == "execution_conditions_invalid"


def test_result_sidecar_summary_and_kit_binding_mutations_are_typed_invalid() -> None:
    result = _sealed()
    name, raw, sidecar, summary = _returned_bytes(result)
    cases = (
        (raw + b"x", sidecar, summary, "result_sidecar_invalid"),
        (raw, sidecar + b"x", summary, "result_sidecar_invalid"),
        (raw, sidecar, summary + b"x", "summary_invalid"),
    )
    for changed_raw, changed_sidecar, changed_summary, reason in cases:
        verified = verify_returned_result_bytes(
            _identity(),
            json_name=name,
            result_bytes=changed_raw,
            sidecar_bytes=changed_sidecar,
            summary_bytes=changed_summary,
        )
        assert verified.status == "invalid_run"
        assert verified.reason_code == reason

    other_identity = deepcopy(_identity().to_mapping())
    other_identity["source_commit"] = "c" * 40
    other_identity.pop("schema_id")
    other_identity.pop("schema_version")
    from scripts.live_research_os_office_kit import KitIdentity

    verified = verify_returned_result_bytes(
        KitIdentity(**other_identity),
        json_name=name,
        result_bytes=raw,
        sidecar_bytes=sidecar,
        summary_bytes=summary,
    )
    assert verified.status == "invalid_run"
    assert verified.reason_code == "kit_binding_invalid"


def test_path_wrapper_requires_the_exact_three_returned_files(tmp_path: Path) -> None:
    result = _sealed()
    name, raw, sidecar, summary = _returned_bytes(result)
    json_path = tmp_path / name
    sidecar_path = tmp_path / f"{name}.sha256"
    summary_path = tmp_path / f"{name.removesuffix('.json')}.summary-ko.txt"
    json_path.write_bytes(raw)
    sidecar_path.write_bytes(sidecar)
    summary_path.write_bytes(summary)
    verified = verify_returned_result(
        _identity(),
        json_path=json_path,
        sidecar_path=sidecar_path,
        summary_path=summary_path,
    )
    assert verified.status == "valid_pass"

    summary_path.rename(tmp_path / "wrong-name.txt")
    invalid = verify_returned_result(
        _identity(),
        json_path=json_path,
        sidecar_path=sidecar_path,
        summary_path=tmp_path / "wrong-name.txt",
    )
    assert invalid.status == "invalid_run"
    assert invalid.reason_code == "result_file_set_invalid"
