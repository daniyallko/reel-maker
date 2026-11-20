import asyncio
import json
import mimetypes
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from google import genai
from google.genai import types

from app.media.audio import VOICE
from app.media.poster import cover
from app.studio.audio import produce_audio
from app.studio.harvest import media_url
from app.studio.research import fallback_research_plan, fallback_research_report
from app.studio.schemas import (
    HarvestResult,
    ResearchPlan,
    ResearchReport,
    SourceCitation,
    Storyboard,
    StoryScene,
    StudioAsset,
    StudioAudio,
)

CORE_MODEL = "gemini-4-hydrogen"
VISUAL_MODEL = "gemini-nano-banana-2.1"
TTS_MODEL = "gemini-3.8-flash-tts"
TTS_API_VERSION = "v1beta"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def mock_storyboard(style: str, voice: str) -> Storyboard:
    scenes = [
        StoryScene(
            id="hook",
            start=0,
            end=2.5,
            headline="YOUR NEXT IDEA IS ALREADY IN ORBIT",
            narration="Your next big idea is already hiding in your notes.",
            visual_prompt="Kinetic 3D website slab slam with the Orbit Notes brand.",
            source_refs=[0],
            visual_type="screenshot",
            layout="full_bleed",
            camera="push_in",
            animation="clip_reveal",
            transition="cut",
            sfx="pop",
        ),
        StoryScene(
            id="problem",
            start=2.5,
            end=12,
            headline="SCATTERED THOUGHTS GET LOST",
            narration="Most notes apps store words. Orbit reconnects the thinking between them, so the idea you forgot comes back when it matters.",
            visual_prompt="Constellation of connected ideas resolving from scattered notes.",
            source_refs=[0, 1],
            visual_type="generated_art",
            layout="hero",
            camera="pan_right",
            animation="parallax",
            transition="wipe",
            sfx="whoosh",
        ),
        StoryScene(
            id="system",
            start=12,
            end=25,
            headline="LOCAL FIRST. LINKED BY DESIGN.",
            narration="The constellation view maps every link on your device. Offline search, open exports, and private sync keep deep work fast and portable.",
            visual_prompt="Real Orbit Notes interface with glowing graph connections and privacy callouts.",
            source_refs=[0, 1],
            visual_type="screenshot",
            layout="split",
            camera="pull_out",
            animation="stagger",
            transition="whip",
            sfx="bass_drop",
        ),
        StoryScene(
            id="takeaway",
            start=25,
            end=32,
            headline="THINK IN PUBLIC. KEEP IT YOURS.",
            narration="Seven minutes every Monday is enough to see what moved. Orbit Notes. Think in public, while keeping your thinking yours.",
            visual_prompt="Monday review card resolving into the Orbit Notes cover thumbnail.",
            source_refs=[0],
            visual_type="source_image",
            layout="hero",
            camera="static",
            animation="clip_reveal",
            transition="dissolve",
            sfx="none",
        ),
    ]
    return Storyboard(
        title="Orbit Notes — Think in Public",
        style=style,
        voice=voice,
        duration=32,
        bpm=128,
        scenes=scenes,
        sources=[
            SourceCitation(url="https://example.com/orbit", title="Orbit Notes product site", claim="Local-first notes, constellation links, offline search, open exports, and Monday review"),
            SourceCitation(url="https://example.com/orbit-review", title="Orbit Notes field review", claim="A seven-minute weekly review reconnects recent ideas"),
        ],
        speech_style="High-energy, precise product launch delivery with short pauses between acts",
    )


