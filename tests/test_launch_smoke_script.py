from __future__ import annotations

import os
import subprocess
import sys
import json


def test_launch_smoke_loads_qml_root_in_offscreen_mode(tmp_path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MODORI_CACHE_DIR"] = str(tmp_path / "cache")
    env["MODORI_SETTINGS_PATH"] = str(tmp_path / "settings.json")

    result = subprocess.run(
        [sys.executable, "scripts/launch_smoke.py"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "launch-smoke-ok" in result.stdout


def test_app_launch_smoke_writes_qml_root_payload(tmp_path) -> None:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MODORI_CACHE_DIR"] = str(tmp_path / "cache")
    env["MODORI_SETTINGS_PATH"] = str(tmp_path / "settings.json")
    output_path = tmp_path / "launch-smoke.json"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from modori.app import main; "
                "import sys; "
                "raise SystemExit(main(['modori', '--launch-smoke', sys.argv[1]]))"
            ),
            str(output_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stderr
    assert payload["ok"] is True
    assert payload["root_objects"] == 1
