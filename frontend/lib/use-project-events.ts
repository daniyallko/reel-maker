"use client";

import { useCallback, useEffect, useState } from "react";
import { getProject } from "./api";
import type { AgentStatusEvent, StudioAsset, StudioOutput, StudioProjectSnapshot } from "./types";

export function mergeStudioAssets(current: StudioAsset[], incoming: StudioAsset[]): StudioAsset[] {
  const assets = new Map(current.map((asset) => [asset.id, asset]));
  incoming.forEach((asset) => assets.set(asset.id, asset));
  return [...assets.values()];
}

export type ConnectionState = "connecting" | "live" | "stale" | "closed";

export function useProjectEvents(id: string) {
  const [snapshot, setSnapshot] = useState<StudioProjectSnapshot | null>(null);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setSnapshot(null);
    setError("");
    setConnection("connecting");
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    let events: EventSource | null = null;

    async function connect() {
      try {
        const project = await getProject(id);
        if (!active) return;
        setSnapshot(project);
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Project could not be loaded.");
        return;
      }

      if (!active) return;
      events = new EventSource(`/api/studio/projects/${id}/events`);
      events.onopen = () => { if (active) setConnection("live"); };
      events.onerror = () => {
        if (active && events?.readyState !== EventSource.CLOSED) setConnection("stale");
      };
      events.onmessage = (message) => {
        if (!active) return;
        const event = JSON.parse(message.data) as AgentStatusEvent<StudioOutput, StudioAsset>;
        setSnapshot((current) => {
          if (!current) return current;
          if (current.events.some((existing) => existing.id === event.id)) return current;
          const output = event.payload?.output ?? current.output;
          return {
            ...current,
            assets: event.assets ? mergeStudioAssets(current.assets, event.assets) : current.assets,
            output,
            events: [...current.events, event],
            status: event.agent === "pipeline" && event.status === "failed"
              ? "failed"
              : event.agent === "premiere" && event.status === "complete"
                ? "complete"
                : current.status,
            error: event.status === "failed" ? event.message : current.error,
          };
        });
        if (event.agent === "premiere" || event.agent === "pipeline") {
          setConnection("closed");
          events?.close();
        }
      };
    }

    void connect();
    return () => {
      active = false;
      events?.close();
    };
  }, [id, attempt]);

  return { snapshot, error, connection, retry };
}
