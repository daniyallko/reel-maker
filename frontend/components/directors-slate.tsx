"use client";

import { FilmStrip, Play } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useEffect, useState } from "react";
import { createProject, createSampleProject } from "@/lib/api";
import type { Genre } from "@/lib/types";
import { AppHeader } from "./app-header";
import { CastTagger } from "./cast-tagger";
import { CinematicFooter } from "./cinematic-footer";
import { MouseScrubVideo } from "./cinematic-media";
import { GenreSelector } from "./genre-selector";
import { MediaDump } from "./media-dump";
import { PipelineArchitecture } from "./pipeline-architecture";
import { ScrambleIn } from "./scramble";
import { Button, ErrorNote, SectionHeading } from "./ui";
import { VoiceRecorder } from "./voice-recorder";

export function DirectorsSlate({ onProjectCreated }: { onProjectCreated: (id: string) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [cast, setCast] = useState<string[]>([]);
  const [genre, setGenre] = useState<Genre>("comedy");
  const [notes, setNotes] = useState("");
  const [voiceNote, setVoiceNote] = useState<Blob | null>(null);
  const [pending, setPending] = useState<"project" | "sample" | null>(null);
  const [error, setError] = useState("");
  const [entranceComplete, setEntranceComplete] = useState(false);
  const reducedMotion = Boolean(useReducedMotion());

  useEffect(() => {
    const timeout = setTimeout(() => setEntranceComplete(true), reducedMotion ? 0 : 800);
    return () => clearTimeout(timeout);
  }, [reducedMotion]);

  async function rollCamera() {
    if (files.length < 10) {
      setError(`Add ${10 - files.length} more ${files.length === 9 ? "shot" : "shots"}. A trailer needs at least 10 source files.`);
      return;
    }
    if (!cast.length) {
      setError("Add at least one name to the cast list.");
      return;
    }
    setPending("project");
    setError("");
    try {
      const project = await createProject({ files, cast, genre, notes, voiceNote });
      onProjectCreated(project.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The slate could not be saved. Try again.");
      setPending(null);
    }
  }

  async function sample() {
    setPending("sample");
    setError("");
    try {
      const project = await createSampleProject();
      onProjectCreated(project.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The sample reel could not be loaded. Is the backend running?");
      setPending(null);
    }
  }

  return (
    <div className="min-h-dvh bg-black pb-24 md:pb-0">
      <AppHeader />
      <main id="main-content">
        <section className="relative flex h-screen min-h-[720px] flex-col overflow-hidden px-4 pb-28 pt-24 sm:px-6 sm:pb-12 md:px-8" style={{ height: "100dvh" }} aria-label="CUTLINE introduction">
          <MouseScrubVideo />
          <div className="pointer-events-none absolute inset-0 bg-black/45" aria-hidden="true" />
          <div className="dot-grid pointer-events-none absolute inset-0" aria-hidden="true" />
          <div className="neon-watermark pointer-events-none absolute left-1/2 top-1/2 w-full -translate-x-1/2 translate-y-[-30%] text-center text-[clamp(120px,30vw,521px)] leading-none" aria-hidden="true">CUTLINE</div>

          <motion.div
            className="relative z-10 flex flex-1 flex-col justify-end"
            initial={{ opacity: 0 }}
            animate={{ opacity: entranceComplete ? 1 : 0 }}
            transition={{ duration: reducedMotion ? 0 : 1 }}
          >
            <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
              <div className="flex flex-col gap-4">
                <h1 className="text-[clamp(40px,10vw,100px)] font-light leading-[0.95] tracking-[-0.03em] text-white">
                  <ScrambleIn text="Weekend" delay={200} triggered={entranceComplete} /><br />
                  <ScrambleIn text="In motion" delay={500} triggered={entranceComplete} />
                </h1>
                <motion.p
                  className="max-w-md text-[13px] leading-relaxed text-white/65 sm:text-[15px]"
                  initial={reducedMotion ? false : { opacity: 0, y: 25 }}
                  animate={{ opacity: entranceComplete ? 1 : 0, y: entranceComplete ? 0 : 25 }}
                  transition={{ duration: reducedMotion ? 0 : 0.9, delay: reducedMotion ? 0 : 0.2, ease: [0.215, 0.61, 0.355, 1] }}
                >
                  Dump the evidence. Name the suspects. CUTLINE maps your photos, clips, and inside jokes into one adaptive edit with a trailer, poster, and cast press kit.
                </motion.p>
              </div>
              <h2 className="text-left text-[clamp(40px,10vw,100px)] font-light leading-[0.95] tracking-[-0.03em] text-white md:text-right">
                <ScrambleIn text="One" delay={700} triggered={entranceComplete} /><br />
                <ScrambleIn text="Trailer" delay={1000} triggered={entranceComplete} />
              </h2>
            </div>
            <div className="mt-8 flex items-center gap-3 text-xs text-white/45">
              <span className="h-px w-12 bg-white/35" aria-hidden="true" /> Scroll to load dailies
            </div>
          </motion.div>
        </section>

        <div className="relative z-10 bg-black px-4 pb-16 pt-20 md:px-8">
          <div className="mx-auto max-w-[1440px]">
            <div className="mb-8 border-b border-white/10 pb-6">
              <p className="mono mb-2 text-[11px] tracking-[0.14em] text-white/50">PRODUCTION 001 / DIRECTOR'S SLATE</p>
              <h2 className="text-3xl font-light tracking-[-0.03em] sm:text-4xl">Build the evidence locker</h2>
            </div>
            <div className="grid items-start gap-6 lg:grid-cols-12">
              <section id="media" className="studio-panel scroll-mt-24 p-4 sm:p-5 lg:col-span-7">
                <SectionHeading index="01" title="Media dump" detail="PHOTO + VIDEO / 25 MAX" />
                <MediaDump files={files} onChange={setFiles} />
              </section>

              <div className="space-y-6 lg:col-span-5">
                <section className="studio-panel p-4 sm:p-5">
                  <SectionHeading index="02" title="The real story" detail="OPTIONAL AUDIO" />
                  <VoiceRecorder value={voiceNote} onChange={setVoiceNote} />
                  <label htmlFor="inside-jokes" className="mb-2 mt-5 block text-sm">Inside jokes + plot twists</label>
                  <textarea
                    id="inside-jokes"
                    className="field min-h-24 resize-y"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    placeholder="Theo swore the shortcut would save twenty minutes…"
                    maxLength={1200}
                  />
                </section>

                <section id="cast" className="studio-panel scroll-mt-24 p-4 sm:p-5">
                  <SectionHeading index="03" title="Call sheet" detail={`${cast.length} NAMES`} />
                  <CastTagger value={cast} onChange={setCast} />
                </section>

                <section className="studio-panel p-4 sm:p-5">
                  <SectionHeading index="04" title="Genre" detail="SELECT ONE" />
                  <GenreSelector value={genre} onChange={setGenre} />
                </section>
              </div>
            </div>

            {error && <div className="mt-6"><ErrorNote>{error}</ErrorNote></div>}
            <div className="mt-8 hidden items-center justify-between border-t border-white/10 pt-6 md:flex">
              <p className="max-w-xl text-xs leading-5 text-white/45">Your own media goes to Gemini only after you roll camera. Sample mode runs entirely offline.</p>
              <div className="flex gap-3">
                <Button variant="secondary" loading={pending === "sample"} disabled={pending !== null} onClick={sample}>
                  <FilmStrip size={18} aria-hidden="true" /> Load Sample Chaos Trip
                </Button>
                <Button loading={pending === "project"} disabled={pending !== null} onClick={rollCamera}>
                  <Play size={18} aria-hidden="true" /> Roll camera
                </Button>
              </div>
            </div>
          </div>
        </div>

        <PipelineArchitecture />
        <CinematicFooter />
      </main>

      <div className="safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-black/85 px-4 pt-3 backdrop-blur-md md:hidden">
        <div className="grid grid-cols-[1fr_1.2fr] gap-2">
          <Button variant="secondary" loading={pending === "sample"} disabled={pending !== null} onClick={sample} className="px-2 text-xs">Sample chaos trip</Button>
          <Button loading={pending === "project"} disabled={pending !== null} onClick={rollCamera} className="px-2">
            <Play size={18} aria-hidden="true" /> Roll camera
          </Button>
        </div>
      </div>
    </div>
  );
}
