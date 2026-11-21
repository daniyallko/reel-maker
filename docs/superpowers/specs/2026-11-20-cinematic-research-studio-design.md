# Cinematic Research Studio Design

Date: 2026-11-20

## Intent

Turn the current URL-oriented animated slideshow into a universal cinematic story pipeline. A user supplies a topic, description, or URL with optional documents and images. The system researches the subject, writes a grounded narrative, directs a variable sequence of motion-design shots, aligns narration and sound to the edit, and exports a vertical video.

The user explicitly skipped requirement questions. The implementation choices in this document are the builder's calls, not additional user requirements.

## Goals

- Run external research for text, document, image, mixed, and URL inputs.
- Use Gemini for research planning and evidence synthesis in addition to retrieval.
- Preserve supplied documents and images as evidence and visual assets.
- Replace the fixed website arc with a grounded narrative and variable shot plan.
- Support screenshots, source images, generated art, kinetic typography, diagrams, and data scenes.
- Generate only the raster assets a scene needs; render typography, diagrams, and data procedurally.
- Align scene starts, narration segments, captions, transitions, and SFX.
- Select music from the requested style instead of always using `comedy.wav`.
- Audit narrative/asset relevance as well as typography, layout, and motion.
- Keep the existing multipart API, project snapshots, downloads, and legacy sample readable.

## Non-goals

- No generated-video provider in this iteration. Cinematic motion graphics do not require one.
- No audio/video uploads, PDF OCR, Remotion migration, public deployment, or new frontend framework.
- No claim that Gemini TTS supplies word-level timestamps. This iteration guarantees scene-level audio alignment and bounds estimated word captions to measured scene audio.
- No arbitrary increase in upload, source-text, render-duration, or memory limits.
- No silent substitution of the bundled Orbit or portfolio imagery for unrelated topics.

## Constraints

- Keep Python 3.12, FastAPI, LangGraph, Gemini, Playwright, FFmpeg, Next.js, and the existing provider adapters.
- Keep output at 1080×1920, 30 fps, H.264/yuv420p, AAC 48 kHz, and 30–40 seconds.
- Keep strict/draft review behavior: strict scores at least 8; draft scores at least 7 and labels unreviewed fallback.
- Keep `window.seekTo(t)` deterministic and prohibit network access, wall-clock animation, and external resources in motion HTML.
- Keep all critical content inside y=160–1580 and reserve the lower caption zone.
- Keep the 3 GiB backend memory cap and two FFmpeg encoder threads.
- Accept 4–8 contiguous scenes for compatibility. Ask the live scriptwriter for 6–8 scenes; legacy four-scene fixtures and portfolio output remain valid.
- Include at most four uploaded images in each multimodal AI request. All validated images remain available to the visual builder.
- Use at most eight deduplicated research sources, 4,000 retrieved characters per source, and 24,000 combined retrieved characters.

## Research contracts

Add `ResearchPlan` and `ResearchReport` contracts.

`ResearchPlan` contains:

- `topic`: normalized subject from the user brief, not necessarily a URL hostname.
- `angle`: narrative research angle appropriate to the selected style.
- `queries`: one to four bounded search queries.

`ResearchReport` contains:

- `topic`, `angle`, `queries`, and `summary`.
- `claims`: evidence statements with `source_refs` into the report's source list.
- `sources`: existing `SourceCitation` objects.
- `external_research`: whether non-inline external evidence was used.
- `provider`: actual research synthesis provider or `deterministic`.

Extend `SourceCitation` with excluded retrieved `content` so long source text does not leak into project JSON or downloads.

The research orchestrator plans from the supplied bundle, harvests URLs, retrieves external evidence for every non-sample input, merges and deduplicates citations, and asks Gemini to synthesize the report. Empty or failed retrieval falls back to supplied evidence and records deterministic/degraded behavior. It never invents citations.

## Narrative and shot contracts

Keep `Storyboard` and `StoryScene` as the public output models. Add these `StoryScene` fields with defaults for legacy data:

- `visual_type`: `screenshot | source_image | generated_art | kinetic_type | diagram | data`.
- `layout`: `hero | split | bento | full_bleed`.
- `camera`: `push_in | pull_out | pan_left | pan_right | static`.
- `animation`: `clip_reveal | stagger | counter_roll | path_draw | parallax`.
- `transition`: `cut | wipe | whip | dissolve`.
- `sfx`: `whoosh | pop | bass_drop | none`.
- `callouts`: zero to four short labels for diagrams and supporting visual structure.
- `metrics`: zero to three `{label,value,display}` objects for sourced data scenes.

