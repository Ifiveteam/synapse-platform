import { useCallback, useEffect, useRef, useState } from "react";

import { useAuthStore } from "@/stores/auth";
import { API_BASE_URL } from "@/lib/env";

const API = `${API_BASE_URL}/api/v1`;

interface AnalysisStats {
  saved: number;
  raw_count: number;
  filtered_count: number;
  cleaned_count: number;
  shorts_count: number;
  category_stats: Record<string, number>;
}

type Tab = "upload" | "drive" | "guide";
type UploadStatus = "idle" | "uploading" | "polling" | "success" | "error";

const UPLOAD_TASK_KEY = "synapse-upload-task";

export const DRIVE_STORAGE_KEY = "synapse-drive-tasks";
export const DRIVE_STATS_KEY = "synapse-drive-stats";
export const DRIVE_ANALYZED_KEY = "synapse-analyzed-files";

function loadPersistedTasks(): Record<string, { taskId: string; status: string }> {
  try {
    return JSON.parse(localStorage.getItem(DRIVE_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePersistedTasks(tasks: Record<string, { taskId: string; status: string }>) {
  localStorage.setItem(DRIVE_STORAGE_KEY, JSON.stringify(tasks));
}

function loadAnalyzedFiles(): Record<string, AnalysisStats> {
  try {
    return JSON.parse(localStorage.getItem(DRIVE_ANALYZED_KEY) || "{}");
  } catch {
    return {};
  }
}

function AnalysisSummary({ stats }: { stats: AnalysisStats }) {
  const noiseRemoved = stats.raw_count - (stats.filtered_count ?? stats.cleaned_count);
  const longCount = stats.cleaned_count - stats.shorts_count;
  const categoryTotal = Object.values(stats.category_stats).reduce((sum, n) => sum + n, 0);
  const topCategories = Object.entries(stats.category_stats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="space-y-4 rounded-2xl border border-violet-100 bg-violet-50 p-5">
      <p className="text-sm font-semibold text-violet-800">분석 완료</p>
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "파싱", value: stats.raw_count, sub: "원본 항목", color: "text-gray-700" },
          { label: "노이즈 제거", value: noiseRemoved, sub: "광고·삭제됨", color: "text-orange-600" },
          { label: "분류 완료", value: stats.cleaned_count, sub: "2개월 시청 기록", color: "text-violet-700" },
          { label: "숏츠", value: stats.shorts_count, sub: `롱폼 ${longCount.toLocaleString()}건`, color: "text-red-500" },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-gray-100 bg-white px-3 py-3 text-center">
            <p className={`text-xl font-bold ${item.color}`}>{item.value.toLocaleString()}</p>
            <p className="mt-0.5 text-xs font-medium text-gray-500">{item.label}</p>
            <p className="text-[10px] text-gray-400">{item.sub}</p>
          </div>
        ))}
      </div>
      {topCategories.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium text-gray-500">
            카테고리 분류 (상위 5 · 합계 {categoryTotal.toLocaleString()}건)
          </p>
          <div className="flex flex-wrap gap-2">
            {topCategories.map(([cat, count]) => (
              <span
                key={cat}
                className="rounded-full border border-violet-200 bg-white px-3 py-1 text-xs text-violet-700"
              >
                {cat} <span className="font-semibold">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      <p className="text-xs text-gray-400">
        DB 샘플 저장 <span className="font-semibold text-gray-600">{stats.saved}</span>건
        {categoryTotal !== stats.cleaned_count && stats.cleaned_count > 0 ? (
          <span className="text-orange-600"> · 분류 합계 불일치</span>
        ) : null}
      </p>
    </div>
  );
}

function authHeaders(): HeadersInit {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function DirectUploadTab({
  onSuccess,
  selectFileLabel,
}: {
  onSuccess: () => void;
  selectFileLabel: string;
}) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [message, setMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(UPLOAD_TASK_KEY);
    if (!saved) return;
    const { taskId } = JSON.parse(saved);
    setStatus("polling");
    setMessage("분석 중... (수분 소요)");

    pollingRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/indexer/analyze/${taskId}`);
        const d = await r.json();
        if (d.status === "success") {
          clearInterval(pollingRef.current!);
          localStorage.removeItem(UPLOAD_TASK_KEY);
          setStatus("success");
          setMessage(`완료! ${d.processed}개 영상 저장됨`);
          onSuccess();
        } else if (d.status === "error") {
          clearInterval(pollingRef.current!);
          localStorage.removeItem(UPLOAD_TASK_KEY);
          setStatus("error");
          setMessage(d.message || "분석 중 오류 발생");
        }
      } catch {
        /* 일시적 오류 무시 */
      }
    }, 3000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [onSuccess]);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".zip") && !file.name.endsWith(".json")) {
        setStatus("error");
        setMessage("ZIP 또는 JSON 파일만 업로드 가능합니다.");
        return;
      }

      setStatus("uploading");
      setMessage("업로드 중...");

      const form = new FormData();
      form.append("file", file);

      try {
        const res = await fetch(`${API}/indexer/analyze`, {
          method: "POST",
          headers: authHeaders(),
          body: form,
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(
            typeof body.detail === "string" ? body.detail : "업로드에 실패했습니다.",
          );
        }
        const data = await res.json();
        const taskId = data.task_id;

        localStorage.setItem(UPLOAD_TASK_KEY, JSON.stringify({ taskId }));
        setStatus("polling");
        setMessage("분석 중... (수분 소요)");

        if (pollingRef.current) clearInterval(pollingRef.current);
        pollingRef.current = setInterval(async () => {
          try {
            const r = await fetch(`${API}/indexer/analyze/${taskId}`);
            const d = await r.json();
            if (d.status === "success") {
              clearInterval(pollingRef.current!);
              localStorage.removeItem(UPLOAD_TASK_KEY);
              setStatus("success");
              setMessage(`완료! ${d.processed}개 영상 저장됨`);
              onSuccess();
            } else if (d.status === "error") {
              clearInterval(pollingRef.current!);
              localStorage.removeItem(UPLOAD_TASK_KEY);
              setStatus("error");
              setMessage(d.message || "분석 중 오류 발생");
            }
          } catch {
            /* 일시적 오류 무시 */
          }
        }, 3000);
      } catch (err) {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "업로드 실패. 서버가 실행 중인지 확인하세요.");
      }
    },
    [onSuccess],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div className="p-6">
      <input
        ref={inputRef}
        type="file"
        accept=".zip,.json"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {status === "idle" || status === "error" ? (
        <>
          <div
            onDrop={onDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => inputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed py-14 transition-colors ${
              dragOver
                ? "border-violet-400 bg-violet-50"
                : "border-gray-200 hover:border-violet-300 hover:bg-gray-50"
            }`}
          >
            <div className="text-4xl text-gray-300">📁</div>
            <p className="text-sm font-medium text-gray-600">
              Takeout ZIP을 여기에 끌어다 놓으세요
            </p>
            <p className="text-xs text-gray-400">
              모든 동영상과 파일 권장 · 최대 500MB
            </p>
            <button
              type="button"
              className="mt-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-700"
            >
              {selectFileLabel}
            </button>
          </div>
          {status === "error" && (
            <p className="mt-3 text-center text-sm text-red-600">{message}</p>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-4 py-14">
          {status === "success" ? (
            <>
              <div className="text-4xl">✅</div>
              <p className="text-sm font-semibold text-emerald-700">{message}</p>
              <button
                type="button"
                onClick={() => setStatus("idle")}
                className="text-xs text-gray-400 underline"
              >
                다시 업로드
              </button>
            </>
          ) : (
            <>
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
              <p className="text-sm text-gray-500">{message}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function GuideTab() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <p className="mb-1 text-sm font-semibold text-gray-800">Google Takeout이란?</p>
        <p className="text-xs leading-relaxed text-gray-500">
          구글이 제공하는 데이터보내기 서비스입니다. YouTube 시청 기록을 ZIP 파일로보내
          Synapse에 연결하면 시청 패턴을 분석할 수 있습니다.
        </p>
      </div>
      <div className="space-y-3">
        {[
          {
            num: 1,
            title: "takeout.google.com 접속",
            desc: "구글 계정으로 로그인 후 Takeout 페이지로 이동합니다.",
            url: "https://takeout.google.com",
          },
          {
            num: 2,
            title: "YouTube만 선택",
            desc: '"모두 선택 해제" 버튼을 누른 뒤 YouTube 항목만 체크하세요.',
          },
          {
            num: 3,
            title: "보내기 방법 → Google Drive",
            desc: '"다음 단계"에서 대상을 "Drive에 추가"로 설정하세요.',
          },
          {
            num: 4,
            title: "보내기 요청",
            desc: "요청 완료 후 구글이 처리하는 데 수 분~수 시간이 걸립니다. Drive에 파일이 생기면 자동으로 감지합니다.",
          },
        ].map((s) => (
          <div key={s.num} className="flex gap-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
              {s.num}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800">{s.title}</p>
              <p className="mt-0.5 text-xs text-gray-500">{s.desc}</p>
              {s.url && (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block text-xs text-violet-600 underline"
                >
                  {s.url} →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-700">
       보내기 완료까지 최대 수 시간 걸릴 수 있어요. Drive 탭에서 30초마다 자동으로 파일을
        확인합니다.
      </div>
    </div>
  );
}

function DriveTab({
  onSuccess,
  resetKey,
  showGuideHint,
}: {
  onSuccess: () => void;
  resetKey: number;
  showGuideHint: boolean;
}) {
  const [status, setStatus] = useState<
    "idle" | "searching" | "downloading" | "processing" | "success" | "error" | "waiting"
  >("idle");
  const [stats, setStats] = useState<AnalysisStats | null>(() => {
    const analyzed = loadAnalyzedFiles();
    const keys = Object.keys(analyzed);
    return keys.length > 0 ? analyzed[keys[keys.length - 1]] : null;
  });
  const [errorMsg, setErrorMsg] = useState("");
  const [fileName, setFileName] = useState("");
  const [countdown, setCountdown] = useState(30);
  const token = useAuthStore((s) => s.token);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback(
    (taskId: string, fileId: string) => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      pollingRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API}/takeout/status/${taskId}`);
          const d = await r.json();
          if (d.status === "downloading") setStatus("downloading");
          if (d.status === "processing") setStatus("processing");
          if (d.status === "success" || d.status === "error" || d.status === "not_found") {
            clearInterval(pollingRef.current!);
            pollingRef.current = null;
            savePersistedTasks({});
            if (d.status === "not_found") {
              setStatus("error");
              setErrorMsg("서버가 재시작되어 분석이 중단됐습니다. 재분석을 눌러주세요.");
              return;
            }
            if (d.status === "success") {
              const newStats: AnalysisStats = {
                saved: d.saved ?? 0,
                raw_count: d.raw_count ?? 0,
                filtered_count: d.filtered_count ?? 0,
                cleaned_count: d.cleaned_count ?? 0,
                shorts_count: d.shorts_count ?? 0,
                category_stats: d.category_stats ?? {},
              };
              const analyzed = loadAnalyzedFiles();
              analyzed[fileId] = newStats;
              localStorage.setItem(DRIVE_ANALYZED_KEY, JSON.stringify(analyzed));
              setStats(newStats);
              setStatus("success");
              onSuccess();
            } else {
              setStatus("error");
              setErrorMsg(d.message || "분석 중 오류가 발생했습니다");
            }
          }
        } catch {
          /* 일시적 오류 무시 */
        }
      }, 3000);
    },
    [onSuccess],
  );

  const runAuto = useCallback(
    async (force = false) => {
      if (!token) return;

      const analyzed = loadAnalyzedFiles();
      if (!force && Object.keys(analyzed).length > 0) {
        const lastStats = Object.values(analyzed).at(-1)!;
        setStats(lastStats);
        setStatus("success");
        return;
      }

      setStatus("searching");
      try {
        const res = await fetch(`${API}/takeout/drive/auto`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();

        if (data.status === "no_files") {
          setStatus("waiting");
          return;
        }

        setFileName(data.file_name || "");
        setStatus("downloading");

        const persisted = loadPersistedTasks();
        persisted[data.file_id] = { taskId: data.task_id, status: "downloading" };
        savePersistedTasks(persisted);

        startPolling(data.task_id, data.file_id);
      } catch {
        setStatus("error");
        setErrorMsg("Drive 연결에 실패했습니다");
      }
    },
    [token, startPolling],
  );

  useEffect(() => {
    const persisted = loadPersistedTasks();
    const inProgress = Object.entries(persisted).find(
      ([, v]) => v.status !== "success" && v.status !== "error",
    );
    if (inProgress) {
      const [fileId, { taskId, status: s }] = inProgress;
      setStatus(s as "downloading" | "processing");
      startPolling(taskId, fileId);
    } else {
      runAuto();
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [resetKey, runAuto, startPolling]);

  useEffect(() => {
    if (status !== "waiting") return;
    const poll = setInterval(() => runAuto(), 30000);
    const tick = setInterval(() => setCountdown((c) => (c <= 1 ? 30 : c - 1)), 1000);
    return () => {
      clearInterval(poll);
      clearInterval(tick);
    };
  }, [status, runAuto]);

  if (!token) {
    return (
      <div className="flex flex-col items-center gap-4 py-14 text-center">
        <p className="text-sm text-gray-500">Google 계정 연동이 필요합니다</p>
        <a
          href={`${API}/auth/login`}
          className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-700"
        >
          Google 로그인
        </a>
      </div>
    );
  }

  if (status === "searching") {
    return (
      <div className="flex flex-col items-center gap-3 py-14">
        <div className="h-7 w-7 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
        <p className="text-sm text-gray-500">Drive에서 Takeout 파일 탐색 중...</p>
      </div>
    );
  }

  if (status === "waiting") {
    return (
      <div className="flex flex-col items-center gap-3 py-14 text-center">
        <div className="h-7 w-7 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
        <p className="text-sm text-gray-500">Drive에서 Takeout 파일을 기다리는 중...</p>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>{countdown}초 후 자동 재확인</span>
          <span>·</span>
          <button type="button" onClick={() => runAuto()} className="text-violet-600 underline">
            지금 확인
          </button>
        </div>
        {showGuideHint && (
          <p className="text-xs text-gray-400">
            가이드는 <span className="font-medium text-gray-500">? 가이드</span> 탭을 확인하세요
          </p>
        )}
      </div>
    );
  }

  if (status === "downloading" || status === "processing") {
    return (
      <div className="flex flex-col items-center gap-3 py-14 text-center">
        <div className="h-7 w-7 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
        <p className="text-sm font-medium text-gray-700">
          {status === "downloading" ? "파일 다운로드 중..." : "분석 중..."}
        </p>
        {fileName && <p className="text-xs text-gray-400">{fileName}</p>}
        <p className="text-xs text-gray-400">페이지를 벗어나도 계속 진행됩니다</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex flex-col items-center gap-3 py-14 text-center">
        <p className="text-sm text-red-500">{errorMsg}</p>
        <button type="button" onClick={() => runAuto(true)} className="text-xs text-violet-600 underline">
          다시 시도
        </button>
      </div>
    );
  }

  if (status === "success" && stats) {
    return (
      <div className="space-y-4 p-6">
        <AnalysisSummary stats={stats} />
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => runAuto(true)}
            className="text-xs text-gray-400 underline hover:text-gray-600"
          >
            재분석
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 py-14">
      <div className="h-7 w-7 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
      <p className="text-sm text-gray-400">연결 중...</p>
    </div>
  );
}

export interface UploadPanelProps {
  onSuccess?: () => void;
  showGuideTab?: boolean;
  uploadTabLabel?: string;
  driveTabLabel?: string;
  selectFileLabel?: string;
  className?: string;
}

export function UploadPanel({
  onSuccess,
  showGuideTab = false,
  uploadTabLabel = "파일 직접 업로드",
  driveTabLabel = "Drive 연동",
  selectFileLabel = "파일 직접 선택",
  className,
}: UploadPanelProps) {
  const [tab, setTab] = useState<Tab>("upload");

  const handleSuccess = () => {
    onSuccess?.();
  };

  const tabs = [
    { id: "upload" as const, icon: "📁", label: uploadTabLabel },
    { id: "drive" as const, icon: "☁", label: driveTabLabel },
    ...(showGuideTab ? [{ id: "guide" as const, icon: "?", label: "가이드" }] : []),
  ];

  return (
    <div className={className ?? "rounded-2xl border border-border bg-card shadow-sm"}>
      <div className="border-b border-border px-6 pt-5 pb-0">
        <div className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 border-b-2 px-4 pb-3 text-sm font-medium transition-colors ${
                tab === t.id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <span
                className={
                  t.id === "guide"
                    ? "flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px] font-bold"
                    : ""
                }
              >
                {t.icon}
              </span>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "upload" && (
        <DirectUploadTab onSuccess={handleSuccess} selectFileLabel={selectFileLabel} />
      )}
      {tab === "drive" && (
        <DriveTab
          resetKey={0}
          onSuccess={handleSuccess}
          showGuideHint={showGuideTab}
        />
      )}
      {tab === "guide" && showGuideTab && <GuideTab />}
    </div>
  );
}

export function resetDriveUploadState() {
  localStorage.removeItem(DRIVE_STATS_KEY);
  localStorage.removeItem(DRIVE_STORAGE_KEY);
  localStorage.removeItem(DRIVE_ANALYZED_KEY);
}
