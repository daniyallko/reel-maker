"use client";

import { ArrowSquareOut, DownloadSimple, InstagramLogo, Plus, ShareNetwork, WhatsappLogo } from "@phosphor-icons/react";
import { AnimatePresence } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { shareForInstagram, whatsappShareUrl } from "@/lib/share";
import type { ProjectSnapshot } from "@/lib/types";
import { timecode } from "@/lib/format";
import { CastStack } from "./cast-stack";
import { CinematicFooter } from "./cinematic-footer";
import { VIDEOS, VideoBackground } from "./cinematic-media";
import { CinematicTitle } from "./cinematic-title";
import { CurtainModal } from "./curtain-modal";
import { PosterTilt } from "./poster-tilt";
import { TrailerPlayer } from "./trailer-player";

export function Premiere({ project }: { project: ProjectSnapshot }) {
  const output = project.output!;
  const [modal, setModal] = useState<"poster" | "edl" | null>(null);
  const [notice, setNotice] = useState("");

  function shareWhatsApp() {
    window.open(whatsappShareUrl(output.edl.title, window.location.href), "_blank", "noopener,noreferrer");
  }

  async function shareInstagram() {
    try {
      const message = await shareForInstagram(output.edl.title, new URL(output.trailer_url, window.location.origin).toString());
      setNotice(message);
      window.setTimeout(() => setNotice(""), 5000);
    } catch (cause) {
      if (cause instanceof Error && cause.name === "AbortError") return;
      setNotice("Sharing was blocked. Download the trailer, then add it to your reel.");
    }
  }

  return (
    <div className="relative min-h-screen bg-black pb-24 md:pb-0">
      <VideoBackground src={VIDEOS.premiere} />
      <div className="pointer-events-none absolute inset-0 bg-black/70" aria-hidden="true" />
      <div className="relative z-20 mx-auto max-w-[1440px] px-4 pb-32 pt-28 md:px-8 md:pb-16 md:pt-32">
        <div id="press-kit" className="mb-8 flex scroll-mt-24 flex-col justify-between gap-6 border-b border-white/10 pb-8 md:flex-row md:items-end">
          <CinematicTitle title={output.edl.title} tagline={output.edl.tagline} />
          <Link href="/" className="btn btn-secondary shrink-0 self-start md:self-auto"><Plus size={17} aria-hidden="true" /> New production</Link>
        </div>

        <div className="mb-12 grid gap-8 md:grid-cols-3 md:gap-6" aria-label="Press kit metrics">
          {[[`${output.duration.toFixed(1)}s`, "Final runtime"], [String(output.edl.segments.length).padStart(2, "0"), "Timed shots"], [String(output.cast_cards.length).padStart(2, "0"), "Cast freeze frames"]].map(([value, label]) => (
            <div key={label}>
              <p className="text-[clamp(48px,10vw,80px)] font-light leading-none tracking-[-0.04em]">{value}</p>
              <p className="mt-4 text-sm text-white/45">{label}</p>
            </div>
          ))}
        </div>

        <div className="grid items-start gap-8 lg:grid-cols-12">
          <div className="lg:col-span-6 xl:col-span-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="mono text-[11px] text-white/50">FINAL CUT / 9:16 / H.264</p>
              <p className="mono text-[11px] text-white">{timecode(output.duration)}</p>
            </div>
            <TrailerPlayer output={output} assets={project.assets} />
            <button type="button" className="btn btn-ghost mt-2 px-0 text-xs" onClick={() => setModal("edl")}>Inspect edit decision list <ArrowSquareOut size={16} className="text-white" aria-hidden="true" /></button>
          </div>

          <div className="space-y-10 lg:col-span-6 lg:col-start-7 xl:col-span-6 xl:col-start-7">
            <div className="grid items-start gap-6 sm:grid-cols-2">
              <PosterTilt src={output.poster_url} title={output.edl.title} onOpen={() => setModal("poster")} />
              <div className="flex flex-col justify-between gap-6 sm:min-h-full">
                <div>
                  <p className="mono text-[11px] text-white/55">THEATRICAL ONE-SHEET</p>
                  <h2 className="display mt-2 text-3xl uppercase leading-tight">Proof the weekend happened.</h2>
                  <p className="mt-3 text-sm leading-6 text-white/55">Hero frame graded, credits set, and every bad decision preserved in print.</p>
                </div>
                <dl className="border-y border-white/10 py-3 text-xs">
                  <div className="flex justify-between gap-4 py-1"><dt className="text-white/45">Runtime</dt><dd className="mono">{output.duration.toFixed(1)} SEC</dd></div>
                  <div className="flex justify-between gap-4 py-1"><dt className="text-white/45">Shots</dt><dd className="mono">{output.edl.segments.length.toString().padStart(2, "0")}</dd></div>
                  <div className="flex justify-between gap-4 py-1"><dt className="text-white/45">Genre</dt><dd className="mono uppercase">{output.edl.genre}</dd></div>
                  <div className="flex justify-between gap-4 py-1"><dt className="text-white/45">Certification</dt><dd className="mono">98% CHAOTIC</dd></div>
                </dl>
                <div className="grid gap-2">
                  <a href={`/api/projects/${project.id}/download`} className="btn btn-primary" download><DownloadSimple size={18} aria-hidden="true" /> Download all</a>
                  <div className="grid grid-cols-2 gap-2">
                    <button type="button" className="btn btn-secondary px-2" onClick={shareWhatsApp}><WhatsappLogo size={18} aria-hidden="true" /> WhatsApp</button>
                    <button type="button" className="btn btn-secondary px-2" onClick={shareInstagram}><InstagramLogo size={18} aria-hidden="true" /> Instagram</button>
                  </div>
                </div>
              </div>
            </div>

            <div id="cast" className="relative scroll-mt-24 overflow-hidden rounded-[14px] border border-white/10 p-4 sm:p-6">
              <VideoBackground src={VIDEOS.cast} />
              <div className="pointer-events-none absolute inset-0 bg-black/70" aria-hidden="true" />
              <div className="relative z-10"><CastStack cards={output.cast_cards} /></div>
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-20"><CinematicFooter /></div>

      <AnimatePresence>
        {modal === "poster" && (
          <CurtainModal title="Theatrical one-sheet" onClose={() => setModal(null)}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={output.poster_url} alt={`Full-resolution poster for ${output.edl.title}`} className="mx-auto h-auto max-h-none w-full max-w-[720px]" />
          </CurtainModal>
        )}
        {modal === "edl" && (
          <CurtainModal title="Edit decision list" onClose={() => setModal(null)}>
            <div className="mx-auto max-w-5xl">
              <p className="mono mb-6 text-xs text-white/55">{output.edl.title} / {output.duration.toFixed(1)} SEC / {output.edl.segments.length} SHOTS</p>
              <ol className="border-t border-white/10">
                {output.edl.segments.map((segment) => (
                  <li key={`${segment.asset_id}-${segment.start}`} className="grid gap-3 border-b border-white/10 py-4 sm:grid-cols-[90px_110px_1fr]">
                    <span className="mono text-xs text-white">{timecode(segment.start)}</span>
                    <span className="mono text-[11px] text-white/50">ACT {segment.act}<br />{segment.ken_burns.replaceAll("_", " ").toUpperCase()}</span>
                    <div className="min-w-0">
                      <p className="text-sm text-white">{segment.title_card ?? project.assets.find((asset) => asset.id === segment.asset_id)?.filename ?? segment.asset_id}</p>
                      {segment.voiceover && <p className="mt-1 text-sm leading-6 text-white/55">VO: {segment.voiceover}</p>}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </CurtainModal>
        )}
      </AnimatePresence>

      {notice && <p role="status" className="fixed bottom-24 left-1/2 z-[60] w-[calc(100%-32px)] max-w-lg -translate-x-1/2 border border-white/15 bg-black/90 px-4 py-3 text-center text-sm shadow-xl md:bottom-6">{notice}</p>}

      <div className="safe-bottom fixed inset-x-0 bottom-0 z-30 grid grid-cols-2 gap-2 border-t border-white/10 bg-black/85 px-4 pt-3 backdrop-blur-md md:hidden">
        <a href={`/api/projects/${project.id}/download`} className="btn btn-primary" download><DownloadSimple size={18} aria-hidden="true" /> Download all</a>
        <button type="button" className="btn btn-secondary" onClick={shareWhatsApp}><ShareNetwork size={18} aria-hidden="true" /> Share</button>
      </div>
    </div>
  );
}
