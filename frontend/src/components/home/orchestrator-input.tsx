import { ArrowUp, Mic, Paperclip, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";

export function OrchestratorInput() {
  const user = useAuthStore((s) => s.user);
  const disabled = !user;

  return (
    <div className="shrink-0 px-6 pb-6">
      <div
        className={`border-border flex items-center gap-3 rounded-2xl border bg-card px-4 py-3 shadow-sm ${
          disabled ? "opacity-70" : ""
        }`}
      >
        <Search size={18} className="text-muted-foreground shrink-0" />
        <input
          type="text"
          disabled={disabled}
          placeholder={
            disabled
              ? "로그인 후 오케스트레이터와 대화할 수 있습니다."
              : "Ask Orchestrator anything..."
          }
          className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none disabled:cursor-not-allowed"
        />
        <div className="flex shrink-0 items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="text-muted-foreground size-8"
            disabled={disabled}
          >
            <Paperclip size={16} />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="text-muted-foreground size-8"
            disabled={disabled}
          >
            <Mic size={16} />
          </Button>
          <Button
            type="button"
            size="icon"
            className="size-8 rounded-full"
            disabled={disabled}
          >
            <ArrowUp size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
}
