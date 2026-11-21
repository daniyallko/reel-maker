"use client";

import { AnimatePresence, motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { StudioPremiere } from "./studio-premiere";
import { StudioScreening } from "./studio-screening";
import { useProjectEvents } from "@/lib/use-project-events";

export function ProjectView({ id }: { id: string }) {
  const { snapshot, error, connection, retry } = useProjectEvents(id);
  const reduceMotion = Boolean(useReducedMotion());

  return (
    <div className="min-h-dvh">
      <AnimatePresence mode="wait">
        <motion.main
          id="main-content"
          key={snapshot?.output ? "premiere" : "screening"}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
          transition={{ duration: reduceMotion ? 0 : 0.32 }}
        >
          {snapshot?.output && snapshot.status === "complete" ? (
            <StudioPremiere output={snapshot.output} sourceUrl={snapshot.source_url} />
          ) : (
            <StudioScreening project={snapshot} error={error} connection={connection} onRetry={retry} />
          )}
        </motion.main>
      </AnimatePresence>
    </div>
  );
}
