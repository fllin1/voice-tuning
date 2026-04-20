from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db

router = APIRouter()


class PassageIn(BaseModel):
    title: str
    text: str
    character_slot: str | None = None
    emotion_tags: list[str] | None = None


@router.get("/api/passages")
def list_passages(slot: str | None = None) -> dict:
    return {"passages": db.list_passages(slot=slot)}


@router.get("/api/passages/{passage_id}")
def get_passage(passage_id: int) -> dict:
    p = db.get_passage(passage_id)
    if not p:
        raise HTTPException(404, "passage not found")
    return p


@router.post("/api/passages")
def create_passage(body: PassageIn) -> dict:
    pid = db.create_passage(
        title=body.title,
        text=body.text,
        character_slot=body.character_slot,
        emotion_tags=body.emotion_tags,
    )
    return {"id": pid}
