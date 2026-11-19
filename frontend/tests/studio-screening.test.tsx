import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StudioScreening } from "@/components/studio-screening";
import type { StudioProjectSnapshot } from "@/lib/types";

const project: StudioProjectSnapshot = {
  id: "telemetry01",
  status: "running",
  source_url: "https://example.com",
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
      message: "Finding the story beyond the landing page… (12s)",
      progress: 10,
      timestamp: 1700000004,
      assets: null,
      payload: null,
    },
  ],
};

describe("StudioScreening telemetry", () => {
  it("shows the executing icon for the active backend step", () => {
    render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    expect(screen.getByRole("img", { name: "External Story Researcher executing" })).toBeInTheDocument();
  });

  it("streams backend responses with technical event metadata", () => {
    render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    const log = screen.getByRole("log", { name: "Backend response stream" });
    expect(log).toHaveTextContent("#000002");
    expect(log).toHaveTextContent("researcher");
    expect(log).toHaveTextContent("RUNNING");
    expect(log).toHaveTextContent("10%");
    expect(log).toHaveTextContent("Finding the story beyond the landing page… (12s)");
    expect(log).toHaveTextContent("UTC");
  });

  it("keeps completed backend responses visible", () => {
    render(<StudioScreening project={project} connection="live" onRetry={vi.fn()} />);
    const log = screen.getByRole("log", { name: "Backend response stream" });
    expect(log).toHaveTextContent("#000001");
    expect(log).toHaveTextContent("COMPLETE");
    expect(log).toHaveTextContent("3 real source assets captured.");
  });

  it("keeps backend responses visible when the pipeline fails", () => {
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
    expect(screen.queryByRole("img", { name: "External Story Researcher executing" })).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "External Story Researcher failed" })).toBeInTheDocument();
  });
});
