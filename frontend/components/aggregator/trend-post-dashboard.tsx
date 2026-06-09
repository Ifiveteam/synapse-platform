"use client";

import { Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CognitiveChart } from "@/components/aggregator/cognitive-chart";
import { MarkdownReport } from "@/components/aggregator/markdown-report";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getTrendPostPdfUrl, type TrendPostResponse } from "@/lib/api/trend";
import { ROUTES } from "@/lib/routes";

interface TrendPostDashboardProps {
  agentSlug: string;
  post: TrendPostResponse;
}

function formatGeneratedAt(iso: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function TrendPostDashboard({
  agentSlug,
  post,
}: TrendPostDashboardProps) {
  const [isDownloading, setIsDownloading] = useState(false);

  async function handleDownloadPdf() {
    setIsDownloading(true);

    try {
      window.open(getTrendPostPdfUrl(post.post_id), "_blank", "noopener,noreferrer");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-6 py-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild variant="ghost" size="sm" className="w-fit px-0">
              <Link href={ROUTES.trendPosts(agentSlug)}>← 리포트 목록</Link>
            </Button>
            <Button asChild variant="ghost" size="sm" className="w-fit px-0">
              <Link href={ROUTES.agentDetail(agentSlug)}>에이전트로</Link>
            </Button>
          </div>
          <div>
            <p className="text-muted-foreground text-sm font-medium">
              B2B 트렌드 분석 리포트
            </p>
            <h1 className="text-3xl font-bold tracking-tight">
              시장 인지 성향 분석 보고서
            </h1>
            <p className="text-muted-foreground mt-2 text-sm">
              생성일: {formatGeneratedAt(post.generated_at)}
            </p>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          className="shrink-0"
          onClick={handleDownloadPdf}
          disabled={isDownloading}
        >
          {isDownloading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Download className="size-4" />
          )}
          PDF 보고서 다운로드
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(280px,360px)_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>성향 균형도</CardTitle>
            <CardDescription>
              코호트 {post.cohort_size.toLocaleString("ko-KR")}명 기준 8각 인지
              축 평균 점수
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CognitiveChart axes={post.axes} cohortSize={post.cohort_size} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>분석 리포트</CardTitle>
            <CardDescription>
              Gemini가 생성한 B2B 마켓 인사이트 본문
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MarkdownReport content={post.report_markdown} />
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
