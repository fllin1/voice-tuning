from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import characters, db

router = APIRouter()


class ToggleIn(BaseModel):
    slot: str
    result_id: int


@router.get("/api/shortlist/{slot}")
def list_for_slot(slot: str) -> dict:
    if not characters.is_valid_slot(slot):
        raise HTTPException(400, f"unknown slot: {slot}")
    rows = db.list_shortlist(slot)
    for r in rows:
        r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"
    return {"shortlist": rows}


@router.post("/api/shortlist/toggle")
def toggle(body: ToggleIn) -> dict:
    if not characters.is_valid_slot(body.slot):
        raise HTTPException(400, f"unknown slot: {body.slot}")
    if not db.get_result(body.result_id):
        raise HTTPException(404, "result not found")
    shortlisted = db.toggle_shortlist(body.slot, body.result_id)
    return {"shortlisted": shortlisted}
