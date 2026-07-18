from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from PySide6.QtGui import QImageReader

from scripts.package_windows import build_pyinstaller_command


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "tests/fixtures/research_flow_visual_states.json"
CAPTURE_SCRIPT = ROOT / "scripts/capture_research_flow_gallery.py"
PACKET_SCRIPT = ROOT / "scripts/build_research_flow_visual_review_packet.py"
THEME_PATH = ROOT / "src/modori/ui/qml/theme/Theme.qml"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _nearest_rank_p95(values: list[float]) -> float:
    assert values
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


def _load_script(path: Path, name: str) -> ModuleType:
    assert path.is_file(), f"missing required visual evidence script: {path.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _walk(
    value: object, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], object]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, (*path, str(index)))


def test_gallery_manifest_freezes_the_approved_matrix_before_capture() -> None:
    manifest = _manifest()
    constraints = manifest["constraints"]
    assert isinstance(constraints, dict)
    assert manifest["schema_id"] == "modori.research-flow.visual-gallery"
    assert manifest["schema_version"] == 1
    assert constraints["viewports"] == {
        "minimum": {"width": 1024, "height": 640},
        "reference": {"width": 1180, "height": 760},
    }
    assert constraints["panel_capture_width"] == 360
    assert constraints["locales"] == ["ko", "en"]
    assert constraints["modes"] == ["guided", "standard"]
    assert constraints["scale_factors"] == [1.0, 1.25, 1.5, 2.0]
    assert constraints["reduce_effects"] == [False, True]

    items = manifest["items"]
    fixtures = manifest["fixtures"]
    assert isinstance(items, list)
    assert isinstance(fixtures, dict)
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids)) == 29
    required_fields = {
        "id",
        "capture_kind",
        "state_id",
        "locale",
        "mode",
        "interaction_state",
        "viewport",
        "scale_factor",
        "reduce_effects",
        "fixture_id",
        "expected_present",
        "expected_absent",
        "expected_properties",
    }
    for item in items:
        assert set(item) == required_fields
        assert item["fixture_id"] in fixtures
        assert item["locale"] in constraints["locales"]
        assert item["mode"] in constraints["modes"]
        assert item["viewport"] in constraints["viewports"]
        assert item["scale_factor"] in constraints["scale_factors"]
        assert item["reduce_effects"] in constraints["reduce_effects"]

    states = {item["state_id"] for item in items}
    assert {
        "clarify_ready",
        "scope_boundary",
        "memory_unavailable",
        "failure",
        "fingerprinting",
        "candidate_ready",
        "preparation_blocked",
        "recovery_pending",
        "retracted",
        "replan_required",
        "abstain_ready",
        "causal_scope_notice",
        "prepare_review",
        "confirmed",
    } <= states
    interactions = {item["interaction_state"] for item in items}
    assert {
        "collapsed",
        "expanded",
        "default",
        "hover",
        "keyboard_focus",
        "disabled",
        "pressed",
    } <= interactions
    assert {item["scale_factor"] for item in items} == {1.0, 1.25, 1.5, 2.0}
    assert {item["locale"] for item in items} == {"ko", "en"}
    assert {item["mode"] for item in items} == {"guided", "standard"}
    assert {item["reduce_effects"] for item in items} == {False, True}


def test_manifest_fixture_content_is_synthetic_and_privacy_closed() -> None:
    manifest = _manifest()
    privacy = manifest["privacy"]
    assert isinstance(privacy, dict)
    forbidden_fields = set(privacy["forbidden_fixture_fields"])
    forbidden_patterns = [
        re.compile(pattern) for pattern in privacy["forbidden_text_patterns"]
    ]

    offenders: list[str] = []
    for path, value in _walk(manifest["fixtures"]):
        if path and path[-1] in forbidden_fields:
            offenders.append(".".join(path))
        if isinstance(value, str):
            for pattern in forbidden_patterns:
                if pattern.search(value):
                    offenders.append(f"{'.'.join(path)}={value}")

    assert offenders == []
    assert privacy["capture_scope"] == "application-content-only"
    assert privacy["metadata_policy"] == "no-text-metadata"


