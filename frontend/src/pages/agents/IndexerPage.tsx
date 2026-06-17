import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  UploadPanel,
  resetDriveUploadState,
} from "@/components/upload/upload-panel";
import { API_BASE_URL } from "@/lib/env";
import { youtubeCategoryLabel } from "@/lib/youtube-categories";
import { ROUTES } from "@/routes";
import { useAuthStore } from "@/stores/auth";

const API = `${API_BASE_URL}/api/v1`;

interface Video {
  id: string;
  title: string;
  channel: string;
  url: string;
  watched_at: string;
  youtube_category_id: string;
  tags: string[];
  duration: number;
  is_shorts: boolean;
}

function formatDuration(sec: number) {
  if (!sec) return "-";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function VideoList({ refreshKey, onReset }: { refreshKey: number; onReset: () => void }) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    setLoading(true);
    const token = useAuthStore.getState().token;
    fetch(`${API}/indexer/videos`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((data) => {
        setVideos(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [refreshKey]);

  const handleReset = async () => {
    if (!confirm("수집된 영상을 모두 삭제할까요?")) return;
    setResetting(true);
    try {
      const token = useAuthStore.getState().token;
      await fetch(`${API}/indexer/videos`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
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
          type="button"
          onClick={handleReset}
          disabled={resetting}
          className="text-xs text-red-400 underline hover:text-red-600 disabled:opacity-50"
        >
          {resetting ? "삭제 중..." : "초기화"}
        </button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-100">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="p-3 text-left font-medium text-gray-500">#</th>
              <th className="p-3 text-left font-medium text-gray-500">제목</th>
              <th className="p-3 text-left font-medium text-gray-500">채널</th>
              <th className="p-3 text-left font-medium text-gray-500">카테고리</th>
              <th className="p-3 text-left font-medium text-gray-500">키워드</th>
              <th className="p-3 text-left font-medium text-gray-500">길이</th>
            </tr>
          </thead>
          <tbody>
            {videos.map((v, i) => (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="p-3 text-gray-400">
                  <div className="flex items-center gap-1.5">
                    <span>{i + 1}</span>
                    {v.is_shorts && (
                      <span className="rounded bg-red-100 px-1 py-0.5 text-xs leading-none font-medium text-red-600">
                        숏츠
                      </span>
                    )}
                  </div>
                </td>
                <td className="p-3">
                  <a
                    href={v.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {v.title}
                  </a>
                </td>
                <td className="p-3 text-gray-600">{v.channel}</td>
                <td className="p-3">
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs text-violet-700">
                    {youtubeCategoryLabel(v.youtube_category_id)}
                  </span>
                </td>
                <td className="p-3 text-xs text-gray-500">
                  {v.tags?.slice(0, 3).join(", ") || "-"}
                </td>
                <td className="p-3 text-gray-500">{formatDuration(v.duration)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function IndexerPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [refreshKey, setRefreshKey] = useState(0);

  // 구 OAuth URL(/agents/indexer?token=) → 업로드 화면으로
  useEffect(() => {
    const urlToken = searchParams.get("token");
    if (urlToken) {
      navigate(ROUTES.upload, { replace: true });
    }
  }, [searchParams, navigate]);

  const onSuccess = () => setRefreshKey((k) => k + 1);
  const onReset = () => {
    resetDriveUploadState();
    setRefreshKey((k) => k + 1);
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="mb-8">
        <p className="text-xs font-medium tracking-wide text-gray-400 uppercase">Agent 1</p>
        <h1 className="mt-0.5 text-3xl font-bold tracking-tight text-gray-900">Indexer</h1>
        <p className="mt-1 text-sm text-gray-500">YouTube 시청 기록을 수집하고 분류합니다</p>
      </div>

      <div className="mb-10">
        <p className="mb-4 text-sm font-semibold text-gray-700">시청 기록 업로드</p>
        <UploadPanel
          onSuccess={onSuccess}
          showGuideTab
          uploadTabLabel="직접 업로드"
          selectFileLabel="파일 선택"
          className="rounded-2xl border border-gray-200 bg-white shadow-sm"
        />
      </div>

      <VideoList refreshKey={refreshKey} onReset={onReset} />
    </main>
  );
}
