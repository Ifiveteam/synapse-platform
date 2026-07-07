import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeftRight,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";

import {
  deleteMyAnalysis,
  deleteMyAnalysisBatch,
  deleteMyAnalysisSource,
} from "@/api/analyses";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ANALYSIS_PAGE_SIZE,
  isAnalysisPending,
  type AnalysisResultItem,
} from "@/lib/analyses/types";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { useSidebarStore } from "@/stores/sidebar";

function AnalysisListItem({
  item,
  onDelete,
}: {
  item: AnalysisResultItem;
  onDelete?: (item: AnalysisResultItem) => void;
}) {
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

      <Badge variant={pending ? "orange" : "secondary"} className="shrink-0">
        {pending
          ? item.status === "pending"
            ? "대기 중"
            : item.stage === "indexing"
              ? "분류 중"
              : "분석 중"
          : "완료"}
      </Badge>

      {onDelete && !pending && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(item);
          }}
          className="text-muted-foreground hover:text-destructive shrink-0 rounded-full p-1 transition-colors"
          aria-label="삭제"
        >
          <Trash2 size={16} />
        </button>
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

/** 진행 중인 배치(같이 올린 파일들)를 한 박스로 — 파일별 상태 + 박스 레벨 단계. */
function InProgressGroup({
  items,
  onDelete,
}: {
  items: AnalysisResultItem[];
  onDelete?: (items: AnalysisResultItem[]) => void;
}) {
  const isProfiling = items.some((it) => it.stage === "profiling");
  const fileBadge = (it: AnalysisResultItem): string => {
    if (isProfiling) return "분류 완료";
    if (it.status === "pending") return "대기 중";
    if (it.stage === "indexing") return "분류 중";
    return "분류 완료";
  };

  return (
    <div className="border-border rounded-2xl border bg-card px-4 py-4">
      <div className="flex items-center gap-4">
        <div className="bg-accent text-accent-foreground flex h-11 w-11 shrink-0 items-center justify-center rounded-full">
          <CircleDot size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">개인성향 분석</p>
          <p className="text-muted-foreground mt-0.5 text-xs">
            {isProfiling ? "분류 완료 · 분석 중" : `파일 ${items.length}개 처리 중`}
          </p>
        </div>
        <Badge variant="orange" className="shrink-0 gap-1">
          {isProfiling && <Loader2 className="size-3 animate-spin" />}
          {isProfiling ? "분석 중" : "진행 중"}
        </Badge>
        {onDelete && (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDelete(items);
            }}
            className="text-muted-foreground hover:text-destructive shrink-0 rounded-full p-1 transition-colors"
            aria-label="삭제"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>
      <div className="border-border mt-3 space-y-1.5 border-t pt-3">
        {items.map((it) => (
          <div key={it.id} className="flex items-center gap-2 pl-1">
            <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs">
              {it.fileName ?? "파일"}
            </span>
            <Badge variant="secondary" className="shrink-0 text-[10px]">
              {fileBadge(it)}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

/** 비교할 완료 분석 2개를 고르는 팝업. 같은 항목 중복 선택 불가, 정확히 2개만. */
function CompareModal({
  items,
  selectedIds,
  onToggle,
  onClose,
  onConfirm,
}: {
  items: AnalysisResultItem[];
  selectedIds: string[];
  onToggle: (id: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="border-border bg-card relative z-10 flex max-h-[80vh] w-full max-w-md flex-col rounded-2xl border p-5 shadow-xl">
        <div className="mb-1 flex items-center justify-between">
          <h3 className="text-base font-semibold">비교분석</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="닫기"
          >
            <X size={18} />
          </button>
        </div>
        <p className="text-muted-foreground mb-4 text-sm">
          비교할 완료 분석 2개를 선택하세요. ({selectedIds.length}/2)
        </p>

        <ul className="-mx-1 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-1">
          {items.map((item) => {
            const selected = selectedIds.includes(item.id);
            const disabled = !selected && selectedIds.length >= 2;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onToggle(item.id)}
                  className={cn(
                    "border-border flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors",
                    selected && "border-primary ring-primary/20 ring-2",
                    !disabled && "hover:bg-secondary/60",
                    disabled && "cursor-not-allowed opacity-50",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                      selected
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-muted-foreground/40 bg-background",
                    )}
                  >
                    {selected && <Check size={14} strokeWidth={3} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{item.title}</p>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {item.date}
                    </p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>

        <Button
          onClick={onConfirm}
          disabled={selectedIds.length !== 2}
          className="mt-4 shrink-0"
        >
          비교 보기
        </Button>
      </div>
    </div>
  );
}

export function MyAnalysesPage() {
  const navigate = useNavigate();
  const items = useSidebarStore((s) => s.analyses);
  const loadAnalyses = useSidebarStore((s) => s.loadAnalyses);
  const removeAnalysis = useSidebarStore((s) => s.removeAnalysis);
  const refreshAnalyses = useSidebarStore((s) => s.refreshAnalyses);
  const [page, setPage] = useState(1);
  // 캐시된 목록이 있으면 스피너 없이 바로 표시(백그라운드 갱신)
  const [loading, setLoading] = useState(items.length === 0);
  const [error, setError] = useState<string | null>(null);
  const [showCompare, setShowCompare] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<AnalysisResultItem | null>(
    null,
  );
  // 진행중(배치/소스) 삭제 대상 — 그룹 items
  const [deleteJob, setDeleteJob] = useState<AnalysisResultItem[] | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteMyAnalysis(deleteTarget.id);
      removeAnalysis(deleteTarget.id);
      setDeleteTarget(null);
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!deleteJob || deleteJob.length === 0) return;
    setDeleting(true);
    try {
      const batchId = deleteJob[0].batchId;
      if (batchId) await deleteMyAnalysisBatch(batchId);
      else await deleteMyAnalysisSource(deleteJob[0].id);
      await refreshAnalyses(); // 서버 기준 재동기화 (그룹 전체 반영)
      setDeleteJob(null);
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  const completedItems = useMemo(
    () => items.filter((item) => item.status === "completed"),
    [items],
  );
  const canCompare = completedItems.length >= 2;

  // 분석 목록 — 스토어 단일 소스(동시 호출 dedupe). 사이드바·허브와 공유.
  useEffect(() => {
    let cancelled = false;
    if (items.length === 0) setLoading(true); // 캐시 없을 때만 스피너
    setError(null);
    void loadAnalyses().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadAnalyses]);

  // 진행 중(job) 항목은 **배치별로** 그룹 박스 하나씩, 완료 스냅샷만 개별 + 페이지네이션
  const jobItems = useMemo(() => items.filter((i) => i.kind === "job"), [items]);
  const jobGroups = useMemo(() => {
    const map = new Map<string, AnalysisResultItem[]>();
    for (const it of jobItems) {
      // 배치가 다르면 다른 박스. batch_id 없으면(구/자동 단일) 각자 독립 박스.
      const key = it.batchId ?? `solo:${it.id}`;
      const arr = map.get(key);
      if (arr) arr.push(it);
      else map.set(key, [it]);
    }
    return Array.from(map.values());
  }, [jobItems]);
  const snapshotItems = useMemo(
    () => items.filter((i) => i.kind === "snapshot"),
    [items],
  );
  const showJobGroup = jobItems.length > 0;

  // 완료 스냅샷은 최신순 전체를 페이지네이션으로 노출
  const totalPages = Math.max(
    1,
    Math.ceil(snapshotItems.length / ANALYSIS_PAGE_SIZE),
  );
  const currentPage = Math.min(page, totalPages);
  const visibleSnapshots = snapshotItems.slice(
    (currentPage - 1) * ANALYSIS_PAGE_SIZE,
    currentPage * ANALYSIS_PAGE_SIZE,
  );

  const openCompare = () => {
    if (!canCompare) return;
    setSelectedIds([]);
    setShowCompare(true);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((itemId) => itemId !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
  };

  const handleCompare = () => {
    if (selectedIds.length !== 2) return;

    const selected = selectedIds
      .map((id) => completedItems.find((item) => item.id === id))
      .filter((item): item is AnalysisResultItem => item != null);

    if (selected.length !== 2) return;

    const sorted = [...selected].sort((a, b) => {
      const ta = a.snapshotAt ? new Date(a.snapshotAt).getTime() : 0;
      const tb = b.snapshotAt ? new Date(b.snapshotAt).getTime() : 0;
      return ta - tb;
    });

    setShowCompare(false);
    navigate(ROUTES.analysisCompare(sorted[0].id, sorted[1].id));
  };

  return (
    <div className="flex flex-col">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold tracking-tight">
              개인성향 분석 목록
            </h2>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="gap-1.5"
            disabled={!canCompare}
            onClick={openCompare}
            title={
              canCompare
                ? undefined
                : "완료된 분석이 2개 이상이면 비교할 수 있습니다."
            }
          >
            <ArrowLeftRight size={16} />
            비교분석
          </Button>
          <Button size="sm" className="gap-1.5" asChild>
            <Link to={ROUTES.upload} onClick={(e) => e.stopPropagation()}>
              <Plus size={16} />
              새로 추가
            </Link>
          </Button>
        </div>
      </div>

      {loading && items.length === 0 && (
        <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 py-16 text-sm">
          <Loader2 className="size-4 animate-spin" />
          목록 불러오는 중…
        </div>
      )}

      {error && (
        <div className="border-border text-destructive rounded-2xl border border-dashed px-6 py-16 text-center text-sm">
          {error}
        </div>
      )}

      {(!loading || items.length > 0) && !error && (
        <div className="flex flex-1 flex-col gap-3">
          {showJobGroup &&
            jobGroups.map((group) => (
              <InProgressGroup
                key={group[0].batchId ?? group[0].id}
                items={group}
                onDelete={setDeleteJob}
              />
            ))}
          {visibleSnapshots.map((item) => (
            <AnalysisListItem
              key={item.id}
              item={item}
              onDelete={setDeleteTarget}
            />
          ))}
          {!showJobGroup && visibleSnapshots.length === 0 && (
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

      {showCompare && (
        <CompareModal
          items={completedItems}
          selectedIds={selectedIds}
          onToggle={toggleSelect}
          onClose={() => setShowCompare(false)}
          onConfirm={handleCompare}
        />
      )}

      {(deleteTarget || deleteJob) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          onClick={(e) => e.stopPropagation()}
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => {
              if (deleting) return;
              setDeleteTarget(null);
              setDeleteJob(null);
            }}
          />
          <div className="border-border bg-card relative z-10 w-full max-w-sm rounded-2xl border p-5 shadow-xl">
            <h3 className="text-base font-semibold">분석 삭제</h3>
            <p className="text-muted-foreground mt-2 text-sm">
              <span className="text-foreground font-medium">
                {deleteTarget ? deleteTarget.title : "진행 중인 분석"}
              </span>{" "}
              분석을 삭제하시겠습니까? 되돌릴 수 없습니다.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setDeleteTarget(null);
                  setDeleteJob(null);
                }}
                disabled={deleting}
              >
                취소
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5"
                onClick={() =>
                  void (deleteTarget ? handleDelete() : handleDeleteJob())
                }
                disabled={deleting}
              >
                <Trash2 size={15} className={deleting ? "animate-pulse" : ""} />
                {deleting ? "삭제 중…" : "삭제"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
