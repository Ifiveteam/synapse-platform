import { Link, useParams } from "react-router-dom";
import { ExternalLink, Share2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getScrapDetail } from "@/lib/scraps/mock";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ROUTES } from "@/routes";
import { cn } from "@/lib/utils";

function PreviewPlaceholder({ label }: { label: string }) {
  return (
    <div
      className={cn(
        "border-border flex min-h-[220px] flex-col items-center justify-center rounded-2xl border bg-card",
        "bg-[repeating-linear-gradient(-45deg,var(--border)_0,var(--border)_1px,transparent_0,transparent_12px)]",
      )}
    >
      <p className="text-muted-foreground rounded-lg bg-card/90 px-4 py-2 text-sm">
        {label}
      </p>
    </div>
  );
}

export function ScrapDetailPage() {
  const { id } = useParams<{ id: string }>();
  const detail = id ? getScrapDetail(id) : undefined;

  if (!detail) {
    return <NotFoundPage />;
  }

  return (
    <div className="flex h-full min-h-0 flex-col px-6 py-6">
      <div className="mx-auto flex w-full max-w-6xl min-h-0 flex-1 flex-col">
        <nav className="text-muted-foreground mb-4 flex flex-wrap items-center gap-1.5 text-xs">
          <Link to={ROUTES.home} className="hover:text-foreground transition-colors">
            홈
          </Link>
          <span>/</span>
          <Link
            to={ROUTES.scraps}
            className="hover:text-foreground transition-colors"
          >
            스크랩
          </Link>
          <span>/</span>
          <span className="text-foreground max-w-[200px] truncate sm:max-w-none">
            {detail.title}
          </span>
        </nav>

        <div className="mb-4 flex items-start justify-between gap-4">
          <h1 className="min-w-0 text-2xl font-semibold tracking-tight">
            {detail.title}
          </h1>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Share2 size={14} />
              공유
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:text-destructive gap-1.5"
            >
              <Trash2 size={14} />
              삭제
            </Button>
          </div>
        </div>

        <div className="border-border bg-secondary/30 mb-6 flex items-center gap-2 rounded-xl border px-4 py-2.5">
          <span className="text-muted-foreground shrink-0 text-xs">URL</span>
          <a
            href={detail.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary min-w-0 flex-1 truncate text-sm hover:underline"
          >
            {detail.url}
          </a>
          <ExternalLink size={14} className="text-muted-foreground shrink-0" />
        </div>

        <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
          <div className="flex min-h-0 flex-col gap-4">
            <PreviewPlaceholder label={detail.previewLabel} />

            <div className="border-border flex min-h-0 flex-1 flex-col rounded-2xl border bg-card p-5">
              <p className="mb-4 text-sm font-semibold">스크랩 내용</p>
              <p className="text-muted-foreground flex-1 text-sm leading-relaxed">
                {detail.content}
              </p>
              <div className="border-graph/30 bg-graph/5 mt-5 rounded-xl border p-4">
                <p className="text-graph mb-1 text-[10px] font-semibold tracking-widest uppercase">
                  AI 요약
                </p>
                <p className="text-sm leading-relaxed">{detail.summary}</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="border-border rounded-2xl border bg-card p-4">
              <p className="mb-3 text-sm font-semibold">정보</p>
              <dl className="space-y-2.5 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground shrink-0">작성일</dt>
                  <dd className="text-right font-medium">{detail.savedAt}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground shrink-0">출처</dt>
                  <dd className="text-right font-medium">{detail.source}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground shrink-0">카테고리</dt>
                  <dd className="text-right font-medium">{detail.category}</dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {detail.tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="outline"
                    className="border-graph/40 text-graph rounded-full px-2.5 py-0.5 text-xs"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="border-border rounded-2xl border bg-card p-4">
              <p className="mb-3 text-sm font-semibold">관련 분석</p>
              <ul className="space-y-2">
                {detail.relatedAnalyses.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={ROUTES.analysisDetail(item.id)}
                      className="hover:bg-secondary/60 flex items-start gap-2.5 rounded-lg px-1 py-1.5 transition-colors"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px]",
                          item.checked
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border bg-background",
                        )}
                        aria-hidden
                      >
                        {item.checked ? "✓" : ""}
                      </span>
                      <span className="text-sm leading-snug">{item.title}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