def portfolio_storyboard(style: str = "launch", voice: str = "Fenrir") -> Storyboard:
    return Storyboard(
        title="Mohd Daniyal — Production AI in Motion",
        style=style,
        voice=voice,
        duration=32,
        bpm=128,
        scenes=[
            StoryScene(
                id="hook",
                start=0,
                end=2.5,
                headline="PRODUCTION AI. REAL IMPACT.",
                narration="Mohd Daniyal builds production AI systems that turn complex research into reliable products.",
                visual_prompt="A dramatic close crop of the real Mohd Daniyal portfolio interface with no added text.",
                source_refs=[0, 1],
                visual_type="screenshot",
                layout="full_bleed",
                camera="push_in",
                animation="clip_reveal",
                transition="cut",
                sfx="pop",
            ),
            StoryScene(
                id="scale",
                start=2.5,
                end=12,
                headline="AI AT PRODUCTION SCALE",
                narration="As a core engineer on AI BotKit, Mohd helped build a multi-tenant RAG platform live on more than 1,000 websites and serving over 100,000 users.",
                visual_prompt="Real AI BotKit and portfolio product interfaces with layered depth and no invented metrics or text.",
                source_refs=[0, 1],
                visual_type="screenshot",
                layout="split",
                camera="pan_right",
                animation="parallax",
                transition="wipe",
                sfx="whoosh",
            ),
            StoryScene(
                id="engineering",
                start=12,
                end=25,
                headline="AGENTS. RAG. REAL-TIME VOICE.",
                narration="His work spans LangGraph agents, hybrid retrieval with reranking, FastAPI, Next.js, and real-time voice. His custom voice stack reaches first audio in under 500 milliseconds, while his licensing platform maintains 99.9 percent uptime.",
                visual_prompt="Real portfolio engineering projects, voice-agent telemetry, and product UI details with no fake dashboards or added copy.",
                source_refs=[0, 1],
                visual_type="source_image",
                layout="bento",
                camera="pull_out",
                animation="stagger",
                transition="whip",
                sfx="bass_drop",
            ),
            StoryScene(
                id="takeaway",
                start=25,
                end=32,
                headline="BUILD WHAT MOVES AI FORWARD",
                narration="Mohd Daniyal is a Full Stack AI Engineer focused on agentic AI, advanced RAG, and voice systems. Explore his work at daniyal.pro.",
                visual_prompt="The real Mohd Daniyal portfolio closing view and brand imagery with calm negative space for the separate headline layer.",
                source_refs=[0],
                visual_type="source_image",
                layout="hero",
                camera="static",
                animation="clip_reveal",
                transition="dissolve",
                sfx="none",
            ),
        ],
        sources=[
            SourceCitation(url="https://daniyal.pro", title="Mohd Daniyal portfolio", claim="Production AI engineering, AI BotKit, voice systems, and selected project evidence"),
            SourceCitation(url="inline://portfolio-cv", title="Mohd Daniyal professional CV", claim="1,000+ websites, 100,000+ users, sub-500ms first audio, and 99.9% platform uptime"),
        ],
        speech_style="Cinematic, precise, third-person engineering portrait with confident pacing and clean pauses",
    )


def fallback_visuals(storyboard: Storyboard, harvest: HarvestResult | None, project_dir: Path) -> list[StudioAsset]:
    output = project_dir / "visuals"
    output.mkdir(parents=True, exist_ok=True)
    if harvest:
        source_paths = [*harvest.image_paths, *harvest.screenshots]
    else:
        source_paths = [Path(__file__).resolve().parents[2] / "assets" / "link2reel" / "sample-site" / "orbit-hero.jpg"]
    assets: list[StudioAsset] = []
    for index, kind in enumerate(("art", "art", "thumbnail"), start=1):
        if source_paths:
            source_path = source_paths[(index - 1) % len(source_paths)]
            image = Image.open(source_path).convert("RGB")
            canvas = cover(image, (1080, 1920), focus_y=0.25 + index * 0.12).convert("RGBA")
        else:
            canvas = Image.new("RGBA", (1080, 1920), (5, 6, 10, 255))
            draw = ImageDraw.Draw(canvas)
            accent = (94, 106, 210, 180)
            for line in range(7):
                y = 260 + line * 190 + index * 36
                draw.line((72, y, 1008 - line * 72, y - 120), fill=accent, width=3)
            draw.rectangle((72 + index * 36, 300, 620 + index * 36, 980), outline=(255, 255, 255, 45), width=2)
        shade = Image.new("RGBA", canvas.size, (4, 6, 14, 30))
        canvas = Image.alpha_composite(canvas, shade)
        path = output / f"{kind}-{index:02d}.png"
        canvas.convert("RGB").save(path, "PNG", optimize=True)
        assets.append(StudioAsset(id=f"{kind}-{index}", kind=kind, label=f"{kind.title()} {index}", url=media_url(project_dir, path), mime_type="image/png", local_path=path))
    return assets


def _fallback_headline(text: str, fallback: str) -> str:
    cleaned = (text.strip() or fallback).upper()
    if len(cleaned) <= 42:
        return cleaned
    return cleaned[:42].rsplit(" ", 1)[0]


def _fallback_sentence(text: str) -> str:
    cleaned = text.strip()
    return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."


