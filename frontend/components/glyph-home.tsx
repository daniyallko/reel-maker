"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createStudioProject, createStudioSample } from "@/lib/api";
import { DEFAULT_SETTINGS, SPECIES, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";
import { GlyphCanvas } from "./glyph-canvas";
import { GlyphTweaks } from "./glyph-tweaks";
import { ErrorNote } from "./ui";

const SAMPLE_URLS = [
  ["AI startup", "https://example.com"],
  ["GitHub repo", "https://github.com/google/genai"],
  ["Product launch", "https://www.producthunt.com"],
  ["Wikipedia deep-dive", "https://en.wikipedia.org/wiki/Artificial_intelligence"],
] as const;

function greetingForHour(hour: number) {
  if (hour >= 5 && hour < 12) return "Good morning, Rosalie";
  if (hour >= 12 && hour < 17) return "Good afternoon, Rosalie";
  if (hour >= 17 && hour < 22) return "Good evening, Rosalie";
  return "Still up, Rosalie?";
}

export function GlyphHome() {
  const router = useRouter();
  const [species, setSpecies] = useState<SpeciesKey>("moth");
  const [settings, setSettings] = useState<GlyphSettings>(DEFAULT_SETTINGS);
  const [text, setText] = useState("");
  const [pending, setPending] = useState<"url" | "sample" | null>(null);
  const [error, setError] = useState("");
  const [greeting, setGreeting] = useState("Good day, Rosalie");
  const [thumb, setThumb] = useState({ left: 0, top: 0, width: 0, height: 32 });
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const textarea = useRef<HTMLInputElement>(null);
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
    const tick = () => setGreeting(greetingForHour(new Date().getHours()));
    tick();
    const timer = window.setInterval(tick, 60000);
    return () => window.clearInterval(timer);
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

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || pending) return;
    try {
      const parsed = new URL(text.trim());
      if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Unsupported protocol");
    } catch {
      setError("Enter a public http or https URL");
      return;
    }
    setPending("url");
    setError("");
    try {
      const project = await createStudioProject({ url: text.trim(), style: settings.style, voice: settings.voice });
      window.dispatchEvent(new CustomEvent("chat:submit", { detail: text.trim() }));
      setText("");
      router.push(`/project/${project.id}`);
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
      router.push(`/project/${project.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The sample could not be loaded");
      setPending(null);
    }
  }

  const isValidUrl = (() => {
    try {
      const parsed = new URL(text.trim());
      return ["http:", "https:"].includes(parsed.protocol);
    } catch {
      return false;
    }
  })();

  return (
    <div className="glyph-home" style={{ "--blur": `${settings.blur}px`, "--tint": settings.tint, "--edge": settings.edge, "--radius": `${settings.radius}px`, "--composer-width": `${settings.width}px` } as React.CSSProperties}>
      <svg className="liquid-filter" width="0" height="0" aria-hidden="true"><defs><filter id="liquid-glass" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB"><feTurbulence type="fractalNoise" baseFrequency="0.007 0.011" numOctaves="2" seed="11" result="noise" /><feGaussianBlur in="noise" stdDeviation="2" result="map" /><feDisplacementMap in="SourceGraphic" in2="map" scale={settings.refraction} xChannelSelector="R" yChannelSelector="G" /></filter></defs></svg>
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
        <div className="masthead">
          <div className="avatar" aria-hidden="true" />
          <h1>{greeting}</h1>
        </div>
        <form className="composer glass" onSubmit={submit} noValidate>
          <div className="composer-input">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" strokeWidth="2" /><path d="M15.5 15.5L20.5 20.5" stroke="currentColor" strokeWidth="2" /></svg>
            <div className="composer-url-field">
              <label htmlFor="source-url">Source URL</label>
              <input
                ref={textarea}
                id="source-url"
                type="url"
                value={text}
                onChange={(event) => {
                  const value = event.target.value;
                  setText(value);
                  try {
                    const parsed = new URL(value);
                    if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Unsupported protocol");
                    setError("");
                  } catch {
                    setError(value.trim() ? "Enter a public http or https URL" : "");
                  }
                }}
                placeholder="Paste a public URL..."
                aria-describedby="url-hint"
                required
                maxLength={2000}
              />
              <p id="url-hint" className={isValidUrl ? "url-hint valid" : "url-hint"}>{isValidUrl ? "Public URL detected. Every control is ready." : "Enter a public http or https URL."}</p>
            </div>
          </div>
          <div className="source-pills" aria-label="Sample URLs">
            {SAMPLE_URLS.map(([label, url]) => <button key={label} type="button" onClick={() => setText(url)}>{label}</button>)}
          </div>
          <div className="composer-selects">
            <label htmlFor="video-style">Video style
              <select id="video-style" value={settings.style} onChange={(event) => onChange("style", event.target.value)}>
                <option value="launch">High-Energy Tech Launch</option>
                <option value="deep_dive">Vox-Style Deep Dive</option>
                <option value="roast">Honest Product Roast</option>
                <option value="founder">60s Founder Story</option>
              </select>
            </label>
            <label htmlFor="voice">Studio voice
              <select id="voice" value={settings.voice} onChange={(event) => onChange("voice", event.target.value)}>
                <option value="Charon">Charon</option>
                <option value="Fenrir">Fenrir</option>
                <option value="Puck">Puck</option>
                <option value="Aoede">Aoede</option>
              </select>
            </label>
          </div>
          <div className="composer-row">
            <button type="button" className="add-button" onClick={sample} disabled={pending !== null}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" /></svg>
              <span>Load Sample Link (Instant Demo)</span>
            </button>
            <div className="composer-actions">
              <button type="submit" className="send-button" disabled={!isValidUrl || pending !== null} aria-label="Make my reel"><svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden="true"><path d="M8.5 13.5v-10M4 8l4.5-4.5L13 8" stroke="currentColor" strokeWidth="1.6" /></svg></button>
            </div>
          </div>
          {pending && <p className="composer-status" role="status">{pending === "sample" ? "Loading the sample reel…" : "Harvesting your URL…"}</p>}
          {error && <ErrorNote>{error}</ErrorNote>}
        </form>
      </main>

      <p className="scatter-hint">click to scatter</p>
      <GlyphTweaks settings={settings} onChange={onChange} species={species} />
    </div>
  );
}
