"""Engine discovery. Probes each engine; failures mark it unavailable, not crash."""
from .base import EngineUnavailable, TTSEngine
from .hume import HumeEngine
from .kokoro import KokoroEngine
from .orpheus import OrpheusEngine

_engines: dict[str, TTSEngine] | None = None


def _probe(cls: type[TTSEngine]) -> TTSEngine:
    try:
        engine = cls()
        engine.available = True
        engine.unavailable_reason = None
    except EngineUnavailable as exc:
        engine = cls.__new__(cls)
        engine.name = cls.name if hasattr(cls, "name") else cls.__name__.lower()
        engine.available = False
        engine.unavailable_reason = str(exc)
    return engine


def get_engines() -> dict[str, TTSEngine]:
    global _engines
    if _engines is None:
        _engines = {
            "kokoro": _probe(KokoroEngine),
            "orpheus": _probe(OrpheusEngine),
            "hume": _probe(HumeEngine),
        }
    return _engines


def get_engine(name: str) -> TTSEngine:
    engines = get_engines()
    if name not in engines:
        raise KeyError(f"unknown engine: {name}")
    eng = engines[name]
    if not eng.available:
        raise EngineUnavailable(f"{name}: {eng.unavailable_reason}")
    return eng
