import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useAuthStore } from "@/stores/auth";
import { API_BASE_URL } from "@/lib/env";
import { connectDriveFolder } from "@/lib/google-picker";
import {
  getDriveConnection,
  listDriveFiles,
  triggerDriveFile,
  type DriveConnection,
  type DriveFile,
} from "@/api/takeout";
import { fetchMyAnalyses } from "@/api/analyses";
import type { AnalysisResultItem } from "@/lib/analyses/types";

const API = `${API_BASE_URL}/api/v1`;

type Tab = "upload" | "drive" | "guide";

/** 업로드 POST 진행 중(서버 소스 생성 전) 임시 표시 항목. */
type UploadingFile = { id: string; fileName: string };

function authHeaders(): HeadersInit {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DirectUploadTab({
  onSuccess,
  selectFileLabel,
}: {
  onSuccess: () => void;
  selectFileLabel: string;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectError, setSelectError] = useState("");
  // 업로드 POST 진행 중(서버 소스 생성 전) 임시 항목 — 나머지는 DB(analyses)가 정본
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  // DB 기반 진행 중 분석 (분류/분석) — /me/analyses와 동일 소스
  const [runningItems, setRunningItems] = useState<AnalysisResultItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const onSuccessRef = useRef(onSuccess);
  useEffect(() => {
    onSuccessRef.current = onSuccess;
  }, [onSuccess]);

  // DB에서 진행 중(running) 분석을 폴링 — 영속 정본이라 새로고침·재시작에도 유지
  const refreshRunning = useCallback(async () => {
    try {
      const items = await fetchMyAnalyses();
      setRunningItems(items.filter((it) => it.status === "running"));
    } catch {
      /* 일시적 오류 무시 — 다음 틱에 재시도 */
    }
  }, []);

  useEffect(() => {
    void refreshRunning();
    const timer = setInterval(() => void refreshRunning(), 3000);
    return () => clearInterval(timer);
  }, [refreshRunning]);

  const selectFile = useCallback((file: File) => {
    if (!file.name.endsWith(".zip") && !file.name.endsWith(".json")) {
      setSelectedFile(null);
      setSelectError("ZIP 또는 JSON 파일만 업로드 가능합니다.");
      return;
    }
    setSelectError("");
    setSelectedFile(file);
  }, []);

  const startAnalysis = useCallback(
    async (file: File) => {
      const id = crypto.randomUUID();
      // 확인 카드를 닫고 즉시 드롭존 복귀 → 다른 파일 계속 추가 가능
      setSelectedFile(null);
      setSelectError("");
      setUploadingFiles((prev) => [...prev, { id, fileName: file.name }]);

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
        if (data.status === "already_completed") {
          toast.info(`${file.name}은(는) 이미 분석된 파일입니다.`);
        } else if (data.status === "already_running") {
          toast.info(`${file.name}은(는) 이미 분석 중입니다.`);
        } else if (!data.task_id) {
          toast.error("분석을 시작하지 못했습니다.");
        } else {
          toast.success(`${file.name} 업로드 완료 — 분석을 시작했어요`);
        }
        // 서버에 소스가 생성됐으니 DB 목록 즉시 갱신
        onSuccessRef.current();
        void refreshRunning();
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : "업로드 실패. 서버가 실행 중인지 확인하세요.",
        );
      } finally {
        setUploadingFiles((prev) => prev.filter((j) => j.id !== id));
      }
    },
    [refreshRunning],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) selectFile(file);
    },
    [selectFile],
  );

  return (
    <div className="p-6">
      <input
        ref={inputRef}
        type="file"
        accept=".zip,.json"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) selectFile(file);
          e.target.value = "";
        }}
      />

      {selectedFile ? (
        <div className="flex flex-col items-center gap-4 rounded-xl border-2 border-violet-200 bg-violet-50/50 py-10">
          <div className="text-4xl">📄</div>
          <div className="text-center">
            <p className="text-sm font-semibold break-all text-gray-800">
              {selectedFile.name}
            </p>
            <p className="mt-0.5 text-xs text-gray-400">
              {formatBytes(selectedFile.size)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void startAnalysis(selectedFile)}
              className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-700"
            >
              분석 시작
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedFile(null);
                setSelectError("");
              }}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
            >
              다른 파일
            </button>
          </div>
        </div>
      ) : (
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
          <p className="text-xs text-gray-400">모든 동영상과 파일 권장 · 최대 500MB</p>
          <button
            type="button"
            className="mt-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-700"
          >
            {selectFileLabel}
          </button>
        </div>
      )}

      {selectError && (
        <p className="mt-3 text-center text-sm text-red-600">{selectError}</p>
      )}

      {/* 진행 중 목록 — DB(analyses) 정본 + 업로드 POST 중 임시 항목.
          완료되면 자동으로 사라지고 결과는 '활동 이력'에서 확인. */}
      {(uploadingFiles.length > 0 || runningItems.length > 0) && (
        <div className="mt-5 space-y-2">
          {uploadingFiles.map((f) => (
            <div
              key={f.id}
              className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3"
            >
              <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
              <p className="min-w-0 flex-1 truncate text-sm font-medium text-gray-700">
                {f.fileName}
              </p>
              <span className="shrink-0 text-xs font-medium text-violet-600">
                업로드 중...
              </span>
            </div>
          ))}
          {runningItems.map((it) => (
            <div
              key={it.id}
              className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-3"
            >
              <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
              <p className="min-w-0 flex-1 truncate text-sm font-medium text-gray-700">
                {it.title}
              </p>
              <span className="shrink-0 text-xs font-medium text-violet-600">
                {it.stage === "indexing" ? "분류 중" : "분석 중"}
              </span>
            </div>
          ))}
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
            title: "YouTube만 선택 + 형식 JSON 권장",
            desc: '"모두 선택 해제" 후 "YouTube 및 YouTube Music"만 체크하세요. → "여러 형식" 버튼에서 "기록(시청 기록)"을 JSON으로 바꾸면 가장 정확합니다. (HTML도 지원하지만 시각 정확도는 JSON이 더 좋아요.)',
          },
          {
            num: 3,
            title: "받는 방법 → Google Drive",
            desc: 'ZIP 형식 + "Drive에 추가"로 설정합니다. 정기 분석을 원하면 "2개월마다 1년 동안"으로 설정하면 새 기록이 폴더에 자동으로 쌓입니다.',
          },
          {
            num: 4,
            title: "Drive 폴더 1회 연동",
            desc: '[Drive 연동] 탭에서 "폴더 연동"으로 Takeout 폴더를 선택하세요. 이후 새 Takeout이 쌓일 때마다 자동으로 분석됩니다. 전체 드라이브 권한은 필요 없어요.',
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
        내보내기 완료까지 수 분~수 시간 걸릴 수 있어요. 폴더를 한 번 연동해두면 새 파일이
        쌓일 때마다 자동 분석되고, 급하면 [직접 업로드] 탭으로 ZIP을 바로 올릴 수도 있어요.
      </div>
    </div>
  );
}

