import { ExternalLink, Loader2, MessageSquare, Sparkles } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ArchiverChatMessage } from "@/api/archiver";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useScrapDetail } from "@/features/scraps/hooks/useScrapDetail";
import { cn } from "@/lib/utils";

const MARKDOWN_CLASS =
  "[&_blockquote]:border-l-2 [&_blockquote]:pl-2 [&_blockquote]:italic [&_code]:rounded [&_code]:bg-black/10 [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mb-1.5 [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-medium [&_ol]:ml-4 [&_ol]:list-decimal [&_ol]:space-y-0.5 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:ml-4 [&_ul]:list-disc [&_ul]:space-y-0.5 dark:[&_code]:bg-white/10";

function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatMessageTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso));
  } catch {
    return "";
  }
}

function truncateBody(text: string, max = 1200): string {
  const normalized = text.trim();
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max - 1)}…`;
}

function ArchiverChatTimeline({ messages }: { messages: ArchiverChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <p className="text-muted-foreground py-2 text-sm">
        이 페이지 URL과 연결된 Archiver 대화 기록이 없습니다.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((msg) => {
        const isUser = msg.role === "user";
        return (
          <div
            key={msg.id}
            className={cn("flex gap-2", isUser ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                isUser
                  ? "rounded-br-sm bg-primary text-primary-foreground"
                  : "rounded-bl-sm bg-muted/80 ring-1 ring-border",
              )}
            >
              <div className="mb-1 flex items-center gap-1.5 text-[10px] opacity-70">
                {isUser ? (
                  <span>나</span>
                ) : (
                  <>
                    <Sparkles className="size-3" />
                    <span>Archiver</span>
                  </>
                )}
                <span>·</span>
                <span>{formatMessageTime(msg.created_at)}</span>
              </div>
              {isUser ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <div className={MARKDOWN_CLASS}>
                  <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RawBodySnapshot({ body }: { body: string | null }) {
  const preview = body ? truncateBody(body) : null;

  if (!preview) return null;

  return (
    <div className="border-border bg-muted/30 rounded-xl border p-4">
      <p className="text-muted-foreground mb-2 text-xs font-medium">수집된 페이지 본문</p>
      <p className="text-foreground/90 text-sm leading-relaxed whitespace-pre-wrap">
        {preview}
      </p>
    </div>
  );
}

export interface ScrapDetailPanelProps {
  scrapId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ScrapDetailPanel({
  scrapId,
  open,
  onOpenChange,
}: ScrapDetailPanelProps) {
  const { scrap, archiverHistory, loading, error } = useScrapDetail(open ? scrapId : null);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="border-border border-b pr-12">
          {loading ? (
            <>
              <SheetTitle>스크랩 불러오는 중…</SheetTitle>
              <SheetDescription>지식 허브 데이터를 가져오고 있습니다.</SheetDescription>
            </>
          ) : error ? (
            <>
              <SheetTitle>불러오기 실패</SheetTitle>
              <SheetDescription>{error}</SheetDescription>
            </>
          ) : scrap ? (
            <>
              <SheetTitle className="line-clamp-2 text-left leading-snug">
                {scrap.title?.trim() || "(제목 없음)"}
              </SheetTitle>
              <SheetDescription className="text-left">
                {formatDateTime(scrap.created_at)}
              </SheetDescription>
            </>
          ) : (
            <>
              <SheetTitle>스크랩 상세</SheetTitle>
              <SheetDescription>항목을 선택해 주세요.</SheetDescription>
            </>
          )}
        </SheetHeader>

        {loading && (
          <div className="text-muted-foreground flex flex-1 items-center justify-center gap-2 p-6">
            <Loader2 className="size-5 animate-spin" />
            <span className="text-sm">로딩 중…</span>
          </div>
        )}

        {!loading && scrap && (
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
            <section className="border-border space-y-3 border-b p-6">
              {scrap.url && (
                <Button variant="outline" size="sm" className="gap-1.5" asChild>
                  <a href={scrap.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="size-3.5" />
                    원본 페이지 열기
                  </a>
                </Button>
              )}

              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{scrap.category}</Badge>
                {scrap.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-[11px]">
                    #{tag}
                  </Badge>
                ))}
              </div>
            </section>

            <section className="border-border space-y-3 border-b p-6">
              <div className="flex items-center gap-2">
                <Sparkles className="text-primary size-4" />
                <h3 className="text-sm font-semibold">AI 요약</h3>
              </div>
              <div className={cn("prose-sm text-sm leading-relaxed", MARKDOWN_CLASS)}>
                <Markdown remarkPlugins={[remarkGfm]}>{scrap.summary}</Markdown>
              </div>
              {scrap.tags.length > 0 && (
                <div className="pt-1">
                  <p className="text-muted-foreground mb-1.5 text-[11px] font-medium tracking-wide uppercase">
                    핵심 키워드
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {scrap.tags.map((tag) => (
                      <span
                        key={tag}
                        className="bg-primary/10 text-primary rounded-full px-2.5 py-0.5 text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            <section className="border-border space-y-4 border-b p-6">
              <div className="flex items-center gap-2">
                <MessageSquare className="text-primary size-4" />
                <h3 className="text-sm font-semibold">이 페이지에서 나눈 Archiver 대화</h3>
              </div>
              {!scrap.url ? (
                <p className="text-muted-foreground text-sm">
                  원본 URL이 없어 대화 기록을 찾을 수 없습니다.
                </p>
              ) : (
                <ArchiverChatTimeline messages={archiverHistory} />
              )}
            </section>

            {scrap.raw_body_snapshot && (
              <section className="p-6">
                <RawBodySnapshot body={scrap.raw_body_snapshot} />
              </section>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
