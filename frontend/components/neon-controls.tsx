"use client";

import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";

export function CutlineLogo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="-50 -50 100 100" className={className} fill="currentColor" aria-hidden="true">
      {[0, 90, 180, 270].map((rotation) => (
        <path
          key={rotation}
          transform={`rotate(${rotation})`}
          d="M 1.5,23 L 1.5,33 C 1.5,38.5 6,43 11.5,43 L 16.5,43 C 22,43 26.5,38.5 26.5,33 Q 28,28 33,26.5 C 38.5,26.5 43,22 43,16.5 L 43,11.5 C 43,6 38.5,1.5 33,1.5 L 23,1.5 Q 12,12 1.5,23 Z"
        />
      ))}
    </svg>
  );
}

export function SquashHamburger({ open }: { open: boolean }) {
  const reducedMotion = Boolean(useReducedMotion());
  const spring = reducedMotion ? { duration: 0 } : { type: "spring" as const, stiffness: 300, damping: 20 };
  return (
    <span className="relative block h-3 w-[18px] scale-90 sm:scale-100" aria-hidden="true">
      <motion.span className="absolute left-0 top-0 block h-[1.5px] w-full bg-white" animate={open ? { rotate: 45, y: 5 } : { rotate: 0, y: 0 }} transition={spring} />
      <motion.span className="absolute left-0 top-[5px] block h-[1.5px] w-full bg-white" animate={open ? { opacity: 0, scaleX: 0 } : { opacity: 1, scaleX: 1 }} transition={spring} />
      <motion.span className="absolute left-0 top-[10px] block h-[1.5px] w-full bg-white" animate={open ? { rotate: -45, y: -5 } : { rotate: 0, y: 0 }} transition={spring} />
    </span>
  );
}
