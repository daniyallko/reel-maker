import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SceneTimeline } from "@/components/scene-timeline";
import { mock_storyboard } from "./studio-fixtures";

describe("SceneTimeline", () => {
  it("seeks to the selected scene and reports its narration", () => {
    const onSeek = vi.fn();
    const { rerender } = render(<SceneTimeline scenes={mock_storyboard.scenes} currentTime={4} onSeek={onSeek} />);
    fireEvent.click(screen.getByRole("button", { name: /12.0s/ }));
    expect(onSeek).toHaveBeenCalledWith(12.01);
    rerender(<SceneTimeline scenes={mock_storyboard.scenes} currentTime={12.01} onSeek={onSeek} />);
    expect(screen.getByText(/The constellation view maps every link/)).toBeInTheDocument();
  });
});
