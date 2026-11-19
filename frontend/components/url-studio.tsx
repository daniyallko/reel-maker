"use client";

import { Link as LinkIcon, Play } from "@phosphor-icons/react";
import { useState } from "react";
import { createStudioProject, createStudioSample } from "@/lib/api";
import { AppHeader } from "./app-header";
import { CinematicFooter } from "./cinematic-footer";
import { MouseScrubVideo } from "./cinematic-media";
import { ScrambleIn } from "./scramble";
import { Button, ErrorNote, SectionHeading } from "./ui";

const SAMPLE_URLS = [
  { label: "AI startup", url: "https://example.com" },
  { label: "GitHub repo", url: "https://github.com/google/genai" },
  { label: "Product launch", url: "https://www.producthunt.com" },
  { label: "Wikipedia deep-dive", url: "https://en.wikipedia.org/wiki/Artificial_intelligence" },
];
const STYLES = [
  { id: "launch", label: "High-Energy Tech Launch" },
  { id: "deep_dive", label: "Vox-Style Deep Dive" },
  { id: "roast", label: "Honest Product Roast" },
  { id: "founder", label: "60s Founder Story" },
];
const VOICES = ["Charon", "Fenrir", "Puck", "Aoede"];

export function UrlStudio({ onProjectCreated }: { onProjectCreated: (id: string) => void }) {
  const [url, setUrl] = useState("");
  const [style, setStyle] = useState("launch");
  const [voice, setVoice] = useState("Fenrir");
  const [pending, setPending] = useState<"url" | "sample" | null>(null);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
    } catch {
      setError("Enter a public http or https URL");
      return;
    }
    setPending("url");
    setError("");
    try {
      const project = await createStudioProject({ url, style, voice });
      onProjectCreated(project.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The URL could not be harvested");
      setPending(null);
    }
  }

  async function sample() {
    setPending("sample");
    setError("");
    try {
      const project = await createStudioSample();
      onProjectCreated(project.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The sample could not be loaded");
      setPending(null);
    }
  }

  return (
    <div className="min-h-dvh bg-black pb-16 md:pb-0">
      <AppHeader />
      <main id="main-content">
        <section className="relative flex min-h-[72dvh] flex-col justify-end overflow-hidden px-4 pb-16 pt-28 sm:px-8 md:pb-20">
          <MouseScrubVideo />
          <div className="pointer-events-none absolute inset-0 bg-black/55" aria-hidden="true" />
          <div className="dot-grid pointer-events-none absolute inset-0" aria-hidden="true" />
          <div className="neon-watermark pointer-events-none absolute left-1/2 top-1/2 w-full -translate-x-1/2 -translate-y-1/2 text-center text-[clamp(100px,25vw,400px)] leading-none" aria-hidden="true">REEL</div>
          <div className="relative z-10">
            <p className="mono mb-4 text-[11px] tracking-[.14em] text-white/55">AUTONOMOUS URL-TO-MOTION STUDIO</p>
            <h1 className="max-w-5xl text-[clamp(48px,10vw,104px)] font-light leading-[.94] tracking-[-.04em]">
              <ScrambleIn text="Any link." delay={200} triggered /><br />
              <ScrambleIn text="In motion." delay={500} triggered />
            </h1>
            <p className="mt-6 max-w-xl text-sm leading-relaxed text-white/60">No uploads. No timeline. Just a URL. LINK2REEL harvests the story, writes the script, and programs every frame.</p>
          </div>
        </section>

        <section className="relative z-10 mx-auto max-w-5xl px-4 pb-16 md:px-8" aria-labelledby="source-heading">
          <form onSubmit={submit} noValidate className="studio-panel -mt-8 p-5 sm:p-8">
            <SectionHeading index="01" title="Source command bar" detail="PUBLIC URLS ONLY" />
            <label htmlFor="source-url" className="mb-2 block text-sm">Source URL</label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <LinkIcon size={18} className="absolute left-3 top-3.5 text-white/45" aria-hidden="true" />
                <input
                  id="source-url"
                  type="url"
                  className="field pl-10"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://your-next-big-thing.com"
                  required
                  aria-describedby="url-hint"
                />
              </div>
              <Button type="submit" loading={pending === "url"} disabled={pending !== null} className="sm:min-w-40"><Play size={17} aria-hidden="true" /> Make my reel</Button>
            </div>
            <p id="url-hint" className="metadata mt-2">Public pages only. Private IPs and credentials are rejected before launch.</p>

            <div className="mt-5 flex flex-wrap gap-2" aria-label="Sample URLs">
              {SAMPLE_URLS.map((sample) => (
                <button key={sample.label} type="button" className="btn btn-secondary min-h-11 px-3 text-xs" onClick={() => setUrl(sample.url)}>{sample.label}</button>
              ))}
            </div>

            <div className="mt-8 grid gap-8 md:grid-cols-2">
              <fieldset>
                <legend className="mb-3 text-sm">Video style</legend>
                <div className="grid gap-2" role="radiogroup" aria-label="Video style">
                  {STYLES.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      role="radio"
                      aria-checked={style === option.id}
                      onClick={() => setStyle(option.id)}
                      className={`min-h-11 rounded-lg border px-3 text-left text-xs transition-colors ${style === option.id ? "border-white bg-white text-black" : "border-white/15 bg-white/5 text-white/65 hover:border-white/35"}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </fieldset>
              <fieldset id="voice">
                <legend className="mb-3 text-sm">Gemini 3.8 studio voice</legend>
                <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Narration voice">
                  {VOICES.map((option) => (
                    <button
                      key={option}
                      type="button"
                      role="radio"
                      aria-checked={voice === option}
                      onClick={() => setVoice(option)}
                      className={`min-h-11 rounded-lg border px-3 text-xs transition-colors ${voice === option ? "border-white bg-white text-black" : "border-white/15 bg-white/5 text-white/65 hover:border-white/35"}`}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </fieldset>
            </div>

            {error && <div className="mt-5"><ErrorNote>{error}</ErrorNote></div>}
            <div className="mt-8 flex flex-col items-start justify-between gap-4 border-t border-white/10 pt-5 sm:flex-row sm:items-center">
              <p className="text-xs leading-5 text-white/45">Offline or rate-limited? The pre-baked motion demo exercises the complete player and source kit.</p>
              <Button type="button" variant="secondary" loading={pending === "sample"} disabled={pending !== null} onClick={sample}>Load Sample Link (Instant Demo)</Button>
            </div>
          </form>
        </section>
        <CinematicFooter />
      </main>
    </div>
  );
}
