import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ListVideo, Loader2, Plus, Target, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  applyIdeal,
  deleteIdeal,
  getActiveProposal,
  listIdeals,
} from "@/api/navigator";
import { fetchMyAnalyses } from "@/api/analyses";
import type { IdealResponse } from "@/api/types/navigator";
import { IDEAL_TYPE_LABEL } from "@/lib/navigator/labels";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/routes";
import { useSidebarStore } from "@/stores/sidebar";

function IdealCard({
  item,
  onApply,
  onDelete,
  embedded = false,
}: {
  item: IdealResponse;
  onApply: (id: string) => void;
  onDelete?: (item: IdealResponse) => void;
  embedded?: boolean;
}) {
  const navigate = useNavigate();
  const inner = (
    <>
      <div className="bg-accent text-accent-foreground flex h-12 w-12 shrink-0 items-center justify-center rounded-xl">
        <Target size={22} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {item.persona_label || `${IDEAL_TYPE_LABEL[item.ideal_type]} 이상향`}
            </p>
            <p className="text-muted-foreground mt-0.5 text-xs">
              {IDEAL_TYPE_LABEL[item.ideal_type]}
            </p>
            <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">
              {item.reasoning || "설명 없음"}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                navigate(ROUTES.playlistsForIdeal(item.id));
              }}
              className="border-border text-muted-foreground hover:text-primary hover:border-primary/40 inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors"
            >
              <ListVideo size={13} />
              재생목록
            </button>
            {item.is_active ? (
              <Badge variant="indigo" className="rounded-full">
                적용 중
              </Badge>
            ) : (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onApply(item.id);
                }}
                className="border-primary text-primary hover:bg-primary/5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors"
              >
                적용
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onDelete(item);
                }}
                className="text-muted-foreground hover:text-destructive rounded-full p-1 transition-colors"
                aria-label="삭제"
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );

  const className =
    "bg-card text-card-foreground border-border hover:border-primary/40 flex items-start gap-4 rounded-2xl border px-4 py-4 shadow-sm transition-colors";

  // 허브(embedded)에선 개별 링크 대신 박스 전체 클릭(→ 이상향 관리)에 맡긴다.
  if (embedded) {
    return <div className={className}>{inner}</div>;
  }

  return (
    <Link to={ROUTES.idealDetail(item.id)} className={className}>
      {inner}
    </Link>
  );
}

