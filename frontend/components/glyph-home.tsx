"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createStudioInput, createStudioSample } from "@/lib/api";
import { DEFAULT_SETTINGS, SPECIES, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";
import { GlyphCanvas } from "./glyph-canvas";
import { GlyphTweaks } from "./glyph-tweaks";
import { ErrorNote } from "./ui";

const ACCEPTED_EXTENSIONS = new Set(["pdf", "txt", "png", "jpg", "jpeg", "webp"]);
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_TOTAL_BYTES = 30 * 1024 * 1024;

export function GlyphHome() {
  const router = useRouter();
  const [species, setSpecies] = useState<SpeciesKey>("moth");
  const [settings, setSettings] = useState<GlyphSettings>(DEFAULT_SETTINGS);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [qualityMode, setQualityMode] = useState<"strict" | "draft">("strict");
  const [pending, setPending] = useState<"url" | "sample" | null>(null);
  const [error, setError] = useState("");
  const [thumb, setThumb] = useState({ left: 0, top: 4, width: 0, height: 32 });
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const count = useRef<number | undefined>(undefined);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("animal") as string | null;
    if (requested && SPECIES.some((item) => item.key === requested || `${item.key}s` === requested)) {
      const normalized = requested === "turtles" ? "turtle" : requested === "flyingfish" ? "flyingfish" : requested.replace(/s$/, "") as SpeciesKey;
      if (SPECIES.some((item) => item.key === normalized)) setSpecies(normalized);
    } else {
      try {
        const saved = localStorage.getItem("wild-tab:animal") as SpeciesKey | null;
        if (saved && SPECIES.some((item) => item.key === saved)) setSpecies(saved);
      } catch { /* storage can be blocked */ }
    }
    const rawCount = Number(params.get("count"));
    if (Number.isFinite(rawCount) && rawCount > 0) count.current = Math.min(200, Math.round(rawCount));
    try {
      const saved = localStorage.getItem(`wild-tab:tweaks:${requested || "moth"}`);
      if (saved) setSettings((current) => ({ ...current, ...JSON.parse(saved) }));
    } catch { /* storage can be blocked */ }
    if (navigator.userAgent.includes("Chrome/")) document.documentElement.classList.add("liquid");
    if (window.matchMedia?.("(pointer:fine)")?.matches) textarea.current?.focus();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("wild-tab:animal", species);
      localStorage.setItem(`wild-tab:tweaks:${species}`, JSON.stringify(settings));
    } catch { /* storage can be blocked */ }
  }, [species, settings]);

  useLayoutEffect(() => {
    function placeThumb() {
      const index = SPECIES.findIndex((item) => item.key === species);
      const button = buttons.current[index];
      if (button) setThumb({ left: button.offsetLeft, top: button.offsetTop, width: button.offsetWidth, height: button.offsetHeight });
    }
    placeThumb();
    window.addEventListener("resize", placeThumb);
    return () => window.removeEventListener("resize", placeThumb);
  }, [species]);

  function onChange(key: keyof GlyphSettings, value: number | boolean | string) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  function selectSpecies(key: SpeciesKey) {
    setSpecies(key);
    try { localStorage.setItem("wild-tab:animal", key); } catch { /* storage can be blocked */ }
  }

  function onSpeciesKeyDown(event: React.KeyboardEvent, index: number) {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const next = (index + (event.key === "ArrowRight" ? 1 : -1) + SPECIES.length) % SPECIES.length;
    selectSpecies(SPECIES[next].key);
    buttons.current[next]?.focus();
  }

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const selected = [...incoming];
    if (selected.some((file) => !ACCEPTED_EXTENSIONS.has(file.name.split(".").pop()?.toLowerCase() ?? ""))) {
      setError("Use PDF, TXT, PNG, JPG, JPEG, or WebP source files.");
      return;
    }
    if (selected.some((file) => file.size > MAX_FILE_BYTES)) {
      setError("Each source file must be at most 10 MB.");
      return;
    }
    const next = [...files, ...selected];
    if (next.length > 8) {
      setError("Upload at most 8 source files.");
      return;
    }
    if (next.reduce((total, file) => total + file.size, 0) > MAX_TOTAL_BYTES) {
      setError("Source files must total at most 30 MB.");
      return;
    }
    setError("");
    setFiles(next);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if ((!text.trim() && !files.length) || pending) return;
    if (/^https?:\/\//i.test(text.trim())) {
      try {
        const parsed = new URL(text.trim());
        if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Unsupported protocol");
      } catch {
        setError("Enter a valid public URL or write your story in plain text.");
        return;
      }
    }
    setPending("url");
    setError("");
    try {
      const project = await createStudioInput({ source: text.trim(), style: settings.style, voice: settings.voice, qualityMode, files });
      router.push(`/project/${project.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Your story could not be started.");
      setPending(null);
    }
  }

  async function sample() {
    setPending("sample");
    setError("");
    try {
      const project = await createStudioSample();
      router.push(`/project/${project.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The portfolio demo could not be loaded.");
      setPending(null);
    }
  }

  const hasSource = Boolean(text.trim() || files.length);

  return (
    <div className="glyph-home" style={{ "--blur": `${settings.blur}px`, "--tint": settings.tint, "--edge": settings.edge, "--radius": `${settings.radius}px`, "--composer-width": `${settings.width}px` } as React.CSSProperties}>
      <svg className="liquid-filter" width="0" height="0" aria-hidden="true"><defs><filter id="liquid-glass" x="0" y="0" width="0" height="0" colorInterpolationFilters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.007 0.011" numOctaves="2" seed="11" result="noise" /><feGaussianBlur in="noise" stdDeviation="2" result="map" /><feDisplacementMap in="SourceGraphic" in2="map" scale={settings.refraction} xChannelSelector="R" yChannelSelector="G" /></filter></defs></svg>
      <GlyphCanvas species={species} settings={settings} count={count.current} />

      <nav className="species-bar" aria-label="Animal species">
        <div className="choices glass" role="radiogroup" aria-label="Animal">
          <span className="species-thumb" style={{ transform: `translate(${thumb.left}px, ${thumb.top}px)`, width: thumb.width, height: thumb.height }} aria-hidden="true" />
          {SPECIES.map((item, index) => (
            <button
              key={item.key}
              ref={(node) => { buttons.current[index] = node; }}
              type="button"
              role="radio"
              aria-checked={species === item.key}
              tabIndex={species === item.key ? 0 : -1}
              className="species-pill"
              onClick={() => selectSpecies(item.key)}
              onKeyDown={(event) => onSpeciesKeyDown(event, index)}
            >
              <span className="species-dot" style={{ background: `radial-gradient(circle at 35% 30%, ${item.color.replace("rgb", "rgba").replace(")", ", .55)")}, ${item.color} 70%)` }} aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="glyph-stage">
        <div className="hero-copy">
          <p className="hero-eyebrow">LINK2REEL / CINEMATIC STORY STUDIO</p>
          <h1>Your story. <span>Cut like a film.</span></h1>
          <p>Links, ideas, PDFs, and images become cinematic vertical reels with narration, motion, and a finished press kit.</p>
        </div>
        <form className="composer glass" onSubmit={submit} noValidate>
          <div className="composer-input">
            <textarea
              ref={textarea}
              id="story-source"
              aria-label="Story, link, or description"
              value={text}
              onChange={(event) => { setText(event.target.value); setError(""); }}
              placeholder="Paste a link, describe your film, or write about anything…"
              required
              maxLength={30000}
            />
          </div>
          <p className="source-guidance">Start with a URL, topic, or rough idea. Add source files for richer evidence.</p>

          <div className="source-upload">
            <input id="source-files" type="file" multiple accept=".pdf,.txt,.png,.jpg,.jpeg,.webp" onChange={(event) => addFiles(event.target.files)} className="sr-only" />
            <label htmlFor="source-files" className="upload-button">Add source files</label>
            <span className="upload-types">PDF, TXT, PNG, JPG, WebP · 8 files max</span>
          </div>
          {files.length > 0 && <ul className="upload-list" aria-label="Selected source files">
            {files.map((file, index) => <li key={`${file.name}-${file.size}-${index}`}><span>{file.name}</span><button type="button" aria-label={`Remove ${file.name}`} onClick={() => setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button></li>)}
          </ul>}
          <p className="provider-notice">Uploads are sent to your configured AI providers for analysis.</p>

          <div className="composer-selects">
            <label htmlFor="video-style">Cinematic style
              <select id="video-style" value={settings.style} onChange={(event) => onChange("style", event.target.value)}>
                <option value="launch">Cinematic launch</option>
                <option value="tech_launch">Tech premiere</option>
                <option value="deep_dive">Editorial documentary</option>
                <option value="roast">Satirical cut</option>
                <option value="founder">Founder story</option>
              </select>
            </label>
            <label htmlFor="voice">Narration voice
              <select id="voice" value={settings.voice} onChange={(event) => onChange("voice", event.target.value)}>
                <option value="Charon">Charon · measured</option>
                <option value="Fenrir">Fenrir · cinematic</option>
                <option value="Puck">Puck · energetic</option>
                <option value="Aoede">Aoede · warm</option>
              </select>
            </label>
            <label htmlFor="quality-mode">Review mode
              <select id="quality-mode" value={qualityMode} onChange={(event) => setQualityMode(event.target.value as "strict" | "draft")}>
                <option value="strict">Strict · director approved</option>
                <option value="draft">Draft · preview with review notes</option>
              </select>
            </label>
          </div>

          <div className="composer-actions">
            <button type="submit" className="send-button" disabled={!hasSource || pending !== null}>{pending === "url" ? "Building your film…" : "Create my film"}</button>
          </div>
          {pending && <p className="composer-status" role="status">{pending === "sample" ? "Loading the portfolio reel…" : "Starting the studio…"}</p>}
          {error && <ErrorNote>{error}</ErrorNote>}
        </form>
        <section className="demo-premiere" aria-label="Portfolio demo">
          <div><span>FEATURED REEL</span><p>See how a CV and portfolio become a cinematic engineering story.</p></div>
          <button type="button" onClick={sample} disabled={pending !== null}>Watch portfolio demo</button>
        </section>
      </main>

      <p className="scatter-hint">click to scatter</p>
      <GlyphTweaks settings={settings} onChange={onChange} species={species} />
    </div>
  );
}
