# CUTLINE

CUTLINE turns a group trip's photos, short clips, inside jokes, and an optional voice note into a 22-second vertical trailer, a theatrical poster, and character freeze-frame cards.

## Local servers

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health check: http://localhost:8000/api/health

**Load Sample Chaos Trip** works without a Gemini key or network calls to AI providers. It uses eight original sample frames, an original synthesized score, offline FFmpeg narration, and a cached press kit when available.

## Setup

Requirements: Python 3.12, Node.js 22+, FFmpeg with `libx264` and `flite`, and `ffprobe`.

```bash
python3 -m venv .venv
.venv/bin/pip install -e './backend[dev]'
npm --prefix frontend install
```

The repository includes generated sample JPEGs and four original WAV soundtracks. To regenerate them:

```bash
.venv/bin/python backend/scripts/generate_sample_assets.py
.venv/bin/python backend/scripts/generate_music.py
```

To pre-bake the offline sample press kit:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/prebake_sample.py
```

## Run

Terminal 1:

```bash
backend/scripts/run_limited.sh
```

The launcher caps backend address space at 3 GiB (`CUTLINE_MEMORY_KIB` overrides it), limits native worker threads, and keeps render failures inside the job instead of exhausting WSL memory.

Terminal 2:

```bash
NODE_OPTIONS=--max-old-space-size=1536 npm --prefix frontend run dev -- --hostname 0.0.0.0 --port 3000
```

The Next.js server rewrites `/api/*` and `/media/*` to `http://127.0.0.1:8000`. Set `BACKEND_URL` if the backend uses another address.

## Your own media

Copy `backend/.env.example` to `backend/.env` and set:

```bash
GEMINI_API_KEY=your_key_here
```

Real projects start with the live-verified `gemini-3.5-flash-lite` and retry/fall back through `3.8`, `3.7`, `3.6`, `3.5`, and `3.1-flash-lite` for batched multimodal perception and structured EDL generation. Narration uses `edge-tts`, with offline FFmpeg fallback. Poster subject extraction uses `rembg`. These providers require network access. The first rembg run may download its local inference model. Without a key, use sample mode; real uploads return a clear 503 response.

## Pipeline

1. Local perceptual-hash dedupe, Laplacian blur rejection, video keyframe extraction, and 768px perception derivatives.
2. LangGraph perception and screenwriting.
3. Parallel Pillow/OpenCV poster production and audio production.
4. FFmpeg Ken Burns motion, clip trimming, title cards, beat flashes, audio ducking, and 1080×1920 H.264 export.
5. FFprobe duration/stream checks and full frame decode before the premiere event.

Events are buffered and replayed over SSE, so reloading a project does not restart rendering.

## API

- `POST /api/projects` — multipart media, cast, genre, notes, optional voice note
- `POST /api/projects/sample` — start the offline sample
- `GET /api/projects/{id}` — project snapshot
- `GET /api/projects/{id}/events` — buffered SSE feed
- `GET /api/projects/{id}/download` — trailer, poster, EDL, and cast-card ZIP
- `/media/{id}/...` — generated project media

## Sharing

WhatsApp opens a user-initiated share URL. Browsers cannot publish directly to Instagram; CUTLINE uses the system share sheet when available, otherwise it downloads the trailer and copies the caption.

## Verification

```bash
cd backend
../.venv/bin/python -m pytest -v

cd ../frontend
node tests/e2e.mjs
npm test
npm run typecheck
npm run build
```

The browser suite requires both dev servers and Playwright Chromium (`npx playwright install chromium`). It covers mouse scrubbing, navigation, 375px layouts, reduced motion, sample SSE, playback, cast controls, modals, timeline seeking, downloads, and sharing.

For a live multimodal production using `GEMINI_API_KEY`:

```bash
cd backend
../.venv/bin/python scripts/e2e_real.py
```

Current results are recorded in `docs/superpowers/verification.md`.

## Design

The source of truth is `design-system/cutline/MASTER.md`: SynapseX-style black/white Space Mono, Anton SC watermarks, full-viewport video backgrounds, glass navigation pills, scramble reveals, and spring motion. The anti-slop audit is in `docs/superpowers/unslop-audit.md`.

This local development server has no authentication. Do not expose it to a public network without adding access controls and upload isolation.
