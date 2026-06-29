import os
import shutil
import uuid
from pathlib import Path

import pytest


MPLCONFIGDIR = Path.cwd() / "matplotlib-cache"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))


@pytest.fixture
def tmp_path():
    root = (Path.cwd() / ".test-tmp").resolve()
    path = (root / uuid.uuid4().hex).resolve()
    if root not in path.parents:
        raise RuntimeError(f"Unsafe tmp_path outside test root: {path}")
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        if path.exists():
            shutil.rmtree(path)
