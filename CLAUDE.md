# Voice-Tuning — Project Rules

This project follows the global `~/.claude/CLAUDE.md` rules. Project-specific notes:

## Stack
- **Backend**: FastAPI + Jinja2 + stdlib `sqlite3`. No ORM.
- **Frontend**: HTMX + vanilla JS. No build step.
- **Python**: 3.12, managed by `uv`.
- **TTS**: `mlx-audio` for Kokoro and Orpheus. `httpx` for Hume (optional).

## Run
```bash
uv sync
uv run uvicorn backend.main:app --reload
```

## Architectural rules
- **One generation at a time** for local engines. They share the single Apple GPU; parallel runs only contend.
- **Content-addressed audio cache**: hash key = `engine_version | voice_id | speed | params_json | text`.
  Hash is included so model upgrades don't return stale audio.
- **Engines are discovered at startup** (`backend.engines.registry`). If a dependency or env var is missing,
  the engine reports `available=False` and the UI grays it out instead of crashing.
- **Routes return JSON** for `/api/*` and HTML for page routes. HTMX swaps fragments where simple.

## Conventions
- Use `uv add` for new deps. Never raw pip.
- Conventional Commits (`feat(engines): add kokoro adapter`). Do not commit unless asked.
- No `Co-Authored-By` trailer.
- Read files before editing.
- No `try/except` unless genuinely needed (external I/O, network, user input). Let errors propagate.
