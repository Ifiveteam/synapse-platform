"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/stores/auth";
import { fetchMe } from "@/lib/api/auth";

const API = "http://localhost:8000/api/v1";

// ── 타입 ─────────────────────────────────────

interface Video {
  id: number;
  title: string;
  channel: string;
  url: string;
  watched_at: string;
  category: string;
  keywords: string[];
  duration: number;
  is_shorts: boolean;
}

interface DriveFile {
  id: string;
  name: string;
  size: string;
  modifiedTime: string;
}

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

// ── 유틸 ─────────────────────────────────────

function formatDuration(sec: number) {
  if (!sec) return "-";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: string) {
  const n = parseInt(bytes || "0");
  if (n > 1024 * 1024 * 1024) return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
  if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024).toFixed(0)} KB`;
}

// ── 직접 업로드 탭 ─────────────────────────────

const UPLOAD_TASK_KEY = "synapse-upload-task";

function DirectUploadTab({ onSuccess }: { onSuccess: () => void }) {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [message, setMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 마운트 시 이전 진행 중 태스크 복원
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
      } catch { /* 일시적 오류 무시 */ }
    }, 3000);

    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [onSuccess]);

  const handleFile = useCallback(async (file: File) => {
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
      const res = await fetch(`${API}/indexer/analyze`, { method: "POST", body: form });
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
        } catch { /* 일시적 오류 무시 */ }
      }, 3000);
    } catch {
      setStatus("error");
      setMessage("업로드 실패. 서버가 실행 중인지 확인하세요.");
    }
  }, [onSuccess]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

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
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => inputRef.current?.click()}
            className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed py-14 cursor-pointer transition-colors ${
              dragOver ? "border-violet-400 bg-violet-50" : "border-gray-200 hover:border-violet-300 hover:bg-gray-50"
            }`}
          >
            <div className="text-4xl text-gray-300">📁</div>
            <p className="text-sm font-medium text-gray-600">Takeout ZIP을 여기에 끌어다 놓으세요</p>
            <p className="text-xs text-gray-400">또는 클릭해서 파일 선택 · 최대 500MB</p>
            <button className="mt-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 transition-colors">
              파일 선택
            </button>
          </div>
          {status === "error" && (
            <p className="mt-3 text-sm text-red-600 text-center">{message}</p>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-4 py-14">
          {status === "success" ? (
            <>
              <div className="text-4xl">✅</div>
              <p className="text-sm font-semibold text-emerald-700">{message}</p>
              <button
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

// ── 분석 결과 요약 ────────────────────────────

function AnalysisSummary({ stats }: { stats: AnalysisStats }) {
  const noiseRemoved = stats.raw_count - (stats.filtered_count ?? stats.cleaned_count);
  const normalCount = stats.cleaned_count - stats.shorts_count;
  const topCategories = Object.entries(stats.category_stats).slice(0, 3);

  return (
    <div className="rounded-2xl border border-violet-100 bg-violet-50 p-5 space-y-4">
      <p className="text-sm font-semibold text-violet-800">분석 완료</p>

      {/* 처리 단계 */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "파싱", value: stats.raw_count, sub: "원본 항목", color: "text-gray-700" },
          { label: "노이즈 제거", value: noiseRemoved, sub: "광고·삭제됨", color: "text-orange-600" },
          { label: "일반 영상", value: normalCount, sub: "처리 완료", color: "text-violet-700" },
          { label: "숏츠", value: stats.shorts_count, sub: "Shorts 분류", color: "text-red-500" },
        ].map((item) => (
          <div key={item.label} className="rounded-xl bg-white px-3 py-3 text-center border border-gray-100">
            <p className={`text-xl font-bold ${item.color}`}>{item.value.toLocaleString()}</p>
            <p className="text-xs font-medium text-gray-500 mt-0.5">{item.label}</p>
            <p className="text-[10px] text-gray-400">{item.sub}</p>
          </div>
        ))}
      </div>

      {/* 카테고리 */}
      {topCategories.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-2">카테고리 분류</p>
          <div className="flex flex-wrap gap-2">
            {topCategories.map(([cat, count]) => (
              <span key={cat} className="rounded-full bg-white border border-violet-200 px-3 py-1 text-xs text-violet-700">
                {cat} <span className="font-semibold">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400">
        총 <span className="font-semibold text-gray-600">{stats.saved}</span>개 저장됨
      </p>
    </div>
  );
}

// ── 테이크아웃 가이드 ─────────────────────────

const GUIDE_STEPS = [
  { num: 1, title: "takeout.google.com 접속", desc: "구글 테이크아웃 페이지로 이동합니다.", url: "https://takeout.google.com" },
  { num: 2, title: "YouTube 선택", desc: '"모두 선택 해제" 후 YouTube만 체크하세요.' },
  { num: 3, title: "저장 위치 → Google Drive", desc: '"내보내기 방법"에서 Drive에 추가를 선택하세요.' },
  { num: 4, title: "내보내기 요청", desc: '완료되면 Drive에 "Takeout" 폴더가 생성됩니다. (수 분~수 시간 소요)' },
];

function TakeoutGuide({ onNext }: { onNext: () => void }) {
  return (
    <div className="p-6 flex flex-col gap-5">
      <div className="space-y-3">
        {GUIDE_STEPS.map((s) => (
          <div key={s.num} className="flex gap-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
              {s.num}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800">{s.title}</p>
              <p className="mt-0.5 text-xs text-gray-500">{s.desc}</p>
              {s.url && (
                <a href={s.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-violet-600 underline">
                  {s.url} →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
      <button
        onClick={onNext}
        className="w-full rounded-xl bg-violet-600 py-3 text-sm font-semibold text-white hover:bg-violet-700 transition-colors"
      >
        내보내기 완료했어요 → 지금 확인하기
      </button>
    </div>
  );
}

// ── 가이드 탭 ────────────────────────────────

function GuideTab() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-800 mb-1">Google Takeout이란?</p>
        <p className="text-xs text-gray-500 leading-relaxed">
          구글이 제공하는 데이터 내보내기 서비스입니다. YouTube 시청 기록을 ZIP 파일로 내보내
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
            title: "내보내기 방법 → Google Drive",
            desc: '"다음 단계"에서 대상을 "Drive에 추가"로 설정하세요.',
          },
          {
            num: 4,
            title: "내보내기 요청",
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
                <a href={s.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-violet-600 underline">
                  {s.url} →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-amber-50 border border-amber-100 px-4 py-3 text-xs text-amber-700 leading-relaxed">
        💡 내보내기 완료까지 최대 수 시간 걸릴 수 있어요. Drive 탭에서 30초마다 자동으로 파일을 확인합니다.
      </div>
    </div>
  );
}

// ── Drive 연동 탭 ─────────────────────────────

const STORAGE_KEY = "synapse-drive-tasks";
const STATS_KEY = "synapse-drive-stats";

function loadPersistedTasks(): Record<string, { taskId: string; status: string }> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePersistedTasks(tasks: Record<string, { taskId: string; status: string }>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function loadPersistedStats(): Record<string, AnalysisStats> {
  try {
    return JSON.parse(localStorage.getItem(STATS_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePersistedStats(stats: Record<string, AnalysisStats>) {
  localStorage.setItem(STATS_KEY, JSON.stringify(stats));
}

const ANALYZED_KEY = "synapse-analyzed-files";

function loadAnalyzedFiles(): Record<string, AnalysisStats> {
  try { return JSON.parse(localStorage.getItem(ANALYZED_KEY) || "{}"); } catch { return {}; }
}

function DriveTab({ onSuccess, resetKey }: { onSuccess: () => void; resetKey: number }) {
  const [status, setStatus] = useState<"idle" | "searching" | "downloading" | "processing" | "success" | "error" | "no_files" | "waiting">("idle");
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

  const startPolling = useCallback((taskId: string, fileId: string) => {
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
            // 서버 재시작으로 태스크 유실 → 재분석 유도
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
            localStorage.setItem(ANALYZED_KEY, JSON.stringify(analyzed));
            setStats(newStats);
            setStatus("success");
            onSuccess();
          } else {
            setStatus("error");
            setErrorMsg(d.message || "분석 중 오류가 발생했습니다");
          }
        }
      } catch { /* 일시적 오류 무시 */ }
    }, 3000);
  }, [onSuccess]);

  const runAuto = useCallback(async (force = false) => {
    if (!token) return;

    // 이미 완료된 결과가 있고 강제 재분석 아니면 표시만
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
  }, [token, startPolling]);

  // 마운트 시 이전 진행 중 태스크 복원 또는 자동 시작
  useEffect(() => {
    const persisted = loadPersistedTasks();
    const inProgress = Object.entries(persisted).find(
      ([, v]) => v.status !== "success" && v.status !== "error"
    );
    if (inProgress) {
      const [fileId, { taskId, status: s }] = inProgress;
      setStatus(s as "downloading" | "processing");
      startPolling(taskId, fileId);
    } else {
      runAuto();
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [resetKey, runAuto, startPolling]);

  // 파일 없으면 30초마다 재시도
  useEffect(() => {
    if (status !== "waiting") return;
    const poll = setInterval(() => runAuto(), 30000);
    const tick = setInterval(() => setCountdown((c) => (c <= 1 ? 30 : c - 1)), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [status, runAuto]);

  if (!token) {
    return (
      <div className="flex flex-col items-center gap-4 py-14 text-center">
        <p className="text-sm text-gray-500">Google 계정 연동이 필요합니다</p>
        <a
          href="http://localhost:8000/api/v1/auth/login"
          className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 transition-colors"
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
          <button onClick={() => runAuto()} className="text-violet-600 underline">지금 확인</button>
        </div>
        <p className="text-xs text-gray-400">가이드는 <span className="font-medium text-gray-500">? 가이드</span> 탭을 확인하세요</p>
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
        <button onClick={() => runAuto(true)} className="text-xs text-violet-600 underline">다시 시도</button>
      </div>
    );
  }

  if (status === "success" && stats) {
    return (
      <div className="p-6 space-y-4">
        <AnalysisSummary stats={stats} />
        <div className="flex justify-end">
          <button
            onClick={() => runAuto(true)}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
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

// ── 수집 영상 목록 ─────────────────────────────

function VideoList({ refreshKey, onReset }: { refreshKey: number; onReset: () => void }) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/indexer/videos`)
      .then((r) => r.json())
      .then((data) => { setVideos(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [refreshKey]);

  const handleReset = async () => {
    if (!confirm("수집된 영상을 모두 삭제할까요?")) return;
    setResetting(true);
    try {
      await fetch(`${API}/indexer/videos`, { method: "DELETE" });
      onReset();
    } finally {
      setResetting(false);
    }
  };

  if (loading) return null;
  if (videos.length === 0) return null;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-800">
          수집된 영상 <span className="text-sm font-normal text-gray-400">{videos.length}개</span>
        </h2>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="text-xs text-red-400 hover:text-red-600 underline disabled:opacity-50"
        >
          {resetting ? "삭제 중..." : "초기화"}
        </button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-100">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="text-left p-3 font-medium text-gray-500">#</th>
              <th className="text-left p-3 font-medium text-gray-500">제목</th>
              <th className="text-left p-3 font-medium text-gray-500">채널</th>
              <th className="text-left p-3 font-medium text-gray-500">카테고리</th>
              <th className="text-left p-3 font-medium text-gray-500">키워드</th>
              <th className="text-left p-3 font-medium text-gray-500">길이</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v, i) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="p-3 text-gray-400">{i + 1}</td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    {v.is_shorts && (
                      <span className="rounded px-1.5 py-0.5 text-xs bg-red-100 text-red-600 font-medium shrink-0">
                        Shorts
                      </span>
                    )}
                    <a href={v.url} target="_blank" rel="noreferrer" className="hover:underline text-blue-600">
                      {v.title}
                    </a>
                  </div>
                </td>
                <td className="p-3 text-gray-600">{v.channel}</td>
                <td className="p-3">
                  <span className="rounded-full bg-violet-100 text-violet-700 px-2 py-0.5 text-xs">
                    {v.category || "-"}
                  </span>
                </td>
                <td className="p-3 text-gray-500 text-xs">{v.keywords?.slice(0, 3).join(", ") || "-"}</td>
                <td className="p-3 text-gray-500">{formatDuration(v.duration)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── 메인 ─────────────────────────────────────

export default function IndexerPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, setToken, setUser } = useAuthStore();
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshKey, setRefreshKey] = useState(0);

  // OAuth 콜백 토큰 처리
  useEffect(() => {
    const urlToken = searchParams.get("token");
    if (urlToken) {
      setToken(urlToken);
      fetchMe(urlToken).then((u) => { if (u) setUser(u); });
      router.replace("/agents/indexer");
    }
  }, [searchParams, setToken, setUser, router]);

  const [driveResetKey, setDriveResetKey] = useState(0);

  const onSuccess = () => setRefreshKey((k) => k + 1);
  const onReset = () => {
    localStorage.removeItem(STATS_KEY);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ANALYZED_KEY);
    setDriveResetKey((k) => k + 1);
    setRefreshKey((k) => k + 1);
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="mb-8">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Agent 1</p>
        <h1 className="mt-0.5 text-3xl font-bold tracking-tight text-gray-900">Indexer</h1>
        <p className="mt-1 text-sm text-gray-500">YouTube 시청 기록을 수집하고 분류합니다</p>
      </div>

      {/* 업로드 카드 */}
      <div className="mb-10 rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-6 pt-5 pb-0">
          <p className="mb-4 text-sm font-semibold text-gray-700">시청 기록 업로드</p>

          <div className="flex gap-0">
            {([
              { id: "upload", icon: "📁", label: "직접 업로드" },
              { id: "drive",  icon: "☁",  label: "Drive 연동" },
              { id: "guide",  icon: "?",  label: "가이드" },
            ] as const).map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 border-b-2 px-4 pb-3 text-sm font-medium transition-colors ${
                  tab === t.id ? "border-violet-600 text-violet-700" : "border-transparent text-gray-400 hover:text-gray-600"
                }`}
              >
                <span className={t.id === "guide" ? "flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px] font-bold" : ""}>
                  {t.icon}
                </span>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {tab === "upload" && <DirectUploadTab onSuccess={onSuccess} />}
        {tab === "drive"  && <DriveTab key={driveResetKey} onSuccess={onSuccess} />}
        {tab === "guide"  && <GuideTab />}
      </div>

      {/* 수집 영상 목록 - 영상 있을 때만 표시 */}
      <VideoList refreshKey={refreshKey} onReset={onReset} />
    </main>
  );
}
