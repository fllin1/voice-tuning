import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import db

router = APIRouter()

# 8 voice slots for Classroom of the Elite
COTE_SLOTS = [
    {"slot": "ayanokoji", "label": "Ayanokōji Kiyotaka"},
    {"slot": "horikita", "label": "Horikita Suzune"},
    {"slot": "kushida_public", "label": "Kushida Kikyō (public)"},
    {"slot": "kushida_private", "label": "Kushida Kikyō (private)"},
    {"slot": "karuizawa", "label": "Karuizawa Kei"},
    {"slot": "ichinose", "label": "Ichinose Honami"},
    {"slot": "sakayanagi", "label": "Sakayanagi Arisu"},
    {"slot": "ryuen", "label": "Ryūen Kakeru"},
]


class CastingIn(BaseModel):
    result_id: int | None = None
    notes: str | None = None


@router.get("/api/casting/slots")
def list_slots() -> dict:
    return {"slots": COTE_SLOTS}


@router.get("/api/casting/results/{slot}")
def list_results_for_slot(slot: str) -> dict:
    if slot not in {s["slot"] for s in COTE_SLOTS}:
        raise HTTPException(400, f"unknown slot: {slot}")
    rows = db.list_results_for_slot(slot)
    for r in rows:
        r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"
    return {"results": rows}


@router.get("/api/casting")
def list_casting() -> dict:
    state = db.get_casting()
    out = []
    for slot in COTE_SLOTS:
        entry = state.get(slot["slot"])
        result = db.get_result(entry["result_id"]) if entry and entry["result_id"] else None
        if result:
            result["audio_url"] = f"/api/audio/{result['audio_hash']}.wav"
        out.append({**slot, "result": result, "notes": entry["notes"] if entry else None})
    return {"slots": out}


@router.put("/api/casting/{slot}")
def upsert_casting(slot: str, body: CastingIn) -> dict:
    if slot not in {s["slot"] for s in COTE_SLOTS}:
        raise HTTPException(400, f"unknown slot: {slot}")
    if body.result_id is not None and not db.get_result(body.result_id):
        raise HTTPException(404, "result not found")
    db.upsert_casting(slot, body.result_id, body.notes)
    return {"ok": True}


@router.get("/api/casting/export")
def export_casting():
    state = db.get_casting()
    payload = {"exported_at": int(time.time()), "cast": []}
    for slot in COTE_SLOTS:
        entry = state.get(slot["slot"])
        result = db.get_result(entry["result_id"]) if entry and entry["result_id"] else None
        payload["cast"].append({
            "slot": slot["slot"],
            "label": slot["label"],
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
