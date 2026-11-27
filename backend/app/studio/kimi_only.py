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
from app.studio.motion import sanitize_motion_html
from app.studio.renderer import MotionRenderer, is_light_color, verify_studio_video
from app.studio.schemas import SourceCitation, Storyboard, StoryScene, StudioAsset
from app.studio.timeline import align_audio_timeline
from app.studio.vision import capture_keyframes, director_review_times

VOICE_CADENCE = {
    "Fenrir": 1.04,
    "Charon": 1.08,
    "Puck": 0.94,
    "Aoede": 0.98,
    "Lessac": 1.00,
}

DEFAULT_PALETTE = {
    "bg": "#0e1117",
    "surface": "#161b24",
    "ink": "#f4f2ed",
    "accent": "#e09f3e",
    "muted": "#8b94a5",
}


async def ask(client, key, prompt, picture=None, max_tokens=12000):
    content = [{"type": "text", "text": prompt}]
    if picture:
        with Image.open(picture) as im:
            im.thumbnail((1080, 1280))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=80)
        data = base64.b64encode(buf.getvalue()).decode()
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + data}})
    request = {"model": KIMI_MODEL, "messages": [{"role": "user", "content": content}],
               "stream": True, "reasoning_effort": "low", "max_tokens": max_tokens}
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
    return re.sub(r"^\s*```(?:html|json|javascript|js)?\s*|\s*```\s*$", "", "".join(chunks)).strip()


def _unwrap_shot_body(code: str) -> str:
    cleaned = re.sub(r"^\s*```(?:javascript|js)?\s*|\s*```\s*$", "", code).strip()
    match = re.match(r"^(?:function\s+\w*\s*\([^)]*\)|(?:\([^)]*\)|[a-zA-Z_$][\w$]*)\s*=>)\s*\{([\s\S]*)\}\s*;?\s*$", cleaned)
    return match.group(1).strip() if match else cleaned


def _normalize_palette(raw: dict | None) -> dict[str, str]:
    palette = dict(DEFAULT_PALETTE)
    if isinstance(raw, dict):
        for key in palette:
            val = raw.get(key)
            if isinstance(val, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", val.strip()):
                palette[key] = val.strip()
    return palette


def compose_film_html(board: Storyboard, art_direction: dict, shot_bodies: list[str]) -> str:
    palette = _normalize_palette(art_direction.get("palette"))
    shots_meta = [
        {"headline": s.headline, "start": s.start, "end": s.end}
        for s in board.scenes
    ]
    shot_fns = "\n".join(
        f"function drawShot_{i}(ctx, localT, duration, W, H, P) {{\n{_unwrap_shot_body(body)}\n}}"
        for i, body in enumerate(shot_bodies)
    )
    dispatch = ", ".join(f"drawShot_{i}" for i in range(len(shot_bodies)))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; width: 1080px; height: 1920px; overflow: hidden; background: {palette["bg"]}; }}
  canvas {{ display: block; width: 1080px; height: 1920px; }}
</style>
</head>
<body>
<canvas id="stage" width="1080" height="1920"></canvas>
<script>
const W = 1080, H = 1920;
const P = {json.dumps(palette)};
const SHOTS = {json.dumps(shots_meta)};
const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');

function clamp(v, lo, hi) {{ return Math.max(lo, Math.min(hi, v)); }}
function lerp(a, b, t) {{ return a + (b - a) * t; }}
function easeOutCubic(t) {{ t = clamp(t, 0, 1); return 1 - Math.pow(1 - t, 3); }}
function easeInOutCubic(t) {{ t = clamp(t, 0, 1); return t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2; }}
function roundRectPath(c, x, y, w, h, r) {{
  c.beginPath();
  if (c.roundRect) {{ c.roundRect(x, y, w, h, r); }}
  else {{ c.rect(x, y, w, h); }}
}}

{shot_fns}
const DRAWERS = [{dispatch}];

function drawHeader(ctx, headline, localT, index) {{
  const enter = easeOutCubic(localT / 0.35);
  ctx.save();
  ctx.globalAlpha = enter;
  const yShift = (1 - enter) * 18;
  ctx.fillStyle = P.accent;
  ctx.fillRect(85, 168 + yShift, 54 * enter, 5);
  ctx.fillStyle = P.muted;
  ctx.font = '600 22px system-ui, -apple-system, sans-serif';
  ctx.textBaseline = 'top';
  ctx.fillText('0' + (index + 1) + ' / 0' + SHOTS.length, 152, 159 + yShift);
  ctx.fillStyle = P.ink;
  ctx.font = '700 54px system-ui, -apple-system, sans-serif';
  const words = headline.split(' ');
  const lines = [];
  let line = '';
  for (const w of words) {{
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width > 910 && line) {{ lines.push(line); line = w; }}
    else {{ line = test; }}
  }}
  if (line) lines.push(line);
  lines.slice(0, 2).forEach((ln, li) => {{
    ctx.fillText(ln, 85, 198 + yShift + li * 64);
  }});
  ctx.restore();
}}

