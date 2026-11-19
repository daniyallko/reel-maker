import { describe, expect, it } from "vitest";
import { mergeStudioAssets } from "@/lib/use-project-events";

describe("mergeStudioAssets", () => {
  it("keeps earlier assets and replaces only matching ids", () => {
    const current = [{ id: "hero", kind: "screenshot" as const, label: "Hero", url: "/hero", mime_type: "image/png" }];
    const incoming = [{ id: "critique", kind: "critique" as const, label: "Audit", url: "/audit", mime_type: "image/png" }];
    expect(mergeStudioAssets(current, incoming).map((asset) => asset.id)).toEqual(["hero", "critique"]);
  });
});
