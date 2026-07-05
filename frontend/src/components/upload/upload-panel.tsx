import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/env";
import { connectDriveFolder } from "@/lib/google-picker";
import {
  getDriveConnection,
  listDriveFiles,
  sealBatch,
  triggerDriveFile,
  type DriveConnection,
  type DriveFile,
} from "@/api/takeout";
import { fetchMyAnalyses } from "@/api/analyses";
import type { AnalysisResultItem } from "@/lib/analyses/types";

const API = `${API_BASE_URL}/api/v1`;

type Tab = "upload" | "drive";

/** 업로드 POST 진행 중(서버 소스 생성 전) 임시 표시 항목. */
type UploadingFile = { id: string; fileName: string };

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
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
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
      setRunningItems(
        items.filter((it) => it.status === "running" || it.status === "pending"),
      );
    } catch {
      /* 일시적 오류 무시 — 다음 틱에 재시도 */
    }
  }, []);

  useEffect(() => {
    void refreshRunning();
    const timer = setInterval(() => void refreshRunning(), 3000);
    return () => clearInterval(timer);
  }, [refreshRunning]);

  // 여러 파일 선택 — 확장자 검증 후 (파일명+크기) 기준 중복 제거하여 추가
  const addFiles = useCallback((incoming: File[]) => {
    const valid = incoming.filter(
      (f) => f.name.endsWith(".zip") || f.name.endsWith(".json"),
    );
    setSelectError(
      valid.length < incoming.length
        ? "ZIP 또는 JSON 파일만 업로드 가능합니다."
        : "",
    );
    if (valid.length === 0) return;
    setSelectedFiles((prev) => {
      const key = (f: File) => `${f.name}:${f.size}`;
      const seen = new Set(prev.map(key));
      const merged = [...prev];
      for (const f of valid) if (!seen.has(key(f))) merged.push(f);
      return merged;
    });
  }, []);

  const removeSelected = useCallback((idx: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  // 파일 1건 업로드 (진행 중 임시 표시). 결과 상태 문자열 반환.
  const uploadOne = useCallback(
    async (file: File, batchId: string): Promise<string | null> => {
    const id = crypto.randomUUID();
    setUploadingFiles((prev) => [...prev, { id, fileName: file.name }]);
    const form = new FormData();
    form.append("file", file);
    form.append("batch_id", batchId);
    try {
      const res = await fetch(`${API}/indexer/analyze`, {
        method: "POST",
        credentials: "include",
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
        toast.error(`${file.name} 분석을 시작하지 못했습니다.`);
      }
      return data.status ?? null;
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : `${file.name} 업로드 실패`,
      );
      return null;
    } finally {
      setUploadingFiles((prev) => prev.filter((j) => j.id !== id));
    }
  }, []);

  // 선택한 파일 전부 업로드 (동시 POST → 서버에서 유저별 순차 인덱싱)
  const startAll = useCallback(async () => {
    if (selectedFiles.length === 0) return;
    const files = selectedFiles;
    setSelectedFiles([]);
    setSelectError("");
    // 이 클릭 = 한 배치. 업로드 응답을 다 받은 뒤 seal("다 보냄")로 배치를 닫는다.
    const batchId = crypto.randomUUID();
    const results = await Promise.all(files.map((f) => uploadOne(f, batchId)));
    try {
      await sealBatch(batchId);
    } catch {
      // seal 실패 시 서버 자동-seal 안전망이 배치를 마무리한다
    }
    const started = results.filter((r) => r === "started").length;
    if (started > 0) {
      toast.success(`${started}개 파일 업로드 완료 — 분석을 시작했어요`);
    }
    onSuccessRef.current();
    void refreshRunning();
  }, [selectedFiles, uploadOne, refreshRunning]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) {
        addFiles(Array.from(e.dataTransfer.files));
      }
    },
    [addFiles],
  );

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".zip,.json"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) addFiles(Array.from(e.target.files));
          e.target.value = "";
        }}
      />

      {selectedFiles.length > 0 ? (
        <div className="rounded-xl border-2 border-violet-200 bg-violet-50/50 p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">
              선택한 파일 {selectedFiles.length}개
            </p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-xs font-medium text-violet-600 hover:underline"
            >
              + 파일 추가
            </button>
          </div>
          <div className="max-h-64 space-y-1.5 overflow-y-auto">
            {selectedFiles.map((f, i) => (
              <div
                key={`${f.name}:${f.size}:${i}`}
                className="flex items-center gap-2 rounded-lg bg-white px-3 py-2"
              >
                <span className="text-lg">📄</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-800">
                    {f.name}
                  </p>
                  <p className="text-xs text-gray-400">{formatBytes(f.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeSelected(i)}
                  aria-label="제거"
                  className="shrink-0 rounded p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={() => void startAll()}
              className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-violet-700"
            >
              분석 시작 ({selectedFiles.length})
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedFiles([]);
                setSelectError("");
              }}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
            >
              전체 취소
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
            Takeout ZIP을 여기에 끌어다 놓으세요 (여러 개 가능)
          </p>
          <p className="text-xs text-gray-400">
            여러 개 한 번에 선택 가능 · 파일당 최대 500MB
          </p>
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
                {it.status === "pending"
                  ? "대기 중"
                  : it.stage === "indexing"
                    ? "분류 중"
                    : it.stage === "indexed"
                      ? "분류 완료"
                      : "분석 중"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type GuideStep = { num: number; title: string; desc: string; url?: string };

/** 탭 오른쪽에 붙는 가이드 본문 (인트로 + 단계 카드 + 팁). */
function GuideSteps({
  intro,
  steps,
  tip,
}: {
  intro: { title: string; body: string };
  steps: GuideStep[];
  tip: string;
}) {
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-1 text-sm font-semibold text-gray-800">{intro.title}</p>
        <p className="text-xs leading-relaxed text-gray-500">{intro.body}</p>
      </div>
      <div className="space-y-2.5">
        {steps.map((s) => (
          <div
            key={s.num}
            className="flex gap-3 rounded-xl border border-gray-100 bg-gray-50 p-3.5"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">
              {s.num}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800">{s.title}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-gray-500">{s.desc}</p>
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
      <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-2.5 text-xs leading-relaxed text-amber-700">
        {tip}
      </div>
    </div>
  );
}

/** 파일 직접 업로드 탭 가이드 — Takeout ZIP을 내려받아 직접 올리는 흐름. */
function UploadGuide() {
  return (
    <GuideSteps
      intro={{
        title: "Takeout ZIP 준비하기",
        body: "Google Takeout에서 YouTube 기록을 내려받아 왼쪽에 올리면 분석돼요.",
      }}
      steps={[
        {
          num: 1,
          title: "Takeout 접속",
          desc: "구글 로그인 후 Takeout으로 이동.",
          url: "https://takeout.google.com",
        },
        {
          num: 2,
          title: "YouTube만 선택 (JSON 권장)",
          desc: '"모두 선택 해제" → "YouTube 및 YouTube Music"만 체크. 형식은 "기록"을 JSON으로 두면 가장 정확해요.',
        },
        {
          num: 3,
          title: "ZIP으로 내보내기",
          desc: "형식을 ZIP으로 내보낸 뒤 파일을 내려받으세요.",
        },
      ]}
      tip="내려받은 ZIP·JSON을 왼쪽에 끌어다 놓거나 직접 선택하면 바로 분석돼요. 여러 개도 한 번에 가능."
    />
  );
}

/** Drive 연동 탭 가이드 — Takeout을 Drive에 쌓고 폴더를 1회 연동하는 흐름. */
function DriveGuide() {
  return (
    <GuideSteps
      intro={{
        title: "Google Takeout이란?",
        body: "구글의 데이터 내보내기 서비스예요. Takeout을 Drive에 쌓고 폴더를 1회 연동하면 새 기록이 생길 때마다 자동 분석돼요.",
      }}
      steps={[
        {
          num: 1,
          title: "Takeout 접속",
          desc: "구글 로그인 후 Takeout으로 이동.",
          url: "https://takeout.google.com",
        },
        {
          num: 2,
          title: "YouTube만 선택 (JSON 권장)",
          desc: '"모두 선택 해제" → "YouTube 및 YouTube Music"만 체크. 형식은 "기록"을 JSON 권장.',
        },
        {
          num: 3,
          title: "받는 방법 → Drive",
          desc: '"Drive에 추가" 선택. "2개월마다 1년"으로 두면 새 기록이 폴더에 자동으로 쌓여요.',
        },
        {
          num: 4,
          title: "Drive 폴더 연동",
          desc: '왼쪽 "폴더 연동"에서 Takeout 폴더 선택. 이후 자동 분석돼요.',
        },
      ]}
      tip="폴더를 한 번 연동해두면 새 파일이 쌓일 때마다 자동 분석돼요."
    />
  );
}

/** 탭 콘텐츠(좌) + 해당 탭 가이드(우) 2단 레이아웃. showGuides=false면 콘텐츠만. */
function TabWithGuide({
  showGuides,
  guide,
  children,
}: {
  showGuides: boolean;
  guide: React.ReactNode;
  children: React.ReactNode;
}) {
  if (!showGuides) {
    return <div className="p-6">{children}</div>;
  }
  return (
    <div className="grid min-h-0 flex-1 lg:grid-cols-[24rem_minmax(0,1fr)]">
      <aside className="border-border border-b p-6 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:border-r lg:border-b-0">
        {guide}
      </aside>
      <div className="p-6 lg:h-full lg:min-h-0 lg:overflow-y-auto">{children}</div>
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
  const user = useAuthStore((s) => s.user);
  const [conn, setConn] = useState<DriveConnection | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchRunning, setBatchRunning] = useState(false);

  useEffect(() => {
    if (!user) return;
    getDriveConnection()
      .then(setConn)
      .catch(() => setConn({ connected: false, folder_name: null }));
  }, [user]);

  const connected = Boolean(conn?.connected);

  const refreshFiles = useCallback(async () => {
    try {
      const r = await listDriveFiles();
      setFiles(r.files);
      // 더 이상 선택 불가(분석 시작됨/완료)해진 파일은 선택 해제
      const selectable = new Set(
        r.files
          .filter((f) => f.status === "new" || f.status === "failed")
          .map((f) => f.id),
      );
      setSelectedIds((prev) => {
        const next = new Set([...prev].filter((id) => selectable.has(id)));
        return next.size === prev.size ? prev : next;
      });
    } catch {
      /* 일시적 오류 무시 */
    }
  }, []);

  // 연동됐으면 폴더 파일 목록 로드 + 상태 갱신 폴링 (대기중→분류중→분석됨 반영)
  useEffect(() => {
    if (!user || !connected) return;
    void refreshFiles();
    const timer = setInterval(() => void refreshFiles(), 5000);
    return () => clearInterval(timer);
  }, [user, connected, refreshFiles]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // 여러 파일 한 번에 분석 큐에 등록 (유저별 직렬 처리라 안전)
  const analyzeIds = useCallback(
    async (ids: string[]) => {
      if (ids.length === 0 || batchRunning) return;
      setBatchRunning(true);
      try {
        // 이 클릭 = 한 배치. 트리거를 모두 보낸 뒤 seal로 닫는다.
        const batchId = crypto.randomUUID();
        const results = await Promise.all(
          ids.map((id) => triggerDriveFile(id, batchId).catch(() => null)),
        );
        try {
          await sealBatch(batchId);
        } catch {
          // seal 실패 시 서버 자동-seal 안전망이 처리
        }
        const started = results.filter((r) => r?.status === "started").length;
        if (started > 0) {
          toast.success(`${started}개 파일 분석을 시작했어요`);
          onSuccess();
        } else {
          toast.info("새로 시작한 분석이 없습니다.");
        }
        setSelectedIds(new Set());
        void refreshFiles();
      } finally {
        setBatchRunning(false);
      }
    },
    [batchRunning, onSuccess, refreshFiles],
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

  if (!user) {
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

  // 아직 분석 안 한(새/실패) 파일 — "전체 분석" 대상
  const newFiles = files.filter(
    (f) => f.status === "new" || f.status === "failed",
  );

  return (
    <div className="space-y-4">
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
        </div>
      </div>

      {message && <p className="text-sm text-emerald-700">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {connected && files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold text-gray-500">
              폴더 내 Takeout 파일 · 선택해서 분석
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={batchRunning || selectedIds.size === 0}
                onClick={() => void analyzeIds([...selectedIds])}
                className="rounded-lg border border-violet-300 bg-white px-3 py-1.5 text-xs font-semibold text-violet-700 transition-colors hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                선택 분석{selectedIds.size > 0 ? ` (${selectedIds.size})` : ""}
              </button>
              <button
                type="button"
                disabled={batchRunning || newFiles.length === 0}
                onClick={() => void analyzeIds(newFiles.map((f) => f.id))}
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
              >
                {batchRunning ? "시작 중..." : `전체 분석${newFiles.length ? ` (${newFiles.length})` : ""}`}
              </button>
            </div>
          </div>
          {files.map((f) => {
            const selectable = f.status === "new" || f.status === "failed";
            const checked = selectedIds.has(f.id);
            const label =
              f.status === "completed"
                ? "완료"
                : f.status === "pending"
                  ? "대기 중"
                  : f.status === "running"
                    ? f.stage === "indexing"
                      ? "분류 중"
                      : f.stage === "indexed"
                        ? "분류 완료"
                        : "분석 중"
                    : f.status === "failed"
                      ? "재시도"
                      : "새 파일";
            return (
              <div
                key={f.id}
                role={selectable ? "button" : undefined}
                onClick={() => selectable && toggleSelect(f.id)}
                className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                  selectable
                    ? "cursor-pointer border-violet-200 bg-white hover:bg-violet-50"
                    : "cursor-not-allowed border-gray-100 bg-gray-50 opacity-60"
                } ${checked ? "ring-2 ring-violet-400" : ""}`}
              >
                {selectable && (
                  <input
                    type="checkbox"
                    checked={checked}
                    readOnly
                    className="h-4 w-4 shrink-0 accent-violet-600"
                  />
                )}
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
                        : f.status === "pending"
                          ? "bg-amber-50 text-amber-600"
                          : f.status === "failed"
                            ? "bg-red-50 text-red-600"
                            : "bg-violet-100 text-violet-700"
                  }`}
                >
                  {label}
                </span>
              </div>
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
  /** 각 탭 오른쪽에 해당 탭 전용 가이드를 표시. */
  showGuides?: boolean;
  uploadTabLabel?: string;
  driveTabLabel?: string;
  selectFileLabel?: string;
  className?: string;
}

export function UploadPanel({
  onSuccess,
  showGuides = false,
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
  ];

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col",
        className ?? "rounded-2xl border border-border bg-card shadow-sm",
      )}
    >
      <div className="border-b border-border px-6 pt-5 pb-0 shrink-0">
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
              <span>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === "upload" && (
        <TabWithGuide showGuides={showGuides} guide={<UploadGuide />}>
          <DirectUploadTab
            onSuccess={handleSuccess}
            selectFileLabel={selectFileLabel}
          />
        </TabWithGuide>
      )}
      {tab === "drive" && (
        <TabWithGuide showGuides={showGuides} guide={<DriveGuide />}>
          <DriveTab resetKey={0} onSuccess={handleSuccess} showGuideHint={showGuides} />
        </TabWithGuide>
      )}
    </div>
  );
}
