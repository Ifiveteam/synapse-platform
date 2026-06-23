import { ArrowUp, Search } from "lucide-react";
import { useRef, useState } from "react";

import { streamCurator } from "@/api/curator";
import type { ChartEntry } from "@/stores/chat";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { useSidebarStore } from "@/stores/sidebar";

export function CuratorInput() {
  const user = useAuthStore((s) => s.user);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sessionId = useChatStore((s) => s.sessionId);
  const { addUserMessage, startAssistantMessage, appendToken, setStatus, addChartEntry, finishAssistantMessage } =
    useChatStore();

  const loadChats = useSidebarStore((s) => s.loadChats);
  const disabled = !user || isStreaming;
  const [focused, setFocused] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    setValue("");
    addUserMessage(trimmed);
    const assistantId = startAssistantMessage();

    try {
      for await (const chunk of streamCurator(trimmed, sessionId)) {
        if (chunk.event === "status") {
          setStatus(assistantId, chunk.content);
        } else if (chunk.event === "chart") {
          try {
            const entry = JSON.parse(chunk.content) as ChartEntry;
            addChartEntry(assistantId, entry);
          } catch {
            // ignore malformed chart data
          }
        } else {
          appendToken(assistantId, chunk.content);
        }
      }
    } catch {
      appendToken(assistantId, "❌ 오류가 발생했습니다.");
    } finally {
      finishAssistantMessage(assistantId);
      void loadChats();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="shrink-0 px-6 pb-6 pt-3">
      <div
        className={`border-border flex items-center gap-3 rounded-2xl border bg-card px-4 py-3 shadow-[0_8px_32px_-4px_rgba(0,0,0,0.18)] ring-1 ring-black/5 outline-none dark:shadow-[0_8px_32px_-4px_rgba(0,0,0,0.5)] dark:ring-white/5 ${
          disabled && !isStreaming ? "opacity-70" : ""
        }`}
        style={focused ? { animation: "input-wave 1.2s ease-out infinite" } : undefined}
      >
        <Search size={18} className="text-muted-foreground shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            !user
              ? "로그인 후 큐레이터와 대화할 수 있습니다."
              : isStreaming
                ? "답변 생성 중..."
                : "큐레이터에게 무엇이든 물어보세요..."
          }
          className="placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none focus:outline-none disabled:cursor-not-allowed"
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        <Button
          type="button"
          size="icon"
          className="size-8 shrink-0 rounded-full"
          disabled={disabled}
          onClick={() => void handleSend()}
        >
          <ArrowUp size={16} />
        </Button>
      </div>
    </div>
  );
}
