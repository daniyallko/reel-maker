"use client";

import { Check, Copy, DownloadSimple, Play } from "@phosphor-icons/react";
import Link from "next/link";
import { useRef, useState } from "react";
import { DEFAULT_SETTINGS, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";
import { GlyphCanvas } from "./glyph-canvas";
import { GlyphTweaks } from "./glyph-tweaks";
import type { StudioOutput } from "@/lib/types";
import { CurtainModal } from "./curtain-modal";
import { PosterTilt } from "./poster-tilt";
import { SceneTimeline } from "./scene-timeline";

export function StudioPremiere({ output, sourceUrl }: { output: StudioOutput; sourceUrl?: string }) {
  const video = useRef<HTMLVideoElement>(null);
  const [species, setSpecies] = useState<SpeciesKey>("moth");
  const [settings, setSettings] = useState<GlyphSettings>(DEFAULT_SETTINGS);
  const [currentTime, setCurrentTime] = useState(0);
  const [notice, setNotice] = useState("");
  const [inspecting, setInspecting] = useState(false);

  async function copyScript() {
    try {
      await navigator.clipboard.writeText(output.script);
      setNotice("Script copied to the clipboard");
    } catch {
      setNotice("Clipboard access was blocked. Select the script below to copy it.");
    }
    window.setTimeout(() => setNotice(""), 4000);
  }

  return (
    <div className="glyph-page">
      <GlyphCanvas species={species} settings={settings} />
      <GlyphTweaks settings={settings} onChange={(key, value) => setSettings((current) => ({ ...current, [key]: value }))} species={species} />
      <div className="glyph-page-content">
        <header className="premiere-hero" id="press-kit">
          <div className="premiere-heading">
            <div className="avatar" aria-hidden="true" />
            <div>
              <p className="mono premiere-kicker">THE PREMIERE PRESS KIT</p>
              <h1>{output.title}</h1>
              {sourceUrl && <p className="premiere-source">SOURCE / <a href={sourceUrl} target="_blank" rel="noopener noreferrer">{sourceUrl}</a></p>}
            </div>
          </div>
          <Link href="/" className="btn btn-secondary"><Play size={17} aria-hidden="true" /> New URL</Link>
        </header>

        <div className="premiere-metrics" aria-label="Video metadata">
          <span>{output.duration.toFixed(0)} sec runtime</span>
          <span>{output.scenes.length.toString().padStart(2, "0")} scenes</span>
          <span>{output.bpm} BPM</span>
          <span>1080 × 1920 / 30 fps</span>
        </div>

        <div className="premiere-layout">
          <section className="premiere-player-frame" aria-label="Trailer player">
            <div className="premiere-player-label mono">FINAL CUT / 9:16</div>
            <video
              ref={video}
              src={output.trailer_url}
              className="premiere-video"
              controls
              playsInline
              preload="metadata"
              onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
              aria-label={`${output.title} vertical motion video`}
            >
              Your browser does not support HTML5 video. <a href={output.trailer_url}>Download the reel.</a>
            </video>
            <SceneTimeline scenes={output.scenes} currentTime={currentTime} onSeek={(time) => {
              if (video.current) {
                video.current.currentTime = time;
                setCurrentTime(time);
              }
            }} />
          </section>

          <aside className="premiere-side" aria-label="Press kit">
            <div className="premiere-poster">
              <PosterTilt src={output.thumbnail_url} title={output.title} onOpen={() => setInspecting(true)} />
            </div>
            <div className="premiere-summary">
              <p className="mono premiere-kicker">NANO BANANA COVER / 9:16</p>
              <h2>The source, reframed.</h2>
              <p>Real captures and generated artwork inside one deterministic motion system.</p>
              <dl className="premiere-facts">
                <div><dt>Runtime</dt><dd>{output.duration.toFixed(0)} SEC</dd></div>
                <div><dt>Scenes</dt><dd>{output.scenes.length.toString().padStart(2, "0")}</dd></div>
                <div><dt>Beat grid</dt><dd>{output.bpm} BPM</dd></div>
                {Object.keys(output.critique_scores ?? {}).length > 0 && <div><dt>Director score</dt><dd>{Math.min(...Object.values(output.critique_scores ?? {}))}/10</dd></div>}
              </dl>
              <div className="premiere-downloads">
                <a href={output.trailer_url} className="btn btn-primary" download><DownloadSimple size={18} aria-hidden="true" /> Download MP4</a>
                <a href={output.thumbnail_url} className="btn btn-secondary" download><DownloadSimple size={18} aria-hidden="true" /> Download PNG</a>
                <a href={`/api/studio/projects/${output.trailer_url.split("/")[2]}/download`} className="btn btn-primary" download><DownloadSimple size={18} aria-hidden="true" /> Download all</a>
              </div>
            </div>
          </aside>
        </div>

        <div className="premiere-script">
          <section className="studio-panel p-5" aria-labelledby="script-title">
            <div className="premiere-section-heading">
              <h2 id="script-title">Script + cited sources</h2>
              <button type="button" className="btn btn-secondary min-h-11 px-3 text-xs" onClick={copyScript}><Copy size={16} aria-hidden="true" /> Copy script</button>
            </div>
            <pre className="premiere-script-text">{output.script}</pre>
          </section>
          <section className="studio-panel p-5" aria-label="Cited sources">
            <h2>Cited sources</h2>
            <ol className="premiere-sources">
              {output.sources.map((source, index) => (
                <li key={`${source.url}-${index}`}>
                  <span className="mono">[{index + 1}]</span>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a>
                  <p>{source.claim}</p>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
      <footer className="glyph-footer">LINK2REEL / SOURCE TO MOTION</footer>
      {inspecting && (
        <CurtainModal title="Cover thumbnail" onClose={() => setInspecting(false)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={output.thumbnail_url} alt={`Full-resolution cover for ${output.title}`} className="mx-auto w-full max-w-[720px]" />
        </CurtainModal>
      )}
      {notice && <p role="status" className="premiere-notice"><Check size={16} aria-hidden="true" />{notice}</p>}
    </div>
  );
}
