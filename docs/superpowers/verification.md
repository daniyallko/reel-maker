# LINK2REEL verification ledger

Date: 2026-11-20
Branch: `feat/cinematic-research-studio`
Worktree: `/home/daniyallko/reel-maker/.worktrees/cinematic-research-studio`

## Automated verification

Commands in this Automated verification section ran against this worktree. No live provider key was used for these checks. Live-provider commands are listed separately below as not run.

### Sample regeneration

```bash
cd /home/daniyallko/reel-maker/.worktrees/cinematic-research-studio/backend && ../.venv/bin/python scripts/prebake_link2reel.py
```

Result: **PASS**, exit 0. Regenerated `trailer.mp4`, `visuals/thumbnail-03.png`, aligned `audio/narration.wav`, `audio/captions.ass`, `sample.json`, `studio-output.json`, four scene assets, source captures/scroll video, and `audit/contact-sheet.png`.

Integration fix: the shared virtual environment's editable install points at the original checkout. Both scripts now prepend their own backend directory to `sys.path`, so script execution cannot silently import another checkout. The first pre-bake attempt failed with `ModuleNotFoundError: No module named 'app.studio.timeline'`; the successful run above followed that fix.

### Backend

```bash
cd /home/daniyallko/reel-maker/.worktrees/cinematic-research-studio/backend && ../.venv/bin/python -m pytest -q
```

Result: **182/182 tests passed** in 53.57s. This includes the fix-round regression proving scenes 3–4 and the cover use rich, nonprocedural imagery and that the cover differs from the engineering scene. The focused portfolio/visual run passed 11/11 tests in 2.66s.

```bash
cd /home/daniyallko/reel-maker/.worktrees/cinematic-research-studio/backend && ../.venv/bin/python -c "from pathlib import Path; from app.studio.renderer import SAMPLE_OUTPUT, verify_studio_video; print(verify_studio_video(SAMPLE_OUTPUT / 'trailer.mp4'))"
```

Result: **PASS** — `valid=True duration=32.0 width=1080 height=1920 has_audio=True errors=[]`.

### Frontend, typecheck, and production build

```bash
cd /home/daniyallko/reel-maker/.worktrees/cinematic-research-studio/frontend && npm test && npm run typecheck && npm run build
```

Results:

- Vitest: **34/34 tests passed** across 10 files in 5.35s.
- TypeScript: `tsc --noEmit` **passed**.
- Next.js 16.4.6 production build: **passed**; `/` and `/_not-found` prerendered and `/project/[id]` built as a dynamic route.

### Browser and download compatibility

The backend and frontend were started from this worktree on ports 8000 and 3000 after verifying both ports were free. Their process working directories were confirmed as this worktree's `backend` and `frontend` directories. Backend health returned `{"status":"ok","gemini":false,"sample":true}`.

```bash
cd /home/daniyallko/reel-maker/.worktrees/cinematic-research-studio/frontend && node tests/studio-e2e.mjs
```

Result: **PASS** — `{"status":"passed","duration":32,"projectId":"e2dc18b6cf5e"}`. Covered four directed sample scenes with retimed third-scene seeking, typed scene labels, citations, portfolio evidence, script-copy feedback, a ZIP response with `PK` signature, 375px mobile overflow checks, reduced-motion video pausing, and browser error collection. Desktop and mobile Premiere screenshots were inspected; neither showed horizontal page overflow. Headless Chromium blocked direct clipboard access and displayed the implemented manual-copy fallback. Fix round 1 changed bundled imagery only, so the browser suite was not rerun.

The sample JSON validates as `StudioOutput`; its download route still supplies MP4, PNG, script, and sources in a ZIP. The multipart input and legacy JSON URL route schemas were not changed.

## Regenerated portfolio sample

- Source: `https://daniyal.pro` plus sanitized professional CV evidence.
- Title: `Mohd Daniyal — Production AI in Motion`.
- Narration: third person, retaining the source-backed 1,000+ websites, 100,000+ users, sub-500ms first audio, and 99.9% uptime claims.
- Direction: four cited scenes with explicit visual type, layout, camera, animation, transition, SFX, callouts, and metrics fields. Scenes retimed to 0–2.50234375, 2.50234375–11.98125, 11.98125–24.9934375, and 24.9934375–32 seconds.
- Review state: **`Unreviewed draft`**. `quality_mode` is `draft`, `review_label` is `Unreviewed draft`, and `critique_scores` is `{}` because no review provider was configured. No AI audit pass is claimed.
- Contact sheet: seven frames at 0.600, 1.000, 1.251, 7.242, 18.487, 28.497, and 31.500 seconds. Manual inspection found legible headlines and no obvious clipping. The first two scenes use portfolio screenshots. The third scene uses a real portfolio hero capture and the fourth uses the real projects/experience capture, both with scene-specific layouts. The cover is a distinct split composition combining the real hero and experience captures rather than an abstract fallback. No AI creative audit pass is claimed.
- Video: H.264/yuv420p, 1080×1920, 30/1fps, 960 frames, 32.000000s.
- Audio: AAC, 48 kHz, 32.000000s; measured mean volume -18.2 dB and maximum volume -6.2 dB.
- Strict technical media QA: valid, no errors. This is separate from the unavailable creative AI audit.

