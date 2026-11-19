import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GlyphHome } from "@/components/glyph-home";
import { createStudioInput, createStudioSample } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", () => ({
  createStudioInput: vi.fn().mockResolvedValue({ id: "acme123" }),
  createStudioSample: vi.fn().mockResolvedValue({ id: "sample123" }),
}));

describe("GlyphHome universal composer", () => {
  beforeEach(() => vi.clearAllMocks());

  it("presents a cinematic source composer without URL shortcuts", () => {
    const { container } = render(<GlyphHome />);
    expect(screen.getByRole("heading", { name: "Your story. Cut like a film." })).toBeInTheDocument();
    expect(screen.getByLabelText("Story, link, or description")).toBeInTheDocument();
    expect(screen.queryByText("Source URL")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "AI startup" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "GitHub repo" })).not.toBeInTheDocument();
    expect(container.querySelector(".composer-input svg")).toBeNull();
    expect(screen.getByText("Uploads are sent to your configured AI providers for analysis.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create my film" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Watch portfolio demo" })).toBeInTheDocument();
  });

  it("submits a topic, cinematic controls, and uploaded sources", async () => {
    render(<GlyphHome />);
    fireEvent.change(screen.getByLabelText("Story, link, or description"), { target: { value: "A documentary about ocean repair" } });
    fireEvent.change(screen.getByLabelText("Cinematic style"), { target: { value: "tech_launch" } });
    fireEvent.change(screen.getByLabelText("Narration voice"), { target: { value: "Aoede" } });
    const file = new File(["Ocean evidence"], "ocean.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Add source files"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Create my film" }));
    await waitFor(() => expect(createStudioInput).toHaveBeenCalledWith({
      source: "A documentary about ocean repair",
      style: "tech_launch",
      voice: "Aoede",
      qualityMode: "strict",
      files: [file],
    }));
  });

  it("removes an uploaded source before submission", () => {
    render(<GlyphHome />);
    const file = new File(["Evidence"], "notes.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Add source files"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Remove notes.txt" }));
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });

  it("loads the instant portfolio demo", () => {
    render(<GlyphHome />);
    fireEvent.click(screen.getByRole("button", { name: "Watch portfolio demo" }));
    expect(createStudioSample).toHaveBeenCalledOnce();
  });

  it("aligns the selected species thumb with its pill", async () => {
    const { container } = render(<GlyphHome />);
    const rabbit = screen.getByRole("radio", { name: "Rabbit" });
    Object.defineProperties(rabbit, {
      offsetLeft: { value: 96 },
      offsetTop: { value: 4 },
      offsetWidth: { value: 120 },
      offsetHeight: { value: 32 },
    });
    fireEvent.click(rabbit);
    const thumb = container.querySelector(".species-thumb") as HTMLElement;
    await waitFor(() => expect(thumb.style.transform).toBe("translate(96px, 4px)"));
    expect(thumb.style.width).toBe("120px");
    expect(thumb.style.height).toBe("32px");
  });
});
