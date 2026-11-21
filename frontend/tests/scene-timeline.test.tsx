import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SceneTimeline } from "@/components/scene-timeline";
import { directedScenes, mock_storyboard } from "./studio-fixtures";

describe("SceneTimeline", () => {
  it("seeks to the selected scene and reports its narration", () => {
    const onSeek = vi.fn();
    const { rerender } = render(<SceneTimeline scenes={mock_storyboard.scenes} currentTime={4} onSeek={onSeek} />);
    fireEvent.click(screen.getByRole("button", { name: /12.0s/ }));
    expect(onSeek).toHaveBeenCalledWith(12.01);
    rerender(<SceneTimeline scenes={mock_storyboard.scenes} currentTime={12.01} onSeek={onSeek} />);
    expect(screen.getByText(/The constellation view maps every link/)).toBeInTheDocument();
  });

  it("labels legacy scenes without typed direction as scene", () => {
    render(<SceneTimeline scenes={mock_storyboard.scenes} currentTime={0} onSeek={vi.fn()} />);
    expect(screen.getAllByText("scene")).toHaveLength(4);
  });

  it("shows directed visual types and seeks variable scenes", () => {
    const onSeek = vi.fn();
    render(<SceneTimeline scenes={directedScenes} currentTime={0} onSeek={onSeek} />);
    expect(screen.getByText("diagram")).toBeInTheDocument();
    expect(screen.getByText("data")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /25.0s/ }));
    expect(onSeek).toHaveBeenCalledWith(25.01);
  });
});
