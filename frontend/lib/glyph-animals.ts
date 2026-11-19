export type SpeciesKey = "moth" | "rabbit" | "turtle" | "squid" | "owl" | "flyingfish" | "eagle";

export interface GlyphSettings {
  density: number;
  corner: boolean;
  direction: number;
  speed: number;
  size: number;
  sway: number;
  spread: number;
  separation: number;
  hue: number;
  shimmer: number;
  sparkle: number;
  fog: number;
  trail: number;
  trailFade: number;
  grid: number;
  detail: number;
  blur: number;
  refraction: number;
  tint: number;
  edge: number;
  radius: number;
  width: number;
  style: string;
  voice: string;
  flapRate: number;
  glide: number;
  burst: number;
  pause: number;
  hopSpeed: number;
  scare: number;
  meander: number;
  flipperBeat: number;
  pulseRate: number;
  pulsePower: number;
  pulseGlow: number;
  armLength: number;
  hover: number;
  cruising: number;
  swoopSpeed: number;
  wingbeat: number;
  howOften: number;
  leapLength: number;
  leapHeight: number;
  foldingFlap: boolean;
}

export const DEFAULT_SETTINGS: GlyphSettings = {
  density: 1,
  corner: false,
  direction: 49,
  speed: 1,
  size: 1,
  sway: 0.04,
  spread: 0.06,
  separation: 300,
  hue: 0,
  shimmer: 0.3,
  sparkle: 0.12,
  fog: 0.75,
  trail: 1,
  trailFade: 1.3,
  grid: 1.05,
  detail: 1.3,
  blur: 3.5,
  refraction: 40,
  tint: 0,
  edge: 0.55,
  radius: 24,
  width: 720,
  style: "launch",
  voice: "Fenrir",
  flapRate: 1,
  glide: 2.75,
  burst: 1,
  pause: 1,
  hopSpeed: 1,
  scare: 0.6,
  meander: 0.4,
  flipperBeat: 1,
  pulseRate: 1,
  pulsePower: 1,
  pulseGlow: 1,
  armLength: 1,
  hover: 1.3,
  cruising: 0.5,
  swoopSpeed: 1.3,
  wingbeat: 1,
  howOften: 1,
  leapLength: 0.6,
  leapHeight: 1,
  foldingFlap: false,
};

export const SPECIES: Array<{ key: SpeciesKey; label: string; color: string; scale: number; direction: number; detail: number; trailColor: [number, number, number] }> = [
  { key: "moth", label: "Moth", color: "rgb(232,162,124)", scale: 1, direction: 49, detail: 1.3, trailColor: [255, 196, 156] },
  { key: "rabbit", label: "Rabbit", color: "rgb(248,199,181)", scale: 1.15, direction: 0, detail: 1.7, trailColor: [226, 190, 168] },
  { key: "turtle", label: "Sea turtle", color: "rgb(109,176,138)", scale: 1.6, direction: 49, detail: 1.3, trailColor: [110, 200, 186] },
  { key: "squid", label: "Squid", color: "rgb(232,106,160)", scale: 1.55, direction: 131, detail: 1.3, trailColor: [255, 140, 196] },
  { key: "owl", label: "Owl", color: "rgb(217,195,160)", scale: 2.1, direction: 49, detail: 1.3, trailColor: [236, 212, 170] },
  { key: "flyingfish", label: "Flying fish", color: "rgb(133,227,221)", scale: 1.25, direction: 131, detail: 1.3, trailColor: [120, 214, 226] },
  { key: "eagle", label: "Eagle", color: "rgb(230,233,242)", scale: 1.5, direction: 49, detail: 1.7, trailColor: [200, 204, 226] },
];

export const speciesByKey = Object.fromEntries(SPECIES.map((species) => [species.key, species]));

type RGB = [number, number, number];
type PartKind = "plain" | "shine" | "dark" | "light" | "fur" | "soft" | "bright" | "line";
interface Part { kind: PartKind; color: RGB; glyph?: string }
interface Animal {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  depth: number;
  roll: number;
  span: number;
  phase: number;
  leapHeight: number;
  seed: number;
  panic: number;
  timer: number;
  mode: number;
}
interface Pellet { x: number; y: number; vx: number; vy: number; life: number }
interface Simulation {
  width: number;
  height: number;
  species: SpeciesKey;
  settings: GlyphSettings;
  animals: Animal[];
  pellets: Pellet[];
  trails: Map<number, number>;
  time: number;
  cw: number;
  ch: number;
  font: string;
  background: HTMLCanvasElement | null;
}

