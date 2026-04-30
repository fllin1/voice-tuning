from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import characters, db
from ..engines.registry import get_engines

router = APIRouter()


class VoiceNoteIn(BaseModel):
    # Partial-update semantics: only fields listed in `model_fields_set`
    # are written; unspecified fields preserve their existing DB value.
    params_fp: str = ""
    notes: str | None = None
    stars: int | None = None
    playback_speed: float | None = None


class VoiceProfileIn(BaseModel):
    description: str | None = None
    sample_result_id: int | None = None
    traits: list[str] | None = None


@router.get("/api/voices")
def list_voices(slot: str | None = None) -> dict:
    """List engines + voices. If slot is provided, include slot-scoped notes."""
    if slot is not None and not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    notes_map = db.get_voice_notes(slot) if slot else {}
    # Flatten: default bucket (params_fp="") feeds the legacy user_notes field.
    flat_default = {
        (e, v): row.get("notes") or ""
        for (e, v, fp), row in notes_map.items()
        if fp == ""
    }
    out = []
    for name, engine in get_engines().items():
        voices = []
        if engine.available:
            for v in engine.list_voices():
                d = v.model_dump()
                d["user_notes"] = flat_default.get((name, v.id), "")
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
def get_voice_note(engine: str, voice_id: str, slot: str, params_fp: str = "") -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    row = db.get_voice_notes(slot).get((engine, voice_id, params_fp)) or {}
    return {
        "notes": row.get("notes"),
        "stars": row.get("stars"),
        "playback_speed": row.get("playback_speed"),
    }


@router.put("/api/voices/{engine}/{voice_id}/notes")
def put_voice_notes(engine: str, voice_id: str, slot: str, body: VoiceNoteIn) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    provided = set(body.model_fields_set)
    kwargs = {}
    if "notes" in provided:
        kwargs["notes"] = body.notes
    if "stars" in provided:
        kwargs["stars"] = body.stars
    if "playback_speed" in provided:
        ps = body.playback_speed
        if ps is not None and not (0.5 <= ps <= 2.0):
            raise HTTPException(400, "playback_speed must be between 0.5 and 2.0")
        kwargs["playback_speed"] = ps
    db.upsert_voice_note(engine, voice_id, slot, body.params_fp, **kwargs)
    return {"ok": True}


@router.get("/api/voices/{engine}/{voice_id}/profile")
def get_voice_profile(engine: str, voice_id: str) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    profile = db.get_voice_profile(engine, voice_id) or {
        "description": None,
        "sample_result_id": None,
        "traits": [],
    }
    return {
        "description": profile.get("description"),
        "sample_result_id": profile.get("sample_result_id"),
        "traits": profile.get("traits") or [],
    }


@router.put("/api/voices/{engine}/{voice_id}/profile")
def put_voice_profile(engine: str, voice_id: str, body: VoiceProfileIn) -> dict:
    engines = get_engines()
    if engine not in engines:
        raise HTTPException(404, "engine not found")
    db.upsert_voice_profile(
        engine, voice_id,
        description=body.description,
        sample_result_id=body.sample_result_id,
        traits=body.traits,
    )
    return {"ok": True}
