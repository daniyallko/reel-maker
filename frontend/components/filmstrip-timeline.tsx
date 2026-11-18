"use client";

import type { CuratedAsset, EDLSegment, TrailerEDL } from "@/lib/types";
import { shortTime, timecode } from "@/lib/format";
import { cn } from "./ui";

interface FilmstripTimelineProps {
  edl: TrailerEDL;
  assets: CuratedAsset[];
  currentTime: number;
  audioLevel: number;
  onSeek: (time: number) => void;
}

export function FilmstripTimeline({ edl, assets, currentTime, audioLevel, onSeek }: FilmstripTimelineProps) {
  const assetMap = new Map(assets.map((asset) => [asset.id, asset]));
  const active = edl.segments.find((segment) => currentTime >= segment.start && currentTime < segment.end) ?? edl.segments.at(-1);
  return (
    <section className="mt-3 border border-hairline bg-surface p-3" aria-label="Audio-reactive filmstrip timeline">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="mono text-[11px] text-muted">EDIT DECISION LIST / 24 FPS</span>
        <span className="mono text-[11px] text-marquee">{timecode(currentTime)}</span>
      </div>
      <div className="no-scrollbar relative overflow-x-auto pb-1">
        <div className="relative flex min-w-[540px] gap-[2px]">
          {edl.segments.map((segment) => {
            const asset = assetMap.get(segment.asset_id);
            const isActive = active?.asset_id === segment.asset_id && active?.start === segment.start;
            return (
              <button
                type="button"
                key={`${segment.asset_id}-${segment.start}`}
                onClick={() => onSeek(segment.start + 0.01)}
                className={cn("group relative h-24 min-w-0 overflow-hidden border text-left transition-colors", isActive ? "border-marquee" : "border-hairline hover:border-muted")}
                style={{ flexGrow: segment.end - segment.start, flexBasis: 0 }}
                aria-label={`Seek to ${shortTime(segment.start)}, ${asset?.filename ?? segment.asset_id}${segment.voiceover ? `, narration: ${segment.voiceover}` : ""}`}
                aria-pressed={isActive}
              >
                {asset && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={asset.thumbnail_url} alt="" className={cn("size-full object-cover", !isActive && "opacity-55 grayscale-[35%]")} loading="lazy" />
                )}
                <span className="absolute inset-x-0 bottom-0 flex justify-between bg-canvas/85 px-1.5 py-1 font-mono text-[11px] text-paper">
                  <span>{shortTime(segment.start)}</span><span>A{segment.act}</span>
                </span>
                {isActive && (
                  <span
                    className="pointer-events-none absolute inset-x-0 bottom-0 top-1/2 origin-bottom bg-marquee/20"
                    style={{ transform: `scaleY(${0.25 + audioLevel * 0.75})` }}
                    aria-hidden="true"
                  />
                )}
              </button>
            );
          })}
          {edl.beat_markers.map((marker) => (
            <span key={marker} className="pointer-events-none absolute -top-1 h-28 w-px bg-tally" style={{ left: `${(marker / edl.duration) * 100}%` }} aria-hidden="true" />
          ))}
        </div>
      </div>
      <div className="mt-3 grid gap-2 border-t border-hairline pt-3 sm:grid-cols-[auto_1fr] sm:items-start">
        <span className="mono text-[11px] text-tally">VO / {active?.voiceover ? shortTime(active.start) : "NONE"}</span>
        <p className="text-xs leading-5 text-muted">{active?.voiceover ?? active?.title_card ?? "Score and ambient sound only."}</p>
      </div>
      <div className="mt-2 flex items-center gap-2" aria-hidden="true">
        <span className="mono text-[11px] text-muted">AUDIO</span>
        <div className="h-1 flex-1 bg-hairline"><div className="h-full origin-left bg-marquee transition-transform duration-75" style={{ transform: `scaleX(${Math.min(1, audioLevel * 1.8)})` }} /></div>
      </div>
    </section>
  );
}
