from backend import db


def test_init_creates_tables_and_passages_crud():
    db.init_db()
    assert db.list_passages() == []
    pid = db.create_passage("title", "text", character_slot="ayanokoji",
                            emotion_tags=["<sigh>"])
    p = db.get_passage(pid)
    assert p["title"] == "title"
    assert p["character_slot"] == "ayanokoji"
    assert p["emotion_tags"] == ["<sigh>"]
    assert db.list_passages(slot="ayanokoji")[0]["id"] == pid
    assert db.list_passages(slot="other") == []


def test_results_dedupe_on_audio_hash():
    db.init_db()
    pid = db.create_passage("t", "x")
    a = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "h", 100)
    b = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "h", 100)
    assert a == b
    c = db.find_or_create_result(pid, "kokoro", "af_bella", 1.0, None, "h2", 100)
    assert c != a


def test_ratings_upsert():
    db.init_db()
    pid = db.create_passage("t", "x")
    rid = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "h", 100)
    db.upsert_rating(rid, 4, "good")
    r = db.get_result(rid)
    assert r["stars"] == 4 and r["notes"] == "good"
    db.upsert_rating(rid, 5, "better")
    r = db.get_result(rid)
    assert r["stars"] == 5 and r["notes"] == "better"


def test_ab_match_lifecycle():
    db.init_db()
    pid = db.create_passage("t", "x")
    a = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "ha", 100)
    b = db.find_or_create_result(pid, "kokoro", "af_bella", 1.0, None, "hb", 100)
    mid = db.create_ab_match(a, b)
    db.decide_ab_match(mid, "a")
    # No public read, but ensure no error and second decide overrides
    db.decide_ab_match(mid, "tie")


def test_casting_upsert_and_export_shape():
    db.init_db()
    pid = db.create_passage("t", "x", character_slot="ayanokoji")
    rid = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "h", 100)
    db.upsert_casting("ayanokoji", rid, "calm baseline")
    state = db.get_casting()
    assert state["ayanokoji"]["result_id"] == rid
    assert state["ayanokoji"]["notes"] == "calm baseline"


def test_delete_result_cleans_up_references():
    db.init_db()
    pid = db.create_passage("t", "x", character_slot="ayanokoji")
    a = db.find_or_create_result(pid, "kokoro", "af_heart", 1.0, None, "ha", 100)
    b = db.find_or_create_result(pid, "kokoro", "af_bella", 1.0, None, "hb", 100)
    db.upsert_rating(a, 4, "nice")
    db.upsert_casting("ayanokoji", a, "pick")
    mid = db.create_ab_match(a, b)
    db.decide_ab_match(mid, "a")

    audio_hash = db.delete_result(a)
    assert audio_hash == "ha"
    assert db.get_result(a) is None
    # ratings cascade, ab_matches hard-deleted, casting detached
    assert db.get_casting()["ayanokoji"]["result_id"] is None
    # The ab_match that referenced `a` is gone
    with db.connect() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM ab_matches WHERE result_a_id = ? OR result_b_id = ?",
            (a, a),
        ).fetchone()["n"]
    assert remaining == 0


def test_delete_missing_result_returns_none():
    db.init_db()
    assert db.delete_result(9999) is None


def test_count_results_with_hash():
    db.init_db()
    p1 = db.create_passage("t1", "x")
    p2 = db.create_passage("t2", "x")
    r1 = db.find_or_create_result(p1, "kokoro", "af_heart", 1.0, None, "shared", 100)
    r2 = db.find_or_create_result(p2, "kokoro", "af_heart", 1.0, None, "shared", 100)
    assert r1 != r2
    assert db.count_results_with_hash("shared") == 2
    db.delete_result(r1)
    assert db.count_results_with_hash("shared") == 1
    db.delete_result(r2)
    assert db.count_results_with_hash("shared") == 0
