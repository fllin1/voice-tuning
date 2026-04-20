from fastapi import APIRouter

from ..engines.registry import get_engines

router = APIRouter()


@router.get("/api/voices")
def list_voices() -> dict:
    out = []
    for name, engine in get_engines().items():
        out.append({
            "engine": name,
            "available": engine.available,
            "unavailable_reason": engine.unavailable_reason,
            "pool": engine.pool,
            "voices": [v.model_dump() for v in engine.list_voices()] if engine.available else [],
            "param_schema": list(getattr(type(engine), "PARAM_SCHEMA", [])),
        })
    return {"engines": out}
