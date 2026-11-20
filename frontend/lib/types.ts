export type AssetKind = "photo" | "video";
export type AssetStatus = "pending" | "kept" | "rejected";
export type Genre = "action" | "indie" | "comedy" | "scifi";
export type ProjectStatus = "queued" | "running" | "complete" | "failed";

export interface CuratedAsset {
  id: string;
  filename: string;
  kind: AssetKind;
  status: AssetStatus;
  score: number;
  emotion: number;
  lighting: number;
  action: number;
  kept: boolean;
  hero: boolean;
  rejection_reason: string | null;
  url: string;
  thumbnail_url: string;
  duration: number | null;
  width: number | null;
  height: number | null;
}

export interface VibeProfile {
  transcript: string;
  destination: string;
  inside_jokes: string[];
  plot_twists: string[];
  energy: string;
}

export interface CastCredit {
  name: string;
  role: string;
  asset_id: string | null;
  card_url: string | null;
}

export interface EDLSegment {
  asset_id: string;
  act: 1 | 2 | 3;
  start: number;
  end: number;
  ken_burns: "zoom_in" | "zoom_out" | "pan_left" | "pan_right";
  title_card: string | null;
  voiceover: string | null;
}

export interface TrailerEDL {
  title: string;
  tagline: string;
  duration: number;
  genre: Genre;
  segments: EDLSegment[];
  cast: CastCredit[];
  beat_markers: number[];
}

export interface PressKitOutput {
  trailer_url: string;
  poster_url: string;
  cast_cards: CastCredit[];
  edl: TrailerEDL;
  duration: number;
  beat_markers: number[];
}

export interface AgentStatusEvent<TOutput = PressKitOutput, TAsset = CuratedAsset> {
  id: number;
  project_id: string;
  agent: string;
  status: "pending" | "running" | "complete" | "failed";
  message: string;
  progress: number;
  timestamp: number;
  assets: TAsset[] | null;
  payload?: {
    output?: TOutput;
    edl?: TrailerEDL;
    vibe?: VibeProfile;
    [key: string]: unknown;
  } | null;
}

export interface ProjectSnapshot {
  id: string;
  status: ProjectStatus;
  genre: Genre;
  created_at: number;
  assets: CuratedAsset[];
  events: AgentStatusEvent[];
  output: PressKitOutput | null;
  error: string | null;
}

export interface StudioAsset {
  id: string;
  kind: "screenshot" | "image" | "video" | "art" | "thumbnail" | "audio" | "critique";
  label: string;
  url: string;
  mime_type: string;
}

export interface StoryScene {
  id: string;
  start: number;
  end: number;
  headline: string;
  narration: string;
  visual_prompt: string;
  source_refs: number[];
  visual_type?: "screenshot" | "source_image" | "generated_art" | "kinetic_type" | "diagram" | "data";
  layout?: "hero" | "split" | "bento" | "full_bleed";
  camera?: "push_in" | "pull_out" | "pan_left" | "pan_right" | "static";
  animation?: "clip_reveal" | "stagger" | "counter_roll" | "path_draw" | "parallax";
  transition?: "cut" | "wipe" | "whip" | "dissolve";
  sfx?: "whoosh" | "pop" | "bass_drop" | "none";
  callouts?: string[];
  metrics?: { label: string; value: number; display: string }[];
}

export interface SourceCitation {
  url: string;
  title: string;
  claim: string;
}

export interface StudioOutput {
  title: string;
  trailer_url: string;
  thumbnail_url: string;
  preview_url: string;
  duration: number;
  bpm: number;
  scenes: StoryScene[];
  sources: SourceCitation[];
  script: string;
  source_url: string | null;
  style: string;
  voice: string;
  quality_mode?: "strict" | "draft";
  review_label?: string | null;
  critique_scores?: Record<string, number>;
}

export interface StudioProjectSnapshot {
  id: string;
  status: ProjectStatus;
  source_url: string;
  source_title?: string;
  style: string;
  voice: string;
  quality_mode?: "strict" | "draft";
  created_at: number;
  assets: StudioAsset[];
  events: AgentStatusEvent<StudioOutput, StudioAsset>[];
  output: StudioOutput | null;
  error: string | null;
}

export interface ProjectInput {
  files: File[];
  cast: string[];
  genre: Genre;
  notes: string;
  voiceNote: Blob | null;
}