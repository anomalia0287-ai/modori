from __future__ import annotations

import ast
from pathlib import Path


UI_ROOT = Path("src/modori/ui")


def test_ui_layer_does_not_import_private_step_helpers() -> None:
    violations: list[str] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module is None or not node.module.startswith("modori.steps"):
                continue
            private_names = sorted(alias.name for alias in node.names if alias.name.startswith("_"))
            if private_names:
                violations.append(f"{path}:{node.lineno}:{', '.join(private_names)}")

    assert violations == []


def test_ui_controller_does_not_keep_pipeline_internals() -> None:
    path = UI_ROOT / "controller.py"
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    controller = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UiController"
    )
    forbidden = {
        "_variable_keys",
        "_has_downstream_steps",
        "_has_pipeline_step",
        "_metadata_insert_after_step_id",
        "_run_current_pipeline",
        "_display_results_from_pipeline",
        "_kind_for_result",
        "_default_report_exporter",
        "_format_step_chain",
    }
    actual = {node.name for node in controller.body if isinstance(node, ast.FunctionDef)}

    assert sorted(actual & forbidden) == []


def test_ui_controller_does_not_keep_scattered_result_text_fields() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "_result_summary",
        "_result_table_text",
        "_result_notes_text",
        "_chart_paths_text",
        "_chart_source_text",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_keep_import_or_run_bookkeeping() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "_import_preview_text",
        "_pending_import_path",
        "_latest_run_id",
        "_last_future",
        "def submit_engine_job",
        "def _local_path_from_qml",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_own_variable_metadata_edit_internals() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "VariableMetadataPatchStep",
        "normalize_variable_metadata_patch",
        "Measure(str",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_own_analysis_selection_edit_internals() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "AnalysisSelectionCommandBuilder",
        "def _edit_pipeline_step",
        "def _analysis_command_builder",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_keep_pipeline_state_fields() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "_pipeline_version",
        "_status",
        "_stale",
        "_step_chain_text",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_own_library_resolution() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "load_library",
        "ui_entity_to_library_key",
        "resolve_help_key",
        "def _get_library",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_does_not_own_data_session_loading_policy() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "build_reference_slice_pipeline",
        "AnalysisPreferences",
        "def _default_pipeline_factory",
        "has_downstream_steps() and not options.confirm_new_session",
        "데이터 파일을 가져오지 못했습니다.",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_uses_service_composition_instead_of_individual_service_fields() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")
    forbidden = {
        "_pipeline_ops",
        "_analysis_editor",
        "_metadata_editor",
        "_data_session_loader",
        "_import_flow",
        "_report_export_service",
        "_result_binding_presenter",
        "_explanation_service",
        "_explanation_presenter",
    }

    assert sorted(name for name in forbidden if name in source) == []


def test_ui_controller_has_no_dead_library_field() -> None:
    path = UI_ROOT / "controller.py"
    source = path.read_text(encoding="utf-8")

    assert "self._library" not in source


def test_ui_services_use_explicit_pipeline_ops_protocols() -> None:
    checked_paths = [
        UI_ROOT / "analysis_editor.py",
        UI_ROOT / "metadata_editor.py",
        UI_ROOT / "data_session.py",
        UI_ROOT / "pipeline_state.py",
    ]
    violations: list[str] = []
    for path in checked_paths:
        source = path.read_text(encoding="utf-8")
        if "pipeline_ops: object" in source:
            violations.append(str(path))

    assert violations == []


def test_ui_controller_stays_within_facade_size_budget() -> None:
    path = UI_ROOT / "controller.py"
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    controller = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "UiController"
    )
    methods = [node for node in controller.body if isinstance(node, ast.FunctionDef)]
    longest_method = max(node.end_lineno - node.lineno + 1 for node in methods)

    assert controller.end_lineno - controller.lineno + 1 <= 560
    assert len(methods) <= 60
    assert longest_method <= 45
