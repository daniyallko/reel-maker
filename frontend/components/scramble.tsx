"use client";

import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { useEffect, useState } from "react";

const CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+~|}{[]:;?><";
const randomCharacter = () => CHARACTERS[Math.floor(Math.random() * CHARACTERS.length)];

export function ScrambleIn({ text, delay, triggered }: { text: string; delay: number; triggered: boolean }) {
  const [display, setDisplay] = useState(" ");
  const reducedMotion = Boolean(useReducedMotion());

  useEffect(() => {
    if (reducedMotion) {
      setDisplay(text);
      return;
    }
    if (!triggered) {
      setDisplay(" ");
      return;
    }
    let interval: ReturnType<typeof setInterval> | undefined;
    const timeout = setTimeout(() => {
      let cursor = 0;
      interval = setInterval(() => {
        cursor += 0.5;
        const revealed = Math.floor(cursor);
        setDisplay(text.split("").map((character, index) => {
          if (character === " ") return " ";
          if (index < revealed) return character;
          if (index < revealed + 3) return randomCharacter();
          return "";
        }).join(""));
        if (revealed >= text.length) {
          if (interval) clearInterval(interval);
          setDisplay(text);
        }
      }, 25);
    }, delay);
    return () => {
      clearTimeout(timeout);
      if (interval) clearInterval(interval);
    };
  }, [delay, reducedMotion, text, triggered]);

  return <span aria-label={text}><span aria-hidden="true">{display}</span></span>;
}

export function ScrambleText({ text, isHovered, className }: { text: string; isHovered: boolean; className?: string }) {
  const [display, setDisplay] = useState(text);
  const reducedMotion = Boolean(useReducedMotion());

  useEffect(() => {
    if (!isHovered || reducedMotion) {
      setDisplay(text);
      return;
    }
    let frame = 0;
    const interval = setInterval(() => {
      frame += 1;
      const revealed = Math.floor(frame / 4);
      setDisplay(text.split("").map((character, index) => {
        if (character === " ") return " ";
        return index < revealed ? character : randomCharacter();
      }).join(""));
      if (revealed >= text.length) {
        clearInterval(interval);
        setDisplay(text);
      }
    }, 25);
    return () => clearInterval(interval);
  }, [isHovered, reducedMotion, text]);

  return <span className={className} aria-label={text}><span aria-hidden="true">{display}</span></span>;
}
