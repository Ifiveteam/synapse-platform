import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { API_BASE_URL } from "@/lib/env";

const API = `${API_BASE_URL}/api/v1`;
type Path = "none" | "upload" | "drive";

// ── Step 0: Google 로그인 ────────────────────

function StepConnect() {
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-100 text-3xl">🔗</div>
      <div>
        <h2 className="text-xl font-bold text-gray-900">Google 계정 연동</h2>
        <p className="mt-2 text-sm text-gray-500">
          YouTube 시청 기록과 Google Drive에 접근하기 위해
          <br />Google 계정 연동이 필요합니다.
        </p>
      </div>
      <a
        href={`${API}/auth/login`}
        className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-6 py-3 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
      >
        <svg width="18" height="18" viewBox="0 0 18 18">
          <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
          <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
          <path fill="#FBBC05" d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332z"/>
          <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58z"/>
        </svg>
        Google 계정으로 시작하기
      </a>
      <p className="text-xs text-gray-400">Drive 읽기 권한만 요청합니다. 파일을 수정하거나 삭제하지 않습니다.</p>
    </div>
  );
}

// ── Step 1: 방법 선택 ─────────────────────────

function StepChoice({ onChoose }: { onChoose: (p: Path) => void }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-100 text-3xl mx-auto">🤔</div>
        <h2 className="text-xl font-bold text-gray-900">어떻게 시작할까요?</h2>
        <p className="mt-2 text-sm text-gray-500">YouTube 시청 기록 업로드 방법을 선택하세요.</p>
      </div>

      <div className="space-y-3">
        <button
          onClick={() => onChoose("upload")}
          className="w-full flex items-start gap-4 rounded-xl border-2 border-gray-100 bg-white p-5 text-left hover:border-violet-300 hover:bg-violet-50 transition-colors group"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-100 text-xl">📁</div>
          <div>
            <p className="text-sm font-semibold text-gray-800">이미 테이크아웃 ZIP 있음</p>
            <p className="mt-0.5 text-xs text-gray-500">구글 테이크아웃을 미리 받아두셨다면 바로 업로드하세요.</p>
          </div>
        </button>

        <button
          onClick={() => onChoose("drive")}
          className="w-full flex items-start gap-4 rounded-xl border-2 border-gray-100 bg-white p-5 text-left hover:border-violet-300 hover:bg-violet-50 transition-colors group"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-xl">☁</div>
          <div>
            <p className="text-sm font-semibold text-gray-800">처음이에요</p>
            <p className="mt-0.5 text-xs text-gray-500">가이드를 따라 테이크아웃을 진행한 뒤 Drive에서 파일을 확인하고 분석을 시작하세요.</p>
          </div>
        </button>
      </div>
    </div>
  );
}

// ── Step 2A: 직접 업로드 ──────────────────────

