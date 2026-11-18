"use client";

import { Microphone, Stop, Trash } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { timecode } from "@/lib/format";
import { ErrorNote } from "./ui";

export function VoiceRecorder({ value, onChange }: { value: Blob | null; onChange: (blob: Blob | null) => void }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => setSeconds((current) => current + 1), 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => () => {
    stream.current?.getTracks().forEach((track) => track.stop());
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  async function start() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("This browser cannot record audio. You can still add the story in the notes below.");
      return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks.current = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : undefined;
      const nextRecorder = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined);
      recorder.current = nextRecorder;
      nextRecorder.ondataavailable = (event) => {
        if (event.data.size) chunks.current.push(event.data);
      };
      nextRecorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: nextRecorder.mimeType || "audio/webm" });
        onChange(blob);
        if (audioUrl) URL.revokeObjectURL(audioUrl);
        setAudioUrl(URL.createObjectURL(blob));
        stream.current?.getTracks().forEach((track) => track.stop());
      };
      setSeconds(0);
      nextRecorder.start();
      setRecording(true);
    } catch {
      stream.current?.getTracks().forEach((track) => track.stop());
      stream.current = null;
      recorder.current = null;
      setRecording(false);
      setError("Microphone access was denied. Allow access or leave the voice note empty.");
    }
  }

  function stop() {
    recorder.current?.stop();
    setRecording(false);
  }

  function remove() {
    onChange(null);
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm">Voice note <span className="text-muted">(optional)</span></span>
        <span className={`mono text-xs ${recording ? "text-tally" : "text-muted"}`} aria-live="off">
          {recording && <span className="mr-2 inline-block size-2 rounded-full bg-tally align-middle" aria-hidden="true" />}
          {timecode(seconds).slice(3)}
        </span>
      </div>
      {!value ? (
        <button
          type="button"
          className={recording ? "btn btn-primary w-full" : "btn btn-secondary w-full"}
          onClick={recording ? stop : start}
          aria-pressed={recording}
        >
          {recording ? <Stop size={18} weight="fill" aria-hidden="true" /> : <Microphone size={18} aria-hidden="true" />}
          {recording ? "Stop recording" : "Record the real story"}
        </button>
      ) : (
        <div className="border border-hairline p-3">
          <audio className="h-11 w-full" controls src={audioUrl ?? undefined}>Your browser does not support audio playback.</audio>
          <button type="button" className="btn btn-ghost mt-2 px-0 text-xs" onClick={remove}>
            <Trash size={16} aria-hidden="true" /> Record again
          </button>
        </div>
      )}
      <p className="metadata mt-2">Confess the wrong turn, the missing keys, or who booked the house.</p>
      {error && <div className="mt-3"><ErrorNote>{error}</ErrorNote></div>}
    </div>
  );
}
