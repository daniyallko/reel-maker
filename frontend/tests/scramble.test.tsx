import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ScrambleIn, ScrambleText } from "@/components/scramble";

afterEach(() => {
  vi.useRealTimers();
});

describe("ScrambleIn", () => {
  it("reserves space before triggering, then reveals the exact text", () => {
    vi.useFakeTimers();
    const { container, rerender } = render(<ScrambleIn text="CUTLINE" delay={200} triggered={false} />);
    expect(container.textContent).toBe(" ");
    rerender(<ScrambleIn text="CUTLINE" delay={200} triggered={true} />);
    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(screen.getByText("CUTLINE")).toBeInTheDocument();
  });
});

describe("ScrambleText", () => {
  it("restores the original text immediately after hover ends", () => {
    vi.useFakeTimers();
    const { rerender } = render(<ScrambleText text="Metrics" isHovered={true} />);
    act(() => {
      vi.advanceTimersByTime(50);
    });
    rerender(<ScrambleText text="Metrics" isHovered={false} />);
    expect(screen.getByText("Metrics")).toBeInTheDocument();
  });

  it("settles on the original text after a hover scramble", () => {
    vi.useFakeTimers();
    render(<ScrambleText text="About" isHovered={true} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("About")).toBeInTheDocument();
  });
});
