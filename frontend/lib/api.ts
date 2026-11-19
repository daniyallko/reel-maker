import type { ProjectInput, ProjectSnapshot, StudioProjectSnapshot } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // The status message remains useful when the response is not JSON.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export function createSampleProject(): Promise<ProjectSnapshot> {
  return request<ProjectSnapshot>("/api/projects/sample", { method: "POST" });
}

export function createProject(input: ProjectInput): Promise<ProjectSnapshot> {
  const form = new FormData();
  input.files.forEach((file) => form.append("files", file, file.name));
  form.append("cast", input.cast.join(","));
  form.append("genre", input.genre);
  form.append("notes", input.notes);
  if (input.voiceNote) {
    const extension = input.voiceNote.type.includes("mp4") ? "mp4" : input.voiceNote.type.includes("ogg") ? "ogg" : input.voiceNote.type.includes("mpeg") ? "mp3" : input.voiceNote.type.includes("wav") ? "wav" : "webm";
    form.append("voice_note", input.voiceNote, `directors-note.${extension}`);
  }
  return request<ProjectSnapshot>("/api/projects", { method: "POST", body: form });
}

export function getProject(id: string): Promise<StudioProjectSnapshot> {
  return request<StudioProjectSnapshot>(`/api/studio/projects/${id}`, { cache: "no-store" });
}

export function createStudioProject(input: { url: string; style: string; voice: string }): Promise<StudioProjectSnapshot> {
  return request<StudioProjectSnapshot>("/api/studio/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function createStudioSample(): Promise<StudioProjectSnapshot> {
  return request<StudioProjectSnapshot>("/api/studio/projects/sample", { method: "POST" });
}