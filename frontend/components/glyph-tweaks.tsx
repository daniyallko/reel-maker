"use client";

import { useState } from "react";
import { DEFAULT_SETTINGS, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";

interface SliderProps {
  label: string;
  setting: keyof GlyphSettings;
  min: number;
  max: number;
  step: number;
  settings: GlyphSettings;
  onChange: (key: keyof GlyphSettings, value: number | boolean | string) => void;
}

function Slider({ label, setting, min, max, step, settings, onChange }: SliderProps) {
  const value = settings[setting] as number;
  const decimals = step < 0.1 ? 2 : step < 1 ? 1 : 0;
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <label className="tweak-row" title="Double-click the name to reset it.">
      <span className="tweak-label" onDoubleClick={() => onChange(setting, DEFAULT_SETTINGS[setting])}>{label}</span>
      <span className="tweak-value">{value.toFixed(decimals)}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(setting, Number(event.target.value))}
        style={{ "--fill": `${fill}%` } as React.CSSProperties}
        aria-label={label}
      />
    </label>
  );
}

function Toggle({ label, setting, settings, onChange }: Omit<SliderProps, "min" | "max" | "step">) {
  return (
    <label className="tweak-toggle">
      <span>{label}</span>
      <input type="checkbox" checked={Boolean(settings[setting])} onChange={(event) => onChange(setting, event.target.checked)} />
      <span className="switch" aria-hidden="true" />
    </label>
  );
}

const groups: Array<{ title: string; sliders: Array<[string, number, number, number]> }> = [
  { title: "Movement", sliders: [["density", 0.1, 4, 0.1], ["direction", 0, 360, 1], ["speed", 0.1, 3, 0.1], ["sway", 0, 0.6, 0.01], ["spread", 0, 0.8, 0.01], ["size", 0.3, 2.5, 0.1], ["separation", 0, 1000, 10]] },
  { title: "Look", sliders: [["hue", -180, 180, 1], ["shimmer", 0, 1, 0.01], ["sparkle", 0, 1, 0.01], ["fog", 0, 1, 0.01], ["trail", 0, 4, 0.1], ["trailFade", 0.05, 6, 0.05], ["grid", 0, 4, 0.05], ["detail", 0.5, 2, 0.1]] },
  { title: "Chat glass", sliders: [["blur", 0, 30, 0.5], ["refraction", 0, 150, 1], ["tint", 0, 3, 0.05], ["edge", 0, 2, 0.05], ["radius", 0, 48, 1], ["width", 320, 960, 10]] },
];

export function GlyphTweaks({ settings, onChange, species }: { settings: GlyphSettings; onChange: (key: keyof GlyphSettings, value: number | boolean | string) => void; species: SpeciesKey }) {
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem("wild-tab:tweaks-open") === "true"; } catch { return false; }
  });
  const [copied, setCopied] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const speciesGroups: Record<SpeciesKey, Array<[string, number, number, number]>> = {
    moth: [["flapRate", 0.2, 3, 0.1], ["glide", 0, 5, 0.1]],
    rabbit: [["burst", 0.1, 4, 0.1], ["pause", 0, 4, 0.1], ["hopSpeed", 0.1, 3, 0.1], ["scare", 0, 2, 0.1]],
    turtle: [["meander", 0, 1, 0.05], ["flipperBeat", 0.2, 3, 0.1]],
    squid: [["pulseRate", 0.2, 3, 0.1], ["pulsePower", 0.1, 3, 0.1], ["pulseGlow", 0, 3, 0.1], ["armLength", 0.3, 2, 0.1]],
    owl: [["hover", 0.1, 4, 0.1], ["cruising", 0, 1, 0.05], ["swoopSpeed", 0.2, 3, 0.1], ["wingbeat", 0.2, 3, 0.1]],
    flyingfish: [["howOften", 0.2, 4, 0.1], ["leapLength", 0.1, 2, 0.1], ["leapHeight", 0, 3, 0.1]],
    eagle: [["wingbeat", 0.2, 3, 0.1], ["glide", 0, 5, 0.1]],
  };

  function toggleOpen(next: boolean) {
    setOpen(next);
    try { localStorage.setItem("wild-tab:tweaks-open", String(next)); } catch { /* storage can be blocked */ }
  }

  async function copySettings() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(settings, null, 2));
      setCopied(true);
    } catch {
      console.log(JSON.stringify(settings, null, 2));
      setCopied(true);
    }
    window.setTimeout(() => setCopied(false), 1400);
  }

  function reset() {
    if (!confirmReset) {
      setConfirmReset(true);
      window.setTimeout(() => setConfirmReset(false), 3000);
      return;
    }
    (Object.keys(DEFAULT_SETTINGS) as Array<keyof GlyphSettings>).forEach((key) => onChange(key, DEFAULT_SETTINGS[key]));
    try { localStorage.removeItem(`wild-tab:tweaks:${species}`); } catch { /* storage can be blocked */ }
    setConfirmReset(false);
  }

  return (
    <>
      <button type="button" className="tweaks-opener glass" onClick={() => toggleOpen(!open)} aria-expanded={open} aria-controls="tweaks-panel">
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true"><path d="M2 4h11M2 11h11M5 2v4M10 9v4" stroke="currentColor" strokeWidth="1.4" /></svg>
        Tweaks
      </button>
      {open && (
        <aside id="tweaks-panel" className="tweaks-panel glass" aria-label="Tweaks panel">
          <header className="tweaks-header">
            <strong>Tweaks</strong>
            <div className="tweaks-actions">
              <button type="button" onClick={copySettings}>{copied ? "Copied" : "Copy"}</button>
              <button type="button" className={confirmReset ? "danger" : ""} onClick={reset}>{confirmReset ? "Reset all?" : "Reset"}</button>
              <button type="button" className="tweaks-close" onClick={() => toggleOpen(false)} aria-label="Close tweaks">×</button>
            </div>
          </header>
          <div className="tweaks-body">
            {groups.map((group) => (
              <section key={group.title} className="tweak-group">
                <h3>{group.title}</h3>
                {group.sliders.map(([setting, min, max, step]) => <Slider key={setting} label={setting === "trailFade" ? "Trail fade" : setting === "refraction" ? "Refraction" : setting[0].toUpperCase() + setting.slice(1)} setting={setting as keyof GlyphSettings} min={min} max={max} step={step} settings={settings} onChange={onChange} />)}
                {group.title === "Movement" && <Toggle label="Corner to corner" setting="corner" settings={settings} onChange={onChange} />}
                {group.title === "Chat glass" && (
                  <div className="tweak-selects">
                    <label>Style<select value={settings.style} onChange={(event) => onChange("style", event.target.value)}><option value="launch">Tech launch</option><option value="deep_dive">Deep dive</option><option value="roast">Product roast</option><option value="founder">Founder story</option></select></label>
                    <label>Voice<select value={settings.voice} onChange={(event) => onChange("voice", event.target.value)}><option>Charon</option><option>Fenrir</option><option>Puck</option><option>Aoede</option></select></label>
                  </div>
                )}
              </section>
            ))}
            <section className="tweak-group">
              <h3>{species} controls</h3>
              {speciesGroups[species].map(([setting, min, max, step]) => <Slider key={setting} label={setting[0].toUpperCase() + setting.slice(1)} setting={setting as keyof GlyphSettings} min={min} max={max} step={step} settings={settings} onChange={onChange} />)}
            </section>
          </div>
        </aside>
      )}
    </>
  );
}
