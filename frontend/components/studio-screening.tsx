"use client";

import { ArrowClockwise, Check, CircleNotch, XCircle } from "@phosphor-icons/react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import type { StudioProjectSnapshot } from "@/lib/types";
import type { ConnectionState } from "@/lib/use-project-events";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { DEFAULT_SETTINGS, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";
import { GlyphCanvas } from "./glyph-canvas";
import { GlyphTweaks } from "./glyph-tweaks";
import { Button } from "./ui";

const AGENTS = [
  ["harvester", "Web Harvester"],
  ["researcher", "External Story Researcher"],
  ["scriptwriter", "Viral Scriptwriter"],
  ["nano_visuals", "Nano Banana Visuals"],
  ["voice_studio", "Gemini Studio Voice"],
  ["motion_coder", "Motion Coder"],
  ["vision_director", "Vision Director"],
  ["renderer", "30fps Renderer"],
  ["qa_critic", "QA Critic"],
] as const;

export function StudioScreening({ project, connection, onRetry, error }: { project: StudioProjectSnapshot | null; connection: ConnectionState; onRetry: () => void; error?: string }) {
  const [species, setSpecies] = useState<SpeciesKey>("moth");
  const [settings, setSettings] = useState<GlyphSettings>(DEFAULT_SETTINGS);
  const reduceMotion = Boolean(useReducedMotion());
  const events = project?.events ?? [];
  const latest = events.at(-1);
  const progress = latest?.progress ?? 0;
  const audioPreview = [...events].reverse().find((event) => typeof event.payload?.preview_url === "string")?.payload?.preview_url as string | undefined;
  const current = events.at(-1);
  const currentLabel = current?.agent === "pipeline" ? "Pipeline" : AGENTS.find(([id]) => id === current?.agent)?.[1] ?? "Studio preparation";
  const sourceTitle = project?.source_title || project?.source_url || "Preparing your source";
  const isWebSource = Boolean(project?.source_url.startsWith("http://") || project?.source_url.startsWith("https://"));
  const connectionLabel = project?.status === "failed" ? "Production stopped" : connection === "live" ? "Live production" : connection === "stale" ? "Reconnecting to live updates" : connection === "closed" ? "Production review closed" : "Connecting to the studio";

  return (
    <div className="glyph-page">
      <GlyphCanvas species={species} settings={settings} />
      <GlyphTweaks settings={settings} onChange={(key, value) => setSettings((current) => ({ ...current, [key]: value }))} species={species} />
      <div className="glyph-page-content">
        <div className="screening-heading mb-8 border-b border-white/10 pb-6">
          <p className="mono mb-3 text-[11px] tracking-[.14em] text-white/55">{connectionLabel.toUpperCase()} / {Math.round(progress)}%</p>
          <h1 className="text-3xl font-medium tracking-tight sm:text-4xl">Building your cinematic reel</h1>
          <p className="mt-3 max-w-full break-words text-sm text-white/55">
            {isWebSource ? <a href={project?.source_url} target="_blank" rel="noopener noreferrer" className="underline decoration-white/30 underline-offset-4">{sourceTitle}</a> : sourceTitle}
          </p>
          <div className="mt-5 h-px bg-white/15" role="progressbar" aria-label="Studio production progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
            <div className="h-full origin-left bg-white transition-transform duration-500" style={{ transform: `scaleX(${progress / 100})` }} />
          </div>
          <p className="sr-only" role="status" aria-live="polite">{latest?.message ?? "Connecting to the studio"}</p>
        </div>

        <>
          {project?.error || error ? (
            <section className="studio-panel mx-auto mb-6 max-w-2xl p-6 text-center" role="alert">
              <XCircle size={30} className="mx-auto mb-4 text-white" aria-hidden="true" />
              <h2 className="text-2xl">The reel jammed.</h2>
              <p className="mt-3 text-sm leading-6 text-white/55">{project?.error || error}</p>
              <Button className="mt-5" onClick={onRetry}><ArrowClockwise size={17} aria-hidden="true" /> Reconnect</Button>
            </section>
          ) : null}
          <div className="grid items-start gap-6 lg:grid-cols-12">
            <section id="source-assets" className="studio-panel p-4 sm:p-5 lg:col-span-8" aria-label="Source asset contact sheet">
              <div className="mb-4 flex items-end justify-between gap-3">
                <div>
                  <p className="mono text-[11px] text-white/55">SOURCE CONTACT SHEET</p>
                  <h2 className="mt-1 text-xl">Real assets, not fake UI</h2>
                </div>
                <span className="metadata">{project?.assets.length ?? 0} ASSETS</span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {project?.assets.map((asset) => (
                  <figure key={asset.id} className="relative aspect-[4/3] overflow-hidden rounded-lg border border-white/10 bg-black/45">
                    {asset.kind === "video" ? (
                      <video src={asset.url} className="size-full object-cover" muted playsInline controls aria-label={asset.label} />
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={asset.url} alt={asset.label} className="size-full object-cover" loading="lazy" />
                    )}
                    <figcaption className="absolute inset-x-0 bottom-0 bg-black/75 px-2 py-1.5 text-[11px] text-white/75">{asset.label}</figcaption>
                  </figure>
                ))}
                {!project?.assets.length && Array.from({ length: 6 }, (_, index) => <div key={index} className="aspect-[4/3] animate-pulse rounded-lg bg-white/5" />)}
              </div>
              {audioPreview && (
                <div className="mt-4 border-t border-white/10 pt-4">
                  <p className="mono mb-2 text-[11px] text-white/45">NARRATION PREVIEW</p>
                  <audio src={audioPreview} controls className="h-11 w-full">Your browser does not support audio playback.</audio>
                </div>
              )}
            </section>

            <aside id="agent-telemetry" className="studio-panel p-4 sm:p-5 lg:col-span-4" aria-label="Current production process">
              <p className="mono mb-4 text-[11px] text-white/55">CURRENT PROCESS</p>
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={current?.id ?? "waiting"}
                  initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={reduceMotion ? undefined : { opacity: 0, y: -12 }}
                  transition={{ duration: reduceMotion ? 0 : 0.24, ease: "easeOut" }}
                  className="min-h-32"
                >
                  <span className="mb-4 inline-flex" role="img" aria-label={`${currentLabel} ${current?.status === "running" ? "executing" : current?.status ?? "pending"}`}>
                    {current?.status === "running" ? <CircleNotch size={24} className={reduceMotion ? "text-white" : "animate-spin text-white"} /> : current?.status === "complete" ? <Check size={24} /> : current?.status === "failed" ? <XCircle size={24} /> : <CircleNotch size={24} className="text-white/25" />}
                  </span>
                  <h2 className="text-xl">{currentLabel}</h2>
                  <p className="mt-2 text-sm leading-6 text-white/55">{current?.message ?? "Preparing the source bundle…"}</p>
                  <p className="mono mt-4 text-[10px] text-white/35">{current ? `EVENT #${String(current.id).padStart(6, "0")} / ${current.status.toUpperCase()} / ${current.progress}%` : "WAITING FOR BACKEND RESPONSE"}</p>
                </motion.div>
              </AnimatePresence>
            </aside>
            <section className="studio-panel overflow-hidden lg:col-span-12" aria-labelledby="backend-stream-title">
              <div className="flex flex-wrap items-end justify-between gap-3 border-b border-white/10 px-4 py-4 sm:px-5">
                <div>
                  <p className="mono text-[11px] text-white/55">BACKEND RESPONSE STREAM</p>
                  <h2 id="backend-stream-title" className="mt-1 text-xl">Live execution log</h2>
                </div>
                <p className="mono text-[11px] text-white/55">SSE / {connection.toUpperCase()} / {events.length} EVENTS</p>
              </div>
              <div role="log" aria-label="Backend response stream" aria-live="polite" aria-relevant="additions text" className="mono max-h-80 overflow-y-auto bg-black/50 px-4 py-2 text-[11px] sm:px-5">
                {events.length ? events.slice(-12).map((event) => {
                  const timestamp = new Date(event.timestamp * 1000).toISOString();
                  return (
                    <article key={event.id} className="grid gap-2 border-b border-white/10 py-3 last:border-b-0 md:grid-cols-[220px_1fr_auto] md:items-start">
                      <p className="text-white/45">#{String(event.id).padStart(6, "0")} / {event.agent}</p>
                      <p className="leading-5 text-white/85">{event.message}</p>
                      <p className="text-white/45 md:text-right">{event.status.toUpperCase()} / {event.progress}% / <time dateTime={timestamp}>{timestamp.slice(11, 19)} UTC</time></p>
                    </article>
                  );
                }) : <p className="py-4 text-white/45">Awaiting backend response…</p>}
              </div>
            </section>
          </div>
        </>
      </div>
    </div>
  );
}
