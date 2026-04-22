import hashlib
import json
from pathlib import Path

from .settings import get_settings


def compute_hash(
    engine_version: str,
    voice_id: str,
    speed: float,
    params: dict | None,
    text: str,
) -> str:
    payload = {
        "engine_version": engine_version,
        "voice_id": voice_id,
        "speed": round(speed, 4),
        "params": params or {},
        "text": text,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def path_for(audio_hash: str) -> Path:
    return get_settings().audio_cache_dir / f"{audio_hash}.wav"


def has(audio_hash: str) -> bool:
    return path_for(audio_hash).exists()


def write(audio_hash: str, wav_bytes: bytes) -> Path:
    p = path_for(audio_hash)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(wav_bytes)
    return p


def read(audio_hash: str) -> bytes:
    return path_for(audio_hash).read_bytes()


def delete(audio_hash: str) -> bool:
    p = path_for(audio_hash)
    if p.exists():
        p.unlink()
        return True
    return False
