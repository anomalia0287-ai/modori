from __future__ import annotations

import hashlib
from pathlib import Path

from modori.core import Dataset
from modori.recommendations import RecommendationService
from modori.steps.data_prep import metadata_variables
from modori.table_io import read_full


PAYLOAD_SCRIPT = Path("scripts/attach_modori_payload_disk.ps1")
ATTACH_WRAPPER = Path("RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd")
CHECK_WRAPPER = Path("RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd")
CHECK_SCRIPT = Path("scripts/check_modori_payload_v2.ps1")
EXPERIMENTAL_FIXTURES = Path(".visual-qa/clean-win-vm-payload")
EXPERIMENTAL_FIXTURE_HASHES = {
    "experimental-candidate.csv": "7C8930F6CF05428F4C80EF99E54278664D4CEE303361C5A4B819407DF1975CF3",
    "experimental-configuration.csv": "DA555DA9FB6379AC0192EC174477885DB0812AB806B7734CB155206CC56D8DCD",
    "experimental-no-candidate.csv": "8E2B0BFF6B601D1D54626990A48F2436F0AD7C2021C19AE636B3A34C1CADA4AC",
}


def _payload_script_text() -> str:
    return PAYLOAD_SCRIPT.read_text(encoding="utf-8")


def _batch_block(script_text: str, variable_name: str) -> str:
    marker = f"${variable_name} = @\""
    return script_text.split(marker, maxsplit=1)[1].split('"@', maxsplit=1)[0]


def test_payload_script_writes_a_human_readable_contract_file() -> None:
    text = _payload_script_text()

    assert "QA_CONTRACT.txt" in text
    assert "engine-smoke-reference.xlsx" in text
    assert "V1 statistical engine checks" in text
    assert "v1_statistics_smoke" in text
    assert "visible-import-reference.xlsx" in text
    assert "public_data_formats" in text
    assert "Engine smoke sample" in text
    assert "Import visibility samples" in text
    assert "Public data import contract samples" in text


def test_engine_smoke_batch_uses_engine_reference_not_import_reference() -> None:
    text = _payload_script_text()
    engine_block = _batch_block(text, "engineSmoke")

    assert "start /wait" in engine_block
    assert "--engine-smoke" in engine_block
    assert "Samples\\engine-smoke-reference.xlsx" in engine_block
    assert "Samples\\visible-import-reference.xlsx" not in engine_block
    assert "type \"%USERPROFILE%\\Desktop\\modori-engine-smoke.json\"" in engine_block
    assert "exit /b %RESULT%" in engine_block


def test_public_data_smoke_batch_uses_public_data_fixtures_and_writes_json() -> None:
    text = _payload_script_text()
    smoke_block = text.split('$publicDataSmoke = @"', maxsplit=1)[1].split('"@', maxsplit=1)[0]

    assert "start /wait" in smoke_block
    assert "--public-data-smoke" in smoke_block
    assert "Samples\\public_data_formats" in smoke_block
    assert "Modori-QA-Evidence" in smoke_block
    assert "result.json" in smoke_block
    assert "exit-code.txt" in smoke_block
    assert "stdout.txt" in smoke_block
    assert "README-next-step.txt" in smoke_block
    assert 'type "%EVIDENCE%\\stdout.txt"' in smoke_block
    assert "modori-public-data-smoke.json" not in smoke_block
    assert "exit /b %RESULT%" in smoke_block


def test_attach_wrapper_requires_explicit_admin_instead_of_hidden_self_elevation() -> None:
    text = ATTACH_WRAPPER.read_text(encoding="utf-8")

    assert "Start-Process" not in text
    assert "-Verb RunAs" not in text
    assert "-RebuildPayload" in text
    assert "This file must be run as Administrator." in text
    assert "No VM changes were made." in text
    assert "attach-payload-v2.log" in text
    assert "Expected success evidence" in text
    assert "Validate new payload contents" in text
    assert "Attach payload disk to VM" in text
    assert '-WorkspaceRoot "%~dp0."' in text


def test_payload_v2_check_wrapper_is_read_only_and_requires_admin() -> None:
    text = CHECK_WRAPPER.read_text(encoding="utf-8")

    assert "Start-Process" not in text
    assert "-Verb RunAs" not in text
    assert "check_modori_payload_v2.ps1" in text
    assert "This file must be run as Administrator." in text
    assert "No VM changes were made." in text
    assert "Expected current-payload evidence" in text
    assert "Payload V2 is current for the packaged app" in text


def test_payload_v2_check_reports_stale_payload_against_packaged_app() -> None:
    text = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "Payload freshness" in text
    assert "Get-NewestSourceWriteTimeUtc" in text
    assert "STATUS: Payload V2 is older than the packaged app" in text
    assert "STATUS: Payload V2 is current for the packaged app" in text
    assert "-RebuildPayload" in text


