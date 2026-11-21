# Universal Story Studio design

Date: 2026-11-19

## Intent

Turn LINK2REEL from a URL-only studio into a cinematic story studio. A user can supply a URL, topic, description, pasted text, PDF, TXT file, or images and receive a sourced vertical motion reel. The bundled instant demo presents Mohd Daniyal's engineering portfolio using third-person narration.

## Goals

- Accept any of these source forms and allow images or documents to supplement a URL or text prompt.
- Preserve real source images in the video and ground narration in supplied evidence.
- Add independent Vision Director providers without hiding low-quality work.
- Make the homepage understandable without instructions and the project page show only the active process plus a technical response stream.
- Bundle a working offline portfolio demo with real captures from `https://daniyal.pro` and evidence from the supplied CV.
- Keep the existing 32-second, 1080×1920, 30fps, H.264/AAC renderer and 3 GiB backend memory cap.

## Non-goals

- No public unauthenticated deployment.
- No arbitrary executable uploads, archive extraction, or remote URL fetching from uploaded documents.
- No silent reduction of the strict 8/10 quality threshold.
- No invented achievements, customer claims, metrics, or portfolio content.
- No requirement for an Anthropic key; its adapter is optional because only Gemini, Groq, and OpenRouter keys are currently configured.

## Source model

Introduce a `SourceBundle` contract shared by every input type. Replace `HarvestResult` with this model and keep `HarvestResult = SourceBundle` as a compatibility alias:

- `kind`: `url | text | mixed | sample`.
- `title` and `source_url` or an `inline://text` identifier; project snapshots expose this as `source_title` and render links only for HTTP(S) sources.
- `dom_copy`: normalized extracted source text.
- `assets`: real images/screenshots available to the motion pipeline.
- `palette`, `fonts`, and `citations`.
- `screenshots` and `image_paths` for deterministic visual fallbacks.

Text and PDF inputs never pass `None` to the storyboard provider and never reach the hardcoded sample storyboard. Text-only inputs skip external URL research. `HarvestResult = SourceBundle` preserves existing imports during migration.

Input rules:

- URL input uses the existing SSRF-protected Playwright harvester.
- Non-URL input becomes a text source; it does not require a fake public URL.
- PDF and TXT input is extracted locally. PDF support uses `pypdf`; TXT decoding tries UTF-8 and reports undecodable files.
- Images use Pillow validation and become `StudioAsset` objects available to `fallback_visuals` and generated motion scenes.
- Allow at most 8 files, 10 MB per file, 30 MB total, and 30,000 extracted characters. Accepted extensions/MIME types are `.pdf`, `.txt`, `.png`, `.jpg`, `.jpeg`, and `.webp`.
- Keep the existing JSON URL endpoint for compatibility and add a multipart `/api/studio/projects/inputs` endpoint for the unified composer.
- Return bounded `422` errors for empty input, unsupported files, oversized uploads, invalid PDFs, and empty extraction.

## Provider and quality architecture

Create a common asynchronous `VisionProvider` interface returning the existing `VisionAudit` shape. Provider order is configurable with `VISION_PROVIDER_ORDER`, defaulting to `gemini,openrouter,groq,anthropic`.

- Gemini: retain the current provider and models.
- OpenRouter: OpenAI-compatible chat completions with base64 `image_url`; default model `inclusionai/ling-3.2-flash:free` and structured JSON schema where supported.
- Groq: OpenAI-compatible chat completions with base64 `image_url`; default model `qwen/qwen3.8-27b`; validate returned JSON with Pydantic.
- Anthropic: optional official `anthropic` Python SDK adapter using `claude-haiku-5-5`, base64 image input, and structured output. It remains inactive without `ANTHROPIC_API_KEY`.

Routing rules:

- Fall through only for authentication/configuration absence, timeout, connection failure, `429`, `5xx`, unavailable models, or invalid/schema-incomplete responses.
- Honor `retry-after`; use at most two attempts per configured provider and a 60-second timeout per attempt.
- Never fall through merely because a valid audit contains low scores.
- Split critique and motion repair. Audits contain only scores/issues; repair returns HTML separately and must pass sanitization, offline CSP, and `seekTo(t)` validation.
- Recompute pass/fail on the server from exactly four unique criteria; do not trust the model's `passed` flag.
- Emit provider/model/attempt/fallback details to the backend response stream without exposing keys.

Quality modes:

- `strict` remains the default and requires all four scores ≥8.
- `draft` is an explicit opt-in that permits scores ≥7 and labels the output `Unreviewed draft` in the Premiere UI and `StudioOutput.review_label`; it is not burned into video frames.
- A deterministic unaudited render is allowed only in draft mode and carries the same UI/metadata label; it never claims an AI audit passed.
- `quality_mode` is accepted by the API, persisted on jobs/output, and restored with completed projects.

## Portfolio demo

Bundle a sanitized CV source at `backend/assets/link2reel/portfolio/cv.txt`. It contains professional evidence from the supplied CV but omits phone numbers, email addresses, and street-level location details.

The 32-second third-person story:

1. Mohd Daniyal builds production AI systems.
2. AI BotKit on 1,000+ websites serving 100,000+ users.
3. Agentic AI, hybrid RAG, real-time voice, LangGraph, FastAPI, Next.js, and production infrastructure.
4. Sub-500ms voice response, multilingual RAG, podcast automation, 99.9% uptime, and `daniyal.pro`.

Use real portfolio captures and project imagery. Do not use stock people or invented interfaces. Pre-bake the MP4, cover, citations, narration, and six-frame contact sheet for instant offline replay using the same renderer as user projects.

## Homepage

Replace the greeting/avatar with a clear cinematic headline: “Your story. Cut like a film.” Add supporting copy explaining that text, links, PDFs, and images become vertical motion reels.

The composer contains:

- A large textarea with no “Source URL” label, magnifying-glass icon, or quick-link pills.
- File upload for the accepted document/image types.
- A visible one-line notice that uploaded content is sent to the user-configured AI providers for analysis; the user approved this disclosure and processing choice.
- More cinematic style and voice controls, including the existing `tech_launch` option with cinematic labels rather than new style identifiers.
- A large text generate button.
- A separate “Watch portfolio demo” button with no plus icon.
- Corrected species-pill alignment, margins, padding, and selected-pill geometry across desktop and mobile.

## Project page

Remove the entire application top bar, including logo, hamburger, reel ID, and create button.

Replace the generic screening masthead with “Building your cinematic reel”, the source title/URL, and a readable connection state. Show only the current agent with an animated `CircleNotch`, animated transitions between stages, progress, and backend message. Keep completed/failed responses in the technical log. On terminal failure, stop all execution animation and retain the failed response.

## Verification

- Unit tests for every source type, upload limit, malformed input, provider order, retry behavior, low-score handling, draft labeling, and optional-provider configuration.
- Component tests for the composer, uploads, species selection, active-stage transitions, failure state, and demo action.
- Real browser tests for desktop/mobile URL, text, and file submission, reduced motion, and instant portfolio playback.
- Full backend/frontend suites, typecheck, production build, and offline sample QA.
- Final portfolio MP4 is H.264/AAC, 1080×1920, 30/1fps, 32 seconds, non-silent, with matching stream durations and a valid cover.
