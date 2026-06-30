import { apiFetchAuth } from "@/api/client";

export interface ArchiverSessionSummary {
  session_id: string;
  context_title: string;
  context_url: string;
  last_activity: string;
}

export async function fetchArchiverSessions(): Promise<ArchiverSessionSummary[]> {
  const res = await apiFetchAuth<{
    status: string;
    data: ArchiverSessionSummary[];
  }>("/api/v1/archiver/sessions");
  return res.data;
}

export interface ArchiverChatMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export async function fetchArchiverHistory(
  sessionId: string,
): Promise<ArchiverChatMessage[]> {
  const res = await apiFetchAuth<{
    status: string;
    data: ArchiverChatMessage[];
  }>(`/api/v1/archiver/history/${encodeURIComponent(sessionId)}`);
  return res.data;
}
