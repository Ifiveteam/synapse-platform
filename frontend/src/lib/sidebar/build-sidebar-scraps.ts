import type { ArchiverSessionSummary } from "@/api/archiver";
import type { ScrapItem } from "@/api/scraps";
import type { SidebarScrap } from "@/lib/sidebar/types";

function normalizeUrl(url: string | null | undefined): string {
  if (!url?.trim()) return "";
  try {
    const parsed = new URL(url.trim());
    const path = parsed.pathname.replace(/\/$/, "") || "/";
    return `${parsed.origin}${path}`.toLowerCase();
  } catch {
    return url.trim().toLowerCase().replace(/\/$/, "");
  }
}

function resolveArchiverSession(
  scrap: ScrapItem,
  sessions: ArchiverSessionSummary[],
): ArchiverSessionSummary | undefined {
  if (scrap.session_id) {
    const byId = sessions.find((s) => s.session_id === scrap.session_id);
    if (byId) return byId;
  }

  const scrapUrl = normalizeUrl(scrap.url);
  if (!scrapUrl) return undefined;

  return sessions.find((s) => normalizeUrl(s.context_url) === scrapUrl);
}

export function buildSidebarScraps(
  scraps: ScrapItem[],
  sessions: ArchiverSessionSummary[],
  formatRelativeTime: (iso: string) => string,
  limit = 3,
): SidebarScrap[] {
  const bySession = new Map<
    string,
    { scrap: ScrapItem; session: ArchiverSessionSummary }
  >();

  for (const scrap of scraps) {
    const session = resolveArchiverSession(scrap, sessions);
    if (!session) continue;

    const existing = bySession.get(session.session_id);
    if (
      !existing ||
      new Date(scrap.created_at).getTime() >
        new Date(existing.scrap.created_at).getTime()
    ) {
      bySession.set(session.session_id, { scrap, session });
    }
  }

  return [...bySession.values()]
    .sort(
      (a, b) =>
        new Date(b.scrap.created_at).getTime() -
        new Date(a.scrap.created_at).getTime(),
    )
    .slice(0, limit)
    .map(({ scrap, session }) => ({
      id: scrap.id,
      sessionId: session.session_id,
      title:
        scrap.title?.trim() ||
        session.context_title?.trim() ||
        "(제목 없음)",
      savedAt: formatRelativeTime(scrap.created_at),
    }));
}
