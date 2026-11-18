"use client";

import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";

export function CinematicTitle({ title, tagline }: { title: string; tagline: string }) {
  const reduceMotion = Boolean(useReducedMotion());
  return (
    <div>
      <p className="mono mb-3 text-[11px] tracking-[0.16em] text-marquee">THE PREMIERE PRESS KIT / FINAL CUT</p>
      <h1 className="display min-w-0 max-w-full text-balance text-5xl uppercase leading-[0.94] [overflow-wrap:anywhere] sm:text-6xl lg:text-7xl" aria-label={title}>
        {title.split(" ").map((word, index) => (
          <motion.span
            key={`${word}-${index}`}
            className="mr-[0.2em] inline-block max-w-full [overflow-wrap:anywhere]"
            aria-hidden="true"
            initial={reduceMotion ? false : { opacity: 0, filter: "blur(12px)", y: 12 }}
            animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
            transition={{ duration: 0.65, delay: reduceMotion ? 0 : 0.12 + index * 0.11, ease: [0.2, 0.8, 0.2, 1] }}
          >
            {word}
          </motion.span>
        ))}
      </h1>
      <motion.p
        className="mono mt-4 max-w-2xl text-xs leading-6 tracking-[0.08em] text-muted"
        initial={reduceMotion ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: reduceMotion ? 0 : 0.65 }}
      >
        {tagline}
      </motion.p>
    </div>
  );
}
