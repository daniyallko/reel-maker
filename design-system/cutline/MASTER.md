# LINK2REEL Glyph Design System

**Direction:** A procedural glyph-animal new tab for URL-to-motion production. Near-black grid, keyboard-drawn animals, frosted liquid glass, and a focused source composer.

## Foundations

- Canvas `#06070c`; text `#E8EBF7`; soft text `rgba(232,235,247,.72)`; muted text `rgba(232,235,247,.4)`.
- Glass: 135° white tint gradient, 1px white edge, inset rim, dark shadow, and Chromium liquid displacement. Non-Chromium uses plain blur.
- Geist for UI, Geist Mono 600 for canvas glyphs and tweak values. Both fonts are embedded as base64 WOFF2 in `frontend/app/glyph-fonts.css`.
- Seven species: Moth, Rabbit, Sea turtle, Squid, Owl, Flying fish, Eagle. Their dot colors, direction, scale, detail, and trail colors come from `frontend/lib/glyph-animals.ts`.
- Composer and tweak controls use white primary actions, pill secondary actions, and soft text rather than neon decoration.

## Views

### New tab

Seven species pills sit above a centered avatar/greeting and URL composer below the hero. Composer contains the source URL, sample URL pills, sample demo, style, and voice controls. Tweaks is top-right on desktop and a bottom sheet on mobile. Clicking empty canvas space startles animals and leaves a trail burst.

### Screening Room

The same procedural canvas and avatar sit behind source assets, live agent telemetry, and narration preview. Source URL remains visible beside progress.

### Premiere

The procedural canvas sits behind the vertical player, scene timeline, generated cover, script, and cited sources. The generated poster is an output asset, not a substitute for the procedural animals.

## Responsive and motion

- Pills wrap on small screens, never sideways-scroll. Thumb follows offsetLeft and offsetTop.
- Composer moves below the hero at every breakpoint. URL, style, voice, and sample actions stay together.
- Reduced motion draws one settled still and disables tap reactions.
- Background videos are removed from these views. No external image assets are used for the animals.
- Memory caps and existing studio API/SSE behavior remain unchanged.
