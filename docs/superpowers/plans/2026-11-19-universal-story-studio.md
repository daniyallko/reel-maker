# Universal Story Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add universal text/document/image sources, independent vision providers, a cinematic composer, active-only telemetry, and a bundled portfolio reel.

**Architecture:** Normalize every input into one `SourceBundle`, then keep the existing LangGraph production stages and deterministic renderer. Provider adapters sit behind one audited fallback router; UI and offline sample changes consume the same project/output contracts.

**Tech Stack:** FastAPI, Pydantic, LangGraph, httpx, google-genai, optional Anthropic SDK, pypdf, Pillow, Next.js, React, TypeScript, Playwright, FFmpeg.

**Spec:** `docs/superpowers/specs/2026-11-19-universal-story-studio-design.md`

## Global Constraints

- Keep 32-second, 1080×1920, 30fps H.264/AAC output and the 3 GiB backend memory cap.
- Strict quality remains four scores ≥8; draft is explicit and labeled `Unreviewed draft`.
- Never expose API keys or send data to a provider without its configured key.
- Maximum 8 files, 10 MB each, 30 MB total, and 30,000 extracted characters.
- Do not expose the development server publicly or remove SSRF/CSP/upload isolation.
- Keep the existing JSON URL API and legacy CUTLINE tests working.
- Portfolio visuals use third-person narration and omit private contact details.

## Review Focus

- Empty or malformed uploads return bounded 422 responses rather than starting jobs.
- A valid low-score audit triggers repair, not provider shopping.
- Provider timeout/quota/schema failure advances through configured providers and emits useful telemetry.
- Text-only projects work without a fabricated public URL or screenshot.
- Terminal jobs stop animation while preserving backend responses and demo playback.

---

### Task 1: Unified source ingestion

**Files:**
- Create: `backend/app/studio/sources.py`
- Modify: `backend/app/studio/schemas.py`, `backend/app/studio/api.py`, `backend/app/studio/jobs.py`, `backend/pyproject.toml`
- Test: `backend/tests/studio/test_sources.py`, `backend/tests/studio/test_studio_api.py`

**Interfaces:**
- Produces: `SourceBundle` with `kind/title/source_url/dom_copy/citations`, `HarvestResult = SourceBundle` compatibility alias, `ingest_text(...)`, `ingest_uploads(...)`, and `StudioJobManager.create_input(source, style, voice, files)`.
- Existing URL jobs produce the same bundle shape through the harvester; text-only jobs skip URL research and never reach `write_storyboard(None)`.
- `StudioProjectSnapshot.source_title` carries the display title; only HTTP(S) sources render as links.

- [ ] Write failing tests for text-only input, TXT/PDF extraction, PNG/JPEG/WebP assets, empty input, bad MIME/extension, bad PDF, 8-file/10 MB/30 MB/30,000-character limits, and the multipart endpoint.
- [ ] Run `pytest backend/tests/studio/test_sources.py -q` and confirm missing-ingestion failures.
- [ ] Add `pypdf`, the `SourceBundle` contract, bounded local extraction, Pillow pixel-count validation, and the multipart endpoint while retaining `POST /projects`; return fixed public 422 messages without internal paths.
- [ ] Run source/API tests and confirm accepted assets become `StudioAsset` objects with project-local paths.
- [ ] Record verified tests; do not commit unless requested: `feat: add universal story source ingestion`.

### Task 2: Independent Vision provider router

**Files:**
- Create: `backend/app/studio/vision_providers.py`
- Modify: `backend/app/studio/vision.py`, `backend/app/config.py`, `backend/app/studio/jobs.py`, `backend/app/studio/providers.py`, `backend/pyproject.toml`, `backend/.env.example`
- Test: `backend/tests/studio/test_vision_providers.py`

**Interfaces:**
- Produces: `VisionProvider.audit(contact_sheet, html) -> VisionAudit` and `VisionProviderRouter.audit(...)`.
- Configures `VISION_PROVIDER_ORDER`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, and optional `ANTHROPIC_API_KEY`.

- [ ] Write failing tests for Gemini → OpenRouter → Groq → Anthropic order, missing keys, retryable errors, `retry-after`, malformed JSON, missing criteria, and no fallback after valid low scores.
- [ ] Run router tests and confirm the router is absent.
- [ ] Implement Gemini, OpenRouter (`inclusionai/ling-3.2-flash:free`), Groq (`qwen/qwen3.8-27b`), and optional official Anthropic SDK (`claude-haiku-5-5`) adapters with 60-second timeouts and two attempts; lazy-import Anthropic behind an optional dependency extra.
- [ ] Validate exactly four unique criteria and recompute `passed` server-side; redact provider errors.
- [ ] Run router and existing vision tests.
- [ ] Record verified tests; do not commit unless requested: `feat: add resilient vision provider routing`.

### Task 3: Repair and quality modes

**Files:**
- Modify: `backend/app/studio/graph.py`, `backend/app/studio/vision.py`, `backend/app/studio/motion.py`, `backend/app/studio/schemas.py`, `backend/app/studio/renderer.py`
- Test: `backend/tests/studio/test_vision_fallback.py`, `backend/tests/studio/test_renderer.py`

