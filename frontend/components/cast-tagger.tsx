"use client";

import { Plus, X } from "@phosphor-icons/react";
import { useState } from "react";

export function CastTagger({ value, onChange }: { value: string[]; onChange: (names: string[]) => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  function add() {
    const clean = name.trim().replace(/,$/, "");
    if (!clean) return;
    if (value.some((item) => item.toLowerCase() === clean.toLowerCase())) {
      setError("That cast member is already on the call sheet.");
      return;
    }
    if (value.length >= 12) {
      setError("The billing block is full at 12 names.");
      return;
    }
    onChange([...value, clean]);
    setName("");
    setError("");
  }

  return (
    <div>
      <label htmlFor="cast-name" className="mb-2 block text-sm text-paper">Cast list</label>
      <div className="flex gap-2">
        <input
          id="cast-name"
          className="field"
          value={name}
          onChange={(event) => { setName(event.target.value); setError(""); }}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              add();
            }
          }}
          placeholder="Friend's name"
          maxLength={36}
          aria-describedby={error ? "cast-error" : "cast-hint"}
        />
        <button type="button" className="btn btn-secondary w-12 shrink-0 px-0" onClick={add} aria-label="Add cast member">
          <Plus size={19} aria-hidden="true" />
        </button>
      </div>
      <p id={error ? "cast-error" : "cast-hint"} className={error ? "mt-2 text-xs text-[#f0a3a6]" : "metadata mt-2"} role={error ? "alert" : undefined}>
        {error || "Press Enter after each name. They get a role and a freeze frame."}
      </p>
      {value.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Current cast">
          {value.map((castMember) => (
            <li key={castMember} className="flex min-h-9 items-center gap-2 border border-hairline bg-surface-raised pl-3">
              <span className="text-sm">{castMember}</span>
              <button
                type="button"
                className="flex size-11 items-center justify-center text-muted hover:text-paper"
                onClick={() => onChange(value.filter((name) => name !== castMember))}
                aria-label={`Remove ${castMember}`}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
