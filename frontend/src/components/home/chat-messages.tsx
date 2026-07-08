import { useEffect, useRef } from "react";
import Markdown from "react-markdown";
import { useNavigate } from "react-router-dom";

import { ChartBlock } from "@/components/home/chart-block";
import { type ChatMessage, type ChatStoreHook, useChatStore } from "@/stores/chat";

function formatTime(ts?: number) {
  if (!ts) return null;
  return new Date(ts).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function ChatLink({ href, children }: { href?: string; children?: React.ReactNode }) {
  const navigate = useNavigate();
  const isInternal = href?.startsWith("/");

  return (
    <button
      onClick={() => isInternal ? navigate(href!) : window.open(href, "_blank")}
      className="mt-1 inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-opacity hover:opacity-90"
    >
      {children}
    </button>
  );
}

function MessageRow({ msg }: { msg: ChatMessage }) {
  const time = formatTime(msg.createdAt);
  const isUser = msg.role === "user";

  return (
    <div className={`group flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {isUser && time && (
        <span className="shrink-0 translate-x-1 text-[11px] text-muted-foreground opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
          {time}
        </span>
      )}

      {isUser ? (
        <div className="bg-primary max-w-[75%] rounded-3xl rounded-br-md px-4 py-2.5 text-sm text-white">
          {msg.imageUrl && (
            <img
              src={msg.imageUrl}
              alt=""
              className="mb-1.5 max-h-52 w-full rounded-2xl object-cover"
            />
          )}
          {msg.content}
        </div>
      ) : (
        <div className="flex max-w-[85%] flex-col gap-1">
          {msg.status && (
            <div className="flex items-center gap-2 px-1">
              <span
                className="border-muted-foreground/25 border-t-primary inline-block size-3 shrink-0 rounded-full border-2"
                style={{ animation: "status-ring-spin 0.8s linear infinite" }}
              />
              <p
                key={msg.status}
                className="text-muted-foreground text-xs"
                style={{ animation: "status-fade-in 0.25s ease-out" }}
              >
                {msg.status}
              </p>
            </div>
          )}
          {(msg.content || !msg.status || msg.chartData?.length) && (
            <div className="rounded-3xl rounded-bl-md bg-muted px-4 py-2.5 text-sm leading-relaxed shadow-sm ring-1 ring-black/5 dark:ring-white/5">
              {msg.chartData?.length ? <ChartBlock charts={msg.chartData} /> : null}
              <div className="[&_blockquote]:border-l-2 [&_blockquote]:pl-2 [&_blockquote]:italic [&_code]:rounded [&_code]:bg-black/10 [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs [&_ol]:ml-4 [&_ol]:list-decimal [&_ol]:space-y-0.5 [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_ul]:ml-4 [&_ul]:list-disc [&_ul]:space-y-0.5 dark:[&_code]:bg-white/10">
                <Markdown components={{ a: ({ href, children }) => <ChatLink href={href}>{children}</ChatLink> }}>{msg.content}</Markdown>
              </div>
              {msg.streaming && msg.content && (
                <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current align-middle opacity-70" />
              )}
            </div>
          )}
        </div>
      )}

      {!isUser && time && (
        <span className="shrink-0 -translate-x-1 text-[11px] text-muted-foreground opacity-0 transition-all duration-200 group-hover:-translate-x-0 group-hover:opacity-100">
          {time}
        </span>
      )}
    </div>
  );
}

export function ChatMessages({
  useStore = useChatStore,
  maxWidthClassName = "max-w-2xl",
}: {
  useStore?: ChatStoreHook;
  /** 메시지 컬럼 최대 폭 (Tailwind max-w-* 클래스). 페이지마다 다르게 좁힐 때 사용. */
  maxWidthClassName?: string;
}) {
  const messages = useStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-4">
      <div className={`mx-auto flex w-full flex-col gap-4 ${maxWidthClassName}`}>
        {messages.map((msg) => (
          <MessageRow key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
