import { Link, useParams } from "react-router-dom";
import { ArrowUp, Bookmark, Share2, User } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAnalysisDetail } from "@/lib/analyses/mock";
import { ROUTES } from "@/routes";
import { NotFoundPage } from "@/pages/NotFoundPage";

export function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const detail = id ? getAnalysisDetail(id) : undefined;

  if (!detail) {
    return <NotFoundPage />;
  }

  const isPending = detail.status === "pending";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mx-auto flex w-full max-w-5xl min-h-0 flex-1 flex-col px-6 py-6">
        <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
          <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
            홈
          </Link>
          <span>/</span>
          <Link
            to={ROUTES.myAnalyses}
            className="hover:text-foreground transition-colors"
          >
            분석결과
          </Link>
          <span>/</span>
          <span className="text-foreground">개인성향 분석 결과</span>
        </nav>

        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              개인성향 분석 결과
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">{detail.date}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Share2 size={14} />
              공유
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5">
              <Bookmark size={14} />
              스크랩하기
            </Button>
          </div>
        </div>

        {isPending ? (
          <div className="border-border text-muted-foreground flex flex-1 items-center justify-center rounded-2xl border border-dashed text-sm">
            분석이 아직 완료되지 않았습니다.
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(0,1fr)_240px]">
            <div className="flex min-h-0 flex-col gap-4">
              <div className="border-border bg-secondary/30 flex min-h-[200px] flex-col items-center justify-center rounded-2xl border">
                <User size={48} className="text-muted-foreground mb-3 opacity-40" />
                <p className="text-muted-foreground text-sm">대표이미지</p>
                <p className="mt-1 text-base font-semibold">
                  {detail.characterName}
                </p>
              </div>

              <div className="border-border rounded-2xl border bg-card p-5">
                <p className="mb-3 text-sm font-semibold">특징</p>
                <p className="text-primary mb-2 text-sm font-semibold">
                  {detail.typeName}
                </p>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {detail.description}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {detail.tags.map((tag) => (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="rounded-full px-3 py-1"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <div className="border-border rounded-2xl border bg-card p-4">
                <p className="mb-3 text-sm font-semibold">키워드</p>
                <p className="text-muted-foreground mb-2 text-[10px] font-semibold tracking-widest uppercase">
                  Top 5
                </p>
                <ol className="space-y-2.5">
                  {detail.keywords.map((kw, i) => (
                    <li key={kw} className="flex items-start gap-2 text-sm">
                      <span className="bg-accent text-accent-foreground flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold">
                        {i + 1}
                      </span>
                      <span className="leading-snug">{kw}</span>
                    </li>
                  ))}
                </ol>
              </div>

              <div className="border-border rounded-2xl border bg-card p-4">
                <p className="mb-3 text-sm font-semibold">비슷한 캐릭터</p>
                <div className="border-border bg-secondary/40 mb-3 flex h-24 items-center justify-center rounded-xl border">
                  <span className="text-muted-foreground text-xs">
                    {detail.similarCharacter.imageLabel}
                  </span>
                </div>
                <p className="text-sm font-medium">
                  {detail.similarCharacter.name}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {!isPending && (
        <div className="border-border shrink-0 border-t px-6 py-4">
          <div className="border-border mx-auto flex max-w-5xl items-center gap-3 rounded-2xl border bg-card px-4 py-3 shadow-sm">
            <input
              type="text"
              placeholder="이 분석에 대해 물어보세요..."
              className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
            />
            <Button type="button" size="icon" className="size-8 rounded-full">
              <ArrowUp size={16} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
