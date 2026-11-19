"use client";

import { useEffect, useRef } from "react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { createSimulation, drawSimulation, resizeSimulation, scatter, simulateStill, stepSimulation, type GlyphSettings, type SpeciesKey } from "@/lib/glyph-animals";

export function GlyphCanvas({ species, settings, count }: { species: SpeciesKey; settings: GlyphSettings; count?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simulationRef = useRef<ReturnType<typeof createSimulation> | null>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let context: CanvasRenderingContext2D | null = null;
    try {
      context = canvas.getContext("2d");
    } catch {
      context = null;
    }
    if (!context) return;
    let active = true;
    let frame = 0;
    let last = performance.now();
    const simulation = createSimulation(canvas.clientWidth, canvas.clientHeight, species, settings, getComputedStyle(canvas).fontFamily, count);
    simulationRef.current = simulation;

    const draw = () => {
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(canvas.clientWidth * ratio);
      canvas.height = Math.round(canvas.clientHeight * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      drawSimulation(context, simulation);
    };
    const resize = () => {
      resizeSimulation(simulation, canvas.clientWidth, canvas.clientHeight);
      draw();
    };
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    observer?.observe(canvas);
    const intersection = typeof IntersectionObserver !== "undefined" ? new IntersectionObserver(([entry]) => { active = entry.isIntersecting; }) : null;
    intersection?.observe(canvas);

    const animate = (now: number) => {
      if (!active) { last = now; frame = requestAnimationFrame(animate); return; }
      const elapsed = Math.min(0.1, (now - last) / 1000);
      last = now;
      const steps = Math.min(4, Math.max(1, Math.round(elapsed * 60)));
      for (let index = 0; index < steps; index++) stepSimulation(simulation, elapsed / steps);
      draw();
      frame = requestAnimationFrame(animate);
    };

    if (reducedMotion) {
      simulateStill(simulation);
      draw();
    } else {
      if (document.fonts?.load) {
        document.fonts.load("600 16px Geist Mono").then(() => {
          resize();
          frame = requestAnimationFrame(animate);
        });
      } else {
        resize();
        frame = requestAnimationFrame(animate);
      }
    }
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
      intersection?.disconnect();
    };
  }, [species, settings, count, reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className="glyph-field"
      aria-hidden="true"
      onPointerDown={(event) => {
        if (reducedMotion || !simulationRef.current) return;
        const rect = event.currentTarget.getBoundingClientRect();
        scatter(simulationRef.current, event.clientX - rect.left, event.clientY - rect.top);
      }}
    />
  );
}
