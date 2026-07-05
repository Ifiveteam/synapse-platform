import { apiFetchAuth } from "@/api/client";
import type {
  ActiveProposalResponse,
  AxisScores8,
  AxisScores13,
  NavigatorChatMessage,
  PlaylistPeriod,
  ChatStreamHandlers,
  ComparisonResponse,
  CompleteEvent,
  GuideResponse,
  IdealEvent,
  IdealResponse,
  IdealType,
  PlaylistChatHandlers,
  PlaylistResponse,
  PlaylistSummary,
  ProposalsResponse,
  SaveStartResponse,
} from "@/api/types/navigator";
import { API_BASE_URL } from "@/lib/env";

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
  target_disposition?: Record<string, number>;
  target_interest?: Record<string, number>;
  persona_label?: string;
  reasoning: string;
  taste_keywords?: string[];
  source_profile_history_id?: string;
}) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const listIdeals = () => apiFetchAuth<IdealResponse[]>(`${P}/ideals`);

/** 진행 중(추천 생성 중)인 이상향 설계 여부 — 관리 배너용 */
export const getActiveProposal = () =>
  apiFetchAuth<ActiveProposalResponse>(`${P}/proposals/active`);

/** 설계 대화 이력 — '이어서 설계하기'로 돌아왔을 때 복원용 */
export const getChatHistory = (sessionId: string) =>
  apiFetchAuth<NavigatorChatMessage[]>(
    `${P}/chat/history?session_id=${encodeURIComponent(sessionId)}`,
  );

export const getIdeal = (id: string) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal/${id}`);

export const applyIdeal = (id: string) =>
  apiFetchAuth<IdealResponse>(`${P}/ideal/${id}/apply`, { method: "POST" });

export const deleteIdeal = (id: string) =>
  apiFetchAuth<void>(`${P}/ideal/${id}`, { method: "DELETE" });

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
export const createPlaylist = (
  idealId: string,
  refreshPeriod: PlaylistPeriod = "none",
) =>
  apiFetchAuth<PlaylistResponse>(`${P}/ideal/${idealId}/playlists`, {
    method: "POST",
    body: JSON.stringify({ refresh_period: refreshPeriod }),
  });

export const setPlaylistPeriod = (
  playlistId: string,
  refreshPeriod: PlaylistPeriod,
) =>
  apiFetchAuth<PlaylistResponse>(`${P}/playlists/${playlistId}/period`, {
    method: "PATCH",
    body: JSON.stringify({ refresh_period: refreshPeriod }),
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

export const savePlaylistToYoutube = (playlistId: string) =>
  apiFetchAuth<SaveStartResponse>(`${P}/playlists/${playlistId}/save`, {
    method: "POST",
  });

export async function streamPlaylistChat(
  playlistId: string,
  message: string,
  handlers: PlaylistChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}${P}/playlists/${playlistId}/chat`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
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
    working_disposition?: Record<string, number> | null;
    working_interest?: Record<string, number> | null;
    ideal_type?: IdealType | null;
    force_finalize?: boolean;
  },
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}${P}/chat/stream`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
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
        } else if (event === "complete") {
          try {
            handlers.onComplete?.(JSON.parse(content) as CompleteEvent);
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
}
