import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

Object.defineProperty(HTMLMediaElement.prototype, "play", { value: vi.fn().mockResolvedValue(undefined), configurable: true });
Object.defineProperty(HTMLMediaElement.prototype, "pause", { value: vi.fn(), configurable: true });
Object.defineProperty(HTMLCanvasElement.prototype, "getContext", { value: vi.fn().mockReturnValue(null), configurable: true });