def test_existing_payload_vhdx_is_validated_before_attach() -> None:
    text = _payload_script_text()

    assert "Assert-PayloadDriveContents" in text
    assert "Mount-VHD -Path $Path -ReadOnly -PassThru" in text
    assert "QA_CONTRACT.txt" in text
    assert "Run-Engine-Smoke-XLSX.bat" in text
    assert "Run-Public-Data-Smoke.bat" in text
    assert "Samples\\public_data_formats\\kosis-two-row.csv" in text
    assert "Samples\\public_data_formats\\cp949-public.csv" in text
    assert "Samples\\public_data_formats\\notice-only.xlsx" in text


def test_payload_attach_requires_vm_off_to_avoid_hot_add_detection_drift() -> None:
    text = _payload_script_text()

    assert '$vm.State -ne "Off"' in text
    assert "VM must be Off before attaching Payload V2" in text


def test_attach_script_stops_transcript_before_success_exit() -> None:
    text = _payload_script_text()

    assert "function Complete-Success" in text
    assert "Stop-TranscriptIfStarted" in text
    assert text.count("exit 0") == 1


def test_attach_script_has_global_failure_trap_for_preflight_errors() -> None:
    text = _payload_script_text()

    assert "trap {" in text
    assert 'Write-Host "FAILED: $($_.Exception.Message)"' in text
    assert "Stop-TranscriptIfStarted" in text
    assert "$script:vhdMounted" in text


def test_attach_script_can_rebuild_payload_v2_instead_of_reusing_stale_vhdx() -> None:
    text = _payload_script_text()

    assert "[switch]$RebuildPayload" in text
    assert "Payload rebuild requested" in text
    assert "Remove-VMHardDiskDrive -VMHardDiskDrive" in text
    assert "ModoriPayloadV2.before-rebuild-" in text
    assert "Move-Item -LiteralPath $PayloadVhdPath" in text


def test_attach_script_detaches_legacy_payload_v1_to_prevent_drive_ambiguity() -> None:
    text = _payload_script_text()

    assert '$LegacyPayloadVhdPath = "C:\\VM\\ModoriPayload\\ModoriPayload.vhdx"' in text
    assert "Remove legacy Payload V1 disk" in text
    assert '$_.Path -eq $LegacyPayloadVhdPath' in text


def test_attach_script_rejects_stale_existing_payload_when_not_rebuilding() -> None:
    text = _payload_script_text()

    assert "Assert-PayloadVhdIsCurrent" in text
    assert "Get-NewestSourceWriteTimeUtc" in text
    assert "Existing payload VHDX is older than the packaged app" in text
    assert "rerun this script with -RebuildPayload" in text


def test_smoke_batches_switch_console_to_utf8_before_printing_json() -> None:
    script = _payload_script_text()

    assert script.count("chcp 65001 >nul") >= 2
    assert 'if ($smokeBatch -notmatch "chcp 65001")' in script


def test_payload_includes_visible_grid_overflow_fixture_for_manual_qa() -> None:
    text = _payload_script_text()

    assert "visible-grid-overflow.csv" in text
    assert "Samples\\visible-grid-overflow.csv" in text


def test_visible_grid_overflow_fixture_is_not_used_for_engine_smoke() -> None:
    text = _payload_script_text()
    engine_block = _batch_block(text, "engineSmoke")

    assert "engine-smoke-reference.xlsx" in engine_block
    assert "visible-grid-overflow.csv" not in engine_block


def test_experimental_recommendation_fixtures_are_pinned() -> None:
    actual = {
        name: hashlib.sha256((EXPERIMENTAL_FIXTURES / name).read_bytes())
        .hexdigest()
        .upper()
        for name in EXPERIMENTAL_FIXTURE_HASHES
    }

    assert actual == EXPERIMENTAL_FIXTURE_HASHES


def test_payload_requires_and_copies_experimental_recommendation_fixtures() -> None:
    text = _payload_script_text()

    for name in EXPERIMENTAL_FIXTURE_HASHES:
        assert name in text
        assert f"Samples\\experimental_recommendation\\{name}" in text
    assert "experimental_recommendation" in text


def _recommendation_kinds_for_fixture(name: str) -> tuple[tuple[str, bool], ...]:
    result = read_full(EXPERIMENTAL_FIXTURES / name, "csv")
    dataset = Dataset(
        df=result.frame,
        variables=metadata_variables(
            result.frame,
            origin_step_id="payload-fixture",
            metadata=result.metadata,
        ),
    )
    state = RecommendationService().recommend(dataset)
    return tuple(
        (candidate.kind, candidate.requires_configuration)
        for candidate in state.candidates
    )


def test_experimental_recommendation_fixtures_produce_bounded_product_states() -> None:
    ordinary = _recommendation_kinds_for_fixture("experimental-candidate.csv")
    configuration = _recommendation_kinds_for_fixture(
        "experimental-configuration.csv"
    )
    no_candidate = _recommendation_kinds_for_fixture(
        "experimental-no-candidate.csv"
    )

    assert ordinary
    assert any(kind == "descriptives" for kind, _required in ordinary)
    assert any(
        kind == "anova_factorial" and required
        for kind, required in configuration
    )
    assert no_candidate == ()
