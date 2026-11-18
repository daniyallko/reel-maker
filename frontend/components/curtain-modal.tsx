"use client";

import { X } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useEffect, useRef } from "react";

export function CurtainModal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  const reduceMotion = Boolean(useReducedMotion());
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    close.current?.focus();
    return () => {
      document.body.style.overflow = oldOverflow;
      previous?.focus();
    };
  }, []);

  return (
    <motion.div
      className="fixed inset-0 z-50 bg-canvas/95"
      initial={reduceMotion ? false : { clipPath: "inset(100% 0 0 0)" }}
      animate={{ clipPath: "inset(0% 0 0 0)" }}
      exit={reduceMotion ? undefined : { clipPath: "inset(100% 0 0 0)" }}
      transition={{ duration: reduceMotion ? 0 : 0.42, ease: [0.76, 0, 0.18, 1] }}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
        if (event.key === "Tab" && panel.current) {
          const focusable = Array.from(panel.current.querySelectorAll<HTMLElement>("button, a[href], video[controls], [tabindex='0']"));
          const first = focusable[0];
          const last = focusable.at(-1);
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
          if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
        }
      }}
    >
      <div ref={panel} role="dialog" aria-modal="true" aria-label={title} className="h-full overflow-y-auto">
        <div className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-hairline bg-canvas/95 px-4 md:px-8">
          <h2 className="display text-xl uppercase">{title}</h2>
          <button ref={close} type="button" className="btn btn-secondary size-11 px-0" onClick={onClose} aria-label="Close inspector"><X size={19} aria-hidden="true" /></button>
        </div>
        <div className="p-4 md:p-8">{children}</div>
      </div>
    </motion.div>
  );
}
