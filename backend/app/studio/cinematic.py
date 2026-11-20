import html
import json
import math
import re

from app.studio.schemas import Storyboard, StoryScene, StudioAsset


def inline_script_json(value) -> str:
    return (
        json.dumps(value)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def _asset_for_scene(assets: list[StudioAsset], scene: StoryScene, index: int) -> StudioAsset:
    scene_id = f"scene-{scene.id}"
    asset = next((candidate for candidate in assets if candidate.id == scene_id), None)
    if asset is None and index < len(assets) and assets[index].kind != "thumbnail":
        asset = assets[index]
    if asset is None:
        raise ValueError(f"Missing primary visual asset for scene {scene.id}")
    return asset


def _headline(scene: StoryScene) -> str:
    words = " ".join(
        f'<span class="word">{html.escape(word)}</span>'
        for word in scene.headline.split(" ")
    )
    return f'<h1 class="headline" data-critical>{words}</h1>'


def _media(scene: StoryScene, asset: StudioAsset, index: int) -> str:
    labels = {
        "screenshot": "SOURCE / INTERFACE",
        "source_image": "SOURCE / IMAGE",
        "generated_art": "EVIDENCE / INTERPRETATION",
    }
    media_chrome = ""
    if scene.visual_type == "screenshot":
        media_chrome = '<div class="browser-chrome"><i></i><i></i><i></i><span>CAPTURED SOURCE</span></div>'
    return f"""
<div class="media-shell browser media-{scene.visual_type}" data-critical>
  {media_chrome}
  <img class="scene-asset" src="{html.escape(asset.local_path.as_uri(), quote=True)}" alt="" draggable="false">
  <div class="media-shade"></div><div class="frame-corner corner-a"></div><div class="frame-corner corner-b"></div>
</div>
<div class="media-index"><span>{index + 1:02d}</span>{labels[scene.visual_type]}</div>
"""


def _kinetic(scene: StoryScene) -> str:
    words = scene.callouts or scene.headline.split()
    content = "".join(
        f'<span class="kinetic-word" style="--word-index:{index}">{html.escape(word)}</span>'
        for index, word in enumerate(words[:6])
    )
    return f"""
<div class="kinetic-template" data-critical>
  <div class="kinetic-axis"></div><div class="kinetic-sequence">SEQUENCE / {len(words):02d}</div>
  <div class="kinetic-words">{content}</div>
  <div class="kinetic-rule"><span></span></div>
</div>
"""


def _diagram(scene: StoryScene, scene_index: int) -> str:
    count = len(scene.callouts)
    width = 600 if scene.layout == "split" else 936
    center_x = width / 2
    radius_x = width * 0.32
    positions = []
    for index in range(count):
        angle = -math.pi / 2 + index * math.tau / count
        positions.append((center_x + radius_x * math.cos(angle), 270 + 190 * math.sin(angle)))
    coordinates = " ".join(f"{'M' if index == 0 else 'L'} {x:.2f} {y:.2f}" for index, (x, y) in enumerate(positions))
    if count > 2:
        coordinates += " Z"
    nodes = "".join(
        f'<div class="diagram-node" data-critical style="left:{x:.2f}px;top:{y:.2f}px"><span>{index + 1:02d}</span><strong>{html.escape(label)}</strong></div>'
        for index, (label, (x, y)) in enumerate(zip(scene.callouts, positions, strict=True))
    )
    return f"""
<div class="diagram-template" data-critical>
  <svg class="diagram-svg" viewBox="0 0 {width} 540" width="{width}" height="540" aria-hidden="true">
    <defs><marker id="arrow-{scene_index}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" class="diagram-arrow"></path></marker></defs>
    <path class="diagram-orbit" d="M {center_x - radius_x:.2f} 270 A {radius_x:.2f} 190 0 1 1 {center_x + radius_x:.2f} 270 A {radius_x:.2f} 190 0 1 1 {center_x - radius_x:.2f} 270"></path>
    <path class="diagram-path" pathLength="1" marker-end="url(#arrow-{scene_index})" d="{coordinates}"></path>
  </svg>
  {nodes}
</div>
"""


def _metric_parts(metric) -> dict:
    match = re.match(r"^([^0-9+\-]*)([+\-]?[\d,]+(?:\.\d+)?)(.*)$", metric.display, re.DOTALL)
    prefix = match.group(1) if match else ""
    suffix = match.group(3) if match else ""
    decimals = len(match.group(2).partition(".")[2]) if match and "." in match.group(2) else 0
    target = float(match.group(2).replace(",", "")) if match else metric.value
    return {
        "label": metric.label,
        "value": metric.value,
        "target": target,
        "display": metric.display,
        "prefix": prefix,
        "suffix": suffix,
        "decimals": decimals,
    }


def _data(scene: StoryScene) -> str:
    cards = "".join(
        f"""
<div class="metric-card" data-critical>
  <div class="metric-label">{html.escape(metric.label)}</div>
  <div class="metric-value">{html.escape(metric.display)}</div>
  <div class="metric-track"><div class="metric-fill"></div></div>
</div>
"""
        for metric in scene.metrics
    )
    return f"""
<div class="data-template" data-critical>
  <div class="data-kicker">MEASURED / SOURCED</div>
  <div class="metric-grid">{cards}</div>
  <div class="data-footnote"><span></span> VALUES FROM THE SCENE EVIDENCE</div>
</div>
"""


def _callouts(scene: StoryScene) -> str:
    if not scene.callouts or scene.visual_type in {"diagram", "kinetic_type"}:
        return ""
    callouts = "".join(f'<span class="callout" data-critical>{html.escape(callout)}</span>' for callout in scene.callouts)
    return f'<div class="callout-rail" data-critical>{callouts}</div>'


def _scene_html(scene: StoryScene, asset: StudioAsset, index: int, bpm: int) -> tuple[str, dict]:
    template = "media"
    if scene.visual_type == "kinetic_type":
        template = "kinetic"
    elif scene.visual_type == "diagram":
        template = "diagram"
    elif scene.visual_type == "data":
        template = "data"

    media = f"""
<div class="media-shell browser procedural-media" data-critical>
  <img class="scene-asset" src="{html.escape(asset.local_path.as_uri(), quote=True)}" alt="" draggable="false">
  <div class="media-shade"></div>
</div>
"""
    if template == "media":
        media = _media(scene, asset, index)
    body = media
    if template == "kinetic":
        body += _kinetic(scene)
    elif template == "diagram":
        body += _diagram(scene, index)
    elif template == "data":
        body += _data(scene)

    root = f"""
<section class="scene layout-{scene.layout} transition-{scene.transition} template-{template}" data-scene-id="{html.escape(scene.id, quote=True)}" data-visual-type="{scene.visual_type}" data-template="{template}" data-active="false" data-phase="0">
  <div class="chrome" data-critical>LINK2REEL / {scene.visual_type.replace('_', ' ').upper()}</div>
  <div class="scene-number" data-critical>{index + 1:02d}</div>
  <div class="composition">
    {body}
    {_headline(scene)}
    {_callouts(scene)}
  </div>
  <div class="beat" data-critical><span></span> {bpm} BPM / 30 FPS</div>
</section>
"""
    data = {
        "start": scene.start,
        "end": scene.end,
        "layout": scene.layout,
        "camera": scene.camera,
        "animation": scene.animation,
        "transition": scene.transition,
        "visualType": scene.visual_type,
        "metrics": [_metric_parts(metric) for metric in scene.metrics],
    }
    return root, data


def cinematic_motion_html(
    storyboard: Storyboard,
    assets: list[StudioAsset],
    accent: str = "#d4a853",
) -> str:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        accent = "#d4a853"
    rendered = [
        _scene_html(scene, _asset_for_scene(assets, scene, index), index, storyboard.bpm)
        for index, scene in enumerate(storyboard.scenes)
    ]
    scene_markup = "".join(item[0] for item in rendered)
    scene_data = [item[1] for item in rendered]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
:root {{ --enter:400ms; --exit:200ms; --stagger:60ms; --accent:{accent}; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
html,body {{ width:1080px; height:1920px; overflow:hidden; }}
body {{ background:#05060a; color:#f5f3ed; font-family:Arial,Helvetica,sans-serif; }}
.stage {{ position:relative; width:1080px; height:1920px; overflow:hidden; perspective:1400px; background:radial-gradient(circle at 72% 24%,#1a2030 0,#090c13 42%,#05060a 78%); }}
.stage::before {{ content:""; position:absolute; left:72px; top:160px; bottom:340px; width:1px; background:#ffffff12; pointer-events:none; }}
.stage::after {{ content:""; position:absolute; inset:0; pointer-events:none; opacity:.03; background-image:radial-gradient(#fff 1px,transparent 1px); background-size:5px 5px; }}
.scene {{ position:absolute; inset:0; opacity:0; visibility:hidden; transform-style:preserve-3d; }}
.composition {{ position:absolute; inset:0; transform-origin:540px 850px; transform-style:preserve-3d; }}
.chrome {{ position:absolute; left:72px; top:174px; color:#ffffff88; font:18px monospace; letter-spacing:.18em; }}
.scene-number {{ position:absolute; right:72px; top:160px; color:#ffffff18; font-size:112px; font-weight:700; line-height:.92; letter-spacing:-.05em; }}
.headline {{ position:absolute; left:72px; top:1110px; width:936px; font-size:66px; font-weight:700; line-height:1.02; letter-spacing:-.045em; text-wrap:balance; text-shadow:0 4px 30px #000; }}
.word {{ display:inline-block; margin-right:.20em; opacity:0; transform-origin:0 100%; }}
.word:last-child {{ margin-right:0; }}
.beat {{ position:absolute; left:72px; top:1500px; color:{accent}; font:18px monospace; letter-spacing:.14em; }}
.beat span {{ display:inline-block; width:34px; height:2px; margin:0 14px 5px 0; background:{accent}; }}
.media-shell {{ position:absolute; left:72px; top:330px; width:936px; height:700px; overflow:hidden; border:1px solid #ffffff32; border-radius:18px; background:#0d111b; box-shadow:0 40px 100px #000b,0 4px 18px #0008; transform-origin:50% 50%; }}
.scene-asset {{ width:100%; height:100%; object-fit:cover; object-position:50% 40%; user-select:none; }}
.media-shade {{ position:absolute; inset:0; pointer-events:none; background:linear-gradient(180deg,#05060a08 40%,#05060a88 100%); }}
.browser-chrome {{ position:absolute; z-index:2; left:0; right:0; top:0; height:48px; display:flex; align-items:center; gap:9px; padding:0 20px; background:#090b11dd; border-bottom:1px solid #ffffff18; }}
.browser-chrome i {{ width:8px; height:8px; border-radius:50%; background:#ffffff38; }}
.browser-chrome span {{ margin-left:auto; color:#ffffff70; font:12px monospace; letter-spacing:.16em; }}
.media-source_image {{ border-radius:2px; border-left:4px solid var(--accent); }}
.media-generated_art {{ border-radius:36px 4px 36px 4px; box-shadow:-24px 40px 100px #000c,24px 0 80px color-mix(in srgb,var(--accent) 12%,transparent); }}
.media-index {{ position:absolute; right:80px; top:292px; color:#ffffff70; font:13px monospace; letter-spacing:.16em; writing-mode:vertical-rl; }}
.media-index span {{ color:{accent}; font-size:22px; margin-bottom:14px; }}
.frame-corner {{ position:absolute; width:52px; height:52px; border-color:{accent}; opacity:.8; }}
.corner-a {{ left:22px; bottom:22px; border-left:2px solid; border-bottom:2px solid; }}
.corner-b {{ right:22px; top:70px; border-right:2px solid; border-top:2px solid; }}
.layout-full_bleed .media-shell {{ top:280px; height:780px; border-radius:8px; }}
.layout-full_bleed .headline {{ top:1130px; }}
.layout-split .media-shell {{ left:72px; top:330px; width:600px; height:720px; }}
.layout-split .headline {{ left:724px; top:410px; width:284px; font-size:54px; line-height:1.04; }}
.layout-split .media-index {{ display:none; }}
.layout-split.template-kinetic .kinetic-template {{ width:600px; }}
.layout-split.template-kinetic .kinetic-word {{ max-width:500px; font-size:68px; }}
.layout-split.template-kinetic .kinetic-word:nth-child(even) {{ margin-left:60px; }}
.layout-split.template-diagram .diagram-template {{ width:600px; }}
.layout-split.template-diagram .diagram-node {{ width:160px; }}
.layout-split.template-data .headline {{ left:72px; top:1040px; width:936px; font-size:66px; }}
.layout-bento .media-shell {{ left:360px; top:300px; width:648px; height:600px; border-radius:4px 28px 4px 28px; }}
.layout-bento .headline {{ top:1030px; }}
.procedural-media {{ opacity:.26; filter:saturate(.7); border-color:#ffffff12; box-shadow:none; }}
.template-kinetic .procedural-media,.template-diagram .procedural-media,.template-data .procedural-media {{ left:120px; top:320px; width:840px; height:650px; }}
.kinetic-template {{ position:absolute; left:72px; top:330px; width:936px; height:570px; border-top:1px solid #ffffff26; border-bottom:1px solid #ffffff26; overflow:hidden; }}
.kinetic-axis {{ position:absolute; left:24px; top:0; bottom:0; width:1px; background:{accent}; }}
.kinetic-sequence {{ position:absolute; left:52px; top:24px; color:{accent}; font:15px monospace; letter-spacing:.18em; }}
.kinetic-words {{ position:absolute; left:52px; right:0; top:86px; }}
.kinetic-word {{ display:block; width:max-content; max-width:850px; color:#f5f3ed; font-size:92px; font-weight:800; line-height:.92; letter-spacing:-.055em; text-transform:uppercase; opacity:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; transform-origin:left top; }}
.kinetic-word:nth-child(even) {{ margin-left:130px; color:transparent; -webkit-text-stroke:1px #ffffffb0; }}
.kinetic-rule {{ position:absolute; left:52px; right:0; bottom:24px; height:4px; background:#ffffff12; }}
.kinetic-rule span {{ display:block; height:100%; width:40%; background:{accent}; }}
.diagram-template {{ position:absolute; left:72px; top:330px; width:936px; height:540px; overflow:hidden; }}
.diagram-svg {{ position:absolute; inset:0; overflow:hidden; }}
.diagram-orbit {{ fill:none; stroke:#ffffff12; stroke-width:1; stroke-dasharray:4 10; }}
.diagram-path {{ fill:none; stroke:{accent}; stroke-width:4; stroke-linecap:round; stroke-linejoin:round; stroke-dasharray:1; stroke-dashoffset:1; }}
.diagram-arrow {{ fill:{accent}; }}
.diagram-node {{ position:absolute; width:190px; height:108px; padding:16px 18px; overflow:hidden; transform:translate(-50%,-50%); background:#0b0f18f2; border:1px solid #ffffff30; box-shadow:0 16px 40px #0008; }}
.diagram-node span {{ display:block; color:{accent}; font:13px monospace; letter-spacing:.16em; margin-bottom:8px; }}
.diagram-node strong {{ display:-webkit-box; max-height:52px; font-size:23px; line-height:1.12; overflow:hidden; overflow-wrap:anywhere; -webkit-box-orient:vertical; -webkit-line-clamp:2; }}
.template-diagram .headline,.template-data .headline {{ top:1040px; }}
.data-template {{ position:absolute; left:72px; top:340px; width:936px; height:480px; padding:34px 0 0; overflow:hidden; border-top:1px solid #ffffff30; }}
.data-kicker {{ color:{accent}; font:16px monospace; letter-spacing:.18em; margin-bottom:32px; }}
.metric-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:18px; height:320px; }}
.metric-card {{ height:320px; padding:28px; overflow:hidden; transform-origin:left top; background:#0c1019ee; border:1px solid #ffffff24; box-shadow:0 24px 60px #0007; }}
.metric-label {{ height:40px; display:-webkit-box; color:#ffffffa0; font:16px monospace; line-height:1.2; letter-spacing:.12em; text-transform:uppercase; overflow:hidden; overflow-wrap:anywhere; -webkit-box-orient:vertical; -webkit-line-clamp:2; }}
.metric-value {{ height:132px; margin-top:18px; display:-webkit-box; color:#f5f3ed; font-size:64px; font-weight:700; line-height:1.02; letter-spacing:-.045em; overflow:hidden; overflow-wrap:anywhere; -webkit-box-orient:vertical; -webkit-line-clamp:2; }}
.metric-track {{ height:6px; margin-top:24px; background:#ffffff12; }}
.metric-fill {{ height:100%; width:0; background:{accent}; }}
.data-footnote {{ margin-top:28px; color:#ffffff60; font:13px monospace; letter-spacing:.12em; }}
.data-footnote span {{ display:inline-block; width:7px; height:7px; margin-right:10px; border-radius:50%; background:{accent}; }}
.callout-rail {{ position:absolute; left:72px; top:1370px; width:936px; height:108px; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; align-content:start; overflow:hidden; }}
.callout {{ height:44px; min-width:0; padding:12px 16px; overflow:hidden; border:1px solid #ffffff28; color:#ffffffb0; background:#090c14aa; font:16px monospace; letter-spacing:.08em; white-space:nowrap; text-overflow:ellipsis; }}
.layout-split .callout-rail {{ left:724px; top:1100px; width:284px; height:224px; grid-template-columns:minmax(0,1fr); }}
.layout-split.template-data .callout-rail {{ left:72px; top:1340px; width:936px; height:108px; grid-template-columns:repeat(2,minmax(0,1fr)); }}
</style></head><body><main class="stage" id="stage">{scene_markup}</main><script>
const scenes = {inline_script_json(scene_data)};
const phaseDuration = Math.min(3, Math.max(1.8, 60 / {storyboard.bpm} * 5));
const enterMs = 400, exitMs = 200, staggerMs = 60;
const frames = {{
  hero: [
    {{x:72,y:330,w:936,h:700}}, {{x:150,y:300,w:780,h:740}},
    {{x:180,y:390,w:720,h:560}}, {{x:110,y:320,w:860,h:690}}
  ],
  full_bleed: [
    {{x:72,y:280,w:936,h:780}}, {{x:120,y:320,w:840,h:720}},
    {{x:72,y:350,w:936,h:690}}, {{x:96,y:260,w:888,h:790}}
  ],
  split: [
    {{x:72,y:330,w:600,h:720}}, {{x:120,y:370,w:552,h:640}},
    {{x:72,y:300,w:600,h:760}}, {{x:96,y:350,w:576,h:680}}
  ],
  bento: [
    {{x:360,y:300,w:648,h:600}}, {{x:72,y:340,w:600,h:600}},
    {{x:300,y:280,w:708,h:640}}, {{x:408,y:330,w:600,h:580}}
  ]
}};
const roots = [...document.querySelectorAll('.scene')];
scenes.forEach((scene, index) => {{
  scene.root = roots[index];
  scene.composition = scene.root.querySelector('.composition');
  scene.media = scene.root.querySelector('.media-shell');
  scene.image = scene.root.querySelector('.scene-asset');
  scene.words = [...scene.root.querySelectorAll('.word')];
  scene.kineticWordRoot = scene.root.querySelector('.kinetic-words');
  scene.kineticWords = [...scene.root.querySelectorAll('.kinetic-word')];
  scene.diagramTemplate = scene.root.querySelector('.diagram-template');
  scene.diagramOrbit = scene.root.querySelector('.diagram-orbit');
  scene.diagramNodes = [...scene.root.querySelectorAll('.diagram-node')].map(node => ({{
    node, x:parseFloat(node.style.left), y:parseFloat(node.style.top)
  }}));
  scene.paths = [...scene.root.querySelectorAll('.diagram-path')];
  scene.metricNodes = [...scene.root.querySelectorAll('.metric-card')].map(card => ({{
    card, value: card.querySelector('.metric-value'), fill: card.querySelector('.metric-fill')
  }}));
  scene.calloutNodes = [...scene.root.querySelectorAll('.callout')];
}});
const clamp = value => Math.max(0, Math.min(1, value));
const easeOut = value => 1 - Math.pow(1 - clamp(value), 4);
const easeIn = value => Math.pow(clamp(value), 3);
function mediaCamera(scene, local, duration, phaseProgress) {{
  const progress = clamp(local / duration);
  if (scene.camera === 'pull_out') return {{scale:1.08 - .08 * progress, x:0, y:0}};
  if (scene.camera === 'pan_left') return {{scale:1.035, x:28 - 56 * progress, y:0}};
  if (scene.camera === 'pan_right') return {{scale:1.035, x:-28 + 56 * progress, y:0}};
  if (scene.camera === 'static') return {{scale:1, x:0, y:0}};
  return {{scale:.96 + .08 * progress + .012 * phaseProgress, x:0, y:0}};
}}
function updateHeadline(scene, local) {{
  scene.words.forEach((word, index) => {{
    const progress = easeOut((local * 1000 - index * staggerMs) / enterMs);
    word.style.opacity = progress;
    const reveal = scene.animation === 'clip_reveal' ? (1 - progress) * 100 : 0;
    word.style.clipPath = `inset(${{reveal}}% 0 0 0)`;
    const distance = scene.animation === 'stagger' ? 54 : 30;
    word.style.transform = `translateY(${{(1 - progress) * distance}}px)`;
  }});
}}
function updateTransition(scene, local, duration, active) {{
  scene.root.dataset.active = active ? 'true' : 'false';
  scene.root.style.visibility = active ? 'visible' : 'hidden';
  if (!active) return;
  const enter = clamp(local * 1000 / enterMs);
  const exit = clamp((duration - local) * 1000 / exitMs);
  let opacity = Math.min(easeOut(enter), 1 - easeIn(1 - exit));
  let clip = 'inset(0 0 0 0)';
  let transform = 'translate3d(0,0,0)';
  if (scene.transition === 'cut') opacity = 1;
  if (scene.transition === 'wipe') {{
    opacity = 1;
    clip = `inset(0 ${{(1 - easeOut(enter)) * 100}}% 0 0)`;
  }}
  if (scene.transition === 'whip') transform = `translate3d(${{(1 - easeOut(enter)) * 160 - (1 - exit) * 100}}px,0,0)`;
  scene.root.style.opacity = clamp(opacity);
  scene.root.style.clipPath = clip;
  scene.root.style.transform = transform;
}}
function arrangeDiagram(scene, phase) {{
  if (!scene.diagramNodes.length) return;
  const count = scene.diagramNodes.length;
  const width = scene.diagramTemplate.clientWidth;
  const arrangement = phase % 4;
  const positions = scene.diagramNodes.map((entry, index) => {{
    if (arrangement === 1) {{
      const margin = scene.layout === 'split' ? 90 : 105;
      return {{x:count === 1 ? width / 2 : margin + index * (width - margin * 2) / (count - 1), y:270}};
    }}
    if (arrangement === 2) {{
      const offset = scene.layout === 'split' ? 50 : 70;
      return {{x:width / 2 + (index % 2 ? offset : -offset), y:count === 1 ? 270 : 70 + index * 400 / (count - 1)}};
    }}
    if (arrangement === 3) {{
      const base = scene.diagramNodes[(index + 1) % count];
      return {{x:base.x, y:base.y}};
    }}
    return {{x:entry.x, y:entry.y}};
  }});
  scene.diagramNodes.forEach((entry, index) => {{
    const left = `${{positions[index].x}}px`;
    const top = `${{positions[index].y}}px`;
    const opacity = index === phase % count ? '1' : '.78';
    if (entry.node.style.left !== left) entry.node.style.left = left;
    if (entry.node.style.top !== top) entry.node.style.top = top;
    if (entry.node.style.opacity !== opacity) entry.node.style.opacity = opacity;
  }});
  const coordinates = positions.map((position, index) => `${{index === 0 ? 'M' : 'L'}} ${{position.x}} ${{position.y}}`).join(' ');
  const pathData = coordinates + (count > 2 && arrangement !== 1 && arrangement !== 2 ? ' Z' : '');
  scene.paths.forEach(path => {{ if (path.getAttribute('d') !== pathData) path.setAttribute('d', pathData); }});
  if (scene.diagramOrbit) scene.diagramOrbit.style.opacity = arrangement === 0 || arrangement === 3 ? 1 : 0;
}}
window.seekTo = function(t) {{
  const time = Number.isFinite(t) ? t : 0;
  scenes.forEach((scene, index) => {{
    const duration = scene.end - scene.start;
    const local = Math.max(0, Math.min(duration, time - scene.start));
    const active = time >= scene.start && time < scene.end;
    const phase = Math.floor(local / phaseDuration);
    const phaseProgress = (local % phaseDuration) / phaseDuration;
    scene.root.dataset.phase = String(phase);
    updateTransition(scene, local, duration, active);
    if (!active) return;

    const phaseX = [0, -14, 12, -6][phase % 4];
    const phaseY = [0, 8, -6, 4][phase % 4];
    const phaseScale = [1, 1.012, .992, 1.018][phase % 4];
    scene.composition.style.transform = `translate3d(${{phaseX}}px,${{phaseY}}px,0) scale(${{phaseScale}})`;
    const frame = frames[scene.layout][phase % 4];
    const camera = mediaCamera(scene, local, duration, phaseProgress);
    scene.media.style.left = `${{frame.x}}px`;
    scene.media.style.top = `${{frame.y}}px`;
    scene.media.style.width = `${{frame.w}}px`;
    scene.media.style.height = `${{frame.h}}px`;
    const tilt = scene.visualType === 'screenshot' ? (1 - easeOut(local * 1000 / enterMs)) * (index === 0 ? 42 : 12) : 0;
    const parallax = scene.animation === 'parallax' ? Math.sin(local * .8) * 8 : 0;
    const cameraTransform = Math.abs(tilt) < .001
      ? `translate(${{camera.x + parallax}}px,${{camera.y}}px) scale(${{camera.scale}})`
      : `perspective(1400px) translate3d(${{camera.x + parallax}}px,${{camera.y}}px,0) rotateX(${{tilt}}deg) scale(${{camera.scale}})`;
    scene.media.style.transform = cameraTransform;
    scene.image.style.objectPosition = `${{50 + (phase % 3 - 1) * 14}}% ${{36 + (phase % 4) * 9}}%`;
    updateHeadline(scene, local);

    if (scene.kineticWordRoot) scene.kineticWordRoot.style.top = `${{[86, 132, 48, 104][phase % 4]}}px`;
    scene.kineticWords.forEach((word, wordIndex) => {{
      const progress = easeOut((local - wordIndex * .08) / .46);
      const arrangement = phase % 4;
      const direction = wordIndex % 2 ? -1 : 1;
      const shift = arrangement === 1 ? direction * (scene.layout === 'split' ? 36 : 60)
        : arrangement === 3 ? -direction * (scene.layout === 'split' ? 24 : 40) : 0;
      const compact = scene.kineticWords.length > 4;
      word.style.fontSize = `${{compact ? (scene.layout === 'split' ? 52 : 64) : (scene.layout === 'split' ? 68 : 92)}}px`;
      word.style.maxWidth = scene.layout === 'split'
        ? (wordIndex % 2 ? '400px' : '460px') : (wordIndex % 2 ? '660px' : '760px');
      word.style.opacity = progress;
      word.style.transform = `translate3d(${{(1 - progress) * 110 + shift}}px,${{(1 - progress) * 36}}px,0)`;
    }});
    arrangeDiagram(scene, phase);
    scene.paths.forEach((path, pathIndex) => {{
      const progress = easeOut((local - pathIndex * .16) / 1.65);
      path.style.strokeDashoffset = String(1 - progress);
    }});
    scene.metricNodes.forEach((nodes, metricIndex) => {{
      const metric = scene.metrics[metricIndex];
      const progress = easeOut((local - metricIndex * .12) / 1.4);
      const value = metric.target * progress;
      const formatted = value.toLocaleString('en-US', {{minimumFractionDigits:metric.decimals, maximumFractionDigits:metric.decimals}});
      nodes.value.textContent = progress >= 1 ? metric.display : `${{metric.prefix}}${{formatted}}${{metric.suffix}}`;
      nodes.fill.style.width = `${{progress * 100}}%`;
      if (scene.metricNodes.length === 1) {{
        nodes.card.style.width = `${{[100, 72, 88, 64][phase % 4]}}%`;
        nodes.card.style.transform = `translate(${{[0, 24, 64, 0][phase % 4]}}px,0) scale(${{[1, .9, .96, .86][phase % 4]}})`;
      }} else {{
        const emphasized = metricIndex === phase % scene.metricNodes.length;
        nodes.card.style.width = '100%';
        nodes.card.style.transform = `translateY(${{emphasized ? -12 : 12}}px) scale(${{emphasized ? 1 : .94}})`;
      }}
    }});
    scene.calloutNodes.forEach((callout, calloutIndex) => {{
      const progress = easeOut((local - .25 - calloutIndex * .08) / .4);
      callout.style.opacity = progress;
      callout.style.transform = `translateY(${{(1 - progress) * 22}}px)`;
    }});
  }});
}};
window.seekTo(0);
</script></body></html>"""
