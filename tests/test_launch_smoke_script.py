from __future__ import annotations

import os
import subprocess
import sys


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
