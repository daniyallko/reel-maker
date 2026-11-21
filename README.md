# LINK2REEL

Autonomous research-to-motion-video studio. A topic, description, public URL, document, image set, or mixed brief becomes a sourced 30–40 second vertical video with typed cinematic scenes, studio narration, deterministic HTML motion, and scene-bounded word captions.

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

Set `GEMINI_API_KEY` in `backend/.env`. Optional: set `FIRECRAWL_API_KEY` to use Firecrawl search for faster, sourced research. Without it, bounded DDGS queries provide external retrieval when available. Failed retrieval falls back to supplied evidence and is labeled deterministic; it is not reported as external research. Use **Watch portfolio demo** for the offline sample.

## 2026 model stack

- `gemini-4-hydrogen` (`thinking_level=HIGH`) for research planning and synthesis, storyboards, motion HTML, and the six-criterion Vision audit.
- `gemini-nano-banana-2.1` for requested vertical generated artwork and the cover thumbnail. Screenshots, supplied images, and procedural scenes use their directed asset paths instead.
- `gemini-3.8-flash-tts` through `v1beta` for Charon, Fenrir, Puck, and Aoede narration. Transcript text stays verbatim; style travels on `Part.speech_metadata`.

Provider failures have deterministic visual, audio, script, and motion fallbacks. No generated HTML may load external scripts or resources. Fallbacks do not claim external research, exact word-level TTS timestamps, or an AI review that did not occur.

## Production graph

1. **Research:** Playwright captures available website screenshots, brand palette/fonts/copy, source images, and a four-second scroll video. Every non-sample input receives bounded external query retrieval; uploaded evidence is retained and citations are deduplicated.
2. **Storyboard:** Gemini writes 6–8 researched scenes when available. The public schema accepts 4–8 contiguous scenes for legacy compatibility. Each scene cites evidence and declares its visual type, layout, camera, animation, transition, and SFX.
3. **Assets:** The scene builder creates one matching primary asset per scene plus a separate cover. It routes screenshots, source images, generated art, kinetic typography, diagrams, and data scenes without reusing unrelated sample imagery.
4. **Narration and timing:** TTS produces measured scene segments. The timeline retimes scenes around complete narration, pads and concatenates segment audio, and selects music from the requested style. Estimated word captions remain inside their measured scene audio; they are not exact TTS timestamps.
5. **Motion and creative QA:** Deterministic single-file HTML exposes `window.seekTo(t)`. Review frames include the hook pair, every scene midpoint, and the final frame, capped at 12. One audit/revision cycle scores typography/contrast, safe-zone compliance, editorial craft, visual momentum, narrative alignment, and asset relevance.
6. **Render:** Playwright captures 30fps frames at 1080×1920. FFmpeg mixes ASS captions, aligned narration, style music, retimed scene SFX, and sidechain ducking with two encoder threads. Strict creative review requires all six scores at least 8; draft and unreviewed states remain labeled separately from technical media QA.

## Studio API

- `POST /api/studio/projects/inputs` — multipart `source`, `style`, `voice`, `quality_mode`, and optional `files`
- `POST /api/studio/projects` — legacy JSON `{url, style, voice, quality_mode}`
- `POST /api/studio/projects/sample` — instant offline demo
- `GET /api/studio/projects/{id}` — project and output snapshot
- `GET /api/studio/projects/{id}/events` — buffered SSE with replay and `Last-Event-ID`
- `GET /api/studio/projects/{id}/download` — MP4, PNG, script, and source ZIP
- `/media/{id}/...` — captures, generated art, audio, audit contact sheet, and final video

Legacy CUTLINE routes under `/api/projects` remain available for backward compatibility. LINK2REEL uses only `/api/studio`.

## Offline sample

```bash
cd backend
../.venv/bin/python scripts/prebake_link2reel.py
```

This renders a 32-second, third-person portfolio reel from `https://daniyal.pro` and sanitized professional CV evidence. It caches scene assets, cover, aligned narration, captions, citations, a storyboard-derived contact sheet, and the MP4 in `backend/assets/link2reel/sample-output`. Without a configured review provider, its metadata says `Unreviewed draft`; that label is not an AI audit pass. Rebuild after changing the portfolio evidence, scene direction, motion templates, timeline, or caption renderer.

## Verification

```bash
cd backend
../.venv/bin/python -m pytest -q
../.venv/bin/python -c "from app.studio.renderer import SAMPLE_OUTPUT, verify_studio_video; print(verify_studio_video(SAMPLE_OUTPUT / 'trailer.mp4'))"

cd ../frontend
npm test
npm run typecheck
npm run build
node tests/studio-e2e.mjs
```

The browser suite requires this checkout's backend on port 8000 and frontend on port 3000. Live provider smoke is separate from offline verification. The URL check uses `https://example.com` by default; set `STUDIO_TEST_URL` to test another domain. The topic check posts multipart input and requires external evidence, 6–8 cited scenes, and all six strict audit scores when strict mode is selected.

```bash
cd backend
../.venv/bin/python scripts/e2e_studio_live.py
STUDIO_TEST_TOPIC="A short cinematic documentary about ocean cleanup robots." ../.venv/bin/python scripts/e2e_studio_live.py
```

Results and unrun live checks are recorded in `docs/superpowers/verification.md`. Design direction and final polish are in `design-system/cutline/MASTER.md` and `docs/superpowers/unslop-audit.md`.

The development server has no authentication. Do not expose it publicly without access controls, URL egress restrictions, and upload isolation.
