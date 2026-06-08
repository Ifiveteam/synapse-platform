"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Agent } from "@/lib/agents";
import { ROUTES } from "@/lib/routes";
import { useAgentStore } from "@/stores/use-agent-store";

interface AgentDetailProps {
  agent: Agent;
  index: number;
}

interface VideoItem {
  title: string;
  channel: string;
  category: string;
  watched_at: string;
}

interface AnalyzeResult {
  status: string;
  total?: number;
  processed?: number;
  category_stats?: Record<string, number>;
  videos?: VideoItem[];
  message?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  intellectual_curiosity: "지적 호기심",
  self_improvement: "자기계발",
  social_awareness: "사회·시선",
  depth_immersion: "깊이·몰입",
  practical_orientation: "실용 지향",
  emotional_comfort: "정서·위로",
  creative_expression: "창의·표현",
  entertainment_release: "오락·해방",
};

export function AgentDetail({ agent, index }: AgentDetailProps) {
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const setSelectedAgentId = useAgentStore((state) => state.setSelectedAgentId);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setSelectedAgentId(agent.id);
  }, [agent.id, setSelectedAgentId]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const pollResult = (taskId: string) => {
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/indexer/analyze/${taskId}`
        );
        const data = await res.json();
        if (data.status === "success" || data.status === "error") {
          clearInterval(pollingRef.current!);
          setResult(data);
          setLoading(false);
        }
      } catch {
        clearInterval(pollingRef.current!);
        setError("결과 조회 실패");
        setLoading(false);
      }
    }, 3000);
  };

  const handleAnalyze = async (sample = false) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    const endpoint = sample
      ? "http://localhost:8000/api/v1/indexer/analyze/sample"
      : "http://localhost:8000/api/v1/indexer/analyze";

    try {
      const res = await fetch(endpoint, { method: "POST", body: formData });
      const data = await res.json();
      if (data.task_id) pollResult(data.task_id);
    } catch {
      setError("API 연결 실패. FastAPI 서버가 실행 중인지 확인해주세요.");
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-16">
      <Button asChild variant="ghost" className="mb-8 w-fit">
        <Link href={ROUTES.home}>
          <ArrowLeft className="size-4" />
          메인으로 돌아가기
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <p className="text-muted-foreground text-sm font-medium">Agent {index}</p>
          <CardTitle className="text-3xl">{agent.name}</CardTitle>
          <CardDescription className="text-base">{agent.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4 text-sm">
            <p>
              <span className="text-muted-foreground">에이전트 ID:</span>{" "}
              <code className="font-mono">{agent.id}</code>
            </p>
            {selectedAgentId === agent.id && (
              <p className="text-muted-foreground mt-2">
                Zustand 스토어에 현재 에이전트가 선택되었습니다.
              </p>
            )}
          </div>

          {agent.id === "indexer" && (
            <div className="space-y-4">
              <div className="border-2 border-dashed rounded-lg p-6 text-center">
                <input
                  type="file"
                  accept=".json"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <p className="text-muted-foreground text-sm">
                    {file ? file.name : "Google Takeout JSON 파일을 선택하세요"}
                  </p>
                  <Button
                    variant="outline"
                    className="mt-2"
                    type="button"
                    onClick={() => document.getElementById("file-upload")?.click()}
                  >
                    파일 선택
                  </Button>
                </label>
              </div>

              <div className="flex flex-col gap-2">
                <Button
                  className="w-full"
                  onClick={() => handleAnalyze(false)}
                  disabled={!file || loading}
                >
                  {loading ? "분석 중..." : "전체 분석"}
                </Button>
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={() => handleAnalyze(true)}
                  disabled={!file || loading}
                >
                  ⚡ 샘플 분석 (20개)
                </Button>
              </div>

              {loading && (
                <div className="bg-muted rounded-lg p-4 text-sm text-center">
                  <p className="text-muted-foreground">
                    ⏳ 백그라운드에서 분석 중이에요. 잠시만 기다려주세요...
                  </p>
                </div>
              )}

              {error && (
                <div className="bg-destructive/10 text-destructive rounded-lg p-4 text-sm">
                  {error}
                </div>
              )}

              {result?.status === "success" && (
                <div className="space-y-3">
                  <div className="bg-green-50 rounded-lg p-4 space-y-2">
                    <p className="font-medium text-green-800">✅ 분석 완료!</p>
                    <p className="text-sm text-green-700">전체 항목: {result.total}개</p>
                    <p className="text-sm text-green-700">처리 완료: {result.processed}개</p>

                    {result.category_stats && (
                      <div className="border-t border-green-200 pt-3 space-y-1">
                        <p className="font-medium text-green-800 mb-2">📊 카테고리 분포</p>
                        {Object.entries(result.category_stats).map(([key, count]) => (
                          <div key={key} className="flex justify-between text-sm text-green-700">
                            <span>{CATEGORY_LABELS[key] ?? key}</span>
                            <span>{count}개</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {result.videos && result.videos.length > 0 && (
                    <div className="rounded-lg border p-4 space-y-2">
                      <p className="font-medium text-sm">🎬 분석된 영상 목록</p>
                      <div className="max-h-72 overflow-y-auto space-y-2">
                        {result.videos.map((video, i) => (
                          <div key={i} className="bg-muted rounded p-3 text-sm">
                            <p className="font-medium truncate">{video.title}</p>
                            <div className="flex justify-between mt-1">
                              <span className="text-muted-foreground text-xs truncate">
                                {video.channel}
                              </span>
                              <span className="text-xs font-medium text-green-600 ml-2 shrink-0">
                                {CATEGORY_LABELS[video.category] ?? video.category}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {result?.status === "error" && (
                <div className="bg-destructive/10 text-destructive rounded-lg p-4 text-sm">
                  {result.message}
                </div>
              )}
            </div>
          )}

          {agent.id !== "indexer" && (
            <p className="text-muted-foreground text-sm">
              이 화면에서 {agent.name} 에이전트와의 상호작용 UI를 확장할 수 있습니다.
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}