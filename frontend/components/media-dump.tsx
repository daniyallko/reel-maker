"use client";

import { FileVideo, Image as ImageIcon, Plus, UploadSimple, X } from "@phosphor-icons/react";
import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useEffect, useMemo, useRef, useState } from "react";
import { fileSize } from "@/lib/format";

interface MediaDumpProps {
  files: File[];
  onChange: (files: File[]) => void;
}

export function MediaDump({ files, onChange }: MediaDumpProps) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const reduceMotion = Boolean(useReducedMotion());
  const previews = useMemo(() => files.map((file) => ({ file, url: URL.createObjectURL(file) })), [files]);

  useEffect(() => () => previews.forEach(({ url }) => URL.revokeObjectURL(url)), [previews]);

  function add(incoming: File[]) {
    const accepted = incoming.filter((file) => /^(image\/(jpeg|png|webp)|video\/(mp4|quicktime|webm))$/.test(file.type));
    if (accepted.length !== incoming.length) setError("Some files were skipped. Use JPEG, PNG, WebP, MP4, MOV, or WebM.");
    else setError("");
    const unique = accepted.filter((file) => !files.some((current) => current.name === file.name && current.size === file.size));
    onChange([...files, ...unique].slice(0, 25));
  }

  return (
    <div>
      <input
        ref={input}
        type="file"
        className="sr-only"
        multiple
        accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
        onChange={(event) => {
          add(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
        aria-label="Choose trip photos and videos"
      />
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          add(Array.from(event.dataTransfer.files));
        }}
        className={`flex min-h-36 w-full flex-col items-center justify-center border border-dashed px-4 py-6 text-center transition-colors ${dragging ? "border-marquee bg-[#1c1a14]" : "border-[#3a3a44] bg-[#0e0e12] hover:border-muted"}`}
      >
        <UploadSimple size={28} className="mb-3 text-marquee" aria-hidden="true" />
        <span className="text-sm font-semibold">Drop the whole camera roll</span>
        <span className="metadata mt-1">10–25 photos + short clips · or tap to browse</span>
      </button>
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="metadata">Duplicates and blurry shots get cut locally.</p>
        <span className={`mono text-xs ${files.length >= 10 ? "text-keeper" : "text-muted"}`}>{files.length.toString().padStart(2, "0")} / 25</span>
      </div>
      {error && <p className="mt-2 text-xs text-[#f0a3a6]" role="alert">{error}</p>}
      {files.length > 0 && (
        <motion.ul layout className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4" aria-label="Uploaded contact sheet">
          {previews.map(({ file, url }, index) => (
            <motion.li
              layout
              key={`${file.name}-${file.size}`}
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.28, delay: reduceMotion ? 0 : Math.min(index * 0.04, 0.4) }}
              className="group relative aspect-[4/3] overflow-hidden border border-hairline bg-surface-raised"
            >
              {file.type.startsWith("video/") ? (
                <video src={url} muted playsInline preload="metadata" className="size-full object-cover opacity-85" aria-label={`Video preview ${file.name}`} />
              ) : (
                // Local object URLs cannot use next/image optimization.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={url} alt={`Upload ${index + 1}: ${file.name}`} className="size-full object-cover" />
              )}
              <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-canvas/90 px-2 py-1.5">
                <span className="mono flex min-w-0 items-center gap-1 text-[11px] text-paper">
                  {file.type.startsWith("video/") ? <FileVideo size={12} aria-hidden="true" /> : <ImageIcon size={12} aria-hidden="true" />}
                  <span className="truncate">{fileSize(file.size)}</span>
                </span>
                <span className="mono text-[11px] text-muted">{String(index + 1).padStart(2, "0")}</span>
              </div>
              <button
                type="button"
                className="absolute right-1 top-1 flex size-11 items-center justify-center bg-canvas/80 text-paper sm:size-9 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"
                onClick={() => onChange(files.filter((_, fileIndex) => fileIndex !== index))}
                aria-label={`Remove ${file.name}`}
              >
                <X size={15} aria-hidden="true" />
              </button>
            </motion.li>
          ))}
          {files.length < 25 && (
            <li>
              <button type="button" className="flex aspect-[4/3] size-full min-h-20 flex-col items-center justify-center gap-2 border border-dashed border-hairline text-muted hover:border-muted hover:text-paper" onClick={() => input.current?.click()}>
                <Plus size={20} aria-hidden="true" /><span className="metadata">Add shots</span>
              </button>
            </li>
          )}
        </motion.ul>
      )}
    </div>
  );
}
