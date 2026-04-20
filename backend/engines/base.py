from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class EngineUnavailable(Exception):
    """Raised by engines that cannot start (missing dep, bad credentials, etc.)."""


class GenerationError(Exception):
    """Raised when a generation call fails."""


class VoiceMeta(BaseModel):
    id: str
    label: str
    gender: Literal["m", "f", "n"] | None = None
    accent: str | None = None
    notes: str | None = None


class TTSEngine(ABC):
    name: str
    pool: Literal["local", "cloud"] = "local"
    available: bool = False
    unavailable_reason: str | None = None
    version: str = "v1"  # bumped when the underlying model changes; goes into cache hash
    # Per-engine advanced-param schema consumed by the UI to render sliders.
    # Each entry: {key, label, type, min, max, step, default}.
    PARAM_SCHEMA: list[dict] = []

    @abstractmethod
    def list_voices(self) -> list[VoiceMeta]: ...

    @abstractmethod
    async def generate(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        params: dict | None = None,
    ) -> bytes:
        """Return WAV bytes."""
