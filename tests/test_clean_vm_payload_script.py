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
    assert "Engine smoke sample" in text
    assert "Import visibility samples" in text


def test_engine_smoke_batch_uses_engine_reference_not_import_reference() -> None:
    text = _payload_script_text()
    engine_block = text.split('$engineSmoke = @"', maxsplit=1)[1].split('"@', maxsplit=1)[0]

    assert "start /wait" in engine_block
    assert "--engine-smoke" in engine_block
    assert "Samples\\engine-smoke-reference.xlsx" in engine_block
    assert "Samples\\visible-import-reference.xlsx" not in engine_block
    assert "type \"%USERPROFILE%\\Desktop\\modori-engine-smoke.json\"" in engine_block
    assert "exit /b %RESULT%" in engine_block


def test_attach_wrapper_requires_explicit_admin_instead_of_hidden_self_elevation() -> None:
    text = ATTACH_WRAPPER.read_text(encoding="utf-8")

    assert "Start-Process" not in text
    assert "-Verb RunAs" not in text
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