const random = (seed: number) => {
  let value = seed | 0;
  value = (value * 1664525 + 1013904223) | 0;
  return (value >>> 0) / 4294967296;
};
const hash = (x: number, y: number, seed = 1) => random(Math.round(x * 73856093 ^ y * 19349663 ^ seed * 83492791));
const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeIn = (t: number) => t * t * t;

function ellipse(u: number, v: number, cx: number, cy: number, rx: number, ry: number, angle = 0): number {
  const dx = u - cx, dy = v - cy;
  const cos = Math.cos(angle), sin = Math.sin(angle);
  const x = dx * cos + dy * sin, y = -dx * sin + dy * cos;
  return Math.sqrt((x * x) / (rx * rx) + (y * y) / (ry * ry));
}
function segment(u: number, v: number, x1: number, y1: number, x2: number, y2: number, width: number): boolean {
  const dx = x2 - x1, dy = y2 - y1;
  const length = Math.hypot(dx, dy) || 1;
  const t = clamp(((u - x1) * dx + (v - y1) * dy) / (length * length), 0, 1);
  return Math.hypot(u - (x1 + dx * t), v - (y1 + dy * t)) <= width;
}
function lobe(u: number, v: number, cx: number, cy: number, reach: number, roundness: number, angle = 0): number {
  return ellipse(u, v, cx, cy, reach / 2, reach * roundness, angle);
}
function bodyColor(kind: PartKind, color: RGB, part: Part): Part {
  return { kind, color: [...color] as RGB, glyph: part.glyph };
}
const dark = (color: RGB, glyph = "#%@"): Part => ({ kind: "dark", color, glyph });
const light = (color: RGB, glyph = "o*"): Part => ({ kind: "light", color, glyph });
const fur = (color: RGB, glyph = "8#@"): Part => ({ kind: "fur", color, glyph });
const shine = (color: RGB, glyph?: string): Part => ({ kind: "shine", color, glyph });
const soft = (color: RGB, glyph?: string): Part => ({ kind: "soft", color, glyph });
const bright = (color: RGB, glyph = ".:*"): Part => ({ kind: "bright", color, glyph });
const plain = (color: RGB, glyph?: string): Part => ({ kind: "plain", color, glyph });
const line = (color: RGB, glyph = ".:+*"): Part => ({ kind: "line", color, glyph });
const eye = (color: RGB = [12, 12, 16]): Part => ({ kind: "dark", color, glyph: "●" });

