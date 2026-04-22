from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db
from ..engines.registry import get_engines

router = APIRouter()


class VoiceNoteIn(BaseModel):
    notes: str | None = None


@router.get("/api/voices")
def list_voices() -> dict:
    user_notes = db.get_voice_notes()
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


@router.put("/api/voices/{engine}/{voice_id}/notes")
def put_voice_notes(engine: str, voice_id: str, body: VoiceNoteIn) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    db.upsert_voice_note(engine, voice_id, body.notes)
    return {"ok": True}
