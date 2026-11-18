"use client";

import { AnimatePresence, motion } from "motion/react";
import { useMotionPreference as useReducedMotion } from "@/lib/use-motion-preference";
import { AppHeader } from "./app-header";
import { Premiere } from "./premiere";
import { ScreeningRoom } from "./screening-room";
import { useProjectEvents } from "@/lib/use-project-events";

export function ProjectView({ id }: { id: string }) {
  const { snapshot, error, connection, retry } = useProjectEvents(id);
  const reduceMotion = Boolean(useReducedMotion());
  const status = snapshot?.status === "complete" ? "PREMIERE" : "SCREENING ROOM";

  return (
    <div className="min-h-dvh">
      <AppHeader
        projectId={id}
        status={status}
        navItems={snapshot?.output ? [{ label: "Press kit", target: "press-kit" }, { label: "Cast", target: "cast" }] : [{ label: "Agents", target: "agents" }, { label: "Dailies", target: "dailies" }]}
      />
      <AnimatePresence mode="wait">
        <motion.main
          id="main-content"
          key={snapshot?.output ? "premiere" : "screening"}
          layoutId="workspace"
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
          transition={{ duration: reduceMotion ? 0 : 0.32 }}
        >
          {snapshot?.output && snapshot.status === "complete" ? (
            <Premiere project={snapshot} />
          ) : (
            <ScreeningRoom project={snapshot} error={error} connection={connection} onRetry={retry} />
          )}
        </motion.main>
      </AnimatePresence>
    </div>
  );
}
