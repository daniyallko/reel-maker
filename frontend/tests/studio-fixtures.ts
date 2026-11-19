import type { StoryScene } from "@/lib/types";

export const mock_storyboard = {
  title: "Orbit Notes",
  style: "launch",
  voice: "Fenrir",
  duration: 32,
  bpm: 128,
  scenes: [
    { id: "hook", start: 0, end: 2.5, headline: "Hook", narration: "First line", visual_prompt: "Hook visual", source_refs: [0] },
    { id: "problem", start: 2.5, end: 12, headline: "Problem", narration: "Second line", visual_prompt: "Problem visual", source_refs: [0] },
    { id: "system", start: 12, end: 25, headline: "System", narration: "The constellation view maps every link", visual_prompt: "System visual", source_refs: [0] },
    { id: "takeaway", start: 25, end: 32, headline: "Takeaway", narration: "Final line", visual_prompt: "Takeaway visual", source_refs: [0] },
  ] satisfies StoryScene[],
  sources: [],
  speech_style: "High energy",
};
