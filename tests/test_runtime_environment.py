import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from modori.cache import cache_dir


def test_installed_package_imports_from_non_project_working_directory(tmp_path) -> None:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["MODORI_CACHE_DIR"] = str(tmp_path / "cache")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import modori.app; print('import-ok')",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "import-ok" in result.stdout


def test_pipeline_from_json_registers_builtin_steps_in_fresh_process(tmp_path) -> None:
    payload = {
        "source_dataset": {
            "df": {"columns": [], "index": [], "data": []},
            "variables": {},
        },
        "steps": [
            {
                "type": "data.compose_scale",
                "id": "compose",
                "title": "Compose score",
                "params": {
                    "items": ["q1"],
                    "method": "mean",
                    "name": "score",
                    "missing_policy": {"preset": "survey", "min_valid": 1.0},
                },
                "input_step_ids": [],
            }
        ],
    }
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["MODORI_CACHE_DIR"] = str(tmp_path / "cache")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from modori.core import Pipeline; "
                f"pipeline = Pipeline.from_json({json.dumps(json.dumps(payload))}); "
                "print(pipeline.steps[0].step_type)"
            ),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "data.compose_scale" in result.stdout


def test_cache_dir_returns_absolute_configured_directory(tmp_path, monkeypatch) -> None:
    configured = tmp_path / "cache"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(configured))

    result = cache_dir()

    assert result == configured.resolve()
    assert result.is_dir()


def test_cache_dir_ignores_relative_configured_directory(tmp_path, monkeypatch) -> None:
    relative = Path("relative-cache-from-env")
    appdata_root = tmp_path / "localappdata"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODORI_CACHE_DIR", str(relative))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata_root))

    result = cache_dir()

    assert result == (appdata_root / "Modori" / "cache").resolve()
    assert result.is_dir()
    assert not relative.exists()


def test_cache_dir_rejects_configured_symlink(tmp_path, monkeypatch) -> None:
    target = tmp_path / "target-cache"
    target.mkdir()
    link = tmp_path / "linked-cache"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available in this environment")
    appdata_root = tmp_path / "localappdata"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(link))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata_root))

    result = cache_dir()

    assert result == (appdata_root / "Modori" / "cache").resolve()


def test_cache_dir_falls_back_when_configured_path_is_file(
    tmp_path,
    monkeypatch,
) -> None:
    configured_file = tmp_path / "cache-file"
    configured_file.write_text("not a directory", encoding="utf-8")
    appdata_root = tmp_path / "localappdata"
    monkeypatch.setenv("MODORI_CACHE_DIR", str(configured_file))
    monkeypatch.setenv("LOCALAPPDATA", str(appdata_root))
    monkeypatch.setenv("TMP", str(tmp_path / "tmp"))
    monkeypatch.setenv("TEMP", str(tmp_path / "tmp"))

    result = cache_dir()

    assert result == (appdata_root / "Modori" / "cache").resolve()
    assert result.is_dir()


def test_reporting_ignores_legacy_matplotlib_cache_env(tmp_path) -> None:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("MPLCONFIGDIR", None)
    env["MODORI_CACHE_DIR"] = str(tmp_path / "cache")
    env["MODORI_MPLCONFIGDIR"] = str(tmp_path / "legacy-mpl-cache")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; import modori.steps.reporting; print(os.environ['MPLCONFIGDIR'])",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == (tmp_path / "cache" / "matplotlib").resolve()
