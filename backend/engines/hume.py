"""Hume Octave TTS via HTTP. Optional — gated by HUME_API_KEY env var.

Voices are fetched from the Hume voice library on first call and cached to
disk under ``audio_cache/.hume_voices.json`` so we don't re-fetch every run.
"""
import base64
import json

import httpx

from ..settings import get_settings
from .base import EngineUnavailable, GenerationError, TTSEngine, VoiceMeta

API_BASE = "https://api.hume.ai/v0"
DEFAULT_FORMAT = {"type": "wav"}

HUME_PARAM_SCHEMA: list[dict] = [
    {"key": "description", "label": "Description",
     "type": "string", "default": "",
     "placeholder": "Calm narration, slightly wistful…"},
    {"key": "num_generations", "label": "Num generations",
     "type": "int", "min": 1, "max": 5, "step": 1, "default": 1},
    {"key": "trailing_silence", "label": "Trailing silence (s)",
     "type": "float", "min": 0.0, "max": 2.0, "step": 0.05, "default": 0.0},
]


class HumeEngine(TTSEngine):
    name = "hume"
    pool = "cloud"
    version = "hume-octave-v1"
    PARAM_SCHEMA = HUME_PARAM_SCHEMA

    def __init__(self) -> None:
        s = get_settings()
        if not s.hume_api_key:
            raise EngineUnavailable("HUME_API_KEY not set")
        self._api_key = s.hume_api_key
        self._cache_path = s.audio_cache_dir / ".hume_voices.json"
        self._voices: list[VoiceMeta] | None = None

    def list_voices(self) -> list[VoiceMeta]:
        if self._voices is None:
            self._voices = self._load_voices()
        return list(self._voices)

    def _load_voices(self) -> list[VoiceMeta]:
        if self._cache_path.exists():
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            return [VoiceMeta(**v) for v in data]
        voices = self._fetch_voices()
        self._cache_path.write_text(
            json.dumps([v.model_dump() for v in voices], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return voices

    def _fetch_voices(self) -> list[VoiceMeta]:
        out: list[VoiceMeta] = []
        page = 0
        with httpx.Client(timeout=30.0) as client:
            while True:
                r = client.get(
                    f"{API_BASE}/tts/voices",
                    headers={"X-Hume-Api-Key": self._api_key},
                    params={"provider": "HUME_AI", "page_number": page, "page_size": 100},
                )
                r.raise_for_status()
                payload = r.json()
                page_items = payload.get("voices_page") or []
                for v in page_items:
                    out.append(VoiceMeta(
                        id=v["id"],
                        label=v.get("name") or v["id"],
                        notes=", ".join(v.get("compatible_octave_models") or []) or None,
                    ))
                if len(page_items) < 100:
                    break
                page += 1
        return out

    async def generate(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        params: dict | None = None,
    ) -> bytes:
        p = params or {}
        utterance: dict = {
            "text": text,
            "voice": {"id": voice_id, "provider": "HUME_AI"},
            "speed": speed,
        }
        description = p.get("description")
        if description:
            utterance["description"] = description
        trailing_silence = p.get("trailing_silence")
        if trailing_silence:
            utterance["trailing_silence"] = float(trailing_silence)
        num_generations = max(1, min(5, int(p.get("num_generations") or 1)))

        body = {
            "utterances": [utterance],
            "format": DEFAULT_FORMAT,
            "num_generations": num_generations,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{API_BASE}/tts",
                headers={"X-Hume-Api-Key": self._api_key},
                json=body,
            )
            if r.status_code != 200:
                raise GenerationError(f"Hume {r.status_code}: {r.text[:300]}")
            payload = r.json()
        gens = payload.get("generations") or []
        if not gens:
            raise GenerationError("Hume returned no generations")
        return base64.b64decode(gens[0]["audio"])