function sampleSpecies(species: SpeciesKey, u: number, v: number, animal: Animal, time: number): Part | null {
  const phase = animal.phase;
  const alarm = animal.panic > 0 ? 1 : 0;
  if (species === "moth") {
    const opening = 0.1 + 0.9 * ((0.5 + 0.5 * Math.cos(phase)) ** 0.8) * (1 - 0.35 * (animal.mode > 0 ? 1 : 0));
    if (ellipse(u, v, 0.15, 0, 0.04, 0.04) < 1) return fur([112, 70, 50], "%#8");
    if (ellipse(u, v, -0.05, 0, 0.15, 0.05) < 1) return fur([112, 70, 50], "%#8");
    if (ellipse(u, v, -0.25, 0, 0.12, 0.025) < 1) return fur([70 + (Math.floor((u + 0.4) * 22) % 2) * 80, 42 + (Math.floor((u + 0.4) * 22) % 2) * 56, 32 + (Math.floor((u + 0.4) * 22) % 2) * 40], "%#8");
    for (const side of [-1, 1]) {
      const fore = lobe(u, v, 0.05, side * (0.05 + 0.32 * opening), 0.64, 0.3, side * -0.35);
      if (fore < 1) {
        if (fore > 0.86) return dark([84, 46, 32], "@");
        if (fore > 0.48 && fore < 0.58) return dark([150, 88, 60], "#");
        return shine([200 + 48 * fore, 132 + 46 * fore, 96 + 40 * fore]);
      }
      const hind = lobe(u, v, -0.05, side * (0.05 + 0.24 * opening), 0.38, 0.55, side * 0.45);
      if (hind < 1) return fore > 0.8 ? dark([84, 46, 32], "@") : shine([200 + 48 * hind, 132 + 46 * hind, 96 + 40 * hind]);
      if (ellipse(u, v, -0.04, side * 0.24, 0.075, 0.06) < 1) return dark([50, 32, 28], "@");
    }
    if (segment(u, v, 0.17, -0.014, 0.36, -0.13, 0.009) || segment(u, v, 0.17, 0.014, 0.36, 0.13, 0.009)) return line([214, 170, 130]);
    return null;
  }
  if (species === "rabbit") {
    const air = Math.max(0, Math.sin(phase));
    if (ellipse(u, v, 0.13, -0.12 - 0.08 * air, 0.034, 0.24, 0.35 + 0.35 * air + 0.25 * alarm) < 1) return light([244, 150, 156], "|");
    if (ellipse(u, v, 0.105, -0.11 - 0.06 * air, 0.034, 0.24, 0.35 + 0.35 * air + 0.25 * alarm) < 1) return light([208, 122, 130], "|");
    if (ellipse(u, v, 0.17, -0.07, 0.09, 0.072) < 1) return fur([248, 199, 181], "%8");
    if (ellipse(u, v, -0.28, -0.01, 0.048, 0.048) < 1) return light([255, 250, 246], "*@");
    if (ellipse(u, v, -0.05, 0.02, 0.2, 0.125) < 1) return v > 0.08 ? fur([206, 150, 132], "%8") : fur([248, 199, 181], "%8");
    if (ellipse(u, v, -0.15, 0.05, 0.12, 0.12) < 1) return fur([248, 199, 181], "%8");
    if (ellipse(u, v, 0.2, -0.09, 0.018, 0.018) < 1) return eye();
    if (ellipse(u, v, 0.24, -0.055, 0.022, 0.015) < 1) return light([244, 150, 156], "o");
    if (segment(u, v, -0.2, 0.13, -0.32 - 0.05 * air, 0.13, 0.022) || segment(u, v, 0.08, 0.08, 0.18 + 0.08 * air, 0.1, 0.018)) return line([248, 199, 181]);
    return null;
  }
  if (species === "turtle") {
    const shell = ellipse(u, v, -0.02, 0, 0.28, 0.22);
    if (shell < 1) {
      if (shell > 0.83) return dark([74, 132, 100], "=");
      if (Math.abs(v) > 0.07 && Math.abs(v) < 0.09) return dark([40, 84, 62], "|");
      if (Math.abs((u + 0.02) % 0.14) < 0.018) return dark([40, 84, 62], "-");
      return shine([109 + 24 * (1 - shell), 176 + 32 * (1 - shell), 138 + 24 * (1 - shell)]);
    }
    if (ellipse(u, v, 0.33, 0, 0.085, 0.07) < 1 || segment(u, v, 0.22, 0, 0.3, 0, 0.045)) return shine([142, 200, 164]);
    const beat = Math.sin(phase) * 0.6;
    for (const side of [-1, 1]) {
      if (segment(u, v, 0.12, side * 0.17, 0.12 + 0.24 * Math.cos(1.25 - beat), side * (0.17 + 0.24 * Math.sin(1.25 - beat)), 0.045)) return shine([142, 200, 164]);
      if (segment(u, v, -0.2, side * 0.13, -0.2 + 0.11 * Math.cos(2.5 + 0.28 * Math.sin(phase + 1.4)), side * (0.13 + 0.11 * Math.sin(2.5 + 0.28 * Math.sin(phase + 1.4))), 0.032)) return shine([142, 200, 164]);
      if (ellipse(u, v, 0.37, side * 0.045, 0.018, 0.018) < 1) return eye();
    }
    if (segment(u, v, -0.29, 0, -0.36, 0, 0.025)) return line([142, 200, 164]);
    return null;
  }
  if (species === "squid") {
    const cycle = (time * 0.6 + animal.seed) % 1;
    const squeeze = cycle < 0.22 ? easeOut(cycle / 0.22) : 1 - easeIn((cycle - 0.22) / 0.78);
    const width = 0.1 * (1 - 0.16 * squeeze);
    if (ellipse(u, v, 0.25, 0, 0.28, width) < 1) {
      if (Math.abs(v) > width * 0.82) return bright([255, 200, 226], ":;");
      if (Math.abs(v) < 0.015) return bright([255, 200, 226], "|");
      return shine([232 + 30 * (1 - Math.abs(v)), 106 + 24 * (1 - Math.abs(v)), 160 + 30 * (1 - Math.abs(v))]);
    }
    if (ellipse(u, v, -0.06, 0, 0.09, 0.08) < 1) return shine([232, 106, 160]);
    for (const side of [-1, 1]) {
      if (ellipse(u, v, 0.42, side * 0.09, 0.11, 0.07) < 1) return soft([232, 106, 160], ".:");
      if (ellipse(u, v, -0.055, side * 0.06, 0.018, 0.018) < 1) return eye();
    }
    for (let index = 0; index < 8; index++) {
      const angle = (index - 3.5) * 0.2 + 0.035 * Math.sin(phase - 3.5 + index);
      const length = 0.42 * (1 + 0.15 * Math.sin(index * 2));
      if (segment(u, v, -0.08, 0, -0.08 - length * Math.cos(angle), length * Math.sin(angle) * 0.65, 0.014)) return line([232, 104, 168]);
    }
    for (const side of [-1, 1]) {
      if (segment(u, v, -0.08, side * 0.04, -0.72, side * 0.12, 0.014)) return line([255, 160, 204], "o");
      if (ellipse(u, v, -0.72, side * 0.12, 0.07, 0.045) < 1) return bright([255, 160, 204], "o@o");
    }
    if (ellipse(u, v, 0.2, 0, 0.4 + 0.05 * squeeze, 0.2 + 0.03 * squeeze) > 0.85 && ellipse(u, v, 0.2, 0, 0.4 + 0.05 * squeeze, 0.2 + 0.03 * squeeze) < 1.15) return bright([255, 200, 226], ".");
    return null;
  }
  if (species === "owl") {
    if (ellipse(u, v, 0.13, 0, 0.1, 0.1) < 1) return v > 0.02 && Math.abs(v) < 0.025 ? dark([128, 100, 70], "v") : light([244, 232, 206], "o");
    if (ellipse(u, v, -0.06, 0, 0.16, 0.085) < 1) return fur([217, 195, 160], "%8");
    const wingPhase = (0.5 + 0.5 * Math.cos(phase)) ** 0.8;
    const opening = Math.max(0.3, (0.55 + 0.45 * wingPhase) * (1 - 0.5 * (animal.mode > 0 ? 1 : 0)));
    for (const side of [-1, 1]) {
      const wing = lobe(u, v, -0.02, side * (0.06 + 0.5 * opening), 0.56, 0.28, side * 0.2);
      if (wing < 1) return wing > 0.72 ? dark([150, 118, 82], "#") : plain([217 + 20 * (1 - wing), 195 + 18 * (1 - wing), 160 + 16 * (1 - wing)]);
      if (segment(u, v, -0.18, side * 0.06, -0.34, side * 0.1, 0.025)) return dark([150, 118, 82], "v");
      if (ellipse(u, v, 0.135, side * 0.045, 0.026, 0.026) < 1) return eye([250, 186, 58]);
      if (segment(u, v, 0.19, side * 0.06, 0.26, side * 0.09, 0.018)) return dark([128, 100, 70], "^");
    }
    return null;
  }
  if (species === "flyingfish") {
    const arc = Math.max(0, Math.sin(Math.PI * ((time * 0.6 + animal.seed) % 1))) * animal.leapHeight;
    if (ellipse(u, v, 0, 0, 0.32, 0.082) < 1) return v < 0 ? dark([62, 150, 150], "=:") : v > 0.04 ? light([224, 250, 246], "o.") : shine([133, 227, 221]);
    for (const side of [-1, 1]) {
      const opening = 0.42 + 0.58 * arc;
      if (lobe(u, v, 0.12, side * 0.17, 0.46 * opening, 0.24, side * -0.4) < 1) return soft([160, 238, 232], ".:");
      if (lobe(u, v, -0.1, side * 0.11, 0.2, 0.22, side * -0.35) < 1) return soft([160, 238, 232], ".:");
      if (ellipse(u, v, 0.24, side * 0.032, 0.018, 0.018) < 1) return eye();
    }
    if (segment(u, v, -0.28, 0, -0.46, -0.1, 0.025) || segment(u, v, -0.28, 0, -0.46, 0.1, 0.025)) return line([92, 190, 186], "\\/");
    return null;
  }
  if (species === "eagle") {
    const flap = (0.5 + 0.5 * Math.cos(phase)) ** 0.8;
    for (const side of [-1, 1]) {
      const wing = lobe(u, v, 0.02, side * (0.05 + 0.25 * flap), 0.54, 0.24, side * 0.18);
      if (wing < 1) return wing > 0.72 ? dark([112, 120, 144], "=#") : light([236, 238, 246], "o.");
      if (segment(u, v, -0.14, 0, -0.38, side * 0.12, 0.028)) return light([252, 252, 255], "v");
      if (ellipse(u, v, 0.225, side * 0.026, 0.018, 0.018) < 1) return eye([240, 190, 70]);
    }
    if (ellipse(u, v, -0.02, 0, 0.17, 0.062) < 1) return light([252, 252, 255], "v");
    if (ellipse(u, v, 0.215, 0, 0.075, 0.048) < 1) return light([252, 252, 255], "o.");
    if (segment(u, v, 0.26, 0, 0.31, 0.015, 0.025) || segment(u, v, 0.26, 0, 0.31, -0.015, 0.025)) return bright([240, 190, 70], "@");
    if (segment(u, v, -0.24, -0.04, -0.3, -0.08, 0.015) || segment(u, v, -0.24, 0.04, -0.3, 0.08, 0.015)) return line([240, 190, 70], "|");
    return null;
  }
  return null;
}