## Live-provider smoke

Required provider keys are absent from the process environment. Sharing the original checkout's `backend/.env` into this worktree was denied, and that file was not read, copied, linked, sourced, or printed.

- URL smoke command: `cd backend && env -u STUDIO_TEST_URL ../.venv/bin/python scripts/e2e_studio_live.py` — **not run** because required provider keys are not present in the process environment and sharing `backend/.env` into this worktree was denied.
- Topic smoke command: `cd backend && STUDIO_TEST_TOPIC="A short cinematic documentary about ocean cleanup robots." ../.venv/bin/python scripts/e2e_studio_live.py` — **not run** because required provider keys are not present in the process environment and sharing `backend/.env` into this worktree was denied.

Therefore external live research, live 6–8-scene topic generation, live asset relevance, live six-criterion AI review, and a live text-only contact sheet have no new pass evidence in this run. The smoke script now uses multipart `/api/studio/projects/inputs` for `STUDIO_TEST_TOPIC`, retains the legacy URL path otherwise, checks 4–8 scenes generally and 6–8 for topics, requires external HTTP(S) evidence and cited scenes for topics, rejects known website-template narration, checks media QA and downloads, and enforces all six criteria at least 8 in strict mode.

## Runtime constraints and remaining limitations

- The backend process runs under a systemd user scope with `MemoryMax=3221225472` bytes (3 GiB). FFmpeg retains two encoder threads.
- Output remains within the required 30–40 second container; this sample is exactly 32 seconds.
- Captions are estimated word events bounded by measured scene narration. Exact word-level TTS synchronization is not claimed.
- Mixed-source input has a finite combined bound: harvested page copy is capped at 18,000 characters and uploaded source text at 30,000 characters, so the two together can total 48,000 characters. This documents the combined bound; no additional mixed-source enforcement test was required.
- Live-provider behavior remains unverified in this environment. The regenerated sample is explicitly unreviewed even though its source scenes and cover now use real portfolio captures.

## Provider fallback follow-up — 2026-11-21

Fallback changes are on `feat/universal-story-studio` and are currently uncommitted. They add OpenRouter/Groq structured generation, schema-repair retries, bounded 429 backoff, provider-attempt telemetry, mixed-media storyboard fallbacks, SVG/vector artwork, null-response handling, and unsafe-SVG validation.

### Automated and direct provider checks

- Full backend: **208/208 tests passed** in 59.24s.
- Direct OpenRouter structured research: **PASS** — valid `ResearchPlan` for ocean cleanup robots.
- Direct Groq structured research: **PASS** — valid `ResearchPlan` for ocean cleanup robots.
- Direct Groq storyboard: **PASS** — valid eight-scene `Storyboard` after provider/schema retries.
- `git diff --check`: **PASS**.

### Live smoke outcomes

- URL strict smoke: **FAIL** at the six-criterion creative gate. This is not a pass claim. The latest recorded scores were `{'typography/contrast': 7, 'safe-zone compliance': 9, 'editorial craft': 5, 'visual momentum': 4, 'narrative alignment': 6, 'asset relevance': 5}`.
- Ocean-topic strict smoke: **FAIL** at the six-criterion creative gate. The final recorded scores were `{'typography/contrast': 8, 'safe-zone compliance': 9, 'editorial craft': 5, 'visual momentum': 4, 'narrative alignment': 7, 'asset relevance': 6}`.
- URL explicit draft smoke: **PASS** — project `720cdbca0260`, 32 seconds, four cited scenes, valid media QA and ZIP, `Unreviewed draft` with no scores.
- Ocean-topic explicit draft smoke: **PASS** — project `788a76736d9a`, 32 seconds, seven cited scenes and three sources including external HTTP(S) research. Scores: `{'typography/contrast': 9, 'safe-zone compliance': 9, 'editorial craft': 8, 'visual momentum': 7, 'narrative alignment': 8, 'asset relevance': 8}`. `Unreviewed draft` is retained.

### Browser outcomes

- Full browser suite: **PASS** — project `b677a98cdb02`, duration 32 seconds; homepage, sample playback, scene seeking, citations, downloads, mobile overflow, reduced motion, and browser errors checked.
- Live URL draft playback: **PASS** — project `720cdbca0260`, 32-second video, four scene buttons, no browser errors. Screenshot inspected at `frontend/test-results/live-url-draft-premiere.png`.
- Live ocean-topic draft playback and scene seeking: **PASS** — project `788a76736d9a`, 32-second video, seven scene buttons, no browser errors. Screenshot inspected at `frontend/test-results/live-topic-draft-premiere.png`.
- The ocean contact sheet was inspected at `backend/data/788a76736d9a/audit/contact-sheet.png`. It contains generated art, diagrams, kinetic type, and procedural scenes; draft scores are reported above. Strict quality is not claimed.

Strict creative quality and reliable live art generation still depend on provider availability and output quality. The draft path produces valid videos; it does not prove the strict 8/10 creative gate passes.
