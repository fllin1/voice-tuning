"""Orpheus 3B via mlx-audio. Routes through mlx_audio.tts.models.llama.

Note: Orpheus does not have a `speed` parameter. The cache hash still varies by
speed (so the result row is stable), but speed adjustments are no-ops at the
engine level — apply post-processing if you need them.
"""
import asyncio
import io

import numpy as np
import soundfile as sf

from ..settings import get_settings
from .base import EngineUnavailable, GenerationError, TTSEngine, VoiceMeta

ORPHEUS_VOICES: list[VoiceMeta] = [
    VoiceMeta(id="tara", label="Tara", gender="f"),
    VoiceMeta(id="leah", label="Leah", gender="f"),
    VoiceMeta(id="jess", label="Jess", gender="f"),
    VoiceMeta(id="mia", label="Mia", gender="f"),
    VoiceMeta(id="zoe", label="Zoe", gender="f"),
    VoiceMeta(id="leo", label="Leo", gender="m"),
    VoiceMeta(id="dan", label="Dan", gender="m"),
    VoiceMeta(id="zac", label="Zac", gender="m"),
]
_VOICE_IDS = {v.id for v in ORPHEUS_VOICES}

EMOTION_TAGS = {"<laugh>", "<chuckle>", "<sigh>", "<gasp>"}

# mlx-audio's llama backend accepts these kwargs on generate(). Defaults mirror
# mlx_audio.tts.models.llama.llama.Model.generate() defaults.
ORPHEUS_PARAM_SCHEMA: list[dict] = [
    {"key": "temperature", "label": "Temperature",
     "type": "float", "min": 0.0, "max": 2.0, "step": 0.05, "default": 0.6},
    {"key": "top_p", "label": "Top-p",
     "type": "float", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.8},
    {"key": "top_k", "label": "Top-k",
     "type": "int", "min": 0, "max": 500, "step": 1, "default": 50},
    {"key": "repetition_penalty", "label": "Repetition penalty",
     "type": "float", "min": 1.0, "max": 2.0, "step": 0.01, "default": 1.3},
    {"key": "repetition_context_size", "label": "Repetition context",
     "type": "int", "min": 1, "max": 256, "step": 1, "default": 20},
]


class OrpheusEngine(TTSEngine):
    name = "orpheus"
    pool = "local"
    version = "orpheus-3b-v1"
    PARAM_SCHEMA = ORPHEUS_PARAM_SCHEMA

    def __init__(self) -> None:
        try:
            from mlx_audio.tts import load  # noqa: F401
        except ImportError as exc:
            raise EngineUnavailable(f"mlx-audio not importable: {exc}") from exc
        self._settings = get_settings()
        self._model = None

    def list_voices(self) -> list[VoiceMeta]:
        return list(ORPHEUS_VOICES)

    def _ensure_model(self) -> None:
        if self._model is None:
            from mlx_audio.tts import load
            self._model = load(self._settings.orpheus_repo)

    async def generate(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        params: dict | None = None,
    ) -> bytes:
        if voice_id not in _VOICE_IDS:
            raise GenerationError(f"unknown Orpheus voice: {voice_id!r}")
        prepared = self._inject_emotion(text, params)
        sampler = self._resolve_sampler(params)
        return await asyncio.to_thread(self._sync, prepared, voice_id, sampler)

    def _resolve_sampler(self, params: dict | None) -> dict:
        """Clamp provided sampler params to schema bounds; fill missing with defaults."""
        src = params or {}
        out: dict = {}
        for p in ORPHEUS_PARAM_SCHEMA:
            k = p["key"]
            v = src.get(k, p["default"])
            if p["type"] == "float":
                v = float(max(p["min"], min(p["max"], float(v))))
            elif p["type"] == "int":
                v = int(max(p["min"], min(p["max"], int(v))))
            out[k] = v
        return out

    def _inject_emotion(self, text: str, params: dict | None) -> str:
        """Append a model-supported emotion tag from params, if any.

        Pass `params={"emotion_tag": "<laugh>"}` to append, or just write the
        tag inline in the text — the model handles them either way.
        """
        if not params:
            return text
        tag = params.get("emotion_tag")
        if tag and tag in EMOTION_TAGS:
            return f"{text} {tag}"
        return text

    def _sync(self, text: str, voice: str, sampler: dict) -> bytes:
        self._ensure_model()
        chunks: list[np.ndarray] = []
        sample_rate = None
        for result in self._model.generate(
            text=text, voice=voice, max_tokens=2000, **sampler,
        ):
            chunks.append(np.array(result.audio))
            sample_rate = result.sample_rate
        if not chunks:
            raise GenerationError("Orpheus produced no audio")
        audio = np.concatenate(chunks).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