function createAnimal(id: number, width: number, height: number, species: SpeciesKey, settings: GlyphSettings): Animal {
  const spec = speciesByKey[species];
  const roll = Math.random();
  const depth = 0.18 + 0.82 * Math.pow(roll, 1.6);
  const base = clamp(Math.min(width, height) * 0.2, 80, 190) * spec.scale * settings.size;
  const direction = (settings.corner ? -45 : settings.direction) * Math.PI / 180;
  const cruise = 82 * (0.55 + 0.45 * depth) * settings.speed;
  return { id, x: Math.random() * width, y: Math.random() * height, vx: Math.cos(direction) * cruise, vy: Math.sin(direction) * cruise, depth, roll, span: base * depth, phase: Math.random() * Math.PI * 2, leapHeight: settings.leapHeight, seed: Math.random() * 10000, panic: 0, timer: Math.random() * 2, mode: 0 };
}

export function createSimulation(width: number, height: number, species: SpeciesKey, settings: GlyphSettings, font: string, count?: number): Simulation {
  const spec = speciesByKey[species];
  const base = clamp(Math.min(width, height) * 0.2, 80, 190) * spec.scale * settings.size;
  const target = count ?? clamp(Math.round(width * height / (48000 * Math.pow(base / 160, 2)) * settings.density), 1, 30);
  const simulation: Simulation = { width, height, species, settings, animals: [], pellets: [], trails: new Map(), time: 0, cw: 9, ch: 13, font, background: null };
  for (let index = 0; index < target; index++) simulation.animals.push(createAnimal(index, width, height, species, settings));
  resizeSimulation(simulation, width, height);
  return simulation;
}