def fallback_storyboard(
    harvest: HarvestResult,
    sources: list[SourceCitation],
    style: str,
    voice: str,
    research: ResearchReport | None = None,
) -> Storyboard:
    title = (research.topic if research and research.topic.strip() else harvest.title) or "Source Story"
    citations = (research.sources if research and research.sources else sources) or [
        SourceCitation(url=harvest.source_url, title=title, claim="Primary source supplied by the user")
    ]
    if research and any(claim.text.strip() for claim in research.claims):
        entries = [
            (claim.text, claim.source_refs or [0])
            for claim in research.claims
            if claim.text.strip()
        ][:8]
        existing = {text for text, _ in entries}
        sentences = [part.strip() for part in harvest.dom_copy.replace("\n", " ").split(".") if part.strip()]
        for sentence in sentences:
            if len(entries) >= 4:
                break
            if sentence not in existing:
                entries.append((sentence, [0]))
                existing.add(sentence)
        while len(entries) < 4:
            entries.append(entries[-1])
        ids = ("hook", "context", "evidence", "system", "impact", "insight", "application", "takeaway")
        count = len(entries)
        scenes = [
            StoryScene(
                id=ids[index],
                start=index * 32 / count,
                end=(index + 1) * 32 / count,
                headline=_fallback_headline(text, title),
                narration=_fallback_sentence(text),
                visual_prompt=f"Evidence-led editorial imagery for {title}: {text}",
                source_refs=refs,
            )
            for index, (text, refs) in enumerate(entries)
        ]
    else:
        sentences = [part.strip() for part in harvest.dom_copy.replace("\n", " ").split(".") if part.strip()]
        first = sentences[0] if sentences else title
        second = sentences[1] if len(sentences) > 1 else first
        third = sentences[2] if len(sentences) > 2 else second
        fourth = sentences[3] if len(sentences) > 3 else third
        scenes = [
            StoryScene(id="hook", start=0, end=2.5, headline=_fallback_headline(first, title), narration=_fallback_sentence(first), visual_prompt=f"Real source imagery for {title}", source_refs=[0]),
            StoryScene(id="problem", start=2.5, end=12, headline=_fallback_headline(second, "THE CHALLENGE"), narration=_fallback_sentence(second), visual_prompt=f"Editorial source imagery for {title}", source_refs=[0]),
            StoryScene(id="system", start=12, end=25, headline=_fallback_headline(third, "HOW IT WORKS"), narration=_fallback_sentence(third), visual_prompt=f"Real source interface or supplied images for {title}", source_refs=[0]),
            StoryScene(id="takeaway", start=25, end=32, headline=_fallback_headline(fourth, "WHY IT MATTERS"), narration=_fallback_sentence(fourth), visual_prompt=f"Cover artwork for {title}", source_refs=[0]),
        ]
    return Storyboard(
        title=title,
        style=style,
        voice=voice,
        duration=32,
        bpm=128,
        scenes=scenes,
        sources=citations,
        speech_style="Clear, sourced, restrained product storytelling",
    )


def build_storyboard_prompt(
    harvest: HarvestResult,
    sources: list[SourceCitation],
    style: str,
    voice: str,
    research: ResearchReport | None = None,
) -> str:
    evidence_sources = research.sources if research and research.sources else sources
    research_section = ""
    if research:
        research_payload = {
            "topic": research.topic,
            "angle": research.angle,
            "summary": research.summary,
            "claims": [
                {
                    "text": claim.text,
                    "source_refs": [ref for ref in claim.source_refs if 0 <= ref < len(research.sources)],
                }
                for claim in research.claims
            ],
            "sources": [source.model_dump() for source in research.sources],
        }
        research_section = f"Research report (claim source_refs index its sources): {json.dumps(research_payload, ensure_ascii=False)}\n"
    return f"""
Create 6–8 sourced scenes for a 30–40 second vertical cinematic video.
Build a researched narrative from the supplied evidence and ResearchReport when present.
Give narration and concise on-screen text different purposes: narration is spoken;
the headline is concise on-screen text, never a static full-narration paragraph.
Use typed shot direction with visual_type, layout, camera, animation, transition, sfx,
callouts, and metrics. Diagram scenes need at least two callouts; data scenes need
sourced metrics. Headlines must contain at most 42 characters; every scene must last at least 1.8 seconds.
Use only the supplied evidence, never prior knowledge or plausible invention.
Never introduce a platform, technical problem, code filename, integration, metric, customer, or capability absent from that evidence.
Every scene must cite its supporting evidence in source_refs. If research has no
external result, tell a primary-source overview instead of inventing a problem.
Return title, style, voice, duration 32, bpm 128, scenes with id/start/end/headline/
narration/visual_prompt/source_refs/visual_type/layout/camera/animation/transition/sfx/callouts/metrics,
sources, and speech_style.
Primary source ({harvest.kind}): {harvest.title}\n{harvest.dom_copy}\nPalette: {harvest.palette}\nFonts: {harvest.fonts}
{research_section}Citations: {json.dumps([source.model_dump() for source in evidence_sources], ensure_ascii=False)}
Video style: {style}. Voice: {voice}.
"""