def test_capture_and_packet_scripts_implement_closed_evidence_boundaries() -> None:
    capture = _load_script(CAPTURE_SCRIPT, "research_flow_capture_contract")
    packet = _load_script(PACKET_SCRIPT, "research_flow_packet_contract")

    capture.validate_manifest(_manifest())
    assert capture.validate_clean_status(" M unrelated.txt", allow_dirty=True) is None
    with pytest.raises(capture.GalleryCaptureError, match="clean worktree"):
        capture.validate_clean_status(" M unrelated.txt", allow_dirty=False)
    assert capture.scan_forbidden_text(
        [r"C:\Users\someone\study.csv"],
        _manifest()["privacy"]["forbidden_text_patterns"],
    )

    assert packet.passes_contrast(4.5, 4.5) is True
    assert packet.passes_contrast(4.499999, 4.5) is False
    assert packet.passes_contrast(3.0, 3.0) is True
    assert packet.passes_contrast(2.999999, 3.0) is False


def test_exact_srgb_contrast_formula_and_alpha_composition() -> None:
    packet = _load_script(PACKET_SCRIPT, "research_flow_contrast_contract")

    assert packet.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert packet.contrast_ratio("#777777", "#777777") == pytest.approx(1.0)
    assert packet.composite_rgba(
        (0.0, 0.0, 0.0, 0.5), (1.0, 1.0, 1.0, 1.0)
    ) == pytest.approx((0.5, 0.5, 0.5, 1.0))


def test_every_declared_research_flow_contrast_pair_passes_unrounded_gate() -> None:
    packet = _load_script(PACKET_SCRIPT, "research_flow_contrast_evaluator")
    results = packet.evaluate_contrast_pairs(_manifest(), THEME_PATH)

    assert len(results) == len(_manifest()["contrast_pairs"])
    assert [row for row in results if not row["passes"]] == []
    assert {row["id"] for row in results} >= {
        "primary-default",
        "primary-hover",
        "primary-pressed",
        "focus-indicator",
        "primary-focus-indicator",
        "stale-badge",
        "error-badge",
    }


@pytest.fixture(scope="module")
def rendered_gallery(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert CAPTURE_SCRIPT.is_file(), "capture harness must exist before rendering"
    output = tmp_path_factory.mktemp("research-flow-gallery")
    completed = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_SCRIPT),
            "--manifest",
            str(MANIFEST_PATH),
            "--output",
            str(output),
            "--allow-dirty",
        ],
        cwd=ROOT,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return output


def test_full_matrix_renders_the_production_component_contract(
    rendered_gallery: Path,
) -> None:
    gallery = json.loads(
        (rendered_gallery / "gallery-manifest.json").read_text(encoding="utf-8")
    )
    assert gallery["schema_id"] == "modori.research-flow.rendered-gallery"
    assert gallery["source_commit"]
    assert len(gallery["items"]) == 29
    assert {item["scale_factor"] for item in gallery["items"]} == {
        1.0,
        1.25,
        1.5,
        2.0,
    }
    state_render_times: list[float] = []
    interaction_response_times: list[float] = []
    for item in gallery["items"]:
        assert item["source_commit"] == gallery["source_commit"]
        assert item["capture_kind"] in {"panel", "work_shell", "interaction"}
        assert item["production_component_exercised"] is True
        assert item["missing_present_regions"] == []
        assert item["unexpected_visible_regions"] == []
        assert item["property_mismatches"] == []
        assert item["horizontal_overflow_sources"] == [], item
        assert item["horizontal_overflow"] is False
        if sys.platform == "win32":
            assert item["qt_platform"] == "windows"
            assert item["visual_fidelity"] == "production-windows"
        assert item["font_family_count"] > 0
        if item["capture_kind"] == "panel":
            assert 0 < item["component_width"] <= 360
            assert item["header_title_clipped"] is False, item
        state_render_times.append(float(item["state_render_ms"]))
        if item["interaction_response_ms"] is not None:
            interaction_response_times.append(float(item["interaction_response_ms"]))
        assert item["logical_size"] in ([1024, 640], [1180, 760])
        image_path = rendered_gallery / item["image"]
        assert image_path.is_file()
        assert hashlib.sha256(image_path.read_bytes()).hexdigest() == item["sha256"]

    performance = _manifest()["constraints"]["performance_baseline"]["regression_gate"]
    assert _nearest_rank_p95(state_render_times) <= float(
        performance["single_item_render_p95_ms_max"]
    )
    assert _nearest_rank_p95(interaction_response_times) <= float(
        performance["interaction_response_p95_ms_max"]
    )


