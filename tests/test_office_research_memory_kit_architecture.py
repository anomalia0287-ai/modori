from __future__ import annotations

import ast
from pathlib import Path

from scripts.build_office_research_memory_kit import PAYLOAD_SOURCE_MAP


KIT_PYTHON_FILES = (
    Path("scripts/office_research_memory_kit.py"),
    Path("scripts/verify_office_research_memory_kit.py"),
    Path("scripts/run_office_research_memory_benchmark.py"),
    Path("scripts/build_office_research_memory_kit.py"),
)


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_kit_python_has_no_network_ui_installer_or_product_calculation_imports() -> None:
    forbidden = {
        "aiohttp",
        "ftplib",
        "http",
        "pip",
        "requests",
        "smtplib",
        "socket",
        "tkinter",
        "urllib",
        "webbrowser",
        "winreg",
    }
    for path in KIT_PYTHON_FILES:
        assert _imported_roots(path).isdisjoint(forbidden), path
        source = path.read_text(encoding="utf-8")
        assert "modori.steps" not in source
        assert "modori.ui" not in source
        assert "modori.workflow" not in source


def test_powershell_and_cmd_templates_have_no_network_elevation_or_host_mutation() -> None:
    template_root = Path("scripts/office_benchmark_kit")
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted(template_root.iterdir())
    )
    forbidden = {
        "invoke-webrequest",
        "invoke-restmethod",
        "start-process",
        "verb runas",
        "set-itemproperty",
        "new-itemproperty",
        "remove-item",
        "get-childitem -recurse",
        "powercfg",
        "set-service",
        "stop-service",
        "start-service",
        "win32_network",
        "get-netadapter",
        "serialnumber",
        "ipaddress",
        "macaddress",
        "userprofile",
    }
    assert not {item for item in forbidden if item in source}
    assert "get-filehash" not in source
    assert source.count("system.security.cryptography.sha256") >= 2


def test_hardware_probe_uses_only_approved_windows_inventory_commands() -> None:
    source = Path(
        "scripts/run_office_research_memory_benchmark.py"
    ).read_text(encoding="utf-8")
    assert "Get-CimInstance Win32_ComputerSystem" in source
    assert "Get-CimInstance Win32_Processor" in source
    assert "Get-Partition" in source
    assert "Get-Disk" in source
    assert "Get-PhysicalDisk" in source
    assert "Get-Volume" in source
    assert "Win32_LogicalDisk" not in source
    assert "Win32_NetworkAdapter" not in source


def test_payload_allowlist_is_the_minimal_modori_import_closure() -> None:
    destinations = set(PAYLOAD_SOURCE_MAP.values())
    assert "payload/src/modori/path_policy.py" in destinations
    assert "payload/scripts/benchmark_research_memory.py" in destinations
    assert "payload/scripts/run_office_research_memory_benchmark.py" in destinations
    assert not any(path.startswith("payload/tests/") for path in destinations)
    assert not any("fixtures" in path or "recommendation" in path for path in destinations)
    assert not any(path.endswith((".csv", ".xlsx", ".sav", ".sqlite3")) for path in destinations)


def test_kit_has_no_api_that_can_grant_product_claim_authority() -> None:
    source = Path("scripts/office_research_memory_kit.py").read_text(encoding="utf-8")
    assert '"office_hardware_claim_allowed": False' in source
    assert "office_hardware_claim_allowed=True" not in source
    assert "office_hardware_claim_allowed = True" not in source
