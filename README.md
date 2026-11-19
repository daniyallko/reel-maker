# LINK2REEL

Autonomous URL-to-motion-video studio. A public URL becomes a sourced 30–40 second vertical video with real site captures, external research, Gemini-generated artwork, studio narration, deterministic HTML motion, and word-level captions.

## Run

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health: http://localhost:8000/api/health

Requirements: Python 3.12, Node 22+, FFmpeg with `libx264`, `libass`, and `flite`, and Playwright Chromium.

```bash
python3 -m venv .venv
.venv/bin/pip install -e './backend[dev]'
.venv/bin/playwright install chromium
npm --prefix frontend install
```

Start the backend with its physical-memory cap:

```bash
backend/scripts/run_limited.sh
```

The launcher defaults to 3 GiB (`CUTLINE_MEMORY_MAX`) and limits native worker threads. Start the frontend with a 1.5 GiB heap:

```bash
NODE_OPTIONS=--max-old-space-size=1536 npm --prefix frontend run dev -- --hostname 0.0.0.0 --port 3000
```

Set `GEMINI_API_KEY` in `backend/.env`. Optional: set `FIRECRAWL_API_KEY` to use Firecrawl search for faster, sourced research. Without it, DDGS runs two bounded parallel queries with a primary-source fallback. Without either key, use **Load Sample Link (Instant Demo)**.

## 2026 model stack

- `gemini-4-hydrogen` (`thinking_level=HIGH`) for research synthesis, storyboards, motion HTML, and the four-frame Vision audit.
- `gemini-nano-banana-2.1` for vertical generated artwork and the cover thumbnail, with real screenshots and web/image search types.
- `gemini-3.8-flash-tts` through `v1beta` for Charon, Fenrir, Puck, and Aoede narration. Transcript text stays verbatim; style travels on `Part.speech_metadata`.

Provider failures have deterministic visual, audio, script, and motion fallbacks. No generated HTML may load external scripts or resources.

## Production graph

1. **Research:** Playwright captures hero/mid screenshots, brand palette/fonts/copy, source images, and a four-second scroll video while DDGS researches outside sources.
2. **Storyboard:** four sourced scenes follow 0–3s hook, 3–14s problem, 14–28s system, 28–35s takeaway at 128 BPM.
3. **Assets:** Nano Banana creates two art frames and a cover while TTS creates scene audio and exact timings.
4. **Motion:** deterministic single-file HTML exposes `window.seekTo(t)`. Four stills at t=1, 6, 14, 22 receive one Vision audit/revision.
5. **Render:** Playwright captures 1050 frames at 1080×1920/30fps. FFmpeg mixes ASS word captions, narration, music, and sidechain ducking with two encoder threads.

## Studio API

- `POST /api/studio/projects` — JSON `{url, style, voice}`
- `POST /api/studio/projects/sample` — instant offline demo
- `GET /api/studio/projects/{id}` — project and output snapshot
- `GET /api/studio/projects/{id}/events` — buffered SSE with replay and `Last-Event-ID`
- `GET /api/studio/projects/{id}/download` — MP4, PNG, script, and source ZIP
- `/media/{id}/...` — captures, generated art, audio, audit contact sheet, and final video

Legacy CUTLINE routes under `/api/projects` remain available for backward compatibility. LINK2REEL uses only `/api/studio`.

## Offline sample

```bash
.venv/bin/python backend/scripts/prebake_link2reel.py
```

This renders a 35-second sample from a real local Orbit Notes site and caches it in `backend/assets/link2reel/sample-output`. Rebuild after changing the sample site, motion template, or caption renderer.

## Verification

```bash
cd backend
../.venv/bin/python -m pytest -q

cd ../frontend
npm test
node tests/studio-e2e.mjs
npm run typecheck
npm run build
```

Live provider and full-pipeline check (uses `https://example.com` by default; set `STUDIO_TEST_URL` to test another domain):

```bash
cd backend
../.venv/bin/python scripts/e2e_studio_live.py
```

Results are recorded in `docs/superpowers/verification.md`. Design direction and final polish are in `design-system/cutline/MASTER.md` and `docs/superpowers/unslop-audit.md`.

The development server has no authentication. Do not expose it publicly without access controls, URL egress restrictions, and upload isolation.
