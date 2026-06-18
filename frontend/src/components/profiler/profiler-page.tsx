import { Link } from "react-router-dom";
import { ArrowLeft, ArrowLeftRight, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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
import { ApiError } from "@/api/client";
import {
  analyzeProfile,
  getPersonas,
  pollJobUntilDone,
} from "@/api/profiler";
import type {
  JobStatus,
  NotificationPayload,
  PersonaInfo,
  ProfilerResult,
} from "@/api/types/profiler";
import { ROUTES } from "@/routes";
import { useProfilerStore } from "@/stores/profiler";

type TabId = "profile" | "graph" | "compare";

const STATUS_LABEL: Record<JobStatus, string> = {
  pending: "대기 중",
  running: "분석 중",
  completed: "완료",
  failed: "실패",
};

const EMAIL_STORAGE_KEY = "profiler_notify_email";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export function ProfilerPage() {
  const setProfilerResult = useProfilerStore((s) => s.setResult);
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [notifyEmail, setNotifyEmail] = useState("");
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [result, setResult] = useState<ProfilerResult | null>(null);
  const [notification, setNotification] = useState<NotificationPayload | null>(
    null,
  );
  const [loadingPersonas, setLoadingPersonas] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(EMAIL_STORAGE_KEY);
    if (saved) {
      setNotifyEmail(saved);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await getPersonas();
        if (cancelled) return;
        setPersonas(res.personas);
        if (res.personas.length > 0) {
          setSelectedUserId(res.personas[0].id);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "백엔드에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
          );
        }
      } finally {
        if (!cancelled) setLoadingPersonas(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const emailValid = isValidEmail(notifyEmail);

  const runAnalysis = useCallback(async () => {
    if (!selectedUserId || !emailValid) return;
    const email = notifyEmail.trim();
    localStorage.setItem(EMAIL_STORAGE_KEY, email);

    setAnalyzing(true);
    setError(null);
    setResult(null);
    setNotification(null);
    setJobStatus("pending");

    try {
      const { job_id } = await analyzeProfile(selectedUserId, email);
      setJobStatus("running");
      const job = await pollJobUntilDone(job_id);
      setJobStatus(job.status);

      if (job.status === "failed") {
        setError(job.error ?? "분석이 실패했습니다.");
        return;
      }

      if (job.notification) {
        setNotification(job.notification);
      }

      if (job.result) {
        setResult(job.result);
        setProfilerResult(job.result); // Navigator 연동용 전역 store에도 저장
        setActiveTab("profile");
      }
    } catch (err) {
      setJobStatus("failed");
      setError(err instanceof Error ? err.message : "분석 중 오류가 발생했습니다.");
    } finally {
      setAnalyzing(false);
    }
  }, [selectedUserId, notifyEmail, emailValid]);

  const tabs: { id: TabId; label: string; disabled?: boolean }[] = [
    { id: "profile", label: "프로필", disabled: !result },
    { id: "graph", label: "그래프", disabled: !selectedUserId },
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
          데이터라는 거울을 통해 사용자의 현재 상태와 성향을 있는 그대로 비춰주는
          분석가
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
          <CardTitle className="text-lg">페르소나 선택</CardTitle>
          <CardDescription>
            mock 데이터 3명 중 선택 후 분석을 실행하세요
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingPersonas ? (
            <p className="text-muted-foreground flex items-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin" />
              페르소나 목록 로딩…
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-3">
              {personas.map((persona) => (
                <button
                  key={persona.id}
                  type="button"
                  onClick={() => {
                    setSelectedUserId(persona.id);
                    setResult(null);
                    setJobStatus(null);
                    setNotification(null);
                  }}
                  className={`rounded-lg border p-4 text-left text-sm transition-colors ${
                    selectedUserId === persona.id
                      ? "border-primary bg-primary/5 ring-primary ring-1"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <p className="font-semibold">{persona.label}</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    {persona.description}
                  </p>
                  <code className="text-muted-foreground mt-2 block text-xs">
                    {persona.id}
                  </code>
                </button>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <label
              htmlFor="profiler-notify-email"
              className="text-sm font-medium"
            >
              분석 완료 알림 · 메일 수신 주소
            </label>
            <input
              id="profiler-notify-email"
              type="email"
              value={notifyEmail}
              onChange={(event) => setNotifyEmail(event.target.value)}
              placeholder="you@ifive.site"
              className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              autoComplete="email"
            />
            {notifyEmail && !emailValid && (
              <p className="text-destructive text-xs">
                올바른 이메일 주소를 입력해 주세요.
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={() => void runAnalysis()}
              disabled={
                !selectedUserId || !emailValid || analyzing || loadingPersonas
              }
            >
              {analyzing && <Loader2 className="size-4 animate-spin" />}
              {analyzing ? "분석 중…" : "프로필 분석 시작"}
            </Button>
            {jobStatus && (
              <span className="text-muted-foreground text-sm">
                상태: {STATUS_LABEL[jobStatus]}
                {result?.llm_used !== undefined && result && (
                  <> · LLM {result.llm_used ? "사용" : "fallback"}</>
                )}
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

      {activeTab === "graph" && selectedUserId && (
        <GraphPanel
          userId={selectedUserId}
          profileComputedAt={result?.computed_at ?? null}
        />
      )}

      {activeTab === "compare" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowLeftRight size={18} />
              분석 전후 비교
            </CardTitle>
            <CardDescription>
              완료된 개인성향 분석 2개를 선택해 AI 비교 요약과 수치 변화를 확인할 수
              있습니다.
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
