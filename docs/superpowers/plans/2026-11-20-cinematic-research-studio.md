# Cinematic Research Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a universal researched narrative and cinematic motion-design pipeline for topic, document, image, mixed, and URL inputs.

**Architecture:** Preserve the current multipart API and Playwright/FFmpeg renderer. Add explicit research and shot contracts, route each scene to the right asset/template, retime the storyboard from measured narration, and expand creative QA to narrative and asset relevance.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, Pydantic 2, Gemini, Firecrawl/DDGS, Pillow, Playwright, FFmpeg, Next.js 16, React 19, TypeScript, pytest, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-20-cinematic-research-studio-design.md`

## Global Constraints

- Keep output at 1080×1920, 30 fps, H.264/yuv420p, AAC 48 kHz, and 30–40 seconds.
- Accept 4–8 contiguous scenes; live prompts request 6–8. Legacy four-scene sample data remains readable.
- Keep `window.seekTo(t)` deterministic; prohibit wall-clock animation, network access, and external resources.
- Keep critical content inside y=160–1580 and reserve the lower caption zone.
- Keep strict scores at least 8, draft scores at least 7, and labeled unreviewed fallback.
- Keep the 3 GiB backend memory cap and two FFmpeg encoder threads.
- Use at most four uploaded images per multimodal AI request; retain all validated images for visual routing.
- Use at most eight deduplicated research sources, 4,000 retrieved characters per source, and 24,000 combined retrieved characters.
- Do not add a generated-video provider, PDF OCR, audio/video uploads, Remotion, or a new frontend framework.
- Do not claim exact word-level TTS alignment. Guarantee scene-level alignment and bound estimated word captions to measured scene audio.

## Review Focus

- Image-only or empty-retrieval input: retain supplied evidence and assets without inventing facts; pinned by `test_image_only_research_retains_supplied_evidence` and `test_failed_art_uses_local_procedural_fallback` in Tasks 1 and 4.
- Long or short narration: preserve total duration and contain every complete segment after retiming; pinned by `test_retime_contains_measured_narration` and `test_aligned_audio_matches_storyboard_duration` in Task 6.
- Missing source assets or partial art failure: never use Orbit or reuse the cover as an unrelated scene; pinned by `test_failed_art_uses_local_procedural_fallback` and `test_scene_assets_are_unique_and_cover_is_separate` in Task 4.
- Invalid model direction: reject uncited scenes, invalid source indexes, data without metrics, and diagrams without callouts; pinned by `test_direction_requires_valid_evidence_and_visual_payloads` in Task 3.
- Hostile source text and off-screen motion: preserve escaped deterministic HTML and safe zones for every scene type; pinned by `test_source_markup_cannot_break_motion_clock_or_inject_html` and `test_cinematic_scenes_stay_deterministic_and_inside_safe_zones` in Task 5.

---

### Task 1: Universal Research Contracts and Retrieval

**Files:**
- Modify: `backend/app/studio/schemas.py:18-38`
- Modify: `backend/app/studio/research.py:1-90`
- Test: `backend/tests/studio/test_universal_research.py`

**Interfaces:**
- Consumes: existing `SourceBundle`, `SourceCitation`, and DDGS/Firecrawl configuration.
- Produces:
  - `SourceCitation.content: str = Field(default="", exclude=True)`.
  - `ResearchPlan(topic: str, angle: str, queries: list[str])`.
  - `EvidenceClaim(text: str, source_refs: list[int])`.
  - `ResearchReport(topic, angle, summary, claims, sources, queries, external_research, provider)`.
  - `fallback_research_plan(bundle: SourceBundle, style: str) -> ResearchPlan`.
  - `fallback_research_report(bundle: SourceBundle, plan: ResearchPlan, sources: list[SourceCitation]) -> ResearchReport`.
  - `research_queries(url: str, queries: list[str], timeout: float = 10) -> list[SourceCitation]`.
  - `search_ddgs(query: str, max_results: int = 2) -> list[dict]` for deterministic tests.
  - Existing `research_url(url, title, timeout)` remains as a compatibility wrapper.

- [ ] **Step 1: Write the failing tests**

```python
def test_text_topic_builds_external_research_plan():
    plan = fallback_research_plan(ingest_text("Ocean cleanup robots"), "deep_dive")
    assert plan.topic == "Ocean cleanup robots"
    assert 1 <= len(plan.queries) <= 4
    assert all("Ocean cleanup robots" in query for query in plan.queries)


