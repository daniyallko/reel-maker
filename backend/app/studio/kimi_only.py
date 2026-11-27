"""Single-provider studio. Moonshot handles writing, animation and visual review."""
import asyncio
import base64
import io
import json
import re
import wave

import httpx
from PIL import Image
from playwright.async_api import Error as BrowserError

from app.studio.audio import produce_audio
from app.studio.fallback_providers import KIMI_ENDPOINT, KIMI_MODEL
from app.studio.motion import sanitize_motion_html, validate_motion_clock
from app.studio.renderer import MotionRenderer, verify_studio_video
from app.studio.schemas import SourceCitation, Storyboard, StoryScene, StudioAsset
from app.studio.timeline import align_audio_timeline
from app.studio.vision import capture_keyframes, director_review_times


async def ask(client, key, prompt, picture=None):
    content = [{"type": "text", "text": prompt}]
    if picture:
        with Image.open(picture) as im:
            im.thumbnail((1080, 1280))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=80)
        data = base64.b64encode(buf.getvalue()).decode()
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + data}})
    request = {"model": KIMI_MODEL, "messages": [{"role": "user", "content": content}],
               "stream": True, "reasoning_effort": "low", "max_tokens": 12000}
    chunks = []
    finish = None
    try:
        async with asyncio.timeout(600), client.stream("POST", KIMI_ENDPOINT, json=request,
                headers={"Authorization": f"Bearer {key}"}) as response:
            if response.is_error:
                await response.aread()
                try:
                    detail = response.json().get("error", {}).get("type")
                except Exception:
                    detail = response.text[:200]
                raise RuntimeError(f"Kimi HTTP {response.status_code}: {detail}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                for choice in json.loads(payload).get("choices", []):
                    chunks.append(choice.get("delta", {}).get("content") or "")
                    finish = choice.get("finish_reason") or finish
    except TimeoutError as exc:
        raise TimeoutError("Kimi response timed out after 600s") from exc
    if finish != "stop" or not any(chunks):
        raise ValueError(f"Incomplete Kimi response (finish_reason={finish})")
    return re.sub(r"^\s*```(?:html|json)?\s*|\s*```\s*$", "", "".join(chunks)).strip()


async def make_film(settings, directory, brief, emit, style="deep_dive", citations=None, quality_mode="draft"):
    if not settings.moonshot_api_key:
        raise ValueError("Kimi-only mode requires MOONSHOT_API_KEY")
    from piper import PiperVoice, SynthesisConfig
    voice_file = settings.data_dir / "localvoices/en_US-lessac-high.onnx"
    voice = await asyncio.to_thread(PiperVoice.load, voice_file)
    directory.mkdir(parents=True, exist_ok=True)
    citations = citations or [SourceCitation(url="inline://brief", title="Production brief", claim=brief[:240])]
    async with httpx.AsyncClient(timeout=httpx.Timeout(100, connect=15)) as client:
        async def generate(prompt, picture=None):
            return await ask(client, settings.moonshot_api_key, prompt, picture)

        await emit("scriptwriter", "Kimi is writing four connected shots.", 20)
        prompt = ("Direct a 32-second editorial motion film. Output only JSON with title and shots, exactly 4. "
                  "Each shot has headline (under 32 characters), narration (one complete sentence of 8–13 words), "
                  "and action (concrete visible motion). Open on a surprising physical detail, track one subject "
                  "through cause and effect, finish on a visual payoff. Avoid production directions in speech. "
                  "Use the supplied facts. Brief: " + brief)
        for attempt in range(2):
            try:
                plan = json.loads(await generate(prompt))
                shots = plan["shots"]
                if len(shots) != 4:
                    raise ValueError("Exactly four shots required")
                scenes = [StoryScene(id=f"shot-{i+1}", start=i*8, end=(i+1)*8, headline=s["headline"],
                           narration=s["narration"], visual_prompt=s["action"], source_refs=[0],
                           layout="full_bleed") for i,s in enumerate(shots)]
                if any(not 3 <= len(s.narration.split()) <= 16 for s in scenes):
                    raise ValueError("Keep each spoken line within 16 words")
                break
            except (ValueError, TypeError, KeyError) as exc:
                if attempt:
                    raise
                prompt += f" Correct the output: {exc}"
        board = Storyboard(title=plan["title"], style=style, voice="Lessac", duration=32, scenes=scenes,
                           sources=citations, speech_style="Conversational documentary", directed_motion=True)
        await emit("voice_studio", "Recording locally with Piper Lessac.", 40)
        speeds = iter([0.97, 1.02, 0.98, 1.08])
        async def speak(line, *_):
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                await asyncio.to_thread(voice.synthesize_wav, line, wav, syn_config=SynthesisConfig(length_scale=next(speeds)))
            return buf.getvalue()
        audio = await produce_audio(board, directory, speak, narration_voice="Piper · Lessac (local)", strict_voice=True)
        board, audio = align_audio_timeline(board, audio, directory)
        (directory/"storyboard.json").write_text(board.model_dump_json(indent=2))
        await emit("motion_coder", "Kimi is drawing and animating the film.", 55)
        shot_directions = [{"headline": s.headline, "action": s.visual_prompt, "start": s.start, "end": s.end} for s in board.scenes]
        prompt = ("Return a self-contained HTML document drawing this film on a 1080x1920 Canvas. Implement "
                  "window.seekTo(t) in seconds, paint the entire frame on every call, initialize at 0. "
                  "Only inline JS/CSS. No external files, fonts, timers, random(), or network. Design a premium "
                  "technical magazine spread in motion: accurate mechanical geometry, bold editorial type, restrained "
                  "palette, physical continuity across shots, contrasting camera distances, a single highlighted moving "
                  "part, clear foreground/background separation, polished transitions. Keep headlines in a clear "
                  "header band (y=180..360) and keep graphics inside x=85..995 and y=380..1450 so artwork never "
                  "overlaps headlines. Reserve lower 400 px for captions. No fake HUD, generic boxes or tiny text. "
                  "Use headlines as the only on-screen text. Leave the caption area empty: the video encoder adds "
                  "synchronized captions. Draw these shots with their actual timings: " + json.dumps(shot_directions))
        times = director_review_times(board)
        for attempt in range(3):
            try:
                html = sanitize_motion_html(await generate(prompt))
                await validate_motion_clock(html, directory)
                sheet = await capture_keyframes(html, directory, times)
                review = json.loads(await generate(
                    f"Inspect this contact sheet against the supplied story. It is a 3-column grid of {len(times)} "
                    f"sampled frames at timestamps {times} (trailing dark cells without a timestamp are grid padding, "
                    "not blank frames; multiple timestamps within the same shot's [start, end] range naturally share "
                    "that shot's headline). Return JSON with usable (boolean) and issues (short string). Fail "
                    "unreadable/cropped/overlapped headlines, blank sampled frames, unrelated subject or static shots "
                    "that never change across the whole film. " + board.model_dump_json(), sheet))
                (directory/"visual-review.json").write_text(json.dumps(review, indent=2))
                if review["usable"] is not True:
                    raise ValueError(review["issues"])
                break
            except (ValueError, KeyError, RuntimeError, BrowserError) as exc:
                if attempt == 2:
                    raise
                prompt += f" Correct the following defect: {str(exc)[:1200]}"
        (directory/"motion.txt").write_text(html)
    cover = sorted((directory/"audit").glob("frame-*.png"))[1]
    asset = StudioAsset(id="cover", kind="thumbnail", label="Cover", mime_type="image/png",
                        url=f"/media/{directory.name}/audit/{cover.name}", local_path=cover)
    await emit("renderer", "Rendering the reviewed Kimi animation.", 85)
    output = await MotionRenderer().render(html, board, [asset], audio, directory, quality_mode=quality_mode,
                                          review_label="Kimi-reviewed storyboard frames")
    qa = await asyncio.to_thread(verify_studio_video, directory/"output/trailer.mp4")
    if not qa.valid:
        raise RuntimeError(qa.errors)
    verdict = await review_export(settings, directory)
    if not verdict["usable"] and quality_mode == "strict":
        raise ValueError("Kimi final review: " + str(verdict["issues"]))
    output = output.model_copy(update={"review_label": "Kimi-reviewed export frames" if verdict["usable"] else "Draft with visual issues"})
    path = directory/"output/studio-output.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(output.model_dump_json(indent=2))
    tmp.replace(path)
    return output


async def review_export(settings, directory):
    async with httpx.AsyncClient(timeout=httpx.Timeout(100, connect=15)) as client:
        response = await ask(client, settings.moonshot_api_key,
            "Inspect these encoded frames at phone size (3-column grid of sampled timestamps; any trailing dark "
            "cells without a timestamp label are grid padding, not blank frames). Check composition, contrast, "
            "caption legibility, subject continuity and clarity. Return JSON with usable (boolean), "
            "strengths (string), issues (string).",
            directory / "audit/contact-sheet.png")
    review = json.loads(response)
    if not isinstance(review.get("usable"), bool) or not isinstance(review.get("issues"), str):
        raise ValueError("Kimi returned an invalid final review")
    (directory / "export-review.json").write_text(json.dumps(review, indent=2))
    return review
