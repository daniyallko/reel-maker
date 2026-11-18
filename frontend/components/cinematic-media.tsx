"use client";

import { Pause, Play } from "@phosphor-icons/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useEffect, useRef, useState } from "react";

export const VIDEOS = {
  hero: "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_083515_290e5a10-0b95-41af-a5e2-32b6389baa4d.mp4",
  screening: "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_092455_089c54f8-3b03-4966-9df1-e9746063d0ef.mp4",
  premiere: "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_095810_ecea3dd2-fc5e-4e41-8696-4219290b6589.mp4",
  cast: "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_095750_32a52ce0-2005-45c9-9093-41f03fde9530.mp4",
  footer: "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_080203_fd7f4f85-3a86-4837-8192-85e7bfe68e75.mp4",
} as const;

export function clampSeek(current: number, delta: number, duration: number, sensitivity = 0.8): number {
  if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(current)) return current;
  return Math.min(duration, Math.max(0, current + delta * sensitivity));
}

export function MouseScrubVideo({ className = "" }: { className?: string }) {
  const video = useRef<HTMLVideoElement>(null);
  const seeking = useRef(false);
  const pendingDelta = useRef(0);
  const lastX = useRef<number | null>(null);

  useEffect(() => {
    const element = video.current;
    if (!element) return;
    element.pause();
    const applySeek = () => {
      if (!video.current || seeking.current || pendingDelta.current === 0) return;
      const target = clampSeek(video.current.currentTime, pendingDelta.current, video.current.duration);
      pendingDelta.current = 0;
      if (Math.abs(target - video.current.currentTime) < 0.001) {
        seeking.current = false;
        return;
      }
      seeking.current = true;
      video.current.currentTime = target;
    };
    const onSeeked = () => {
      seeking.current = false;
      applySeek();
    };
    element.addEventListener("seeked", onSeeked);
    return () => element.removeEventListener("seeked", onSeeked);
  }, []);

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      const delta = lastX.current === null ? 0 : event.clientX - lastX.current;
      lastX.current = event.clientX;
      pendingDelta.current += delta;
      if (pendingDelta.current === 0) return;
      if (!seeking.current && video.current && Number.isFinite(video.current.duration)) {
        const target = clampSeek(video.current.currentTime, pendingDelta.current, video.current.duration);
        pendingDelta.current = 0;
        if (Math.abs(target - video.current.currentTime) < 0.001) return;
        seeking.current = true;
        video.current.currentTime = target;
      }
    };
    window.addEventListener("pointermove", onPointerMove);
    return () => window.removeEventListener("pointermove", onPointerMove);
  }, []);

  return <VideoBackground ref={video} src={VIDEOS.hero} autoPlay={false} className={className} />;
}

interface VideoBackgroundProps extends React.VideoHTMLAttributes<HTMLVideoElement> {
  ref?: React.Ref<HTMLVideoElement>;
  src: string;
  autoPlay?: boolean;
  className?: string;
}

export function VideoBackground({ ref, src, autoPlay = true, className = "", onPointerMove, onPointerLeave, ...props }: VideoBackgroundProps) {
  const reducedMotion = Boolean(useReducedMotion());
  const localVideo = useRef<HTMLVideoElement | null>(null);
  const [playing, setPlaying] = useState(autoPlay && !reducedMotion);

  useEffect(() => {
    const element = localVideo.current;
    if (!element) return;
    if (reducedMotion || !playing) {
      element.pause();
      if (reducedMotion) setPlaying(false);
      return;
    }
    void element.play().catch(() => setPlaying(false));
  }, [playing, reducedMotion]);

  useEffect(() => {
    const element = localVideo.current;
    if (!element || !autoPlay) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) element.pause();
      else if (playing && !reducedMotion) void element.play().catch(() => undefined);
    }, { threshold: 0.05 });
    observer.observe(element);
    return () => observer.disconnect();
  }, [autoPlay, playing, reducedMotion]);

  return (
    <>
      <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
        <video
          ref={(node) => {
            localVideo.current = node;
            if (typeof ref === "function") ref(node);
            else if (ref) ref.current = node;
          }}
          src={src}
          className={`size-full object-cover ${onPointerMove ? "pointer-events-auto" : ""}`}
          muted
          loop
          playsInline
          preload={autoPlay ? "metadata" : "auto"}
          onPointerMove={onPointerMove}
          onPointerLeave={onPointerLeave}
          {...props}
        />
      </div>
      <button
        type="button"
        className="btn absolute right-4 top-24 z-30 min-h-11 rounded-full border-white/15 bg-black/45 px-4 text-xs text-white backdrop-blur-md hover:bg-black/65"
        onClick={() => setPlaying((current) => !current)}
        aria-label={playing ? "Pause background video" : "Play background video"}
      >
        {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
        {playing ? "Pause" : "Play"}
      </button>
    </>
  );
}
