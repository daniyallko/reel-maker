"use client";

import type { StoryScene } from "@/lib/types";
import { timecode } from "@/lib/format";

export function SceneTimeline({ scenes, currentTime, onSeek }: { scenes: StoryScene[]; currentTime: number; onSeek: (time: number) => void }) {
  const active = scenes.find((scene) => currentTime >= scene.start && currentTime < scene.end) ?? scenes.at(-1);
  return (
    <section id="scene-timeline" className="mt-3 rounded-[14px] border border-white/10 bg-black/60 p-3 backdrop-blur-md" aria-label="Scene timeline">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="mono text-[11px] text-white/45">SCENE MAP / 30 FPS</span>
        <span className="mono text-[11px] text-white">{timecode(currentTime)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {scenes.map((scene, index) => (
          <button
            key={scene.id}
            type="button"
            onClick={() => onSeek(scene.start + 0.01)}
            aria-pressed={active?.id === scene.id}
            aria-label={`Seek to ${scene.start.toFixed(1)}s, ${scene.headline}`}
            className={`min-h-20 rounded-lg border p-2 text-left transition-colors ${active?.id === scene.id ? "border-white bg-white/15" : "border-white/10 bg-black/40 hover:border-white/35"}`}
          >
            <span className="mono block text-[11px] text-white/45">0{index + 1} / {scene.start.toFixed(1)}s</span>
            <span className="mt-1 block text-[11px] leading-4 text-white">{scene.headline}</span>
          </button>
        ))}
      </div>
      <p className="mt-3 border-t border-white/10 pt-3 text-xs leading-5 text-white/55">{active?.narration}</p>
    </section>
  );
}
