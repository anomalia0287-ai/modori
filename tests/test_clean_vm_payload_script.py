from __future__ import annotations

from pathlib import Path


PAYLOAD_SCRIPT = Path("scripts/attach_modori_payload_disk.ps1")
ATTACH_WRAPPER = Path("RUN_ATTACH_PAYLOAD_AS_ADMIN.cmd")
CHECK_WRAPPER = Path("RUN_CHECK_PAYLOAD_V2_AS_ADMIN.cmd")


def _payload_script_text() -> str:
    return PAYLOAD_SCRIPT.read_text(encoding="utf-8")


def test_payload_script_writes_a_human_readable_contract_file() -> None:
    text = _payload_script_text()

    assert "QA_CONTRACT.txt" in text
    assert "engine-smoke-reference.xlsx" in text
    assert "visible-import-reference.xlsx" in text
    assert "public_data_formats" in text
    assert "Engine smoke sample" in text
    assert "Import visibility samples" in text
    assert "Public data import contract samples" in text


def test_engine_smoke_batch_uses_engine_reference_not_import_reference() -> None:
    text = _payload_script_text()
    engine_block = text.split('$engineSmoke = @"', maxsplit=1)[1].split('"@', maxsplit=1)[0]

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
    assert "modori-public-data-smoke.json" in smoke_block
    assert "type \"%USERPROFILE%\\Desktop\\modori-public-data-smoke.json\"" in smoke_block
    assert "exit /b %RESULT%" in smoke_block


def test_attach_wrapper_requires_explicit_admin_instead_of_hidden_self_elevation() -> None:
    text = ATTACH_WRAPPER.read_text(encoding="utf-8")

    assert "Start-Process" not in text
    assert "-Verb RunAs" not in text
    assert "-RebuildPayload" in text
    assert "This file must be run as Administrator." in text
    assert "No VM changes were made." in text
    assert "attach-payload-v2.log" in text


def test_payload_v2_check_wrapper_is_read_only_and_requires_admin() -> None:
    text = CHECK_WRAPPER.read_text(encoding="utf-8")

    assert "Start-Process" not in text
    assert "-Verb RunAs" not in text
    assert "check_modori_payload_v2.ps1" in text
    assert "This file must be run as Administrator." in text
    assert "No VM changes were made." in text


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
