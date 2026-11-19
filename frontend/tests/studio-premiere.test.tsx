import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StudioPremiere } from "@/components/studio-premiere";
import { mock_storyboard } from "./studio-fixtures";

const output = {
  title: "Example documentary",
  trailer_url: "/media/demo/output/trailer.mp4",
  thumbnail_url: "/media/demo/output/thumbnail.png",
  preview_url: "/media/demo/audio/narration.wav",
  duration: 32,
  bpm: 128,
  scenes: mock_storyboard.scenes,
  sources: [],
  script: "A complete script",
  source_url: "https://example.com",
  style: "launch",
  voice: "Fenrir",
  quality_mode: "draft" as const,
  review_label: "Unreviewed draft",
};

describe("StudioPremiere review labels", () => {
  it("shows draft warnings in the UI instead of burning them into video", () => {
    render(<StudioPremiere output={output} sourceUrl="https://example.com" />);
    expect(screen.getByText("Unreviewed draft")).toBeInTheDocument();
  });

  it("does not render inline text sources as external links", () => {
    render(<StudioPremiere output={output} sourceUrl="inline://text" />);
    expect(screen.queryByRole("link", { name: "inline://text" })).not.toBeInTheDocument();
    expect(screen.getByText("Example documentary")).toBeInTheDocument();
  });

  it("renders inline citations as text instead of unsupported links", () => {
    render(<StudioPremiere output={{ ...output, sources: [{ url: "inline://text", title: "Written source", claim: "User supplied text" }] }} sourceUrl="inline://text" />);
    expect(screen.getByText("Written source")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Written source" })).not.toBeInTheDocument();
  });
});