export function resizeSimulation(simulation: Simulation, width: number, height: number) {
  simulation.width = Math.max(1, Math.round(width));
  simulation.height = Math.max(1, Math.round(height));
  const detail = speciesByKey[simulation.species].detail;
  simulation.cw = clamp(Math.round(simulation.width / 124 / detail), 5, 24);
  simulation.ch = Math.round(simulation.cw * 1.45);
  const canvas = document.createElement("canvas");
  canvas.width = simulation.width;
  canvas.height = simulation.height;
  const gridWidth = simulation.width;
  const gridHeight = simulation.height;
  const context = canvas.getContext("2d")!;
  context.fillStyle = "#06070c";
  context.fillRect(0, 0, gridWidth, gridHeight);
  context.strokeStyle = `rgba(255,255,255,${0.055 * simulation.settings.grid})`;
  context.lineWidth = 1;
  for (let x = 0; x < gridWidth; x += simulation.cw) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, gridHeight); context.stroke(); }
  for (let y = 0; y < gridHeight; y += simulation.ch) { context.beginPath(); context.moveTo(0, y); context.lineTo(gridWidth, y); context.stroke(); }
  simulation.background = canvas;
}

function hueRotate(color: RGB, degrees: number): RGB {
  const angle = degrees * Math.PI / 180;
  const cos = Math.cos(angle), sin = Math.sin(angle);
  const [r, g, b] = color.map((value) => value / 255);
  const matrix = [
    cos + (1 - cos) / 3, (1 - cos) / 3 - sin / Math.sqrt(3), (1 - cos) / 3 + sin / Math.sqrt(3),
    (1 - cos) / 3 + sin / Math.sqrt(3), cos + (1 - cos) / 3, (1 - cos) / 3 - sin / Math.sqrt(3),
    (1 - cos) / 3 - sin / Math.sqrt(3), (1 - cos) / 3 + sin / Math.sqrt(3), cos + (1 - cos) / 3,
  ];
  return [
    clamp((r * matrix[0] + g * matrix[1] + b * matrix[2]) * 255, 0, 255),
    clamp((r * matrix[3] + g * matrix[4] + b * matrix[5]) * 255, 0, 255),
    clamp((r * matrix[6] + g * matrix[7] + b * matrix[8]) * 255, 0, 255),
  ];
}

