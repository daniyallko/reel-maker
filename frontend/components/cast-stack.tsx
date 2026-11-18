"use client";

import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import { AnimatePresence, motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useState } from "react";
import type { CastCredit } from "@/lib/types";
import { Button } from "./ui";

export function CastStack({ cards }: { cards: CastCredit[] }) {
  const [[index, direction], setPosition] = useState<[number, number]>([0, 1]);
  const reduceMotion = Boolean(useReducedMotion());
  const current = cards[index];

  function move(step: number) {
    setPosition(([position]) => [(position + step + cards.length) % cards.length, step]);
  }

  if (!current) return null;
  return (
    <section aria-roledescription="carousel" aria-label="Meet the Cast character cards">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="mono text-[11px] text-marquee">CHARACTER FREEZE FRAMES</p>
          <h2 className="display mt-1 text-2xl uppercase">Meet the cast</h2>
        </div>
        <span className="mono text-xs text-muted">{String(index + 1).padStart(2, "0")} / {String(cards.length).padStart(2, "0")}</span>
      </div>
      <div className="relative mx-auto aspect-[4/5] w-full max-w-[420px]">
        <div className="absolute inset-x-3 top-3 h-full border border-hairline bg-surface-raised" aria-hidden="true" />
        <div className="absolute inset-x-1.5 top-1.5 h-full border border-[#33333c] bg-surface" aria-hidden="true" />
        <AnimatePresence initial={false} custom={direction} mode="popLayout">
          <motion.figure
            key={`${current.name}-${index}`}
            className="absolute inset-0 overflow-hidden border border-hairline bg-surface"
            custom={direction}
            initial={reduceMotion ? false : { x: direction * 80, opacity: 0, rotate: direction * 2 }}
            animate={{ x: 0, opacity: 1, rotate: 0 }}
            exit={reduceMotion ? undefined : { x: direction * -70, opacity: 0, rotate: direction * -2 }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
            drag={reduceMotion ? false : "x"}
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.15}
            onDragEnd={(_, info) => {
              if (info.offset.x < -55) move(1);
              if (info.offset.x > 55) move(-1);
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={current.card_url ?? ""} alt={`${current.name} as ${current.role}`} className="size-full object-cover" loading="lazy" draggable={false} />
            <figcaption className="sr-only" aria-live="polite">{current.name} as {current.role}, card {index + 1} of {cards.length}</figcaption>
          </motion.figure>
        </AnimatePresence>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <Button variant="secondary" onClick={() => move(-1)} aria-label="Previous cast member"><ArrowLeft size={17} aria-hidden="true" /> Previous</Button>
        <p className="metadata hidden sm:block">SWIPE OR USE ARROWS</p>
        <Button variant="secondary" onClick={() => move(1)} aria-label="Next cast member">Next <ArrowRight size={17} aria-hidden="true" /></Button>
      </div>
    </section>
  );
}
