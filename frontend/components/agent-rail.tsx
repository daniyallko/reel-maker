import { Check, Circle, CircleNotch, XCircle } from "@phosphor-icons/react";
import type { AgentStatusEvent } from "@/lib/types";
import { cn } from "./ui";

const AGENTS = [
  ["memory_curator", "Memory Curator"],
  ["voice_analyst", "Voice & Vibe Analyst"],
  ["screenwriter", "Trailer Screenwriter"],
  ["poster_director", "Poster Art Director"],
  ["audio_producer", "Audio & VO Producer"],
  ["editor", "FFmpeg Editor"],
  ["qa_critic", "QA Critic"],
] as const;

export function AgentRail({ events }: { events: AgentStatusEvent[] }) {
  return (
    <ol className="divide-y divide-hairline border-y border-hairline">
      {AGENTS.map(([id, label], index) => {
        const event = [...events].reverse().find((item) => item.agent === id);
        const status = event?.status ?? "pending";
        return (
          <li key={id} className="flex min-h-16 items-start gap-3 py-3">
            <span className="mono w-5 pt-0.5 text-[11px] text-muted">{String(index + 1).padStart(2, "0")}</span>
            <span className="pt-0.5" aria-hidden="true">
              {status === "running" ? <CircleNotch size={17} className="animate-spin text-tally" /> : status === "complete" ? <Check size={17} className="text-keeper" /> : status === "failed" ? <XCircle size={17} className="text-tally" /> : <Circle size={17} className="text-[#484852]" />}
            </span>
            <div className="min-w-0 flex-1">
              <p className={cn("text-sm font-medium", status === "pending" && "text-muted")}>{label}</p>
              <p className="mt-0.5 text-xs leading-5 text-muted">{event?.message ?? "Waiting for dailies"}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
