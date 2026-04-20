from backend import cache


def test_hash_is_deterministic():
    h1 = cache.compute_hash("v1", "af_heart", 1.0, {"k": 1}, "Hello")
    h2 = cache.compute_hash("v1", "af_heart", 1.0, {"k": 1}, "Hello")
    assert h1 == h2 and len(h1) == 64


def test_hash_changes_with_each_field():
    base = cache.compute_hash("v1", "af_heart", 1.0, None, "Hello")
    assert cache.compute_hash("v2", "af_heart", 1.0, None, "Hello") != base
    assert cache.compute_hash("v1", "af_bella", 1.0, None, "Hello") != base
    assert cache.compute_hash("v1", "af_heart", 1.1, None, "Hello") != base
    assert cache.compute_hash("v1", "af_heart", 1.0, {"x": 1}, "Hello") != base
    assert cache.compute_hash("v1", "af_heart", 1.0, None, "World") != base


def test_write_has_read_roundtrip():
    h = cache.compute_hash("v1", "af_heart", 1.0, None, "Hello")
    assert not cache.has(h)
    cache.write(h, b"RIFF...fake wav...")
    assert cache.has(h)
    assert cache.read(h) == b"RIFF...fake wav..."
    assert cache.path_for(h).suffix == ".wav"