function colorForPart(part: Part, animal: Animal, simulation: Simulation, u: number, v: number, coverage: number): string {
  const fog = (1 - animal.depth) * simulation.settings.fog;
  let color = part.color;
  if (part.kind === "shine") {
    const shimmer = 1 - 0.4 * simulation.settings.shimmer + simulation.settings.shimmer * Math.sin(2.2 * simulation.time + 9 * u + 6 * v + animal.seed);
    color = color.map((channel) => channel * shimmer) as RGB;
  }
  color = color.map((channel) => channel + (255 - channel) * fog) as RGB;
  color = hueRotate(color, simulation.settings.hue);
  const twinkle = hash(u * 1000, v * 1000, Math.floor(simulation.time * 6));
  if (twinkle < simulation.settings.sparkle * (part.kind === "shine" ? 1 : 0.33)) return "#ffffff";
  const [r, g, b] = color.map(Math.round);
  return `rgb(${r},${g},${b})`;
}

function drawAnimal(context: CanvasRenderingContext2D, animal: Animal, simulation: Simulation) {
  const spec = speciesByKey[simulation.species];
  const extent = simulation.species === "moth" ? 0.78 : 0.68;
  const span = animal.span;
  const cw = simulation.cw, ch = simulation.ch;
  const direction = Math.atan2(animal.vy, animal.vx);
  const cos = Math.cos(direction), sin = Math.sin(direction);
  for (let x = Math.floor((animal.x - extent * span) / cw); x <= Math.ceil((animal.x + extent * span) / cw); x++) {
    for (let y = Math.floor((animal.y - extent * span) / ch); y <= Math.ceil((animal.y + extent * span) / ch); y++) {
      if (x < 0 || y < 0 || x * cw > simulation.width || y * ch > simulation.height) continue;
      const points = [[0.25, 0.3], [0.75, 0.3], [0.25, 0.72], [0.75, 0.72]];
      const centerX = x * cw + cw / 2, centerY = y * ch + ch / 2;
      const centerU = ((centerX - animal.x) * cos + (centerY - animal.y) * sin) / span;
      const centerV = (-(centerX - animal.x) * sin + (centerY - animal.y) * cos) / span;
      const center = sampleSpecies(simulation.species, centerU, centerV, animal, simulation.time);
      let hits = 0;
      let part = center;
      for (const [px, py] of points) {
        const u = ((x * cw + px * cw - animal.x) * cos + (y * ch + py * ch - animal.y) * sin) / span;
        const v = (-(x * cw + px * cw - animal.x) * sin + (y * ch + py * ch - animal.y) * cos) / span;
        const sampled = sampleSpecies(simulation.species, u, v, animal, simulation.time);
        if (sampled) { hits++; if (!part) part = sampled; }
      }
      const coverage = hits / points.length;
      if (!part) continue;
      const color = colorForPart(part, animal, simulation, centerU, centerV, coverage);
      if (center && coverage >= 0.6) {
        context.fillStyle = color;
        context.fillRect(x * cw + 1, y * ch + 1, cw - 1, ch - 1);
      }
      const glyphs = part.glyph || ".:;+=*%#";
      const glyphIndex = Math.floor(hash(x * 13 + y * 17, animal.seed) * glyphs.length);
      const glyph = part.kind === "line" ? glyphs[glyphIndex % glyphs.length] : glyphs[glyphIndex % glyphs.length];
      context.fillStyle = part.kind === "dark" ? `rgba(255,255,255,${0.65 + 0.35 * animal.depth})` : `rgba(6,7,12,${0.72 - 0.25 * animal.depth})`;
      context.font = `600 ${Math.round(ch * 0.74)}px ${simulation.font}`;
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText(glyph, centerX, centerY + 1);
    }
  }
  if (simulation.species === "squid") {
    context.fillStyle = "rgba(255,176,214,.25)";
    for (let index = 0; index < Math.ceil(simulation.width * simulation.height / 6000); index++) {
      const x = hash(index, 2) * simulation.width;
      const y = (hash(index, 4) * simulation.height + simulation.time * (3 + hash(index, 7) * 9)) % simulation.height;
      context.fillText(index % 12 === 0 ? "*" : ".", x, y);
    }
  }
}

