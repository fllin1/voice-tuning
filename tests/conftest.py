import os
from pathlib import Path

import pytest

# Force settings to use a temp directory before any backend module loads.
@pytest.fixture(autouse=True)
def _isolated_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VT_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("VT_AUDIO_CACHE_DIR", str(tmp_path / "cache"))
    # Force-empty (not delete): pydantic-settings reads .env directly, so a
    # real HUME_API_KEY in .env leaks into tests via the file. Env vars
    # override the .env file, so setting "" here keeps tests Hume-less.
    monkeypatch.setenv("HUME_API_KEY", "")
    # Reset cached singletons
    import backend.settings as s
    s._settings = None
    import backend.engines.registry as reg
    reg._engines = None
    yield
    s._settings = None
    reg._engines = None
