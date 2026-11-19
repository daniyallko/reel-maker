import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GlyphHome } from "@/components/glyph-home";
import { createStudioProject, createStudioSample } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", () => ({
  createStudioProject: vi.fn().mockResolvedValue({ id: "acme123" }),
  createStudioSample: vi.fn().mockResolvedValue({ id: "sample123" }),
}));

describe("GlyphHome URL composer", () => {
  beforeEach(() => vi.clearAllMocks());

  it("detects a public URL and enables every control", async () => {
    render(<GlyphHome />);
    const input = screen.getByLabelText("Source URL");
    fireEvent.change(input, { target: { value: "https://acme.example" } });
    expect(screen.getByText("Public URL detected. Every control is ready.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Video style"), { target: { value: "roast" } });
    fireEvent.change(screen.getByLabelText("Studio voice"), { target: { value: "Aoede" } });
    fireEvent.click(screen.getByRole("button", { name: "Make my reel" }));
    await waitFor(() => expect(createStudioProject).toHaveBeenCalledWith({ url: "https://acme.example", style: "roast", voice: "Aoede" }));
  });

  it("rejects an invalid URL before calling the API", () => {
    render(<GlyphHome />);
    fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "not-a-url" } });
    fireEvent.click(screen.getByRole("button", { name: "Make my reel" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a public http or https URL");
    expect(createStudioProject).not.toHaveBeenCalled();
  });

  it("loads the instant offline demo", () => {
    render(<GlyphHome />);
    fireEvent.click(screen.getByRole("button", { name: "Load Sample Link (Instant Demo)" }));
    expect(createStudioSample).toHaveBeenCalledOnce();
  });
});
