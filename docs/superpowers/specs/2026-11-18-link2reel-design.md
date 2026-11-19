# LINK2REEL Design

## Intent

Turn a public URL into a sourced 30–40 second vertical motion video. Keep CUTLINE's proven FastAPI/LangGraph/SSE runtime and neon cinema UI, but replace photo-slideshow production with web research and deterministic programmatic motion graphics.

## Decisions

- Add `/api/studio` routes beside legacy CUTLINE routes for backward compatibility. New frontend code uses only `/api/studio`.
- Reuse `EventBus`, event IDs/replay, `Last-Event-ID`, project media serving, ZIP downloads, `useProjectEvents`, motion preference hook, and the 3 GiB backend/1.5 GiB Node limits.
- Use `google-genai` 3.5.x with `gemini-4-hydrogen`, `gemini-nano-banana-2.1`, and `gemini-3.8-flash-tts` (`v1beta`). TTS transcript text stays verbatim; style goes on `Part.speech_metadata`.
- Use parallel Playwright harvesting and DDGS research. Real captures include hero/mid screenshots, palette/fonts/copy, high-res images, and a 4-second video.
- Nano Banana returns generated image parts through `generate_content`; reference scraped screenshots and enable web/image search types.
- Generate or fall back to a deterministic single-file HTML template exposing `window.seekTo(t)`. Validate offline assets and required choreography. Capture 30fps at 1080×1920.
- Audit t=1,6,14,22 through Gemini Vision before rendering. Limit auto-patching to one revision and use a deterministic contrast/layout fallback if the model cannot complete it.
- Generate scene audio separately for exact timing, combine one narration WAV, write word-level ASS captions, and mix with sidechain ducking.
- Pre-bake one 35-second offline sample using the same deterministic renderer and real local sample-site screenshots. Cache it for instant demo replay.

## Non-goals

- No fake DOM UI drawn as a substitute for scraped site imagery.
- No external scripts or network access inside generated motion HTML.
- No loss of the existing CUTLINE API or tests.
- No GitHub push unless separately requested.

## Acceptance

- New URL input, styles, voices, live asset events, and sourced Premiere output work at 375px and desktop.
- Sample demo completes offline and emits all stages plus MP4/PNG/ZIP.
- Real provider failures use explicit fallbacks rather than hanging indefinitely.
- Backend/frontend unit tests, browser tests, typecheck, build, and media QA pass.