function drawTrails(context: CanvasRenderingContext2D, simulation: Simulation) {
  const [r, g, b] = speciesByKey[simulation.species].trailColor;
  for (const [key, energy] of simulation.trails) {
    if (energy < 0.03) continue;
    const x = key % Math.ceil(simulation.width / simulation.cw);
    const y = Math.floor(key / Math.ceil(simulation.width / simulation.cw));
    const size = Math.max(2, Math.round(0.19 * simulation.cw * (energy > 0.6 ? 1.5 : 1)));
    const twinkle = 0.75 + 0.25 * Math.sin(5 * simulation.time + key * 0.7);
    context.fillStyle = `rgba(${r},${g},${b},${Math.min(0.85, energy * 0.85) * twinkle})`;
    context.fillRect(x * simulation.cw + simulation.cw / 2 - size / 2, y * simulation.ch + simulation.ch * 0.6 - size / 2, size, size);
  }
}

export function stepSimulation(simulation: Simulation, dt: number) {
  simulation.time += dt;
  const direction = (simulation.settings.corner ? -45 : simulation.settings.direction) * Math.PI / 180;
  for (const animal of simulation.animals) {
    const cruise = 82 * (0.55 + 0.45 * animal.depth) * simulation.settings.speed;
    const sway = simulation.settings.sway * (Math.sin(0.13 * simulation.time) + 0.5 * Math.sin(0.31 * simulation.time + 1.7));
    const aim = direction + sway + (animal.roll - 0.5) * simulation.settings.spread;
    animal.vx += (Math.cos(aim) * cruise - animal.vx) * dt * 2;
    animal.vy += (Math.sin(aim) * cruise - animal.vy) * dt * 2;
    if (simulation.species === "squid") {
      const cycle = (simulation.time * 0.6 + animal.seed) % 1;
      const jet = cycle < 0.22 ? 6.2 * simulation.settings.pulsePower : 1;
      animal.vx += Math.cos(aim) * cruise * (jet - 1) * dt;
      animal.vy += Math.sin(aim) * cruise * (jet - 1) * dt;
    }
    if (simulation.species === "rabbit" && animal.mode === 0 && Math.random() < dt * 0.6) animal.mode = 1;
    if (simulation.species === "rabbit" && animal.mode === 1) { animal.vx *= 0.96; animal.vy *= 0.96; if (animal.timer <= 0) { animal.mode = 0; animal.timer = (Math.random() * 1.6 + 0.5) * simulation.settings.burst; } }
    if (simulation.species === "owl" && animal.timer <= 0) { animal.mode = animal.mode === 0 ? 1 : 0; animal.timer = (1 + Math.random() * 2) * simulation.settings.hover; }
    animal.timer -= dt;
    animal.phase += dt * (simulation.species === "moth" ? 16.3 * simulation.settings.flapRate : simulation.species === "owl" ? 21 * simulation.settings.wingbeat : simulation.species === "squid" ? 3.8 * simulation.settings.pulseRate : simulation.species === "turtle" ? 5 * simulation.settings.flipperBeat : 5);
    animal.x += animal.vx * dt;
    animal.y += animal.vy * dt;
    animal.panic = Math.max(0, animal.panic - dt);
    const span = animal.span;
    if (animal.x < -span || animal.x > simulation.width + span || animal.y < -span || animal.y > simulation.height + span) {
      animal.x = Math.random() * simulation.width;
      animal.y = Math.random() * simulation.height;
    }
  }
  for (const pellet of simulation.pellets) {
    pellet.x += pellet.vx * dt;
    pellet.y += pellet.vy * dt;
    pellet.vx *= Math.exp(-0.8 * dt);
    pellet.vy *= Math.exp(-0.8 * dt);
    pellet.life -= dt;
    for (const turtle of simulation.animals.filter((animal) => simulation.species === "turtle")) {
      if (Math.hypot(turtle.x - pellet.x, turtle.y - pellet.y) < turtle.span * 0.32 + 6) pellet.life = 0;
    }
  }
  simulation.pellets = simulation.pellets.filter((pellet) => pellet.life > 0);
  for (const [key, energy] of simulation.trails) {
    const decayed = energy * Math.exp(-dt * simulation.settings.trailFade);
    if (decayed < 0.03) simulation.trails.delete(key); else simulation.trails.set(key, decayed);
  }
}

