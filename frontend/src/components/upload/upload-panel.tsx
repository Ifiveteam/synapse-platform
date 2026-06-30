import { useCallback, useEffect, useRef, useState } from "react";

import { useAuthStore } from "@/stores/auth";
import { uploadLocalStorage } from "@/lib/upload-local-storage";
import { API_BASE_URL } from "@/lib/env";
import { connectDriveFolder } from "@/lib/google-picker";
import { getDriveConnection, type DriveConnection } from "@/api/takeout";

const API = `${API_BASE_URL}/api/v1`;

type Tab = "upload" | "drive" | "guide";
type UploadStatus = "idle" | "uploading" | "polling" | "success" | "error";

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
    const saved = localStorage.getItem(uploadLocalStorage.directUploadTask);
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
          localStorage.removeItem(uploadLocalStorage.directUploadTask);
          setStatus("success");
          setMessage(`완료! ${d.processed}개 영상 저장됨`);
          onSuccess();
        } else if (d.status === "error") {
          clearInterval(pollingRef.current!);
          localStorage.removeItem(uploadLocalStorage.directUploadTask);
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

        localStorage.setItem(
          uploadLocalStorage.directUploadTask,
          JSON.stringify({ taskId }),
        );
        setStatus("polling");
        setMessage("분석 중... (수분 소요)");

        if (pollingRef.current) clearInterval(pollingRef.current);
        pollingRef.current = setInterval(async () => {
          try {
            const r = await fetch(`${API}/indexer/analyze/${taskId}`);
            const d = await r.json();
            if (d.status === "success") {
              clearInterval(pollingRef.current!);
              localStorage.removeItem(uploadLocalStorage.directUploadTask);
              setStatus("success");
              setMessage(`완료! ${d.processed}개 영상 저장됨`);
              onSuccess();
            } else if (d.status === "error") {
              clearInterval(pollingRef.current!);
              localStorage.removeItem(uploadLocalStorage.directUploadTask);
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
            desc: '"모두 선택 해제" 후 "YouTube 및 YouTube Music"만 체크하세요. (시청 기록 포함)',
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

  useEffect(() => {
    if (!token) return;
    getDriveConnection()
      .then(setConn)
      .catch(() => setConn({ connected: false, folder_name: null }));
  }, [token]);

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
