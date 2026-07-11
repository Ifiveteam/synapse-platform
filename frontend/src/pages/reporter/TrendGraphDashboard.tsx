import { lazy, Suspense, useCallback, useState } from "react";
import axios from "axios";
import {
  BarChart3,
  CalendarDays,
  FileText,
  Loader2,
  Network,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { KnowledgeGraphPanel } from "@/pages/reporter/KnowledgeGraphPanel";
import {
  todayKstDateString,
  triggerDailyPipeline,
} from "@/services/reporter";

const TrendStreamGraph = lazy(() =>
  import("@/pages/reporter/TrendStreamGraph").then((m) => ({
    default: m.TrendStreamGraph,
  })),
);
const TrendHeatmap = lazy(() =>
  import("@/pages/reporter/TrendHeatmap").then((m) => ({
    default: m.TrendHeatmap,
  })),
);
const TrendReportViewer = lazy(() =>
  import("@/pages/reporter/TrendReportViewer").then((m) => ({
    default: m.TrendReportViewer,
  })),
);

function TabPanelFallback() {
  return (
    <div className="text-muted-foreground flex min-h-[320px] items-center justify-center text-sm">
      패널 로딩 중…
    </div>
  );
}

function pipelineErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  if (err instanceof Error && err.message.trim()) {
    return err.message;
  }
  return "실시간 분석 파이프라인 실행에 실패했습니다.";
}

export function TrendGraphDashboard() {
  const [selectedDate, setSelectedDate] = useState(todayKstDateString);
  const [activeTab, setActiveTab] = useState("graph");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRunPipeline = useCallback(async () => {
    if (isAnalyzing) return;

    setIsAnalyzing(true);
    try {
      const result = await triggerDailyPipeline(selectedDate);
      toast.success(result.message);
      setRefreshKey((prev) => prev + 1);
    } catch (err) {
      toast.error(pipelineErrorMessage(err));
    } finally {
      setIsAnalyzing(false);
    }
  }, [isAnalyzing, selectedDate]);

  const panelKey = `${selectedDate}-${refreshKey}`;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 md:px-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-muted-foreground mb-1 flex items-center gap-2 text-xs font-medium uppercase tracking-wider">
            <Network className="size-3.5" />
            Phase 4 · Trend Intelligence
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            트렌드 인텔리전스 대시보드
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">
            지식 네트워크, 시계열 스트림, 활동 히트맵, 텍스트 리포트를 한 화면에서
            탐색합니다.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="border-border bg-card flex items-center gap-2 rounded-lg border px-3 py-2 shadow-sm">
            <CalendarDays className="text-muted-foreground size-4 shrink-0" />
            <span className="text-muted-foreground text-xs">종료일</span>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              disabled={isAnalyzing}
              className="bg-transparent text-sm font-medium outline-none disabled:opacity-60"
              aria-label="트렌드 대시보드 조회 종료일"
            />
          </label>
          <span className="text-muted-foreground hidden text-xs sm:inline">
            지식 그래프는 종료일 포함 최근 7일을 합산합니다
          </span>

          <Button
            type="button"
            onClick={() => void handleRunPipeline()}
            disabled={isAnalyzing}
            className="gap-2 shadow-sm"
          >
            {isAnalyzing ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Sparkles className="size-4" />
            )}
            실시간 분석 실행
          </Button>
        </div>
      </header>

      <div className="relative">
        {isAnalyzing && (
          <div
            className="bg-background/80 absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 rounded-xl backdrop-blur-sm"
            role="status"
            aria-live="polite"
            aria-label="실시간 분석 진행 중"
          >
            <Loader2 className="size-10 animate-spin text-indigo-500" />
            <p className="max-w-md px-6 text-center text-sm font-medium">
              Gemini 인텔리전스 에이전트가 실시간 트렌드 분석 및 리포트를 생성
              중입니다 (약 5~10초 소요)…
            </p>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="h-auto w-full flex-wrap sm:w-fit">
            <TabsTrigger value="graph" className="gap-1.5">
              <Network className="size-3.5" />
              지식 신경망
            </TabsTrigger>
            <TabsTrigger value="charts" className="gap-1.5">
              <BarChart3 className="size-3.5" />
              스트림 & 히트맵
            </TabsTrigger>
            <TabsTrigger value="report" className="gap-1.5">
              <FileText className="size-3.5" />
              텍스트 리포트
            </TabsTrigger>
          </TabsList>

          <TabsContent value="graph">
            <KnowledgeGraphPanel
              key={`graph-${panelKey}`}
              selectedDate={selectedDate}
            />
          </TabsContent>

          <TabsContent value="charts">
            <div className="flex flex-col gap-4">
              <Suspense fallback={<TabPanelFallback />}>
                <TrendStreamGraph
                  key={`stream-${panelKey}`}
                  selectedDate={selectedDate}
                />
              </Suspense>
              <Suspense fallback={<TabPanelFallback />}>
                <TrendHeatmap key={`heatmap-${refreshKey}`} />
              </Suspense>
            </div>
          </TabsContent>

          <TabsContent value="report">
            <Suspense fallback={<TabPanelFallback />}>
              <TrendReportViewer
                key={`report-${panelKey}`}
                selectedDate={selectedDate}
              />
            </Suspense>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