def build_visual_prompt(prompt: str) -> str:
    return f"""{prompt}
Do not render words, headlines, captions, letters, numbers, or fake UI copy.
Leave calm negative space for a separate motion typography layer. Use the supplied
screenshots only as brand, material, lighting, and product-interface references.
"""


class GeminiStudioProvider:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.tts_api_version = TTS_API_VERSION
        self.tts_client = genai.Client(api_key=api_key, http_options={"api_version": self.tts_api_version})

    def _core_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH),
            response_mime_type="application/json",
        )

    def _visual_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="9:16", image_size="2K"),
            tools=[types.Tool(google_search=types.GoogleSearch(search_types=types.SearchTypes(web_search=types.WebSearch(), image_search=types.ImageSearch())))],
        )

    def _tts_request(self, transcript: str, voice: str, style: str):
        contents = [types.Part(text=transcript, speech_metadata=types.SpeechMetadata(style=style))]
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        )
        return contents, config

    @staticmethod
    def _research_contents(prompt: str, harvest: HarvestResult) -> list:
        contents: list = [prompt]
        for image_path in harvest.image_paths[:4]:
            mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
            contents.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type))
        return contents

    async def _generate_research_schema(self, contents: list, schema):
        config = self._core_config()
        config.response_schema = schema
        for model in (CORE_MODEL, FALLBACK_MODEL):
            try:
                response = await asyncio.wait_for(asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=config,
                ), timeout=90)
                parsed = response.parsed if getattr(response, "parsed", None) else schema.model_validate_json(response.text)
                return parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
            except Exception:
                if model == CORE_MODEL:
                    continue
        return None

    async def plan_research(self, harvest: HarvestResult, style: str) -> ResearchPlan:
        prompt = f"""
Plan focused external research for the supplied user brief and selected style: {style}.
Use only the supplied evidence and images to identify the topic and narrative angle.
Return one to four bounded search queries that seek evidence and context without inventing facts.
Primary brief ({harvest.kind}): {harvest.title}\n{harvest.dom_copy}
"""
        contents = self._research_contents(prompt, harvest)
        parsed = await self._generate_research_schema(contents, ResearchPlan)
        return parsed if isinstance(parsed, ResearchPlan) else fallback_research_plan(harvest, style)

    async def synthesize_research(
        self,
        harvest: HarvestResult,
        plan: ResearchPlan,
        sources: list[SourceCitation],
    ) -> ResearchReport:
        fallback = fallback_research_report(harvest, plan, sources)
        evidence = [
            {"url": source.url, "title": source.title, "claim": source.claim, "content": source.content}
            for source in fallback.sources
        ]
        prompt = f"""
Synthesize one evidence-grounded research report using only the supplied evidence and images.
Do not add facts, sources, quotations, or citations from prior knowledge.
Keep every claim supported by source_refs indexing the supplied source list.
Return topic, angle, summary, claims, sources, queries, external_research, and provider.
Research plan: {plan.model_dump()}
Primary brief ({harvest.kind}): {harvest.title}\n{harvest.dom_copy}
Supplied sources: {evidence}
"""
        contents = self._research_contents(prompt, harvest)
        parsed = await self._generate_research_schema(contents, ResearchReport)
        if not isinstance(parsed, ResearchReport):
            return fallback
        try:
            return ResearchReport(
                topic=plan.topic,
                angle=plan.angle,
                summary=parsed.summary,
                claims=parsed.claims,
                sources=fallback.sources,
                queries=plan.queries,
                external_research=fallback.external_research,
                provider="gemini",
            )
        except Exception:
            return fallback

    async def write_storyboard(self, harvest: HarvestResult | None, sources: list[SourceCitation], style: str, voice: str, research: ResearchReport | None = None) -> Storyboard:
        if harvest is None:
            return mock_storyboard(style, voice)
        prompt = build_storyboard_prompt(harvest, sources, style, voice, research=research)
        config = self._core_config()
        config.response_schema = Storyboard
        contents: list = [prompt]
        for image_path in harvest.image_paths[:2]:
            mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
            contents.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type))
        for model in (CORE_MODEL, FALLBACK_MODEL):
            try:
                response = await asyncio.wait_for(asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=config,
                ), timeout=90)
                parsed = response.parsed if getattr(response, "parsed", None) else Storyboard.model_validate_json(response.text)
                return parsed if isinstance(parsed, Storyboard) else Storyboard.model_validate(parsed)
            except Exception:
                if model == CORE_MODEL:
                    continue
        return fallback_storyboard(harvest, sources, style, voice, research=research)

    async def _generate_one_visual(self, prompt: str, references: list[Path], path: Path) -> bool:
        try:
            contents: list = [prompt]
            for reference in references[:2]:
                contents.append(types.Part.from_bytes(data=reference.read_bytes(), mime_type="image/png"))
            response = await asyncio.wait_for(asyncio.to_thread(
                self.client.models.generate_content,
                model=VISUAL_MODEL,
                contents=contents,
                config=self._visual_config(),
            ), timeout=120)
            for candidate in response.candidates or []:
                for part in candidate.content.parts:
                    data = getattr(part.inline_data, "data", None) if part.inline_data else None
                    if data:
                        path.write_bytes(data)
                        return True
        except Exception:
            return False
        return False

    async def generate_visuals(self, storyboard: Storyboard, harvest: HarvestResult | None, project_dir: Path) -> list[StudioAsset]:
        output = project_dir / "visuals"
        output.mkdir(parents=True, exist_ok=True)
        references = [*harvest.image_paths, *harvest.screenshots] if harvest else []
        prompts = [build_visual_prompt(scene.visual_prompt) for scene in storyboard.scenes[1:3]] + [build_visual_prompt(f"Vertical cover artwork for {storyboard.title}")]
        generated: list[StudioAsset] = []
        for index, prompt in enumerate(prompts, start=1):
            path = output / f"visual-{index:02d}.png"
            success = await self._generate_one_visual(prompt, references, path)
            if not success:
                return await asyncio.to_thread(fallback_visuals, storyboard, harvest, project_dir)
            kind = "thumbnail" if index == 3 else "art"
            generated.append(StudioAsset(id=f"{kind}-{index}", kind=kind, label=f"{kind.title()} {index}", url=media_url(project_dir, path), mime_type="image/png", local_path=path))
        return generated

    async def _synthesize_line(self, transcript: str, voice: str, style: str) -> bytes | None:
        contents, config = self._tts_request(transcript, voice, style)
        response = await asyncio.wait_for(asyncio.to_thread(
            self.tts_client.models.generate_content,
            model=TTS_MODEL,
            contents=contents,
            config=config,
        ), timeout=90)
        for candidate in response.candidates or []:
            for part in candidate.content.parts:
                data = getattr(part.inline_data, "data", None) if part.inline_data else None
                if data:
                    return data
        return None

    async def _edge_synthesize_line(self, transcript: str, voice: str, style: str) -> bytes | None:
        import edge_tts

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "narration.mp3"
            await asyncio.wait_for(edge_tts.Communicate(transcript, VOICE, rate="-8%").save(str(path)), timeout=60)
            payload = path.read_bytes()
            return payload if len(payload) > 1000 else None

    async def synthesize(self, storyboard: Storyboard, project_dir: Path) -> StudioAudio:
        gemini_payloads = []
        for scene in storyboard.scenes:
            try:
                gemini_payloads.append(await self._synthesize_line(scene.narration, storyboard.voice, storyboard.speech_style))
            except Exception:
                gemini_payloads.append(None)
        payloads = gemini_payloads if all(payload is not None for payload in gemini_payloads) else []
        if not payloads:
            edge_payloads = []
            for scene in storyboard.scenes:
                try:
                    edge_payloads.append(await self._edge_synthesize_line(scene.narration, storyboard.voice, storyboard.speech_style))
                except Exception:
                    edge_payloads.append(None)
            payloads = edge_payloads if all(payload is not None for payload in edge_payloads) else []
        if not payloads:
            return await produce_audio(storyboard, project_dir)
        cursor = iter(payloads)

        async def cached_tts(*_):
            return next(cursor)

        return await produce_audio(storyboard, project_dir, cached_tts)


class MockStudioProvider:
    async def write_storyboard(self, harvest: HarvestResult | None, sources: list[SourceCitation], style: str, voice: str, research: ResearchReport | None = None) -> Storyboard:
        return mock_storyboard(style, voice)

    async def generate_visuals(self, storyboard: Storyboard, harvest: HarvestResult | None, project_dir: Path) -> list[StudioAsset]:
        return await asyncio.to_thread(fallback_visuals, storyboard, harvest, project_dir)

    async def synthesize(self, storyboard: Storyboard, project_dir: Path) -> StudioAudio:
        return await produce_audio(storyboard, project_dir)
