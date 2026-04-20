"""Kokoro-82M via mlx-audio. Lazy-loads the model on first generate()."""
import asyncio
import io

import numpy as np
import soundfile as sf

from ..settings import get_settings
from .base import EngineUnavailable, GenerationError, TTSEngine, VoiceMeta

# Canonical voice list from the Kokoro release. Each is a separate .safetensors
# pack in the model repo, lazily downloaded by mlx-audio.
KOKORO_VOICES: list[VoiceMeta] = [
    VoiceMeta(id="af_heart", label="Heart (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_bella", label="Bella (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_nicole", label="Nicole (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_kore", label="Kore (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_sarah", label="Sarah (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_sky", label="Sky (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_nova", label="Nova (US, F)", gender="f", accent="us"),
    VoiceMeta(id="af_aoede", label="Aoede (US, F)", gender="f", accent="us"),
    VoiceMeta(id="am_michael", label="Michael (US, M)", gender="m", accent="us"),
    VoiceMeta(id="am_fenrir", label="Fenrir (US, M)", gender="m", accent="us"),
    VoiceMeta(id="am_onyx", label="Onyx (US, M)", gender="m", accent="us"),
    VoiceMeta(id="am_puck", label="Puck (US, M)", gender="m", accent="us"),
    VoiceMeta(id="am_adam", label="Adam (US, M)", gender="m", accent="us"),
    VoiceMeta(id="bf_emma", label="Emma (UK, F)", gender="f", accent="uk"),
    VoiceMeta(id="bf_isabella", label="Isabella (UK, F)", gender="f", accent="uk"),
    VoiceMeta(id="bf_alice", label="Alice (UK, F)", gender="f", accent="uk"),
    VoiceMeta(id="bf_lily", label="Lily (UK, F)", gender="f", accent="uk"),
    VoiceMeta(id="bm_george", label="George (UK, M)", gender="m", accent="uk"),
    VoiceMeta(id="bm_daniel", label="Daniel (UK, M)", gender="m", accent="uk"),
    VoiceMeta(id="bm_fable", label="Fable (UK, M)", gender="m", accent="uk"),
]

_VOICE_IDS = {v.id for v in KOKORO_VOICES}


class KokoroEngine(TTSEngine):
    name = "kokoro"
    pool = "local"
    version = "kokoro-82m-v1"
    # Kokoro is non-autoregressive — no sampler knobs. Speed is a top-level arg.
    PARAM_SCHEMA: list[dict] = []

    def __init__(self) -> None:
        try:
            from mlx_audio.tts import load  # noqa: F401
        except ImportError as exc:
            raise EngineUnavailable(f"mlx-audio not importable: {exc}") from exc
        self._settings = get_settings()
        self._model = None
        self._lang_code = "a"  # 'a' = American English in mlx-audio Kokoro pipeline

    def list_voices(self) -> list[VoiceMeta]:
        return list(KOKORO_VOICES)

    def _ensure_model(self) -> None:
        if self._model is None:
            from mlx_audio.tts import load
            self._model = load(self._settings.kokoro_repo)

    def _resolve_voice(self, voice_id: str) -> str:
        """Validate a single voice id or comma-separated blend.

        mlx-audio supports comma-separated blends with equal weighting (averaged).
        Weighted-blend syntax (`af_nicole:70,am_fenrir:30`) is parsed but currently
        falls back to equal-weight averaging — proper weighted blending is a v2 task.
        """
        parts = [p.strip() for p in voice_id.split(",")]
        clean = []
        for p in parts:
            base = p.split(":", 1)[0]
            if base not in _VOICE_IDS:
                raise GenerationError(f"unknown Kokoro voice: {base!r}")
            clean.append(base)
        return ",".join(clean)

    async def generate(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        params: dict | None = None,
    ) -> bytes:
        voice = self._resolve_voice(voice_id)
        return await asyncio.to_thread(self._generate_sync, text, voice, speed)

    def _generate_sync(self, text: str, voice: str, speed: float) -> bytes:
        self._ensure_model()
        chunks: list[np.ndarray] = []
        sample_rate = None
        for result in self._model.generate(
            text=text, voice=voice, speed=speed, lang_code=self._lang_code,
        ):
            chunks.append(np.array(result.audio))
            sample_rate = result.sample_rate
        if not chunks:
            raise GenerationError("Kokoro produced no audio")
        audio = np.concatenate(chunks).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()
