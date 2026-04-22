from fastapi.testclient import TestClient

from backend import cache, db
from backend.main import app


def _seed(audio_hash: str, passage_title: str = "t") -> tuple[int, int]:
    pid = db.create_passage(passage_title, "x")
    rid = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, audio_hash, 100)
    cache.write(audio_hash, b"wav-bytes")
    return pid, rid


def test_delete_result_removes_row_and_audio_when_last_reference():
    db.init_db()
    _, rid = _seed("only-ref")
    c = TestClient(app)
    r = c.delete(f"/api/results/{rid}")
    assert r.status_code == 200
    assert r.json() == {"deleted": True, "audio_removed": True}
    assert db.get_result(rid) is None
    assert not cache.has("only-ref")


def test_delete_result_keeps_audio_when_other_rows_reference_it():
    db.init_db()
    _, rid_a = _seed("shared-ref", passage_title="t1")
    _, rid_b = _seed("shared-ref", passage_title="t2")
    assert rid_a != rid_b
    c = TestClient(app)
    r = c.delete(f"/api/results/{rid_a}")
    assert r.status_code == 200
    assert r.json() == {"deleted": True, "audio_removed": False}
    assert cache.has("shared-ref")
    # Second delete should now unlink the WAV
    r = c.delete(f"/api/results/{rid_b}")
    assert r.json() == {"deleted": True, "audio_removed": True}
    assert not cache.has("shared-ref")


def test_delete_missing_result_returns_404():
    db.init_db()
    c = TestClient(app)
    r = c.delete("/api/results/99999")
    assert r.status_code == 404