export function drawSimulation(context: CanvasRenderingContext2D, simulation: Simulation) {
  if (simulation.background && simulation.background.width > 0 && simulation.background.height > 0) context.drawImage(simulation.background, 0, 0);
  drawTrails(context, simulation);
  const sorted = [...simulation.animals].sort((a, b) => a.roll - b.roll);
  for (const animal of sorted) drawAnimal(context, animal, simulation);
}

export function scatter(simulation: Simulation, x: number, y: number) {
  const radius = 6 * simulation.cw;
  for (let dx = -6; dx <= 6; dx++) for (let dy = -6; dy <= 6; dy++) {
    if (Math.hypot(dx, dy) <= 6) {
      const key = Math.floor((x + dx * simulation.cw) / simulation.cw) + Math.floor((y + dy * simulation.ch) / simulation.ch) * Math.ceil(simulation.width / simulation.cw);
      simulation.trails.set(key, Math.min(1.6, (simulation.trails.get(key) || 0) + 1.4 * simulation.settings.trail));
    }
  }
  if (simulation.species === "turtle") {
    for (let index = 0; index < 8; index++) {
      const angle = Math.random() * Math.PI * 2;
      const distance = Math.random() * 70;
      simulation.pellets.push({ x: x + Math.cos(angle) * distance, y: y + Math.sin(angle) * distance, vx: Math.cos(angle) * 10, vy: Math.sin(angle) * 10, life: 14 });
    }
    simulation.pellets = simulation.pellets.slice(-60);
    return;
  }
  for (const animal of simulation.animals) {
    const distance = Math.hypot(animal.x - x, animal.y - y);
    if (distance < 240) {
      const strength = 1 - distance / 240;
      const angle = Math.atan2(animal.y - y, animal.x - x);
      const kick = 420 * strength * animal.depth;
      animal.vx = Math.cos(angle) * kick;
      animal.vy = Math.sin(angle) * kick;
      animal.panic = 0.6 + Math.random() * 0.6;
    }
  }
}

export function simulateStill(simulation: Simulation) {
  for (let index = 0; index < 240; index++) stepSimulation(simulation, 1 / 60);
}
