"""Bounded async job runner.

One semaphore per pool: local engines share a single slot (Apple GPU contention),
cloud engines (Hume) share a wider pool. Each job stores status + result so the
HTMX poll endpoint can surface progress.
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Literal

from .settings import get_settings


JobStatus = Literal["queued", "running", "done", "failed"]


@dataclass
class Job:
    id: str
    status: JobStatus = "queued"
    result_id: int | None = None
    audio_hash: str | None = None
    audio_url: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class Batch:
    id: str
    job_ids: list[str]


class JobManager:
    def __init__(self) -> None:
        s = get_settings()
        self._local_sem = asyncio.Semaphore(s.local_concurrency)
        self._cloud_sem = asyncio.Semaphore(s.cloud_concurrency)
        self._jobs: dict[str, Job] = {}
        self._batches: dict[str, Batch] = {}

    def submit_batch(
        self,
        runners: list[tuple[str, Callable[[], Awaitable[dict]]]],
    ) -> Batch:
        """Submit a batch of (pool, async-fn) tuples.

        pool: 'local' or 'cloud' — selects which semaphore guards execution.
        runner: async callable returning {result_id, audio_hash, audio_url}.
        """
        batch_id = uuid.uuid4().hex
        job_ids: list[str] = []
        for pool, runner in runners:
            job = Job(id=uuid.uuid4().hex)
            self._jobs[job.id] = job
            job_ids.append(job.id)
            asyncio.create_task(self._run(pool, job, runner))
        batch = Batch(id=batch_id, job_ids=job_ids)
        self._batches[batch.id] = batch
        return batch

    async def _run(
        self, pool: str, job: Job, runner: Callable[[], Awaitable[dict]],
    ) -> None:
        sem = self._local_sem if pool == "local" else self._cloud_sem
        async with sem:
            job.status = "running"
            try:
                out = await runner()
            except Exception as exc:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                return
        job.result_id = out.get("result_id")
        job.audio_hash = out.get("audio_hash")
        job.audio_url = out.get("audio_url")
        job.status = "done"

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def get_batch(self, batch_id: str) -> Batch | None:
        return self._batches.get(batch_id)


_manager: JobManager | None = None


def get_manager() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
