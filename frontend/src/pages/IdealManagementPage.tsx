import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Target, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  MOCK_IDEAL_PROFILES,
  type IdealProfile,
} from "@/lib/ideals/mock";
import { ROUTES } from "@/routes";

function IdealCard({
  item,
  onDelete,
}: {
  item: IdealProfile;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="border-border flex items-start gap-4 rounded-2xl border bg-card px-4 py-4">
      <div className="bg-accent text-accent-foreground flex h-12 w-12 shrink-0 items-center justify-center rounded-xl">
        <Target size={22} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {item.name} — {item.subtitle}
            </p>
            <p className="text-muted-foreground mt-1 text-xs">
              생성일: {item.createdAt}
            </p>
          </div>

          <button
            type="button"
            onClick={() => onDelete(item.id)}
            title="삭제"
            className="text-muted-foreground hover:bg-secondary hover:text-destructive shrink-0 rounded-lg p-2 transition-colors"
          >
            <Trash2 size={16} />
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {item.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="rounded-full">
              {tag}
            </Badge>
          ))}
          {item.isActive && (
            <Badge variant="indigo" className="rounded-full">
              적용 중
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

export function IdealManagementPage() {
  const [ideals, setIdeals] = useState(MOCK_IDEAL_PROFILES);

  const handleDelete = (id: string) => {
    setIdeals((prev) => prev.filter((item) => item.id !== id));
  };

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-6 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">이상향 관리</h1>
        <Button size="sm" className="shrink-0 gap-1.5" asChild>
          <Link to={ROUTES.navigator}>
            <Plus size={16} />
            새로 추가
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-4">
        {ideals.map((item) => (
          <IdealCard key={item.id} item={item} onDelete={handleDelete} />
        ))}

        <Link
          to={ROUTES.navigator}
          className="border-border text-muted-foreground hover:border-primary/40 hover:text-foreground flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed transition-colors"
        >
          <Plus size={20} />
          <span className="text-sm font-medium">새 이상향 추가하기</span>
        </Link>
      </div>
    </div>
  );
}
