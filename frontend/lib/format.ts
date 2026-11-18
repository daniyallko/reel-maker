export function timecode(seconds: number, fps = 24): string {
  const safe = Math.max(0, Number.isFinite(seconds) ? seconds : 0);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const wholeSeconds = Math.floor(safe % 60);
  const frames = Math.floor((safe % 1) * fps);
  return [hours, minutes, wholeSeconds, frames]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function shortTime(seconds: number): string {
  return `00:${Math.floor(seconds).toString().padStart(2, "0")}`;
}

export function fileSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
