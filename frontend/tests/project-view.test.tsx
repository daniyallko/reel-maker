import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectView } from "@/components/project-view";

vi.mock("@/lib/use-project-events", () => ({
  useProjectEvents: () => ({
    snapshot: {
      id: "telemetry01",
      status: "running",
      source_url: "https://example.com",
      source_title: "Example documentary",
      style: "launch",
      voice: "Fenrir",
      created_at: 1,
      assets: [],
      events: [],
      output: null,
      error: null,
    },
    error: "",
    connection: "live",
    retry: vi.fn(),
  }),
}));

describe("ProjectView chrome", () => {
  it("removes the application top bar from the production page", () => {
    render(<ProjectView id="telemetry01" />);
    expect(screen.queryByText("LINK2REEL")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open navigation" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Building your cinematic reel" })).toBeInTheDocument();
  });
});
