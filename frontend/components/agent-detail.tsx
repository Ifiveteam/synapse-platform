"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";

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

interface AnalyzeResult {
  status: string;
  total: number;
  processed: number;
  category_stats?: Record<string, number>;
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

  useEffect(() => {
    setSelectedAgentId(agent.id);
  }, [agent.id, setSelectedAgentId]);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/v1/indexer/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch {
      setError("API 연결 실패. FastAPI 서버가 실행 중인지 확인해주세요.");
    } finally {
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
          <p className="text-muted-foreground text-sm font-medium">
            Agent {index}
          </p>
          <CardTitle className="text-3xl">{agent.name}</CardTitle>
          <CardDescription className="text-base">
            {agent.description}
          </CardDescription>
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
                    onClick={() =>
                      document.getElementById("file-upload")?.click()
                    }
                  >
                    파일 선택
                  </Button>
                </label>
              </div>

              <Button
                className="w-full"
                onClick={handleAnalyze}
                disabled={!file || loading}
              >
                {loading ? "분석 중..." : "분석 시작"}
              </Button>

              {error && (
                <div className="bg-destructive/10 text-destructive rounded-lg p-4 text-sm">
                  {error}
                </div>
              )}

              {result && (
                <div className="bg-green-50 rounded-lg p-4 space-y-2">
                  <p className="font-medium text-green-800">✅ 분석 완료!</p>
                  <p className="text-sm text-green-700">
                    전체 항목: {result.total}개
                  </p>
                  <p className="text-sm text-green-700">
                    처리 완료: {result.processed}개
                  </p>
                  {result.category_stats && (
                    <div className="mt-3 border-t border-green-200 pt-3 space-y-1">
                      <p className="font-medium text-green-800 mb-2">
                        📊 카테고리 분포
                      </p>
                      {Object.entries(result.category_stats).map(
                        ([key, count]) => (
                          <div
                            key={key}
                            className="flex justify-between text-sm text-green-700"
                          >
                            <span>{CATEGORY_LABELS[key] ?? key}</span>
                            <span>{count}개</span>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {agent.id !== "indexer" && (
            <p className="text-muted-foreground text-sm">
              이 화면에서 {agent.name} 에이전트와의 상호작용 UI를 확장할 수
              있습니다.
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}