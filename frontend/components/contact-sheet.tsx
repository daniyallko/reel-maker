"use client";

import { Check, Crown, X } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import type { CuratedAsset } from "@/lib/types";
import { cn } from "./ui";

export function ContactSheet({ assets }: { assets: CuratedAsset[] }) {
  const reduceMotion = Boolean(useReducedMotion());
  if (!assets.length) {
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4" aria-label="Waiting for media">
        {Array.from({ length: 8 }, (_, index) => <div key={index} className="aspect-[4/3] animate-pulse bg-surface-raised" />)}
      </div>
    );
  }
  return (
    <motion.ul layout className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4" aria-label="Agent contact sheet">
      {assets.map((asset, index) => (
        <motion.li
          layout
          key={asset.id}
          initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: reduceMotion ? 0 : Math.min(index * 0.04, 0.4) }}
          className={cn("relative aspect-[4/3] overflow-hidden border bg-[#0e0e12]", asset.hero ? "border-marquee" : asset.status === "kept" ? "border-keeper" : "border-hairline")}
        >
          {/* Backend media is dynamically generated per project. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={asset.thumbnail_url}
            alt={`${asset.filename}: ${asset.status}`}
            className={cn("size-full object-cover transition-[filter,opacity] duration-300", asset.status === "rejected" && "opacity-35 grayscale", asset.status === "pending" && "opacity-70")}
            loading="lazy"
          />
          <span className="absolute left-2 top-2 bg-canvas/85 px-1.5 py-1 font-mono text-[11px] text-paper">{String(index + 1).padStart(2, "0")}</span>
          {asset.hero && <span className="absolute right-2 top-2 flex items-center gap-1 bg-marquee px-1.5 py-1 font-mono text-[11px] font-bold text-canvas"><Crown size={11} aria-hidden="true" />HERO</span>}
          <div className="absolute inset-x-0 bottom-0 flex min-h-8 items-center justify-between gap-1 bg-canvas/90 px-2 py-1.5">
            <span className={cn("mono flex items-center gap-1 text-[11px] font-semibold", asset.status === "kept" ? "text-keeper" : asset.status === "rejected" ? "text-rejected" : "text-muted")}>
              {asset.status === "kept" ? <Check size={12} aria-hidden="true" /> : asset.status === "rejected" ? <X size={12} aria-hidden="true" /> : null}
              {asset.status === "pending" ? "IN QUEUE" : asset.status === "kept" ? "KEEPER" : "CUT"}
            </span>
            {asset.score > 0 && <span className="mono text-[11px] text-marquee">{asset.score.toFixed(1)}</span>}
          </div>
          {asset.rejection_reason && <span className="sr-only">{asset.rejection_reason}</span>}
        </motion.li>
      ))}
    </motion.ul>
  );
}
