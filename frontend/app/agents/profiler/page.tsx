import type { Metadata } from "next";

import { ProfilerPage } from "@/components/agents/profiler/profiler-page";

export const metadata: Metadata = {
  title: "Profiler | Synapse Platform",
  description:
    "데이터라는 거울을 통해 사용자의 현재 상태와 성향을 있는 그대로 비춰주는 분석가",
};

export default function ProfilerAgentPage() {
  return <ProfilerPage />;
}
