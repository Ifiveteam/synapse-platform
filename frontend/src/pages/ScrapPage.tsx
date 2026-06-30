import { useCallback, useEffect, useMemo, useState } from "react";
import { Bookmark, Loader2 } from "lucide-react";

import {
  fetchScrapGraph,
  fetchScraps,
  type ScrapGraphData,
  type ScrapGraphNode,
  type ScrapItem,
} from "@/api/scraps";
import {
  DEFAULT_MIN_SIMILARITY,
  ScrapEmbeddingGraph,
} from "@/components/scraps/scrap-embedding-graph";
import { Badge } from "@/components/ui/badge";
import { useScrapDetailPanelStore } from "@/stores/scrap-detail-panel";
import { useSidebarStore } from "@/stores/sidebar";
import { cn } from "@/lib/utils";

function formatSavedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function ScrapListPanel({
  items,
  loading,
  highlightedId,
  selectedId,
  onSelect,
}: {
  items: ScrapItem[];
  loading: boolean;
  highlightedId: string | null;
  selectedId: string | null;
  onSelect: (scrapId: string) => void;
}) {
  if (loading) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 text-sm">
        <Loader2 className="size-4 animate-spin" />
        스크랩 목록 불러오는 중…
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-muted-foreground flex flex-1 items-center justify-center p-6 text-center text-sm">
        저장된 스크랩이 없습니다.
        <br />
        익스텐션에서 페이지를 스크랩해 보세요.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onSelect(item.id)}
          className={cn(
            "border-border hover:bg-secondary/50 flex w-full flex-col gap-2 rounded-xl border bg-card px-4 py-3 text-left transition-colors",
            (highlightedId === item.id || selectedId === item.id) &&
              "border-primary/50 bg-primary/5 ring-1 ring-primary/20",
          )}
        >
          <div className="flex items-start gap-3">
            <div className="bg-accent text-accent-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
              <Bookmark size={16} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-sm font-medium leading-snug">
                {item.title?.trim() || "(제목 없음)"}
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                {item.category} · {formatSavedAt(item.created_at)}
              </p>
            </div>
          </div>
          <p className="text-muted-foreground line-clamp-2 pl-12 text-xs leading-relaxed">
            {item.summary}
          </p>
          {item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pl-12">
              {item.tags.slice(0, 4).map((tag) => (
                <Badge key={tag} variant="secondary" className="px-1.5 py-0 text-[10px]">
                  #{tag}
                </Badge>
              ))}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}

export function ScrapPage() {
  const loadSidebarScraps = useSidebarStore((s) => s.loadScraps);
  const [scraps, setScraps] = useState<ScrapItem[]>([]);
  const [graphData, setGraphData] = useState<ScrapGraphData | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [graphLoading, setGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [minSimilarity, setMinSimilarity] = useState(DEFAULT_MIN_SIMILARITY);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const openScrapPanel = useScrapDetailPanelStore((s) => s.openScrapPanel);
  const selectedScrapId = useScrapDetailPanelStore((s) => s.selectedScrapId);

  const allNodesForFilters: ScrapGraphNode[] = useMemo(
    () =>
      scraps.map((item) => ({
        id: item.id,
        title: item.title,
        category: item.category,
        tags: item.tags,
      })),
    [scraps],
  );

  const loadList = useCallback(async () => {
    setListLoading(true);
    try {
      const data = await fetchScraps();
      setScraps(data);
    } catch {
      setScraps([]);
    } finally {
      setListLoading(false);
    }
  }, []);

  const loadGraph = useCallback(async () => {
    setGraphLoading(true);
    setGraphError(null);
    try {
      const data = await fetchScrapGraph({
        categories: selectedCategories.length ? selectedCategories : undefined,
        tags: selectedTags.length ? selectedTags : undefined,
      });
      setGraphData(data);
    } catch (err) {
      setGraphData(null);
      setGraphError(err instanceof Error ? err.message : "그래프를 불러오지 못했습니다.");
    } finally {
      setGraphLoading(false);
    }
  }, [selectedCategories, selectedTags]);

  useEffect(() => {
    void loadList();
    void loadSidebarScraps();
  }, [loadList, loadSidebarScraps]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  const filteredList = useMemo(() => {
    return scraps.filter((item) => {
      if (
        selectedCategories.length > 0 &&
        !selectedCategories.includes(item.category)
      ) {
        return false;
      }
      if (selectedTags.length > 0) {
        const tagSet = new Set(item.tags);
        if (!selectedTags.some((tag) => tagSet.has(tag))) return false;
      }
      return true;
    });
  }, [scraps, selectedCategories, selectedTags]);

  return (
    <div className="flex h-full min-h-0 flex-col px-4 py-5 sm:px-6 sm:py-6">
      <header className="mb-4 shrink-0">
        <h1 className="text-xl font-semibold tracking-tight">스크랩 대시보드</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          임베딩 기반 의미 그래프로 스크랩 간 연관성을 탐색하세요.
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-5 lg:gap-5">
        <section className="flex min-h-[min(560px,72vh)] flex-col lg:col-span-3">
          {graphError ? (
            <div className="border-border text-destructive flex flex-1 items-center justify-center rounded-2xl border bg-card p-6 text-sm">
              {graphError}
            </div>
          ) : (
            <ScrapEmbeddingGraph
              className="h-full"
              data={graphData}
              allNodesForFilters={allNodesForFilters}
              loading={graphLoading}
              selectedCategories={selectedCategories}
              selectedTags={selectedTags}
              onCategoriesChange={setSelectedCategories}
              onTagsChange={setSelectedTags}
              minSimilarity={minSimilarity}
              onMinSimilarityChange={setMinSimilarity}
              onNodeHover={setHoveredNodeId}
              onNodeClick={openScrapPanel}
            />
          )}
        </section>

        <aside className="border-border flex min-h-[320px] flex-col rounded-2xl border bg-card lg:col-span-2">
          <div className="border-border shrink-0 border-b px-4 py-3">
            <h2 className="text-sm font-semibold">스크랩 목록</h2>
            <p className="text-muted-foreground mt-0.5 text-xs">
              {filteredList.length}건
              {(selectedCategories.length > 0 || selectedTags.length > 0) && " (필터 적용)"}
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col p-3">
            <ScrapListPanel
              items={filteredList}
              loading={listLoading}
              highlightedId={hoveredNodeId}
              selectedId={selectedScrapId}
              onSelect={openScrapPanel}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}
