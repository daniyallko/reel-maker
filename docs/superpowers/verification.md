# LINK2REEL verification ledger

Date: 2026-11-19

## Automated results

- Backend: **72/72 tests passed** in 49.11s.
- Frontend: **16/16 unit and component tests passed** across 7 files.
- TypeScript: `tsc --noEmit` passed.
- Production build: `next build` passed for `/` and `/project/[id]`.
- Offline browser suite: **passed** with a 32-second video, scene seeking, cited sources, script copy, valid MP4/PNG/ZIP downloads, 375px overflow checks, and reduced-motion checks. Browser project: `4ef5ad753666`.
- Memory: backend rendering ran under `systemd-run --user --scope -p MemoryMax=3G`; Node heap was capped at 1.5 GiB.
- Chromium sandbox disablement was removed from harvesting, motion validation, keyframe capture, and frame rendering.

## Motion-studio changes

- `motion.py`: added four scene grids and five-beat portrait/landscape phase changes, continuous camera drift, brand-accent extraction, 72px margins, safe text regions, and deterministic `window.seekTo(t)` choreography.
- `providers.py`: removed duplicate baked-in headlines, reduced source darkening, added evidence-only storyboard constraints, excluded embedded typography from generated art, and made narration fallback consistent across all four scenes.
- `harvest.py`: waits for network idle, fonts, and entrance motion before hero capture; mid-page capture also waits for motion.
- `vision.py`: requires four scores of at least 8/10 before rendering; missing or low scores fail the live job instead of reaching FFmpeg.
- `renderer.py`: verifies H.264, AAC, 1080×1920, 30fps, audio/video duration within 0.1s, successful decode, and non-silent audio.
- Offline sample: rebuilt with the approved template and six keyframes at 0.6, 3.5, 8, 14, 21, and 27 seconds.

## Live Linear production

- Project: `e79589e649e9`
- Source URL: `https://linear.app`
- Final contact sheet: `backend/data/e79589e649e9/audit/contact-sheet.png`
- Vision scores: typography/contrast **9**, safe-zone compliance **9**, editorial craft **9**, visual momentum **9**.
- Initial audits failed with overlapping duplicate typography and static compositions. The approved phase-layout audit passed all four criteria.
- Nano Banana artwork was unavailable for this run; the approved render uses deterministic crops of real Linear captures.
- Gemini TTS retry returned no audio for all four lines. All four Edge `en-US-ChristopherNeural` lines succeeded and replaced the earlier mixed narration.
- Final MP4: `backend/data/e79589e649e9/output/trailer.mp4`
- Cover: `backend/data/e79589e649e9/visuals/thumbnail-03.png` (1080×1920).
- Press kit: trailer MP4, thumbnail PNG, script TXT, and sources JSON verified through the download API.

### Final media probe

- Video: H.264, 1080×1920, 30/1 fps, 960 frames, 32.000000s.
- Audio: AAC, 32.000000s.
- Container: 32.000000s, 4,257,062 bytes.
- Strict QA: valid, with no errors.
- Mean volume: -18.1 dB; maximum volume: -1.5 dB.
- Integrated loudness: -16.2 LUFS; true peak: -1.5 dBFS.

## Runtime and git

- Frontend remains on port 3000.
- Patched verification backend runs on port 8001 under the physical memory cap and restores the Linear output with its 9/9/9/9 scores.
- The pre-existing port-8000 process could not be terminated by the agent. Restart it before expecting the patched code and restored output on port 8000.
- No refactor commit or push has been created.
