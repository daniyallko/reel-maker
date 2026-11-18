# CUTLINE verification ledger

Date: 2026-11-18

## Final automated results

- Backend: **18/18 tests passed** in 2.88s.
- Frontend unit tests: **8/8 passed** across scramble, video seek, and microphone cleanup.
- Frontend TypeScript: `tsc --noEmit` passed.
- Frontend production build: `next build` compiled and generated `/` plus `/project/[id]` successfully.
- Browser/sample suite: passed with a 22-second trailer, 1080×1920 poster, cast navigation, timeline seeking, playback, both inspector modals, ZIP download, WhatsApp popup, and Instagram fallback.
- Responsive checks: 375px home and Premiere have no horizontal overflow.
- Reduced motion: final text is visible, background videos stay paused, and no hydration mismatch remains.
- Mouse scrub: advances the supplied hero video with chained seeks.
- Sample SSE: reaches the Premiere Press Kit and all output interactions.
- Screenshots: `frontend/test-results/neon-home.png`, `neon-mobile-home.png`, `neon-premiere.png`, and `neon-premiere-mobile.png`.

## Commands

```bash
cd backend && ../.venv/bin/python -m pytest -v
cd frontend && node tests/e2e.mjs && npm test && npm run typecheck && npm run build
```

## Live provider findings

- Google rejected `gemini-2.5-flash` with a 404 deprecation response for new users. After live availability probes, CUTLINE starts with `gemini-3.5-flash-lite`.
- Live calls then returned transient `503 UNAVAILABLE` demand errors. CUTLINE now retries transient errors and falls back in order through `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, and `gemini-3.1-flash-lite`.
- Minimal live probes confirmed all four primary models were returning 503 while both lite models returned `OK`.
- Retry, model-fallback, request-timeout, and Gemini-compatible EDL schema tests pass. The provider schema uses string act enums and avoids unsupported `exclusiveMinimum` constraints.
- Real 10-image + WAV voice-note production: **passed**. Project `83d314fa5c1d`, title **The Big Sur Blunder**, 22.0 seconds, 7 shots, 4 cast cards, 8 keeper assets, valid 1080×1920 H.264/audio, and valid ZIP download.

## Runtime

- Backend: running on port 8000 with Gemini enabled, capped at **3 GiB address space** via `backend/scripts/run_limited.sh`.
- Frontend: running on port 3000 with `NODE_OPTIONS=--max-old-space-size=1536`.
- Native limits: ONNX intra/inter-op 1 thread, OpenCV 1 thread, FFmpeg 2 threads, filter graph 1 thread, rembg input 768px.
- Post-render backend RSS was 548 MiB and VSZ 1.08 GiB, below the enforced cap; WSL reported 8.1 GiB available.
- Browser suite also passed against the memory-limited servers.
- Git: repository initialized on `main`; no commit created.