def test_image_only_research_retains_supplied_evidence():
    bundle = ingest_text("Uploaded image: robot.png", title="robot.png")
    plan = fallback_research_plan(bundle, "deep_dive")
    report = fallback_research_report(bundle, plan, [])
    assert report.provider == "deterministic"
    assert report.claims
    assert report.sources[0].url.startswith("inline://")


@pytest.mark.asyncio
async def test_topic_research_dedupes_and_bounds_sources(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr("app.studio.research.search_ddgs", lambda query, max_results=2: [
        {"href": "https://example.com/robots", "title": "Robots", "body": "Ocean cleanup evidence"}
    ])
    sources = await research_queries("inline://text", ["ocean robots", "ocean robots explained"], timeout=1)
    assert len(sources) == 1
    assert sources[0].content == "Ocean cleanup evidence"
    assert "content" not in sources[0].model_dump()
```

Add a retrieval test proving eight-source, 4,000-character-per-source, and 24,000-character-total bounds.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_universal_research.py -q`
Expected: FAIL because the research contracts and functions do not exist.

- [ ] **Step 3: Implement research contracts and bounded retrieval**

Add the models with claim-reference validation. Generalize Firecrawl to query search, use parallel DDGS queries, dedupe by normalized URL, bound content, and return no fake primary citation for `inline://` inputs. Preserve the old `research_url` behavior for URL callers.

- [ ] **Step 4: Run research tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_universal_research.py tests/studio/test_research_speed.py tests/studio/test_graph_sources.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/schemas.py backend/app/studio/research.py backend/tests/studio/test_universal_research.py
git commit -m "feat: add universal research evidence contracts" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 2: Gemini Research Synthesis and Graph Integration

**Files:**
- Modify: `backend/app/studio/providers.py:200-250`
- Modify: `backend/app/studio/graph.py:26-113`
- Test: `backend/tests/studio/test_universal_research.py`
- Test: `backend/tests/studio/test_graph_sources.py`

**Interfaces:**
- Consumes: Task 1 research contracts and retrieval.
- Produces:
  - `GeminiStudioProvider.plan_research(harvest: SourceBundle, style: str) -> ResearchPlan`.
  - `GeminiStudioProvider.synthesize_research(harvest: SourceBundle, plan: ResearchPlan, sources: list[SourceCitation]) -> ResearchReport`.
  - `research_bundle(provider, bundle: SourceBundle | None, source_url: str, project_dir: Path, sample: bool = False, style: str = "deep_dive") -> tuple[SourceBundle, ResearchReport]`.
  - `StudioState.research_report: ResearchReport`.
  - `write_storyboard(..., research: ResearchReport | None = None)` optional keyword added without removing existing parameters.

- [ ] **Step 1: Write failing orchestration and provider tests**

```python
@pytest.mark.asyncio
async def test_text_only_graph_researches_and_synthesizes(monkeypatch, tmp_path):
    bundle = ingest_text("Ocean cleanup robots")
    seen = []

    async def fake_queries(url, queries, timeout=10):
        seen.extend(queries)
        return [SourceCitation(url="https://example.com/ocean", title="Ocean evidence", claim="Robots collect plastic", content="Robots collect plastic")]

    class Provider:
        async def plan_research(self, harvest, style):
            return ResearchPlan(topic=harvest.title, angle="Systems", queries=["ocean cleanup robots"])
        async def synthesize_research(self, harvest, plan, sources):
            return fallback_research_report(harvest, plan, sources).model_copy(update={"provider": "gemini"})

    monkeypatch.setattr("app.studio.graph.research_queries", fake_queries)
    harvested, report = await research_bundle(Provider(), bundle, bundle.source_url, tmp_path)
    assert seen == ["ocean cleanup robots"]
    assert report.provider == "gemini"
    assert report.external_research is True
```

Add provider request tests asserting structured `ResearchPlan`/`ResearchReport` schemas, CORE then FALLBACK model order, 90-second timeouts, up to four image parts, and deterministic fallback on invalid responses.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_universal_research.py -q`
Expected: FAIL because provider research methods and `research_bundle` are missing.

- [ ] **Step 3: Implement provider research and orchestration**

Use structured Gemini calls with supplied evidence only. In `research_bundle`, plan from the original brief, harvest URLs concurrently where possible, run external retrieval for every non-sample input, merge uploaded evidence, and synthesize one report. Store the report in graph state and pass it to storyboard writing. Keep sample replay behavior unchanged and emit actual source/provider counts.

- [ ] **Step 4: Run integration tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_universal_research.py tests/studio/test_graph_sources.py tests/studio/test_provider_fallback.py tests/studio/test_providers.py -q`
Expected: PASS; old four-argument storyboard calls still work through the optional research keyword.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/providers.py backend/app/studio/graph.py backend/tests/studio/test_universal_research.py backend/tests/studio/test_graph_sources.py
git commit -m "feat: synthesize researched evidence for every input" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 3: Typed Narrative and Shot Direction

**Files:**
- Modify: `backend/app/studio/schemas.py:41-72`
- Modify: `backend/app/studio/providers.py:30-102,146-189,227-250`
- Create: `backend/tests/studio/directed_fixtures.py`
- Test: `backend/tests/studio/test_story_direction.py`
- Modify: `backend/tests/studio/test_providers.py`

**Interfaces:**
- Consumes: `ResearchReport` and supplied source bundle.
- Produces:
  - `SceneMetric(label: str, value: float, display: str)`.
  - `StoryScene.visual_type`, `layout`, `camera`, `animation`, `transition`, `sfx`, `callouts`, and `metrics` with the literal values and defaults specified in the design.
  - `directed_storyboard()` test fixture with six scenes at 0–2, 2–7, 7–12, 12–18, 18–25, and 25–32 seconds; types `screenshot`, `source_image`, `generated_art`, `kinetic_type`, `diagram`, and `data`.
  - Fixture diagram callouts `["Collect", "Sort", "Recycle"]`; fixture data metric `{label: "Collected", value: 1200, display: "1,200 kg"}`.
  - Fixture SFX: `pop`, `whoosh`, `bass_drop`, then `none`; all scenes cite source 0.

- [ ] **Step 1: Write failing validation and narrative tests**

```python
def test_direction_supports_six_typed_scenes():
    storyboard = directed_storyboard()
    assert len(storyboard.scenes) == 6
    assert storyboard.scenes[-1].metrics[0].display == "1,200 kg"
    assert storyboard.scenes[-2].callouts == ["Collect", "Sort", "Recycle"]


def test_direction_requires_valid_evidence_and_visual_payloads():
    payload = directed_storyboard().model_dump()
    payload["scenes"][0]["source_refs"] = []
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)
    payload = directed_storyboard().model_dump()
    payload["scenes"][-1]["metrics"] = []
    with pytest.raises(ValidationError):
        Storyboard.model_validate(payload)
```

Also test rejection of three scenes, nine scenes, duplicate IDs, scenes shorter than 1.8 seconds, out-of-range references, diagrams with fewer than two callouts, and headlines longer than 42 characters. Test the fallback narrative uses `ResearchReport.claims` and contains none of `Behind the landing page`, `The story behind the page`, or `The takeaway is simple`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_story_direction.py -q`
Expected: FAIL on missing scene fields and validators.

- [ ] **Step 3: Implement typed scenes and researched scriptwriting**

Add defaults so legacy four-scene objects validate. Enforce 4–8 scenes, unique IDs, contiguous timing, evidence references, and visual payloads. Change the live prompt to request 6–8 researched scenes with separate narration/screen text and typed direction. Make fallback scenes from research claims, retaining the old function signature with optional `research`. Assign explicit visual/SFX direction to the mock and portfolio storyboards so portfolio scenes continue using real screenshots/source images rather than defaulting to generated art.

- [ ] **Step 4: Run story and compatibility tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_story_direction.py tests/studio/test_providers.py tests/studio/test_portfolio_demo.py -q`
Expected: PASS, including legacy four-scene mock and portfolio fixtures.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/schemas.py backend/app/studio/providers.py backend/tests/studio/directed_fixtures.py backend/tests/studio/test_story_direction.py backend/tests/studio/test_providers.py
git commit -m "feat: direct typed cinematic story scenes" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 4: Scene-Aware Visual Asset Builder

**Files:**
- Create: `backend/app/studio/visuals.py`
- Modify: `backend/app/studio/providers.py:105-131,252-286,338-347`
- Test: `backend/tests/studio/test_visual_assets.py`
- Modify: `backend/tests/studio/test_motion.py`

**Interfaces:**
- Consumes: typed `Storyboard`, `SourceBundle`, and provider `_generate_one_visual(prompt, references, path)`.
- Produces:
  - `build_scene_visuals(storyboard: Storyboard, harvest: SourceBundle | None, project_dir: Path, generate_art: Callable[[str, list[Path], Path], Awaitable[bool]] | None = None) -> list[StudioAsset]`.
  - One primary asset per scene with ID `scene-{scene.id}`, followed by one `thumbnail` cover.
  - `GeminiStudioProvider.generate_visuals` and `MockStudioProvider.generate_visuals` delegate to this builder.

- [ ] **Step 1: Write failing asset-routing tests**

```python
@pytest.mark.asyncio
async def test_scene_assets_are_unique_and_cover_is_separate(tmp_path):
    calls = []
    async def generate(prompt, references, path):
        calls.append(prompt)
        Image.new("RGB", (1080, 1920), "#204060").save(path)
        return True
    assets = await build_scene_visuals(directed_storyboard(), ingest_text("Ocean robots"), tmp_path, generate)
    assert len(assets) == 7
    assert [asset.id for asset in assets[:-1]] == [f"scene-{scene.id}" for scene in directed_storyboard().scenes]
    assert assets[-1].kind == "thumbnail"
    assert len(calls) == 2  # one generated_art scene plus cover


@pytest.mark.asyncio
async def test_failed_art_uses_local_procedural_fallback(tmp_path):
    async def fail(*_):
        return False
    assets = await build_scene_visuals(directed_storyboard(), ingest_text("No source images"), tmp_path, fail)
    assert len(assets) == 7
    assert all(asset.local_path.exists() for asset in assets)
    assert all("orbit-hero" not in str(asset.local_path) for asset in assets)
```

Add tests proving uploaded images are preferred for `source_image`, screenshots only for `screenshot`, procedural scenes do not call the art provider, and one failed art request does not replace successful scenes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_visual_assets.py -q`
Expected: FAIL because `build_scene_visuals` does not exist.

- [ ] **Step 3: Implement visual routing**

Create stable per-scene assets and a separate cover. Generate art only for `generated_art` and the cover. Create procedural backgrounds for `kinetic_type`, `diagram`, `data`, and missing-media fallbacks. Preserve relevant uploads/source images and never fall back to the bundled Orbit image for unrelated input.

- [ ] **Step 4: Run visual and existing motion tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_visual_assets.py tests/studio/test_motion.py -q`
Expected: PASS after updating positional-asset expectations to the new explicit contract.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/visuals.py backend/app/studio/providers.py backend/tests/studio/test_visual_assets.py backend/tests/studio/test_motion.py
git commit -m "feat: route visual assets by scene direction" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 5: Deterministic Cinematic Scene Templates

**Files:**
- Create: `backend/app/studio/cinematic.py`
- Modify: `backend/app/studio/motion.py:74-236`
- Test: `backend/tests/studio/test_cinematic_motion.py`
- Modify: `backend/tests/studio/test_motion.py`

**Interfaces:**
- Consumes: typed scenes and ordered per-scene assets from Task 4.
- Produces:
  - `cinematic_motion_html(storyboard: Storyboard, assets: list[StudioAsset], accent: str = "#d4a853") -> str`.
  - `fallback_motion_html` delegates to `cinematic_motion_html` without changing its public signature.
  - DOM markers `data-scene-id`, `data-visual-type`, and `data-critical` for browser validation.

- [ ] **Step 1: Write failing template and browser tests**

```python
@pytest.mark.asyncio
async def test_every_visual_type_has_a_distinct_template(tmp_path):
    storyboard = directed_storyboard()
    assets = await build_scene_visuals(storyboard, ingest_text("Ocean robots"), tmp_path)
    html = cinematic_motion_html(storyboard, assets)
    for visual_type in ("screenshot", "source_image", "generated_art", "kinetic_type", "diagram", "data"):
        assert f'data-visual-type="{visual_type}"' in html
```

Add `test_cinematic_scenes_stay_deterministic_and_inside_safe_zones`: seek every scene midpoint plus 0.5 seconds, assert identical pixels when returning to the same timestamp, exactly one active scene, loaded images, no horizontal overflow, every `data-critical` rectangle within y=160–1580, and no rendered static full-narration paragraph. Add assertions that diagram stroke state and data counter text change with time, each scene uses its matching asset, and long scenes change composition within 1.8–3.0 seconds.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_cinematic_motion.py -q`
Expected: FAIL because cinematic templates and markers do not exist.

- [ ] **Step 3: Implement cinematic templates**

Build deterministic media, kinetic-type, diagram, and data templates. Use scene `layout`, `camera`, `animation`, and `transition`; remove the static narration paragraph; use escaped `callouts` and `metrics`; draw SVG paths/counters from `t`; preserve safe zones and phase changes. Update the AI motion prompt to follow typed direction instead of forcing website slabs for every subject. Keep sanitization and `validate_motion_clock` mandatory.

- [ ] **Step 4: Run all motion security and geometry tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_cinematic_motion.py tests/studio/test_motion.py -q`
Expected: PASS, including hostile source markup, deterministic clock, no overlap, and safe-zone checks.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/cinematic.py backend/app/studio/motion.py backend/tests/studio/test_cinematic_motion.py backend/tests/studio/test_motion.py
git commit -m "feat: render cinematic typed motion scenes" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 6: Narration-Aligned Timeline and Captions

**Files:**
- Create: `backend/app/studio/timeline.py`
- Modify: `backend/app/studio/schemas.py:75-80`
- Modify: `backend/app/studio/audio.py:20-69`
- Modify: `backend/app/studio/graph.py:101-113,178-197`
- Modify: `backend/app/studio/renderer.py:30-54`
- Test: `backend/tests/studio/test_timeline.py`
- Modify: `backend/tests/studio/test_renderer.py`

**Interfaces:**
- Consumes: measured narration segments and initial storyboard.
- Produces:
  - `StudioAudio.segment_paths: list[Path] = Field(default_factory=list, exclude=True)`.
  - `retime_storyboard(storyboard: Storyboard, measured: list[float]) -> Storyboard`.
  - `align_audio_timeline(storyboard: Storyboard, audio: StudioAudio, project_dir: Path) -> tuple[Storyboard, StudioAudio]`.
  - A `timing` graph node after `visuals` and `audio`, before `motion`.

- [ ] **Step 1: Write failing timing tests**

```python
def test_retime_contains_measured_narration():
    storyboard = directed_storyboard()
    measured = [1.2, 3.5, 2.0, 4.5, 3.0, 2.2]
    retimed = retime_storyboard(storyboard, measured)
    assert retimed.duration == storyboard.duration == 32
    assert retimed.scenes[0].start == 0
    assert abs(retimed.scenes[-1].end - 32) < 0.001
    for scene, duration in zip(retimed.scenes, measured, strict=True):
        assert scene.end - scene.start >= duration
    for previous, current in zip(retimed.scenes, retimed.scenes[1:], strict=False):
        assert current.start == previous.end
```

Add tests for equal-length lists, rejection of zero/negative measured values, rejection of measured audio longer than its initial scene slot, very short and slot-filling narration, and no scene shorter than 1.8 seconds. Add `test_aligned_audio_matches_storyboard_duration` using short generated WAV segments; assert `media_duration(aligned.voice_path) == 32` and segment paths/durations remain aligned with their scenes.

For captions, assert every word event for scene `i` starts at `retimed.scenes[i].start`, ends no later than `scene.start + measured[i]`, and never crosses `scene.end`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_timeline.py tests/studio/test_renderer.py::test_word_level_ass_captions -q`
Expected: FAIL because retiming, aligned audio, and caption bounds do not exist.

- [ ] **Step 3: Implement measured timeline alignment**

Populate `segment_paths` in `produce_audio`. In `retime_storyboard`, require one positive measured duration per scene and reject any duration exceeding its initial slot; initial per-scene tempo fitting guarantees this invariant for pipeline audio. Start with `max(1.8, measured)` per scene, distribute remaining visual hold proportionally to initial scene lengths, and preserve total duration. In `align_audio_timeline`, pad each segment to its retimed slot, concatenate, and return updated models. Clamp captions to measured narration within each retimed scene. Change telemetry to `Narration aligned to scene timings.`

- [ ] **Step 4: Run audio, graph, and renderer tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_timeline.py tests/studio/test_renderer.py tests/studio/test_async_renderer.py tests/studio/test_providers.py tests/studio/test_heartbeat.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/timeline.py backend/app/studio/schemas.py backend/app/studio/audio.py backend/app/studio/graph.py backend/app/studio/renderer.py backend/tests/studio/test_timeline.py backend/tests/studio/test_renderer.py
git commit -m "fix: align narration and captions to directed scenes" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 7: Style Music and Timeline-Driven SFX

**Files:**
- Modify: `backend/app/studio/audio.py:9-20,63-69`
- Modify: `backend/app/studio/renderer.py:57-84`
- Test: `backend/tests/studio/test_audio_direction.py`
- Modify: `backend/tests/studio/test_renderer.py`

**Interfaces:**
- Consumes: retimed storyboard and scene `sfx` values.
- Produces:
  - `music_for_style(style: str) -> Path`.
  - Exact mapping `launch → action.wav`, `tech_launch → scifi.wav`, `deep_dive → indie.wav`, `founder → indie.wav`, `roast → comedy.wav`.
  - `build_mix_command` retains its signature but creates only required SFX inputs and delays from scene starts.

- [ ] **Step 1: Write failing audio-direction tests**

```python
def test_every_style_selects_its_music():
    assert music_for_style("launch").name == "action.wav"
    assert music_for_style("tech_launch").name == "scifi.wav"
    assert music_for_style("deep_dive").name == "indie.wav"
    assert music_for_style("founder").name == "indie.wav"
    assert music_for_style("roast").name == "comedy.wav"


def test_sfx_follow_retimed_scene_starts(tmp_path):
    storyboard = retime_storyboard(directed_storyboard(), [1.2, 3.5, 2.0, 4.5, 3.0, 2.2])
    command = build_mix_command(tmp_path, storyboard, tmp_path / "voice.wav", tmp_path / "music.wav", tmp_path / "captions.ass", tmp_path / "trailer.mp4")
    graph = next(part for part in command if "sidechaincompress" in part)
    for scene in storyboard.scenes:
        if scene.sfx != "none":
            assert f"adelay={round(scene.start * 1000)}|{round(scene.start * 1000)}" in graph
    assert "adelay=25000|25000" not in graph
```

Add a test that `none` cues create no input and that `bass_drop` maps to `drop.wav`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_audio_direction.py -q`
Expected: FAIL on fixed comedy music and hardcoded SFX delays.

- [ ] **Step 3: Implement style music and dynamic mixing**

Select music in `produce_audio`. Build unique SFX inputs in encounter order, map `bass_drop` to `drop.wav`, generate one delayed stream per non-`none` scene cue, and adjust `amix` input count. Preserve ducking, loudness normalization, one filter thread, and two encoder threads.

- [ ] **Step 4: Run audio and mix tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_audio_direction.py tests/studio/test_renderer.py tests/studio/test_async_renderer.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/audio.py backend/app/studio/renderer.py backend/tests/studio/test_audio_direction.py backend/tests/studio/test_renderer.py
git commit -m "feat: sync style music and sfx to the edit" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 8: Storyboard-Driven Creative QA

**Files:**
- Modify: `backend/app/studio/vision.py:11-92,95-161`
- Modify: `backend/app/studio/vision_providers.py:11-16`
- Modify: `backend/app/studio/graph.py:115-160`
- Test: `backend/tests/studio/test_creative_qa.py`
- Modify: `backend/tests/studio/test_vision_fallback.py`
- Modify: `backend/tests/studio/test_vision_providers.py`

**Interfaces:**
- Consumes: final retimed storyboard and deterministic motion HTML.
- Produces:
  - `director_review_times(storyboard: Storyboard) -> list[float]`.
  - Six required criteria: existing four plus `narrative alignment` and `asset relevance`.
  - Dynamic-height contact sheets and storyboard-derived graph review times.

- [ ] **Step 1: Write failing review-coverage tests**

```python
def test_review_times_cover_every_scene_and_motion_pair():
    storyboard = directed_storyboard()
    times = director_review_times(storyboard)
    assert len(times) <= 12
    assert times[:2] == [0.6, 1.0]
    assert times[-1] == 31.5
    for scene in storyboard.scenes:
        assert round((scene.start + scene.end) / 2, 3) in times


def test_creative_audit_requires_narrative_and_asset_relevance():
    assert "narrative alignment" in REQUIRED_CRITERIA
    assert "asset relevance" in REQUIRED_CRITERIA
    assert len(REQUIRED_CRITERIA) == 6
```

Add tests that contact-sheet height is `ceil(len(times)/3) * 640`, all provider prompts mention narrative alignment, asset relevance, irrelevant screenshots, and abstract placeholders, and all six scores use existing strict/draft thresholds.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_creative_qa.py -q`
Expected: FAIL on fixed times, four criteria, and fixed contact-sheet height.

- [ ] **Step 3: Implement dynamic creative QA**

Create a hook pair at 0.6/1.0 seconds, include every scene midpoint and `duration-0.5`, deduplicate and cap at 12 without dropping scene midpoints. Build enough contact-sheet rows. Extend both audit prompts and validation to six criteria. Use `director_review_times` in the graph and keep one repair attempt.

- [ ] **Step 4: Run all vision tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests/studio/test_creative_qa.py tests/studio/test_vision_fallback.py tests/studio/test_vision_providers.py tests/studio/test_motion.py -q`
Expected: PASS with shared six-criterion test fixtures.

- [ ] **Step 5: Commit**

```bash
git add backend/app/studio/vision.py backend/app/studio/vision_providers.py backend/app/studio/graph.py backend/tests/studio/test_creative_qa.py backend/tests/studio/test_vision_fallback.py backend/tests/studio/test_vision_providers.py
git commit -m "feat: audit narrative and asset relevance" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 9: Frontend Shot Map and Truthful Telemetry

**Files:**
- Modify: `frontend/lib/types.ts:97-137`
- Modify: `frontend/components/scene-timeline.tsx:11-30`
- Modify: `frontend/components/studio-screening.tsx:14-24`
- Modify: `backend/app/studio/graph.py:87-105,115-160`
- Modify: `frontend/tests/studio-fixtures.ts`
- Test: `frontend/tests/scene-timeline.test.tsx`
- Test: `frontend/tests/studio-screening.test.tsx`

**Interfaces:**
- Consumes: expanded `StudioOutput.scenes` and backend events.
- Produces: optional TypeScript `visual_type`, `layout`, `camera`, `animation`, `transition`, `sfx`, `callouts`, and `metrics` fields so old saved output remains readable; a `directedScenes` fixture matching the six backend fixture scenes; visual-type labels in the shot map.

- [ ] **Step 1: Write failing frontend tests**

```tsx
it("shows directed visual types and seeks variable scenes", () => {
  const onSeek = vi.fn();
  render(<SceneTimeline scenes={directedScenes} currentTime={0} onSeek={onSeek} />);
  expect(screen.getByText("diagram")).toBeInTheDocument();
  expect(screen.getByText("data")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /25.0s/ }));
  expect(onSeek).toHaveBeenCalledWith(25.01);
});
```

Add a screening test for labels `Story Researcher`, `Narrative Scriptwriter`, `Scene Asset Director`, `Narration Studio`, and `Motion Director`; assert removed provider/fixed-act wording is absent.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- scene-timeline.test.tsx studio-screening.test.tsx`
Expected: FAIL because visual-type labels and new process names are absent.

