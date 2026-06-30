import { useEffect, useState } from "react";

import { fetchScrapDetail, type ScrapDetail, type ScrapItem } from "@/api/scraps";
import type { ArchiverChatMessage } from "@/api/archiver";

interface UseScrapDetailResult {
  scrap: ScrapItem | null;
  archiverSessionId: string | null;
  archiverHistory: ArchiverChatMessage[];
  loading: boolean;
  error: string | null;
}

export function useScrapDetail(scrapId: string | null): UseScrapDetailResult {
  const [detail, setDetail] = useState<ScrapDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scrapId) {
      setDetail(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchScrapDetail(scrapId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setDetail(null);
          setError(err instanceof Error ? err.message : "스크랩을 불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [scrapId]);

  return {
    scrap: detail?.scrap ?? null,
    archiverSessionId: detail?.archiver_session_id ?? null,
    archiverHistory: detail?.archiver_history ?? [],
    loading,
    error,
  };
}
