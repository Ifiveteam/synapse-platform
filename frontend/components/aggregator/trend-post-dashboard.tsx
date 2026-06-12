"use client";

import { Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CognitiveObsidianGraph } from "@/components/aggregator/cognitive-obsidian-graph";
import { TrendGapDashboard } from "@/components/aggregator/trend-gap-dashboard";
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

function neutralityBadgeClass(status: string): string {
  if (status === "안정") return "bg-emerald-100 text-emerald-800";
  if (status === "주의") return "bg-amber-100 text-amber-800";
  return "bg-rose-100 text-rose-800";
}

export function TrendPostDashboard({
  agentSlug,
  post,
}: TrendPostDashboardProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const { report } = post;

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
              {report.headline_summary}
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

      <Card>
        <CardHeader>
          <CardTitle>미디어 중립성</CardTitle>
          <CardDescription>{report.neutrality_reason}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <span className="text-3xl font-bold">{report.neutrality_score}</span>
          <span className="text-muted-foreground text-sm">/ 100</span>
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${neutralityBadgeClass(report.neutrality_status)}`}
          >
            {report.neutrality_status}
          </span>
        </CardContent>
      </Card>

      <Card className="h-fit lg:max-w-2xl">
        <CardHeader>
          <CardTitle>성향 균형도</CardTitle>
          <CardDescription>
            옵시디언 그래프 뷰 — 코호트 {post.cohort_size.toLocaleString("ko-KR")}
            명 기준 8각 인지 축 연결망
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CognitiveObsidianGraph
            radarChartData={report.radar_chart_data}
            dominantAxes={report.dominant_axes}
            deficientAxes={report.deficient_axes}
            cohortSize={post.cohort_size}
          />
        </CardContent>
      </Card>

      <TrendGapDashboard
        macroTrendInternal={report.macro_trend_internal}
        macroTrendExternal={report.macro_trend_external}
        gapAnalysis={report.gap_analysis}
        recommendations={report.recommendations}
      />
    </main>
  );
}
