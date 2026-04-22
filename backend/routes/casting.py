import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import characters, db

router = APIRouter()


class CastingIn(BaseModel):
    result_id: int | None = None
    notes: str | None = None
    reason: str | None = None


@router.get("/api/casting/slots")
def list_slots() -> dict:
    return {"slots": characters.as_dicts()}


@router.get("/api/casting/results/{slot}")
def list_results_for_slot(slot: str) -> dict:
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    rows = db.list_results_for_slot(slot)
    for r in rows:
        r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"
    return {"results": rows}


@router.get("/api/casting")
def list_casting() -> dict:
    state = db.get_casting()
    out = []
    for c in characters.CHARACTERS:
        entry = state.get(c.slot)
        result = db.get_result(entry["result_id"]) if entry and entry["result_id"] else None
        if result:
            result["audio_url"] = f"/api/audio/{result['audio_hash']}.wav"
        out.append({
            "slot": c.slot,
            "label": c.label,
            "portrait_key": c.portrait_key,
            "variant": c.variant,
            "result": result,
            "notes": entry["notes"] if entry else None,
        })
    return {"slots": out}


@router.put("/api/casting/{slot}")
def upsert_casting(slot: str, body: CastingIn) -> dict:
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    if body.result_id is not None and not db.get_result(body.result_id):
        raise HTTPException(404, "result not found")

    current = db.get_casting().get(slot)
    prev_result_id = current["result_id"] if current else None
    cast_changed = prev_result_id != body.result_id

    db.upsert_casting(slot, body.result_id, body.notes)
    if cast_changed:
        db.append_casting_history(slot, body.result_id, body.reason)
    return {"ok": True}


@router.get("/api/casting/history/{slot}")
def get_history(slot: str, limit: int = 3) -> dict:
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    return {"history": db.list_casting_history(slot, limit)}


@router.get("/api/casting/export")
def export_casting():
    state = db.get_casting()
    payload = {"exported_at": int(time.time()), "cast": []}
    for c in characters.CHARACTERS:
        entry = state.get(c.slot)
        result = db.get_result(entry["result_id"]) if entry and entry["result_id"] else None
        payload["cast"].append({
            "slot": c.slot,
            "label": c.label,
            "variant": c.variant,
            "engine": result["engine"] if result else None,
            "voice_id": result["voice_id"] if result else None,
            "speed": result["speed"] if result else None,
            "params": result["params"] if result else None,
            "notes": entry["notes"] if entry else None,
        })
    blob = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    fname = f"casting_{int(time.time())}.json"
    return Response(
        content=blob,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
