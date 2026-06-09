"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { analyzeTrend } from "@/lib/api/trend";
import { ROUTES } from "@/lib/routes";

interface AggregatorAnalyzeButtonProps {
  agentSlug: string;
}

export function AggregatorAnalyzeButton({
  agentSlug,
}: AggregatorAnalyzeButtonProps) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setIsLoading(true);
    setError(null);

    try {
      const { post_id } = await analyzeTrend();
      router.push(ROUTES.trendPost(agentSlug, post_id));
    } catch (cause) {
      const message =
        cause instanceof Error
          ? cause.message
          : "알 수 없는 오류가 발생했습니다.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button
        type="button"
        size="lg"
        className="w-full"
        onClick={handleAnalyze}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            분석 중...
          </>
        ) : (
          "실시간 트렌드 분석 및 리포트 발행"
        )}
      </Button>
      {error && (
        <p className="text-destructive text-sm" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
