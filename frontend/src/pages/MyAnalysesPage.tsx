import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Loader2,
  Plus,
} from "lucide-react";

import { fetchMyAnalyses } from "@/api/analyses";
import { ApiError } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ANALYSIS_PAGE_SIZE,
  isAnalysisPending,
  type AnalysisResultItem,
} from "@/lib/analyses/types";
import { ROUTES } from "@/routes";

type FilterTab = "all" | "completed" | "pending";

function AnalysisListItem({ item }: { item: AnalysisResultItem }) {
  const pending = isAnalysisPending(item.status);
  const content = (
    <>
      <div className="bg-accent text-accent-foreground flex h-11 w-11 shrink-0 items-center justify-center rounded-full">
        <CircleDot size={20} />
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{item.title}</p>
        <p className="text-muted-foreground mt-0.5 text-xs">{item.date}</p>
      </div>

      <Badge
        variant={pending ? "orange" : "secondary"}
        className="shrink-0"
      >
        {pending ? (item.status === "running" ? "분석 중" : "미완료") : "완료"}
      </Badge>

      {!pending && (
        <ChevronRight size={18} className="text-muted-foreground shrink-0" />
      )}
    </>
  );

  if (pending) {
    return (
      <div className="border-border flex items-center gap-4 rounded-2xl border bg-card px-4 py-4 opacity-90">
        {content}
      </div>
    );
  }

  return (
    <Link
      to={ROUTES.analysisDetail(item.id)}
      className="border-border hover:bg-secondary/60 flex items-center gap-4 rounded-2xl border bg-card px-4 py-4 transition-colors"
    >
      {content}
    </Link>
  );
}

export function MyAnalysesPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<AnalysisResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await fetchMyAnalyses();
        if (!cancelled) setItems(list);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "분석 목록을 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    if (filter === "completed") {
      return items.filter((item) => item.status === "completed");
    }
    return items.filter((item) => isAnalysisPending(item.status));
  }, [filter, items]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ANALYSIS_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filtered.slice(
    (currentPage - 1) * ANALYSIS_PAGE_SIZE,
    currentPage * ANALYSIS_PAGE_SIZE,
  );

  const handleFilterChange = (value: string) => {
    setFilter(value as FilterTab);
    setPage(1);
  };

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              개인성향 분석 목록
            </h1>
            <span className="text-muted-foreground text-sm">최신순 정렬</span>
          </div>

          <Tabs
            value={filter}
            onValueChange={handleFilterChange}
            className="mt-4 gap-0"
          >
            <TabsList className="h-9 bg-transparent p-0">
              <TabsTrigger value="all" className="px-4 shadow-none">
                전체
              </TabsTrigger>
              <TabsTrigger value="completed" className="px-4 shadow-none">
                완료
              </TabsTrigger>
              <TabsTrigger value="pending" className="px-4 shadow-none">
                미완료
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <Button size="sm" className="shrink-0 gap-1.5" asChild>
          <Link to={ROUTES.upload}>
            <Plus size={16} />
            새로 추가
          </Link>
        </Button>
      </div>

      {loading && (
        <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 py-16 text-sm">
          <Loader2 className="size-4 animate-spin" />
          목록 불러오는 중…
        </div>
      )}

      {!loading && error && (
        <div className="border-border text-destructive rounded-2xl border border-dashed px-6 py-16 text-center text-sm">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="flex flex-1 flex-col gap-3">
          {pageItems.length > 0 ? (
            pageItems.map((item) => (
              <AnalysisListItem key={item.id} item={item} />
            ))
          ) : (
            <div className="border-border text-muted-foreground rounded-2xl border border-dashed px-6 py-16 text-center text-sm">
              {items.length === 0
                ? "아직 분석 결과가 없습니다. 시청 기록을 업로드한 뒤 프로파일러가 완료되면 여기에 표시됩니다."
                : "해당하는 분석 결과가 없습니다."}
            </div>
          )}
        </div>
      )}

      {!loading && !error && totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8"
            disabled={currentPage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft size={16} />
          </Button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
            <Button
              key={n}
              type="button"
              variant={n === currentPage ? "default" : "outline"}
              size="icon"
              className="size-8 text-xs"
              onClick={() => setPage(n)}
            >
              {n}
            </Button>
          ))}

          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            <ChevronRight size={16} />
          </Button>
        </div>
      )}
    </div>
  );
}
