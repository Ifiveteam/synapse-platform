import { useCallback, useEffect, useState } from "react";

import { GraphListView } from "@/components/profiler/graph-list-view";
import { ForceGraphCanvas } from "@/components/profiler/force-graph-canvas";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/api/client";
import { getGraph } from "@/api/profiler";
import type { GraphViewData } from "@/api/types/profiler";

type GraphSubTab = "visual" | "list";
type GraphKind = "taste" | "knowledge";

interface GraphPanelProps {
  userId: string;
  profileComputedAt?: string | null;
}

export function GraphPanel({ userId, profileComputedAt }: GraphPanelProps) {
  const [kind, setKind] = useState<GraphKind>("taste");
  const [subTab, setSubTab] = useState<GraphSubTab>("visual");
  const [graph, setGraph] = useState<GraphViewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getGraph(userId, kind);
      setGraph(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "그래프를 불러오지 못했습니다.");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [userId, kind]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph, profileComputedAt]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant={kind === "taste" ? "default" : "outline"}
            size="sm"
            onClick={() => setKind("taste")}
          >
            취향
          </Button>
          <Button
            type="button"
            variant={kind === "knowledge" ? "default" : "outline"}
            size="sm"
            onClick={() => setKind("knowledge")}
          >
            지식 탐색
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void loadGraph()}
            disabled={loading}
          >
            새로고침
          </Button>
        </div>

        <div className="flex gap-1 rounded-lg border p-1">
          <Button
            type="button"
            variant={subTab === "visual" ? "default" : "ghost"}
            size="sm"
            onClick={() => setSubTab("visual")}
          >
            시각화
          </Button>
          <Button
            type="button"
            variant={subTab === "list" ? "default" : "ghost"}
            size="sm"
            onClick={() => setSubTab("list")}
          >
            목록
          </Button>
        </div>
      </div>

      <Card className="border-0 shadow-none">
        <CardHeader className="px-0 pt-0">
          <CardTitle className="text-lg">
            {subTab === "visual" ? "관계 그래프" : "노드 · 엣지 목록"}
          </CardTitle>
          <CardDescription>
            {kind === "taste"
              ? "태그·채널·축이 유사도(연관 weight)로 묶인 무방향 관계 그래프입니다."
              : "도메인 간 무방향 연관 네트워크입니다."}
          </CardDescription>
        </CardHeader>
        <CardContent className="px-0">
          {error && (
            <p className="text-destructive mb-4 text-sm" role="alert">
              {error}
            </p>
          )}

          {loading && !graph && (
            <p className="text-muted-foreground text-sm">그래프 로딩 중…</p>
          )}

          {graph && graph.nodes.length > 0 && subTab === "visual" && (
            <ForceGraphCanvas graph={graph} />
          )}

          {graph && graph.nodes.length > 0 && subTab === "list" && (
            <GraphListView graph={graph} />
          )}

          {graph && graph.nodes.length === 0 && (
            <p className="text-muted-foreground text-sm">표시할 노드가 없습니다.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
