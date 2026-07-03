import type { AgentId } from "@/lib/agents";

export const ROUTES = {
  ME: {
    HOME: "/me",
    ACTIVITY: "/me/activity",
  },
  home: "/",
  login: "/login",
  upload: "/upload",
  myAnalyses: "/me/analyses",
  analysisDetail: (id: string) => `/me/analyses/${id}`,
  analysisCompare: (fromId: string, toId: string) =>
    `/me/analyses/compare?from=${encodeURIComponent(fromId)}&to=${encodeURIComponent(toId)}`,
  idealManagement: "/me/ideals",
  idealSetup: "/me/ideals/new",
  idealDetail: (id: string) => `/me/ideals/${id}`,
  playlists: "/me/playlists",
  playlistsForIdeal: (id: string) => `/me/playlists?ideal=${id}`,
  trends: "/trends",
  scraps: "/me/scraps",
  scrapDetail: (id: string) => `/me/scraps/${id}`,
  settings: "/settings",
  download: "/download",
  agentDetail: (slug: AgentId | string) => `/agents/${slug}`,
  trendPosts: (slug: AgentId | string) => `/agents/${slug}/posts`,
  trendPost: (slug: AgentId | string, postId: string) =>
    `/agents/${slug}/posts/${postId}`,
  paymentSuccess: "/payment/success",
} as const;
