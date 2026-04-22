from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import characters, db
from ..engines.registry import get_engines

router = APIRouter()


class VoiceNoteIn(BaseModel):
    notes: str | None = None


@router.get("/api/voices")
def list_voices(slot: str | None = None) -> dict:
    """List engines + voices. If slot is provided, include slot-scoped notes."""
    if slot is not None and not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    user_notes = db.get_voice_notes(slot) if slot else {}
    out = []
    for name, engine in get_engines().items():
        voices = []
        if engine.available:
            for v in engine.list_voices():
                d = v.model_dump()
                d["user_notes"] = user_notes.get((name, v.id), "")
                voices.append(d)
        out.append({
            "engine": name,
            "available": engine.available,
            "unavailable_reason": engine.unavailable_reason,
            "pool": engine.pool,
            "voices": voices,
            "param_schema": list(getattr(type(engine), "PARAM_SCHEMA", [])),
        })
    return {"engines": out}


@router.get("/api/voices/{engine}/{voice_id}/notes")
def get_voice_note(engine: str, voice_id: str, slot: str) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    notes = db.get_voice_notes(slot).get((engine, voice_id), "")
    return {"notes": notes}


@router.put("/api/voices/{engine}/{voice_id}/notes")
def put_voice_notes(engine: str, voice_id: str, slot: str, body: VoiceNoteIn) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    db.upsert_voice_note(engine, voice_id, slot, body.notes)
    return {"ok": True}
