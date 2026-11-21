import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StudioScreening } from "@/components/studio-screening";
import type { StudioProjectSnapshot } from "@/lib/types";

const project: StudioProjectSnapshot = {
  id: "telemetry01",
  status: "running",
  source_url: "https://example.com",
  source_title: "Example documentary",
  style: "launch",
  voice: "Fenrir",
  created_at: 1,
  assets: [],
  output: null,
  error: null,
  events: [
    {
      id: 1,
      project_id: "telemetry01",
      agent: "harvester",
      status: "complete",
      message: "3 real source assets captured.",
      progress: 20,
      timestamp: 1700000000,
      assets: null,
      payload: null,
    },
    {
      id: 2,
      project_id: "telemetry01",
      agent: "researcher",
      status: "running",
      message: "Researching evidence for the story… (12s)",
      progress: 10,
      timestamp: 1700000004,
      assets: null,
      payload: null,
    },
  ],
};

describe("StudioScreening active telemetry", () => {
  it.each([
    ["researcher", "Story Researcher"],
    ["scriptwriter", "Narrative Scriptwriter"],
    ["nano_visuals", "Scene Asset Director"],
    ["voice_studio", "Narration Studio"],
    ["motion_coder", "Motion Director"],
  ])("uses work-focused stage label %s / %s", (agent, label) => {
    const currentProject: StudioProjectSnapshot = {
      ...project,
      events: [{
        ...project.events[1],
        agent,
        message: agent === "scriptwriter" ? "Writing the narrative shot map…" : "Directing the current production stage…",
      }],
    };
    render(<StudioScreening project={currentProject} connection="live" onRetry={vi.fn()} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: `${label} executing` })).toBeInTheDocument();
    for (const removed of ["External Story Researcher", "Viral Scriptwriter", "Nano Banana Visuals", "Gemini Studio Voice", "Motion Coder"]) {
      expect(screen.queryByText(removed)).not.toBeInTheDocument();
    }
    expect(screen.queryByText(/four-act/i)).not.toBeInTheDocument();
  });

  it("shows only the current backend process", () => {
    render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Building your cinematic reel" })).toBeInTheDocument();
    expect(screen.getByText("Example documentary")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Story Researcher executing" })).toBeInTheDocument();
    expect(screen.queryByText("Web Harvester")).not.toBeInTheDocument();
    expect(screen.queryByText("Narrative Scriptwriter")).not.toBeInTheDocument();
  });

  it("animates to the next active process", async () => {
    const { rerender } = render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    const next: StudioProjectSnapshot = {
      ...project,
      events: [...project.events, {
        id: 3,
        project_id: "telemetry01",
        agent: "scriptwriter",
        status: "running",
        message: "Writing the narrative shot map…",
        progress: 32,
        timestamp: 1700000008,
        assets: null,
        payload: null,
      }],
    };
    rerender(<StudioScreening project={next} connection="live" onRetry={vi.fn()} />);
    expect(await screen.findByRole("img", { name: "Narrative Scriptwriter executing" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("img", { name: "Story Researcher executing" })).not.toBeInTheDocument());
  });

  it("streams backend responses with technical event metadata", () => {
    render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    const log = screen.getByRole("log", { name: "Backend response stream" });
    expect(log).toHaveTextContent("#000002");
    expect(log).toHaveTextContent("researcher");
    expect(log).toHaveTextContent("RUNNING");
    expect(log).toHaveTextContent("10%");
    expect(log).toHaveTextContent("Researching evidence for the story… (12s)");
    expect(log).toHaveTextContent("UTC");
    expect(log).toHaveTextContent("3 real source assets captured.");
  });

  it("keeps backend responses visible and stops animation on failure", () => {
    const failed: StudioProjectSnapshot = {
      ...project,
      status: "failed",
      error: "Vision provider unavailable",
      events: [...project.events, {
        id: 3,
        project_id: "telemetry01",
        agent: "pipeline",
        status: "failed",
        message: "Vision provider unavailable",
        progress: 100,
        timestamp: 1700000008,
        assets: null,
        payload: null,
      }],
    };
    render(<StudioScreening project={failed} connection="closed" onRetry={vi.fn()} />);
    expect(screen.getByRole("log", { name: "Backend response stream" })).toHaveTextContent("Vision provider unavailable");
    expect(screen.queryByRole("img", { name: /executing/ })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Pipeline failed" })).toBeInTheDocument();
  });

  it("does not render inline text sources as external links", () => {
    const inline = { ...project, source_url: "inline://text", source_title: "My written story" };
    render(<StudioScreening project={inline} connection="live" onRetry={vi.fn()} />);
    expect(screen.getByText("My written story")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "inline://text" })).not.toBeInTheDocument();
  });
});
