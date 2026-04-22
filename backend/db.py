import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .settings import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS passages (
    id INTEGER PRIMARY KEY,
    character_slot TEXT,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    emotion_tags TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    passage_id INTEGER REFERENCES passages(id),
    engine TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    speed REAL NOT NULL,
    params_json TEXT,
    audio_hash TEXT NOT NULL,
    duration_ms INTEGER,
    generated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_audio_hash ON results(audio_hash);
CREATE INDEX IF NOT EXISTS idx_results_passage ON results(passage_id);

CREATE TABLE IF NOT EXISTS ratings (
    result_id INTEGER PRIMARY KEY REFERENCES results(id) ON DELETE CASCADE,
    stars INTEGER CHECK(stars BETWEEN 1 AND 5),
    notes TEXT,
    tags TEXT,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS casting (
    character_slot TEXT PRIMARY KEY,
    result_id INTEGER REFERENCES results(id),
    notes TEXT,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_notes (
    engine TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    slot TEXT NOT NULL,
    notes TEXT,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (engine, voice_id, slot)
);

CREATE TABLE IF NOT EXISTS shortlist (
    slot TEXT NOT NULL,
    result_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    rank INTEGER,
    added_at INTEGER NOT NULL,
    PRIMARY KEY (slot, result_id)
);
CREATE INDEX IF NOT EXISTS idx_shortlist_slot ON shortlist(slot);

CREATE TABLE IF NOT EXISTS casting_history (
    id INTEGER PRIMARY KEY,
    slot TEXT NOT NULL,
    result_id INTEGER REFERENCES results(id) ON DELETE SET NULL,
    changed_at INTEGER NOT NULL,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_casting_history_slot
    ON casting_history(slot, changed_at DESC);
"""


def init_db(db_path: Path | None = None) -> None:
    path = db_path or get_settings().db_path
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    _migrate(db_path)


def _migrate(db_path: Path | None = None) -> None:
    """Apply versioned migrations, idempotent (guarded by PRAGMA user_version)."""
    path = db_path or get_settings().db_path
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        (ver,) = conn.execute("PRAGMA user_version").fetchone()
        if ver < 2:
            _migrate_v2(conn)
            conn.execute("PRAGMA user_version = 2")
        conn.commit()


def _migrate_v2(conn: sqlite3.Connection) -> None:
    # Drop A/B testing (scrapped — personal tool, no multi-evaluator scope).
    conn.execute("DROP TABLE IF EXISTS ab_matches")

    # Tags on ratings (JSON array, nullable).
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(ratings)").fetchall()]
    if "tags" not in cols:
        conn.execute("ALTER TABLE ratings ADD COLUMN tags TEXT")

    # Shortlist per slot.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS shortlist ("
        "  slot TEXT NOT NULL,"
        "  result_id INTEGER NOT NULL REFERENCES results(id) ON DELETE CASCADE,"
        "  rank INTEGER,"
        "  added_at INTEGER NOT NULL,"
        "  PRIMARY KEY (slot, result_id)"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shortlist_slot ON shortlist(slot)")

    # Casting swap history.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS casting_history ("
        "  id INTEGER PRIMARY KEY,"
        "  slot TEXT NOT NULL,"
        "  result_id INTEGER REFERENCES results(id) ON DELETE SET NULL,"
        "  changed_at INTEGER NOT NULL,"
        "  reason TEXT"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_casting_history_slot "
        "ON casting_history(slot, changed_at DESC)"
    )

    # voice_notes: PK change (engine, voice_id) → (engine, voice_id, slot).
    # Fan existing rows across all 8 slots so the current note stays visible
    # per-character; from here on, edits diverge per slot.
    vn_cols = [r["name"] for r in conn.execute("PRAGMA table_info(voice_notes)").fetchall()]
    if "slot" not in vn_cols:
        conn.execute(
            "CREATE TABLE voice_notes_new ("
            "  engine TEXT NOT NULL,"
            "  voice_id TEXT NOT NULL,"
            "  slot TEXT NOT NULL,"
            "  notes TEXT,"
            "  updated_at INTEGER NOT NULL,"
            "  PRIMARY KEY (engine, voice_id, slot)"
            ")"
        )
        slot_union = " UNION ALL ".join(f"SELECT '{s}' AS slot" for s in SLOTS)
        conn.execute(
            "INSERT OR IGNORE INTO voice_notes_new "
            "(engine, voice_id, slot, notes, updated_at) "
            "SELECT vn.engine, vn.voice_id, s.slot, vn.notes, vn.updated_at "
            f"FROM voice_notes vn CROSS JOIN ({slot_union}) s"
        )
        conn.execute("DROP TABLE voice_notes")
        conn.execute("ALTER TABLE voice_notes_new RENAME TO voice_notes")


# Character slot order (matches casting presentation order).
SLOTS = [
    "ayanokoji", "horikita",
    "kushida_public", "kushida_private",
    "karuizawa", "ichinose",
    "sakayanagi", "ryuen",
]


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = get_settings().db_path
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------- passages ----------

def list_passages(slot: str | None = None) -> list[dict]:
    with connect() as conn:
        if slot:
            rows = conn.execute(
                "SELECT * FROM passages WHERE character_slot = ? ORDER BY id",
                (slot,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM passages ORDER BY id").fetchall()
    return [_passage_row_to_dict(r) for r in rows]


def get_passage(passage_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM passages WHERE id = ?", (passage_id,)).fetchone()
    return _passage_row_to_dict(row) if row else None


def create_passage(
    title: str, text: str, character_slot: str | None = None,
    emotion_tags: list[str] | None = None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO passages (character_slot, title, text, emotion_tags, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (character_slot, title, text,
             json.dumps(emotion_tags) if emotion_tags else None,
             now_ms()),
        )
        return cur.lastrowid


def _passage_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["emotion_tags"] = json.loads(d["emotion_tags"]) if d.get("emotion_tags") else []
    return d


# ---------- results ----------

def find_or_create_result(
    passage_id: int | None,
    engine: str,
    voice_id: str,
    speed: float,
    params: dict | None,
    audio_hash: str,
    duration_ms: int | None,
) -> int:
    """Reuse an existing row pointing at the same audio_hash if present, else insert."""
    params_json = json.dumps(params) if params else None
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM results WHERE audio_hash = ? AND engine = ? "
            "AND voice_id = ? AND speed = ? "
            "AND COALESCE(params_json, '') = COALESCE(?, '') "
            "AND COALESCE(passage_id, -1) = COALESCE(?, -1) "
            "ORDER BY id LIMIT 1",
            (audio_hash, engine, voice_id, speed, params_json, passage_id),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO results "
            "(passage_id, engine, voice_id, speed, params_json, audio_hash, duration_ms, generated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (passage_id, engine, voice_id, speed, params_json, audio_hash,
             duration_ms, now_ms()),
        )
        return cur.lastrowid


def get_result(result_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, ra.tags "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE r.id = ?",
            (result_id,),
        ).fetchone()
    return _result_row_to_dict(row) if row else None


def list_results_for_passage(passage_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, ra.tags "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE r.passage_id = ? ORDER BY r.id DESC",
            (passage_id,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def list_all_results(limit: int = 200) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, ra.tags "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "ORDER BY r.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def list_results_for_slot(slot: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, ra.tags, p.character_slot "
            "FROM results r "
            "JOIN passages p ON r.passage_id = p.id "
            "LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE p.character_slot = ? "
            "ORDER BY ra.stars DESC NULLS LAST, r.id DESC",
            (slot,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def delete_result(result_id: int) -> str | None:
    """Delete a result, detach casting reference. Return its audio_hash."""
    with connect() as conn:
        row = conn.execute(
            "SELECT audio_hash FROM results WHERE id = ?", (result_id,)
        ).fetchone()
        if not row:
            return None
        audio_hash = row["audio_hash"]
        conn.execute(
            "UPDATE casting SET result_id = NULL, updated_at = ? WHERE result_id = ?",
            (now_ms(), result_id),
        )
        conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
    return audio_hash


def count_results_with_hash(audio_hash: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM results WHERE audio_hash = ?", (audio_hash,)
        ).fetchone()
    return row["n"]


def _result_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["params"] = json.loads(d["params_json"]) if d.get("params_json") else {}
    d.pop("params_json", None)
    if "tags" in d:
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    return d


# ---------- ratings ----------

def upsert_rating(
    result_id: int,
    stars: int | None,
    notes: str | None,
    tags: list[str] | None = None,
) -> None:
    tags_json = json.dumps(tags) if tags else None
    with connect() as conn:
        conn.execute(
            "INSERT INTO ratings (result_id, stars, notes, tags, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(result_id) DO UPDATE SET stars = excluded.stars, "
            "notes = excluded.notes, tags = excluded.tags, "
            "updated_at = excluded.updated_at",
            (result_id, stars, notes, tags_json, now_ms()),
        )


# ---------- casting ----------

def get_casting() -> dict[str, dict | None]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM casting").fetchall()
    return {r["character_slot"]: dict(r) for r in rows}


# ---------- voice notes (slot-scoped) ----------

def get_voice_notes(slot: str | None = None) -> dict[tuple[str, str], str]:
    """Return user notes keyed by (engine, voice_id) for one slot.

    Notes are slot-scoped — the same voice can carry different notes per
    character it's auditioning for. Pass None to return {} (no meaningful
    cross-slot view).
    """
    if slot is None:
        return {}
    with connect() as conn:
        rows = conn.execute(
            "SELECT engine, voice_id, notes FROM voice_notes WHERE slot = ?",
            (slot,),
        ).fetchall()
    return {(r["engine"], r["voice_id"]): r["notes"] for r in rows if r["notes"]}


def upsert_voice_note(engine: str, voice_id: str, slot: str, notes: str | None) -> None:
    with connect() as conn:
        if not notes:
            conn.execute(
                "DELETE FROM voice_notes WHERE engine = ? AND voice_id = ? AND slot = ?",
                (engine, voice_id, slot),
            )
            return
        conn.execute(
            "INSERT INTO voice_notes (engine, voice_id, slot, notes, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(engine, voice_id, slot) DO UPDATE SET "
            "notes = excluded.notes, updated_at = excluded.updated_at",
            (engine, voice_id, slot, notes, now_ms()),
        )


def upsert_casting(slot: str, result_id: int | None, notes: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO casting (character_slot, result_id, notes, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(character_slot) DO UPDATE SET result_id = excluded.result_id, "
            "notes = excluded.notes, updated_at = excluded.updated_at",
            (slot, result_id, notes, now_ms()),
        )


# ---------- shortlist ----------

def list_shortlist(slot: str) -> list[dict]:
    """Return shortlisted candidates for a slot, joined with rating fields."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, ra.tags, s.rank, s.added_at AS shortlisted_at "
            "FROM shortlist s "
            "JOIN results r ON s.result_id = r.id "
            "LEFT JOIN ratings ra ON ra.result_id = r.id "
            "WHERE s.slot = ? "
            "ORDER BY s.rank IS NULL, s.rank, s.added_at DESC",
            (slot,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def toggle_shortlist(slot: str, result_id: int) -> bool:
    """Add or remove a result from a slot's shortlist. Returns the new state."""
    with connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM shortlist WHERE slot = ? AND result_id = ?",
            (slot, result_id),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM shortlist WHERE slot = ? AND result_id = ?",
                (slot, result_id),
            )
            return False
        conn.execute(
            "INSERT INTO shortlist (slot, result_id, rank, added_at) "
            "VALUES (?, ?, NULL, ?)",
            (slot, result_id, now_ms()),
        )
        return True


# ---------- casting history ----------

def append_casting_history(
    slot: str, result_id: int | None, reason: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO casting_history (slot, result_id, changed_at, reason) "
            "VALUES (?, ?, ?, ?)",
            (slot, result_id, now_ms(), reason),
        )


def list_casting_history(slot: str, limit: int = 3) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT ch.id, ch.slot, ch.result_id, ch.changed_at, ch.reason, "
            "       r.engine, r.voice_id "
            "FROM casting_history ch "
            "LEFT JOIN results r ON ch.result_id = r.id "
            "WHERE ch.slot = ? "
            "ORDER BY ch.changed_at DESC LIMIT ?",
            (slot, limit),
        ).fetchall()
    return [dict(r) for r in rows]