- [ ] **Step 3: Implement shot-map types and telemetry labels**

Extend optional TypeScript fields and fixtures. Display `visual_type ?? "scene"` in each scene button and keep the grid usable with eight scenes. Rename stage labels and update backend fixed-four/six-still messages to describe actual work and dynamic review counts.

- [ ] **Step 4: Run frontend unit and type tests**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types.ts frontend/components/scene-timeline.tsx frontend/components/studio-screening.tsx frontend/tests/studio-fixtures.ts frontend/tests/scene-timeline.test.tsx frontend/tests/studio-screening.test.tsx backend/app/studio/graph.py
git commit -m "feat: expose directed shot metadata in the studio" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

### Task 10: Sample Migration and Full Verification

**Files:**
- Modify: `backend/scripts/prebake_link2reel.py:27-60`
- Modify: `backend/scripts/e2e_studio_live.py:11-42`
- Modify: `README.md:1-89`
- Modify: `docs/superpowers/verification.md`
- Test: `backend/tests/studio/test_portfolio_demo.py`
- Test: `frontend/tests/studio-e2e.mjs`

**Interfaces:**
- Consumes: all prior task interfaces.
- Produces: a regenerated compatible portfolio sample, current documentation, and a verification ledger separating automated checks from live-provider evidence.

