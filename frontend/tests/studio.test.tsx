import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { UrlStudio } from "@/components/url-studio";
import { createStudioProject, createStudioSample } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  createStudioProject: vi.fn().mockResolvedValue({ id: "abc123" }),
  createStudioSample: vi.fn().mockResolvedValue({ id: "sample123" }),
}));

describe("UrlStudio", () => {
  beforeEach(() => vi.clearAllMocks());
  it("loads a sample URL and selects style and voice", () => {
    render(<UrlStudio onProjectCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Wikipedia deep-dive" }));
    expect(screen.getByLabelText("Source URL")).toHaveValue("https://en.wikipedia.org/wiki/Artificial_intelligence");
    fireEvent.click(screen.getByRole("radio", { name: "Honest Product Roast" }));
    fireEvent.click(screen.getByRole("radio", { name: "Aoede" }));
    fireEvent.click(screen.getByRole("button", { name: "Make my reel" }));
    expect(createStudioProject).toHaveBeenCalledWith({
      url: "https://en.wikipedia.org/wiki/Artificial_intelligence",
      style: "roast",
      voice: "Aoede",
    });
  });

  it("starts the instant offline demo", () => {
    render(<UrlStudio onProjectCreated={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Load Sample Link (Instant Demo)" }));
    expect(createStudioSample).toHaveBeenCalledOnce();
  });

  it("rejects an invalid URL before calling the API", () => {
    render(<UrlStudio onProjectCreated={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "not-a-url" } });
    fireEvent.click(screen.getByRole("button", { name: "Make my reel" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a public http or https URL");
    expect(createStudioProject).not.toHaveBeenCalled();
  });
});
