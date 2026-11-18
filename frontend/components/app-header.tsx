"use client";

import { AnimatePresence, motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CutlineLogo, SquashHamburger } from "./neon-controls";
import { ScrambleText } from "./scramble";

interface NavItem { label: string; target: string }
interface AppHeaderProps {
  projectId?: string;
  status?: string;
  navItems?: NavItem[];
}

export function AppHeader({ projectId, status = "EDITING BAY 01", navItems = [{ label: "Media", target: "media" }, { label: "Cast", target: "cast" }] }: AppHeaderProps) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState("");
  const [entranceComplete, setEntranceComplete] = useState(false);
  const reducedMotion = Boolean(useReducedMotion());

  useEffect(() => {
    const timeout = setTimeout(() => setEntranceComplete(true), reducedMotion ? 0 : 800);
    return () => clearTimeout(timeout);
  }, [reducedMotion]);

  function scrollTo(target: string) {
    document.getElementById(target)?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
    setOpen(false);
  }

  return (
    <>
      <a href="#main-content" className="fixed left-4 top-2 z-[100] -translate-y-16 bg-white px-4 py-2 text-sm text-black transition-transform focus:translate-y-0">Skip to main content</a>
      <motion.header
        className="pointer-events-none fixed inset-x-0 top-0 z-50 flex h-20 items-center justify-between px-4 sm:px-6 md:px-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: entranceComplete ? 1 : 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.8 }}
      >
        <div className="pointer-events-auto flex min-w-0 items-center gap-2">
          <motion.div
            className="glass-pill h-9 shrink-0 overflow-hidden rounded-[10px] sm:h-12 sm:rounded-[14px]"
            animate={{ width: open ? 0 : "auto", opacity: open ? 0 : 1 }}
            transition={{ type: "spring", stiffness: 350, damping: 28 }}
          >
            <motion.div whileHover={reducedMotion ? undefined : { scale: 1.02 }} whileTap={reducedMotion ? undefined : { scale: 0.98 }}>
              <Link href="/" className="flex h-9 items-center gap-2 px-3 sm:h-12 sm:px-5" aria-label="CUTLINE home">
                <CutlineLogo className="size-4 text-white sm:size-[18px]" />
                <span className="whitespace-nowrap text-[13px] tracking-tight text-white sm:text-base">CUTLINE</span>
              </Link>
            </motion.div>
          </motion.div>

          <motion.div
            className="glass-pill flex h-9 max-w-[calc(100vw-152px)] items-center overflow-hidden rounded-[10px] sm:h-12 sm:rounded-[14px]"
            animate={{ width: open ? 290 : 48 }}
            transition={{ type: "spring", stiffness: 350, damping: 28 }}
          >
            <motion.button
              type="button"
              layout
              onClick={() => setOpen((current) => !current)}
              className="ml-0 flex size-12 shrink-0 items-center justify-center rounded-[14px] hover:bg-white/15"
              animate={{ width: open ? 36 : 48, height: open ? 36 : 48, marginLeft: open ? 6 : 0 }}
              aria-expanded={open}
              aria-label={open ? "Close navigation" : "Open navigation"}
            >
              <SquashHamburger open={open} />
            </motion.button>
            <AnimatePresence>
              {open && (
                <motion.nav
                  className="flex items-center gap-5 pr-5"
                  initial={{ opacity: 0, x: 15 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  aria-label="Page sections"
                >
                  {navItems.map((item) => (
                    <button
                      key={item.target}
                      type="button"
                      className="min-h-11 whitespace-nowrap text-sm text-white/85 hover:text-white"
                      onMouseEnter={() => setHovered(item.label)}
                      onMouseLeave={() => setHovered("")}
                      onFocus={() => setHovered(item.label)}
                      onBlur={() => setHovered("")}
                      onClick={() => scrollTo(item.target)}
                    >
                      <ScrambleText text={item.label} isHovered={hovered === item.label} />
                    </button>
                  ))}
                </motion.nav>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        <div className="pointer-events-auto flex items-center gap-3">
          <span className="mono hidden text-[11px] text-white/45 lg:block">{projectId ? `REEL ${projectId.toUpperCase()}` : status}</span>
          <motion.div whileHover={reducedMotion ? undefined : { scale: 1.03 }} whileTap={reducedMotion ? undefined : { scale: 0.97 }}>
            <Link
              href="/#media"
              className="flex h-9 items-center rounded-full bg-white px-4 text-[13px] text-black sm:h-12 sm:px-6 sm:text-sm"
              onMouseEnter={() => setHovered("create")}
              onMouseLeave={() => setHovered("")}
              onFocus={() => setHovered("create")}
              onBlur={() => setHovered("")}
            >
              <ScrambleText text="Create" isHovered={hovered === "create"} />
            </Link>
          </motion.div>
        </div>
      </motion.header>
    </>
  );
}
