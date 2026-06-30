import { apiFetchAuth } from "@/api/client";
import type {
  AxisScores8,
  AxisScores13,
  ChatStreamHandlers,
  ComparisonResponse,
  GuideResponse,
  IdealEvent,
  IdealResponse,
  IdealType,
  PlaylistChatHandlers,
  PlaylistResponse,
  PlaylistSummary,
  ProposalsResponse,
} from "@/api/types/navigator";
import { API_BASE_URL } from "@/lib/env";
import { useAuthStore } from "@/stores/auth";

// ── REST ─────────────────────────────────────────────────────────
const P = "/api/v1/navigator";

export const getProposals = (sourceProfileHistoryId?: string, refresh = false) => {
  const params = new URLSearchParams();
  if (sourceProfileHistoryId)
    params.set("source_profile_history_id", sourceProfileHistoryId);
  if (refresh) params.set("refresh", "true");
  const qs = params.toString();
  return apiFetchAuth<ProposalsResponse>(`${P}/proposals${qs ? `?${qs}` : ""}`);
};

export const createIdeal = (body: {
  ideal_type: IdealType;
  scores: AxisScores8;
  values_temperament?: AxisScores13;
  persona_label?: string;
  reasoning: string;
  source_profile_history_id?: string;
}) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const listIdeals = () => apiFetchAuth<IdealResponse[]>(`${P}/ideals`);

export const getIdeal = (id: string) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal/${id}`);

export const applyIdeal = (id: string) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal/${id}/apply`, { method: "POST" });

export const getComparison = (id: string) =>
  apiFetchAuth<ComparisonResponse>(`${P}/ideal/${id}/comparison`);

export const getGuide = (id: string, refresh = false) =>
  apiFetchAuth<GuideResponse>(
    `${P}/ideal/${id}/guide${refresh ? "?refresh=true" : ""}`,
  );

const BEHAVIOR_KEYS = [
  "exploration",
  "analytical",
  "creativity",
  "execution",
  "achievement_drive",
  "autonomy",
  "sociality",
  "sensitivity",
];

/** 현재 프로필의 행동 8축 (스냅샷 지정 시 그 분석, 없으면 최신) */
export async function getCurrentAxes(
  snapshotId?: string,
): Promise<AxisScores8> {
  const path = snapshotId
    ? `/api/v1/profiler/me/analyses/${encodeURIComponent(snapshotId)}`
    : `/api/v1/profiler/me/profile`;
  const d = await apiFetchAuth<{ scores: Record<string, number> }>(path);
  const s = d.scores ?? {};
  return Object.fromEntries(BEHAVIOR_KEYS.map((k) => [k, s[k] ?? 0]));
}

// ── 재생목록 ───────────────────────────────────────────────────────
export const createPlaylist = (idealId: string) =>
  apiFetchAuth<PlaylistResponse>(`${P}/ideal/${idealId}/playlists`, {
    method: "POST",
  });

export const listPlaylists = (idealId: string) =>
  apiFetchAuth<PlaylistSummary[]>(`${P}/ideal/${idealId}/playlists`);

export const getPlaylist = (playlistId: string) =>
  apiFetchAuth<PlaylistResponse>(`${P}/playlists/${playlistId}`);

export const renamePlaylist = (playlistId: string, title: string) =>
  apiFetchAuth<PlaylistResponse>(`${P}/playlists/${playlistId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

export const deletePlaylist = (playlistId: string) =>
  apiFetchAuth<void>(`${P}/playlists/${playlistId}`, { method: "DELETE" });

export const refreshPlaylistItem = (playlistId: string, videoId: string) =>
  apiFetchAuth<PlaylistResponse>(`${P}/playlists/${playlistId}/item/refresh`, {
    method: "POST",
    body: JSON.stringify({ video_id: videoId }),
  });

export const regeneratePlaylist = (playlistId: string) =>
  apiFetchAuth<PlaylistResponse>(`${P}/playlists/${playlistId}/regenerate`, {
    method: "POST",
  });

export async function streamPlaylistChat(
  playlistId: string,
  message: string,
  handlers: PlaylistChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = useAuthStore.getState().token;
  const res = await fetch(`${API_BASE_URL}${P}/playlists/${playlistId}/chat`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`playlist chat stream failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const raw of lines) {
      const line = raw.replace(/\r$/, "");
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        let content = "";
        try {
          content = (JSON.parse(payload) as { content?: string }).content ?? "";
        } catch {
          content = payload;
        }
        if (event === "status") handlers.onStatus?.(content);
        else if (event === "playlist") {
          try {
            handlers.onPlaylist?.(JSON.parse(content) as PlaylistResponse);
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
}

// ── 챗 SSE ───────────────────────────────────────────────────────
export async function streamChat(
  body: {
    message: string;
    session_id?: string | null;
    working_values?: AxisScores13 | null;
    ideal_type?: IdealType | null;
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const token = useAuthStore.getState().token;
  const res = await fetch(`${API_BASE_URL}${P}/chat/stream`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    throw new Error(`chat stream failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const raw of lines) {
      const line = raw.replace(/\r$/, "");
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        let content = "";
        try {
          content = (JSON.parse(payload) as { content?: string }).content ?? "";
        } catch {
          content = payload;
        }
        if (event === "status") handlers.onStatus?.(content);
        else if (event === "token") handlers.onToken?.(content);
        else if (event === "ideal") {
          try {
            handlers.onIdeal?.(JSON.parse(content) as IdealEvent);
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
}
