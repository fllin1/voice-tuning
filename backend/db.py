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
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ab_matches (
    id INTEGER PRIMARY KEY,
    result_a_id INTEGER REFERENCES results(id),
    result_b_id INTEGER REFERENCES results(id),
    winner TEXT,
    decided_at INTEGER
);

CREATE TABLE IF NOT EXISTS casting (
    character_slot TEXT PRIMARY KEY,
    result_id INTEGER REFERENCES results(id),
    notes TEXT,
    updated_at INTEGER NOT NULL
);
"""


def init_db(db_path: Path | None = None) -> None:
    path = db_path or get_settings().db_path
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


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
            "SELECT r.*, ra.stars, ra.notes "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE r.id = ?",
            (result_id,),
        ).fetchone()
    return _result_row_to_dict(row) if row else None


def list_results_for_passage(passage_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE r.passage_id = ? ORDER BY r.id DESC",
            (passage_id,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def list_all_results(limit: int = 200) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes "
            "FROM results r LEFT JOIN ratings ra ON r.id = ra.result_id "
            "ORDER BY r.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def list_results_for_slot(slot: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.*, ra.stars, ra.notes, p.character_slot "
            "FROM results r "
            "JOIN passages p ON r.passage_id = p.id "
            "LEFT JOIN ratings ra ON r.id = ra.result_id "
            "WHERE p.character_slot = ? "
            "ORDER BY ra.stars DESC NULLS LAST, r.id DESC",
            (slot,),
        ).fetchall()
    return [_result_row_to_dict(r) for r in rows]


def delete_result(result_id: int) -> str | None:
    """Delete a result, detach casting + ab_matches references. Return its audio_hash."""
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
        conn.execute(
            "DELETE FROM ab_matches WHERE result_a_id = ? OR result_b_id = ?",
            (result_id, result_id),
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
    return d


# ---------- ratings ----------

def upsert_rating(result_id: int, stars: int | None, notes: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO ratings (result_id, stars, notes, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(result_id) DO UPDATE SET stars = excluded.stars, "
            "notes = excluded.notes, updated_at = excluded.updated_at",
            (result_id, stars, notes, now_ms()),
        )


# ---------- A/B matches ----------

def create_ab_match(result_a_id: int, result_b_id: int) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO ab_matches (result_a_id, result_b_id) VALUES (?, ?)",
            (result_a_id, result_b_id),
        )
        return cur.lastrowid


def decide_ab_match(match_id: int, winner: str) -> None:
    if winner not in {"a", "b", "tie"}:
        raise ValueError(f"invalid winner: {winner!r}")
    with connect() as conn:
        conn.execute(
            "UPDATE ab_matches SET winner = ?, decided_at = ? WHERE id = ?",
            (winner, now_ms(), match_id),
        )


# ---------- casting ----------

def get_casting() -> dict[str, dict | None]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM casting").fetchall()
    return {r["character_slot"]: dict(r) for r in rows}


def upsert_casting(slot: str, result_id: int | None, notes: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO casting (character_slot, result_id, notes, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(character_slot) DO UPDATE SET result_id = excluded.result_id, "
            "notes = excluded.notes, updated_at = excluded.updated_at",
            (slot, result_id, notes, now_ms()),
        )
