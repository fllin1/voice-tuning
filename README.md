# Voice-Tuning

Local web app for auditioning TTS voices across multiple engines, comparing them
side-by-side, A/B-testing, and locking in a final cast for a Light Novel
voiceover project. Built around *Classroom of the Elite* (8 voice slots) but
the casting structure is generic.

## Engines

| Engine | Where it runs | When it appears |
| --- | --- | --- |
| Kokoro-82M | local (`mlx-audio`) | always (downloads on first generate) |
| Orpheus 3B | local (`mlx-audio`) | step 5 (currently disabled stub) |
| Hume Octave | cloud HTTP | only if `HUME_API_KEY` is set; step 8 stub |

## Setup

Requires Python 3.12, macOS Apple Silicon, [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                                       # install deps
cp .env.example .env                          # optional; fill HUME_API_KEY if you have one
uv run uvicorn backend.main:app --reload      # http://127.0.0.1:8000
```

The first Kokoro generation downloads ~330 MB of model weights from HuggingFace.

## Pages

- `/` — Compare: pick a passage and one or more voices, generate in batch, rate.
- `/ab` — A/B blind: pick exactly two cards (via the "Add to A/B" toggle on the
  Compare page) then come here for blind alternation.
- `/casting` — Final cast: assign a winning result per character slot, export JSON.

## Data

- `data/passages.json` ships with the default passage library. Add more via the
  Compare page custom-text box or by appending to the JSON.
- `audio_cache/` holds content-addressed WAV files. Hash key includes the engine
  version label so model upgrades don't return stale audio.
- SQLite at `voice-tuning.db` (gitignored) holds passages, results, ratings, A/B
  matches, and casting.

## Layout

See `CLAUDE.md` for project rules and architectural notes.

## Tests

```bash
uv run pytest
```
