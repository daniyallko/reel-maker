import { describe, expect, it } from "vitest";
import { clampSeek } from "@/components/cinematic-media";

describe("clampSeek", () => {
  it("applies delta sensitivity without dropping elapsed time", () => {
    expect(clampSeek(5, 10, 22)).toBe(13);
  });

  it("clamps to the start of the video", () => {
    expect(clampSeek(1, -20, 22)).toBe(0);
  });

  it("clamps to the known duration", () => {
    expect(clampSeek(20, 20, 22)).toBe(22);
  });

  it("keeps the current time when duration is unavailable", () => {
    expect(clampSeek(4, 10, Number.NaN)).toBe(4);
  });
});