**Interfaces:**
- Adds `quality_mode: strict | draft` to the create request, job state, graph state, and `StudioOutput`; adds `review_label: str | None` to output.
- Separates audit JSON from repaired HTML; draft output reads `Unreviewed draft` in the Premiere UI and metadata only, never burned into frames.

- [ ] Write failing tests proving strict rejects 7, draft accepts 7 with a label, unaudited output is draft-only, repair HTML requires sanitization and a valid clock, and valid low scores never advance providers.
- [ ] Run quality tests and confirm the old hard-coded behavior fails them.
- [ ] Implement separate repair responses, one bounded repair/render loop, draft labeling, provider/model/attempt SSE telemetry, and mandatory sanitize + offline CSP + `validate_motion_clock` on every repaired document.
- [ ] Run vision, motion, renderer, and graph tests.
- [ ] Record verified tests; do not commit unless requested: `feat: add audited repair and draft rendering`.

### Task 4: Source-agnostic storyboard and visuals

**Files:**
- Modify: `backend/app/studio/providers.py`, `backend/app/studio/graph.py`, `backend/app/studio/harvest.py`, `backend/app/studio/motion.py`
- Test: `backend/tests/studio/test_providers.py`, `backend/tests/studio/test_motion.py`

**Interfaces:**
- Every provider and graph stage consumes `SourceBundle`; uploaded images participate in `fallback_visuals` and motion scenes.
- Text-only jobs use `inline://text` and real user evidence rather than generic website copy.

- [ ] Write failing tests for text-only storyboards, uploaded-image selection, empty-screenshot fallback, and citation preservation.
- [ ] Run provider/motion tests and confirm URL-only assumptions fail.
- [ ] Replace `HarvestResult` coupling with the shared bundle while retaining URL compatibility and SSRF protections.
- [ ] Run source, provider, motion, and recovery tests.
- [ ] Record verified tests; do not commit unless requested: `feat: produce reels from any source bundle`.

### Task 5: Cinematic universal composer

**Files:**
- Modify: `frontend/components/glyph-home.tsx`, `frontend/app/glyph.css`, `frontend/lib/api.ts`, `frontend/lib/types.ts`
- Test: `frontend/tests/glyph-home.test.tsx`, `frontend/tests/studio.test.tsx`

**Interfaces:**
- Composer posts text/URL plus optional files to `/api/studio/projects/inputs` and routes to the returned project.
- Demo action is `Watch portfolio demo`.

- [ ] Write failing component tests for the large textarea, accepted uploads, no quick links/URL label/search icon, cinematic selectors including `tech_launch`, third-party processing notice, large generate button, separate demo action, and selected-pill thumb offsets matching the selected button.
- [ ] Run component tests and confirm old composer expectations fail.
- [ ] Implement the new headline “Your story. Cut like a film.”, universal multipart submission, upload list/removal, corrected species-pill geometry, and responsive cinematic styling.
- [ ] Run frontend unit tests and typecheck.
- [ ] Record verified tests; do not commit unless requested: `feat: redesign universal cinematic composer`.

### Task 6: Active-only project telemetry

**Files:**
- Modify: `frontend/components/project-view.tsx`, `frontend/components/studio-screening.tsx`, `frontend/app/glyph.css`
- Test: `frontend/tests/studio-screening.test.tsx`

**Interfaces:**
- Only the current agent appears with animated `CircleNotch`; response stream remains visible.
- No application top bar appears on `/project/[id]`.

- [ ] Write failing tests for removed chrome, relevant masthead, one active stage, animated stage replacement, and zero active animation after terminal states.
- [ ] Run telemetry tests and confirm old all-agent behavior fails.
- [ ] Remove `AppHeader`, add “Building your cinematic reel” and source-aware status, use `AnimatePresence` for the active stage, and preserve the response log/error state.
- [ ] Run frontend unit tests and typecheck.
- [ ] Record verified tests; do not commit unless requested: `feat: focus project telemetry on active work`.

### Task 7: Portfolio demo and final verification

**Files:**
- Create: `backend/assets/link2reel/portfolio/cv.txt`
- Modify: `backend/scripts/prebake_link2reel.py`, `backend/app/studio/jobs.py`, `backend/assets/link2reel/sample-output/sample.json`
- Test: `backend/tests/studio/test_recovery.py`, `frontend/tests/studio-e2e.mjs`

**Interfaces:**
- Instant demo replays the bundled third-person Mohd Daniyal portfolio from `daniyal.pro` and sanitized CV evidence.

- [ ] Add the sanitized CV and failing tests for demo source/title, third-person script, exact 1,000+ sites/100,000+ users/sub-500ms/99.9% uptime claims matched to `cv.txt`, no phone/email in frames, and instant playback.
- [ ] Run demo tests before regeneration and confirm Orbit sample expectations fail.
- [ ] Harvest `daniyal.pro`, generate the 32-second portfolio reel with real captures, then replace the pre-baked sample assets without committing frame sequences.
- [ ] Run all backend tests, all frontend tests, typecheck, production build, and desktop/mobile/reduced-motion browser checks.
- [ ] Verify final MP4 with `ffprobe`, strict media QA, and `volumedetect`: H.264/AAC, 1080×1920, 30/1fps, 960 frames, 32 seconds, non-silent, stream durations within 0.1s.
- [ ] Record verified tests; do not commit unless requested: `feat: bundle cinematic portfolio demo`.
