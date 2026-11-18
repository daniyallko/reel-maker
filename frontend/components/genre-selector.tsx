"use client";

import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import type { Genre } from "@/lib/types";
import { cn } from "./ui";

const GENRES: Array<{ id: Genre; label: string; short: string }> = [
  { id: "action", label: "Action Thriller", short: "ACTION" },
  { id: "indie", label: "A24 Indie Coming-of-Age", short: "INDIE" },
  { id: "comedy", label: "Chaotic Hangover Comedy", short: "COMEDY" },
  { id: "scifi", label: "Epic Sci-Fi Quest", short: "SCI-FI" },
];

export function GenreSelector({ value, onChange }: { value: Genre; onChange: (genre: Genre) => void }) {
  const reduceMotion = Boolean(useReducedMotion());
  return (
    <div role="radiogroup" aria-label="Trailer genre" className="grid grid-cols-2 gap-2">
      {GENRES.map((genre) => {
        const selected = value === genre.id;
        return (
          <button
            key={genre.id}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={genre.label}
            onClick={() => onChange(genre.id)}
            className={cn(
              "relative min-h-12 overflow-hidden border px-2 py-3 text-center transition-colors",
              selected ? "border-marquee text-canvas" : "border-hairline text-muted hover:border-[#4a4a55] hover:text-paper",
            )}
          >
            {selected && (
              <motion.span
                layoutId="genre-pill"
                className="absolute inset-0 bg-marquee"
                transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 430, damping: 34 }}
              />
            )}
            <span className="mono relative z-10 text-[11px] font-semibold tracking-[0.12em]">{genre.short}</span>
          </button>
        );
      })}
    </div>
  );
}
