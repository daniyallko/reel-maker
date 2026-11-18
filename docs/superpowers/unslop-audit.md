# CUTLINE unslop audit — Neon redesign

Date: 2026-11-18

## Direction

- **Product:** CUTLINE turns a friend group's trip evidence into a trailer, poster, and cast press kit.
- **Character:** Neural, tactile, exact.
- **World:** Full-viewport cinema, contact sheets, editing telemetry, and theatrical press kits.
- **Moments:** The supplied cinematic videos and generated poster/trailer carry the visual richness.
- **Signature:** Space Mono timecode, scramble reveals, and the four-fold CUTLINE mark.

## Inventory and fixes

- **Spacing:** The prompt's unlayered `* { padding: 0 }` overrode every Tailwind v4 utility. Removed the padding reset; restored all intended gutters, panel padding, and flex bounds.
- **Mobile overlap:** Increased hero bottom space and added page-level bottom padding so fixed action bars do not cover content or the footer.
- **Contrast:** Raised footer copyright and architecture-layer metadata to white/45 or stronger.
- **Controls:** Moved background pause/play controls below the fixed navbar after they overlapped Cast navigation.
- **Motion:** Fixed no-op seek locking in the mouse-scrub queue; viewport pointer tracking now works over hero content. Reduced-motion behavior uses a hydration-safe media-query hook.
- **Typography:** Space Mono is used everywhere except the Anton SC watermark. No generic display sans or competing type families remain.
- **Visuals:** The new prompt explicitly authorizes the neon watermark and glass surfaces. No additional gradients, blobs, emoji icons, or decorative AI imagery were introduced.
- **Copy:** Product language stays specific to camera rolls, agents, dailies, and theatrical output.

## Verification

The browser suite was run after the spacing fixes and passed mouse scrubbing, navigation, 375px overflow checks, reduced motion, sample SSE, playback, cast controls, modals, timeline seeking, downloads, and sharing. Final screenshots are stored in `frontend/test-results/`.
