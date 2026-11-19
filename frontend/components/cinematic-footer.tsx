import { VIDEOS, VideoBackground } from "./cinematic-media";
import { CutlineLogo } from "./neon-controls";

export function CinematicFooter() {
  return (
    <footer className="relative flex min-h-[400px] flex-col overflow-hidden border-t border-white/10 bg-black md:flex-row">
      <div className="relative h-[300px] md:h-auto md:w-1/2">
        <VideoBackground src={VIDEOS.footer} />
        <div className="pointer-events-none absolute inset-0 bg-black/25" aria-hidden="true" />
      </div>
      <div className="flex flex-1 flex-col justify-between p-10 sm:p-16">
        <div>
          <div className="mb-8 flex items-center gap-3 text-white/70">
            <CutlineLogo className="size-[18px]" />
            <span className="text-[15px] tracking-tight">LINK2REEL</span>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-white/45">The next evolution of the URL-to-video studio. Built for stories that deserve more than a static screenshot and a generic slideshow.</p>
        </div>
        <p className="mt-12 text-xs text-white/45">© 2026 LINK2REEL Studio. All rights reserved.</p>
      </div>
    </footer>
  );
}
