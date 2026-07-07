import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { AlertCircle, FileText, Loader2 } from "lucide-react";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fetchMarkdownReport } from "@/services/reporter";

const Markdown = lazy(() => import("react-markdown"));

const ARTICLE_CLASS = cn(
  "text-sm leading-7 text-foreground/90",
  "[&_h1]:mb-4 [&_h1]:mt-0 [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:tracking-tight",
  "[&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:border-b [&_h2]:border-border [&_h2]:pb-2 [&_h2]:text-xl [&_h2]:font-semibold",
  "[&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:text-lg [&_h3]:font-medium",
  "[&_p]:mb-4 [&_p:last-child]:mb-0",
  "[&_ul]:mb-4 [&_ul]:ml-5 [&_ul]:list-disc [&_ul]:space-y-1",
  "[&_ol]:mb-4 [&_ol]:ml-5 [&_ol]:list-decimal [&_ol]:space-y-1",
  "[&_li]:marker:text-muted-foreground",
  "[&_strong]:font-semibold [&_strong]:text-foreground",
  "[&_blockquote]:mb-4 [&_blockquote]:border-l-4 [&_blockquote]:border-indigo-400 [&_blockquote]:bg-muted/40 [&_blockquote]:px-4 [&_blockquote]:py-2 [&_blockquote]:not-italic",
  "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs",
  "[&_hr]:my-8 [&_hr]:border-border",
  "[&_a]:text-indigo-500 [&_a]:underline-offset-2 hover:[&_a]:underline",
  "[&_table]:mb-4 [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:bg-muted/50 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-2",
);

function MarkdownFallback() {
  return (
    <div className="flex min-h-[320px] items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      리포트 렌더러 로딩 중…
    </div>
  );
}

interface TrendReportViewerProps {
  selectedDate: string;
}

export function TrendReportViewer({ selectedDate }: TrendReportViewerProps) {
  const [markdown, setMarkdown] = useState("");
  const [source, setSource] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async (date: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMarkdownReport(date);
      setMarkdown(data.markdown);
      setSource(data.source);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "리포트를 불러오지 못했습니다.";
      setError(message);
      setMarkdown("");
      setSource("");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadReport(selectedDate);
  }, [selectedDate, loadReport]);

  return (
    <div className="border-border bg-card rounded-2xl border shadow-sm">
      <div className="border-border flex flex-wrap items-center justify-between gap-2 border-b px-5 py-4">
        <div className="flex items-center gap-2">
          <FileText className="text-muted-foreground size-4" />
          <div>
            <p className="text-sm font-semibold">텍스트 트렌드 리포트</p>
            <p className="text-muted-foreground text-xs">
              {selectedDate} · B2B 마크다운 인텔리전스
            </p>
          </div>
        </div>
        {source && !loading && (
          <span className="rounded-full bg-muted px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            source: {source}
          </span>
        )}
      </div>

      <div className="relative min-h-[420px] px-5 py-6 md:px-8 md:py-8">
        {loading && (
          <div className="flex min-h-[320px] flex-col items-center justify-center gap-3">
            <Loader2 className="size-8 animate-spin text-indigo-400" />
            <p className="text-sm text-muted-foreground">리포트 불러오는 중…</p>
          </div>
        )}

        {error && !loading && (
          <div className="flex min-h-[320px] flex-col items-center justify-center gap-3 text-center">
            <AlertCircle className="size-10 text-rose-400" />
            <p className="text-sm font-medium">리포트를 불러오지 못했습니다</p>
            <p className="text-muted-foreground max-w-md text-xs">{error}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void loadReport(selectedDate)}
            >
              다시 시도
            </Button>
          </div>
        )}

        {!loading && !error && markdown && (
          <article className={ARTICLE_CLASS}>
            <Suspense fallback={<MarkdownFallback />}>
              <Markdown remarkPlugins={[remarkGfm]}>{markdown}</Markdown>
            </Suspense>
          </article>
        )}
      </div>
    </div>
  );
}
