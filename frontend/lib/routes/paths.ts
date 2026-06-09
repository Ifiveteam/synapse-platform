import type { AgentId } from "@/lib/agents";

export const ROUTES = {
  home: "/",
  agentDetail: (slug: AgentId | string) => `/agents/${slug}`,
  trendPosts: (slug: AgentId | string) => `/agents/${slug}/posts`,
  trendPost: (slug: AgentId | string, postId: string) =>
    `/agents/${slug}/posts/${postId}`,
} as const;
