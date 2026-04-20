from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db

router = APIRouter()


class StartIn(BaseModel):
    result_a_id: int
    result_b_id: int


class DecideIn(BaseModel):
    match_id: int
    winner: str  # 'a' | 'b' | 'tie'


@router.post("/api/ab/start")
def start(body: StartIn) -> dict:
    if not db.get_result(body.result_a_id) or not db.get_result(body.result_b_id):
        raise HTTPException(404, "result not found")
    match_id = db.create_ab_match(body.result_a_id, body.result_b_id)
    return {"match_id": match_id}


@router.post("/api/ab/decide")
def decide(body: DecideIn) -> dict:
    if body.winner not in {"a", "b", "tie"}:
        raise HTTPException(400, "winner must be 'a', 'b', or 'tie'")
    db.decide_ab_match(body.match_id, body.winner)
    return {"ok": True}