- [ ] **Step 1: Update sample and add regression assertions**

Use `build_scene_visuals`, cinematic motion, aligned audio, style music, and `director_review_times` in the pre-bake script. Preserve third-person portfolio evidence and the existing download schema. Add assertions that sample scenes contain valid typed direction and the audit uses six criteria when scores are present. Update README research, scene, asset, timing, and QA descriptions to match the code.

- [ ] **Step 2: Regenerate and inspect the sample**

Run: `cd backend && ../.venv/bin/python scripts/prebake_link2reel.py`
Expected: new `backend/assets/link2reel/sample-output/trailer.mp4`, cover, narration, sources, and contact sheet. Inspect the contact sheet manually; record actual scores or `Unreviewed draft` without claiming an unavailable audit passed.

- [ ] **Step 3: Run backend verification**

Run: `cd backend && ../.venv/bin/python -m pytest -q`
Expected: all backend tests PASS. Run `../.venv/bin/python -c "from pathlib import Path; from app.studio.renderer import SAMPLE_OUTPUT, verify_studio_video; print(verify_studio_video(SAMPLE_OUTPUT / 'trailer.mp4'))"` from `backend` and require `valid=True`.

- [ ] **Step 4: Run frontend and browser verification**

Run: `cd frontend && npm test && npm run typecheck && npm run build`
Expected: all PASS.
Run: `cd frontend && node tests/studio-e2e.mjs`
Expected: browser suite PASS with variable-scene seeking, citations, downloads, mobile layout, and reduced motion.

