import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { analyzeTrend } from "@/api/trend";
import { ROUTES } from "@/routes";

const EMAIL_STORAGE_KEY = "aggregator_notify_email";
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

interface AggregatorAnalyzeButtonProps {
  agentSlug: string;
}

export function AggregatorAnalyzeButton({
  agentSlug,
}: AggregatorAnalyzeButtonProps) {
  const navigate = useNavigate();
  const [notifyEmail, setNotifyEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedEmail = notifyEmail.trim();
  const emailInvalid = trimmedEmail.length > 0 && !isValidEmail(trimmedEmail);

  useEffect(() => {
    const saved = localStorage.getItem(EMAIL_STORAGE_KEY);
    if (saved) {
      setNotifyEmail(saved);
    }
  }, []);

  async function handleAnalyze() {
    if (emailInvalid) return;

    setIsLoading(true);
    setError(null);

    const email = trimmedEmail || undefined;
    if (email) {
      localStorage.setItem(EMAIL_STORAGE_KEY, email);
    }

    try {
      const { post_id } = await analyzeTrend(email);
      navigate(ROUTES.trendPost(agentSlug, post_id));
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
    <div className="space-y-3">
      <div className="space-y-2">
        <label
          htmlFor="aggregator-notify-email"
          className="text-sm font-medium"
        >
          분석 완료 알림 · 메일 수신 주소{" "}
          <span className="text-muted-foreground font-normal">(선택)</span>
        </label>
        <input
          id="aggregator-notify-email"
          type="email"
          value={notifyEmail}
          onChange={(event) => setNotifyEmail(event.target.value)}
          placeholder="you@ifive.site"
          className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-10 w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
          autoComplete="email"
          disabled={isLoading}
        />
        {emailInvalid && (
          <p className="text-destructive text-xs">
            올바른 이메일 주소를 입력해 주세요.
          </p>
        )}
        <p className="text-muted-foreground text-xs">
          입력 시 분석이 끝나면 리포트 링크를 메일로 보내 드립니다.
        </p>
      </div>

      <Button
        type="button"
        size="lg"
        className="w-full"
        onClick={handleAnalyze}
        disabled={isLoading || emailInvalid}
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