function DriveTab({
  onSuccess,
}: {
  onSuccess: () => void;
  resetKey: number;
  showGuideHint: boolean;
}) {
  const token = useAuthStore((s) => s.token);
  const [conn, setConn] = useState<DriveConnection | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getDriveConnection()
      .then(setConn)
      .catch(() => setConn({ connected: false, folder_name: null }));
  }, [token]);

  const connected = Boolean(conn?.connected);

  const refreshFiles = useCallback(async () => {
    try {
      const r = await listDriveFiles();
      setFiles(r.files);
    } catch {
      /* 일시적 오류 무시 */
    }
  }, []);

  // 연동됐으면 폴더 파일 목록 로드 + 상태 갱신 폴링 (분석중→분석됨 반영)
  useEffect(() => {
    if (!token || !connected) return;
    void refreshFiles();
    const timer = setInterval(() => void refreshFiles(), 5000);
    return () => clearInterval(timer);
  }, [token, connected, refreshFiles]);

  const handleTriggerFile = useCallback(
    async (file: DriveFile) => {
      setTriggeringId(file.id);
      try {
        const d = await triggerDriveFile(file.id);
        if (d.status === "started") {
          toast.success(`${file.name ?? "파일"} 분석을 시작했어요`);
          onSuccess();
        } else if (d.status === "already_completed") {
          toast.info("이미 분석된 파일입니다.");
        } else if (d.status === "already_running") {
          toast.info("이미 분석 중입니다.");
        } else {
          toast.error("분석을 시작하지 못했습니다.");
        }
        void refreshFiles();
      } catch {
        toast.error("요청에 실패했습니다.");
      } finally {
        setTriggeringId(null);
      }
    },
    [onSuccess, refreshFiles],
  );

  const handleConnect = useCallback(async () => {
    setConnecting(true);
    setError("");
    try {
      const r = await connectDriveFolder();
      setConn({ connected: true, folder_name: r.folderName });
      setMessage("폴더가 연동됐습니다. 새 Takeout은 자동으로 분석됩니다.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "폴더 연동 실패");
    } finally {
      setConnecting(false);
    }
  }, []);

  const handleAnalyzeNow = useCallback(async () => {
    setAnalyzing(true);
    setError("");
    setMessage("");
    try {
      const res = await fetch(`${API}/takeout/drive/auto`, {
        method: "POST",
        headers: authHeaders(),
      });
      const d = await res.json();
      if (d.status === "started") {
        setMessage("분석을 시작했습니다. 진행상황은 '개인성향 분석 목록'에서 확인하세요.");
        onSuccess();
      } else if (d.status === "no_files") {
        setMessage("연동 폴더에 분석할 Takeout이 없습니다.");
      } else if (d.status === "already_completed") {
        setMessage("이미 분석된 파일입니다.");
      } else if (d.status === "already_running") {
        setMessage("이미 분석이 진행 중입니다.");
      } else {
        setError("분석을 시작하지 못했습니다.");
      }
    } catch {
      setError("요청에 실패했습니다.");
    } finally {
      setAnalyzing(false);
    }
  }, [onSuccess]);

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

  return (
    <div className="space-y-4 p-6">
      <div className="rounded-2xl border border-violet-100 bg-violet-50 p-5">
        <p className="text-sm font-semibold text-violet-800">
          {conn?.connected ? "Takeout 폴더 연동됨" : "Takeout 폴더 연동"}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-violet-700">
          {conn?.connected
            ? `${conn.folder_name ?? "(이름 없음)"} · 새 Takeout이 쌓이면 자동으로 감지·분석됩니다.`
            : "Takeout 폴더를 1회 연동하면 이후 자동으로 감지·분석합니다. 전체 드라이브 권한은 필요 없어요."}
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleConnect()}
            disabled={connecting}
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
          >
            {connecting ? "연동 중..." : conn?.connected ? "폴더 변경" : "폴더 연동"}
          </button>
          {conn?.connected && (
            <button
              type="button"
              onClick={() => void handleAnalyzeNow()}
              disabled={analyzing}
              className="rounded-lg border border-violet-300 bg-white px-4 py-2 text-sm font-semibold text-violet-700 transition-colors hover:bg-violet-100 disabled:opacity-50"
            >
              {analyzing ? "시작 중..." : "지금 분석"}
            </button>
          )}
        </div>
      </div>

      {message && <p className="text-sm text-emerald-700">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {connected && files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500">
            폴더 내 Takeout 파일 · 새 파일을 눌러 분석
          </p>
          {files.map((f) => {
            const selectable = f.status === "new" || f.status === "failed";
            const isTriggering = triggeringId === f.id;
            const label =
              f.status === "completed"
                ? "분석됨"
                : f.status === "running"
                  ? "분석 중"
                  : f.status === "failed"
                    ? "재시도"
                    : "분석하기";
            return (
              <button
                key={f.id}
                type="button"
                disabled={!selectable || isTriggering}
                onClick={() => void handleTriggerFile(f)}
                className={`flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors ${
                  selectable
                    ? "cursor-pointer border-violet-200 bg-white hover:bg-violet-50"
                    : "cursor-not-allowed border-gray-100 bg-gray-50 opacity-60"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p
                    className={`truncate text-sm font-medium ${
                      selectable ? "text-gray-800" : "text-gray-500"
                    }`}
                  >
                    {f.name ?? "(이름 없음)"}
                  </p>
                  {f.modified_time && (
                    <p className="text-xs text-gray-400">
                      {new Date(f.modified_time).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                    f.status === "completed"
                      ? "bg-gray-100 text-gray-400"
                      : f.status === "running"
                        ? "bg-amber-50 text-amber-600"
                        : f.status === "failed"
                          ? "bg-red-50 text-red-600"
                          : "bg-violet-100 text-violet-700"
                  }`}
                >
                  {isTriggering ? "시작 중..." : label}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <p className="text-xs text-gray-400">
        분석 진행상황과 결과는 좌측 '개인성향 분석 목록'에서 확인할 수 있어요.
      </p>
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
  const [tab, setTab] = useState<Tab>(showGuideTab ? "guide" : "upload");

  const handleSuccess = () => {
    onSuccess?.();
  };

  const tabs = [
    ...(showGuideTab
      ? [{ id: "guide" as const, icon: "?", label: "Takeout 가이드" }]
      : []),
    { id: "upload" as const, icon: "📁", label: uploadTabLabel },
    { id: "drive" as const, icon: "☁", label: driveTabLabel },
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