- [ ] **Step 5: Run live topic smoke only when configured**

Update `e2e_studio_live.py` so `STUDIO_TEST_TOPIC` posts multipart `/api/studio/projects/inputs`; otherwise it preserves the existing URL smoke. Replace the fixed four-scene assertion with 4–8 scenes generally and require 6–8 for the live topic path. Require all six critique criteria at least 8 in strict mode.

Run the existing URL smoke with `STUDIO_TEST_URL` unset. Then run `cd backend && STUDIO_TEST_TOPIC="A short cinematic documentary about ocean cleanup robots." ../.venv/bin/python scripts/e2e_studio_live.py`.
Expected when configured: external research is used, narrative is not website-template copy, the topic output has 6–8 cited scenes, assets are relevant, and final media QA passes. When no live key/provider is available, record `not run` and the reason; never record PASS.

- [ ] **Step 6: Record evidence and commit**

Write exact commands, results, test counts, sample review state, live-smoke status, and remaining limitations to `docs/superpowers/verification.md`.

```bash
git add backend/scripts/prebake_link2reel.py backend/scripts/e2e_studio_live.py backend/assets/link2reel/sample-output backend/tests/studio/test_portfolio_demo.py frontend/tests/studio-e2e.mjs README.md docs/superpowers/verification.md docs/superpowers/specs/2026-11-20-cinematic-research-studio-design.md docs/superpowers/plans/2026-11-20-cinematic-research-studio.md
git commit -m "test: verify the cinematic research studio" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Final Branch Review

- [ ] Run `git diff --check` and inspect the complete diff for accidental generated-project data, secrets, or unrelated legacy CUTLINE changes.
- [ ] Confirm the public multipart request and download schemas remain compatible.
- [ ] Confirm no fallback claims external research, exact word synchronization, or AI review that did not occur.
- [ ] Confirm final output remains within 30–40 seconds and the 3 GiB backend cap.
- [ ] Request one fresh whole-branch code review, then a visual review of the regenerated sample and live text-only contact sheet when available.
