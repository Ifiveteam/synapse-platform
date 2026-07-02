import { apiFetchAuth } from "@/api/client";
import { API_BASE_URL } from "@/lib/env";
import { useAuthStore } from "@/stores/auth";

export interface CuratorSession {
  session_id: string;
  title: string;
  updated_at: string;
}

export async function fetchCuratorSessions(): Promise<CuratorSession[]> {
  const data = await apiFetchAuth<{ sessions: CuratorSession[] }>("/api/v1/curator/sessions");
  return data.sessions;
}

export interface CuratorMessageItem {
  role: "user" | "assistant";
  content: string;
}

export async function fetchSessionMessages(sessionId: string): Promise<CuratorMessageItem[]> {
  const data = await apiFetchAuth<{ messages: CuratorMessageItem[] }>(
    `/api/v1/curator/sessions/${sessionId}/messages`,
  );
  return data.messages;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetchAuth(`/api/v1/curator/sessions/${sessionId}`, { method: "DELETE" });
}

export interface CuratorSSEEvent {
  event: "token" | "status" | "chart";
  content: string;
}

export async function* streamCurator(
  message: string,
  sessionId?: string,
  imageBase64?: string,
  imageMimeType?: string,
): AsyncGenerator<CuratorSSEEvent> {
  const token = useAuthStore.getState().token;

  const response = await fetch(`${API_BASE_URL}/api/v1/curator/stream`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      image_base64: imageBase64,
      image_mime_type: imageMimeType,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Curator error: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    let currentEvent: "token" | "status" = "token";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        const ev = line.slice(7).trim();
        if (ev === "status" || ev === "token" || ev === "chart") currentEvent = ev as typeof currentEvent;
      } else if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6)) as { content: string };
          if (data.content) yield { event: currentEvent, content: data.content };
        } catch {
          // ignore malformed lines
        }
      }
    }
  }
}
