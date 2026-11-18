import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { VoiceRecorder } from "@/components/voice-recorder";

const originalMediaDevices = navigator.mediaDevices;
const originalMediaRecorder = globalThis.MediaRecorder;

afterEach(() => {
  Object.defineProperty(navigator, "mediaDevices", { value: originalMediaDevices, configurable: true });
  Object.defineProperty(globalThis, "MediaRecorder", { value: originalMediaRecorder, configurable: true });
});

describe("VoiceRecorder", () => {
  it("stops microphone tracks when recorder construction fails", async () => {
    const stop = vi.fn();
    const stream = { getTracks: () => [{ stop }] };
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
      configurable: true,
    });
    Object.defineProperty(globalThis, "MediaRecorder", {
      value: class {
        static isTypeSupported() { return true; }
        constructor() { throw new Error("Recorder unavailable"); }
      },
      configurable: true,
    });
    render(<VoiceRecorder value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Record the real story" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Microphone access was denied"));
    expect(stop).toHaveBeenCalledOnce();
  });
});
