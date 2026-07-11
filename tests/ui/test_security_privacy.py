import ast
from pathlib import Path


def python_ui_sources() -> list[Path]:
    return sorted(Path("src/modori/ui").glob("**/*.py")) + [Path("src/modori/app.py")]


def qml_sources() -> list[Path]:
    return sorted(Path("src/modori/ui/qml").glob("**/*.qml"))


def test_ui_network_guard_has_no_runtime_network_imports() -> None:
    from modori.ui.security import FORBIDDEN_NETWORK_IMPORTS

    violations: list[str] = []
    for path in python_ui_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_NETWORK_IMPORTS:
                        violations.append(f"{path}:{alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_NETWORK_IMPORTS:
                    violations.append(f"{path}:{node.module}")

    assert violations == []


def test_qml_has_no_remote_assets_or_web_engine() -> None:
    forbidden = ("http://", "https://", "WebEngine", "XmlHttpRequest", "fetch(")
    violations = [
        f"{path}:{token}"
        for path in qml_sources()
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_app_bootstrap_exposes_reduce_effects_from_env(monkeypatch) -> None:
    from modori.app import AppBootstrap

    monkeypatch.setenv("MODORI_REDUCE_EFFECTS", "1")

    assert AppBootstrap().reduceEffects is True


def test_controller_reduce_effects_toggle_persists_to_settings(tmp_path, monkeypatch) -> None:
    from modori.ui.controller import UiController

    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("MODORI_SETTINGS_PATH", str(settings_path))

    controller = UiController(reduce_effects=False)
    assert controller.setReduceEffects(True) is True

    reloaded = UiController()
    assert reloaded.reduceEffects is True


def test_work_screen_exposes_reduce_effects_toggle() -> None:
    work = Path("src/modori/ui/qml/screens/WorkScreen.qml").read_text(encoding="utf-8")
    main = Path("src/modori/ui/qml/Main.qml").read_text(encoding="utf-8")

    assert "work.reduce_effects" in work
    assert "uiController.setReduceEffects" in work
    assert "property bool reduceEffects: uiController.reduceEffects" in main


def test_app_bootstrap_exposes_string_catalog() -> None:
    from modori.app import AppBootstrap

    bootstrap = AppBootstrap()

    assert bootstrap.text("entry.guided") == "실험적 후보 안내"
    assert bootstrap.text("privacy.local") == "데이터는 이 컴퓨터를 떠나지 않습니다"
    assert bootstrap.text("missing.key") == "missing.key"


def test_core_qml_buttons_have_accessible_names() -> None:
    button_files = [
        Path("src/modori/ui/qml/screens/EntryScreen.qml"),
        Path("src/modori/ui/qml/components/PipelineRail.qml"),
    ]

    for path in button_files:
        text = path.read_text(encoding="utf-8")
        assert "Button" in text
        assert "Accessible.name" in text
