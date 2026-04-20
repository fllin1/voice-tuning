import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from .engines.registry import get_engines
from .routes import ab, casting, generate, passages, ratings, voices

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "backend" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    _seed_passages()
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
app.include_router(ab.router)
app.include_router(casting.router)


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


@app.get("/", response_class=HTMLResponse)
def page_compare(request: Request):
    return TEMPLATES.TemplateResponse(request, "compare.html")


@app.get("/ab", response_class=HTMLResponse)
def page_ab(request: Request):
    return TEMPLATES.TemplateResponse(request, "ab.html")


@app.get("/casting", response_class=HTMLResponse)
def page_casting(request: Request):
    return TEMPLATES.TemplateResponse(request, "casting.html")
