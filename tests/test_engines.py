from backend.engines.base import EngineUnavailable, TTSEngine, VoiceMeta
from backend.engines.registry import get_engines


def test_registry_returns_all_three_engines():
    engines = get_engines()
    assert set(engines) == {"kokoro", "orpheus", "hume"}


def test_hume_disabled_without_key():
    engines = get_engines()
    assert engines["hume"].available is False
    assert "HUME_API_KEY" in (engines["hume"].unavailable_reason or "")


def test_kokoro_lists_voices_without_loading_model():
    """Listing voices should not trigger an mlx-audio model download."""
    engines = get_engines()
    kokoro = engines["kokoro"]
    if not kokoro.available:
        return  # mlx-audio not importable in this env; skip
    voices = kokoro.list_voices()
    assert len(voices) >= 20
    assert all(isinstance(v, VoiceMeta) for v in voices)
    assert {v.id for v in voices} >= {"af_heart", "am_michael", "bf_emma", "bm_george"}


def test_orpheus_lists_voices_without_loading_model():
    engines = get_engines()
    orpheus = engines["orpheus"]
    if not orpheus.available:
        return
    voices = orpheus.list_voices()
    assert {v.id for v in voices} == {"tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"}


def test_engine_version_in_cache_hash():
    """Engine `version` field gets baked into cache keys, so a model upgrade
    invalidates stale audio. Sanity-check the field is set."""
    engines = get_engines()
    for name, e in engines.items():
        assert e.version, f"{name} engine missing version"


class _StubEngine(TTSEngine):
    name = "stub"
    pool = "local"
    version = "v1"
    available = True
    def list_voices(self): return []
    async def generate(self, text, voice_id, speed=1.0, params=None): return b""


def test_engine_abc_can_be_subclassed():
    e = _StubEngine()
    assert e.name == "stub" and e.available


def test_engine_unavailable_is_an_exception():
    err = EngineUnavailable("nope")
    assert isinstance(err, Exception)


def test_param_schemas_present():
    """Every engine exposes a PARAM_SCHEMA list (possibly empty) so the UI
    can render Advanced controls dynamically without hard-coded engine knowledge."""
    engines = get_engines()
    for name, e in engines.items():
        schema = type(e).PARAM_SCHEMA
        assert isinstance(schema, list), f"{name} PARAM_SCHEMA must be a list"


def test_orpheus_param_schema_shape():
    """Orpheus exposes the five sampler knobs mlx-audio's llama backend accepts."""
    from backend.engines.orpheus import OrpheusEngine
    schema = OrpheusEngine.PARAM_SCHEMA
    keys = {p["key"] for p in schema}
    assert keys == {
        "temperature", "top_p", "top_k",
        "repetition_penalty", "repetition_context_size",
    }
    for p in schema:
        assert {"key", "label", "type", "default"} <= p.keys()
        if p["type"] in ("int", "float"):
            assert "min" in p and "max" in p
