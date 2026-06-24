import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  applyIdeal,
  listIdeals,
  IDEAL_TYPE_LABEL,
  type IdealResponse,
} from "@/lib/ideals/api";
import { ROUTES } from "@/routes";
import { useSidebarStore } from "@/stores/sidebar";

const TABS = [
  { id: "confirmed", label: "확정 이상향" },
  { id: "setup", label: "이상향 설정" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function IdealCard({
  item,
  onApply,
}: {
  item: IdealResponse;
  onApply: (id: string) => void;
}) {
  return (
    <Link
      to={ROUTES.idealDetail(item.id)}
      className="bg-card text-card-foreground border-border hover:border-primary/40 flex items-start gap-4 rounded-2xl border px-4 py-4 shadow-sm transition-colors"
    >
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

          {item.is_active ? (
            <Badge variant="indigo" className="shrink-0 rounded-full">
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
              className="border-primary text-primary hover:bg-primary/5 shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors"
            >
              적용
            </button>
          )}
        </div>
      </div>
    </Link>
  );
}

function ConfirmedTab({
  ideals,
  loading,
  error,
  onApply,
}: {
  ideals: IdealResponse[];
  loading: boolean;
  error: string | null;
  onApply: (id: string) => void;
}) {
  if (loading) {
    return <p className="text-muted-foreground text-sm">불러오는 중…</p>;
  }
  if (error) {
    return <p className="text-destructive text-sm">{error}</p>;
  }
  return (
    <div className="flex flex-col gap-4">
      {ideals.map((item) => (
        <IdealCard key={item.id} item={item} onApply={onApply} />
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

function SetupTab() {
  return (
    <div className="border-border flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed py-16 text-center">
      <div className="bg-accent text-accent-foreground flex h-14 w-14 items-center justify-center rounded-2xl">
        <Target size={26} />
      </div>
      <div>
        <p className="text-sm font-semibold">이상향 설정</p>
        <p className="text-muted-foreground mt-1 text-xs">
          현재 프로필을 바탕으로 반대·강점심화·균형 이상향을 제안받고,
          <br />
          채팅으로 세부 조정해 나만의 이상향을 설계합니다.
        </p>
      </div>
      <Button asChild className="gap-1.5">
        <Link to={ROUTES.idealSetup}>
          <Plus size={16} />
          이상향 설정하러 가기
        </Link>
      </Button>
    </div>
  );
}

export function IdealManagementPage() {
  const [ideals, setIdeals] = useState<IdealResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("confirmed");
  const setActiveIdealLabel = useSidebarStore((s) => s.setActiveIdealLabel);

  const syncSidebar = useCallback(
    (list: IdealResponse[]) => {
      const active = list.find((x) => x.is_active);
      setActiveIdealLabel(active ? IDEAL_TYPE_LABEL[active.ideal_type] : null);
    },
    [setActiveIdealLabel],
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

  const handleApply = async (id: string) => {
    try {
      await applyIdeal(id);
      await load();
    } catch {
      setError("적용에 실패했습니다.");
    }
  };

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">이상향 관리</h1>
        <Button size="sm" className="shrink-0 gap-1.5" asChild>
          <Link to={ROUTES.idealSetup}>
            <Plus size={16} />
            새로 추가
          </Link>
        </Button>
      </div>

      <Tabs
        value={tab}
        onValueChange={(v) => setTab(v as TabId)}
        className="gap-6"
      >
        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger key={t.id} value={t.id}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="confirmed">
          <ConfirmedTab
            ideals={ideals}
            loading={loading}
            error={error}
            onApply={handleApply}
          />
        </TabsContent>
        <TabsContent value="setup">
          <SetupTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
