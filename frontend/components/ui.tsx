import { CircleNotch } from "@phosphor-icons/react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  loading?: boolean;
  children: ReactNode;
}

export function Button({ variant = "primary", loading, children, disabled, className, ...props }: ButtonProps) {
  return (
    <button
      className={cn("btn", `btn-${variant}`, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <CircleNotch size={17} className="animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

export function SectionHeading({ index, title, detail }: { index: string; title: string; detail?: string }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div className="flex items-baseline gap-3">
        <span className="mono text-[11px] text-tally">{index}</span>
        <h2 className="display text-xl uppercase tracking-[0.035em]">{title}</h2>
      </div>
      {detail && <span className="metadata text-right">{detail}</span>}
    </div>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return <p role="alert" className="border-l-2 border-tally pl-3 text-sm leading-6 text-[#f0a3a6]">{children}</p>;
}
