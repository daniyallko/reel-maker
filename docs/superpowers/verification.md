# LINK2REEL verification ledger

Date: 2026-11-19

## Universal story studio

- Source inputs: URL, topic, description, pasted text, PDF, TXT, PNG, JPG, JPEG, and WebP.
- Upload bounds: 8 files, 10 MB per file, 30 MB total, 30,000 extracted characters, and 40 million pixels per image.
- Multipart endpoint: `POST /api/studio/projects/inputs`; legacy JSON URL endpoint retained.
- Vision routing: Gemini → OpenRouter → Groq → optional Anthropic, with two attempts and validated four-criterion responses.
- Strict mode requires four scores ≥8. Draft mode permits scores ≥7 and an explicitly labeled deterministic `Unreviewed draft` after failed or unavailable review.
- Draft labels appear in Premiere UI and metadata only, not burned into video.
- Uploaded content displays a configured-provider processing notice.

## Portfolio demo

- Source: `https://daniyal.pro` plus sanitized professional CV evidence.
- Title: `Mohd Daniyal — Production AI in Motion`.
- Narration: third person, with source-backed 1,000+ websites, 100,000+ users, sub-500ms first audio, and 99.9% uptime claims.
- Bundle: real portfolio captures, CV evidence, narration, cover, citations, and six-frame contact sheet.
- Review state: `Unreviewed draft` because the final pre-bake did not retain a valid AI audit score set.
- MP4: `backend/assets/link2reel/sample-output/trailer.mp4`.
- Video: H.264, 1080×1920, 30/1fps, 960 frames, 32.000000s.
- Audio: AAC, 32.000000s; mean volume -18.2 dB, maximum -1.5 dB.
- Strict media QA: valid, no errors.

## Live universal-source smoke test

- Project: `e284ead5e20e` (`inline://text` with uploaded document).
- Completed with output `A short cinematic documentary about ocean cleanup robots.`
- Visual audit: typography 10, safe zones 10, editorial craft 10, momentum 9.
- MP4: H.264/AAC, 1080×1920, 30/1fps, 960 frames, 32.000000s on both streams.
- Audio: mean volume -17.7 dB, maximum -1.5 dB.
- Fallback narration was subsequently tightened to remove generic template copy; provider tests pass.

## Automated verification

- Backend: **105/105 tests passed** in 53.19s.
- Frontend: **27/27 tests passed** across 10 files.
- TypeScript: `tsc --noEmit` passed.
- Production build: `next build` passed for `/` and `/project/[id]`.
- Browser suite: passed with 32-second portfolio playback, scene seeking, citations, script copy, ZIP, mobile overflow, and reduced motion checks. Latest browser project: `9b6242b3eadb`.
- Composer screenshots inspected on desktop and 375px mobile; no overflow or browser errors.
- Backend runs on port 8000 under a 3 GiB physical memory cap; Node heap is capped at 1.5 GiB.

## Independent review fixes

- Image-only bundles retain visual manifests and uploaded images reach the storyboard model as multimodal evidence.
- Source text is escaped for inline JSON and inserted with `textContent`, preventing script termination and HTML injection.
- URL jobs retain uploaded document/image citations.
- Uppercase HTTP(S) URLs remain web sources.
- Inline citations render as text instead of unsupported links.
- Deferred minor: combined typed/upload/harvested text can exceed 30,000 characters; enforce a post-merge bound later.

## Workspace

- Implementation branch: `feat/universal-story-studio`.
- Plan/spec: `docs/superpowers/plans/2026-11-19-universal-story-studio.md` and `docs/superpowers/specs/2026-11-19-universal-story-studio-design.md`.
- No commit or push has been created for this branch.
