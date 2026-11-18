"use client";

import { useRouter } from "next/navigation";
import { DirectorsSlate } from "@/components/directors-slate";

export default function Home() {
  const router = useRouter();
  return <DirectorsSlate onProjectCreated={(id) => router.push(`/project/${id}`)} />;
}
