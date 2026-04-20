from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import cache, db
from ..engines.registry import get_engine, get_engines
from ..queue import get_manager

router = APIRouter()


class JobSpec(BaseModel):
    engine: str
    voice_id: str
    speed: float = 1.0
    params: dict | None = None


class GenerateRequest(BaseModel):
    passage_id: int | None = None
    text: str | None = None
    jobs: list[JobSpec] = Field(default_factory=list)


@router.post("/api/generate")
async def submit(req: GenerateRequest) -> dict:
    if not req.jobs:
        raise HTTPException(400, "no jobs")
    if not req.passage_id and not req.text:
        raise HTTPException(400, "either passage_id or text is required")

    if req.passage_id:
        p = db.get_passage(req.passage_id)
        if not p:
            raise HTTPException(404, "passage not found")
        text = p["text"]
    else:
        text = req.text or ""

    engines = get_engines()
    runners: list[tuple[str, callable]] = []
    for job in req.jobs:
        if job.engine not in engines or not engines[job.engine].available:
            raise HTTPException(400, f"engine unavailable: {job.engine}")
        runners.append((engines[job.engine].pool,
                        _build_runner(job, text, req.passage_id)))

    batch = get_manager().submit_batch(runners)
    return {"batch_id": batch.id, "job_ids": batch.job_ids}


def _build_runner(job: JobSpec, text: str, passage_id: int | None):
    async def runner() -> dict:
        engine = get_engine(job.engine)
        audio_hash = cache.compute_hash(
            engine_version=engine.version,
            voice_id=job.voice_id,
            speed=job.speed,
            params=job.params,
            text=text,
        )
        if not cache.has(audio_hash):
            wav_bytes = await engine.generate(
                text=text, voice_id=job.voice_id,
                speed=job.speed, params=job.params,
            )
            cache.write(audio_hash, wav_bytes)
        result_id = db.find_or_create_result(
            passage_id=passage_id,
            engine=job.engine,
            voice_id=job.voice_id,
            speed=job.speed,
            params=job.params,
            audio_hash=audio_hash,
            duration_ms=None,
        )
        return {
            "result_id": result_id,
            "audio_hash": audio_hash,
            "audio_url": f"/api/audio/{audio_hash}.wav",
        }
    return runner


@router.get("/api/generate/{job_id}")
def job_status(job_id: str) -> dict:
    j = get_manager().get_job(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    return {
        "id": j.id, "status": j.status,
        "result_id": j.result_id, "audio_hash": j.audio_hash,
        "audio_url": j.audio_url, "error": j.error,
    }


@router.get("/api/batch/{batch_id}")
def batch_status(batch_id: str) -> dict:
    b = get_manager().get_batch(batch_id)
    if not b:
        raise HTTPException(404, "batch not found")
    jobs = [get_manager().get_job(jid) for jid in b.job_ids]
    return {
        "batch_id": b.id,
        "jobs": [
            {
                "id": j.id, "status": j.status,
                "result_id": j.result_id, "audio_hash": j.audio_hash,
                "audio_url": j.audio_url, "error": j.error,
            }
            for j in jobs if j
        ],
    }


@router.get("/api/audio/{filename}")
def get_audio(filename: str):
    if not filename.endswith(".wav"):
        raise HTTPException(400, "only .wav supported")
    audio_hash = filename[:-4]
    if not cache.has(audio_hash):
        raise HTTPException(404, "audio not in cache")
    return FileResponse(cache.path_for(audio_hash), media_type="audio/wav")


@router.get("/api/results")
def list_results(limit: int = 200) -> dict:
    rows = db.list_all_results(limit=limit)
    for r in rows:
        r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"
    return {"results": rows}


@router.get("/api/results/{result_id}")
def get_result(result_id: int) -> dict:
    r = db.get_result(result_id)
    if not r:
        raise HTTPException(404, "result not found")
    r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"
    return r
