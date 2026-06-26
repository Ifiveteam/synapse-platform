import { Link } from "react-router-dom";
import { ArrowLeft, ArrowLeftRight, Loader2 } from "lucide-react";
import { useCallback, useState } from "react";

import { GraphPanel } from "@/components/profiler/graph-panel";
import { NotificationBanner } from "@/components/profiler/notification-banner";
import { ProfileResults } from "@/components/profiler/profile-results";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { analyzeProfile, pollJobUntilDone } from "@/api/profiler";
import type { DbProfileResponse, JobStatus, NotificationPayload } from "@/api/types/profiler";
import { ROUTES } from "@/routes";
import { useProfilerStore } from "@/stores/profiler";
import { useAuthStore } from "@/stores/auth";

type TabId = "profile" | "graph" | "compare";

const STATUS_LABEL: Record<JobStatus, string> = {
  pending: "대기 중",
  running: "분석 중",
  completed: "완료",
  failed: "실패",
};

export function ProfilerPage() {
  const user = useAuthStore((s) => s.user);
  const setProfilerResult = useProfilerStore((s) => s.setResult);
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<DbProfileResponse | null>(null);
  const [notification, setNotification] = useState<NotificationPayload | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(async () => {
    setAnalyzing(true);
    setError(null);
    setResult(null);
    setNotification(null);
    setJobStatus("pending");

    try {
      const { job_id } = await analyzeProfile();
      setJobStatus("running");
      const job = await pollJobUntilDone(job_id);
      setJobStatus(job.status);

      if (job.status === "failed") {
        setError(job.error ?? "분석이 실패했습니다.");
        return;
      }
      if (job.notification) setNotification(job.notification);
      if (job.result) {
        setResult(job.result);
        setProfilerResult(job.result);
        setActiveTab("profile");
      }
    } catch (err) {
      setJobStatus("failed");
      setError(err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.");
    } finally {
      setAnalyzing(false);
    }
  }, [setProfilerResult]);

  const tabs: { id: TabId; label: string; disabled?: boolean }[] = [
    { id: "profile", label: "프로필", disabled: !result },
    { id: "graph", label: "그래프", disabled: !user },
    { id: "compare", label: "전후 비교" },
  ];

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12">
      <Button asChild variant="ghost" className="mb-6 w-fit">
        <Link to={ROUTES.home}>
          <ArrowLeft className="size-4" />
          메인으로 돌아가기
        </Link>
      </Button>

      <header className="mb-8">
        <p className="text-muted-foreground mb-1 text-sm font-medium">Agent 5</p>
        <h1 className="text-3xl font-bold tracking-tight">Profiler</h1>
        <p className="text-muted-foreground mt-2 max-w-2xl text-base">
          데이터라는 거울을 통해 사용자의 현재 상태와 성향을 있는 그대로 비춰주는 분석가
        </p>
      </header>

      {notification && (
        <NotificationBanner
          notification={notification}
          onDismiss={() => setNotification(null)}
        />
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">프로필 분석</CardTitle>
          <CardDescription>
            내 YouTube 시청 데이터를 기반으로 성향을 분석합니다
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {user && (
            <div className="border-border rounded-lg border bg-secondary/30 px-4 py-3 text-sm">
              <span className="text-muted-foreground">분석 대상: </span>
              <span className="font-medium">{user.name}</span>
              <span className="text-muted-foreground ml-2">({user.email})</span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={() => void runAnalysis()}
              disabled={!user || analyzing}
            >
              {analyzing && <Loader2 className="size-4 animate-spin" />}
              {analyzing ? "분석 중…" : "프로필 분석 시작"}
            </Button>
            {jobStatus && (
              <span className="text-muted-foreground text-sm">
                상태: {STATUS_LABEL[jobStatus]}
              </span>
            )}
          </div>

          {error && (
            <p className="text-destructive text-sm" role="alert">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="mb-4 flex flex-wrap gap-2 border-b pb-2">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            type="button"
            variant={activeTab === tab.id ? "default" : "ghost"}
            size="sm"
            disabled={tab.disabled}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {activeTab === "profile" && result && <ProfileResults result={result} />}

      {activeTab === "profile" && !result && !analyzing && (
        <p className="text-muted-foreground py-12 text-center text-sm">
          분석을 실행하면 8각 레이더, Layer B, TOP5, 해석이 여기에 표시됩니다.
        </p>
      )}

      {activeTab === "graph" && user && (
        <GraphPanel profileComputedAt={result?.snapshot_date ?? null} />
      )}

      {activeTab === "compare" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowLeftRight size={18} />
              분석 전후 비교
            </CardTitle>
            <CardDescription>
              완료된 개인성향 분석 2개를 선택해 AI 비교 요약과 수치 변화를 확인할 수 있습니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to={ROUTES.myAnalyses}>분석 목록에서 비교하기</Link>
            </Button>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
