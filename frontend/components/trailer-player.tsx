"use client";

import { useEffect, useRef, useState } from "react";
import type { CuratedAsset, PressKitOutput } from "@/lib/types";
import { FilmstripTimeline } from "./filmstrip-timeline";

export function TrailerPlayer({ output, assets }: { output: PressKitOutput; assets: CuratedAsset[] }) {
  const video = useRef<HTMLVideoElement>(null);
  const audioContext = useRef<AudioContext | null>(null);
  const analyser = useRef<AnalyserNode | null>(null);
  const animation = useRef<number | null>(null);
  const lastMeterUpdate = useRef(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);

  useEffect(() => () => {
    if (animation.current) cancelAnimationFrame(animation.current);
    void audioContext.current?.close();
  }, []);

  async function enableAnalyser() {
    if (!video.current || analyser.current) {
      await audioContext.current?.resume();
      return;
    }
    try {
      const context = new AudioContext();
      const source = context.createMediaElementSource(video.current);
      const meter = context.createAnalyser();
      meter.fftSize = 128;
      meter.smoothingTimeConstant = 0.72;
      source.connect(meter);
      meter.connect(context.destination);
      audioContext.current = context;
      analyser.current = meter;
      const values = new Uint8Array(meter.frequencyBinCount);
      const update = (now: number) => {
        meter.getByteFrequencyData(values);
        if (now - lastMeterUpdate.current > 70) {
          const average = values.reduce((sum, value) => sum + value, 0) / values.length / 255;
          setAudioLevel(average);
          lastMeterUpdate.current = now;
        }
        animation.current = requestAnimationFrame(update);
      };
      animation.current = requestAnimationFrame(update);
    } catch {
      // Native playback and the time-driven timeline remain available without Web Audio.
      setAudioLevel(0.12);
    }
  }

  return (
    <div>
      <div className="flex justify-center bg-black">
        <video
          ref={video}
          src={output.trailer_url}
          className="aspect-[9/16] max-h-[72dvh] w-full object-contain"
          controls
          playsInline
          preload="metadata"
          crossOrigin="anonymous"
          onPlay={enableAnalyser}
          onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
          onSeeked={(event) => setCurrentTime(event.currentTarget.currentTime)}
          aria-label={`${output.edl.title} vertical movie trailer`}
        >
          Your browser does not support HTML5 video. <a href={output.trailer_url}>Download the trailer.</a>
        </video>
      </div>
      <FilmstripTimeline
        edl={output.edl}
        assets={assets}
        currentTime={currentTime}
        audioLevel={audioLevel}
        onSeek={(time) => {
          if (video.current) {
            video.current.currentTime = time;
            setCurrentTime(time);
          }
        }}
      />
    </div>
  );
}
