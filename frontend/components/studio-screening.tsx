"use client";

import { ArrowClockwise, Check, Circle, CircleNotch, XCircle } from "@phosphor-icons/react";
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

  return (
    <div className="glyph-page">
      <GlyphCanvas species={species} settings={settings} />
      <GlyphTweaks settings={settings} onChange={(key, value) => setSettings((current) => ({ ...current, [key]: value }))} species={species} />
      <div className="glyph-page-content">
        <div className="mb-8 border-b border-white/10 pb-6">
          <div className="masthead">
            <div className="avatar" aria-hidden="true" />
            <h1>Every source becomes a scene.</h1>
          </div>
          <p className="mono mb-2 text-[11px] tracking-[.14em] text-white/55">LIVE AUTONOMOUS SCREENING ROOM</p>
          {project && <p className="mono mt-4 max-w-full break-all text-[11px] text-white/45">SOURCE / <a href={project.source_url} target="_blank" rel="noopener noreferrer" className="underline decoration-white/30 underline-offset-4">{project.source_url}</a></p>}
          <div className="mt-5 flex items-center justify-between gap-4">
            <p className="mono text-[11px] text-white/55">{connection.toUpperCase()} / {project?.id ?? "CONNECTING"}</p>
            <p className="mono text-sm text-white">{Math.round(progress)}%</p>
          </div>
          <div className="mt-3 h-px bg-white/15" role="progressbar" aria-label="Studio production progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
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

            <aside id="agent-telemetry" className="studio-panel p-4 sm:p-5 lg:col-span-4" aria-label="Agent telemetry">
              <h2 className="mb-4 text-xl">Agent telemetry</h2>
              <ol className="divide-y divide-white/10 border-y border-white/10">
                {AGENTS.map(([id, label], index) => {
                  const event = [...events].reverse().find((item) => item.agent === id);
                  const status = project?.status === "failed" && event?.status === "running" ? "failed" : event?.status ?? "pending";
                  return (
                    <li key={id} className="flex min-h-16 items-start gap-3 py-3">
                      <span className="mono w-5 pt-0.5 text-[11px] text-white/40">{String(index + 1).padStart(2, "0")}</span>
                      <span className="pt-0.5" role="img" aria-label={`${label} ${status === "running" ? "executing" : status}`}>
                        {status === "running" ? <CircleNotch size={16} className={reduceMotion ? "text-white" : "animate-spin text-white"} /> : status === "complete" ? <Check size={16} /> : status === "failed" ? <XCircle size={16} /> : <Circle size={16} className="text-white/30" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm ${status === "pending" ? "text-white/40" : "text-white"}`}>{label}</p>
                        <p className="mt-0.5 text-xs leading-5 text-white/45">{event?.message ?? "Waiting for source data"}</p>
                        <p className="mono mt-1 text-[10px] text-white/35">{event ? `EVENT #${String(event.id).padStart(6, "0")} / ${status.toUpperCase()} / ${event.progress}%` : "WAITING FOR BACKEND RESPONSE"}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
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
