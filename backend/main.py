import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import characters, db, voice_descriptions
from .engines.registry import get_engines
from .routes import casting, generate, passages, ratings, shortlist, voices

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "backend" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _seed_passages()
    _seed_voice_profiles()
    for name, eng in get_engines().items():
        if not eng.available:
            print(f"[engine:{name}] disabled — {eng.unavailable_reason}")
        else:
            print(f"[engine:{name}] available")
    yield


app = FastAPI(title="Voice-Tuning", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

app.include_router(voices.router)
app.include_router(passages.router)
app.include_router(generate.router)
app.include_router(ratings.router)
app.include_router(casting.router)
app.include_router(shortlist.router)


def _seed_passages() -> None:
    """Load data/passages.json into the DB if the table is empty."""
    existing = db.list_passages()
    if existing:
        return
    src = ROOT / "data" / "passages.json"
    if not src.exists():
        return
    items = json.loads(src.read_text(encoding="utf-8"))
    for item in items:
        db.create_passage(
            title=item["title"],
            text=item["text"],
            character_slot=item.get("slot"),
            emotion_tags=item.get("emotion_tags"),
        )


def _seed_voice_profiles() -> None:
    """Fill missing description/traits from curated voice_descriptions.

    Never overwrites user-edited descriptions — only upserts when the
    existing row has no description (or no row exists). Traits from
    curation are applied when the row's traits list is empty.
    """
    existing = db.list_voice_profiles()
    for name, eng in get_engines().items():
        if not eng.available:
            continue
        for v in eng.list_voices():
            info = voice_descriptions.lookup(name, v.model_dump())
            if not info:
                continue
            key = f"{name}|{v.id}"
            prev = existing.get(key) or {}
            has_desc = bool((prev.get("description") or "").strip())
            has_traits = bool(prev.get("traits"))
            if has_desc and has_traits:
                continue
            db.upsert_voice_profile(
                engine=name,
                voice_id=v.id,
                description=None if has_desc else info["description"],
                traits=None if has_traits else info.get("traits", []),
            )


def _build_bootstrap() -> dict:
    """Compute the complete initial state for the single-page UI."""
    # results (all, with audio url)
    results = db.list_all_results(limit=500)
    for r in results:
        r["audio_url"] = f"/api/audio/{r['audio_hash']}.wav"

    # passages with slot info for cross-passage validate
    passages_list = db.list_passages()

    # casting: one row per character slot
    casting_state = db.get_casting()
    casting_list: list[dict] = []
    for c in characters.CHARACTERS:
        entry = casting_state.get(c.slot)
        result = db.get_result(entry["result_id"]) if entry and entry["result_id"] else None
        if result:
            result["audio_url"] = f"/api/audio/{result['audio_hash']}.wav"
        casting_list.append({
            "slot": c.slot,
            "label": c.label,
            "portrait_key": c.portrait_key,
            "variant": c.variant,
            "result": result,
            "notes": entry["notes"] if entry else None,
        })

    # voice notes + stars per slot, keyed by "engine|voice_id|params_fp"
    voice_notes: dict[str, dict] = {}
    for c in characters.CHARACTERS:
        voice_notes[c.slot] = {
            f"{e}|{v}|{fp}": {"notes": row["notes"], "stars": row["stars"]}
            for (e, v, fp), row in db.get_voice_notes(c.slot).items()
        }

    # engines / voices (notes are slot-scoped; fetched when popover opens)
    engines_out = []
    for name, eng in get_engines().items():
        voices = []
        if eng.available:
            for v in eng.list_voices():
                voices.append(v.model_dump())
        engines_out.append({
            "engine": name,
            "available": eng.available,
            "unavailable_reason": eng.unavailable_reason,
            "pool": eng.pool,
            "voices": voices,
            "param_schema": list(getattr(type(eng), "PARAM_SCHEMA", [])),
        })

    return {
        "characters": characters.as_dicts(),
        "casting": casting_list,
        "passages": passages_list,
        "engines": engines_out,
        "results": results,
        "voice_notes": voice_notes,
        "voice_profiles": db.list_voice_profiles(),
        "preset_voices": db.list_voice_casting_history_flat(),
        "tryout_text": characters.TRYOUT_TEXT,
    }


@app.get("/", response_class=HTMLResponse)
def page_compare(request: Request):
    return TEMPLATES.TemplateResponse(
        request, "compare.html", {"bootstrap": _build_bootstrap()},
    )
