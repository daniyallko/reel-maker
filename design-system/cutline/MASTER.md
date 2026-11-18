# CUTLINE Neon Design System

**Direction:** SynapseX-style neural cinema applied to CUTLINE's trailer-production workflow. Full-viewport video, black/white monospace type, glass navigation capsules, scramble reveals, and spring motion frame the three product views without changing their function.

## Foundations

- **Canvas:** `#000000`.
- **Text:** `#FFFFFF`; secondary `rgba(255,255,255,.65)`; metadata `rgba(255,255,255,.45)` or stronger.
- **Surfaces:** black at 56–70% over video; raised surfaces white at 8–15%; hairlines white at 12%.
- **Primary action:** white fill with black text. Secondary actions use white/8 glass with white/12 borders.
- **Watermark only:** `radial-gradient(circle, rgba(142,127,148,0) 0%, #8E7F94 70%)` with transparent text fill.
- **Primary type:** Space Mono 400/700, normal and italic. All UI, headings, labels, and telemetry use it.
- **Watermark type only:** Anton SC, uppercase, `clamp(120px, 30vw, 521px)`, -4px tracking.
- **Shape:** 10px controls, 14px panels and glass pills, full-round primary navigation action. Touch targets remain at least 44×44px.

## Video and motion

- Director's Slate hero uses the supplied CloudFront hero video, paused on load. Horizontal viewport pointer movement scrubs time at sensitivity 0.8, with `seeked`-chained requests and no-op seek suppression.
- Screening Room, Premiere, cast, and footer use their assigned videos autoplayed muted and looped. Every video has an accessible pause/play control, pauses offscreen, and remains paused under reduced motion.
- ScrambleIn reveals at 0.5 characters per 25ms after section-specific delays. ScrambleText reveals at four frames per character on hover and resets immediately on exit.
- The hamburger and expanding menu use spring stiffness 300–350 and damping 20–28.
- Screening Room header uses scroll progress through a spring, `rotateX(24deg)`, vertical travel, and `translateZ(15px)`.
- All preference logic uses a hydration-safe media-query hook; reduced motion presents final content without parallax, scramble, autoplay, or spring travel.

## Three product views

### Director's Slate

Full-viewport mouse-scrub hero with dot grid and CUTLINE watermark. Asymmetric `Weekend / In motion` and `One / Trailer` titles sit above the media workflow. Below: media dump, voice/story, cast, genre, adaptive pipeline features, three-layer architecture, and video footer.

### Screening Room

Cinematic video backdrop, top black fade, 3D header, three production metrics, contact sheet, and agent telemetry. Keeper/rejected state remains textual and icon-based, not color-only.

### Premiere Press Kit

Video-backed title and metrics, vertical trailer player, audio-reactive EDL filmstrip, tilting poster, cast stack, sharing, downloads, and video footer. Mobile keeps a fixed bottom action bar with bottom content padding.

## Responsive and accessibility rules

- Mobile gutter 16px; desktop 24–32px; maximum workspace 1440px.
- Fixed headers and bottom bars never cover focused content; scroll targets use 96px offsets and mobile bottom padding.
- Body text stays at least 16px on mobile inputs; metadata stays at least 11px.
- Video controls, cast controls, modals, uploads, and navigation work without gestures or hover.
- No unlayered global padding reset: Tailwind v4 spacing utilities must remain effective.
- No horizontal page overflow at 375px. Reduced-motion and server-rendered markup agree until hydration completes.
