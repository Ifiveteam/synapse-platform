import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Plus,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ANALYSIS_PAGE_SIZE,
  MOCK_ANALYSIS_RESULTS,
  type AnalysisResultItem,
  type AnalysisStatus,
} from "@/lib/analyses/mock";
import { ROUTES } from "@/routes";

type FilterTab = "all" | AnalysisStatus;

function AnalysisListItem({ item }: { item: AnalysisResultItem }) {
  return (
    <Link
      to={ROUTES.analysisDetail(item.id)}
      className="border-border hover:bg-secondary/60 flex items-center gap-4 rounded-2xl border bg-card px-4 py-4 transition-colors"
    >
      <div className="bg-accent text-accent-foreground flex h-11 w-11 shrink-0 items-center justify-center rounded-full">
        <CircleDot size={20} />
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{item.title}</p>
        <p className="text-muted-foreground mt-0.5 text-xs">{item.date}</p>
      </div>

      <Badge
        variant={item.status === "completed" ? "secondary" : "orange"}
        className="shrink-0"
      >
        {item.status === "completed" ? "완료" : "미완료"}
      </Badge>

      <ChevronRight size={18} className="text-muted-foreground shrink-0" />
    </Link>
  );
}

export function MyAnalysesPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (filter === "all") return MOCK_ANALYSIS_RESULTS;
    return MOCK_ANALYSIS_RESULTS.filter((item) => item.status === filter);
  }, [filter]);

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

      <div className="flex flex-1 flex-col gap-3">
        {pageItems.length > 0 ? (
          pageItems.map((item) => (
            <AnalysisListItem key={item.id} item={item} />
          ))
        ) : (
          <div className="border-border text-muted-foreground rounded-2xl border border-dashed px-6 py-16 text-center text-sm">
            해당하는 분석 결과가 없습니다.
          </div>
        )}
      </div>

      {totalPages > 1 && (
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