Validation requires unique scene IDs, contiguous increasing times, 30–40 seconds total, at least 1.8 seconds per scene, headlines of at most 42 characters, and nonempty in-range `source_refs`. Data scenes require metrics. Diagram scenes require at least two callouts.

The prompt requests a researched narrative with 6–8 scenes. Narration and concise on-screen text serve different purposes. The fallback uses research claims rather than generic landing-page phrases.

## Visual asset builder

Create a scene-aware visual builder. It returns one primary asset per scene plus one cover, with stable IDs such as `scene-hook`; the cover never becomes a scene's fallback by positional accident.

Routing:

- `screenshot`: use a captured website screenshot when available.
- `source_image`: use an uploaded or harvested source image.
- `generated_art`: call the existing image provider for that scene.
- `kinetic_type`, `diagram`, and `data`: create only a procedural background; the motion template draws the meaningful content.

A failed art request falls back only that scene to relevant source imagery or a procedural background. Missing assets never select the unrelated Orbit sample. A source screenshot is chosen only when the scene requests it.

## Cinematic motion renderer

Move the deterministic cinematic templates into a focused module and retain `fallback_motion_html` as the compatibility entry point.

Templates provide:

- Masked and staggered headline reveals without a static full-narration paragraph.
- Media hero/split/full-bleed compositions with camera drift and crop changes.
- Procedural diagram nodes and deterministic path drawing.
- Sourced metric counters and bars using `metrics`, never invented values.
- Scene-specific transitions and camera behavior from the shot contract.
- A fresh meaningful composition every 1.8–3.0 seconds in long scenes.
- Stable `data-scene-id`, `data-visual-type`, and critical-element markers for browser tests.

The AI motion prompt receives the same typed direction. It must not turn every subject into a 3D website screenshot. Sanitization and deterministic-clock validation remain mandatory.

## Narration-aligned timeline

Keep initial storyboard duration as the final 30–40 second container. The existing audio producer measures each narration segment and tempo-fits only segments longer than their initial slots.

A new timeline stage then:

1. Computes scene lengths from measured narration plus visual hold time while preserving total storyboard duration.
2. Guarantees every retimed scene contains its complete narration segment.
3. Pads each segment to its retimed scene length and concatenates the padded segments.
4. Updates the storyboard in state before motion, review, captions, SFX, and rendering.

Word captions remain estimates within each measured narration segment. They start at the retimed scene start and never spill into the next scene. Telemetry says scene-aligned narration, not exact word synchronization.

Map styles to existing music: `launch → action.wav`, `tech_launch → scifi.wav`, `deep_dive → indie.wav`, `founder → indie.wav`, and `roast → comedy.wav`.

Build SFX inputs and delays from each scene's actual `sfx` and retimed `start`; omit `none` cues.

## Creative QA

Generate review timestamps from the storyboard rather than fixed 32-second timestamps. Include a hook motion pair, every scene midpoint, and a final frame; cap the set at 12 frames. Build contact sheets with enough rows for the actual frame count.

Extend visual review to six criteria:

- typography/contrast
- safe-zone compliance
- editorial craft
- visual momentum
- narrative alignment
- asset relevance

Prompts must explicitly penalize irrelevant screenshots, abstract placeholder subjects, generic website copy, and repeated compositions. Existing provider retry and strict/draft rules remain unchanged. Technical media QA remains separate.

## Frontend and telemetry

Extend TypeScript scene types without removing existing fields. The scene timeline displays visual type and supports eight scenes. Rename provider-centric stage labels to describe actual work: story research, narrative scriptwriting, scene asset direction, narration, and motion direction.

Update backend messages so they no longer claim a fixed four-act map, exact word timing, or six fixed audit stills.

## Acceptance criteria

- A text-only ocean-robot brief performs external query retrieval and produces a researched, cited non-website narrative.
- A document/image-only brief retains supplied evidence and assets even if external retrieval fails.
- A six-scene storyboard produces six matching scene assets plus one cover, with no positional cover reuse.
- Deterministic rendering covers every visual type, passes browser safe-zone/determinism tests, and does not display full narration as a static paragraph.
- Retimed narration and captions never cross scene boundaries; SFX delays equal retimed scene starts.
- All five styles select their mapped music.
- Review frames cover every scene and all six creative criteria are validated.
- Backend and frontend tests, typecheck, production build, media QA, and browser tests pass. Live provider smoke is reported separately and never marked passed when not run.
