"use client";

import { motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";

const FEATURES = [
  ["Local filtering", "Burst dedupe, blur rejection, and video keyframes before any model call."],
  ["Multimodal perception", "Photos, clips, voice notes, and inside jokes become one structured memory."],
  ["Structured screenplay", "A strict three-act EDL assigns every shot, title card, and narration cue."],
  ["FFmpeg finish", "Ken Burns motion, beat flashes, ducked audio, and a vertical theatrical export."],
];
const LAYERS = [["Layer 1", "Perception"], ["Layer 2", "Screenplay"], ["Layer 3", "Render"]];

export function PipelineArchitecture() {
  const reducedMotion = Boolean(useReducedMotion());
  return (
    <>
      <section className="flex min-h-screen flex-col px-6 py-24 sm:px-12 md:px-16" aria-labelledby="technology-title">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <motion.h2
            id="technology-title"
            className="text-[clamp(36px,8vw,72px)] font-light leading-[0.95] tracking-[-0.03em]"
            initial={reducedMotion ? false : { opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: reducedMotion ? 0 : 1 }}
          >
            Adaptive<br />intelligence
          </motion.h2>
          <motion.p
            className="max-w-xs text-sm leading-relaxed text-white/55 md:pt-2 md:text-right"
            initial={reducedMotion ? false : { opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: reducedMotion ? 0 : 1, delay: reducedMotion ? 0 : 0.2 }}
          >
            The agents learn the shape of your weekend from the evidence. From there, every frame, joke, and musical cue is mapped into one coherent trailer.
          </motion.p>
        </div>
        <div className="flex-1" />
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4 md:gap-6">
          {FEATURES.map(([title, description], index) => (
            <motion.div
              key={title}
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: reducedMotion ? 0 : 0.7, delay: reducedMotion ? 0 : index * 0.1 }}
            >
              <h3 className="mb-2 text-sm font-normal sm:text-base">{title}</h3>
              <p className="text-xs leading-relaxed text-white/45 sm:text-sm">{description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto min-h-screen max-w-3xl px-6 py-32 text-center" aria-labelledby="architecture-title">
        <motion.div
          initial={reducedMotion ? false : { opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: reducedMotion ? 0 : 1 }}
        >
          <p className="mb-8 text-sm uppercase tracking-[0.2em] text-white/45">Architecture</p>
          <h2 id="architecture-title" className="mb-10 text-[clamp(28px,6vw,56px)] font-light leading-[1.15] tracking-[-0.02em]">Three layers. Zero friction.</h2>
          <p className="mx-auto max-w-xl text-base leading-relaxed text-white/50">Source media becomes structured memory. Memory becomes a timed screenplay. The screenplay becomes a trailer, poster, and cast press kit.</p>
        </motion.div>
        <div className="mt-20 flex flex-col items-center gap-4">
          {LAYERS.map(([layer, name], index) => (
            <motion.div
              key={layer}
              className="flex h-[72px] w-full max-w-md items-center justify-between rounded-lg border border-white/10 px-6"
              initial={reducedMotion ? false : { opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: reducedMotion ? 0 : 0.8, delay: reducedMotion ? 0 : 0.2 + index * 0.12 }}
            >
              <span className="text-xs uppercase tracking-[0.15em] text-white/45">{layer}</span>
              <span className="text-lg font-light">{name}</span>
            </motion.div>
          ))}
        </div>
      </section>
    </>
  );
}