function StepUpload({ onDone }: { onDone: () => void }) {
  const [status, setStatus] = useState<"idle" | "uploading" | "polling" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
      setStatus("polling");
      setMessage("분석 중... (수분 소요)");
      const interval = setInterval(async () => {
        const r = await fetch(`${API}/indexer/analyze/${data.task_id}`);
        const d = await r.json();
        if (d.status === "success") {
          clearInterval(interval);
          setStatus("success");
          setMessage(`완료! ${d.processed}개 영상 저장됨`);
          setTimeout(onDone, 1500);
        } else if (d.status === "error") {
          clearInterval(interval);
          setStatus("error");
          setMessage(d.message || "분석 중 오류 발생");
        }
      }, 3000);
    } catch {
      setStatus("error");
      setMessage("업로드 실패. 서버가 실행 중인지 확인하세요.");
    }
  }, [onDone]);

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-orange-100 text-3xl mx-auto">📁</div>
        <h2 className="text-xl font-bold text-gray-900">테이크아웃 ZIP 업로드</h2>
        <p className="mt-2 text-sm text-gray-500">구글 테이크아웃에서 받은 ZIP 파일을 올려주세요.</p>
      </div>

      <input ref={inputRef} type="file" accept=".zip,.json" className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />

      {status === "idle" || status === "error" ? (
        <>
          <div
            onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => inputRef.current?.click()}
            className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed py-12 cursor-pointer transition-colors ${
              dragOver ? "border-violet-400 bg-violet-50" : "border-gray-200 hover:border-violet-300 hover:bg-gray-50"
            }`}
          >
            <div className="text-4xl text-gray-300">📁</div>
            <p className="text-sm font-medium text-gray-600">ZIP을 여기에 끌어다 놓으세요</p>
            <p className="text-xs text-gray-400">또는 클릭해서 파일 선택</p>
            <button className="mt-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 transition-colors">
              파일 선택
            </button>
          </div>
          {status === "error" && <p className="text-sm text-red-600 text-center">{message}</p>}
        </>
      ) : (
        <div className="flex flex-col items-center gap-4 py-10">
          {status === "success" ? (
            <><div className="text-4xl">✅</div><p className="text-sm font-semibold text-emerald-700">{message}</p></>
          ) : (
            <><div className="h-8 w-8 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" /><p className="text-sm text-gray-500">{message}</p></>
          )}
        </div>
      )}
    </div>
  );
}

// ── Step 2B: 테이크아웃 가이드 ───────────────

const GUIDE_STEPS = [
  { num: 1, title: "takeout.google.com 접속", desc: "구글 테이크아웃 페이지로 이동합니다.", url: "https://takeout.google.com" },
  { num: 2, title: "YouTube 선택", desc: '"모두 선택 해제" 후 YouTube만 체크하세요.' },
  { num: 3, title: "저장 위치 → Google Drive", desc: '"내보내기 방법"에서 Drive에 추가를 선택하세요.' },
  { num: 4, title: "내보내기 요청", desc: '완료되면 Drive에 "Takeout" 폴더가 생성됩니다. (수 분~수 시간 소요)' },
];

function StepGuide({ onNext }: { onNext: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-orange-100 text-3xl mx-auto">📦</div>
        <h2 className="text-xl font-bold text-gray-900">YouTube 시청 기록 내보내기</h2>
        <p className="mt-2 text-sm text-gray-500">아래 순서대로 진행해 주세요.</p>
      </div>
      <div className="space-y-3">
        {GUIDE_STEPS.map((s) => (
          <div key={s.num} className="flex gap-4 rounded-xl border border-gray-100 bg-white p-4">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">{s.num}</div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-gray-800">{s.title}</p>
              <p className="mt-0.5 text-xs text-gray-500">{s.desc}</p>
              {s.url && <a href={s.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-violet-600 underline">{s.url} →</a>}
            </div>
          </div>
        ))}
      </div>
      <button onClick={onNext} className="w-full rounded-xl bg-violet-600 py-3 text-sm font-semibold text-white hover:bg-violet-700 transition-colors">
        내보내기 완료 → 파일 대기
      </button>
    </div>
  );
}

// ── Step 3: Drive 자동 감지 ───────────────────

function StepWait({ onDone }: { onDone: () => void }) {
  const user = useAuthStore((s) => s.user);
  const [files, setFiles] = useState<{ id: string; name: string; modifiedTime?: string }[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startAnalysis = useCallback(async (file: { id: string; name: string }) => {
    if (!user) return;
    setTaskStatus("downloading");

    const res = await fetch(`${API}/takeout/drive/trigger/${file.id}`, {
      method: "POST",
      credentials: "include",
    });
    const { task_id } = await res.json();
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      const d = await (await fetch(`${API}/takeout/status/${task_id}`)).json();
      setTaskStatus(d.status);
      if (d.status === "success") {
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
        setTimeout(onDone, 1500);
      }
      if (d.status === "error") {
        clearInterval(pollingRef.current!);
        pollingRef.current = null;
      }
    }, 3000);
  }, [user, onDone]);

  const checkDrive = useCallback(async () => {
    if (!user) return;
    setChecking(true);
    try {
      const data = await (await fetch(`${API}/takeout/drive/files`, {
        credentials: "include",
      })).json();
      const list: { id: string; name: string; modifiedTime?: string }[] = data.files || [];
      const sorted = [...list].sort((a, b) =>
        (b.modifiedTime || "").localeCompare(a.modifiedTime || ""),
      );
      setFiles(sorted);
      if (sorted.length > 0 && !selectedId) {
        setSelectedId(sorted[0].id);
      }
    } finally {
      setChecking(false);
    }
  }, [user, selectedId]);

  useEffect(() => {
    void checkDrive();
    const id = setInterval(() => void checkDrive(), 30000);
    return () => {
      clearInterval(id);
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [checkDrive]);

  const selectedFile = files.find((f) => f.id === selectedId) ?? files[0] ?? null;
  const analyzing = taskStatus === "downloading" || taskStatus === "processing";

  return (
    <div className="flex flex-col gap-6 text-center">
      <div>
        <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-100 text-3xl mx-auto">☁</div>
        <h2 className="text-xl font-bold text-gray-900">Drive 파일 확인</h2>
        <p className="mt-2 text-sm text-gray-500">
          Google Drive에 Takeout ZIP이 보이면 선택 후 분석을 시작하세요.
          <br /><span className="text-xs text-gray-400">30초마다 자동 확인 중</span>
        </p>
      </div>

      {files.length > 0 ? (
        <div className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-4 text-left space-y-3">
          {files.map((file) => (
            <label key={file.id} className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
              <input
                type="radio"
                name="setup-takeout"
                checked={selectedId === file.id}
                onChange={() => setSelectedId(file.id)}
              />
              <span>🗜</span>
              <span className="font-medium truncate">{file.name}</span>
            </label>
          ))}
          <div className="flex items-center gap-2 pt-1">
            {taskStatus === "success" ? (
              <span className="text-sm font-semibold text-emerald-600">분석 완료 ✅</span>
            ) : taskStatus === "error" ? (
              <span className="text-sm text-red-500">오류 발생 ❌</span>
            ) : analyzing ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-violet-200 border-t-violet-600" />
                <span className="text-sm text-violet-600">
                  {taskStatus === "downloading" ? "다운로드 중..." : "분석 중..."}
                </span>
              </>
            ) : (
              <button
                type="button"
                disabled={!selectedFile}
                onClick={() => selectedFile && void startAnalysis(selectedFile)}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
              >
                분석 시작
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-gray-200 py-8">
          {checking
            ? <div className="h-6 w-6 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
            : <p className="text-sm text-gray-400">아직 Drive에 파일이 없습니다</p>
          }
          <button onClick={() => void checkDrive()} className="text-xs text-violet-600 underline">지금 확인하기</button>
        </div>
      )}

      <button onClick={onDone} className="text-xs text-gray-400 underline">나중에 하기 → 메인으로</button>
    </div>
  );
}

// ── 메인 ─────────────────────────────────────

export function SetupPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [step, setStep] = useState(0);
  const [path, setPath] = useState<Path>("none");

  // OAuth 콜백 후 ShellLayout이 refresh 쿠키로 access 발급
  useEffect(() => {
    if (user && step === 0) setStep(1);
  }, [user, step]);

  const handleChoose = (p: Path) => { setPath(p); setStep(2); };
  const handleDone = () => navigate("/upload");
  const handleLogout = () => { logout(); setStep(0); setPath("none"); };

  const stepLabels =
    path === "upload" ? ["Google 연동", "방법 선택", "직접 업로드"] :
    path === "drive"  ? ["Google 연동", "방법 선택", "테이크아웃 가이드", "파일 대기"] :
                        ["Google 연동", "방법 선택"];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        {/* 헤더 */}
        <div className="mb-8 text-center relative">
          {user && (
            <button
              onClick={handleLogout}
              className="absolute right-0 top-0 flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 hover:text-red-500 transition-colors"
            >
              {user.name} · 로그아웃
            </button>
          )}
          <div className="mb-2 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-white font-bold text-lg">S</div>
          <h1 className="text-2xl font-bold text-gray-900">Synapse 시작하기</h1>
        </div>

        {/* 스텝 인디케이터 */}
        <div className="mb-8 flex items-center justify-center gap-2 flex-wrap">
          {stepLabels.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                i < step ? "bg-violet-600 text-white" :
                i === step ? "bg-violet-100 text-violet-700 ring-2 ring-violet-400" :
                "bg-gray-100 text-gray-400"
              }`}>
                {i < step ? "✓" : i + 1}
              </div>
              <span className={`text-xs ${i === step ? "text-violet-700 font-medium" : "text-gray-400"}`}>{label}</span>
              {i < stepLabels.length - 1 && (
                <div className={`h-px w-6 ${i < step ? "bg-violet-400" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* 카드 */}
        <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
          {step === 0 && <StepConnect />}
          {step === 1 && <StepChoice onChoose={handleChoose} />}
          {step === 2 && path === "upload" && <StepUpload onDone={handleDone} />}
          {step === 2 && path === "drive" && <StepGuide onNext={() => setStep(3)} />}
          {step === 3 && path === "drive" && <StepWait onDone={handleDone} />}
        </div>
      </div>
    </div>
  );
}
