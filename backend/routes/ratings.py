from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db

router = APIRouter()


class RatingIn(BaseModel):
    stars: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


@router.put("/api/ratings/{result_id}")
def upsert_rating(result_id: int, body: RatingIn) -> dict:
    if not db.get_result(result_id):
        raise HTTPException(404, "result not found")
    db.upsert_rating(result_id, body.stars, body.notes)
    return {"ok": True}
