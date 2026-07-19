from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/qa/research-os-royal-blue-functional-integration-ledger.json"
EXPECTED_PATHS = {
    "docs/security/file-operations-audit-2026-06-29.md",
    "src/modori/app.py",
    "src/modori/ui/controller.py",
    "src/modori/ui/qml/components/AppButton.qml",
    "src/modori/ui/qml/components/DataGridView.qml",
    "src/modori/ui/qml/components/GuideRail.qml",
    "src/modori/ui/qml/components/PipelineRail.qml",
    "src/modori/ui/qml/screens/WorkScreen.qml",
    "src/modori/ui/qml/theme/Theme.qml",
    "src/modori/ui/recommendation_controller.py",
    "src/modori/ui/strings.py",
    "tests/test_file_operation_audit.py",
    "tests/ui/test_compact_control_system.py",
    "tests/ui/test_cream_nacre_visual_system.py",
    "tests/ui/test_data_grid_qml.py",
    "tests/ui/test_guided_standard_pipeline_rail.py",
    "tests/ui/test_guided_standard_variable_selection_flow.py",
    "tests/ui/test_human_operated_qml_flow.py",
    "tests/ui/test_mode_action_surfaces.py",
    "tests/ui/test_qml_string_catalog.py",
    "tests/ui/test_qml_visual_contract.py",
    "tests/ui/test_result_binding.py",
    "tests/ui/test_result_surface_qml.py",
    "tests/ui/test_security_privacy.py",
    "tests/ui/test_variable_metadata_editing.py",
}
EXPECTED_SOURCE_SEQUENCE = [
    "55fe9791d2b38de6b1de93ba99ad8f0b417015fc",
    "11a1280fa0d4ef9063401a3d9b25e814d81a2708",
    "64801e66cce82063f0cc68c978c27e4b6fa80ac6",
    "847c09505c655a4b36bf5e36af511a7f1fac4413",
    "bca88558818096ef258a635146e920633a6dff7a",
    "9db213cf8c13713608fb8e98aabb44447057be50",
    "7a1ec2fd79ec4b8cf81c9d9008f7699a98124e2e",
]
EXPECTED_INTEGRATED_SEQUENCE = [
    "98451c9e08c40b5987991f438c3a73454f820966",
    "1a5a43c911a705fa532efe5b0b419a7f97175444",
    "70dadf9efb58724d83e95074390cf9a31301b1a6",
    "e05aca3b1a8c4c80144dd69528366330d3e79748",
    "d8fcb7bde47c5a707e5878dce01aa6036ae75f8d",
    "e5db816f211ab8e9fc981e8f99b70a7288914085",
    "05b1ede1fc58a6f3644ceb4fef5d9706f47522af",
]


def _working_tree_blob(path: str) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def test_integration_ledger_is_closed_and_bound_to_the_working_tree() -> None:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert payload["schema_id"] == (
        "modori.research-os-royal-blue-functional-integration-ledger"
    )
    assert payload["schema_version"] == 2
    assert payload["status"] == "verified"
    assert payload["commit_sequence"] == EXPECTED_SOURCE_SEQUENCE
    assert payload["integrated_commit_sequence"] == EXPECTED_INTEGRATED_SEQUENCE

    entries = payload["entries"]
    paths = [entry["path"] for entry in entries]
    assert len(paths) == len(set(paths)) == 25
    assert set(paths) == EXPECTED_PATHS
    assert payload["summary"]["shared_paths"] == 25
    assert payload["summary"]["preview_textual_conflicts"] == 12
    assert sum(bool(entry["textual_conflict_preview"]) for entry in entries) == 12

    for entry in entries:
        assert entry["status"] == "verified", entry["path"]
        assert re.fullmatch(r"[0-9a-f]{40}", entry["integrated_blob_oid"])
        assert entry["integrated_blob_oid"] == _working_tree_blob(entry["path"])
        evidence = entry["evidence"]
        assert set(evidence) == {
            "focused_tests",
            "presence_checks",
            "absence_checks",
        }
        assert all(evidence[key] for key in evidence)
        assert all(
            isinstance(item, str) and item.strip()
            for values in evidence.values()
            for item in values
        )
