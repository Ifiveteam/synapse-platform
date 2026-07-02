import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { useNavigate } from "react-router-dom";

import { ChartBlock } from "@/components/home/chart-block";
import { type ChatMessage, useChatStore } from "@/stores/chat";
import { CHAT_THEMES, useChatThemeStore } from "@/stores/chat-theme";

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

const MENU_W = 240;
const MENU_H = 120;

function ContextMenu({
  x, y, onClose,
}: {
  x: number; y: number; onClose: () => void;
}) {
  const { themeId, setTheme } = useChatThemeStore();
  const ref = useRef<HTMLDivElement>(null);

  const safeX = Math.min(x, window.innerWidth - MENU_W - 8);
  const safeY = Math.min(y, window.innerHeight - MENU_H - 8);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={ref}
      style={{ top: safeY, left: safeX }}
      className="fixed z-50 rounded-2xl border border-border bg-card p-3 shadow-2xl"
    >
      <p className="mb-2.5 text-[11px] font-semibold text-muted-foreground">채팅 테마</p>
      <div className="grid grid-cols-5 gap-2.5">
        {CHAT_THEMES.map((theme) => (
          <button
            key={theme.id}
            type="button"
            title={theme.name}
            onClick={() => { setTheme(theme.id); onClose(); }}
            className="group flex items-center justify-center"
          >
            <div
              className={`size-10 rounded-full shadow-md transition-all duration-150 group-hover:scale-110 ${
                themeId === theme.id ? "scale-110 ring-2 ring-offset-2 ring-foreground/50" : ""
              }`}
              style={{ background: theme.bubble }}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageRow({ msg }: { msg: ChatMessage }) {
  const time = formatTime(msg.createdAt);
  const isUser = msg.role === "user";
  const currentTheme = useChatThemeStore((s) => s.currentTheme());

  return (
    <div className={`group flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {isUser && time && (
        <span className="shrink-0 translate-x-1 text-[11px] text-muted-foreground opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100">
          {time}
        </span>
      )}

      {isUser ? (
        <div
          className="max-w-[75%] rounded-3xl rounded-br-md px-4 py-2.5 text-sm text-white"
          style={{ background: currentTheme.bubble }}
        >
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
            <p className="text-muted-foreground px-1 text-xs italic">{msg.status}</p>
          )}
          {(msg.content || !msg.status || msg.chartData?.length) && (
            <div className="rounded-3xl rounded-bl-md bg-card px-4 py-2.5 text-sm leading-relaxed shadow-sm ring-1 ring-black/5 dark:ring-white/5">
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

export function ChatMessages() {
  const messages = useChatStore((s) => s.messages);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { hasSeenTip, markTipSeen } = useChatThemeStore();
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);
  const [showTip, setShowTip] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!hasSeenTip) {
      const t = setTimeout(() => {
        setShowTip(true);
        markTipSeen();
        setTimeout(() => setShowTip(false), 3000);
      }, 1500);
      return () => clearTimeout(t);
    }
  }, [hasSeenTip, markTipSeen]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setMenu({ x: e.clientX, y: e.clientY });
  };

  return (
    <div
      className="relative flex min-h-0 flex-1 flex-col overflow-y-auto px-6 py-4"
      onContextMenu={handleContextMenu}
    >
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        {messages.map((msg) => (
          <MessageRow key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {showTip && (
        <div className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 rounded-full bg-foreground/80 px-4 py-2 text-xs text-background backdrop-blur-sm">
          우클릭으로 채팅 테마를 변경할 수 있어요
        </div>
      )}

      {menu && (
        <ContextMenu x={menu.x} y={menu.y} onClose={() => setMenu(null)} />
      )}
    </div>
  );
}
