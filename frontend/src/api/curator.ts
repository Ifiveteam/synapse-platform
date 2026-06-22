import { API_BASE_URL } from "@/lib/env";
import { useAuthStore } from "@/stores/auth";

export interface CuratorSSEEvent {
  event: "token" | "status";
  content: string;
}

export async function* streamCurator(
  message: string,
  sessionId?: string,
): AsyncGenerator<CuratorSSEEvent> {
  const token = useAuthStore.getState().token;

  const response = await fetch(`${API_BASE_URL}/api/v1/curator/stream`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
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
        if (ev === "status" || ev === "token") currentEvent = ev;
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