function IdealList({
  ideals,
  loading,
  error,
  onApply,
  onDelete,
  activeOnly = false,
  embedded = false,
}: {
  ideals: IdealResponse[];
  loading: boolean;
  error: string | null;
  onApply: (id: string) => void;
  onDelete?: (item: IdealResponse) => void;
  activeOnly?: boolean;
  embedded?: boolean;
}) {
  if (loading) {
    return <p className="text-muted-foreground text-sm">불러오는 중…</p>;
  }
  if (error) {
    return <p className="text-destructive text-sm">{error}</p>;
  }

  if (activeOnly) {
    // 적용 중 + 그 아래 '적용 중을 제외한' 가장 최근 1개. 목록은 최신순.
    const active = ideals.find((item) => item.is_active) ?? null;
    const recent = ideals.find((item) => item.id !== active?.id) ?? null;
    const cards: IdealResponse[] = [];
    if (active) cards.push(active);
    if (recent) cards.push(recent);
    if (cards.length === 0) {
      // 허브(embedded)에선 박스 전체 클릭(→ 이상향 관리)에 맡긴다.
      return (
        <div className="border-border text-muted-foreground flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed">
          <Plus size={20} />
          <span className="text-sm font-medium">적용 중인 이상향이 없습니다</span>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-4">
        {cards.map((item) => (
          <IdealCard
            key={item.id}
            item={item}
            onApply={onApply}
            onDelete={onDelete}
            embedded={embedded}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {ideals.map((item) => (
        <IdealCard
          key={item.id}
          item={item}
          onApply={onApply}
          onDelete={onDelete}
        />
      ))}

      <Link
        to={ROUTES.idealSetup}
        className="border-border text-muted-foreground hover:border-primary/40 hover:text-foreground flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed transition-colors"
      >
        <Plus size={20} />
        <span className="text-sm font-medium">새 이상향 설계하기</span>
      </Link>
    </div>
  );
}

export function IdealManagementPage({
  embedded = false,
  activeOnly = false,
}: { embedded?: boolean; activeOnly?: boolean } = {}) {
  const [ideals, setIdeals] = useState<IdealResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [designState, setDesignState] = useState<"none" | "pending" | "ready">(
    "none",
  );
  const [designSourceId, setDesignSourceId] = useState<string | null>(null);
  const [designTitle, setDesignTitle] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<IdealResponse | null>(null);
  const [deleting, setDeleting] = useState(false);
  const setActiveIdealLabel = useSidebarStore((s) => s.setActiveIdealLabel);
  const loadIdealPersona = useSidebarStore((s) => s.loadIdealPersona);

  const syncSidebar = useCallback(
    (list: IdealResponse[]) => {
      const active = list.find((x) => x.is_active);
      if (active) {
        setActiveIdealLabel(
          active.persona_label || IDEAL_TYPE_LABEL[active.ideal_type],
        );
      } else {
        // 적용 이상향 없음 → 최신 분석 페르소나로 폴백
        void loadIdealPersona();
      }
    },
    [setActiveIdealLabel, loadIdealPersona],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listIdeals();
      setIdeals(list);
      syncSidebar(list);
    } catch {
      setError("이상향을 불러오지 못했습니다. 로그인 상태를 확인하세요.");
    } finally {
      setLoading(false);
    }
  }, [syncSidebar]);

  useEffect(() => {
    void load();
  }, [load]);

  // 진행 중인 이상향 설계 감지 — pending(생성 중)이면 4초 폴링해 ready로 갱신
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const check = async () => {
      try {
        const r = await getActiveProposal();
        if (cancelled) return;
        setDesignState(r.state);
        setDesignSourceId(r.source_profile_history_id);
        if (r.state === "pending") timer = setTimeout(() => void check(), 4000);
      } catch {
        /* 비로그인 등 무시 */
      }
    };
    void check();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  // 설계 기반 분석의 제목 해석 (분석 목록에서 id 매칭)
  useEffect(() => {
    if (!designSourceId) {
      setDesignTitle(null);
      return;
    }
    let cancelled = false;
    void fetchMyAnalyses()
      .then((list) => {
        if (cancelled) return;
        setDesignTitle(
          list.find((a) => a.id === designSourceId)?.title ?? null,
        );
      })
      .catch(() => {
        /* 무시 */
      });
    return () => {
      cancelled = true;
    };
  }, [designSourceId]);

  const handleApply = async (id: string) => {
    try {
      await applyIdeal(id);
      await load();
    } catch {
      setError("적용에 실패했습니다.");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteIdeal(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch {
      setError("삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div
      className={cn(
        "flex flex-col",
        embedded ? "" : "min-h-full px-4 py-5 sm:px-6 sm:py-6",
      )}
    >
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {embedded ? (
            <h2 className="text-lg font-semibold tracking-tight">이상향 관리</h2>
          ) : (
            <h1 className="text-2xl font-semibold tracking-tight">이상향 관리</h1>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button size="sm" variant="outline" className="gap-1.5" asChild>
            <Link to={ROUTES.playlists} onClick={(e) => e.stopPropagation()}>
              <ListVideo size={16} />
              재생목록
            </Link>
          </Button>
          <Button size="sm" className="gap-1.5" asChild>
            <Link to={ROUTES.idealSetup} onClick={(e) => e.stopPropagation()}>
              <Plus size={16} />
              새로 추가
            </Link>
          </Button>
        </div>
      </div>

      {designState !== "none" && (
        <Link
          to={
            designSourceId
              ? `${ROUTES.idealSetup}?analysis=${designSourceId}`
              : ROUTES.idealSetup
          }
          onClick={(e) => e.stopPropagation()}
          className="bg-card text-card-foreground border-border hover:border-primary/40 mb-4 flex items-start gap-4 rounded-2xl border px-4 py-4 shadow-sm transition-colors"
        >
          <div className="bg-accent text-accent-foreground flex h-12 w-12 shrink-0 items-center justify-center rounded-xl">
            {designState === "pending" ? (
              <Loader2 className="size-5 animate-spin" />
            ) : (
              <Target size={22} />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">
                  {designState === "pending"
                    ? "이상향 추천을 만드는 중"
                    : "진행 중인 이상향 설계"}
                </p>
                <p className="text-muted-foreground mt-0.5 truncate text-xs">
                  {designTitle ? `${designTitle} 분석 기반` : "분석 기반 설계"}
                </p>
                <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">
                  {designState === "pending"
                    ? "완성되면 3안 중 골라 저장할 수 있어요."
                    : "추천 3안이 준비됐어요. 이어서 골라 저장해 보세요."}
                </p>
              </div>
              <span className="border-primary text-primary hover:bg-primary/5 shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors">
                이어서 분석하기
              </span>
            </div>
          </div>
        </Link>
      )}

      <IdealList
        ideals={ideals}
        loading={loading}
        error={error}
        onApply={handleApply}
        onDelete={setDeleteTarget}
        activeOnly={activeOnly}
        embedded={embedded}
      />

      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => !deleting && setDeleteTarget(null)}
          />
          <div className="border-border bg-card relative z-10 w-full max-w-sm rounded-2xl border p-5 shadow-xl">
            <h3 className="text-base font-semibold">이상향 삭제</h3>
            <p className="text-muted-foreground mt-2 text-sm">
              <span className="text-foreground font-medium">
                {deleteTarget.persona_label ||
                  IDEAL_TYPE_LABEL[deleteTarget.ideal_type]}
              </span>{" "}
              이상향을 삭제하시겠습니까? 연관된 재생목록도 함께 삭제되며 되돌릴 수
              없습니다.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                취소
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5"
                onClick={() => void handleDelete()}
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
