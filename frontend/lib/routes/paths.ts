import type { AgentId } from "@/lib/agents";

export const ROUTES = {
  home: "/",
  agentDetail: (slug: AgentId | string) => `/agents/${slug}`,
} as const;
