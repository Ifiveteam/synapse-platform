"use client";

import { useEffect, useState } from "react";

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

export default function IndexerPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/indexer/videos")
      .then((r) => r.json())
      .then((data) => {
        setVideos(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const formatDuration = (seconds: number) => {
    if (!seconds) return "-";
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">수집된 영상</h1>
      <p className="text-gray-500 mb-6">총 {videos.length}개</p>

      {loading ? (
        <p className="text-gray-400">불러오는 중...</p>
      ) : videos.length === 0 ? (
        <p className="text-gray-400">수집된 영상이 없습니다.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left p-3 font-medium">#</th>
                <th className="text-left p-3 font-medium">제목</th>
                <th className="text-left p-3 font-medium">채널</th>
                <th className="text-left p-3 font-medium">카테고리</th>
                <th className="text-left p-3 font-medium">키워드</th>
                <th className="text-left p-3 font-medium">길이</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((v, i) => (
                <tr key={v.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 text-gray-400">{i + 1}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {v.is_shorts && (
                        <span className="px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-600 font-medium shrink-0">
                          Shorts
                        </span>
                      )}
                      <a
                        href={v.url}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:underline text-blue-600"
                      >
                        {v.title}
                      </a>
                    </div>
                  </td>
                  <td className="p-3 text-gray-600">{v.channel}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs">
                      {v.category || "-"}
                    </span>
                  </td>
                  <td className="p-3 text-gray-500 text-xs">
                    {v.keywords?.slice(0, 3).join(", ") || "-"}
                  </td>
                  <td className="p-3 text-gray-500">
                    {formatDuration(v.duration)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
