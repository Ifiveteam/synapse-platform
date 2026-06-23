import { useEffect, useRef } from "react";
import Markdown from "react-markdown";

import { ChartBlock } from "@/components/home/chart-block";
import { type ChatMessage, useChatStore } from "@/stores/chat";

function formatTime(ts?: number) {
  if (!ts) return null;
  return new Date(ts).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function MessageRow({ msg }: { msg: ChatMessage }) {
  const time = formatTime(msg.createdAt);
  const isUser = msg.role === "user";

  return (
    <div className={`group flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {/* 유저 메시지: 타임이 왼쪽 */}
      {isUser && time && (
        <span className="shrink-0 translate-x-1 text-[11px] text-muted-foreground opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
          {time}
        </span>
      )}

      {isUser ? (
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
          {msg.content}
        </div>
      ) : (
        <div className="flex max-w-[85%] flex-col gap-1">
          {msg.status && (
            <p className="text-muted-foreground px-1 text-xs italic">{msg.status}</p>
          )}
          {(msg.content || !msg.status || msg.chartData?.length) && (
            <div className="rounded-2xl rounded-bl-sm bg-card px-4 py-2.5 text-sm leading-relaxed shadow-sm ring-1 ring-black/5 dark:ring-white/5">
              {msg.chartData?.length ? <ChartBlock charts={msg.chartData} /> : null}
              <div className="[&_blockquote]:border-l-2 [&_blockquote]:pl-2 [&_blockquote]:italic [&_code]:rounded [&_code]:bg-black/10 [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs [&_ol]:ml-4 [&_ol]:list-decimal [&_ol]:space-y-0.5 [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:ml-4 [&_ul]:list-disc [&_ul]:space-y-0.5 dark:[&_code]:bg-white/10">
                <Markdown>{msg.content}</Markdown>
              </div>
              {msg.streaming && msg.content && (
                <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current align-middle opacity-70" />
              )}
            </div>
          )}
        </div>
      )}

      {/* AI 메시지: 타임이 오른쪽 */}
      {!isUser && time && (
        <span className="shrink-0 -translate-x-1 text-[11px] text-muted-foreground opacity-0 transition-all duration-200 group-hover:-translate-x-0 group-hover:opacity-100">
          {time}
        </span>
      )}
    </div>
  );
}

export function ChatMessages() {
  const messages = useChatStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-4">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        {messages.map((msg) => (
          <MessageRow key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
