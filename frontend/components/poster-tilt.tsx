"use client";

import { MagnifyingGlassPlus } from "@phosphor-icons/react";
import { motion, useMotionValue, useSpring, useTransform } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import type { PointerEvent } from "react";

export function PosterTilt({ src, title, onOpen }: { src: string; title: string; onOpen: () => void }) {
  const reduceMotion = Boolean(useReducedMotion());
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const rotateX = useSpring(useTransform(rawY, [-0.5, 0.5], [7, -7]), { stiffness: 240, damping: 25 });
  const rotateY = useSpring(useTransform(rawX, [-0.5, 0.5], [-8, 8]), { stiffness: 240, damping: 25 });
  const glareX = useTransform(rawX, [-0.5, 0.5], [20, 80]);
  const glareY = useTransform(rawY, [-0.5, 0.5], [15, 85]);
  const glare = useTransform([glareX, glareY], ([x, y]) => `radial-gradient(circle at ${x}% ${y}%, rgba(255,255,255,0.16), transparent 42%)`);

  function tilt(event: PointerEvent<HTMLButtonElement>) {
    if (reduceMotion) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    rawX.set((event.clientX - bounds.left) / bounds.width - 0.5);
    rawY.set((event.clientY - bounds.top) / bounds.height - 0.5);
  }

  return (
    <div style={{ perspective: 1200 }}>
      <motion.button
        type="button"
        className="group relative block w-full overflow-hidden border border-hairline bg-surface text-left"
        onPointerMove={tilt}
        onPointerLeave={() => { rawX.set(0); rawY.set(0); }}
        onBlur={() => { rawX.set(0); rawY.set(0); }}
        onClick={onOpen}
        onKeyDown={(event) => {
          if (reduceMotion) return;
          if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) event.preventDefault();
          if (event.key === "ArrowLeft") rawX.set(-0.35);
          if (event.key === "ArrowRight") rawX.set(0.35);
          if (event.key === "ArrowUp") rawY.set(-0.35);
          if (event.key === "ArrowDown") rawY.set(0.35);
        }}
        style={reduceMotion ? undefined : { rotateX, rotateY, transformStyle: "preserve-3d" }}
        aria-label={`Inspect full-resolution poster for ${title}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={`Theatrical poster for ${title} with billing-block credits`} className="aspect-[9/16] w-full object-cover" loading="lazy" />
        {!reduceMotion && <motion.span className="pointer-events-none absolute inset-0" style={{ background: glare }} aria-hidden="true" />}
        <span className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-canvas/90 px-3 py-3">
          <span className="mono text-[11px] text-paper">ONE-SHEET / 1080×1920</span>
          <MagnifyingGlassPlus size={18} className="text-marquee" aria-hidden="true" />
        </span>
      </motion.button>
    </div>
  );
}