def test_captures_have_no_text_metadata_or_os_chrome_fields(
    rendered_gallery: Path,
) -> None:
    gallery = json.loads(
        (rendered_gallery / "gallery-manifest.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(gallery, ensure_ascii=False, sort_keys=True)
    for pattern in _manifest()["privacy"]["forbidden_text_patterns"]:
        assert re.search(pattern, serialized) is None
    for item in gallery["items"]:
        reader = QImageReader(str(rendered_gallery / item["image"]))
        assert reader.canRead()
        assert list(reader.textKeys()) == []
        assert item["capture_scope"] == "application-content-only"
        assert item["os_chrome_included"] is False


def test_mode_a_packet_is_digest_bound_and_contains_no_source(
    rendered_gallery: Path,
    tmp_path: Path,
) -> None:
    packet_dir = tmp_path / "mode-a"
    completed = subprocess.run(
        [
            sys.executable,
            str(PACKET_SCRIPT),
            "--gallery",
            str(rendered_gallery),
            "--output",
            str(packet_dir),
            "--source-manifest",
            str(MANIFEST_PATH),
        ],
        cwd=ROOT,
        env={**os.environ, "QT_QPA_PLATFORM": "windows"},
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    result_path = packet_dir / "packet-manifest.json"
    assert result_path == packet_dir / "packet-manifest.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["review_mode"] == "fresh-session-aesthetic"
    assert payload["synthetic_only"] is True
    assert payload["source_included"] is False
    if sys.platform == "win32":
        assert payload["contact_sheet"]["qt_platform"] == "windows"
    assert payload["contact_sheet"]["font_family_count"] > 0
    assert payload["contact_sheet"]["font_family"]
    assert (packet_dir / "visual-brief.md").is_file()
    assert (packet_dir / "immutable-boundaries.md").is_file()
    assert (packet_dir / "contact-sheet.png").is_file()
    text_payload = "\n".join(
        path.read_text(encoding="utf-8") for path in packet_dir.glob("*.md")
    )
    assert "src/" not in text_payload
    assert ".qml" not in text_payload
    for image in payload["images"]:
        path = packet_dir / image["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == image["sha256"]


def test_mode_a_packet_rejects_structural_only_offscreen_renders(
    rendered_gallery: Path,
    tmp_path: Path,
) -> None:
    packet = _load_script(PACKET_SCRIPT, "research_flow_packet_platform_gate")
    structural_gallery = tmp_path / "structural-gallery"
    shutil.copytree(rendered_gallery, structural_gallery)
    gallery_path = structural_gallery / "gallery-manifest.json"
    gallery = json.loads(gallery_path.read_text(encoding="utf-8"))
    gallery["items"][0]["qt_platform"] = "offscreen"
    gallery["items"][0]["visual_fidelity"] = "structural-only-offscreen"
    gallery_path.write_text(
        json.dumps(gallery, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(packet.ReviewPacketError, match="production Windows"):
        packet.build_mode_a_packet(
            structural_gallery,
            tmp_path / "rejected-packet",
            source_manifest_path=MANIFEST_PATH,
        )


def test_gallery_fixtures_and_review_tools_are_excluded_from_production_package() -> (
    None
):
    command = " ".join(build_pyinstaller_command()).replace("\\", "/")

    assert "research_flow_visual_states.json" not in command
    assert "capture_research_flow_gallery.py" not in command
    assert "build_research_flow_visual_review_packet.py" not in command
    assert "tests/fixtures" not in command
    assert ".visual-qa" not in command
    assert "src/modori/ui/qml;modori/ui/qml" in command