window.seekTo = function(t) {{
  t = clamp(t, 0, {board.duration});
  let idx = SHOTS.findIndex((s, i) => t < s.end || i === SHOTS.length - 1);
  if (idx < 0) idx = 0;
  const shot = SHOTS[idx];
  const localT = Math.max(0, t - shot.start);
  const dur = Math.max(0.1, shot.end - shot.start);
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = P.bg;
  ctx.fillRect(0, 0, W, H);
  ctx.save();
  DRAWERS[idx](ctx, localT, dur, W, H, P);
  ctx.restore();
  drawHeader(ctx, shot.headline, localT, idx);
  ctx.restore();
}};

window.seekTo(0);
</script>
</body>
</html>"""


def _select_piper_voice(settings, voice_name: str):
    local_dir = settings.data_dir / "localvoices"
    candidate = local_dir / f"{voice_name.lower()}.onnx"
    if candidate.exists():
        return candidate
    return local_dir / "en_US-lessac-high.onnx"


async def make_film(settings, directory, brief, emit, style="deep_dive", citations=None, quality_mode="draft", voice_name="Lessac"):
    if not settings.moonshot_api_key:
        raise ValueError("Kimi-only mode requires MOONSHOT_API_KEY")
    from piper import PiperVoice, SynthesisConfig
    voice_file = _select_piper_voice(settings, voice_name)
    voice = await asyncio.to_thread(PiperVoice.load, voice_file)
    directory.mkdir(parents=True, exist_ok=True)
    citations = citations or [SourceCitation(url="inline://brief", title="Production brief", claim=brief[:240])]
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15)) as client:
        async def generate(prompt, picture=None, max_tokens=12000):
            return await ask(client, settings.moonshot_api_key, prompt, picture, max_tokens=max_tokens)

        await emit("scriptwriter", "Kimi is designing a bespoke visual direction and shot plan.", 20)
        prompt = (
            "Direct a 32-second bespoke editorial motion explainer film. Output ONLY valid JSON with: "
            "title (string), art_direction ({palette: {bg, surface, ink, accent, muted} as 6-digit hex colors "
            "tailored specifically to the topic mood — vary dark/light/saturated themes, do NOT default to cream; "
            "visual_style: short description of the graphic aesthetic}), and shots (4 to 5 connected shots). "
            "Each shot has: headline (under 32 chars), narration (one complete spoken sentence of 7–13 words), "
            "action (concrete visible motion and geometry), and camera (e.g. macro_detail, cutaway, wide_system, "
            "data_comparison, kinetic_flow). Open on a striking physical or conceptual hook, progress through "
            "distinct camera distances and cause-and-effect visuals, and land on a clear payoff. "
            "Avoid production directions in speech. Brief: " + brief
        )
        for attempt in range(2):
            try:
                plan = json.loads(await generate(prompt, max_tokens=8000))
                shots = plan["shots"]
                if not 4 <= len(shots) <= 6:
                    raise ValueError("4 to 6 shots required")
                slot = 32.0 / len(shots)
                scenes = [
                    StoryScene(
                        id=f"shot-{i+1}",
                        start=round(i * slot, 4),
                        end=32.0 if i == len(shots) - 1 else round((i + 1) * slot, 4),
                        headline=s["headline"],
                        narration=s["narration"],
                        visual_prompt=f"[{s.get('camera', 'medium')}] {s['action']}",
                        source_refs=[0],
                        layout="full_bleed",
                    )
                    for i, s in enumerate(shots)
                ]
                if any(not 3 <= len(s.narration.split()) <= 16 for s in scenes):
                    raise ValueError("Keep each spoken line within 16 words")
                art_direction = plan.get("art_direction") or {}
                break
            except (ValueError, TypeError, KeyError) as exc:
                if attempt:
                    raise
                prompt += f" Correct the output: {exc}"
        board = Storyboard(title=plan["title"], style=style, voice=voice_name, duration=32, scenes=scenes,
                           sources=citations, speech_style="Conversational documentary", directed_motion=True)

        await emit("voice_studio", f"Recording locally with Piper ({voice_name}).", 40)
        base_scale = VOICE_CADENCE.get(voice_name, 1.0)
        cadence_offsets = [0.98, 1.01, 0.99, 1.04, 0.97, 1.02]
        shot_counter = 0

        async def speak(line, *_):
            nonlocal shot_counter
            idx = shot_counter
            shot_counter += 1
            scale = base_scale * cadence_offsets[idx % len(cadence_offsets)]
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                await asyncio.to_thread(voice.synthesize_wav, line, wav, syn_config=SynthesisConfig(length_scale=scale))
            return buf.getvalue()

        audio = await produce_audio(board, directory, speak, narration_voice=f"Piper · {voice_name} (local)", strict_voice=True)
        board, audio = align_audio_timeline(board, audio, directory)
        (directory / "storyboard.json").write_text(board.model_dump_json(indent=2))

        await emit("motion_coder", "Kimi is drawing all scenes in parallel.", 55)
        palette = _normalize_palette(art_direction.get("palette"))
        visual_style = art_direction.get("visual_style", "Clean editorial vector motion")

        async def generate_shot(index: int, scene: StoryScene, extra_note: str = "") -> str:
            shot_prompt = (
                f"Write ONLY the JavaScript body (no function wrapper, no markdown fences, no HTML) for "
                f"shot {index + 1} of {len(board.scenes)} on a 1080x1920 Canvas 2D context.\n"
                f"Available parameters: ctx, localT (seconds from 0 to {scene.end - scene.start:.2f}), "
                f"duration ({scene.end - scene.start:.2f}), W (1080), H (1920), P ({json.dumps(palette)}).\n"
                f"Available helpers: clamp(v,lo,hi), lerp(a,b,t), easeOutCubic(t), easeInOutCubic(t), roundRectPath(c,x,y,w,h,r).\n"
                f"Style: {visual_style}. Topic: {board.title}.\n"
                f"This shot's headline '{scene.headline}' is already drawn in y=155..330, and captions go in y=1500..1920.\n"
                f"Draw rich, bespoke, continuously animated graphics strictly inside x=80..1000 and y=360..1460.\n"
                f"Action to animate: {scene.visual_prompt}\n"
                f"Rules: deterministic pure function of localT (no Math.random, timers, or external assets). "
                f"Ensure visible continuous motion from localT=0 to duration. Do NOT redraw the headline or background fill."
                + (f"\nFix this issue: {extra_note}" if extra_note else "")
            )
            return await generate(shot_prompt, max_tokens=12000)

        shot_bodies = list(await asyncio.gather(*(generate_shot(i, s) for i, s in enumerate(board.scenes))))
        times = director_review_times(board)
        extra_notes = [""] * len(board.scenes)

        for attempt in range(3):
            try:
                html = sanitize_motion_html(compose_film_html(board, art_direction, shot_bodies))
                sheet = await capture_keyframes(html, directory, times, validate_clock=True)
                review = json.loads(await generate(
                    f"Inspect this contact sheet against the supplied story. It is a 3-column grid of {len(times)} "
                    f"sampled frames at timestamps {times} (trailing dark cells without a timestamp are grid padding, "
                    "not blank frames; multiple timestamps within the same shot's [start, end] range naturally share "
                    "that shot's headline). Return JSON with usable (boolean), issues (short string), and optional "
                    "bad_shots (array of 0-based shot indices that need redrawing). Fail unreadable/cropped/overlapped "
                    "headlines, blank sampled frames, unrelated subject or static shots. " + board.model_dump_json(), sheet, max_tokens=2000))
                (directory / "visual-review.json").write_text(json.dumps(review, indent=2))
                if review["usable"] is not True:
                    bad = [i for i in (review.get("bad_shots") or []) if isinstance(i, int) and 0 <= i < len(board.scenes)]
                    raise ValueError(json.dumps({"issues": review["issues"], "bad_shots": bad}))
                break
            except (ValueError, KeyError, RuntimeError, BrowserError) as exc:
                if attempt == 2:
                    raise
                bad_indices = list(range(len(board.scenes)))
                note = str(exc)[:800]
                try:
                    parsed = json.loads(str(exc))
                    note = parsed.get("issues", note)
                    if parsed.get("bad_shots"):
                        bad_indices = parsed["bad_shots"]
                except Exception:
                    pass
                regenerated = await asyncio.gather(*(
                    generate_shot(i, board.scenes[i], note) for i in bad_indices
                ))
                for i, body in zip(bad_indices, regenerated, strict=True):
                    shot_bodies[i] = body
        (directory / "motion.txt").write_text(html)

    cover = sorted((directory / "audit").glob("frame-*.png"))[1]
    asset = StudioAsset(id="cover", kind="thumbnail", label="Cover", mime_type="image/png",
                        url=f"/media/{directory.name}/audit/{cover.name}", local_path=cover)
    await emit("renderer", "Rendering the reviewed Kimi animation.", 85)
    light_bg = is_light_color(palette["bg"])
    output = await MotionRenderer().render(html, board, [asset], audio, directory, quality_mode=quality_mode,
                                          review_label="Kimi-reviewed storyboard frames", light_bg=light_bg, piped=True)
    qa = await asyncio.to_thread(verify_studio_video, directory / "output/trailer.mp4")
    if not qa.valid:
        raise RuntimeError(qa.errors)
    verdict = await review_export(settings, directory)
    if not verdict["usable"] and quality_mode == "strict":
        raise ValueError("Kimi final review: " + str(verdict["issues"]))
    output = output.model_copy(update={"review_label": "Kimi-reviewed export frames" if verdict["usable"] else "Draft with visual issues"})
    path = directory / "output/studio-output.json"
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
