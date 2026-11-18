"use client";

import { ArrowLeft, ArrowClockwise, WarningCircle } from "@phosphor-icons/react";
import { motion, useMotionTemplate, useScroll, useSpring, useTransform } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import Link from "next/link";
import { useRef } from "react";
import type { ProjectSnapshot } from "@/lib/types";
import type { ConnectionState } from "@/lib/use-project-events";
import { AgentRail } from "./agent-rail";
import { VIDEOS, VideoBackground } from "./cinematic-media";
import { ContactSheet } from "./contact-sheet";
import { Button } from "./ui";

interface ScreeningRoomProps {
  project: ProjectSnapshot | null;
  error: string;
  connection: ConnectionState;
  onRetry: () => void;
}

export function ScreeningRoom({ project, error, connection, onRetry }: ScreeningRoomProps) {
  const events = project?.events ?? [];
  const latest = events.at(-1);
  const progress = latest?.progress ?? 0;
  const failed = project?.status === "failed" || Boolean(error);
  const header = useRef<HTMLDivElement>(null);
  const reducedMotion = Boolean(useReducedMotion());
  const { scrollYProgress } = useScroll({ target: header, offset: ["start end", "end start"] });
  const smooth = useSpring(scrollYProgress, { stiffness: 15, damping: 32, mass: 1.8 });
  const y = useTransform(smooth, [0, 1], [60, -120]);
  const opacity = useTransform(smooth, [0.3, 0.5], [0, 1]);
  const transform = useMotionTemplate`rotateX(24deg) translateY(${y}px) translateZ(15px)`;
  const keepers = project?.assets.filter((asset) => asset.kept).length ?? 0;

  return (
    <div className="relative min-h-screen overflow-hidden bg-black">
      <VideoBackground src={VIDEOS.screening} />
      <div className="pointer-events-none absolute inset-0 bg-black/65" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-[180px] bg-gradient-to-b from-black to-transparent" aria-hidden="true" />
      <div className="relative z-20 mx-auto max-w-[1440px] px-4 pb-16 pt-28 md:px-8 md:pt-32">
        <div ref={header} className="mb-8 border-b border-white/10 pb-8 [perspective:400px]">
          <motion.div style={reducedMotion ? { opacity: 1 } : { transform, opacity }}>
            <p className="mono mb-3 text-[11px] tracking-[0.14em] text-white/55">LIVE MULTI-AGENT SCREENING ROOM</p>
            <h1 className="max-w-5xl text-[clamp(34px,6vw,72px)] font-light leading-[1.05] tracking-[-0.03em]">Every signal becomes a cut.</h1>
            <p className="mt-5 max-w-2xl text-sm leading-relaxed text-white/55">The Memory Curator reads the dailies while the Voice Analyst finds the real story. The screenplay, poster, score, and final render follow in sequence.</p>
          </motion.div>
          <div className="mt-6 flex items-center justify-between gap-4">
            <p className="mono flex items-center gap-2 text-[11px] text-white/55"><span className={`inline-block size-2 rounded-full ${connection === "live" ? "bg-white" : "bg-white/35"}`} aria-hidden="true" />{connection === "live" ? "LIVE FEED" : connection === "stale" ? "FEED STALE / RECONNECTING" : connection === "closed" ? "FEED CLOSED" : "CONNECTING"}</p>
            <p className="mono text-[11px] text-white/55">{Math.round(progress)}%</p>
          </div>
          <div className="mt-3 h-px bg-white/15" role="progressbar" aria-label="Trailer production progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
            <div className="h-full origin-left bg-white transition-transform duration-500" style={{ transform: `scaleX(${progress / 100})` }} />
          </div>
          <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{latest ? `${latest.agent.replaceAll("_", " ")}: ${latest.message}` : "Project is loading"}</p>
        </div>

        <div className="mb-12 grid gap-8 md:grid-cols-3 md:gap-6" aria-label="Production metrics">
          {[[`${Math.round(progress)}%`, "Render progress"], [String(keepers).padStart(2, "0"), "Keeper shots"], [String(project?.assets.length ?? 0).padStart(2, "0"), "Source frames"]].map(([value, label], index) => (
            <motion.div
              key={label}
              initial={reducedMotion ? false : { opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: reducedMotion ? 0 : 0.8, delay: reducedMotion ? 0 : index * 0.15 }}
            >
              <p className="text-[clamp(48px,10vw,80px)] font-light leading-none tracking-[-0.04em]">{value}</p>
              <p className="mt-4 text-sm text-white/45">{label}</p>
            </motion.div>
          ))}
        </div>

        {failed ? (
          <section className="studio-panel mx-auto max-w-2xl p-6 text-center">
            <WarningCircle size={32} className="mx-auto mb-4 text-white" aria-hidden="true" />
            <h2 className="display text-2xl uppercase">The reel jammed.</h2>
            <p className="mt-3 text-sm leading-6 text-white/55">{project?.error || error || "The production feed was interrupted."}</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Button onClick={onRetry}><ArrowClockwise size={17} aria-hidden="true" /> Reconnect</Button>
              <Link href="/" className="btn btn-secondary"><ArrowLeft size={17} aria-hidden="true" /> Back to slate</Link>
            </div>
          </section>
        ) : (
          <div className="grid items-start gap-6 lg:grid-cols-12">
            <section id="dailies" className="studio-panel scroll-mt-24 p-4 sm:p-5 lg:col-span-8">
              <div className="mb-4 flex items-end justify-between gap-3">
                <div>
                  <p className="mono text-[11px] text-white/55">CONTACT SHEET / A-CAM</p>
                  <h2 className="display mt-1 text-xl uppercase">Dailies under review</h2>
                </div>
                <p className="metadata text-right">{keepers} KEEPERS<br />{project?.assets.length ?? 0} FRAMES</p>
              </div>
              <div className="film-perforations mb-2 h-2" aria-hidden="true" />
              <ContactSheet assets={project?.assets ?? []} />
              <div className="film-perforations mt-2 h-2" aria-hidden="true" />
            </section>

            <aside id="agents" className="studio-panel scroll-mt-24 p-4 sm:p-5 lg:col-span-4" aria-label="Agent telemetry">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="display text-xl uppercase">Agent telemetry</h2>
                <span className="mono text-[11px] text-white/45">SSE / 01</span>
              </div>
              <AgentRail events={events} />
              <div className="mt-5 rounded-lg bg-black/55 p-3">
                <p className="mono mb-2 text-[11px] text-white/45">PRODUCTION LOG</p>
                <div className="max-h-36 space-y-2 overflow-y-auto" aria-label="Recent production log">
                  {events.slice(-5).reverse().map((event) => (
                    <p key={event.id} className="mono text-[11px] leading-5 text-white/55">
                      <span className="text-white">{String(event.id).padStart(3, "0")}</span> {event.message}
                    </p>
                  ))}
                  {!events.length && <p className="mono text-[11px] text-white/45">Waiting for the projectionist…</p>}
                </div>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
